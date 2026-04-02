//! Error handling for FFI
//!
//! Converts between Rust errors and Python exceptions

use pyo3::prelude::*;
use pyo3::exceptions;

/// FFI result type
pub type PyResult<T> = Result<T, PyError>;

/// FFI error type
#[derive(Debug)]
pub enum PyError {
    /// Runtime error
    Runtime(String),
    /// Value error
    Value(String),
    /// Type error
    Type(String),
    /// IO error
    Io(String),
    /// Not implemented
    NotImplemented(String),
}

impl std::fmt::Display for PyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PyError::Runtime(s) => write!(f, "Runtime error: {}", s),
            PyError::Value(s) => write!(f, "Value error: {}", s),
            PyError::Type(s) => write!(f, "Type error: {}", s),
            PyError::Io(s) => write!(f, "IO error: {}", s),
            PyError::NotImplemented(s) => write!(f, "Not implemented: {}", s),
        }
    }
}

impl std::error::Error for PyError {}

impl From<PyError> for PyErr {
    fn from(err: PyError) -> PyErr {
        match err {
            PyError::Runtime(s) => exceptions::PyRuntimeError::new_err(s),
            PyError::Value(s) => exceptions::PyValueError::new_err(s),
            PyError::Type(s) => exceptions::PyTypeError::new_err(s),
            PyError::Io(s) => exceptions::PyIOError::new_err(s),
            PyError::NotImplemented(s) => exceptions::PyNotImplementedError::new_err(s),
        }
    }
}

impl From<shadowclaude_core::CoreError> for PyError {
    fn from(err: shadowclaude_core::CoreError) -> Self {
        PyError::Runtime(err.to_string())
    }
}

impl From<std::io::Error> for PyError {
    fn from(err: std::io::Error) -> Self {
        PyError::Io(err.to_string())
    }
}

impl From<serde_json::Error> for PyError {
    fn from(err: serde_json::Error) -> Self {
        PyError::Value(err.to_string())
    }
}

impl From<String> for PyError {
    fn from(s: String) -> Self {
        PyError::Runtime(s)
    }
}

impl From<&str> for PyError {
    fn from(s: &str) -> Self {
        PyError::Runtime(s.to_string())
    }
}

/// Convert Result to PyResult
pub trait IntoPyResult<T> {
    /// Convert to PyResult
    fn into_py_result(self) -> PyResult<T>;
}

impl<T, E: Into<PyError>> IntoPyResult<T> for Result<T, E> {
    fn into_py_result(self) -> PyResult<T> {
        self.map_err(|e| e.into())
    }
}

/// Helper macro for Python error conversion
#[macro_export]
macro_rules! py_err {
    ($msg:expr) => {
        $crate::error::PyError::Runtime($msg.to_string())
    };
    ($fmt:expr, $($arg:tt)*) => {
        $crate::error::PyError::Runtime(format!($fmt, $($arg)*))
    };
}

/// Helper macro for value errors
#[macro_export]
macro_rules! py_value_err {
    ($msg:expr) => {
        $crate::error::PyError::Value($msg.to_string())
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_py_error_display() {
        let err = PyError::Runtime("test error".to_string());
        assert!(err.to_string().contains("test error"));
    }

    #[test]
    fn test_py_error_conversion() {
        let err: PyError = "test".into();
        assert!(matches!(err, PyError::Runtime(_)));
    }
}
