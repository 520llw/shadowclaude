//! FFI-specific types
//!
//! Python-compatible type definitions

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// FFI configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FfiConfig {
    /// Enable async support
    pub enable_async: bool,
    /// Thread pool size
    pub thread_pool_size: usize,
    /// Enable tracing
    pub enable_tracing: bool,
}

impl Default for FfiConfig {
    fn default() -> Self {
        Self {
            enable_async: true,
            thread_pool_size: 4,
            enable_tracing: true,
        }
    }
}

/// FFI initialization options
#[derive(Debug, Clone)]
pub struct InitOptions {
    /// Core configuration
    pub core: shadowclaude_core::CoreConfig,
    /// Runtime configuration
    pub runtime: shadowclaude_runtime::RuntimeConfig,
    /// FFI configuration
    pub ffi: FfiConfig,
}

impl Default for InitOptions {
    fn default() -> Self {
        Self {
            core: shadowclaude_core::CoreConfig::default(),
            runtime: shadowclaude_runtime::RuntimeConfig::default(),
            ffi: FfiConfig::default(),
        }
    }
}

/// FFI constants
pub mod constants {
    /// Default timeout for Python operations (seconds)
    pub const DEFAULT_TIMEOUT_SECS: u64 = 30;
    
    /// Max message size for Python transfer (bytes)
    pub const MAX_MESSAGE_SIZE: usize = 10 * 1024 * 1024;
    
    /// API version
    pub const API_VERSION: &str = "1.0.0";
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffi_config_default() {
        let config = FfiConfig::default();
        assert!(config.enable_async);
        assert_eq!(config.thread_pool_size, 4);
    }
}
