//! Protocol error types
//!
//! Comprehensive error handling for protocol operations

use std::fmt;
use std::io;

/// Protocol result type
pub type ProtocolResult<T> = Result<T, ProtocolError>;

/// Protocol error types
#[derive(Debug)]
pub enum ProtocolError {
    /// WebSocket error
    WebSocket(String),
    /// MCP error
    Mcp(String),
    /// Serialization error
    Serialization(String),
    /// Deserialization error
    Deserialization(String),
    /// Connection error
    Connection(String),
    /// IO error
    Io(io::Error),
    /// Timeout error
    Timeout(String),
    /// Protocol violation
    Protocol(String),
    /// Authentication error
    Authentication(String),
    /// Not connected
    NotConnected,
    /// Already connected
    AlreadyConnected,
    /// Connection closed
    ConnectionClosed,
    /// Invalid state
    InvalidState(String),
    /// Message too large
    MessageTooLarge {
        /// Actual size
        size: usize,
        /// Maximum allowed
        max: usize,
    },
    /// Rate limited
    RateLimited {
        /// Retry after seconds
        retry_after: u64,
    },
    /// Compression error
    Compression(String),
    /// Custom error
    Custom(String),
}

impl fmt::Display for ProtocolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ProtocolError::WebSocket(s) => write!(f, "WebSocket error: {}", s),
            ProtocolError::Mcp(s) => write!(f, "MCP error: {}", s),
            ProtocolError::Serialization(s) => write!(f, "Serialization error: {}", s),
            ProtocolError::Deserialization(s) => write!(f, "Deserialization error: {}", s),
            ProtocolError::Connection(s) => write!(f, "Connection error: {}", s),
            ProtocolError::Io(e) => write!(f, "IO error: {}", e),
            ProtocolError::Timeout(s) => write!(f, "Timeout: {}", s),
            ProtocolError::Protocol(s) => write!(f, "Protocol error: {}", s),
            ProtocolError::Authentication(s) => write!(f, "Authentication error: {}", s),
            ProtocolError::NotConnected => write!(f, "Not connected"),
            ProtocolError::AlreadyConnected => write!(f, "Already connected"),
            ProtocolError::ConnectionClosed => write!(f, "Connection closed"),
            ProtocolError::InvalidState(s) => write!(f, "Invalid state: {}", s),
            ProtocolError::MessageTooLarge { size, max } => write!(f, "Message too large: {} > {}", size, max),
            ProtocolError::RateLimited { retry_after } => write!(f, "Rate limited, retry after {}s", retry_after),
            ProtocolError::Compression(s) => write!(f, "Compression error: {}", s),
            ProtocolError::Custom(s) => write!(f, "{}", s),
        }
    }
}

impl std::error::Error for ProtocolError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            ProtocolError::Io(e) => Some(e),
            _ => None,
        }
    }
}

impl From<io::Error> for ProtocolError {
    fn from(err: io::Error) -> Self {
        ProtocolError::Io(err)
    }
}

impl From<serde_json::Error> for ProtocolError {
    fn from(err: serde_json::Error) -> Self {
        if err.is_io() {
            ProtocolError::Io(err.into())
        } else {
            ProtocolError::Serialization(err.to_string())
        }
    }
}

impl From<tungstenite::Error> for ProtocolError {
    fn from(err: tungstenite::Error) -> Self {
        ProtocolError::WebSocket(err.to_string())
    }
}

impl From<tokio_tungstenite::tungstenite::Error> for ProtocolError {
    fn from(err: tokio_tungstenite::tungstenite::Error) -> Self {
        ProtocolError::WebSocket(err.to_string())
    }
}

impl ProtocolError {
    /// Check if error is retryable
    pub fn is_retryable(&self
    ) -> bool {
        matches!(
            self,
            ProtocolError::Connection(_)
                | ProtocolError::Timeout(_)
                | ProtocolError::NotConnected
                | ProtocolError::ConnectionClosed
                | ProtocolError::RateLimited { .. }
        )
    }

    /// Check if error is fatal
    pub fn is_fatal(&self
    ) -> bool {
        matches!(
            self,
            ProtocolError::Protocol(_)
                | ProtocolError::Authentication(_)
                | ProtocolError::InvalidState(_)
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = ProtocolError::NotConnected;
        assert_eq!(err.to_string(), "Not connected");

        let err = ProtocolError::MessageTooLarge { size: 100, max: 50 };
        assert!(err.to_string().contains("100"));
    }

    #[test]
    fn test_error_retryable() {
        assert!(ProtocolError::Timeout("test".to_string()).is_retryable());
        assert!(!ProtocolError::Protocol("test".to_string()).is_retryable());
    }

    #[test]
    fn test_error_fatal() {
        assert!(ProtocolError::Protocol("test".to_string()).is_fatal());
        assert!(!ProtocolError::ConnectionClosed.is_fatal());
    }
}
