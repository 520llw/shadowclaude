//! Dialogue state machine and TAOR cycle implementation
//!
//! TAOR = Think-Act-Observe-Reflect
//! This module implements the dialogue state machine that powers ShadowClaude's
//! conversation flow with advanced context management and tool integration.

use crate::{
    cache::CacheManager,
    error::{CoreError, CoreResult, DialogueError, ErrorContext, ErrorSeverity},
    message::{Message, MessageContent, MessageId, MessageRole},
    session::{Session, SessionId, SessionManager, SessionState},
    types::*,
};
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tracing::{debug, error, info, instrument, trace, warn};

/// Unique identifier for a dialogue turn
pub type TurnId = TypedId<markers::Turn>;

/// Dialogue states in the TAOR cycle
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum DialogueState {
    /// Idle, waiting for input
    Idle,
    /// Thinking about the input
    Thinking,
    /// Acting on the thought (tool use, etc.)
    Acting,
    /// Observing the action results
    Observing,
    /// Reflecting on the observation
    Reflecting,
    /// Generating response
    Responding,
    /// Completed successfully
    Completed,
    /// Error occurred
    Error,
}

impl DialogueState {
    /// Get the next state in the TAOR cycle
    pub fn next(&self) -> Option<DialogueState> {
        use DialogueState::*;
        match self {
            Idle => Some(Thinking),
            Thinking => Some(Acting),
            Acting => Some(Observing),
            Observing => Some(Reflecting),
            Reflecting => Some(Responding),
            Responding => Some(Completed),
            Completed => None,
            Error => None,
        }
    }

    /// Check if this state is terminal
    pub fn is_terminal(&self) -> bool {
        matches!(self, DialogueState::Completed | DialogueState::Error)
    }

    /// Check if the dialogue is active
    pub fn is_active(&self) -> bool {
        !self.is_terminal()
    }

    /// Get display name
    pub fn display_name(&self) -> &'static str {
        match self {
            DialogueState::Idle => "idle",
            DialogueState::Thinking => "thinking",
            DialogueState::Acting => "acting",
            DialogueState::Observing => "observing",
            DialogueState::Reflecting => "reflecting",
            DialogueState::Responding => "responding",
            DialogueState::Completed => "completed",
            DialogueState::Error => "error",
        }
    }
}

impl fmt::Display for DialogueState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.display_name())
    }
}

/// TAOR cycle configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaorConfig {
    /// Maximum thinking time in seconds
    pub max_thinking_secs: u64,
    /// Maximum acting time in seconds
    pub max_acting_secs: u64,
    /// Maximum observing time in seconds
    pub max_observing_secs: u64,
    /// Maximum reflecting time in seconds
    pub max_reflecting_secs: u64,
    /// Maximum response generation time in seconds
    pub max_responding_secs: u64,
    /// Enable tool use during acting phase
    pub enable_tools: bool,
    /// Maximum tool calls per turn
    pub max_tool_calls: usize,
    /// Enable reflection phase
    pub enable_reflection: bool,
    /// Maximum context tokens
    pub max_context_tokens: usize,
}

impl Default for TaorConfig {
    fn default() -> Self {
        Self {
            max_thinking_secs: 30,
            max_acting_secs: 60,
            max_observing_secs: 10,
            max_reflecting_secs: 15,
            max_responding_secs: 60,
            enable_tools: true,
            max_tool_calls: 10,
            enable_reflection: true,
            max_context_tokens: 8192,
        }
    }
}

/// Dialogue configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DialogueConfig {
    /// TAOR cycle configuration
    pub taor: TaorConfig,
    /// Enable streaming responses
    pub enable_streaming: bool,
    /// Response chunk size (tokens)
    pub chunk_size: usize,
    /// Maximum consecutive turns
    pub max_consecutive_turns: usize,
    /// Context retention policy
    pub context_retention: ContextRetention,
    /// Temperature for generation
    pub temperature: f32,
    /// Top-p sampling
    pub top_p: f32,
    /// Maximum response tokens
    pub max_response_tokens: usize,
}

