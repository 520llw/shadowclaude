//! Message types and queue for ShadowClaude
//!
//! This module provides message handling including:
//! - Message types and content
//! - Priority-based message queues
//! - Message routing
//! - Streaming support

use crate::{
    error::{CoreError, CoreResult, ErrorContext, ErrorSeverity, MessageError},
    types::*,
};
use serde::{Deserialize, Serialize};
use std::collections::{BinaryHeap, HashMap, VecDeque};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;
use tracing::{debug, trace, warn};

/// Unique identifier for messages
pub type MessageId = TypedId<markers::Message>;

/// Message roles
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MessageRole {
    /// System message
    System,
    /// User message
    User,
    /// Assistant message
    Assistant,
    /// Tool message
    Tool,
    /// Function message (legacy)
    Function,
}

impl fmt::Display for MessageRole {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            MessageRole::System => write!(f, "system"),
            MessageRole::User => write!(f, "user"),
            MessageRole::Assistant => write!(f, "assistant"),
            MessageRole::Tool => write!(f, "tool"),
            MessageRole::Function => write!(f, "function"),
        }
    }
}

/// Message content types
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", content = "content")]
#[serde(rename_all = "snake_case")]
pub enum MessageContent {
    /// Plain text content
    Text(String),
    /// Multi-modal content
    MultiPart(Vec<ContentPart>),
    /// Structured content (JSON)
    Structured(serde_json::Value),
    /// Tool call
    ToolCall(ToolCallContent),
    /// Tool result
    ToolResult(ToolResultContent),
    /// Error content
    Error(String),
    /// Empty content
    Empty,
}

impl Default for MessageContent {
    fn default() -> Self {
        MessageContent::Empty
    }
}

impl MessageContent {
    /// Create text content
    pub fn text(s: impl Into<String>) -> Self {
        MessageContent::Text(s.into())
    }

    /// Get content as text if possible
    pub fn as_text(&self
    ) -> Option<&str> {
        match self {
            MessageContent::Text(text) => Some(text),
            _ => None,
        }
    }

    /// Check if content is empty
    pub fn is_empty(&self) -> bool {
        match self {
            MessageContent::Text(t) => t.is_empty(),
            MessageContent::MultiPart(parts) => parts.is_empty(),
            MessageContent::Structured(v) => v.is_null() || v.as_object().map(|o| o.is_empty()).unwrap_or(false),
            MessageContent::ToolCall(_) => false,
            MessageContent::ToolResult(_) => false,
            MessageContent::Error(e) => e.is_empty(),
            MessageContent::Empty => true,
        }
    }

    /// Get approximate token count
    pub fn token_estimate(&self
    ) -> usize {
        match self {
            MessageContent::Text(t) => t.len() / 4, // Rough estimate
            MessageContent::MultiPart(parts) => {
                parts.iter().map(|p| p.token_estimate()).sum()
            }
            MessageContent::Structured(v) => serde_json::to_string(v).unwrap_or_default().len() / 4,
            MessageContent::ToolCall(c) => c.arguments.to_string().len() / 4 + 10,
            MessageContent::ToolResult(r) => r.content.len() / 4 + 10,
            MessageContent::Error(e) => e.len() / 4,
            MessageContent::Empty => 0,
        }
    }
}

