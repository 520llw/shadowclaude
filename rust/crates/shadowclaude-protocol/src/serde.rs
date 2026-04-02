//! Serialization utilities
//!
//! High-performance serialization with support for:
//! - JSON
//! - Binary formats
//! - Compression
//! - Streaming

use bytes::{Buf, BufMut, Bytes, BytesMut};
use serde::{de::DeserializeOwned, Deserialize, Serialize};

/// Serialization format
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SerializationFormat {
    /// JSON format
    Json,
    /// MessagePack binary format
    MessagePack,
    /// CBOR binary format
    Cbor,
}

impl Default for SerializationFormat {
    fn default() -> Self {
        SerializationFormat::Json
    }
}

/// Serializer trait
pub trait Serializer {
    /// Serialize to bytes
    fn serialize<T: Serialize>(&self, value: &T
    ) -> crate::ProtocolResult<Bytes>;

    /// Deserialize from bytes
    fn deserialize<T: DeserializeOwned>(
        &self,
        data: &[ u8 ]
    ) -> crate::ProtocolResult<T>;
}

/// JSON serializer
pub struct JsonSerializer;

impl Serializer for JsonSerializer {
    fn serialize<T: Serialize>(
        &self,
        value: &T
    ) -> crate::ProtocolResult<Bytes> {
        let json = serde_json::to_vec(value)
            .map_err(|e| crate::ProtocolError::Serialization(e.to_string()))?;
        Ok(Bytes::from(json))
    }

    fn deserialize<T: DeserializeOwned>(
        &self,
        data: &[ u8 ]
    ) -> crate::ProtocolResult<T> {
        serde_json::from_slice(data)
            .map_err(|e| crate::ProtocolError::Deserialization(e.to_string()))
    }
}

/// MessagePack serializer (when feature enabled)
#[cfg(feature = "messagepack")]
pub struct MessagePackSerializer;

#[cfg(feature = "messagepack")]
impl Serializer for MessagePackSerializer {
    fn serialize<T: Serialize>(
        &self,
        value: &T
    ) -> crate::ProtocolResult<Bytes> {
        let data = rmp_serde::to_vec(value)
            .map_err(|e| crate::ProtocolError::Serialization(e.to_string()))?;
        Ok(Bytes::from(data))
    }

    fn deserialize<T: DeserializeOwned>(
        &self,
        data: &[ u8 ]
    ) -> crate::ProtocolResult<T> {
        rmp_serde::from_slice(data)
            .map_err(|e| crate::ProtocolError::Deserialization(e.to_string()))
    }
}

/// Compression type
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CompressionType {
    /// No compression
    None,
    /// Gzip compression
    Gzip,
    /// Brotli compression
    Brotli,
    /// Zstd compression
    Zstd,
}

impl Default for CompressionType {
    fn default() -> Self {
        CompressionType::None
    }
}

/// Compression utilities
pub struct Compressor;

impl Compressor {
    /// Compress data
    pub fn compress(
        data: &[ u8 ],
        compression: CompressionType
    ) -> crate::ProtocolResult<Bytes> {
        match compression {
            CompressionType::None => Ok(Bytes::copy_from_slice(data)),
            CompressionType::Gzip => Self::gzip_compress(data),
            CompressionType::Brotli => Self::brotli_compress(data),
            CompressionType::Zstd => Self::zstd_compress(data),
        }
    }

    /// Decompress data
    pub fn decompress(
        data: &[ u8 ],
        compression: CompressionType
    ) -> crate::ProtocolResult<Bytes> {
        match compression {
            CompressionType::None => Ok(Bytes::copy_from_slice(data)),
            CompressionType::Gzip => Self::gzip_decompress(data),
            CompressionType::Brotli => Self::brotli_decompress(data),
            CompressionType::Zstd => Self::zstd_decompress(data),
        }
    }

    fn gzip_compress(data: &[ u8 ]
    ) -> crate::ProtocolResult<Bytes> {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        use std::io::Write;

        let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
        encoder.write_all(data).map_err(|e| {
            crate::ProtocolError::Compression(e.to_string())
        })?;
        
        let compressed = encoder.finish().map_err(|e| {
            crate::ProtocolError::Compression(e.to_string())
        })?;
        
        Ok(Bytes::from(compressed))
    }