impl Default for DialogueConfig {
    fn default() -> Self {
        Self {
            taor: TaorConfig::default(),
            enable_streaming: true,
            chunk_size: 16,
            max_consecutive_turns: 10,
            context_retention: ContextRetention::default(),
            temperature: 0.7,
            top_p: 0.9,
            max_response_tokens: 2048,
        }
    }
}

/// Context retention policy
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ContextRetention {
    /// Keep all context
    Full,
    /// Keep last N messages
    LastN(usize),
    /// Keep context within token limit
    TokenLimit(usize),
    /// Summarize old context
    Summarize,
}

impl Default for ContextRetention {
    fn default() -> Self {
        ContextRetention::TokenLimit(8192)
    }
}

/// Configuration for a single turn
#[derive(Debug, Clone)]
pub struct TurnConfig {
    /// Turn timeout
    pub timeout: Duration,
    /// Enable streaming
    pub streaming: bool,
    /// Custom system prompt
    pub system_prompt: Option<String>,
    /// Tool overrides
    pub tools: Option<Vec<ToolDefinition>>,
    /// Temperature override
    pub temperature: Option<f32>,
    /// Max tokens override
    pub max_tokens: Option<usize>,
}

impl Default for TurnConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(120),
            streaming: true,
            system_prompt: None,
            tools: None,
            temperature: None,
            max_tokens: None,
        }
    }
}

/// Tool definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolDefinition {
    /// Tool name
    pub name: String,
    /// Tool description
    pub description: String,
    /// Tool parameters schema
    pub parameters: serde_json::Value,
    /// Whether the tool requires confirmation
    pub requires_confirmation: bool,
}

/// Tool call
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    /// Tool name
    pub tool_name: String,
    /// Call ID
    pub call_id: String,
    /// Arguments
    pub arguments: serde_json::Value,
    /// Timestamp
    pub timestamp: Timestamp,
}

/// Tool result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    /// Call ID
    pub call_id: String,
    /// Success or error
    pub success: bool,
    /// Result content
    pub content: String,
    /// Error message if failed
    pub error: Option<String>,
    /// Execution time in milliseconds
    pub execution_time_ms: u64,
    /// Timestamp
    pub timestamp: Timestamp,
}

/// A dialogue turn
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Turn {
    /// Turn ID
    pub id: TurnId,
    /// Session ID
    pub session_id: SessionId,
    /// Turn number in session
    pub turn_number: u64,
    /// User input
    pub input: String,
    /// State transitions
    pub states: Vec<StateTransition>,
    /// Tool calls made
    pub tool_calls: Vec<ToolCall>,
    /// Tool results
    pub tool_results: Vec<ToolResult>,
    /// Generated response
    pub response: Option<String>,
    /// Token usage
    pub token_usage: TokenUsage,
    /// Timing information
    pub timing: TurnTiming,
    /// Created at
    pub created_at: Timestamp,
    /// Completed at
    pub completed_at: Option<Timestamp>,
}

impl Turn {
    /// Create a new turn
    pub fn new(session_id: SessionId, turn_number: u64, input: String) -> Self {
        let now = Timestamp::now();
        Self {
            id: TurnId::new(),
            session_id,
            turn_number,
            input,
            states: vec![StateTransition::new(DialogueState::Idle, now)],
            tool_calls: Vec::new(),
            tool_results: Vec::new(),
            response: None,
            token_usage: TokenUsage::default(),
            timing: TurnTiming::new(now),
            created_at: now,
            completed_at: None,
        }
    }

    /// Get current state
    pub fn current_state(&self) -> DialogueState {
        self.states
            .last()
            .map(|s| s.state)
            .unwrap_or(DialogueState::Idle)
    }

