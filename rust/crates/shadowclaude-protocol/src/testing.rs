//! Protocol testing utilities
//!
//! Mock servers and test helpers for protocol testing

use crate::{
    McpClient, McpConfig, McpMessage, McpMethod, McpResponse, ProtocolError, ProtocolMessage,
    WebSocketClient, WebSocketConfig, WebSocketServer,
};
use std::collections::VecDeque;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex, RwLock};
use tracing::{debug, info};

/// Mock MCP server for testing
pub struct MockMcpServer {
    /// Expected requests
    expected: Arc<Mutex<VecDeque<McpMessage>>>,
    /// Responses to return
    responses: Arc<Mutex<VecDeque<McpResponse>>>,
    /// Received requests
    received: Arc<Mutex<Vec<McpMessage>>>,
    /// Server address
    addr: SocketAddr,
}

impl MockMcpServer {
    /// Create a new mock server
    pub async fn new() -> std::io::Result<Self> {
        let addr = "127.0.0.1:0".parse().unwrap();
        
        Ok(Self {
            expected: Arc::new(Mutex::new(VecDeque::new())),
            responses: Arc::new(Mutex::new(VecDeque::new())),
            received: Arc::new(Mutex::new(Vec::new())),
            addr,
        })
    }

    /// Expect a request
    pub async fn expect(&self,
        request: McpMessage
    ) {
        self.expected.lock().await.push_back(request);
    }

    /// Queue a response
    pub async fn respond_with(&self,
        response: McpResponse
    ) {
        self.responses.lock().await.push_back(response);
    }

    /// Get received requests
    pub async fn received(&self
    ) -> Vec<McpMessage> {
        self.received.lock().await.clone()
    }

    /// Verify all expected requests received
    pub async fn verify(&self
    ) -> bool {
        self.expected.lock().await.is_empty()
    }

    /// Get server address
    pub fn addr(&self
    ) -> SocketAddr {
        self.addr
    }

    /// Start the mock server
    pub async fn start(&self
    ) -> std::io::Result<()> {
        // Start HTTP server
        Ok(())
    }

    /// Stop the mock server
    pub async fn stop(&self
    ) {
        // Stop server
    }
}

/// Mock WebSocket server for testing
pub struct MockWebSocketServer {
    received_messages: Arc<Mutex<Vec<String>>>,
    responses: Arc<Mutex<VecDeque<String>>>,
    addr: Option<SocketAddr>,
    server: Option<WebSocketServer>,
}

impl MockWebSocketServer {
    /// Create new mock WebSocket server
    pub fn new() -> Self {
        Self {
            received_messages: Arc::new(Mutex::new(Vec::new())),
            responses: Arc::new(Mutex::new(VecDeque::new())),
            addr: None,
            server: None,
        }
    }

    /// Start the server
    pub async fn start(&mut self
    ) -> std::io::Result<SocketAddr> {
        let addr = "127.0.0.1:0".parse().unwrap();
        let config = WebSocketConfig::default();
        let server = WebSocketServer::new(addr, config);

        let actual_addr = addr; // Server would provide actual address
        self.addr = Some(actual_addr);
        self.server = Some(server);

        Ok(actual_addr)
    }

    /// Stop the server
    pub async fn stop(&mut self
    ) {
        if let Some(server) = self.server.take() {
            server.stop().await;
        }
    }

    /// Queue a response message
    pub async fn queue_response(
        &self,
        message: impl Into<String>
    ) {
        self.responses.lock().await.push_back(message.into());
    }

    /// Get received messages
    pub async fn received(&self
    ) -> Vec<String> {
        self.received_messages.lock().await.clone()
    }

    /// Wait for a message
    pub async fn wait_for_message(
        &self,
        timeout_ms: u64
    ) -> Option<String> {
        tokio::time::timeout(
            tokio::time::Duration::from_millis(timeout_ms),
            async {
                loop {
                    let msgs = self.received_messages.lock().await;
                    if !msgs.is_empty() {
                        return msgs.last().cloned();
                    }
                    drop(msgs);
                    tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
                }
            }
        ).await.ok().flatten()
    }
}

/// Protocol test harness
pub struct ProtocolTestHarness {
    /// MCP mock server
    pub mcp_server: Option<MockMcpServer>,
    /// WebSocket mock server
    pub ws_server: Option<MockWebSocketServer>,
}

