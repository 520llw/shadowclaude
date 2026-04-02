//! Protocol message types and frames
//!
//! Defines the message format for all protocol communications

use bytes::Bytes;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Message types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MessageType {
    /// Request message
    Request,
    /// Response message
    Response,
    /// Notification (no response expected)
    Notification,
    /// Error message
    Error,
    /// Ping (keepalive)
    Ping,
    /// Pong (keepalive response)
    Pong,
    /// Stream chunk
    StreamChunk,
    /// Stream end
    StreamEnd,
    /// Control message
    Control,
}

impl MessageType {
    /// Check if message expects a response
    pub fn expects_response(&self
    ) -> bool {
        matches!(self, MessageType::Request)
    }

    /// Check if message is part of a stream
    pub fn is_stream(&self
    ) -> bool {
        matches!(self, MessageType::StreamChunk | MessageType::StreamEnd)
    }
}

/// Protocol message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProtocolMessage {
    /// Message ID
    pub id: Uuid,
    /// Message type
    #[serde(rename = "type")]
    pub message_type: MessageType,
    /// Method or topic
    pub method: Option<String>,
    /// Payload
    pub payload: serde_json::Value,
    /// Metadata
    #[serde(default)]
    pub metadata: HashMap<String, String>,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Correlation ID (for request-response)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<Uuid>,
}

impl ProtocolMessage {
    /// Create a new request message
    pub fn request(method: impl Into<String>, payload: impl Serialize) -> crate::ProtocolResult<Self> {
        Ok(Self {
            id: Uuid::new_v4(),
            message_type: MessageType::Request,
            method: Some(method.into()),
            payload: serde_json::to_value(payload)?,
            metadata: HashMap::new(),
            timestamp: Utc::now(),
            correlation_id: None,
        })
    }

    /// Create a new response message
    pub fn response(request_id: Uuid, payload: impl Serialize) -> crate::ProtocolResult<Self> {
        Ok(Self {
            id: Uuid::new_v4(),
            message_type: MessageType::Response,
            method: None,
            payload: serde_json::to_value(payload)?,
            metadata: HashMap::new(),
            timestamp: Utc::now(),
            correlation_id: Some(request_id),
        })
    }

    /// Create a notification message
    pub fn notification(topic: impl Into<String>, payload: impl Serialize) -> crate::ProtocolResult<Self> {
        Ok(Self {
            id: Uuid::new_v4(),
            message_type: MessageType::Notification,
            method: Some(topic.into()),
            payload: serde_json::to_value(payload)?,
            metadata: HashMap::new(),
            timestamp: Utc::now(),
            correlation_id: None,
        })
    }

    /// Create an error message
    pub fn error(request_id: Option<Uuid>, code: i32, message: impl Into<String>) -> Self {
        let payload = serde_json::json!({
            "code": code,
            "message": message.into(),
        });

        Self {
            id: Uuid::new_v4(),
            message_type: MessageType::Error,
            method: None,
            payload,
            metadata: HashMap::new(),
            timestamp: Utc::now(),
            correlation_id: request_id,
        }
    }

    /// Create ping message
    pub fn ping() -> Self {
        Self {
            id: Uuid::new_v4(),
            message_type: MessageType::Ping,
            method: None,
            payload: serde_json::Value::Null,
            metadata: HashMap::new(),
            timestamp: Utc::now(),
            correlation_id: None,
        }
    }

    /// Create pong message
    pub fn pong(ping_id: Uuid) -> Self {
        Self {
            id: Uuid::new_v4(),
            message_type: MessageType::Pong,
            method: None,
            payload: serde_json::Value::Null,
            metadata: HashMap::new(),
            timestamp: Utc::now(),
            correlation_id: Some(ping_id),
        }
    }

    /// Create stream chunk
    pub fn stream_chunk(stream_id: Uuid, data: impl Serialize, is_end: bool) -> crate::ProtocolResult<Self> {
        Ok(Self {
            id: Uuid::new_v4(),
            message_type: if is_end { MessageType::StreamEnd } else { MessageType::StreamChunk },
            method: None,
            payload: serde_json::to_value(data)?,
            metadata: {
                let mut m = HashMap::new();
                m.insert("stream_id".to_string(), stream_id.to_string());
                m
            },
            timestamp: Utc::now(),
            correlation_id: Some(stream_id),
        })
    }

    /// Get stream ID if this is a stream message
    pub fn stream_id(&self
    ) -> Option<Uuid> {
        if self.message_type.is_stream() {
            self.metadata.get("stream_id")
                .and_then(|s| Uuid::parse_str(s).ok())
                .or(self.correlation_id)
        } else {
            None
        }
    }

    /// Get payload as specific type
    pub fn payload<T: for<'de> Deserialize<'de>>(&self
    ) -> crate::ProtocolResult<T> {
        serde_json::from_value(self.payload.clone())
            .map_err(|e| crate::ProtocolError::Deserialization(e.to_string()))
    }

    /// Serialize to JSON string
    pub fn to_json(&self
    ) -> crate::ProtocolResult<String> {
        serde_json::to_string(self)
            .map_err(|e| crate::ProtocolError::Serialization(e.to_string()))
    }

    /// Deserialize from JSON string
    pub fn from_json(s: &str
    ) -> crate::ProtocolResult<Self> {
        serde_json::from_str(s)
            .map_err(|e| crate::ProtocolError::Deserialization(e.to_string()))
    }
}