    /// Transition to a new state
    pub fn transition_to(&mut self, new_state: DialogueState) {
        self.states.push(StateTransition::new(
            new_state,
            Timestamp::now(),
        ));
    }

    /// Add a tool call
    pub fn add_tool_call(&mut self, call: ToolCall) {
        self.tool_calls.push(call);
    }

    /// Add a tool result
    pub fn add_tool_result(&mut self, result: ToolResult) {
        self.tool_results.push(result);
    }

    /// Set the response
    pub fn set_response(&mut self, response: String) {
        self.response = Some(response);
        self.completed_at = Some(Timestamp::now());
    }

    /// Update token usage
    pub fn update_token_usage(&mut self, usage: TokenUsage) {
        self.token_usage = usage;
    }

    /// Get total duration
    pub fn duration(&self) -> Option<Duration> {
        self.completed_at
            .and_then(|end| end.duration_since(self.created_at))
    }

    /// Check if turn is complete
    pub fn is_complete(&self) -> bool {
        self.current_state().is_terminal()
    }
}

/// State transition record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateTransition {
    /// State
    pub state: DialogueState,
    /// Timestamp
    pub timestamp: Timestamp,
    /// Optional note
    pub note: Option<String>,
}

impl StateTransition {
    /// Create a new state transition
    pub fn new(state: DialogueState, timestamp: Timestamp) -> Self {
        Self {
            state,
            timestamp,
            note: None,
        }
    }

    /// Add a note
    pub fn with_note(mut self, note: impl Into<String>) -> Self {
        self.note = Some(note.into());
        self
    }
}

/// Token usage statistics
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize)]
pub struct TokenUsage {
    /// Prompt tokens
    pub prompt_tokens: usize,
    /// Completion tokens
    pub completion_tokens: usize,
    /// Total tokens
    pub total_tokens: usize,
}

impl TokenUsage {
    /// Create new token usage
    pub fn new(prompt: usize, completion: usize) -> Self {
        Self {
            prompt_tokens: prompt,
            completion_tokens: completion,
            total_tokens: prompt + completion,
        }
    }

    /// Add usage
    pub fn add(&mut self, other: TokenUsage) {
        self.prompt_tokens += other.prompt_tokens;
        self.completion_tokens += other.completion_tokens;
        self.total_tokens += other.total_tokens;
    }
}

/// Turn timing information
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TurnTiming {
    /// Start time
    pub started_at: Timestamp,
    /// Thinking phase duration
    pub thinking_duration_ms: Option<u64>,
    /// Acting phase duration
    pub acting_duration_ms: Option<u64>,
    /// Observing phase duration
    pub observing_duration_ms: Option<u64>,
    /// Reflecting phase duration
    pub reflecting_duration_ms: Option<u64>,
    /// Responding phase duration
    pub responding_duration_ms: Option<u64>,
}

impl TurnTiming {
    /// Create new timing
    pub fn new(started_at: Timestamp) -> Self {
        Self {
            started_at,
            ..Default::default()
        }
    }

    /// Get total duration
    pub fn total_duration_ms(&self) -> u64 {
        self.thinking_duration_ms.unwrap_or(0)
            + self.acting_duration_ms.unwrap_or(0)
            + self.observing_duration_ms.unwrap_or(0)
            + self.reflecting_duration_ms.unwrap_or(0)
            + self.responding_duration_ms.unwrap_or(0)
    }
}

/// TAOR cycle implementation
pub struct TaorCycle {
    /// Configuration
    config: TaorConfig,
    /// Current turn
    current_turn: Option<Turn>,
    /// Tool registry
    tools: HashMap<String, Box<dyn Tool>>,
}

impl TaorCycle {
    /// Create a new TAOR cycle
    pub fn new(config: TaorConfig) -> Self {
        Self {
            config,
            current_turn: None,
            tools: HashMap::new(),
        }
    }

