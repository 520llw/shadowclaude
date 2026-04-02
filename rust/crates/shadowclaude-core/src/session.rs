//! Session management for ShadowClaude
//!
//! This module provides comprehensive session management including:
//! - Session lifecycle management
//! - Persistence and recovery
//! - Distributed session coordination
//! - Session migration between nodes

use crate::{
    cache::{CacheManager, CacheStrategy},
    error::{CoreError, CoreResult, ErrorContext, ErrorSeverity, SessionError},
    message::{Message, MessageId, MessageQueue},
    security::{SecurityContext, SecurityEngine, SecurityLevel},
    types::*,
};
use dashmap::DashMap;
use parking_lot::{Mutex, RwLock};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tracing::{debug, error, info, instrument, warn};

/// Unique identifier for a session
pub type SessionId = TypedId<markers::Session>;

/// Session state enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SessionState {
    /// Session is being initialized
    Initializing,
    /// Session is active and ready
    Active,
    /// Session is processing a request
    Processing,
    /// Session is paused (e.g., waiting for user)
    Paused,
    /// Session is being closed
    Closing,
    /// Session is closed
    Closed,
    /// Session has expired
    Expired,
    /// Session encountered an error
    Error,
}

impl SessionState {
    /// Check if the session is active
    pub fn is_active(&self) -> bool {
        matches!(self, SessionState::Active | SessionState::Processing)
    }

    /// Check if the session can transition to a new state
    pub fn can_transition_to(&self, new_state: SessionState) -> bool {
        use SessionState::*;
        match (self, new_state) {
            (Initializing, Active) => true,
            (Active, Processing) => true,
            (Active, Paused) => true,
            (Active, Closing) => true,
            (Processing, Active) => true,
            (Processing, Error) => true,
            (Paused, Active) => true,
            (Paused, Closing) => true,
            (Closing, Closed) => true,
            (Closed, _) => false,
            (Expired, _) => false,
            (Error, Closing) => true,
            (s1, s2) if s1 == s2 => true, // Same state is always valid
            _ => false,
        }
    }

    /// Check if this is a terminal state
    pub fn is_terminal(&self) -> bool {
        matches!(self, SessionState::Closed | SessionState::Expired)
    }
}

impl fmt::Display for SessionState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SessionState::Initializing => write!(f, "initializing"),
            SessionState::Active => write!(f, "active"),
            SessionState::Processing => write!(f, "processing"),
            SessionState::Paused => write!(f, "paused"),
            SessionState::Closing => write!(f, "closing"),
            SessionState::Closed => write!(f, "closed"),
            SessionState::Expired => write!(f, "expired"),
            SessionState::Error => write!(f, "error"),
        }
    }
}

/// Session configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionConfig {
    /// Maximum number of concurrent sessions
    pub max_concurrent: usize,
    /// Default session timeout
    pub default_timeout_secs: u64,
    /// Maximum session timeout
    pub max_timeout_secs: u64,
    /// Inactivity timeout
    pub inactivity_timeout_secs: u64,
    /// Maximum messages per session
    pub max_messages: usize,
    /// Maximum context tokens
    pub max_context_tokens: usize,
    /// Enable session persistence
    pub enable_persistence: bool,
    /// Persistence interval in seconds
    pub persistence_interval_secs: u64,
    /// Enable distributed sessions
    pub enable_distributed: bool,
    /// Session cache size
    pub cache_size: usize,
}

impl Default for SessionConfig {
    fn default() -> Self {
        Self {
            max_concurrent: 100,
            default_timeout_secs: 3600,
            max_timeout_secs: 86400,
            inactivity_timeout_secs: 300,
            max_messages: 1000,
            max_context_tokens: 8192,
            enable_persistence: true,
            persistence_interval_secs: 60,
            enable_distributed: false,
            cache_size: 10000,
        }
    }
}

/// Session metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionMetadata {
    /// Session ID
    pub id: SessionId,
    /// Session creation time
    pub created_at: Timestamp,
    /// Session last activity time
    pub last_activity: Timestamp,
    /// Session expiration time
    pub expires_at: Timestamp,
    /// User ID
    pub user_id: Option<String>,
    /// Organization ID
    pub org_id: Option<String>,
    /// Client information
    pub client_info: ClientInfo,
    /// Session tags
    pub tags: Vec<String>,
    /// Custom attributes
    pub attributes: HashMap<String, String>,
}

impl SessionMetadata {
    /// Create new metadata for a session
    pub fn new(id: SessionId, config: &SessionConfig) -> Self {
        let now = Timestamp::now();
        let expires = now
            .add(Duration::from_secs(config.default_timeout_secs))
            .unwrap_or(now);

        Self {
            id,
            created_at: now,
            last_activity: now,
            expires_at: expires,
            user_id: None,
            org_id: None,
            client_info: ClientInfo::default(),
            tags: Vec::new(),
            attributes: HashMap::new(),
        }
    }

