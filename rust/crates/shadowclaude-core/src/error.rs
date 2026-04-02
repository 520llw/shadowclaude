//! Error types and handling for ShadowClaude Core
//!
//! This module provides comprehensive error handling with:
//! - Hierarchical error types
//! - Error context and severity levels
//! - Structured error reporting
//! - Error recovery strategies

use std::backtrace::Backtrace;
use std::fmt;
use std::sync::Arc;
use thiserror::Error;
use tracing::{error, warn};

/// Result type alias for core operations
pub type CoreResult<T> = Result<T, CoreError>;

/// Severity level for errors
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize)]
pub enum ErrorSeverity {
    /// Informational, no action needed
    Info,
    /// Warning, operation succeeded but with issues
    Warning,
    /// Error, operation failed but system is stable
    Error,
    /// Critical, system may be unstable
    Critical,
    /// Fatal, system cannot continue
    Fatal,
}

impl fmt::Display for ErrorSeverity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ErrorSeverity::Info => write!(f, "INFO"),
            ErrorSeverity::Warning => write!(f, "WARNING"),
            ErrorSeverity::Error => write!(f, "ERROR"),
            ErrorSeverity::Critical => write!(f, "CRITICAL"),
            ErrorSeverity::Fatal => write!(f, "FATAL"),
        }
    }
}

/// Error context providing additional information about when/where an error occurred
#[derive(Debug, Clone)]
pub struct ErrorContext {
    /// The operation being performed when the error occurred
    pub operation: String,
    /// The component where the error originated
    pub component: String,
    /// Additional context information
    pub details: Option<String>,
    /// The severity level
    pub severity: ErrorSeverity,
    /// Timestamp when the error occurred
    pub timestamp: chrono::DateTime<chrono::Utc>,
    /// Correlation ID for tracing
    pub correlation_id: uuid::Uuid,
}

impl ErrorContext {
    /// Create a new error context
    pub fn new(operation: impl Into<String>, component: impl Into<String>) -> Self {
        Self {
            operation: operation.into(),
            component: component.into(),
            details: None,
            severity: ErrorSeverity::Error,
            timestamp: chrono::Utc::now(),
            correlation_id: uuid::Uuid::new_v4(),
        }
    }

    /// Set the severity level
    pub fn with_severity(mut self, severity: ErrorSeverity) -> Self {
        self.severity = severity;
        self
    }

    /// Add details to the context
    pub fn with_details(mut self, details: impl Into<String>) -> Self {
        self.details = Some(details.into());
        self
    }

    /// Set a specific correlation ID
    pub fn with_correlation_id(mut self, id: uuid::Uuid) -> Self {
        self.correlation_id = id;
        self
    }
}

impl Default for ErrorContext {
    fn default() -> Self {
        Self::new("unknown", "unknown")
    }
}

/// Main error type for ShadowClaude Core
#[derive(Error, Debug, Clone)]
pub enum CoreError {
    /// Session-related errors
    #[error("Session error: {0}")]
    SessionError(SessionError),

    /// Dialogue-related errors
    #[error("Dialogue error: {0}")]
    DialogueError(DialogueError),

    /// Cache-related errors
    #[error("Cache error: {0}")]
    CacheError(CacheError),

    /// Security-related errors
    #[error("Security error: {0}")]
    SecurityError(SecurityError),

    /// Message-related errors
    #[error("Message error: {0}")]
    MessageError(MessageError),

    /// Protocol-related errors
    #[error("Protocol error: {0}")]
    ProtocolError(String),

    /// Serialization errors
    #[error("Serialization error: {0}")]
    SerializationError(String),

    /// Validation errors
    #[error("Validation error: {message}")]
    ValidationError {
        /// Error message
        message: String,
        /// Field that failed validation
        field: Option<String>,
    },

    /// Timeout errors
    #[error("Operation timed out after {duration_ms}ms: {operation}")]
    Timeout {
        /// Operation that timed out
        operation: String,
        /// Timeout duration in milliseconds
        duration_ms: u64,
    },

    /// Resource exhausted errors
    #[error("Resource exhausted: {resource}")]
    ResourceExhausted {
        /// Type of resource
        resource: String,
        /// Current usage
        current: u64,
        /// Maximum allowed
        maximum: u64,
    },

