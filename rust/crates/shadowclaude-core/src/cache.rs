//! Cache management for ShadowClaude
//!
//! This module provides multi-layer caching with:
//! - LRU (Least Recently Used) eviction
//! - TTL (Time To Live) expiration
//! - Size-based eviction
//! - Prompt-aware caching for LLM contexts

use crate::{
    error::{CacheError, CoreError, CoreResult, ErrorContext, ErrorSeverity},
    types::*,
};
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{de::DeserializeOwned, Serialize};
use std::collections::{HashMap, VecDeque};
use std::hash::Hash;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tracing::{debug, error, info, trace, warn};

/// Cache key type
pub type CacheKey = String;

/// Cache strategy enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CacheStrategy {
    /// LRU eviction
    Lru,
    /// TTL expiration
    Ttl,
    /// LRU + TTL combined
    LruTtl,
    /// Size-based eviction
    SizeBased,
    /// Prompt-aware caching
    Prompt,
}

impl Default for CacheStrategy {
    fn default() -> Self {
        CacheStrategy::LruTtl
    }
}

/// Cache configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    /// Maximum cache size in bytes
    pub max_size_bytes: usize,
    /// Maximum number of entries
    pub max_entries: usize,
    /// Default TTL in seconds
    pub default_ttl_secs: u64,
    /// Eviction batch size
    pub eviction_batch_size: usize,
    /// Enable statistics tracking
    pub track_stats: bool,
    /// Cleanup interval in seconds
    pub cleanup_interval_secs: u64,
    /// Default strategy
    pub default_strategy: CacheStrategy,
    /// Compression threshold in bytes
    pub compression_threshold: usize,
    /// Enable compression
    pub enable_compression: bool,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            max_size_bytes: 100 * 1024 * 1024, // 100MB
            max_entries: 100_000,
            default_ttl_secs: 3600,
            eviction_batch_size: 100,
            track_stats: true,
            cleanup_interval_secs: 60,
            default_strategy: CacheStrategy::LruTtl,
            compression_threshold: 1024,
            enable_compression: true,
        }
    }
}

/// Cache entry metadata
#[derive(Debug, Clone)]
struct EntryMeta {
    /// Entry size in bytes
    size: usize,
    /// Creation timestamp
    created_at: Instant,
    /// Last access timestamp
    last_access: Instant,
    /// Expiration time
    expires_at: Option<Instant>,
    /// Access count
    access_count: AtomicU64,
    /// Hit count
    hit_count: AtomicU64,
}

impl EntryMeta {
    fn new(size: usize, ttl: Option<Duration>) -> Self {
        let now = Instant::now();
        Self {
            size,
            created_at: now,
            last_access: now,
            expires_at: ttl.map(|d| now + d),
            access_count: AtomicU64::new(0),
            hit_count: AtomicU64::new(0),
        }
    }

    fn is_expired(&self) -> bool {
        self.expires_at
            .map(|exp| Instant::now() > exp)
            .unwrap_or(false)
    }

    fn touch(&mut self) {
        self.last_access = Instant::now();
        self.access_count.fetch_add(1, Ordering::Relaxed);
    }

    fn record_hit(&self) {
        self.hit_count.fetch_add(1, Ordering::Relaxed);
    }
}

/// Cache entry with type erasure
struct CacheEntry {
    /// Serialized data
    data: Vec<u8>,
    /// Metadata
    meta: RwLock<EntryMeta>,
    /// Is compressed
    compressed: bool,
}

impl CacheEntry {
    fn new(data: Vec<u8>, ttl: Option<Duration>, compressed: bool) -> Self {
        let size = data.len();
        Self {
            data,
            meta: RwLock::new(EntryMeta::new(size, ttl)),
            compressed,
        }
    }

    fn size(&self) -> usize {
        self.data.len()
    }

    fn is_expired(&self) -> bool {
        self.meta.read().is_expired()
    }

    fn touch(&self) {
        self.meta.write().touch();
    }