/// Content part for multi-modal messages
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type")]
#[serde(rename_all = "snake_case")]
pub enum ContentPart {
    /// Text part
    Text { text: String },
    /// Image part
    Image { url: String, #[serde(skip_serializing_if = "Option::is_none")] detail: Option<String> },
    /// Audio part
    Audio { url: String },
    /// Video part
    Video { url: String },
    /// File attachment
    File { name: String, content_type: String, size: usize },
}

impl ContentPart {
    /// Token estimate for this part
    pub fn token_estimate(&self
    ) -> usize {
        match self {
            ContentPart::Text { text } => text.len() / 4,
            ContentPart::Image { .. } => 765, // GPT-4 vision estimate
            ContentPart::Audio { .. } => 100,
            ContentPart::Video { .. } => 500,
            ContentPart::File { size, .. } => size / 100,
        }
    }
}

/// Tool call content
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolCallContent {
    /// Tool call ID
    pub id: String,
    /// Tool type
    #[serde(rename = "type")]
    pub tool_type: String,
    /// Tool name
    pub name: String,
    /// Tool arguments
    pub arguments: serde_json::Value,
}

/// Tool result content
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolResultContent {
    /// Tool call ID
    pub tool_call_id: String,
    /// Tool name
    pub name: String,
    /// Result content
    pub content: String,
    /// Whether successful
    pub is_error: bool,
}

/// Message priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum MessagePriority {
    /// System critical
    Critical = 0,
    /// High priority
    High = 1,
    /// Normal priority
    Normal = 2,
    /// Low priority
    Low = 3,
    /// Background processing
    Background = 4,
}

impl Default for MessagePriority {
    fn default() -> Self {
        MessagePriority::Normal
    }
}

impl MessagePriority {
    /// Get the numeric priority value
    pub fn value(&self
    ) -> u8 {
        *self as u8
    }
}

/// Message structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    /// Message ID
    pub id: MessageId,
    /// Message role
    pub role: MessageRole,
    /// Message content
    pub content: MessageContent,
    /// Creation timestamp
    pub timestamp: Timestamp,
    /// Additional metadata
    #[serde(default)]
    pub metadata: HashMap<String, String>,
}

impl Message {
    /// Create a new message
    pub fn new(role: MessageRole, content: MessageContent) -> Self {
        Self {
            id: MessageId::new(),
            role,
            content,
            timestamp: Timestamp::now(),
            metadata: HashMap::new(),
        }
    }

    /// Create a user message
    pub fn user(content: impl Into<String>) -> Self {
        Self::new(MessageRole::User, MessageContent::Text(content.into()))
    }

    /// Create an assistant message
    pub fn assistant(content: impl Into<String>) -> Self {
        Self::new(MessageRole::Assistant, MessageContent::Text(content.into()))
    }

    /// Create a system message
    pub fn system(content: impl Into<String>) -> Self {
        Self::new(MessageRole::System, MessageContent::Text(content.into()))
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Get approximate token count
    pub fn token_count(&self
    ) -> usize {
        self.content.token_estimate() + 4 // +4 for role
    }

    /// Check if this is a user message
    pub fn is_user(&self
    ) -> bool {
        matches!(self.role, MessageRole::User)
    }

    /// Check if this is an assistant message
    pub fn is_assistant(&self
    ) -> bool {
        matches!(self.role, MessageRole::Assistant)
    }
}

impl Default for Message {
    fn default() -> Self {
        Self {
            id: MessageId::new(),
            role: MessageRole::User,
            content: MessageContent::Empty,
            timestamp: Timestamp::now(),
            metadata: HashMap::new(),
        }
    }
}

/// Priority queue entry
#[derive(Debug, Clone)]
struct PriorityEntry {
    /// Priority
    priority: MessagePriority,
    /// Sequence number for FIFO within same priority
    sequence: u64,
    /// Message
    message: Message,
}

impl PartialEq for PriorityEntry {
    fn eq(&self, other: &Self) -> bool {
        self.priority == other.priority && self.sequence == other.sequence
    }
}

impl Eq for PriorityEntry {}

impl PartialOrd for PriorityEntry {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        // Reverse ordering for min-heap behavior (higher priority first)
        Some(self.cmp(other))
    }
}

impl Ord for PriorityEntry {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        // First by priority (lower value = higher priority)
        self.priority
            .cmp(&other.priority)
            // Then by sequence (earlier = higher priority)
            .then_with(|| other.sequence.cmp(&self.sequence))
    }
}

