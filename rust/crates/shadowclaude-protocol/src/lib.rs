//! ShadowClaude Protocol - WebSocket and MCP implementation
//!
//! This crate provides:
//! - WebSocket client/server
//! - MCP (Model Context Protocol) client
//! - Message serialization
//! - Streaming support

#![warn(missing_docs)]
#![warn(rust_2018_idioms)]

pub mod error;
pub mod extra;
pub mod mcp;
pub mod message;
pub mod serde;
pub mod testing;
pub mod websocket;

pub use error::{ProtocolError, ProtocolResult};
pub use mcp::{McpClient, McpConfig, McpMessage, McpMethod};
pub use message::{MessageFrame, MessageType, ProtocolMessage};
pub use websocket::{WebSocketClient, WebSocketConfig, WebSocketServer};

/// Protocol version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Protocol capabilities
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Capabilities {
    /// WebSocket support
    pub websocket: bool,
    /// MCP support
    pub mcp: bool,
    /// Binary messages
    pub binary_messages: bool,
    /// Compression
    pub compression: bool,
}

impl Capabilities {
    /// Full capabilities
    pub const fn full() -> Self {
        Self {
            websocket: true,
            mcp: true,
            binary_messages: true,
            compression: true,
        }
    }
}

impl Default for Capabilities {
    fn default() -> Self {
        Self::full()
    }
}

/// Initialize the protocol module
pub fn init() {
    tracing::info!("ShadowClaude Protocol v{} initialized", VERSION);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert!(!VERSION.is_empty());
    }

    #[test]
    fn test_capabilities() {
        let caps = Capabilities::full();
        assert!(caps.websocket);
        assert!(caps.mcp);
    }
}