    /// Update last activity timestamp
    pub fn touch(&mut self) {
        self.last_activity = Timestamp::now();
    }

    /// Check if the session has expired
    pub fn is_expired(&self) -> bool {
        Timestamp::now().is_after(self.expires_at)
    }

    /// Check if the session is inactive
    pub fn is_inactive(&self, timeout: Duration) -> bool {
        let now = Timestamp::now();
        match now.duration_since(self.last_activity) {
            Some(duration) => duration >= timeout,
            None => false,
        }
    }
}

/// Client information
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ClientInfo {
    /// Client IP address
    pub ip_address: Option<String>,
    /// User agent
    pub user_agent: Option<String>,
    /// Client version
    pub version: Option<String>,
    /// Platform
    pub platform: Option<String>,
    /// Device ID
    pub device_id: Option<String>,
}

/// Session statistics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SessionStats {
    /// Total messages
    pub message_count: u64,
    /// Total tokens used
    pub total_tokens: u64,
    /// Total turns
    pub turn_count: u64,
    /// Average response time in milliseconds
    pub avg_response_time_ms: f64,
    /// Error count
    pub error_count: u64,
    /// Cache hit rate
    pub cache_hit_rate: f64,
}

/// A conversation session
pub struct Session {
    /// Session metadata
    pub metadata: RwLock<SessionMetadata>,
    /// Current state
    pub state: RwLock<SessionState>,
    /// Message queue
    pub messages: Mutex<MessageQueue>,
    /// Security context
    pub security_context: SecurityContext,
    /// Session statistics
    pub stats: RwLock<SessionStats>,
    /// Configuration
    pub config: SessionConfig,
}

impl Session {
    /// Create a new session
    pub fn new(id: SessionId, config: SessionConfig, security_context: SecurityContext) -> Self {
        let metadata = SessionMetadata::new(id, &config);

        Self {
            metadata: RwLock::new(metadata),
            state: RwLock::new(SessionState::Initializing),
            messages: Mutex::new(MessageQueue::with_capacity(config.max_messages)),
            security_context,
            stats: RwLock::new(SessionStats::default()),
            config,
        }
    }

    /// Get the session ID
    pub fn id(&self) -> SessionId {
        self.metadata.read().id
    }

    /// Get current state
    pub fn state(&self) -> SessionState {
        *self.state.read()
    }

    /// Transition to a new state
    pub fn transition_to(&self, new_state: SessionState) -> CoreResult<()> {
        let mut state = self.state.write();

        if !state.can_transition_to(new_state) {
            return Err(CoreError::SessionError(SessionError::InvalidState {
                current_state: state.to_string(),
                expected_states: vec![new_state.to_string()],
            }));
        }

        debug!(
            session_id = %self.id(),
            from = %*state,
            to = %new_state,
            "Session state transition"
        );

        *state = new_state;
        Ok(())
    }

    /// Add a message to the session
    pub fn add_message(&self, message: Message) -> CoreResult<()> {
        let mut messages = self.messages.lock();

        if messages.len() >= self.config.max_messages {
            return Err(CoreError::MessageError(
                crate::error::MessageError::QueueFull {
                    current: messages.len(),
                    max: self.config.max_messages,
                },
            ));
        }

        messages.push(message);

        // Update metadata and stats
        self.metadata.write().touch();
        self.stats.write().message_count += 1;

        Ok(())
    }

    /// Get all messages
    pub fn get_messages(&self) -> Vec<Message> {
        self.messages.lock().clone().into_vec()
    }

    /// Get message count
    pub fn message_count(&self) -> usize {
        self.messages.lock().len()
    }

    /// Check if the session has expired
    pub fn is_expired(&self) -> bool {
        self.metadata.read().is_expired()
    }

    /// Check if the session is inactive
    pub fn is_inactive(&self) -> bool {
        self.metadata
            .read()
            .is_inactive(Duration::from_secs(self.config.inactivity_timeout_secs))
    }

    /// Touch the session (update last activity)
    pub fn touch(&self) {
        self.metadata.write().touch();
    }

    /// Get statistics snapshot
    pub fn stats(&self) -> SessionStats {
        self.stats.read().clone()
    }

    /// Update statistics
    pub fn update_stats(&self, f: impl FnOnce(&mut SessionStats)) {
        f(&mut *self.stats.write());
    }

    /// Close the session
    pub async fn close(&self) -> CoreResult<()> {
        self.transition_to(SessionState::Closing)?;
        self.transition_to(SessionState::Closed)?;
        info!(session_id = %self.id(), "Session closed");
        Ok(())
    }
}