impl ProtocolTestHarness {
    /// Create new test harness
    pub fn new() -> Self {
        Self {
            mcp_server: None,
            ws_server: None,
        }
    }

    /// Setup MCP mock
    pub async fn with_mcp(mut self
    ) -> std::io::Result<Self> {
        self.mcp_server = Some(MockMcpServer::new().await?);
        Ok(self)
    }

    /// Setup WebSocket mock
    pub async fn with_websocket(mut self
    ) -> std::io::Result<Self> {
        self.ws_server = Some(MockWebSocketServer::new());
        Ok(self)
    }

    /// Start all servers
    pub async fn start(&mut self
    ) -> std::io::Result<()> {
        if let Some(ref server) = self.mcp_server {
            server.start().await?;
        }
        if let Some(ref mut server) = self.ws_server {
            server.start().await?;
        }
        Ok(())
    }

    /// Stop all servers
    pub async fn stop(&mut self
    ) {
        if let Some(server) = self.mcp_server.take() {
            server.stop().await;
        }
        if let Some(mut server) = self.ws_server.take() {
            server.stop().await;
        }
    }

    /// Get MCP client configured for mock server
    pub async fn mcp_client(&self
    ) -> Option<McpClient> {
        self.mcp_server.as_ref().map(|server| {
            let config = McpConfig {
                endpoint: format!("http://{}", server.addr()),
                ..Default::default()
            };
            McpClient::new(config).expect("Failed to create client")
        })
    }

    /// Get WebSocket client configured for mock server
    pub async fn ws_client(&self
    ) -> Option<WebSocketClient> {
        self.ws_server.as_ref().and_then(|server| {
            server.addr.map(|addr| {
                let config = WebSocketConfig::default();
                WebSocketClient::new(format!("ws://{}", addr), config)
            })
        })
    }
}

impl Default for ProtocolTestHarness {
    fn default() -> Self {
        Self::new()
    }
}

/// Assert that message matches pattern
#[macro_export]
macro_rules! assert_message_matches {
    ($msg:expr, $pattern:expr) => {
        let msg_str = serde_json::to_string($msg).unwrap();
        assert!(
            msg_str.contains($pattern),
            "Message '{}' does not contain '{}'",
            msg_str,
            $pattern
        );
    };
}

/// Test utilities
pub mod test_utils {
    use super::*;

    /// Create test message
    pub fn create_test_message(method: &str
    ) -> ProtocolMessage {
        ProtocolMessage::request(method, serde_json::json!({"test": true})).unwrap()
    }

    /// Create test MCP message
    pub fn create_test_mcp_message(method: McpMethod
    ) -> McpMessage {
        McpMessage::new(method)
    }

    /// Wait for condition with timeout
    pub async fn wait_for<F, Fut>(
        condition: F,
        timeout_ms: u64
    ) -> bool
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = bool>,
    {
        tokio::time::timeout(
            tokio::time::Duration::from_millis(timeout_ms),
            async {
                while !condition().await {
                    tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
                }
                true
            }
        ).await.unwrap_or(false)
    }

    /// Generate random port
    pub fn random_port() -> u16 {
        10000 + (std::process::id() % 50000) as u16
    }

    /// Create local address
    pub fn local_addr(port: u16
    ) -> SocketAddr {
        format!("127.0.0.1:{}", port).parse().unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::test_utils::*;

    #[test]
    fn test_create_test_message() {
        let msg = create_test_message("test");
        assert_eq!(msg.method, Some("test".to_string()));
    }

    #[test]
    fn test_create_test_mcp_message() {
        let msg = create_test_mcp_message(McpMethod::Health);
        assert_eq!(msg.method, McpMethod::Health);
    }

    #[test]
    fn test_local_addr() {
        let addr = local_addr(8080);
        assert_eq!(addr.port(), 8080);
    }

    #[tokio::test]
    async fn test_wait_for() {
        let counter = Arc::new(Mutex::new(0));
        let counter_clone = counter.clone();

        tokio::spawn(async move {
            tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
            *counter_clone.lock().await = 1;
        });

        let result = wait_for(|| async {
            *counter.lock().await == 1
        }, 1000).await;

        assert!(result);
    }
}