/// Message queue with priority support
pub struct MessageQueue {
    /// Heap for priority ordering
    heap: BinaryHeap<PriorityEntry>,
    /// Simple queue for FIFO ordering
    fifo: VecDeque<Message>,
    /// Sequence counter
    sequence: AtomicU64,
    /// Maximum capacity
    capacity: usize,
    /// Current size
    size: AtomicU64,
    /// Use priority queue or simple FIFO
    use_priority: bool,
}

impl MessageQueue {
    /// Create a new message queue
    pub fn new() -> Self {
        Self {
            heap: BinaryHeap::new(),
            fifo: VecDeque::new(),
            sequence: AtomicU64::new(0),
            capacity: 1000,
            size: AtomicU64::new(0),
            use_priority: true,
        }
    }

    /// Create with capacity
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            heap: BinaryHeap::with_capacity(capacity),
            fifo: VecDeque::with_capacity(capacity),
            sequence: AtomicU64::new(0),
            capacity,
            size: AtomicU64::new(0),
            use_priority: true,
        }
    }

    /// Create a simple FIFO queue
    pub fn fifo(capacity: usize) -> Self {
        Self {
            heap: BinaryHeap::new(),
            fifo: VecDeque::with_capacity(capacity),
            sequence: AtomicU64::new(0),
            capacity,
            size: AtomicU64::new(0),
            use_priority: false,
        }
    }

    /// Push a message with priority
    pub fn push(
        &mut self,
        message: Message,
        priority: MessagePriority,
    ) -> CoreResult<()> {
        if self.len() >= self.capacity {
            return Err(CoreError::MessageError(MessageError::QueueFull {
                current: self.len(),
                max: self.capacity,
            }));
        }

        if self.use_priority {
            let entry = PriorityEntry {
                priority,
                sequence: self.sequence.fetch_add(1, Ordering::SeqCst),
                message,
            };
            self.heap.push(entry);
        } else {
            self.fifo.push_back(message);
        }

        self.size.fetch_add(1, Ordering::SeqCst);
        trace!(queue_len = self.len(), "Message added to queue");
        Ok(())
    }

    /// Push a message with default priority
    pub fn push_message(
        &mut self,
        message: Message
    ) -> CoreResult<()> {
        self.push(message, MessagePriority::default())
    }

    /// Pop the highest priority message
    pub fn pop(&mut self) -> Option<Message> {
        let result = if self.use_priority {
            self.heap.pop().map(|e| e.message)
        } else {
            self.fifo.pop_front()
        };

        if result.is_some() {
            self.size.fetch_sub(1, Ordering::SeqCst);
        }

        result
    }

    /// Peek at the highest priority message without removing
    pub fn peek(&self) -> Option<&Message> {
        if self.use_priority {
            self.heap.peek().map(|e| &e.message)
        } else {
            self.fifo.front()
        }
    }

    /// Get queue length
    pub fn len(&self) -> usize {
        self.size.load(Ordering::Relaxed) as usize
    }

    /// Check if queue is empty
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Clear the queue
    pub fn clear(&mut self
    ) {
        self.heap.clear();
        self.fifo.clear();
        self.size.store(0, Ordering::SeqCst);
    }

    /// Drain all messages
    pub fn drain(&mut self
    ) -> Vec<Message> {
        let mut messages = Vec::with_capacity(self.len());

        while let Some(msg) = self.pop() {
            messages.push(msg);
        }

        messages
    }

    /// Convert to vector
    pub fn into_vec(self
    ) -> Vec<Message> {
        if self.use_priority {
            self.heap.into_sorted_vec().into_iter().map(|e| e.message).collect()
        } else {
            self.fifo.into_iter().collect()
        }
    }

    /// Retain only messages matching predicate
    pub fn retain<F>(&mut self, f: F)
    where
        F: Fn(&Message) -> bool,
    {
        if self.use_priority {
            let mut new_heap = BinaryHeap::with_capacity(self.capacity);
            let mut size = 0u64;

            while let Some(entry) = self.heap.pop() {
                if f(&entry.message) {
                    new_heap.push(entry);
                    size += 1;
                }
            }

            self.heap = new_heap;
            self.size.store(size, Ordering::SeqCst);
        } else {
            self.fifo.retain(f);
            self.size.store(self.fifo.len() as u64, Ordering::SeqCst);
        }
    }

    /// Get total token count of all messages
    pub fn total_tokens(&self
    ) -> usize {
        if self.use_priority {
            self.heap.iter().map(|e| e.message.token_count()).sum()
        } else {
            self.fifo.iter().map(|m| m.token_count()).sum()
        }
    }

    /// Truncate messages to fit within token limit
    pub fn truncate_to_tokens(&mut self,
        max_tokens: usize
    ) {
        let mut total = 0usize;

        self.retain(|m| {
            let count = m.token_count();
            if total + count <= max_tokens {
                total += count;
                true
            } else {
                false
            }
        });
    }
}