    fn record_hit(&self) {
        self.meta.read().record_hit();
    }
}

/// LRU tracker for cache entries
struct LruTracker {
    /// Ordered list of keys by recency
    order: RwLock<VecDeque<CacheKey>>,
    /// Key positions for O(1) removal
    positions: DashMap<CacheKey, usize>,
}

impl LruTracker {
    fn new() -> Self {
        Self {
            order: RwLock::new(VecDeque::new()),
            positions: DashMap::new(),
        }
    }

    fn record_access(&self, key: &CacheKey) {
        // Remove old position if exists
        if let Some((_, _)) = self.positions.remove(key) {
            // Note: We don't actually remove from order here for performance
            // The cleanup process will handle stale entries
        }

        // Add to front
        let mut order = self.order.write();
        order.push_front(key.clone());
        self.positions.insert(key.clone(), 0);

        // Update positions
        for (i, k) in order.iter().enumerate() {
            self.positions.insert(k.clone(), i);
        }
    }

    fn get_lru_keys(&self, n: usize) -> Vec<CacheKey> {
        let order = self.order.read();
        order.iter().rev().take(n).cloned().collect()
    }

    fn remove(&self, key: &CacheKey) {
        self.positions.remove(key);
    }
}

/// Cache statistics
#[derive(Debug, Clone, Default)]
pub struct CacheStats {
    /// Total entries
    pub entries: usize,
    /// Total size in bytes
    pub total_size: usize,
    /// Cache hits
    pub hits: u64,
    /// Cache misses
    pub misses: u64,
    /// Evictions
    pub evictions: u64,
    /// Expirations
    pub expirations: u64,
    /// Hit rate
    pub hit_rate: f64,
    /// Average entry size
    pub avg_entry_size: usize,
}

/// Prompt cache entry for LLM contexts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptCacheEntry {
    /// Prompt hash
    pub prompt_hash: String,
    /// Prompt text
    pub prompt: String,
    /// Cached response
    pub response: String,
    /// Token count
    pub token_count: usize,
    /// Model identifier
    pub model: String,
    /// Created at
    pub created_at: Timestamp,
}

/// Cache manager
pub struct CacheManager {
    /// Configuration
    config: CacheConfig,
    /// Main cache storage
    storage: DashMap<CacheKey, Arc<CacheEntry>>,
    /// LRU tracker
    lru: LruTracker,
    /// Current size in bytes
    current_size: AtomicU64,
    /// Statistics
    stats: RwLock<CacheStats>,
    /// Cleanup handle
    cleanup_handle: RwLock<Option<tokio::task::JoinHandle<()>>>,
    /// Prompt cache (separate for efficiency)
    prompt_cache: DashMap<String, PromptCacheEntry>,
}

impl CacheManager {
    /// Create a new cache manager
    pub async fn new(config: CacheConfig) -> CoreResult<Self> {
        let manager = Self {
            config,
            storage: DashMap::with_capacity(config.max_entries),
            lru: LruTracker::new(),
            current_size: AtomicU64::new(0),
            stats: RwLock::new(CacheStats::default()),
            cleanup_handle: RwLock::new(None),
            prompt_cache: DashMap::new(),
        };

        // Start cleanup task
        let storage = manager.storage.clone();
        let interval = Duration::from_secs(config.cleanup_interval_secs);
        let max_entries = config.max_entries;
        let max_size = config.max_size_bytes;
        let current_size = manager.current_size.clone();
        let stats = manager.stats.clone();

        let handle = tokio::spawn(async move {
            loop {
                tokio::time::sleep(interval).await;

                let mut expired_count = 0u64;
                let mut removed_size = 0usize;

                // Remove expired entries
                storage.retain(|_, entry| {
                    if entry.is_expired() {
                        expired_count += 1;
                        removed_size += entry.size();
                        false
                    } else {
                        true
                    }
                });

                // Update size
                current_size.fetch_sub(removed_size as u64, Ordering::Relaxed);

                // Update stats
                if expired_count > 0 {
                    let mut s = stats.write();
                    s.entries = storage.len();
                    s.total_size = current_size.load(Ordering::Relaxed) as usize;
                    s.expirations += expired_count;
                }

                trace!(
                    expired = expired_count,
                    remaining = storage.len(),
                    "Cache cleanup completed"
                );
            }
        });

        *manager.cleanup_handle.write() = Some(handle);

        info!("CacheManager initialized");
        Ok(manager)
    }

