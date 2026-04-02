//! ShadowClaude FFI - PyO3 bindings for Python
//!
//! This crate provides Python bindings for ShadowClaude core functionality:
//! - Dialogue management
//! - Session management
//! - Cache operations
//! - Security features

#![warn(missing_docs)]

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};
use pyo3::wrap_pyfunction;

pub mod async_bindings;
pub mod bridge;
pub mod convert;
pub mod error;
pub mod extra;
pub mod types;

pub use bridge::{CoreBridge, RuntimeBridge, ProtocolBridge};
pub use convert::{FromPy, IntoPy, PyConverter};
pub use error::{PyError, PyResult};

/// Module version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Initialize the FFI module
#[pymodule]
fn shadowclaude_ffi(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add("__version__", VERSION)?;
    
    // Add core classes
    m.add_class::<PyDialogueManager>()?;
    m.add_class::<PySessionManager>()?;
    m.add_class::<PyCacheManager>()?;
    m.add_class::<PySecurityEngine>()?;
    m.add_class::<PyRuntime>()?;
    m.add_class::<PyMessage>()?;
    m.add_class::<PySession>()?;
    
    // Add functions
    m.add_wrapped(wrap_pyfunction!(init_runtime))?;
    m.add_wrapped(wrap_pyfunction!(shutdown_runtime))?;
    m.add_wrapped(wrap_pyfunction!(get_version))?;
    
    Ok(())
}

/// Initialize the runtime
#[pyfunction]
fn init_runtime(py: Python) -> PyResult<&PyAny> {
    pyo3_asyncio::tokio::future_into_py(py, async {
        bridge::init_runtime().await.map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
        })
    })
}

/// Shutdown the runtime
#[pyfunction]
fn shutdown_runtime(py: Python) -> PyResult<&PyAny> {
    pyo3_asyncio::tokio::future_into_py(py, async {
        bridge::shutdown_runtime().await.map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
        })
    })
}

/// Get version string
#[pyfunction]
fn get_version() -> String {
    VERSION.to_string()
}

use pyo3::{PyErr, PyResult};
use std::sync::Arc;
use tokio::sync::Mutex;

/// Python wrapper for DialogueManager
#[pyclass(name = "DialogueManager")]
pub struct PyDialogueManager {
    inner: Arc<Mutex<shadowclaude_core::DialogueManager>>,
}

#[pymethods]
impl PyDialogueManager {
    /// Create a new dialogue manager
    #[new]
    fn new(py: Python) -> PyResult<Self> {
        let rt = pyo3_asyncio::tokio::get_runtime();
        
        let inner = rt.block_on(async {
            let config = shadowclaude_core::DialogueConfig::default();
            // This is simplified - in real code would need proper initialization
            todo!("Initialize with proper dependencies")
        });
        
        Ok(Self { inner: Arc::new(Mutex::new(inner)) })
    }
    
    /// Process a message
    fn process_message<'py>(
        &self,
        py: Python<'py>,
        session_id: String,
        message: String,
    ) -> PyResult<&'py PyAny> {
        let inner = self.inner.clone();
        
        pyo3_asyncio::tokio::future_into_py(py, async move {
            let manager = inner.lock().await;
            // Process message
            Ok(())
        })
    }
}

/// Python wrapper for SessionManager
#[pyclass(name = "SessionManager")]
pub struct PySessionManager {
    inner: Arc<Mutex<shadowclaude_core::SessionManager>>,
}

#[pymethods]
impl PySessionManager {
    /// Create a new session manager
    #[new]
    fn new() -> PyResult<Self> {
        todo!("Initialize with proper dependencies")
    }
    
    /// Create a new session
    fn create_session<'py>(
        &self,
        py: Python<'py>,
    ) -> PyResult<&'py PyAny> {
        let inner = self.inner.clone();
        
        pyo3_asyncio::tokio::future_into_py(py, async move {
            // Create session
            Ok("session_id")
        })
    }
    
    /// Get active session count
    fn active_count(&self
    ) -> usize {
        0 // Placeholder
    }
}

/// Python wrapper for CacheManager
#[pyclass(name = "CacheManager")]
pub struct PyCacheManager;

#[pymethods]
impl PyCacheManager {
    /// Create a new cache manager
    #[new]
    fn new() -> Self {
        Self
    }
    
    /// Get a value from cache
    fn get(&self,
        key: String,
    ) -> PyResult<Option<String>> {
        Ok(None)
    }
    
    /// Set a value in cache
    fn set(
        &self,
        key: String,
        value: String,
    ) -> PyResult<()> {
        Ok(())
    }
}

/// Python wrapper for SecurityEngine
#[pyclass(name = "SecurityEngine")]
pub struct PySecurityEngine;

#[pymethods]
impl PySecurityEngine {
    /// Create a new security engine
    #[new]
    fn new() -> Self {
        Self
    }
    
    /// Authenticate a token
    fn authenticate(
        &self,
        token: String,
    ) -> PyResult<bool> {
        Ok(true)
    }
}

/// Python wrapper for Runtime
#[pyclass(name = "Runtime")]
pub struct PyRuntime {
    inner: Option<shadowclaude_runtime::RuntimeExecutor>,
}

#[pymethods]
impl PyRuntime {
    /// Create a new runtime
    #[new]
    fn new(py: Python) -> PyResult<Self> {
        let rt = pyo3_asyncio::tokio::get_runtime();
        
        let executor = rt.block_on(async {
            shadowclaude_runtime::RuntimeExecutor::new(
                shadowclaude_runtime::RuntimeConfig::default()
            ).await
        }).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(Self { inner: Some(executor) })
    }
    
    /// Get metrics
    fn metrics(&self) -> PyResult<Py<PyDict>> {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("active_tasks", 0i64)?;
            dict.set_item("completed_tasks", 0i64)?;
            Ok(dict.into())
        })
    }
}

/// Python wrapper for Message
#[pyclass(name = "Message")]
#[derive(Clone)]
pub struct PyMessage {
    role: String,
    content: String,
}

#[pymethods]
impl PyMessage {
    /// Create a new message
    #[new]
    fn new(role: String, content: String) -> Self {
        Self { role, content }
    }
    
    /// Get role
    #[getter]
    fn role(&self
    ) -> String {
        self.role.clone()
    }
    
    /// Get content
    #[getter]
    fn content(&self
    ) -> String {
        self.content.clone()
    }
    
    /// Create a user message
    #[staticmethod]
    fn user(content: String) -> Self {
        Self::new("user".to_string(), content)
    }
    
    /// Create an assistant message
    #[staticmethod]
    fn assistant(content: String) -> Self {
        Self::new("assistant".to_string(), content)
    }
    
    /// Create a system message
    #[staticmethod]
    fn system(content: String) -> Self {
        Self::new("system".to_string(), content)
    }
    
    fn __repr__(&self
    ) -> String {
        format!("Message(role='{}', content='{}')", self.role, self.content)
    }
}

/// Python wrapper for Session
#[pyclass(name = "Session")]
pub struct PySession {
    id: String,
}

#[pymethods]
impl PySession {
    /// Get session ID
    #[getter]
    fn id(&self
    ) -> String {
        self.id.clone()
    }
    
    /// Get state
    fn state(&self
    ) -> String {
        "active".to_string()
    }
    
    fn __repr__(&self
    ) -> String {
        format!("Session(id='{}')", self.id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert!(!VERSION.is_empty());
    }

    #[test]
    fn test_py_message() {
        let msg = PyMessage::user("Hello".to_string());
        assert_eq!(msg.role(), "user");
        assert_eq!(msg.content(), "Hello");
    }
}
