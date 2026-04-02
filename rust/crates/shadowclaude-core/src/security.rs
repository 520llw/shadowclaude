//! Security system with six-layer defense for ShadowClaude
//!
//! The six layers are:
//! 1. Authentication - Verify identity
//! 2. Authorization - Check permissions
//! 3. Input Validation - Sanitize and validate inputs
//! 4. Rate Limiting - Prevent abuse
//! 5. Content Policy - Enforce safety rules
//! 6. Audit Logging - Track all security events

use crate::{
    error::{CoreError, CoreResult, ErrorContext, ErrorSeverity, SecurityError},
    types::*,
};
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::net::IpAddr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::{debug, error, info, instrument, warn};

/// Security level for different environments
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum SecurityLevel {
    /// Development environment, minimal security
    Development,
    /// Testing environment
    Testing,
    /// Staging environment
    Staging,
    /// Production environment, maximum security
    Production,
    /// High-security environment
    HighSecurity,
}

impl SecurityLevel {
    /// Check if this level requires strict validation
    pub fn requires_strict_validation(&self
    ) -> bool {
        matches!(self, SecurityLevel::Production | SecurityLevel::HighSecurity)
    }

    /// Check if this level requires audit logging
    pub fn requires_audit_logging(&self
    ) -> bool {
        matches!(
            self,
            SecurityLevel::Staging | SecurityLevel::Production | SecurityLevel::HighSecurity
        )
    }

    /// Check if this level requires content filtering
    pub fn requires_content_filtering(&self
    ) -> bool {
        matches!(self, SecurityLevel::Production | SecurityLevel::HighSecurity)
    }
}

impl Default for SecurityLevel {
    fn default() -> Self {
        SecurityLevel::Production
    }
}

/// Security configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    /// Security level
    pub level: SecurityLevel,
    /// Authentication configuration
    pub auth: AuthConfig,
    /// Rate limiting configuration
    pub rate_limit: RateLimitConfig,
    /// Content policy configuration
    pub content_policy: ContentPolicyConfig,
    /// Audit logging configuration
    pub audit: AuditConfig,
    /// Suspicious activity threshold
    pub suspicious_threshold: u8,
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            level: SecurityLevel::Production,
            auth: AuthConfig::default(),
            rate_limit: RateLimitConfig::default(),
            content_policy: ContentPolicyConfig::default(),
            audit: AuditConfig::default(),
            suspicious_threshold: 70,
        }
    }
}

/// Authentication configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    /// Enable authentication
    pub enabled: bool,
    /// Token expiration time in seconds
    pub token_ttl_secs: u64,
    /// Refresh token TTL in seconds
    pub refresh_token_ttl_secs: u64,
    /// Maximum failed login attempts
    pub max_failed_attempts: u32,
    /// Lockout duration in seconds
    pub lockout_duration_secs: u64,
    /// Require MFA
    pub require_mfa: bool,
    /// Allowed token types
    pub allowed_token_types: Vec<TokenType>,
}

impl Default for AuthConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            token_ttl_secs: 3600,
            refresh_token_ttl_secs: 86400 * 7,
            max_failed_attempts: 5,
            lockout_duration_secs: 900,
            require_mfa: false,
            allowed_token_types: vec![TokenType::Bearer, TokenType::ApiKey],
        }
    }
}

/// Token types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TokenType {
    /// Bearer token (JWT)
    Bearer,
    /// API key
    ApiKey,
    /// Session token
    Session,
    /// OAuth token
    OAuth,
}

/// Rate limiting configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    /// Enable rate limiting
    pub enabled: bool,
    /// Default rate limit
    pub default: RateLimit,
    /// Per-endpoint rate limits
    pub endpoints: HashMap<String, RateLimit>,
    /// IP-based rate limiting
    pub ip_based: bool,
    /// User-based rate limiting
    pub user_based: bool,
    /// Burst allowance
    pub burst_size: u32,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        let mut endpoints = HashMap::new();
        endpoints.insert(
            "chat".to_string(),
            RateLimit::new(100, 60),
        );
        endpoints.insert(
            "tools".to_string(),
            RateLimit::new(50, 60),
        );

        Self {
            enabled: true,
            default: RateLimit::new(1000, 60),
            endpoints,
            ip_based: true,
            user_based: true,
            burst_size: 10,
        }
    }
}

