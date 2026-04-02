//! Type conversion between Rust and Python
//!
//! Provides bidirectional conversion for:
//! - Primitive types
//! - Collections
//! - Custom types
//! - Error handling

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString, PyInt, PyFloat, PyBool};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Trait for converting from Python types
pub trait FromPy<T>: Sized {
    /// Convert from Python type
    fn from_py(value: T) -> PyResult<Self>;
}

/// Trait for converting to Python types
pub trait IntoPy<T>: Sized {
    /// Convert to Python type
    fn into_py(self, py: Python) -> PyResult<T>;
}

/// Converter for complex types
pub struct PyConverter;

impl PyConverter {
    /// Convert Rust value to Python dict
    pub fn to_dict<T: Serialize>(
        value: &T,
        py: Python,
    ) -> PyResult<Py<PyDict>> {
        let json = serde_json::to_value(value).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())
        })?;
        
        Self::json_to_pydict(&json, py)
    }
    
    /// Convert JSON value to Python dict
    fn json_to_pydict(value: &serde_json::Value, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        
        if let serde_json::Value::Object(map) = value {
            for (k, v) in map {
                let py_value = Self::json_to_py(v, py)?;
                dict.set_item(k, py_value)?;
            }
        }
        
        Ok(dict.into())
    }
    
    /// Convert JSON value to Python object
    fn json_to_py(value: &serde_json::Value, py: Python) -> PyResult<PyObject> {
        match value {
            serde_json::Value::Null => Ok(py.None()),
            serde_json::Value::Bool(b) => Ok(b.to_object(py)),
            serde_json::Value::Number(n) => {
                if let Some(i) = n.as_i64() {
                    Ok(i.to_object(py))
                } else if let Some(f) = n.as_f64() {
                    Ok(f.to_object(py))
                } else {
                    Ok(py.None())
                }
            }
            serde_json::Value::String(s) => Ok(s.to_object(py)),
            serde_json::Value::Array(arr) => {
                let list = PyList::empty(py);
                for item in arr {
                    let py_item = Self::json_to_py(item, py)?;
                    list.append(py_item)?;
                }
                Ok(list.into())
            }
            serde_json::Value::Object(_) => {
                let dict = Self::json_to_pydict(value, py)?;
                Ok(dict.into())
            }
        }
    }
    
    /// Convert Python dict to Rust type
    pub fn from_dict<T: for<'de> Deserialize<'de>>(
        dict: &PyDict,
    ) -> PyResult<T> {
        let json = Self::pydict_to_json(dict)?;
        
        serde_json::from_value(json).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())
        })
    }
    
    /// Convert Python dict to JSON value
    fn pydict_to_json(dict: &PyDict) -> PyResult<serde_json::Value> {
        let mut map = serde_json::Map::new();
        
        for (key, value) in dict {
            let key_str: String = key.extract()?;
            let json_value = Self::py_to_json(value)?;
            map.insert(key_str, json_value);
        }
        
        Ok(serde_json::Value::Object(map))
    }
    
    /// Convert Python object to JSON value
    fn py_to_json(obj: &PyAny) -> PyResult<serde_json::Value> {
        if obj.is_none() {
            Ok(serde_json::Value::Null)
        } else if let Ok(b) = obj.downcast::<PyBool>() {
            Ok(serde_json::Value::Bool(b.is_true()))
        } else if let Ok(i) = obj.downcast::<PyInt>() {
            let n: i64 = i.extract()?;
            Ok(serde_json::Value::Number(n.into()))
        } else if let Ok(f) = obj.downcast::<PyFloat>() {
            let n: f64 = f.extract()?;
            Ok(serde_json::json!(n))
        } else if let Ok(s) = obj.downcast::<PyString>() {
            let str: String = s.extract()?;
            Ok(serde_json::Value::String(str))
        } else if let Ok(list) = obj.downcast::<PyList>() {
            let mut arr = Vec::new();
            for item in list {
                arr.push(Self::py_to_json(item)?);
            }
            Ok(serde_json::Value::Array(arr))
        } else if let Ok(dict) = obj.downcast::<PyDict>() {
            Self::pydict_to_json(dict)
        } else {
            Ok(serde_json::Value::Null)
        }
    }
}

// Implementations for primitive types

impl FromPy<&PyString> for String {
    fn from_py(value: &PyString) -> PyResult<Self> {
        value.extract()
    }
}

impl FromPy<&PyInt> for i64 {
    fn from_py(value: &PyInt) -> PyResult<Self> {
        value.extract()
    }
}

impl FromPy<&PyDict> for HashMap<String, String> {
    fn from_py(value: &PyDict) -> PyResult<Self> {
        let mut map = HashMap::new();
        for (k, v) in value {
            let key: String = k.extract()?;
            let val: String = v.extract()?;
            map.insert(key, val);
        }
        Ok(map)
    }
}

impl IntoPy<Py<PyDict>> for HashMap<String, String> {
    fn into_py(self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (k, v) in self {
            dict.set_item(k, v)?;
        }
        Ok(dict.into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_converter_basic() {
        pyo3::prepare_freethreaded_python();
        
        Python::with_gil(|py| {
            // Test dict conversion
            let dict = PyDict::new(py);
            dict.set_item("key", "value").unwrap();
            
            let json = PyConverter::pydict_to_json(dict).unwrap();
            assert!(json.is_object());
        });
    }
}