    /// Register a tool
    pub fn register_tool(
        &mut self,
        name: impl Into<String>,
        tool: Box<dyn Tool>,
    ) {
        self.tools.insert(name.into(), tool);
    }

    /// Start a new turn
    pub fn start_turn(
        &mut self,
        session_id: SessionId,
        turn_number: u64,
        input: String,
    ) -> CoreResult<&mut Turn> {
        if self.current_turn.is_some() {
            return Err(CoreError::DialogueError(
                DialogueError::InvalidTransition {
                    from: self
                        .current_turn
                        .as_ref()
                        .unwrap()
                        .current_state()
                        .to_string(),
                    to: DialogueState::Idle.to_string(),
                },
            ));
        }

        let turn = Turn::new(session_id, turn_number, input);
        self.current_turn = Some(turn);
        Ok(self.current_turn.as_mut().unwrap())
    }

    /// Execute the thinking phase
    pub async fn think(
        &mut self,
        context: &DialogueContext,
    ) -> CoreResult<ThinkResult> {
        let turn = self
            .current_turn
            .as_mut()
            .ok_or_else(|| CoreError::DialogueError(DialogueError::TurnFailed(
                "No active turn".to_string()
            )))?;

        if turn.current_state() != DialogueState::Idle {
            return Err(CoreError::DialogueError(DialogueError::InvalidTransition {
                from: turn.current_state().to_string(),
                to: DialogueState::Thinking.to_string(),
            }));
        }

        turn.transition_to(DialogueState::Thinking);
        let start = std::time::Instant::now();

        // Thinking logic: analyze input, determine intent, plan approach
        let result = self.perform_thinking(context, &turn.input).await;

        let duration = start.elapsed().as_millis() as u64;
        turn.timing.thinking_duration_ms = Some(duration);

        match result {
            Ok(think_result) => {
                turn.transition_to(DialogueState::Acting);
                Ok(think_result)
            }
            Err(e) => {
                turn.transition_to(DialogueState::Error);
                Err(e)
            }
        }
    }

    /// Execute the acting phase
    pub async fn act(
        &mut self,
        think_result: &ThinkResult,
    ) -> CoreResult<ActResult> {
        let turn = self
            .current_turn
            .as_mut()
            .ok_or_else(|| CoreError::DialogueError(DialogueError::TurnFailed(
                "No active turn".to_string()
            )))?;

        if turn.current_state() != DialogueState::Thinking {
            return Err(CoreError::DialogueError(DialogueError::InvalidTransition {
                from: turn.current_state().to_string(),
                to: DialogueState::Acting.to_string(),
            }));
        }

        turn.transition_to(DialogueState::Acting);
        let start = std::time::Instant::now();

        let result = self.perform_acting(think_result).await;

        let duration = start.elapsed().as_millis() as u64;
        turn.timing.acting_duration_ms = Some(duration);

        match result {
            Ok(act_result) => {
                turn.transition_to(DialogueState::Observing);
                Ok(act_result)
            }
            Err(e) => {
                turn.transition_to(DialogueState::Error);
                Err(e)
            }
        }
    }

    /// Execute the observing phase
    pub async fn observe(
        &mut self,
        act_result: &ActResult,
    ) -> CoreResult<ObserveResult> {
        let turn = self
            .current_turn
            .as_mut()
            .ok_or_else(|| CoreError::DialogueError(DialogueError::TurnFailed(
                "No active turn".to_string()
            )))?;

        if turn.current_state() != DialogueState::Acting {
            return Err(CoreError::DialogueError(DialogueError::InvalidTransition {
                from: turn.current_state().to_string(),
                to: DialogueState::Observing.to_string(),
            }));
        }

        turn.transition_to(DialogueState::Observing);
        let start = std::time::Instant::now();

        let result = self.perform_observing(act_result).await;

        let duration = start.elapsed().as_millis() as u64;
        turn.timing.observing_duration_ms = Some(duration);

        match result {
            Ok(observe_result) => {
                if self.config.enable_reflection {
                    turn.transition_to(DialogueState::Reflecting);
                } else {
                    turn.transition_to(DialogueState::Responding);
                }
                Ok(observe_result)
            }
            Err(e) => {
                turn.transition_to(DialogueState::Error);
                Err(e)
            }
        }
    }