impl Default for MessageQueue {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Debug for MessageQueue {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("MessageQueue")
            .field("len", &self.len())
            .field("capacity", &self.capacity)
            .field("use_priority", &self.use_priority)
            .field("total_tokens", &self.total_tokens())
            .finish()
    }
}

/// Message stream chunk for streaming responses
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageChunk {
    /// Chunk index
    pub index: u64,
    /// Chunk content
    pub content: String,
    /// Whether this is the final chunk
    pub is_final: bool,
    /// Timestamp
    pub timestamp: Timestamp,
    /// Delta tokens
    pub delta_tokens: Option<usize>,
}

impl MessageChunk {
    /// Create a new chunk
    pub fn new(index: u64, content: impl Into<String>) -> Self {
        Self {
            index,
            content: content.into(),
            is_final: false,
            timestamp: Timestamp::now(),
            delta_tokens: None,
        }
    }

    /// Mark as final chunk
    pub fn final_chunk(mut self) -> Self {
        self.is_final = true;
        self
    }

    /// Set delta tokens
    pub fn with_tokens(mut self, tokens: usize) -> Self {
        self.delta_tokens = Some(tokens);
        self
    }
}

/// Message batch for bulk operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageBatch {
    /// Batch ID
    pub id: String,
    /// Messages
    pub messages: Vec<Message>,
    /// Created at
    pub created_at: Timestamp,
}

impl MessageBatch {
    /// Create a new batch
    pub fn new(messages: Vec<Message>) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            messages,
            created_at: Timestamp::now(),
        }
    }

    /// Get total token count
    pub fn total_tokens(&self
    ) -> usize {
        self.messages.iter().map(|m| m.token_count()).sum()
    }

    /// Get message count
    pub fn len(&self
    ) -> usize {
        self.messages.len()
    }

    /// Check if empty
    pub fn is_empty(&self
    ) -> bool {
        self.messages.is_empty()
    }
}

/// Message routing destination
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MessageDestination {
    /// Send to specific session
    Session(String),
    /// Send to user
    User(String),
    /// Broadcast to all
    Broadcast,
    /// Send to specific channel
    Channel(String),
}

/// Message router for routing messages
pub struct MessageRouter {
    /// Routing rules
    rules: Vec<RoutingRule>,
    /// Default destination
    default_destination: MessageDestination,
}

/// Routing rule
#[derive(Debug, Clone)]
pub struct RoutingRule {
    /// Condition
    pub condition: Box<dyn Fn(&Message) -> bool + Send + Sync>,
    /// Destination
    pub destination: MessageDestination,
}

impl MessageRouter {
    /// Create a new router
    pub fn new() -> Self {
        Self {
            rules: Vec::new(),
            default_destination: MessageDestination::Broadcast,
        }
    }

    /// Add a routing rule
    pub fn add_rule(
        &mut self,
        condition: impl Fn(&Message) -> bool + Send + Sync + 'static,
        destination: MessageDestination,
    ) {
        self.rules.push(RoutingRule {
            condition: Box::new(condition),
            destination,
        });
    }

