//! MCP (Model Context Protocol) client implementation
//!
//! MCP is a protocol for communicating with AI models and services

use crate::{MessageFrame, ProtocolError, ProtocolMessage, ProtocolResult};
use bytes::Bytes;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{mpsc, RwLock};
use tracing::{debug, error, info, trace, warn};
use uuid::Uuid;

/// MCP configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpConfig {
    /// Server endpoint
    pub endpoint: String,
    /// API key
    pub api_key: Option<String>,
    /// Request timeout
    pub request_timeout_secs: u64,
    /// Max retries
    pub max_retries: u32,
    /// Custom headers
    pub headers: HashMap<String, String>,
}

impl Default for McpConfig {
    fn default() -> Self {
        Self {
            endpoint: "http://localhost:8080".to_string(),
            api_key: None,
            request_timeout_secs: 60,
            max_retries: 3,
            headers: HashMap::new(),
        }
    }
}

/// MCP methods
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum McpMethod {
    /// Initialize connection
    Initialize,
    /// Complete/predict
    Complete,
    /// Chat completion
    Chat,
    /// Stream completion
    Stream,
    /// Get model info
    ModelInfo,
    /// List models
    ListModels,
    /// Health check
    Health,
    /// Get embeddings
    Embeddings,
}

impl std::fmt::Display for McpMethod {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            McpMethod::Initialize => write!(f, "initialize"),
            McpMethod::Complete => write!(f, "complete"),
            McpMethod::Chat => write!(f, "chat"),
            McpMethod::Stream => write!(f, "stream"),
            McpMethod::ModelInfo => write!(f, "model_info"),
            McpMethod::ListModels => write!(f, "list_models"),
            McpMethod::Health => write!(f, "health"),
            McpMethod::Embeddings => write!(f, "embeddings"),
        }
    }
}

/// MCP message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpMessage {
    /// Message ID
    pub id: Uuid,
    /// Method
    pub method: McpMethod,
    /// Parameters
    pub params: serde_json::Value,
    /// Context
    #[serde(skip_serializing_if = "Option::is_none")]
    pub context: Option<serde_json::Value>,
}

impl McpMessage {
    /// Create a new MCP message
    pub fn new(method: McpMethod) -> Self {
        Self {
            id: Uuid::new_v4(),
            method,
            params: serde_json::Value::Null,
            context: None,
        }
    }

    /// Set parameters
    pub fn with_params(mut self, params: impl Serialize) -> ProtocolResult<Self> {
        self.params = serde_json::to_value(params)
            .map_err(|e| ProtocolError::Serialization(e.to_string()))?;
        Ok(self)
    }

    /// Set context
    pub fn with_context(mut self, context: impl Serialize) -> ProtocolResult<Self> {
        self.context = Some(
            serde_json::to_value(context)
                .map_err(|e| ProtocolError::Serialization(e.to_string()))?
        );
        Ok(self)
    }

    /// Convert to protocol message
    pub fn to_protocol(self) -> ProtocolResult<ProtocolMessage> {
        ProtocolMessage::request(self.method.to_string(), self)
    }
}

/// MCP response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpResponse {
    /// Response ID (matches request)
    pub id: Uuid,
    /// Result
    pub result: serde_json::Value,
    /// Usage statistics
    #[serde(skip_serializing_if = "Option::is_none")]
    pub usage: Option<Usage>,
    /// Model used
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
}

/// Usage statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Usage {
    /// Prompt tokens
    pub prompt_tokens: usize,
    /// Completion tokens
    pub completion_tokens: usize,
    /// Total tokens
    pub total_tokens: usize,
}

/// MCP client
pub struct McpClient {
    /// Configuration
    config: McpConfig,
    /// HTTP client
    client: reqwest::Client,
    /// Connected state
    connected: Arc<RwLock<bool>>,
}

impl McpClient {
    /// Create a new MCP client
    pub fn new(config: McpConfig) -> ProtocolResult<Self> {
        let client = reqwest::Client::builder()
            .timeout(tokio::time::Duration::from_secs(config.request_timeout_secs))
            .build()
            .map_err(|e| ProtocolError::Connection(e.to_string()))?;

        Ok(Self {
            config,
            client,
            connected: Arc::new(RwLock::new(false)),
        })
    }

    /// Initialize connection
    pub async fn initialize(&self
    ) -> ProtocolResult<McpResponse> {
        let msg = McpMessage::new(McpMethod::Initialize);
        self.send(msg).await
    }

