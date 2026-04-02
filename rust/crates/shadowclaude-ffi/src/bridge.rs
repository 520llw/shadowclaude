//! Bridge between Rust and Python runtime
//!
//! Provides high-level interfaces for Python to interact with ShadowClaude

use shadowclaude_core::{CoreConfig, CoreRuntime};
use shadowclaude_runtime::{RuntimeConfig, RuntimeExecutor};
use std::sync::Arc;
use tokio::sync::Mutex;

/// Global runtime instance
static mut RUNTIME: Option<Arc<Mutex<CoreRuntime>>> = None;

/// Initialize the global runtime
pub async fn init_runtime() -> Result<(), String> {
    unsafe {
        if RUNTIME.is_some() {
            return Err("Runtime already initialized".to_string());
        }
        
        let config = CoreConfig::default();
        let runtime = CoreRuntime::new(config).await
            .map_err(|e| e.to_string())?;
        
        RUNTIME = Some(Arc::new(Mutex::new(runtime)));
        Ok(())
    }
}

/// Shutdown the global runtime
pub async fn shutdown_runtime() -> Result<(), String> {
    unsafe {
        if let Some(runtime) = RUNTIME.take() {
            let rt = runtime.lock().await;
            // Perform shutdown
        }
        Ok(())
    }
}

/// Get the global runtime instance
pub fn get_runtime() -> Option<Arc<Mutex<CoreRuntime>>> {
    unsafe { RUNTIME.clone() }
}

/// Core bridge for Python access
pub struct CoreBridge {
    runtime: Arc<Mutex<CoreRuntime>>,
}

impl CoreBridge {
    /// Create a new core bridge
    pub async fn new() -> Result<Self, String> {
        let runtime = get_runtime()
            .ok_or("Runtime not initialized")?;
        
        Ok(Self { runtime })
    }
    
    /// Get session manager
    pub async fn session_manager(&self) -> Arc<shadowclaude_core::SessionManager> {
        let rt = self.runtime.lock().await;
        rt.session_manager.clone()
    }
    
    /// Get dialogue manager
    pub async fn dialogue_manager(&self) -> Arc<shadowclaude_core::DialogueManager> {
        let rt = self.runtime.lock().await;
        rt.dialogue_manager.clone()
    }
    
    /// Get cache manager
    pub async fn cache_manager(&self) -> Arc<shadowclaude_core::CacheManager> {
        let rt = self.runtime.lock().await;
        rt.cache_manager.clone()
    }
    
    /// Get security engine
    pub async fn security_engine(&self) -> Arc<shadowclaude_core::SecurityEngine> {
        let rt = self.runtime.lock().await;
        rt.security_engine.clone()
    }
    
    /// Get runtime metrics
    pub async fn metrics(&self) -> shadowclaude_core::RuntimeMetrics {
        let rt = self.runtime.lock().await;
        rt.metrics()
    }
}

/// Runtime bridge for executor access
pub struct RuntimeBridge {
    executor: RuntimeExecutor,
}

impl RuntimeBridge {
    /// Create a new runtime bridge
    pub async fn new() -> Result<Self, std::io::Error> {
        let config = RuntimeConfig::default();
        let executor = RuntimeExecutor::new(config).await?;
        
        Ok(Self { executor })
    }
    
    /// Get executor metrics
    pub fn metrics(&self
    ) -> shadowclaude_runtime::ExecutorMetrics {
        self.executor.metrics()
    }
    
    /// Spawn a task
    pub fn spawn<F, T>(
        &self,
        future: F
    ) -> shadowclaude_runtime::RuntimeJoinHandle<T>
    where
        F: std::future::Future<Output = T> + Send + 'static,
        T: Send + 'static,
    {
        self.executor.spawn(future)
    }
}

/// Protocol bridge for WebSocket/MCP access
pub struct ProtocolBridge;

impl ProtocolBridge {
    /// Create a new protocol bridge
    pub fn new() -> Self {
        Self
    }
    
    /// Connect to WebSocket
    pub async fn connect_ws(&self,
        url: &str,
    ) -> Result<(), String> {
        // WebSocket connection logic
        Ok(())
    }
    
    /// Send MCP message
    pub async fn send_mcp(
        &self,
        message: &str,
    ) -> Result<String, String> {
        // MCP send logic
        Ok("response".to_string())
    }
}

impl Default for ProtocolBridge {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_bridge_creation() {
        // Note: This would need proper runtime initialization
    }
}