impl fmt::Debug for Session {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Session")
            .field("id", &self.id())
            .field("state", &self.state())
            .field("message_count", &self.message_count())
            .finish()
    }
}

/// Session manager handles session lifecycle
pub struct SessionManager {
    /// Active sessions
    sessions: Arc<DashMap<SessionId, Arc<Session>>>,
    /// Configuration
    config: SessionConfig,
    /// Cache manager for persistence
    cache_manager: Arc<CacheManager>,
    /// Security engine
    security_engine: Arc<SecurityEngine>,
    /// Session counter
    session_count: AtomicU64,
    /// Cleanup handle
    cleanup_handle: Mutex<Option<tokio::task::JoinHandle<()>>>,
}

impl SessionManager {
    /// Create a new session manager
    pub async fn new(
        config: SessionConfig,
        cache_manager: Arc<CacheManager>,
        security_engine: Arc<SecurityEngine>,
    ) -> CoreResult<Self> {
        let manager = Self {
            sessions: Arc::new(DashMap::with_capacity(config.max_concurrent)),
            config,
            cache_manager,
            security_engine,
            session_count: AtomicU64::new(0),
            cleanup_handle: Mutex::new(None),
        };

        // Start cleanup task
        let sessions = manager.sessions.clone();
        let cleanup_interval = Duration::from_secs(30);
        let handle = tokio::spawn(async move {
            loop {
                tokio::time::sleep(cleanup_interval).await;

                let now = std::time::Instant::now();
                let mut expired = Vec::new();

                for entry in sessions.iter() {
                    let session = entry.value();
                    if session.is_expired() || session.is_inactive() {
                        expired.push(*entry.key());
                    }
                }

                for id in expired {
                    if let Some((_, session)) = sessions.remove(&id) {
                        if let Err(e) = session.close().await {
                            warn!(session_id = %id, error = %e, "Failed to close expired session");
                        } else {
                            debug!(session_id = %id, "Expired session cleaned up");
                        }
                    }
                }

                debug!(
                    expired_count = expired.len(),
                    elapsed_ms = now.elapsed().as_millis(),
                    "Session cleanup completed"
                );
            }
        });

        *manager.cleanup_handle.lock() = Some(handle);

        info!("SessionManager initialized");
        Ok(manager)
    }

    /// Create a new session
    #[instrument(skip(self, security_context))]
    pub async fn create_session(
        &self,
        security_context: SecurityContext,
    ) -> CoreResult<Arc<Session>> {
        // Check session limits
        let current = self.sessions.len();
        if current >= self.config.max_concurrent {
            return Err(CoreError::SessionError(SessionError::LimitExceeded {
                max: self.config.max_concurrent,
                current,
            }));
        }

        // Create session
        let id = SessionId::new();
        let session = Arc::new(Session::new(
            id,
            self.config.clone(),
            security_context,
        ));

        // Transition to active
        session.transition_to(SessionState::Active)?;

        // Store session
        self.sessions.insert(id, session.clone());
        self.session_count.fetch_add(1, Ordering::SeqCst);

        info!(session_id = %id, "Session created");
        Ok(session)
    }

    /// Get a session by ID
    pub fn get_session(&self, id: SessionId) -> CoreResult<Arc<Session>> {
        self.sessions
            .get(&id)
            .map(|entry| {
                let session = entry.value().clone();
                session.touch();
                session
            })
            .ok_or_else(|| {
                CoreError::SessionError(SessionError::NotFound(id.to_string()))
            })
    }

    /// Get or create a session
    pub async fn get_or_create_session(
        &self,
        id: Option<SessionId>,
        security_context: SecurityContext,
    ) -> CoreResult<Arc<Session>> {
        match id {
            Some(id) => self.get_session(id),
            None => self.create_session(security_context).await,
        }
    }

    /// Close a session
    pub async fn close_session(&self, id: SessionId) -> CoreResult<()> {
        if let Some((_, session)) = self.sessions.remove(&id) {
            session.close().await?;
        }
        Ok(())
    }

    /// Get the number of active sessions
    pub fn active_count(&self) -> usize {
        self.sessions.len()
    }

    /// Get total session count (including closed)
    pub fn total_count(&self) -> u64 {
        self.session_count.load(Ordering::SeqCst)
    }

    /// List active sessions with pagination
    pub fn list_sessions(
        &self,
        pagination: Pagination,
    ) -> Paginated<SessionMetadata> {
        let all: Vec<SessionMetadata> = self
            .sessions
            .iter()
            .map(|entry| entry.value().metadata.read().clone())
            .collect();

        let total = all.len() as u64;
        let offset = pagination.offset() as usize;
        let limit = pagination.limit() as usize;

        let items: Vec<SessionMetadata> = all
            .into_iter()
            .skip(offset)
            .take(limit)
            .collect();

        Paginated::new(items, total, pagination)
    }