    /// Route a message
    pub fn route(&self,
        message: &Message
    ) -> &MessageDestination {
        for rule in &self.rules {
            if (rule.condition)(message) {
                return &rule.destination;
            }
        }
        &self.default_destination
    }

    /// Set default destination
    pub fn set_default(
        &mut self,
        destination: MessageDestination
    ) {
        self.default_destination = destination;
    }
}

impl Default for MessageRouter {
    fn default() -> Self {
        Self::new()
    }
}

use std::fmt;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_creation() {
        let msg = Message::user("Hello");
        assert!(msg.is_user());
        assert_eq!(msg.as_text(), Some("Hello"));

        let msg = Message::assistant("Hi there");
        assert!(msg.is_assistant());
    }

    #[test]
    fn test_message_content() {
        let text = MessageContent::text("Hello");
        assert_eq!(text.as_text(), Some("Hello"));

        let empty = MessageContent::Empty;
        assert!(empty.is_empty());
    }

    #[test]
    fn test_message_queue_priority() {
        let mut queue = MessageQueue::new();

        let msg1 = Message::user("Low priority");
        let msg2 = Message::user("High priority");
        let msg3 = Message::user("Normal priority");

        queue.push(msg1.clone(), MessagePriority::Low).unwrap();
        queue.push(msg2.clone(), MessagePriority::High).unwrap();
        queue.push(msg3.clone(), MessagePriority::Normal).unwrap();

        // High priority should come first
        assert_eq!(queue.pop().unwrap().as_text(), Some("High priority"));
        assert_eq!(queue.pop().unwrap().as_text(), Some("Normal priority"));
        assert_eq!(queue.pop().unwrap().as_text(), Some("Low priority"));
    }

    #[test]
    fn test_message_queue_fifo() {
        let mut queue = MessageQueue::fifo(10);

        queue.push_message(Message::user("First")).unwrap();
        queue.push_message(Message::user("Second")).unwrap();
        queue.push_message(Message::user("Third")).unwrap();

        assert_eq!(queue.pop().unwrap().as_text(), Some("First"));
        assert_eq!(queue.pop().unwrap().as_text(), Some("Second"));
        assert_eq!(queue.pop().unwrap().as_text(), Some("Third"));
    }

    #[test]
    fn test_message_queue_capacity() {
        let mut queue = MessageQueue::with_capacity(2);

        queue.push_message(Message::user("1")).unwrap();
        queue.push_message(Message::user("2")).unwrap();

        assert!(queue.push_message(Message::user("3")).is_err());
    }

    #[test]
    fn test_message_token_estimate() {
        let msg = Message::user("This is a test message with some content");
        let tokens = msg.token_count();
        assert!(tokens > 0);
    }

    #[test]
    fn test_message_queue_truncate() {
        let mut queue = MessageQueue::new();

        for i in 0..10 {
            queue.push_message(Message::user("a".repeat(100))).unwrap();
        }

        let before = queue.len();
        queue.truncate_to_tokens(50);
        let after = queue.len();

        assert!(after < before);
    }

    #[test]
    fn test_message_chunk() {
        let chunk = MessageChunk::new(0, "Hello")
            .with_tokens(1)
            .final_chunk();

        assert_eq!(chunk.index, 0);
        assert_eq!(chunk.content, "Hello");
        assert!(chunk.is_final);
        assert_eq!(chunk.delta_tokens, Some(1));
    }

    #[test]
    fn test_message_batch() {
        let messages = vec![
            Message::user("Hello"),
            Message::assistant("Hi"),
        ];

        let batch = MessageBatch::new(messages);
        assert_eq!(batch.len(), 2);
        assert!(batch.total_tokens() > 0);
    }

    #[test]
    fn test_content_part_tokens() {
        let text = ContentPart::Text { text: "Hello world".to_string() };
        assert!(text.token_estimate() > 0);

        let image = ContentPart::Image { url: "http://example.com/img.jpg".to_string(), detail: None };
        assert_eq!(image.token_estimate(), 765);
    }
}