    /// Store a value in the cache
    pub fn set<T: Serialize>(
        &self,
        key: impl Into<CacheKey>,
        value: &T,
        ttl: Option<Duration>,
    ) -> CoreResult<()> {
        let key: CacheKey = key.into();

        // Serialize
        let data = match serde_json::to_vec(value) {
            Ok(d) => d,
            Err(e) => {
                return Err(CoreError::CacheError(CacheError::SerializationFailed(
                    e.to_string(),
                )));
            }
        };

        // Compress if enabled and large enough
        let (final_data, compressed) = if self.config.enable_compression
            && data.len() > self.config.compression_threshold
        {
            use flate2::write::GzEncoder;
            use flate2::Compression;
            use std::io::Write;

            let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
            encoder.write_all(&data).map_err(|e| {
                CoreError::CacheError(CacheError::SerializationFailed(e.to_string()))
            })?;

            let compressed = encoder.finish().map_err(|e| {
                CoreError::CacheError(CacheError::SerializationFailed(e.to_string()))
            })?;

            (compressed, true)
        } else {
            (data, false)
        };

        let entry_size = final_data.len();

        // Check if we need to evict
        self.ensure_space(entry_size)?;

        // Create entry
        let entry = Arc::new(CacheEntry::new(
            final_data,
            ttl.or_else(|| Some(Duration::from_secs(self.config.default_ttl_secs))),
            compressed,
        ));

        // Update size
        self.current_size.fetch_add(entry_size as u64, Ordering::Relaxed);

        // Insert
        self.storage.insert(key.clone(), entry);
        self.lru.record_access(&key);

        // Update stats
        if self.config.track_stats {
            let mut stats = self.stats.write();
            stats.entries = self.storage.len();
            stats.total_size = self.current_size.load(Ordering::Relaxed) as usize;
        }

        trace!(key = %key, size = entry_size, "Cache entry set");
        Ok(())
    }

    /// Get a value from the cache
    pub fn get<T: DeserializeOwned>(
        &self,
        key: &str,
    ) -> CoreResult<Option<T>> {
        match self.storage.get(key) {
            Some(entry) => {
                // Check expiration
                if entry.is_expired() {
                    drop(entry);
                    self.storage.remove(key);
                    self.lru.remove(key);

                    let mut stats = self.stats.write();
                    stats.misses += 1;

                    return Ok(None);
                }

                // Update access tracking
                entry.touch();
                entry.record_hit();
                self.lru.record_access(&key.to_string());

                // Decompress if needed
                let data = if entry.compressed {
                    use flate2::read::GzDecoder;
                    use std::io::Read;

                    let mut decoder = GzDecoder::new(&entry.data[..]);
                    let mut decompressed = Vec::new();
                    decoder.read_to_end(&mut decompressed).map_err(|e| {
                        CoreError::CacheError(CacheError::DeserializationFailed(
                            e.to_string(),
                        ))
                    })?;
                    decompressed
                } else {
                    entry.data.clone()
                };

                // Deserialize
                let value = serde_json::from_slice(&data).map_err(|e| {
                    CoreError::CacheError(CacheError::DeserializationFailed(
                        e.to_string(),
                    ))
                })?;

                // Update stats
                if self.config.track_stats {
                    let mut stats = self.stats.write();
                    stats.hits += 1;
                    self.update_hit_rate(&mut stats);
                }

                trace!(key = %key, "Cache hit");
                Ok(Some(value))
            }
            None => {
                if self.config.track_stats {
                    let mut stats = self.stats.write();
                    stats.misses += 1;
                    self.update_hit_rate(&mut stats);
                }

                trace!(key = %key, "Cache miss");
                Ok(None)
            }
        }
    }