    /// Execute the reflecting phase
    pub async fn reflect(
        &mut self,
        observe_result: &ObserveResult,
    ) -> CoreResult<ReflectResult> {
        let turn = self
            .current_turn
            .as_mut()
            .ok_or_else(|| CoreError::DialogueError(DialogueError::TurnFailed(
                "No active turn".to_string()
            )))?;

        if !self.config.enable_reflection {
            return Ok(ReflectResult::default());
        }

        if turn.current_state() != DialogueState::Observing {
            return Err(CoreError::DialogueError(DialogueError::InvalidTransition {
                from: turn.current_state().to_string(),
                to: DialogueState::Reflecting.to_string(),
            }));
        }

        turn.transition_to(DialogueState::Reflecting);
        let start = std::time::Instant::now();

        let result = self.perform_reflecting(observe_result).await;

        let duration = start.elapsed().as_millis() as u64;
        turn.timing.reflecting_duration_ms = Some(duration);

        match result {
            Ok(reflect_result) => {
                turn.transition_to(DialogueState::Responding);
                Ok(reflect_result)
            }
            Err(e) => {
                turn.transition_to(DialogueState::Error);
                Err(e)
            }
        }
    }

    /// Execute the responding phase
    pub async fn respond(
        &mut self,
        context: &DialogueContext,
    ) -> CoreResult<String> {
        let turn = self
            .current_turn
            .as_mut()
            .ok_or_else(|| CoreError::DialogueError(DialogueError::TurnFailed(
                "No active turn".to_string()
            )))?;

        if turn.current_state() != DialogueState::Responding 
            && turn.current_state() != DialogueState::Reflecting {
            return Err(CoreError::DialogueError(DialogueError::InvalidTransition {
                from: turn.current_state().to_string(),
                to: DialogueState::Responding.to_string(),
            }));
        }

        if turn.current_state() == DialogueState::Reflecting {
            turn.transition_to(DialogueState::Responding);
        }

        let start = std::time::Instant::now();

        let result = self.perform_responding(context, turn).await;

        let duration = start.elapsed().as_millis() as u64;
        turn.timing.responding_duration_ms = Some(duration);

        match result {
            Ok(response) => {
                turn.set_response(response.clone());
                turn.transition_to(DialogueState::Completed);
                Ok(response)
            }
            Err(e) => {
                turn.transition_to(DialogueState::Error);
                Err(e)
            }
        }
    }

    /// Complete the current turn
    pub fn complete_turn(&mut self
    ) -> Option<Turn> {
        self.current_turn.take()
    }

    // Private helper methods
    async fn perform_thinking(
        &self,
        _context: &DialogueContext,
        input: &str,
    ) -> CoreResult<ThinkResult> {
        trace!(input = %input, "Performing thinking phase");
        Ok(ThinkResult {
            intent: "general".to_string(),
            entities: Vec::new(),
            requires_tools: false,
        })
    }

    async fn perform_acting(
        &mut self,
        _think_result: &ThinkResult,
    ) -> CoreResult<ActResult> {
        Ok(ActResult { actions: Vec::new() })
    }

    async fn perform_observing(
        &self,
        _act_result: &ActResult,
    ) -> CoreResult<ObserveResult> {
        Ok(ObserveResult { observations: Vec::new() })
    }

    async fn perform_reflecting(
        &self,
        _observe_result: &ObserveResult,
    ) -> CoreResult<ReflectResult> {
        Ok(ReflectResult { insights: Vec::new() })
    }