/// Content policy configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentPolicyConfig {
    /// Enable content filtering
    pub enabled: bool,
    /// Blocked content types
    pub blocked_types: Vec<ContentType>,
    /// Maximum input length
    pub max_input_length: usize,
    /// Maximum output length
    pub max_output_length: usize,
    /// PII detection
    pub detect_pii: bool,
    /// Toxic content detection
    pub detect_toxicity: bool,
    /// Custom blocked patterns
    pub blocked_patterns: Vec<String>,
}

impl Default for ContentPolicyConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            blocked_types: vec![
                ContentType::Malware,
                ContentType::Phishing,
                ContentType::Illegal,
            ],
            max_input_length: 100_000,
            max_output_length: 50_000,
            detect_pii: true,
            detect_toxicity: true,
            blocked_patterns: Vec::new(),
        }
    }
}

/// Content types for filtering
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ContentType {
    /// Malware
    Malware,
    /// Phishing attempt
    Phishing,
    /// Spam
    Spam,
    /// Illegal content
    Illegal,
    /// Harassment
    Harassment,
    /// Hate speech
    HateSpeech,
    /// Explicit content
    Explicit,
    /// PII (Personally Identifiable Information)
    Pii,
}

/// Audit configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditConfig {
    /// Enable audit logging
    pub enabled: bool,
    /// Log level for security events
    pub log_level: String,
    /// Retention days
    pub retention_days: u32,
    /// Include request bodies
    pub include_request_body: bool,
    /// Include response bodies
    pub include_response_body: bool,
    /// Encrypt audit logs
    pub encrypt_logs: bool,
}

impl Default for AuditConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            log_level: "info".to_string(),
            retention_days: 90,
            include_request_body: false,
            include_response_body: false,
            encrypt_logs: true,
        }
    }
}

/// Security context for a request/session
#[derive(Debug, Clone, Default)]
pub struct SecurityContext {
    /// User ID
    pub user_id: Option<String>,
    /// Organization ID
    pub org_id: Option<String>,
    /// Session ID
    pub session_id: Option<String>,
    /// Client IP address
    pub client_ip: Option<IpAddr>,
    /// Authentication token
    pub token: Option<AuthToken>,
    /// Granted permissions
    pub permissions: HashSet<Permission>,
    /// Security level for this context
    pub level: SecurityLevel,
    /// Risk score (0-100)
    pub risk_score: u8,
}

impl SecurityContext {
    /// Create a new security context
    pub fn new() -> Self {
        Self::default()
    }

    /// Set user ID
    pub fn with_user_id(mut self, user_id: impl Into<String>) -> Self {
        self.user_id = Some(user_id.into());
        self
    }

    /// Set permissions
    pub fn with_permissions(mut self, permissions: HashSet<Permission>) -> Self {
        self.permissions = permissions;
        self
    }

    /// Check if the context has a specific permission
    pub fn has_permission(&self,
        permission: &Permission
    ) -> bool {
        self.permissions.contains(permission)
    }

    /// Check if authenticated
    pub fn is_authenticated(&self
    ) -> bool {
        self.user_id.is_some() && self.token.is_some()
    }

    /// Calculate combined risk score
    pub fn calculate_risk(&mut self
    ) {
        let mut score = 0u8;

        if self.user_id.is_none() {
            score += 20;
        }

        if self.client_ip.is_none() {
            score += 10;
        }

        if self.permissions.is_empty() {
            score += 15;
        }

        self.risk_score = score.min(100);
    }
}

/// Authentication token
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthToken {
    /// Token type
    pub token_type: TokenType,
    /// Token value
    pub value: String,
    /// Expiration time
    pub expires_at: Option<Timestamp>,
    /// Issued at
    pub issued_at: Timestamp,
    /// Issuer
    pub issuer: String,
}

impl AuthToken {
    /// Check if the token is expired
    pub fn is_expired(&self
    ) -> bool {
        self.expires_at
            .map(|exp| Timestamp::now().is_after(exp))
            .unwrap_or(false)
    }

    /// Check if the token is valid
    pub fn is_valid(&self
    ) -> bool {
        !self.is_expired()
    }
}