    /// Not found errors
    #[error("{resource_type} not found: {identifier}")]
    NotFound {
        /// Type of resource
        resource_type: String,
        /// Identifier that was not found
        identifier: String,
    },

    /// Already exists errors
    #[error("{resource_type} already exists: {identifier}")]
    AlreadyExists {
        /// Type of resource
        resource_type: String,
        /// Identifier that already exists
        identifier: String,
    },

    /// Not initialized error
    #[error("Core runtime not initialized")]
    NotInitialized,

    /// Already initialized error
    #[error("Core runtime already initialized")]
    AlreadyInitialized,

    /// Initialization failed
    #[error("Initialization failed: {0}")]
    InitializationFailed(String),

    /// Shutdown in progress
    #[error("Shutdown in progress")]
    ShutdownInProgress,

    /// Cancelled operation
    #[error("Operation cancelled")]
    Cancelled,

    /// Permission denied
    #[error("Permission denied: {required_permission}")]
    PermissionDenied {
        /// The required permission
        required_permission: String,
        /// The context
        context: Option<String>,
    },

    /// Rate limit exceeded
    #[error("Rate limit exceeded: {resource}. Retry after {retry_after_secs}s")]
    RateLimitExceeded {
        /// The rate-limited resource
        resource: String,
        /// Seconds until retry is allowed
        retry_after_secs: u64,
    },

    /// Internal error
    #[error("Internal error: {0}")]
    Internal(String),

    /// Unknown error
    #[error("Unknown error: {0}")]
    Unknown(String),
}

impl CoreError {
    /// Get the severity level for this error
    pub fn severity(&self) -> ErrorSeverity {
        match self {
            CoreError::SessionError(e) => e.severity(),
            CoreError::DialogueError(e) => e.severity(),
            CoreError::CacheError(e) => e.severity(),
            CoreError::SecurityError(e) => e.severity(),
            CoreError::MessageError(e) => e.severity(),
            CoreError::ProtocolError(_) => ErrorSeverity::Error,
            CoreError::SerializationError(_) => ErrorSeverity::Error,
            CoreError::ValidationError { .. } => ErrorSeverity::Warning,
            CoreError::Timeout { .. } => ErrorSeverity::Warning,
            CoreError::ResourceExhausted { .. } => ErrorSeverity::Error,
            CoreError::NotFound { .. } => ErrorSeverity::Warning,
            CoreError::AlreadyExists { .. } => ErrorSeverity::Warning,
            CoreError::NotInitialized => ErrorSeverity::Critical,
            CoreError::AlreadyInitialized => ErrorSeverity::Warning,
            CoreError::InitializationFailed(_) => ErrorSeverity::Critical,
            CoreError::ShutdownInProgress => ErrorSeverity::Info,
            CoreError::Cancelled => ErrorSeverity::Info,
            CoreError::PermissionDenied { .. } => ErrorSeverity::Error,
            CoreError::RateLimitExceeded { .. } => ErrorSeverity::Warning,
            CoreError::Internal(_) => ErrorSeverity::Error,
            CoreError::Unknown(_) => ErrorSeverity::Error,
        }
    }

    /// Check if this error is retryable
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            CoreError::Timeout { .. }
                | CoreError::RateLimitExceeded { .. }
                | CoreError::ResourceExhausted { .. }
                | CoreError::ProtocolError(_)
                | CoreError::CacheError(CacheError::TemporaryUnavailable)
        )
    }

    /// Check if this error is fatal (requires restart)
    pub fn is_fatal(&self) -> bool {
        matches!(
            self,
            CoreError::NotInitialized
                | CoreError::InitializationFailed(_)
                | CoreError::Internal(_)
        )
    }

    /// Convert to an error with context
    pub fn with_context(self, ctx: ErrorContext) -> ContextualError {
        ContextualError {
            error: self,
            context: ctx,
        }
    }
}

/// Session-specific errors
#[derive(Error, Debug, Clone)]
pub enum SessionError {
    /// Session not found
    #[error("Session not found: {0}")]
    NotFound(String),

    /// Session expired
    #[error("Session expired: {session_id}. Expired at {expired_at}")]
    Expired {
        /// Session ID
        session_id: String,
        /// Expiration timestamp
        expired_at: chrono::DateTime<chrono::Utc>,
    },