    /// Check if a key exists in the cache
    pub fn contains(&self,
        key: &str
    ) -> bool {
        self.storage.contains_key(key)
    }

    /// Remove a key from the cache
    pub fn remove(&self,
        key: &str
    ) -> bool {
        if let Some((_, entry)) = self.storage.remove(key) {
            self.current_size.fetch_sub(entry.size() as u64, Ordering::Relaxed);
            self.lru.remove(key);

            if self.config.track_stats {
                let mut stats = self.stats.write();
                stats.entries = self.storage.len();
                stats.total_size = self.current_size.load(Ordering::Relaxed) as usize;
            }

            trace!(key = %key, "Cache entry removed");
            true
        } else {
            false
        }
    }

    /// Clear all entries
    pub fn clear(&self
    ) {
        self.storage.clear();
        self.current_size.store(0, Ordering::Relaxed);

        if self.config.track_stats {
            let mut stats = self.stats.write();
            stats.entries = 0;
            stats.total_size = 0;
        }

        info!("Cache cleared");
    }

    /// Get cache statistics
    pub fn stats(&self) -> CacheStats {
        let mut stats = self.stats.read().clone();
        stats.entries = self.storage.len();
        stats.total_size = self.current_size.load(Ordering::Relaxed) as usize;
        if stats.entries > 0 {
            stats.avg_entry_size = stats.total_size / stats.entries;
        }
        stats
    }

    /// Get current hit rate
    pub fn hit_rate(&self) -> f64 {
        self.stats.read().hit_rate
    }

    /// Get memory usage in bytes
    pub fn memory_usage(&self) -> usize {
        self.current_size.load(Ordering::Relaxed) as usize
    }

    /// Get approximate entry count
    pub fn entry_count(&self) -> usize {
        self.storage.len()
    }

    /// Cache a prompt-response pair
    pub fn cache_prompt(
        &self,
        prompt: &str,
        response: &str,
        model: &str,
        token_count: usize,
    ) {
        use sha2::{Digest, Sha256};

        let mut hasher = Sha256::new();
        hasher.update(prompt.as_bytes());
        hasher.update(model.as_bytes());
        let hash = format!("{:x}", hasher.finalize());

        let entry = PromptCacheEntry {
            prompt_hash: hash.clone(),
            prompt: prompt.to_string(),
            response: response.to_string(),
            token_count,
            model: model.to_string(),
            created_at: Timestamp::now(),
        };

        self.prompt_cache.insert(hash, entry);
        trace!("Prompt cached");
    }

    /// Lookup cached prompt response
    pub fn lookup_prompt(
        &self,
        prompt: &str,
        model: &str,
    ) -> Option<PromptCacheEntry> {
        use sha2::{Digest, Sha256};

        let mut hasher = Sha256::new();
        hasher.update(prompt.as_bytes());
        hasher.update(model.as_bytes());
        let hash = format!("{:x}", hasher.finalize());

        self.prompt_cache.get(&hash).map(|e| e.clone())
    }

    /// Get prompt cache stats
    pub fn prompt_cache_stats(&self) -> (usize, usize) {
        (self.prompt_cache.len(), self.prompt_cache.iter().map(|e| e.token_count).sum())
    }