/// Permission enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Permission {
    /// Read own data
    ReadOwn,
    /// Write own data
    WriteOwn,
    /// Delete own data
    DeleteOwn,
    /// Read any data
    ReadAny,
    /// Write any data
    WriteAny,
    /// Delete any data
    DeleteAny,
    /// Admin access
    Admin,
    /// Use tools
    UseTools,
    /// Manage sessions
    ManageSessions,
    /// View audit logs
    ViewAudit,
    /// Configure system
    Configure,
}

/// Security event types
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SecurityEventType {
    /// Authentication attempt
    AuthAttempt,
    /// Authentication success
    AuthSuccess,
    /// Authentication failure
    AuthFailure,
    /// Authorization check
    AuthzCheck,
    /// Authorization denied
    AuthzDenied,
    /// Rate limit triggered
    RateLimitTriggered,
    /// Content policy violation
    ContentViolation,
    /// Suspicious activity
    SuspiciousActivity,
    /// Session created
    SessionCreated,
    /// Session expired
    SessionExpired,
    /// Token refreshed
    TokenRefreshed,
    /// Permission granted
    PermissionGranted,
    /// Permission revoked
    PermissionRevoked,
}

/// Security event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityEvent {
    /// Event ID
    pub id: uuid::Uuid,
    /// Event type
    pub event_type: SecurityEventType,
    /// Timestamp
    pub timestamp: Timestamp,
    /// User ID
    pub user_id: Option<String>,
    /// Session ID
    pub session_id: Option<String>,
    /// Client IP
    pub client_ip: Option<String>,
    /// Event details
    pub details: HashMap<String, String>,
    /// Risk score
    pub risk_score: u8,
    /// Severity
    pub severity: ErrorSeverity,
}

impl SecurityEvent {
    /// Create a new security event
    pub fn new(event_type: SecurityEventType) -> Self {
        Self {
            id: uuid::Uuid::new_v4(),
            event_type,
            timestamp: Timestamp::now(),
            user_id: None,
            session_id: None,
            client_ip: None,
            details: HashMap::new(),
            risk_score: 0,
            severity: ErrorSeverity::Info,
        }
    }

    /// Set user ID
    pub fn with_user_id(mut self, user_id: impl Into<String>) -> Self {
        self.user_id = Some(user_id.into());
        self
    }

    /// Set session ID
    pub fn with_session_id(mut self, session_id: impl Into<String>) -> Self {
        self.session_id = Some(session_id.into());
        self
    }

    /// Set severity
    pub fn with_severity(mut self, severity: ErrorSeverity) -> Self {
        self.severity = severity;
        self
    }

    /// Add detail
    pub fn with_detail(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.details.insert(key.into(), value.into());
        self
    }
}

/// Rate limiter entry
struct RateLimitEntry {
    /// Request timestamps
    requests: RwLock<Vec<Instant>>,
    /// Blocked until
    blocked_until: RwLock<Option<Instant>>,
}

impl RateLimitEntry {
    fn new() -> Self {
        Self {
            requests: RwLock::new(Vec::new()),
            blocked_until: RwLock::new(None),
        }
    }

    fn is_blocked(&self
    ) -> bool {
        self.blocked_until
            .read()
            .map(|until| Instant::now() < until)
            .unwrap_or(false)
    }

    fn record_request(&self,
        limit: &RateLimit
    ) {
        let mut requests = self.requests.write();
        let now = Instant::now();
        let window = Duration::from_secs(limit.window_secs);

        // Remove old requests outside window
        requests.retain(|t| now.duration_since(*t) < window);

        // Add new request
        requests.push(now);
    }

    fn check_limit(&self,
        limit: &RateLimit
    ) -> bool {
        if self.is_blocked() {
            return false;
        }

        let requests = self.requests.read();
        (requests.len() as u64) < limit.max_requests
    }

    fn block(&self,
        duration: Duration
    ) {
        *self.blocked_until.write() = Some(Instant::now() + duration);
    }
}

/// Security engine implementing six-layer defense
pub struct SecurityEngine {
    /// Configuration
    config: SecurityConfig,
    /// Active tokens
    tokens: DashMap<String, AuthToken>,
    /// Rate limiters per key
    rate_limiters: DashMap<String, Arc<RateLimitEntry>>,
    /// Failed login attempts
    failed_attempts: DashMap<String, (u32, Instant)>,
    /// Audit log
    audit_log: RwLock<Vec<SecurityEvent>>,
    /// Event count
    event_count: AtomicU64,
    /// Suspicious activity tracker
    suspicious_activity: DashMap<String, Vec<SecurityEvent>>,
}