/// Message frame for wire transmission
#[derive(Debug, Clone)]
pub enum MessageFrame {
    /// Text frame (UTF-8)
    Text(String),
    /// Binary frame
    Binary(Bytes),
    /// Ping frame
    Ping(Vec<u8>),
    /// Pong frame
    Pong(Vec<u8>),
    /// Close frame
    Close(Option<(u16, String)>),
}

impl MessageFrame {
    /// Create text frame from message
    pub fn from_message(msg: &ProtocolMessage
    ) -> crate::ProtocolResult<Self> {
        let json = msg.to_json()?;
        Ok(MessageFrame::Text(json))
    }

    /// Parse message from text frame
    pub fn to_message(&self
    ) -> crate::ProtocolResult<ProtocolMessage> {
        match self {
            MessageFrame::Text(text) => {
                ProtocolMessage::from_json(text)
            }
            MessageFrame::Binary(data) => {
                serde_json::from_slice(data)
                    .map_err(|e| crate::ProtocolError::Deserialization(e.to_string()))
            }
            _ => Err(crate::ProtocolError::Protocol(
                "Cannot convert frame type to message".to_string()
            )),
        }
    }

    /// Check if this is a control frame
    pub fn is_control(&self
    ) -> bool {
        matches!(self, MessageFrame::Ping(_) | MessageFrame::Pong(_) | MessageFrame::Close(_))
    }

    /// Get frame size in bytes
    pub fn len(&self
    ) -> usize {
        match self {
            MessageFrame::Text(s) => s.len(),
            MessageFrame::Binary(b) => b.len(),
            MessageFrame::Ping(p) => p.len(),
            MessageFrame::Pong(p) => p.len(),
            MessageFrame::Close(_) => 0,
        }
    }

    /// Check if frame is empty
    pub fn is_empty(&self
    ) -> bool {
        self.len() == 0
    }
}

/// Message builder for fluent construction
pub struct MessageBuilder {
    message: ProtocolMessage,
}

impl MessageBuilder {
    /// Start building a request
    pub fn request(method: impl Into<String>) -> Self {
        Self {
            message: ProtocolMessage {
                id: Uuid::new_v4(),
                message_type: MessageType::Request,
                method: Some(method.into()),
                payload: serde_json::Value::Null,
                metadata: HashMap::new(),
                timestamp: Utc::now(),
                correlation_id: None,
            }
        }
    }

    /// Start building a notification
    pub fn notification(topic: impl Into<String>) -> Self {
        Self {
            message: ProtocolMessage {
                id: Uuid::new_v4(),
                message_type: MessageType::Notification,
                method: Some(topic.into()),
                payload: serde_json::Value::Null,
                metadata: HashMap::new(),
                timestamp: Utc::now(),
                correlation_id: None,
            }
        }
    }

    /// Set payload
    pub fn payload(mut self, payload: impl Serialize) -> crate::ProtocolResult<Self> {
        self.message.payload = serde_json::to_value(payload)?;
        Ok(self)
    }

    /// Add metadata
    pub fn metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.message.metadata.insert(key.into(), value.into());
        self
    }

    /// Set correlation ID
    pub fn correlation(mut self, id: Uuid) -> Self {
        self.message.correlation_id = Some(id);
        self
    }

    /// Build the message
    pub fn build(self) -> ProtocolMessage {
        self.message
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_request() {
        let msg = ProtocolMessage::request("test_method", serde_json::json!({"key": "value"})).unwrap();
        assert_eq!(msg.message_type, MessageType::Request);
        assert_eq!(msg.method, Some("test_method".to_string()));
    }

    #[test]
    fn test_message_response() {
        let request_id = Uuid::new_v4();
        let msg = ProtocolMessage::response(request_id, serde_json::json!({"result": "ok"})).unwrap();
        assert_eq!(msg.message_type, MessageType::Response);
        assert_eq!(msg.correlation_id, Some(request_id));
    }

    #[test]
    fn test_message_error() {
        let msg = ProtocolMessage::error(None, 500, "Internal error");
        assert_eq!(msg.message_type, MessageType::Error);
        assert_eq!(msg.payload["code"], 500);
    }

    #[test]
    fn test_message_ping_pong() {
        let ping = ProtocolMessage::ping();
        assert_eq!(ping.message_type, MessageType::Ping);

        let pong = ProtocolMessage::pong(ping.id);
        assert_eq!(pong.message_type, MessageType::Pong);
        assert_eq!(pong.correlation_id, Some(ping.id));
    }

    #[test]
    fn test_message_serialization() {
        let msg = ProtocolMessage::request("test", serde_json::json!({})).unwrap();
        let json = msg.to_json().unwrap();
        let parsed = ProtocolMessage::from_json(&json).unwrap();
        assert_eq!(msg.id, parsed.id);
    }

    #[test]
    fn test_message_frame() {
        let msg = ProtocolMessage::request("test", serde_json::json!({})).unwrap();
        let frame = MessageFrame::from_message(&msg).unwrap();
        
        match frame {
            MessageFrame::Text(text) => {
                assert!(text.contains("test"));
            }
            _ => panic!("Expected text frame"),
        }
    }

    #[test]
    fn test_message_builder() {
        let msg = MessageBuilder::request("method")
            .payload(serde_json::json!({"data": 123})).unwrap()
            .metadata("key", "value")
            .build();

        assert_eq!(msg.message_type, MessageType::Request);
        assert_eq!(msg.metadata.get("key"), Some(&"value".to_string()));
    }
}