    /// Session limit exceeded
    #[error("Session limit exceeded. Max: {max}, Current: {current}")]
    LimitExceeded {
        /// Maximum allowed sessions
        max: usize,
        /// Current session count
        current: usize,
    },

    /// Invalid session state
    #[error("Invalid session state: {current_state}. Expected: {expected_states:?}")]
    InvalidState {
        /// Current state
        current_state: String,
        /// Expected states
        expected_states: Vec<String>,
    },

    /// Session locked
    #[error("Session locked: {0}")]
    Locked(String),

    /// Session migration failed
    #[error("Session migration failed: {0}")]
    MigrationFailed(String),
}

impl SessionError {
    fn severity(&self) -> ErrorSeverity {
        match self {
            SessionError::NotFound(_) => ErrorSeverity::Warning,
            SessionError::Expired { .. } => ErrorSeverity::Info,
            SessionError::LimitExceeded { .. } => ErrorSeverity::Error,
            SessionError::InvalidState { .. } => ErrorSeverity::Error,
            SessionError::Locked(_) => ErrorSeverity::Warning,
            SessionError::MigrationFailed(_) => ErrorSeverity::Error,
        }
    }
}

/// Dialogue-specific errors
#[derive(Error, Debug, Clone)]
pub enum DialogueError {
    /// Invalid state transition
    #[error("Invalid state transition from {from} to {to}")]
    InvalidTransition {
        /// From state
        from: String,
        /// To state
        to: String,
    },

    /// Turn processing failed
    #[error("Turn processing failed: {0}")]
    TurnFailed(String),

    /// Context window exceeded
    #[error("Context window exceeded. Current: {current_tokens}, Max: {max_tokens}")]
    ContextWindowExceeded {
        /// Current token count
        current_tokens: usize,
        /// Maximum token count
        max_tokens: usize,
    },

    /// Invalid message format
    #[error("Invalid message format: {0}")]
    InvalidMessageFormat(String),

    /// Model error
    #[error("Model error: {0}")]
    ModelError(String),

    /// Tool execution failed
    #[error("Tool execution failed: {tool_name}. Error: {error}")]
    ToolExecutionFailed {
        /// Tool name
        tool_name: String,
        /// Error message
        error: String,
    },
}

impl DialogueError {
    fn severity(&self) -> ErrorSeverity {
        match self {
            DialogueError::InvalidTransition { .. } => ErrorSeverity::Error,
            DialogueError::TurnFailed(_) => ErrorSeverity::Error,
            DialogueError::ContextWindowExceeded { .. } => ErrorSeverity::Warning,
            DialogueError::InvalidMessageFormat(_) => ErrorSeverity::Error,
            DialogueError::ModelError(_) => ErrorSeverity::Error,
            DialogueError::ToolExecutionFailed { .. } => ErrorSeverity::Error,
        }
    }
}

/// Cache-specific errors
#[derive(Error, Debug, Clone)]
pub enum CacheError {
    /// Entry not found
    #[error("Cache entry not found: {0}")]
    EntryNotFound(String),

    /// Cache full
    #[error("Cache full. Current: {current_size}, Max: {max_size}")]
    CacheFull {
        /// Current cache size
        current_size: usize,
        /// Maximum cache size
        max_size: usize,
    },

    /// Serialization failed
    #[error("Cache serialization failed: {0}")]
    SerializationFailed(String),

    /// Deserialization failed
    #[error("Cache deserialization failed: {0}")]
    DeserializationFailed(String),

    /// TTL expired
    #[error("Cache entry TTL expired: {key}. Expired at {expired_at}")]
    TtlExpired {
        /// Cache key
        key: String,
        /// Expiration timestamp
        expired_at: chrono::DateTime<chrono::Utc>,
    },

    /// Temporary unavailable
    #[error("Cache temporarily unavailable")]
    TemporaryUnavailable,

    /// Consistency error
    #[error("Cache consistency error: {0}")]
    ConsistencyError(String),
}

