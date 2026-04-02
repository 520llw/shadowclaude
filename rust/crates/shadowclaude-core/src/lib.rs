//! ShadowClaude Core Runtime
//! 
//! This crate provides the core runtime for ShadowClaude, including:
//! - Dialogue state machine (TAOR cycle)
//! - Session management
//! - Message queue and streaming
//! - Six-layer defense security system
//! - Prompt cache management
//!
//! # Architecture
//!
//! The core runtime is built around several key components:
//!
//! - `DialogueManager`: Manages the TAOR (Think-Act-Observe-Reflect) dialogue cycle
//! - `SessionManager`: Handles conversation session lifecycle
//! - `SecurityEngine`: Implements the six-layer defense security model
//! - `CacheManager`: Manages prompt caching with LRU and TTL strategies
//! - `MessageRouter`: Routes messages between components
//!
//! # Example
//!
//! ```rust
//! use shadowclaude_core::{DialogueManager, SessionConfig};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let config = SessionConfig::default();
//!     let manager = DialogueManager::new(config).await?;
//!     // ... use manager
//!     Ok(())
//! }
//! ```

#![warn(missing_docs)]
#![warn(rust_2018_idioms)]
#![allow(async_fn_in_trait)]

pub mod cache;
pub mod dialogue;
pub mod error;
pub mod message;
pub mod security;
pub mod session;
pub mod types;

// Re-export commonly used types
pub use cache::{CacheConfig, CacheManager, CacheStrategy};
pub use dialogue::{DialogueManager, DialogueState, TaorCycle, TurnConfig};
pub use error::{CoreError, CoreResult, ErrorContext, ErrorSeverity};
pub use message::{Message, MessageContent, MessageId, MessagePriority, MessageQueue};
pub use security::{Permission, SecurityContext, SecurityEngine, SecurityLevel};
pub use session::{Session, SessionConfig, SessionId, SessionManager, SessionState};
pub use types::*;

use once_cell::sync::Lazy;
use std::sync::Arc;
use tracing::info;

/// Global initialization flag
static INIT: Lazy<std::sync::atomic::AtomicBool> = 
    Lazy::new(|| std::sync::atomic::AtomicBool::new(false));

/// Initialize the core runtime
///
/// This should be called once before using any core functionality.
/// It sets up tracing, initializes global state, and validates configurations.
///
/// # Errors
///
/// Returns an error if initialization fails or if called more than once
/// without calling `shutdown()` first.
pub async fn init() -> CoreResult<()> {
    if INIT.swap(true, std::sync::atomic::Ordering::SeqCst) {
        return Err(CoreError::AlreadyInitialized);
    }

    // Initialize tracing
    let subscriber = tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .with_target(true)
        .with_thread_ids(true)
        .with_line_number(true)
        .compact()
        .finish();

    tracing::subscriber::set_global_default(subscriber)
        .map_err(|e| CoreError::InitializationFailed(e.to_string()))?;

    info!("ShadowClaude Core runtime initialized");
    Ok(())
}

/// Shutdown the core runtime
///
/// Cleans up global resources and resets the initialization state.
/// Should be called when the application is shutting down.
pub async fn shutdown() {
    INIT.store(false, std::sync::atomic::Ordering::SeqCst);
    info!("ShadowClaude Core runtime shutdown complete");
}

/// Check if the core runtime is initialized
pub fn is_initialized() -> bool {
    INIT.load(std::sync::atomic::Ordering::SeqCst)
}

/// Core runtime handle
///
/// Provides access to all core components in a unified interface.
#[derive(Debug, Clone)]
pub struct CoreRuntime {
    /// Session manager instance
    pub session_manager: Arc<SessionManager>,
    /// Dialogue manager instance
    pub dialogue_manager: Arc<DialogueManager>,
    /// Cache manager instance
    pub cache_manager: Arc<CacheManager>,
    /// Security engine instance
    pub security_engine: Arc<SecurityEngine>,
}

impl CoreRuntime {
    /// Create a new core runtime with the given configuration
    ///
    /// # Arguments
    ///
    /// * `config` - The core runtime configuration
    ///
    /// # Errors
    ///
    /// Returns an error if any component fails to initialize
    pub async fn new(config: CoreConfig) -> CoreResult<Self> {
        if !is_initialized() {
            init().await?;
        }

        let cache_manager = Arc::new(CacheManager::new(config.cache).await?);
        let security_engine = Arc::new(SecurityEngine::new(config.security).await?);
        let session_manager = Arc::new(SessionManager::new(
            config.session,
            cache_manager.clone(),
            security_engine.clone(),
        ).await?);
        let dialogue_manager = Arc::new(DialogueManager::new(
            config.dialogue,
            session_manager.clone(),
            cache_manager.clone(),
        ).await?);

        info!("CoreRuntime created successfully");

        Ok(Self {
            session_manager,
            dialogue_manager,
            cache_manager,
            security_engine,
        })
    }

    /// Get the current runtime metrics
    pub fn metrics(&self) -> RuntimeMetrics {
        RuntimeMetrics {
            active_sessions: self.session_manager.active_count(),
            cache_hit_rate: self.cache_manager.hit_rate(),
            security_events: self.security_engine.event_count(),
            memory_usage: self.cache_manager.memory_usage(),
        }
    }
}

/// Core runtime configuration
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CoreConfig {
    /// Session configuration
    pub session: SessionConfig,
    /// Dialogue configuration
    pub dialogue: dialogue::DialogueConfig,
    /// Cache configuration
    pub cache: CacheConfig,
    /// Security configuration
    pub security: security::SecurityConfig,
}

impl Default for CoreConfig {
    fn default() -> Self {
        Self {
            session: SessionConfig::default(),
            dialogue: dialogue::DialogueConfig::default(),
            cache: CacheConfig::default(),
            security: security::SecurityConfig::default(),
        }
    }
}

/// Runtime metrics snapshot
#[derive(Debug, Clone, Copy, Default)]
pub struct RuntimeMetrics {
    /// Number of active sessions
    pub active_sessions: usize,
    /// Cache hit rate (0.0 to 1.0)
    pub cache_hit_rate: f64,
    /// Number of security events
    pub security_events: u64,
    /// Memory usage in bytes
    pub memory_usage: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_init_shutdown() {
        // Reset init state
        INIT.store(false, std::sync::atomic::Ordering::SeqCst);
        
        assert!(!is_initialized());
        init().await.unwrap();
        assert!(is_initialized());
        
        // Second init should fail
        assert!(init().await.is_err());
        
        shutdown().await;
        assert!(!is_initialized());
    }

    #[test]
    fn test_core_config_default() {
        let config = CoreConfig::default();
        assert_eq!(config.session.max_concurrent, 100);
    }

    #[tokio::test]
    async fn test_core_runtime_creation() {
        INIT.store(false, std::sync::atomic::Ordering::SeqCst);
        
        let config = CoreConfig::default();
        let runtime = CoreRuntime::new(config).await;
        assert!(runtime.is_ok());
        
        shutdown().await;
    }
}