    /// Send a message
    pub async fn send(
        &self,
        message: McpMessage
    ) -> ProtocolResult<McpResponse> {
        let url = format!("{}/{}", self.config.endpoint, message.method);

        let mut request = self.client.post(&url)
            .json(&message);

        // Add API key if present
        if let Some(ref key) = self.config.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        // Add custom headers
        for (k, v) in &self.config.headers {
            request = request.header(k, v);
        }

        let response = request.send().await
            .map_err(|e| ProtocolError::Connection(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            return Err(ProtocolError::Mcp(format!("HTTP {}: {}", status, text)));
        }

        let mcp_response: McpResponse = response.json().await
            .map_err(|e| ProtocolError::Deserialization(e.to_string()))?;

        Ok(mcp_response)
    }

    /// Complete/predict
    pub async fn complete(
        &self,
        prompt: &str,
        max_tokens: Option<usize>,
    ) -> ProtocolResult<McpResponse> {
        let params = serde_json::json!({
            "prompt": prompt,
            "max_tokens": max_tokens,
        });

        let msg = McpMessage::new(McpMethod::Complete)
            .with_params(params)?;

        self.send(msg).await
    }

    /// Chat completion
    pub async fn chat(
        &self,
        messages: Vec<ChatMessage>,
        model: Option<&str>,
    ) -> ProtocolResult<McpResponse> {
        let params = serde_json::json!({
            "messages": messages,
            "model": model,
        });

        let msg = McpMessage::new(McpMethod::Chat)
            .with_params(params)?;

        self.send(msg).await
    }

    /// Stream completion
    pub async fn stream(
        &self,
        prompt: &str
    ) -> ProtocolResult<impl futures::Stream<Item = ProtocolResult<String>>> {
        // Stream implementation would go here
        todo!("Stream implementation")
    }

    /// Get embeddings
    pub async fn embeddings(
        &self,
        texts: Vec<String>
    ) -> ProtocolResult<McpResponse> {
        let params = serde_json::json!({
            "input": texts,
        });

        let msg = McpMessage::new(McpMethod::Embeddings)
            .with_params(params)?;

        self.send(msg).await
    }

    /// Health check
    pub async fn health(&self
    ) -> ProtocolResult<bool> {
        let msg = McpMessage::new(McpMethod::Health);
        
        match self.send(msg).await {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    /// List available models
    pub async fn list_models(&self
    ) -> ProtocolResult<Vec<ModelInfo>> {
        let msg = McpMessage::new(McpMethod::ListModels);
        
        let response = self.send(msg).await?;
        
        serde_json::from_value(response.result)
            .map_err(|e| ProtocolError::Deserialization(e.to_string()))
    }

    /// Check if connected
    pub async fn is_connected(&self
    ) -> bool {
        *self.connected.read().await
    }

    /// Disconnect
    pub async fn disconnect(&self
    ) {
        *self.connected.write().await = false;
    }
}

/// Chat message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    /// Role
    pub role: String,
    /// Content
    pub content: String,
    /// Name (for function/tool messages)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

impl ChatMessage {
    /// Create user message
    pub fn user(content: impl Into<String>) -> Self {
        Self {
            role: "user".to_string(),
            content: content.into(),
            name: None,
        }
    }

    /// Create assistant message
    pub fn assistant(content: impl Into<String>) -> Self {
        Self {
            role: "assistant".to_string(),
            content: content.into(),
            name: None,
        }
    }

    /// Create system message
    pub fn system(content: impl Into<String>) -> Self {
        Self {
            role: "system".to_string(),
            content: content.into(),
            name: None,
        }
    }
}

/// Model information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    /// Model ID
    pub id: String,
    /// Model name
    pub name: String,
    /// Model description
    pub description: Option<String>,
    /// Context window size
    pub context_window: Option<usize>,
    /// Max output tokens
    pub max_tokens: Option<usize>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mcp_message_new() {
        let msg = McpMessage::new(McpMethod::Complete);
        assert_eq!(msg.method, McpMethod::Complete);
    }

    #[test]
    fn test_mcp_message_with_params() {
        let msg = McpMessage::new(McpMethod::Complete)
            .with_params(serde_json::json!({"prompt": "Hello"}))
            .unwrap();

        assert_eq!(msg.params["prompt"], "Hello");
    }

    #[test]
    fn test_chat_message() {
        let msg = ChatMessage::user("Hello");
        assert_eq!(msg.role, "user");
        assert_eq!(msg.content, "Hello");

        let msg = ChatMessage::assistant("Hi there");
        assert_eq!(msg.role, "assistant");
    }

    #[test]
    fn test_mcp_config_default() {
        let config = McpConfig::default();
        assert_eq!(config.endpoint, "http://localhost:8080");
        assert_eq!(config.max_retries, 3);
    }

    #[test]
    fn test_mcp_method_display() {
        assert_eq!(McpMethod::Complete.to_string(), "complete");
        assert_eq!(McpMethod::Chat.to_string(), "chat");
    }
}