    fn gzip_decompress(data: &[ u8 ]
    ) -> crate::ProtocolResult<Bytes> {
        use flate2::read::GzDecoder;
        use std::io::Read;

        let mut decoder = GzDecoder::new(data);
        let mut decompressed = Vec::new();
        decoder.read_to_end(&mut decompressed).map_err(|e| {
            crate::ProtocolError::Compression(e.to_string())
        })?;
        
        Ok(Bytes::from(decompressed))
    }

    fn brotli_compress(data: &[ u8 ]
    ) -> crate::ProtocolResult<Bytes> {
        use brotli::CompressorWriter;
        use std::io::Write;

        let mut compressed = Vec::new();
        {
            let mut writer = CompressorWriter::new(&mut compressed, 4096, 11, 22);
            writer.write_all(data).map_err(|e| {
                crate::ProtocolError::Compression(e.to_string())
            })?;
        }
        
        Ok(Bytes::from(compressed))
    }

    fn brotli_decompress(data: &[ u8 ]
    ) -> crate::ProtocolResult<Bytes> {
        use brotli::Decompressor;
        use std::io::Read;

        let mut decompressed = Vec::new();
        let mut decompressor = Decompressor::new(data, 4096);
        decompressor.read_to_end(&mut decompressed).map_err(|e| {
            crate::ProtocolError::Compression(e.to_string())
        })?;
        
        Ok(Bytes::from(decompressed))
    }

    fn zstd_compress(data: &[ u8 ]
    ) -> crate::ProtocolResult<Bytes> {
        zstd::encode_all(data, 3)
            .map(Bytes::from)
            .map_err(|e| crate::ProtocolError::Compression(e.to_string()))
    }

    fn zstd_decompress(data: &[ u8 ]
    ) -> crate::ProtocolResult<Bytes> {
        zstd::decode_all(data)
            .map(Bytes::from)
            .map_err(|e| crate::ProtocolError::Compression(e.to_string()))
    }
}

/// Streaming serializer for large messages
pub struct StreamingSerializer {
    chunk_size: usize,
}

impl StreamingSerializer {
    /// Create a new streaming serializer
    pub fn new(chunk_size: usize) -> Self {
        Self { chunk_size }
    }

    /// Serialize to chunks
    pub fn serialize_chunks<T: Serialize>(
        &self,
        value: &T
    ) -> crate::ProtocolResult<Vec<Bytes>> {
        let data = serde_json::to_vec(value)
            .map_err(|e| crate::ProtocolError::Serialization(e.to_string()))?;

        let mut chunks = Vec::new();
        for chunk in data.chunks(self.chunk_size) {
            chunks.push(Bytes::copy_from_slice(chunk));
        }

        Ok(chunks)
    }
}

impl Default for StreamingSerializer {
    fn default() -> Self {
        Self::new(64 * 1024) // 64KB chunks
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_json_serializer() {
        let serializer = JsonSerializer;
        let data = serde_json::json!({"key": "value"});

        let bytes = serializer.serialize(&data).unwrap();
        let decoded: serde_json::Value = serializer.deserialize(&bytes).unwrap();

        assert_eq!(data, decoded);
    }

    #[test]
    fn test_gzip_compression() {
        let data = b"Hello, World! This is test data for compression.";
        
        let compressed = Compressor::gzip_compress(data).unwrap();
        assert!(compressed.len() < data.len() || compressed.len() <= data.len() + 20);

        let decompressed = Compressor::gzip_decompress(&compressed).unwrap();
        assert_eq!(&decompressed[..], &data[..]);
    }

    #[test]
    fn test_brotli_compression() {
        let data = b"Hello, World! This is test data for compression.";
        
        let compressed = Compressor::brotli_compress(data).unwrap();
        let decompressed = Compressor::brotli_decompress(&compressed).unwrap();
        
        assert_eq!(&decompressed[..], &data[..]);
    }

    #[test]
    fn test_zstd_compression() {
        let data = b"Hello, World! This is test data for compression.";
        
        let compressed = Compressor::zstd_compress(data).unwrap();
        let decompressed = Compressor::zstd_decompress(&compressed).unwrap();
        
        assert_eq!(&decompressed[..], &data[..]);
    }

    #[test]
    fn test_streaming_serializer() {
        let serializer = StreamingSerializer::new(10);
        let data = serde_json::json!({"key": "value with some longer content"});

        let chunks = serializer.serialize_chunks(&data).unwrap();
        assert!(chunks.len() > 1);

        let reconstructed: Vec<u8> = chunks.into_iter().flatten().collect();
        let decoded: serde_json::Value = serde_json::from_slice(&reconstructed).unwrap();

        assert_eq!(data, decoded);
    }
}
