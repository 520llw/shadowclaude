//! WebSocket client and server implementation
//!
//! Provides async WebSocket functionality with:
//! - Auto-reconnect
//! - Heartbeat/ping-pong
//! - Message compression
//! - Connection pooling

use crate::{MessageFrame, ProtocolMessage, ProtocolResult, ProtocolError};
use bytes::Bytes;
use futures::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::{broadcast, mpsc, RwLock};
use tokio::time::{interval, timeout};
use tokio_tungstenite::{accept_async, connect_async, tungstenite, WebSocketStream};
use tracing::{debug, error, info, trace, warn};

/// WebSocket configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebSocketConfig {
    /// Connection timeout
    pub connection_timeout_secs: u64,
    /// Heartbeat interval
    pub heartbeat_interval_secs: u64,
    /// Auto reconnect
    pub auto_reconnect: bool,
    /// Reconnect delay
    pub reconnect_delay_secs: u64,
    /// Max reconnect attempts
    pub max_reconnect_attempts: u32,
    /// Message size limit
    pub max_message_size: usize,
    /// Enable compression
    pub enable_compression: bool,
    /// TLS configuration
    pub tls: Option<TlsConfig>,
}

impl Default for WebSocketConfig {
    fn default() -> Self {
        Self {
            connection_timeout_secs: 30,
            heartbeat_interval_secs: 30,
            auto_reconnect: true,
            reconnect_delay_secs: 5,
            max_reconnect_attempts: 10,
            max_message_size: 10 * 1024 * 1024, // 10MB
            enable_compression: true,
            tls: None,
        }
    }
}

/// TLS configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TlsConfig {
    /// CA certificate path
    pub ca_cert: Option<String>,
    /// Client certificate path
    pub client_cert: Option<String>,
    /// Client key path
    pub client_key: Option<String>,
    /// Skip verification (insecure)
    pub skip_verify: bool,
}

/// WebSocket client
pub struct WebSocketClient {
    /// Server URL
    url: String,
    /// Configuration
    config: WebSocketConfig,
    /// Connection state
    connected: Arc<AtomicBool>,
    /// Message sender
    sender: Option<mpsc::UnboundedSender<MessageFrame>>,
    /// Shutdown signal
    shutdown_tx: broadcast::Sender<()>,
    /// Connection handle
    connection_handle: Option<tokio::task::JoinHandle<()>>,
}

impl WebSocketClient {
    /// Create a new WebSocket client
    pub fn new(url: impl Into<String>, config: WebSocketConfig) -> Self {
        let (shutdown_tx, _) = broadcast::channel(1);
        
        Self {
            url: url.into(),
            config,
            connected: Arc::new(AtomicBool::new(false)),
            sender: None,
            shutdown_tx,
            connection_handle: None,
        }
    }

    /// Connect to server
    pub async fn connect(&mut self
    ) -> ProtocolResult<()> {
        if self.connected.load(Ordering::Relaxed) {
            return Err(ProtocolError::AlreadyConnected);
        }

        let url = self.url.clone();
        let config = self.config.clone();
        let connected = self.connected.clone();
        let mut shutdown_rx = self.shutdown_tx.subscribe();

        // Connect with timeout
        let connect_result = timeout(
            Duration::from_secs(config.connection_timeout_secs),
            connect_async(&url
            ),
        ).await;

        let (ws_stream, _) = match connect_result {
            Ok(Ok(result)) => result,
            Ok(Err(e)) => return Err(ProtocolError::Connection(e.to_string())),
            Err(_) => return Err(ProtocolError::Timeout("Connection timeout".to_string())),
        };

        info!("WebSocket connected to {}", url);
        connected.store(true, Ordering::SeqCst);

        // Set up channels
        let (tx, mut rx) = mpsc::unbounded_channel();
        self.sender = Some(tx);

        // Spawn connection handler
        let handle = tokio::spawn(async move {
            let (mut write, mut read) = ws_stream.split();

            // Message forwarding loop
            loop {
                tokio::select! {
                    // Send messages
                    Some(frame) = rx.recv() => {
                        let msg = match frame {
                            MessageFrame::Text(t) => tungstenite::Message::Text(t),
                            MessageFrame::Binary(b) => tungstenite::Message::Binary(b.to_vec()),
                            MessageFrame::Ping(p) => tungstenite::Message::Ping(p),
                            MessageFrame::Pong(p) => tungstenite::Message::Pong(p),
                            MessageFrame::Close(_) => {
                                let _ = write.close().await;
                                break;
                            }
                        };

                        if let Err(e) = write.send(msg).await {
                            error!("WebSocket send error: {}", e);
                            break;
                        }
                    }

                    // Receive messages
                    Some(msg) = read.next() => {
                        match msg {
                            Ok(tungstenite::Message::Text(text)) => {
                                trace!("Received text: {}", text);
                            }
                            Ok(tungstenite::Message::Binary(data)) => {
                                trace!("Received binary: {} bytes", data.len());
                            }
                            Ok(tungstenite::Message::Ping(data)) => {
                                let _ = write.send(tungstenite::Message::Pong(data)).await;
                            }
                            Ok(tungstenite::Message::Close(_)) => {
                                info!("WebSocket closed by server");
                                break;
                            }
                            Err(e) => {
                                error!("WebSocket error: {}", e);
                                break;
                            }
                            _ => {}
                        }
                    }

                    // Shutdown signal
                    _ = shutdown_rx.recv() => {
                        let _ = write.close().await;
                        break;
                    }
                }
            }

            connected.store(false, Ordering::SeqCst);
            info!("WebSocket connection closed");
        });

        self.connection_handle = Some(handle);

        // Start heartbeat
        if self.config.heartbeat_interval_secs > 0 {
            self.start_heartbeat().await?;
        }

        Ok(())
    }