impl CacheError {
    fn severity(&self) -> ErrorSeverity {
        match self {
            CacheError::EntryNotFound(_) => ErrorSeverity::Info,
            CacheError::CacheFull { .. } => ErrorSeverity::Warning,
            CacheError::SerializationFailed(_) => ErrorSeverity::Error,
            CacheError::DeserializationFailed(_) => ErrorSeverity::Error,
            CacheError::TtlExpired { .. } => ErrorSeverity::Info,
            CacheError::TemporaryUnavailable => ErrorSeverity::Warning,
            CacheError::ConsistencyError(_) => ErrorSeverity::Error,
        }
    }
}

/// Security-specific errors
#[derive(Error, Debug, Clone)]
pub enum SecurityError {
    /// Authentication failed
    #[error("Authentication failed: {0}")]
    AuthenticationFailed(String),

    /// Authorization failed
    #[error("Authorization failed: {0}")]
    AuthorizationFailed(String),

    /// Token expired
    #[error("Token expired at {expired_at}")]
    TokenExpired {
        /// Expiration timestamp
        expired_at: chrono::DateTime<chrono::Utc>,
    },

    /// Invalid token
    #[error("Invalid token: {0}")]
    InvalidToken(String),

    /// Permission denied
    #[error("Permission denied: {permission}")]
    PermissionDenied {
        /// Required permission
        permission: String,
    },

    /// Rate limit exceeded
    #[error("Rate limit exceeded for {resource}. Limit: {limit}, Window: {window_secs}s")]
    RateLimitExceeded {
        /// Resource being rate limited
        resource: String,
        /// Maximum allowed requests
        limit: u64,
        /// Window in seconds
        window_secs: u64,
    },

    /// Content policy violation
    #[error("Content policy violation: {policy}. Details: {details}")]
    ContentPolicyViolation {
        /// Policy that was violated
        policy: String,
        /// Violation details
        details: String,
    },

    /// Suspicious activity detected
    #[error("Suspicious activity detected: {activity}. Risk score: {risk_score}")]
    SuspiciousActivity {
        /// Type of activity
        activity: String,
        /// Risk score (0-100)
        risk_score: u8,
    },
}

impl SecurityError {
    fn severity(&self) -> ErrorSeverity {
        match self {
            SecurityError::AuthenticationFailed(_) => ErrorSeverity::Error,
            SecurityError::AuthorizationFailed(_) => ErrorSeverity::Error,
            SecurityError::TokenExpired { .. } => ErrorSeverity::Info,
            SecurityError::InvalidToken(_) => ErrorSeverity::Warning,
            SecurityError::PermissionDenied { .. } => ErrorSeverity::Error,
            SecurityError::RateLimitExceeded { .. } => ErrorSeverity::Warning,
            SecurityError::ContentPolicyViolation { .. } => ErrorSeverity::Error,
            SecurityError::SuspiciousActivity { risk_score, .. } => {
                if *risk_score > 80 {
                    ErrorSeverity::Critical
                } else if *risk_score > 50 {
                    ErrorSeverity::Error
                } else {
                    ErrorSeverity::Warning
                }
            }
        }
    }
}

/// Message-specific errors
#[derive(Error, Debug, Clone)]
pub enum MessageError {
    /// Message too large
    #[error("Message too large: {size} bytes. Max: {max_size} bytes")]
    TooLarge {
        /// Actual size
        size: usize,
        /// Maximum allowed size
        max_size: usize,
    },

    /// Invalid message type
    #[error("Invalid message type: {0}")]
    InvalidType(String),

    /// Queue full
    #[error("Message queue full. Current: {current}, Max: {max}")]
    QueueFull {
        /// Current queue size
        current: usize,
        /// Maximum queue size
        max: usize,
    },

    /// Delivery failed
    #[error("Message delivery failed: {0}")]
    DeliveryFailed(String),

    /// Parse error
    #[error("Message parse error: {0}")]
    ParseError(String),
}

impl MessageError {
    fn severity(&self) -> ErrorSeverity {
        match self {
            MessageError::TooLarge { .. } => ErrorSeverity::Error,
            MessageError::InvalidType(_) => ErrorSeverity::Error,
            MessageError::QueueFull { .. } => ErrorSeverity::Warning,
            MessageError::DeliveryFailed(_) => ErrorSeverity::Error,
            MessageError::ParseError(_) => ErrorSeverity::Error,
        }
    }
}

/// Error with context information
#[derive(Debug, Clone)]
pub struct ContextualError {
    /// The underlying error
    pub error: CoreError,
    /// Context information
    pub context: ErrorContext,
}