impl SecurityEngine {
    /// Create a new security engine
    pub async fn new(config: SecurityConfig) -> CoreResult<Self> {
        let engine = Self {
            config,
            tokens: DashMap::new(),
            rate_limiters: DashMap::new(),
            failed_attempts: DashMap::new(),
            audit_log: RwLock::new(Vec::new()),
            event_count: AtomicU64::new(0),
            suspicious_activity: DashMap::new(),
        };

        // Start cleanup task
        let rate_limiters = engine.rate_limiters.clone();
        let failed_attempts = engine.failed_attempts.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(60));

            loop {
                interval.tick().await;

                // Clean up old rate limiters
                let now = Instant::now();
                rate_limiters.retain(|_, entry| {
                    let requests = entry.requests.read();
                    !requests.is_empty() || entry.is_blocked()
                });

                // Clean up old failed attempts
                failed_attempts.retain(|_, (_, last_attempt)| {
                    now.duration_since(*last_attempt).as_secs() < 3600
                });
            }
        });

        info!("SecurityEngine initialized with {:?} level", engine.config.level);
        Ok(engine)
    }

    // Layer 1: Authentication

    /// Authenticate a token
    #[instrument(skip(self, token))]
    pub fn authenticate(&self,
        token: &str
    ) -> CoreResult<AuthToken> {
        if !self.config.auth.enabled {
            return Err(CoreError::SecurityError(
                SecurityError::AuthenticationFailed("Authentication disabled".to_string()),
            ));
        }

        // Check token existence
        let auth_token = self
            .tokens
            .get(token)
            .map(|t| t.clone())
            .ok_or_else(|| {
                CoreError::SecurityError(SecurityError::InvalidToken(
                    "Token not found".to_string(),
                ))
            })?;

        // Check expiration
        if auth_token.is_expired() {
            self.tokens.remove(token);
            self.log_event(
                SecurityEvent::new(SecurityEventType::AuthFailure)
                    .with_detail("reason", "token_expired")
                    .with_severity(ErrorSeverity::Warning),
            );
            return Err(CoreError::SecurityError(SecurityError::TokenExpired {
                expired_at: auth_token.expires_at.unwrap_or_default().to_datetime(),
            }));
        }

        self.log_event(
            SecurityEvent::new(SecurityEventType::AuthSuccess)
                .with_detail("token_type", format!("{:?}", auth_token.token_type))
                .with_severity(ErrorSeverity::Info),
        );

        Ok(auth_token)
    }

    /// Register a token
    pub fn register_token(
        &self,
        token: AuthToken
    ) {
        self.tokens.insert(token.value.clone(), token);
    }

    /// Revoke a token
    pub fn revoke_token(
        &self,
        token: &str
    ) {
        self.tokens.remove(token);
    }

    // Layer 2: Authorization

    /// Check authorization
    #[instrument(skip(self, context))]
    pub fn authorize(
        &self,
        context: &SecurityContext,
        required_permission: Permission,
    ) -> CoreResult<()> {
        self.log_event(
            SecurityEvent::new(SecurityEventType::AuthzCheck)
                .with_user_id(context.user_id.clone().unwrap_or_default())
                .with_detail("permission", format!("{:?}", required_permission))
                .with_severity(ErrorSeverity::Info),
        );

        if !context.has_permission(&required_permission) {
            self.log_event(
                SecurityEvent::new(SecurityEventType::AuthzDenied)
                    .with_user_id(context.user_id.clone().unwrap_or_default())
                    .with_detail("permission", format!("{:?}", required_permission))
                    .with_severity(ErrorSeverity::Warning),
            );

            return Err(CoreError::SecurityError(SecurityError::PermissionDenied {
                permission: format!("{:?}", required_permission),
            }));
        }

        Ok(())
    }

    // Layer 3: Input Validation

    /// Validate input
    pub fn validate_input(
        &self,
        input: &str
    ) -> CoreResult<()> {
        if input.len() > self.config.content_policy.max_input_length {
            return Err(CoreError::ValidationError {
                message: format!(
                    "Input exceeds maximum length of {}",
                    self.config.content_policy.max_input_length
                ),
                field: Some("input".to_string()),
            });
        }

        // Check blocked patterns
        for pattern in &self.config.content_policy.blocked_patterns {
            if input.contains(pattern) {
                return Err(CoreError::ValidationError {
                    message: "Input contains blocked content".to_string(),
                    field: Some("input".to_string()),
                });
            }
        }

        Ok(())
    }

    // Layer 4: Rate Limiting

    /// Check rate limit
    #[instrument(skip(self))]
    pub fn check_rate_limit(
        &self,
        key: &str,
        resource: &str,
    ) -> CoreResult<()> {
        if !self.config.rate_limit.enabled {
            return Ok(());
        }

        let limit = self
            .config
            .rate_limit
            .endpoints
            .get(resource)
            .copied()
            .unwrap_or(self.config.rate_limit.default);

        let entry = self
            .rate_limiters
            .entry(key.to_string())
            .or_insert_with(|| Arc::new(RateLimitEntry::new()))
            .clone();

        if entry.is_blocked() {
            self.log_event(
                SecurityEvent::new(SecurityEventType::RateLimitTriggered)
                    .with_detail("key", key)
                    .with_detail("resource", resource)
                    .with_severity(ErrorSeverity::Warning),
            );

            return Err(CoreError::SecurityError(SecurityError::RateLimitExceeded {
                resource: resource.to_string(),
                limit: limit.max_requests,
                window_secs: limit.window_secs,
            }));
        }

        entry.record_request(&limit);

        if !entry.check_limit(&limit) {
            entry.block(Duration::from_secs(limit.window_secs));

            self.log_event(
                SecurityEvent::new(SecurityEventType::RateLimitTriggered)
                    .with_detail("key", key)
                    .with_detail("resource", resource)
                    .with_severity(ErrorSeverity::Warning),
            );

            return Err(CoreError::SecurityError(SecurityError::RateLimitExceeded {
                resource: resource.to_string(),
                limit: limit.max_requests,
                window_secs: limit.window_secs,
            }));
        }

        Ok(())
    }

    // Layer 5: Content Policy

    /// Check content against policy
    pub fn check_content(
        &self,
        content: &str,
    ) -> CoreResult<()> {
        if !self.config.content_policy.enabled {
            return Ok(());
        }

        // Check for blocked patterns
        for pattern in &self.config.content_policy.blocked_patterns {
            if content.contains(pattern) {
                self.log_event(
                    SecurityEvent::new(SecurityEventType::ContentViolation)
                        .with_detail("type", "blocked_pattern")
                        .with_detail("pattern", pattern)
                        .with_severity(ErrorSeverity::Error),
                );

                return Err(CoreError::SecurityError(
                    SecurityError::ContentPolicyViolation {
                        policy: "content_filter".to_string(),
                        details: "Content contains blocked patterns".to_string(),
                    },
                ));
            }
        }

        Ok(())
    }

    // Layer 6: Audit Logging

    /// Log a security event
    pub fn log_event(
        &self,
        event: SecurityEvent,
    ) {
        self.event_count.fetch_add(1, Ordering::Relaxed);

        if self.config.audit.enabled {
            let mut log = self.audit_log.write();
            log.push(event);

            // Trim log if too large
            if log.len() > 10000 {
                log.drain(0..1000);
            }
        }
    }

    /// Get audit log
    pub fn get_audit_log(&self
    ) -> Vec<SecurityEvent> {
        self.audit_log.read().clone()
    }

    /// Get event count
    pub fn event_count(&self
    ) -> u64 {
        self.event_count.load(Ordering::Relaxed)
    }

    /// Detect suspicious activity
    pub fn detect_suspicious_activity(
        &self,
        context: &SecurityContext,
    ) -> Option<SecurityEvent> {
        let mut risk_score = 0u8;
        let key = context.user_id.clone().unwrap_or_else(|| {
            context.client_ip.map(|ip| ip.to_string()).unwrap_or_default()
        });

        // Check failed attempts
        if let Some((attempts, _)) = self.failed_attempts.get(&key) {
            if *attempts >= self.config.auth.max_failed_attempts {
                risk_score += 50;
            }
        }

        // Check rate limit violations
        if let Some(entry) = self.rate_limiters.get(&key) {
            let requests = entry.requests.read();
            if requests.len() > 100 {
                risk_score += 30;
            }
        }

        if risk_score >= self.config.suspicious_threshold {
            let event = SecurityEvent::new(SecurityEventType::SuspiciousActivity)
                .with_user_id(context.user_id.clone().unwrap_or_default())
                .with_detail("risk_score", risk_score.to_string())
                .with_detail("key", key.clone())
                .with_severity(ErrorSeverity::Warning);

            let mut activity = self.suspicious_activity.entry(key).or_default();
            activity.push(event.clone());

            return Some(event);
        }

        None
    }

    /// Record failed authentication
    pub fn record_failed_auth(&self,
        key: &str
    ) {
        let mut entry = self.failed_attempts.entry(key.to_string()).or_insert((0, Instant::now()));
        entry.0 += 1;
        entry.1 = Instant::now();
    }

    /// Create security context from token
    pub fn create_context(
        &self,
        token: &AuthToken,
    ) -> SecurityContext {
        let mut context = SecurityContext::new()
            .with_permissions([
                Permission::ReadOwn,
                Permission::WriteOwn,
                Permission::DeleteOwn,
                Permission::UseTools,
            ].into_iter().collect());

        context.token = Some(token.clone());
        context
    }
}