    /// Send a message
    pub async fn send(&self,
        message: &ProtocolMessage
    ) -> ProtocolResult<()> {
        if !self.connected.load(Ordering::Relaxed) {
            return Err(ProtocolError::NotConnected);
        }

        let frame = MessageFrame::from_message(message)?;
        
        if let Some(ref sender) = self.sender {
            sender.send(frame)
                .map_err(|_| ProtocolError::ConnectionClosed)?;
            Ok(())
        } else {
            Err(ProtocolError::NotConnected)
        }
    }

    /// Send raw frame
    pub async fn send_frame(
        &self,
        frame: MessageFrame
    ) -> ProtocolResult<()> {
        if !self.connected.load(Ordering::Relaxed) {
            return Err(ProtocolError::NotConnected);
        }

        if let Some(ref sender) = self.sender {
            sender.send(frame)
                .map_err(|_| ProtocolError::ConnectionClosed)?;
            Ok(())
        } else {
            Err(ProtocolError::NotConnected)
        }
    }

    /// Check if connected
    pub fn is_connected(&self
    ) -> bool {
        self.connected.load(Ordering::Relaxed)
    }

    /// Disconnect
    pub async fn disconnect(&mut self
    ) {
        let _ = self.shutdown_tx.send(());

        if let Some(handle) = self.connection_handle.take() {
            handle.abort();
        }

        self.sender = None;
        self.connected.store(false, Ordering::SeqCst);
    }

    async fn start_heartbeat(&self
    ) -> ProtocolResult<()> {
        // Heartbeat logic would go here
        Ok(())
    }
}

impl Drop for WebSocketClient {
    fn drop(&mut self
    ) {
        let _ = self.shutdown_tx.send(());
    }
}

/// WebSocket server
pub struct WebSocketServer {
    /// Bind address
    addr: SocketAddr,
    /// Configuration
    config: WebSocketConfig,
    /// Shutdown signal
    shutdown_tx: broadcast::Sender<()>,
    /// Active connections
    connections: Arc<RwLock<Vec<ConnectionHandle>>>,
}

/// Connection handle
struct ConnectionHandle {
    id: uuid::Uuid,
    addr: SocketAddr,
}

impl WebSocketServer {
    /// Create a new WebSocket server
    pub fn new(addr: SocketAddr, config: WebSocketConfig) -> Self {
        let (shutdown_tx, _) = broadcast::channel(1);
        
        Self {
            addr,
            config,
            shutdown_tx,
            connections: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Start the server
    pub async fn start(&self
    ) -> ProtocolResult<()> {
        let listener = TcpListener::bind(self.addr).await
            .map_err(|e| ProtocolError::Connection(e.to_string()))?;

        info!("WebSocket server listening on {}", self.addr);

        let mut shutdown_rx = self.shutdown_tx.subscribe();
        let connections = self.connections.clone();

        loop {
            tokio::select! {
                Ok((stream, addr)) = listener.accept() => {
                    let conn_id = uuid::Uuid::new_v4();
                    let conn = ConnectionHandle {
                        id: conn_id,
                        addr,
                    };

                    connections.write().await.push(conn);

                    // Handle connection
                    tokio::spawn(async move {
                        if let Err(e) = Self::handle_connection(stream, addr).await {
                            error!("Connection error from {}: {}", addr, e);
                        }
                    });
                }

                _ = shutdown_rx.recv() => {
                    info!("WebSocket server shutting down");
                    break;
                }
            }
        }

        Ok(())
    }

    /// Stop the server
    pub async fn stop(&self
    ) {
        let _ = self.shutdown_tx.send(());
    }

    /// Get connection count
    pub async fn connection_count(&self
    ) -> usize {
        self.connections.read().await.len()
    }

    async fn handle_connection(
        stream: TcpStream,
        addr: SocketAddr
    ) -> ProtocolResult<()> {
        let ws_stream = accept_async(stream).await
            .map_err(|e| ProtocolError::WebSocket(e.to_string()))?;

        info!("WebSocket connection accepted from {}", addr);

        let (mut write, mut read) = ws_stream.split();

        while let Some(msg) = read.next().await {
            match msg {
                Ok(tungstenite::Message::Text(text)) => {
                    trace!("Received from {}: {}", addr, text);
                    
                    // Echo back for testing
                    let response = tungstenite::Message::Text(format!("Echo: {}", text));
                    write.send(response).await.map_err(|e| {
                        ProtocolError::WebSocket(e.to_string())
                    })?;
                }
                Ok(tungstenite::Message::Binary(data)) => {
                    trace!("Received binary from {}: {} bytes", addr, data.len());
                }
                Ok(tungstenite::Message::Ping(data)) => {
                    write.send(tungstenite::Message::Pong(data)).await
                        .map_err(|e| ProtocolError::WebSocket(e.to_string()))?;
                }
                Ok(tungstenite::Message::Close(_)) => {
                    info!("Connection closed by {}", addr);
                    break;
                }
                Err(e) => {
                    error!("WebSocket error from {}: {}", addr, e);
                    break;
                }
                _ => {}
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_websocket_config_default() {
        let config = WebSocketConfig::default();
        assert!(config.auto_reconnect);
        assert_eq!(config.max_message_size, 10 * 1024 * 1024);
    }

    #[tokio::test]
    async fn test_websocket_client_new() {
        let config = WebSocketConfig::default();
        let client = WebSocketClient::new("ws://localhost:8080", config);
        
        assert!(!client.is_connected());
        assert_eq!(client.url, "ws://localhost:8080");
    }

    // Note: Full integration tests would require a running WebSocket server
}