    /// Get sessions by user ID
    pub fn get_sessions_by_user(
        &self,
        user_id: &str,
    ) -> Vec<Arc<Session>> {
        self.sessions
            .iter()
            .filter(|entry| {
                entry
                    .value()
                    .metadata
                    .read()
                    .user_id
                    .as_ref()
                    .map(|id| id == user_id)
                    .unwrap_or(false)
            })
            .map(|entry| entry.value().clone())
            .collect()
    }

    /// Close all sessions
    pub async fn close_all(&self,
    ) {
        let ids: Vec<SessionId> = self
            .sessions
            .iter()
            .map(|entry| *entry.key())
            .collect();

        for id in ids {
            if let Err(e) = self.close_session(id).await {
                warn!(session_id = %id, error = %e, "Failed to close session during shutdown");
            }
        }
    }

    /// Get session statistics
    pub fn get_stats(&self) -> SessionManagerStats {
        let active = self.active_count();
        let mut total_messages = 0u64;
        let mut total_tokens = 0u64;

        for entry in self.sessions.iter() {
            let stats = entry.value().stats();
            total_messages += stats.message_count;
            total_tokens += stats.total_tokens;
        }

        SessionManagerStats {
            active_sessions: active,
            total_sessions_created: self.total_count(),
            total_messages,
            total_tokens,
        }
    }
}

impl Drop for SessionManager {
    fn drop(&mut self) {
        if let Some(handle) = self.cleanup_handle.lock().take() {
            handle.abort();
        }
    }
}

impl fmt::Debug for SessionManager {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("SessionManager")
            .field("active_sessions", &self.active_count())
            .field("total_created", &self.total_count())
            .field("config", &self.config)
            .finish()
    }
}

/// Session manager statistics
#[derive(Debug, Clone, Default)]
pub struct SessionManagerStats {
    /// Number of active sessions
    pub active_sessions: usize,
    /// Total sessions ever created
    pub total_sessions_created: u64,
    /// Total messages across all sessions
    pub total_messages: u64,
    /// Total tokens used
    pub total_tokens: u64,
}

use std::fmt;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::security::SecurityConfig;

    #[tokio::test]
    async fn test_session_lifecycle() {
        let cache = Arc::new(CacheManager::new(Default::default()).await.unwrap());
        let security = Arc::new(SecurityEngine::new(Default::default()).await.unwrap());
        let manager = SessionManager::new(
            SessionConfig::default(),
            cache,
            security,
        ).await.unwrap();

        let ctx = SecurityContext::default();
        let session = manager.create_session(ctx).await.unwrap();

        assert_eq!(session.state(), SessionState::Active);
        assert_eq!(manager.active_count(), 1);

        manager.close_session(session.id()).await.unwrap();
        assert_eq!(manager.active_count(), 0);
    }

    #[test]
    fn test_session_state_transitions() {
        assert!(SessionState::Initializing.can_transition_to(SessionState::Active));
        assert!(SessionState::Active.can_transition_to(SessionState::Processing));
        assert!(SessionState::Active.can_transition_to(SessionState::Closing));
        assert!(!SessionState::Closed.can_transition_to(SessionState::Active));
    }

    #[tokio::test]
    async fn test_session_limits() {
        let cache = Arc::new(CacheManager::new(Default::default()).await.unwrap());
        let security = Arc::new(SecurityEngine::new(Default::default()).await.unwrap());
        let config = SessionConfig {
            max_concurrent: 2,
            ..Default::default()
        };

        let manager = SessionManager::new(config, cache, security).await.unwrap();

        let ctx = SecurityContext::default();
        let _s1 = manager.create_session(ctx.clone()).await.unwrap();
        let _s2 = manager.create_session(ctx.clone()).await.unwrap();

        assert!(manager.create_session(ctx).await.is_err());
    }

    #[tokio::test]
    async fn test_message_limits() {
        let cache = Arc::new(CacheManager::new(Default::default()).await.unwrap());
        let security = Arc::new(SecurityEngine::new(Default::default()).await.unwrap());
        let config = SessionConfig {
            max_messages: 2,
            ..Default::default()
        };

        let manager = SessionManager::new(config, cache, security).await.unwrap();

        let ctx = SecurityContext::default();
        let session = manager.create_session(ctx).await.unwrap();

        session.add_message(Message::default()).unwrap();
        session.add_message(Message::default()).unwrap();
        assert!(session.add_message(Message::default()).is_err());
    }
}