impl fmt::Debug for SecurityEngine {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("SecurityEngine")
            .field("config", &self.config)
            .field("active_tokens", &self.tokens.len())
            .field("rate_limiters", &self.rate_limiters.len())
            .field("event_count", &self.event_count())
            .finish()
    }
}

use std::fmt;

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_authentication() {
        let engine = SecurityEngine::new(SecurityConfig::default()).await.unwrap();

        let token = AuthToken {
            token_type: TokenType::Bearer,
            value: "test_token".to_string(),
            expires_at: Some(Timestamp::from_millis(u64::MAX)),
            issued_at: Timestamp::now(),
            issuer: "test".to_string(),
        };

        engine.register_token(token.clone());

        let result = engine.authenticate("test_token");
        assert!(result.is_ok());

        let result = engine.authenticate("invalid_token");
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_authorization() {
        let engine = SecurityEngine::new(SecurityConfig::default()).await.unwrap();

        let mut permissions = HashSet::new();
        permissions.insert(Permission::ReadOwn);

        let context = SecurityContext::new().with_permissions(permissions);

        assert!(engine.authorize(&context, Permission::ReadOwn).is_ok());
        assert!(engine.authorize(&context, Permission::WriteAny).is_err());
    }

    #[tokio::test]
    async fn test_rate_limiting() {
        let config = SecurityConfig {
            rate_limit: RateLimitConfig {
                enabled: true,
                default: RateLimit::new(2, 60),
                endpoints: HashMap::new(),
                ip_based: true,
                user_based: true,
                burst_size: 0,
            },
            ..Default::default()
        };
        let engine = SecurityEngine::new(config).await.unwrap();

        assert!(engine.check_rate_limit("user1", "api").is_ok());
        assert!(engine.check_rate_limit("user1", "api").is_ok());
        assert!(engine.check_rate_limit("user1", "api").is_err());
    }

    #[tokio::test]
    async fn test_input_validation() {
        let engine = SecurityEngine::new(SecurityConfig::default()).await.unwrap();

        assert!(engine.validate_input("valid input").is_ok());

        let long_input = "a".repeat(200_000);
        assert!(engine.validate_input(&long_input).is_err());
    }

    #[tokio::test]
    async fn test_audit_logging() {
        let engine = SecurityEngine::new(SecurityConfig::default()).await.unwrap();

        let event = SecurityEvent::new(SecurityEventType::AuthAttempt)
            .with_user_id("user123")
            .with_detail("ip", "192.168.1.1");

        engine.log_event(event);

        assert_eq!(engine.event_count(), 1);
    }

    #[test]
    fn test_security_context() {
        let context = SecurityContext::new()
            .with_user_id("test_user")
            .with_permissions([Permission::ReadOwn, Permission::WriteOwn].into_iter().collect());

        assert!(context.is_authenticated());
        assert!(context.has_permission(&Permission::ReadOwn));
        assert!(!context.has_permission(&Permission::Admin));
    }
}