    async fn perform_responding(
        &self,
        _context: &DialogueContext,
        turn: &Turn,
    ) -> CoreResult<String> {
        Ok(format!("Response to: {}", turn.input))
    }
}

/// Thinking phase result
#[derive(Debug, Clone)]
pub struct ThinkResult {
    /// Detected intent
    pub intent: String,
    /// Extracted entities
    pub entities: Vec<String>,
    /// Whether tool use is required
    pub requires_tools: bool,
}

/// Acting phase result
#[derive(Debug, Clone)]
pub struct ActResult {
    /// Actions taken
    pub actions: Vec<String>,
}

/// Observing phase result
#[derive(Debug, Clone)]
pub struct ObserveResult {
    /// Observations made
    pub observations: Vec<String>,
}

/// Reflecting phase result
#[derive(Debug, Clone, Default)]
pub struct ReflectResult {
    /// Insights gained
    pub insights: Vec<String>,
}

/// Dialogue context
#[derive(Debug, Clone)]
pub struct DialogueContext {
    /// Session ID
    pub session_id: SessionId,
    /// Previous turns
    pub history: Vec<Turn>,
    /// System prompt
    pub system_prompt: String,
    /// Available tools
    pub available_tools: Vec<ToolDefinition>,
    /// User preferences
    pub preferences: HashMap<String, String>,
}

/// Tool trait
#[async_trait::async_trait]
pub trait Tool: Send + Sync {
    /// Get tool definition
    fn definition(&self) -> ToolDefinition;

    /// Execute the tool
    async fn execute(
        &self,
        arguments: serde_json::Value,
    ) -> CoreResult<String>;

    /// Check if execution should require confirmation
    fn requires_confirmation(&self, _arguments: &serde_json::Value) -> bool {
        false
    }
}

/// Dialogue manager
pub struct DialogueManager {
    /// Configuration
    config: DialogueConfig,
    /// Session manager
    session_manager: Arc<SessionManager>,
    /// Cache manager
    cache_manager: Arc<CacheManager>,
    /// Turn counter per session
    turn_counters: DashMap<SessionId, AtomicU64>,
}

impl DialogueManager {
    /// Create a new dialogue manager
    pub async fn new(
        config: DialogueConfig,
        session_manager: Arc<SessionManager>,
        cache_manager: Arc<CacheManager>,
    ) -> CoreResult<Self> {
        Ok(Self {
            config,
            session_manager,
            cache_manager,
            turn_counters: DashMap::new(),
        })
    }

    /// Process a user message
    #[instrument(skip(self, session, message))]
    pub async fn process_message(
        &self,
        session: Arc<Session>,
        message: Message,
    ) -> CoreResult<DialogueResult> {
        // Transition session to processing
        session.transition_to(SessionState::Processing)?;

        // Get turn number
        let turn_number = self
            .turn_counters
            .entry(session.id())
            .or_insert_with(|| AtomicU64::new(0))
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

        // Create TAOR cycle
        let mut cycle = TaorCycle::new(self.config.taor.clone());

        // Get input from message
        let input = match &message.content {
            MessageContent::Text(text) => text.clone(),
            _ => return Err(CoreError::DialogueError(
                DialogueError::InvalidMessageFormat("Expected text message".to_string())
            )),
        };

        // Execute TAOR cycle
        let turn = cycle.start_turn(session.id(), turn_number, input)?;

        // Build context
        let context = DialogueContext {
            session_id: session.id(),
            history: Vec::new(),
            system_prompt: "You are a helpful assistant.".to_string(),
            available_tools: Vec::new(),
            preferences: HashMap::new(),
        };

        // Execute phases
        let think_result = cycle.think(&context).await?;
        let act_result = cycle.act(&think_result).await?;
        let observe_result = cycle.observe(&act_result).await?;
        let _reflect_result = cycle.reflect(&observe_result).await?;
        let response = cycle.respond(&context).await?;

        // Complete turn
        let completed_turn = cycle.complete_turn().unwrap();

        // Add message to session
        let response_message = Message {
            id: MessageId::new(),
            role: MessageRole::Assistant,
            content: MessageContent::Text(response.clone()),
            timestamp: Timestamp::now(),
            metadata: HashMap::new(),
        };
        session.add_message(message)?;
        session.add_message(response_message)?;

        // Transition session back to active
        session.transition_to(SessionState::Active)?;

        Ok(DialogueResult {
            turn: completed_turn,
            response,
        })
    }