    /// Ensure there's enough space for new entry
    fn ensure_space(&self,
        needed: usize
    ) -> CoreResult<()> {
        let current = self.current_size.load(Ordering::Relaxed) as usize;

        if current + needed > self.config.max_size_bytes {
            // Need to evict
            let to_evict = self.lru.get_lru_keys(self.config.eviction_batch_size);
            let mut evicted = 0u64;
            let mut freed = 0usize;

            for key in to_evict {
                if let Some((_, entry)) = self.storage.remove(&key) {
                    freed += entry.size();
                    self.lru.remove(&key);
                    evicted += 1;

                    if current + needed - freed <= self.config.max_size_bytes {
                        break;
                    }
                }
            }

            self.current_size.fetch_sub(freed as u64, Ordering::Relaxed);

            if self.config.track_stats {
                let mut stats = self.stats.write();
                stats.evictions += evicted;
            }

            trace!(evicted = evicted, freed = freed, "Cache eviction performed");
        }

        // Check entry limit
        if self.storage.len() >= self.config.max_entries {
            return Err(CoreError::CacheError(CacheError::CacheFull {
                current_size: self.storage.len(),
                max_size: self.config.max_entries,
            }));
        }

        Ok(())
    }

    fn update_hit_rate(&self,
        stats: &mut CacheStats
    ) {
        let total = stats.hits + stats.misses;
        if total > 0 {
            stats.hit_rate = stats.hits as f64 / total as f64;
        }
    }
}

impl Drop for CacheManager {
    fn drop(&mut self) {
        if let Some(handle) = self.cleanup_handle.write().take() {
            handle.abort();
        }
    }
}

impl fmt::Debug for CacheManager {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let stats = self.stats();
        f.debug_struct("CacheManager")
            .field("entries", &stats.entries)
            .field("total_size", &stats.total_size)
            .field("hit_rate", &stats.hit_rate)
            .field("config", &self.config)
            .finish()
    }
}

use std::fmt;

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_cache_basic() {
        let cache = CacheManager::new(CacheConfig::default()).await.unwrap();

        let key = "test_key";
        let value = "test_value";

        cache.set(key, &value, None).unwrap();
        let retrieved: Option<String> = cache.get(key).unwrap();

        assert_eq!(retrieved, Some(value.to_string()));
    }

    #[tokio::test]
    async fn test_cache_expiration() {
        let cache = CacheManager::new(CacheConfig::default()).await.unwrap();

        let key = "expiring_key";
        let value = "value";

        cache.set(key, &value, Some(Duration::from_millis(10))).unwrap();

        let retrieved: Option<String> = cache.get(key).unwrap();
        assert_eq!(retrieved, Some(value.to_string()));

        tokio::time::sleep(Duration::from_millis(50)).await;

        let retrieved: Option<String> = cache.get(key).unwrap();
        assert_eq!(retrieved, None);
    }

    #[tokio::test]
    async fn test_cache_stats() {
        let cache = CacheManager::new(CacheConfig::default()).await.unwrap();

        cache.set("key1", &"value1", None).unwrap();
        cache.set("key2", &"value2", None).unwrap();

        let _: Option<String> = cache.get("key1").unwrap();
        let _: Option<String> = cache.get("key1").unwrap();
        let _: Option<String> = cache.get("nonexistent").unwrap();

        let stats = cache.stats();
        assert_eq!(stats.entries, 2);
        assert_eq!(stats.hits, 2);
        assert_eq!(stats.misses, 1);
    }

    #[tokio::test]
    async fn test_prompt_cache() {
        let cache = CacheManager::new(CacheConfig::default()).await.unwrap();

        let prompt = "What is the capital of France?";
        let response = "Paris";
        let model = "gpt-4";

        cache.cache_prompt(prompt, response, model, 10);

        let entry = cache.lookup_prompt(prompt, model);
        assert!(entry.is_some());
        assert_eq!(entry.unwrap().response, response);
    }

    #[tokio::test]
    async fn test_cache_eviction() {
        let config = CacheConfig {
            max_entries: 2,
            ..Default::default()
        };
        let cache = CacheManager::new(config).await.unwrap();

        cache.set("key1", &"value1", None).unwrap();
        cache.set("key2", &"value2", None).unwrap();
        cache.set("key3", &"value3", None).unwrap();

        assert!(cache.entry_count() <= 2);
    }
}