impl fmt::Display for ContextualError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[{}] {} in {}: {} | Correlation: {}",
            self.context.severity,
            self.context.operation,
            self.context.component,
            self.error,
            self.context.correlation_id
        )?;
        if let Some(details) = &self.context.details {
            write!(f, " | Details: {}", details)?;
        }
        Ok(())
    }
}

impl std::error::Error for ContextualError {
    fn source(&self) -> Option<&( dyn std::error::Error + 'static )> {
        Some(&self.error)
    }
}

/// Error recovery strategy
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RecoveryStrategy {
    /// Retry the operation
    Retry {
        /// Maximum retry attempts
        max_attempts: u32,
        /// Delay between retries in milliseconds
        delay_ms: u64,
    },
    /// Fail the operation
    Fail,
    /// Degrade functionality
    Degrade,
    /// Ignore the error
    Ignore,
    /// Circuit breaker - stop attempts for a period
    CircuitBreaker {
        /// Duration to open circuit in milliseconds
        open_duration_ms: u64,
    },
}

impl RecoveryStrategy {
    /// Get the default recovery strategy for an error
    pub fn for_error(error: &CoreError) -> Self {
        if error.is_retryable() {
            RecoveryStrategy::Retry {
                max_attempts: 3,
                delay_ms: 1000,
            }
        } else if error.is_fatal() {
            RecoveryStrategy::Fail
        } else {
            RecoveryStrategy::Degrade
        }
    }
}

/// Extension trait for Result types
pub trait ResultExt<T, E> {
    /// Add context to an error
    fn with_context(self, ctx: ErrorContext) -> Result<T, ContextualError>;

    /// Map error to CoreError
    fn map_to_core(self, f: impl FnOnce(E) -> CoreError) -> CoreResult<T>;

    /// Log the error with appropriate level
    fn log_error(self) -> Self;
}

impl<T, E: std::fmt::Debug + std::fmt::Display> ResultExt<T, E> for Result<T, E> {
    fn with_context(self, ctx: ErrorContext) -> Result<T, ContextualError> {
        self.map_err(|e| {
            let core_error = CoreError::Unknown(e.to_string());
            ContextualError {
                error: core_error,
                context: ctx,
            }
        })
    }

    fn map_to_core(self, f: impl FnOnce(E) -> CoreError) -> CoreResult<T> {
        self.map_err(f)
    }

    fn log_error(self) -> Self {
        if let Err(ref e) = self {
            error!(error = %e, "Operation failed");
        }
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_severity_ordering() {
        assert!(ErrorSeverity::Info < ErrorSeverity::Warning);
        assert!(ErrorSeverity::Warning < ErrorSeverity::Error);
        assert!(ErrorSeverity::Error < ErrorSeverity::Critical);
        assert!(ErrorSeverity::Critical < ErrorSeverity::Fatal);
    }

    #[test]
    fn test_error_context_builder() {
        let ctx = ErrorContext::new("test_op", "test_component")
            .with_severity(ErrorSeverity::Warning)
            .with_details("additional info");

        assert_eq!(ctx.operation, "test_op");
        assert_eq!(ctx.component, "test_component");
        assert_eq!(ctx.severity, ErrorSeverity::Warning);
        assert_eq!(ctx.details, Some("additional info".to_string()));
    }

    #[test]
    fn test_core_error_is_retryable() {
        let timeout = CoreError::Timeout {
            operation: "test".to_string(),
            duration_ms: 1000,
        };
        assert!(timeout.is_retryable());

        let not_found = CoreError::NotFound {
            resource_type: "test".to_string(),
            identifier: "id".to_string(),
        };
        assert!(!not_found.is_retryable());
    }

    #[test]
    fn test_recovery_strategy() {
        let retryable = CoreError::Timeout {
            operation: "test".to_string(),
            duration_ms: 1000,
        };
        let strategy = RecoveryStrategy::for_error(&retryable);
        assert!(matches!(strategy, RecoveryStrategy::Retry { .. }));

        let fatal = CoreError::Internal("test".to_string());
        let strategy = RecoveryStrategy::for_error(&fatal);
        assert_eq!(strategy, RecoveryStrategy::Fail);
    }
}