    /// Stream process a user message
    pub async fn stream_process_message(
        &self,
        _session: Arc<Session>,
        _message: Message,
    ) -> CoreResult<impl futures::Stream<Item = CoreResult<String>>> {
        todo!("Streaming implementation")
    }

    /// Get dialogue history for a session
    pub fn get_history(
        &self,
        session_id: SessionId,
    ) -> Vec<Turn> {
        // This would retrieve from cache or storage
        Vec::new()
    }

    /// Clear dialogue history
    pub fn clear_history(
        &self,
        session_id: SessionId,
    ) {
        self.turn_counters.remove(&session_id);
    }
}

impl fmt::Debug for DialogueManager {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("DialogueManager")
            .field("config", &self.config)
            .field("active_sessions", &self.turn_counters.len())
            .finish()
    }
}

/// Dialogue processing result
#[derive(Debug, Clone)]
pub struct DialogueResult {
    /// The completed turn
    pub turn: Turn,
    /// The response text
    pub response: String,
}

use std::fmt;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dialogue_state_transitions() {
        assert_eq!(
            DialogueState::Idle.next(),
            Some(DialogueState::Thinking)
        );
        assert_eq!(
            DialogueState::Thinking.next(),
            Some(DialogueState::Acting)
        );
        assert_eq!(
            DialogueState::Responding.next(),
            Some(DialogueState::Completed)
        );
        assert_eq!(DialogueState::Completed.next(), None);
    }

    #[test]
    fn test_dialogue_state_terminal() {
        assert!(!DialogueState::Idle.is_terminal());
        assert!(!DialogueState::Thinking.is_terminal());
        assert!(DialogueState::Completed.is_terminal());
        assert!(DialogueState::Error.is_terminal());
    }

    #[tokio::test]
    async fn test_taor_cycle() {
        let mut cycle = TaorCycle::new(TaorConfig::default());
        let session_id = SessionId::new();

        cycle.start_turn(session_id, 1, "Hello".to_string()).unwrap();

        let context = DialogueContext {
            session_id,
            history: Vec::new(),
            system_prompt: "Test".to_string(),
            available_tools: Vec::new(),
            preferences: HashMap::new(),
        };

        let think = cycle.think(&context).await.unwrap();
        let act = cycle.act(&think).await.unwrap();
        let observe = cycle.observe(&act).await.unwrap();
        let _reflect = cycle.reflect(&observe).await.unwrap();
        let response = cycle.respond(&context).await.unwrap();

        assert!(!response.is_empty());

        let turn = cycle.complete_turn().unwrap();
        assert_eq!(turn.current_state(), DialogueState::Completed);
    }

    #[tokio::test]
    async fn test_turn_timing() {
        let mut cycle = TaorCycle::new(TaorConfig::default());
        let session_id = SessionId::new();

        cycle.start_turn(session_id, 1, "Test".to_string()).unwrap();

        let context = DialogueContext {
            session_id,
            history: Vec::new(),
            system_prompt: "Test".to_string(),
            available_tools: Vec::new(),
            preferences: HashMap::new(),
        };

        cycle.think(&context).await.unwrap();
        tokio::time::sleep(Duration::from_millis(10)).await;
        
        let turn = cycle.current_turn.as_ref().unwrap();
        assert!(turn.timing.thinking_duration_ms.unwrap_or(0) >= 0);
    }
}
