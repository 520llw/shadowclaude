//! Core types and primitives for ShadowClaude
//!
//! This module defines fundamental types used throughout the core runtime,
//! including identifiers, timestamps, and common data structures.

use serde::{Deserialize, Serialize};
use std::fmt;
use std::str::FromStr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// A unique identifier with type safety
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct TypedId<T> {
    /// The underlying UUID
    #[serde(with = "uuid_serde")]
    pub uuid: uuid::Uuid,
    /// Phantom marker for type safety
    #[serde(skip)]
    pub _marker: std::marker::PhantomData<T>,
}

impl<T> TypedId<T> {
    /// Create a new typed ID
    pub fn new() -> Self {
        Self {
            uuid: uuid::Uuid::new_v4(),
            _marker: std::marker::PhantomData,
        }
    }

    /// Create from an existing UUID
    pub fn from_uuid(uuid: uuid::Uuid) -> Self {
        Self {
            uuid,
            _marker: std::marker::PhantomData,
        }
    }

    /// Parse from a string
    pub fn parse(s: &str) -> Result<Self, uuid::Error> {
        Ok(Self::from_uuid(uuid::Uuid::parse_str(s)?))
    }

    /// Convert to string
    pub fn to_string(&self) -> String {
        self.uuid.to_string()
    }

    /// Get the raw UUID bytes
    pub fn as_bytes(&self) -> &[u8; 16] {
        self.uuid.as_bytes()
    }
}

impl<T> Default for TypedId<T> {
    fn default() -> Self {
        Self::new()
    }
}

impl<T> fmt::Display for TypedId<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.uuid)
    }
}

/// Marker types for ID specialization
pub mod markers {
    /// Session marker
    #[derive(Debug)]
    pub struct Session;

    /// Message marker
    #[derive(Debug)]
    pub struct Message;

    /// Turn marker
    #[derive(Debug)]
    pub struct Turn;

    /// Cache entry marker
    #[derive(Debug)]
    pub struct CacheEntry;

    /// User marker
    #[derive(Debug)]
    pub struct User;

    /// Organization marker
    #[derive(Debug)]
    pub struct Organization;
}

/// Timestamp with millisecond precision
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct Timestamp(u64);

impl Timestamp {
    /// Create a new timestamp from the current time
    pub fn now() -> Self {
        Self(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
        )
    }

    /// Create from milliseconds since epoch
    pub fn from_millis(ms: u64) -> Self {
        Self(ms)
    }

    /// Get milliseconds since epoch
    pub fn as_millis(&self) -> u64 {
        self.0
    }

    /// Get seconds since epoch
    pub fn as_secs(&self) -> u64 {
        self.0 / 1000
    }

    /// Convert to SystemTime
    pub fn to_system_time(&self) -> SystemTime {
        UNIX_EPOCH + Duration::from_millis(self.0)
    }

    /// Convert to chrono DateTime
    pub fn to_datetime(&self) -> chrono::DateTime<chrono::Utc> {
        chrono::DateTime::from_timestamp_millis(self.0 as i64)
            .unwrap_or_else(|| chrono::Utc::now())
    }

    /// Duration since another timestamp
    pub fn duration_since(&self, other: Timestamp) -> Option<Duration> {
        self.0.checked_sub(other.0).map(Duration::from_millis)
    }

    /// Add duration
    pub fn add(&self, duration: Duration) -> Option<Timestamp> {
        let millis = duration.as_millis() as u64;
        self.0.checked_add(millis).map(Timestamp)
    }

    /// Subtract duration
    pub fn sub(&self, duration: Duration) -> Option<Timestamp> {
        let millis = duration.as_millis() as u64;
        self.0.checked_sub(millis).map(Timestamp)
    }

    /// Check if this timestamp is before another
    pub fn is_before(&self, other: Timestamp) -> bool {
        self.0 < other.0
    }

    /// Check if this timestamp is after another
    pub fn is_after(&self, other: Timestamp) -> bool {
        self.0 > other.0
    }

    /// Check if this timestamp is within the given duration from now
    pub fn is_recent(&self, duration: Duration) -> bool {
        let now = Timestamp::now();
        now.0.saturating_sub(self.0) <= duration.as_millis() as u64
    }
}

impl Default for Timestamp {
    fn default() -> Self {
        Self::now()
    }
}

impl From<SystemTime> for Timestamp {
    fn from(st: SystemTime) -> Self {
        let millis = st
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;
        Self(millis)
    }
}

impl From<chrono::DateTime<chrono::Utc>> for Timestamp {
    fn from(dt: chrono::DateTime<chrono::Utc>) -> Self {
        Self(dt.timestamp_millis() as u64)
    }
}

/// Version with semantic versioning support
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct Version {
    /// Major version
    pub major: u64,
    /// Minor version
    pub minor: u64,
    /// Patch version
    pub patch: u64,
}

impl Version {
    /// Create a new version
    pub const fn new(major: u64, minor: u64, patch: u64) -> Self {
        Self {
            major,
            minor,
            patch,
        }
    }

    /// Parse from string
    pub fn parse(s: &str) -> Result<Self, VersionParseError> {
        let parts: Vec<&str> = s.split('.').collect();
        if parts.len() != 3 {
            return Err(VersionParseError::InvalidFormat);
        }

        let major = parts[0]
            .parse()
            .map_err(|_| VersionParseError::InvalidNumber)?;
        let minor = parts[1]
            .parse()
            .map_err(|_| VersionParseError::InvalidNumber)?;
        let patch = parts[2]
            .parse()
            .map_err(|_| VersionParseError::InvalidNumber)?;

        Ok(Self::new(major, minor, patch))
    }

    /// Check if this version is compatible with another (same major)
    pub fn is_compatible_with(&self, other: &Version) -> bool {
        self.major == other.major
    }

    /// Get the next major version
    pub fn next_major(&self) -> Self {
        Self::new(self.major + 1, 0, 0)
    }

    /// Get the next minor version
    pub fn next_minor(&self) -> Self {
        Self::new(self.major, self.minor + 1, 0)
    }

    /// Get the next patch version
    pub fn next_patch(&self) -> Self {
        Self::new(self.major, self.minor, self.patch + 1)
    }
}

impl Default for Version {
    fn default() -> Self {
        Self::new(0, 1, 0)
    }
}

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)
    }
}

/// Version parse error
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum VersionParseError {
    /// Invalid format
    InvalidFormat,
    /// Invalid number
    InvalidNumber,
}

impl fmt::Display for VersionParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            VersionParseError::InvalidFormat => {
                write!(f, "Version must be in format X.Y.Z")
            }
            VersionParseError::InvalidNumber => write!(f, "Version components must be valid numbers"),
        }
    }
}

impl std::error::Error for VersionParseError {}

/// A bounded string with maximum length
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct BoundedString<const MAX: usize> {
    inner: String,
}

impl<const MAX: usize> BoundedString<MAX> {
    /// Create a new bounded string
    pub fn new(s: impl Into<String>) -> Result<Self, String> {
        let inner: String = s.into();
        if inner.len() > MAX {
            return Err(format!(
                "String exceeds maximum length of {}: got {}",
                MAX,
                inner.len()
            ));
        }
        Ok(Self { inner })
    }

    /// Get the string content
    pub fn as_str(&self) -> &str {
        &self.inner
    }

    /// Get the length
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Try to append a string
    pub fn try_push(&mut self, s: &str) -> Result<(), String> {
        let new_len = self.inner.len() + s.len();
        if new_len > MAX {
            return Err(format!(
                "Appending would exceed maximum length of {}: would be {}",
                MAX, new_len
            ));
        }
        self.inner.push_str(s);
        Ok(())
    }
}

impl<const MAX: usize> AsRef<str> for BoundedString<MAX> {
    fn as_ref(&self) -> &str {
        &self.inner
    }
}

impl<const MAX: usize> Default for BoundedString<MAX> {
    fn default() -> Self {
        Self {
            inner: String::new(),
        }
    }
}

impl<const MAX: usize> fmt::Display for BoundedString<MAX> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.inner)
    }
}

/// Counter with atomic operations
#[derive(Debug)]
pub struct AtomicCounter {
    inner: AtomicU64,
}

impl AtomicCounter {
    /// Create a new counter starting at 0
    pub fn new() -> Self {
        Self {
            inner: AtomicU64::new(0),
        }
    }

    /// Create a new counter with an initial value
    pub fn with_initial(value: u64) -> Self {
        Self {
            inner: AtomicU64::new(value),
        }
    }

    /// Increment and return the new value
    pub fn increment(&self) -> u64 {
        self.inner.fetch_add(1, Ordering::SeqCst) + 1
    }

    /// Add a value and return the new value
    pub fn add(&self, value: u64) -> u64 {
        self.inner.fetch_add(value, Ordering::SeqCst) + value
    }

    /// Get the current value
    pub fn get(&self) -> u64 {
        self.inner.load(Ordering::SeqCst)
    }

    /// Set the value
    pub fn set(&self, value: u64) {
        self.inner.store(value, Ordering::SeqCst);
    }

    /// Reset to 0
    pub fn reset(&self) {
        self.inner.store(0, Ordering::SeqCst);
    }
}

impl Default for AtomicCounter {
    fn default() -> Self {
        Self::new()
    }
}

/// Rate limit configuration
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct RateLimit {
    /// Maximum requests allowed
    pub max_requests: u64,
    /// Time window in seconds
    pub window_secs: u64,
}

impl RateLimit {
    /// Create a new rate limit
    pub const fn new(max_requests: u64, window_secs: u64) -> Self {
        Self {
            max_requests,
            window_secs,
        }
    }

    /// Get the rate (requests per second)
    pub fn rate(&self) -> f64 {
        if self.window_secs == 0 {
            return f64::INFINITY;
        }
        self.max_requests as f64 / self.window_secs as f64
    }

    /// Check if a burst of requests is allowed
    pub fn allows_burst(&self, burst_size: u64) -> bool {
        burst_size <= self.max_requests
    }
}

impl Default for RateLimit {
    fn default() -> Self {
        Self::new(100, 60)
    }
}

/// Pagination parameters
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Pagination {
    /// Page number (0-indexed)
    pub page: u64,
    /// Items per page
    pub per_page: u64,
}

impl Pagination {
    /// Create new pagination
    pub const fn new(page: u64, per_page: u64) -> Self {
        Self { page, per_page }
    }

    /// Get the offset for database queries
    pub fn offset(&self) -> u64 {
        self.page * self.per_page
    }

    /// Get the limit for database queries
    pub fn limit(&self) -> u64 {
        self.per_page
    }

    /// Get the next page
    pub fn next(&self) -> Self {
        Self::new(self.page + 1, self.per_page)
    }

    /// Get the previous page
    pub fn prev(&self) -> Self {
        Self::new(self.page.saturating_sub(1), self.per_page)
    }

    /// Create a default pagination (first page, 20 items)
    pub fn default_small() -> Self {
        Self::new(0, 20)
    }

    /// Create a pagination for medium result sets (first page, 50 items)
    pub fn default_medium() -> Self {
        Self::new(0, 50)
    }

    /// Create a pagination for large result sets (first page, 100 items)
    pub fn default_large() -> Self {
        Self::new(0, 100)
    }
}

impl Default for Pagination {
    fn default() -> Self {
        Self::default_small()
    }
}

/// Paginated result wrapper
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Paginated<T> {
    /// The items
    pub items: Vec<T>,
    /// Total count
    pub total: u64,
    /// Current pagination
    pub pagination: Pagination,
    /// Whether there are more items
    pub has_more: bool,
}

impl<T> Paginated<T> {
    /// Create a new paginated result
    pub fn new(items: Vec<T>, total: u64, pagination: Pagination) -> Self {
        let has_more = pagination.offset() + items.len() as u64 < total;
        Self {
            items,
            total,
            pagination,
            has_more,
        }
    }

    /// Map over the items
    pub fn map<U, F>(self, f: F) -> Paginated<U>
    where
        F: FnMut(T) -> U,
    {
        Paginated {
            items: self.items.into_iter().map(f).collect(),
            total: self.total,
            pagination: self.pagination,
            has_more: self.has_more,
        }
    }

    /// Check if result is empty
    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    /// Get the number of items
    pub fn len(&self) -> usize {
        self.items.len()
    }
}

impl<T> Default for Paginated<T> {
    fn default() -> Self {
        Self {
            items: Vec::new(),
            total: 0,
            pagination: Pagination::default(),
            has_more: false,
        }
    }
}

/// Byte size with human-readable formatting
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ByteSize(pub u64);

impl ByteSize {
    /// Create from bytes
    pub const fn from_bytes(bytes: u64) -> Self {
        Self(bytes)
    }

    /// Create from kilobytes
    pub const fn from_kb(kb: u64) -> Self {
        Self(kb * 1024)
    }

    /// Create from megabytes
    pub const fn from_mb(mb: u64) -> Self {
        Self(mb * 1024 * 1024)
    }

    /// Create from gigabytes
    pub const fn from_gb(gb: u64) -> Self {
        Self(gb * 1024 * 1024 * 1024)
    }

    /// Get the size in bytes
    pub fn as_bytes(&self) -> u64 {
        self.0
    }

    /// Get the size in kilobytes
    pub fn as_kb(&self) -> f64 {
        self.0 as f64 / 1024.0
    }

    /// Get the size in megabytes
    pub fn as_mb(&self) -> f64 {
        self.0 as f64 / (1024.0 * 1024.0)
    }

    /// Get the size in gigabytes
    pub fn as_gb(&self) -> f64 {
        self.0 as f64 / (1024.0 * 1024.0 * 1024.0)
    }

    /// Format as human-readable string
    pub fn human_readable(&self) -> String {
        const UNITS: &[(&str, u64)] = &[
            ("EB", 1024u64.pow(6)),
            ("PB", 1024u64.pow(5)),
            ("TB", 1024u64.pow(4)),
            ("GB", 1024u64.pow(3)),
            ("MB", 1024u64.pow(2)),
            ("KB", 1024u64.pow(1)),
            ("B", 1),
        ];

        let bytes = self.0;
        for (unit, threshold) in UNITS {
            if bytes >= *threshold {
                let value = bytes as f64 / *threshold as f64;
                return format!("{:.2} {}", value, unit);
            }
        }
        format!("{} B", bytes)
    }
}

impl Default for ByteSize {
    fn default() -> Self {
        Self(0)
    }
}

impl fmt::Display for ByteSize {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.human_readable())
    }
}

impl Serialize for ByteSize {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_u64(self.0)
    }
}

impl<'de> Deserialize<'de> for ByteSize {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let bytes = u64::deserialize(deserializer)?;
        Ok(Self(bytes))
    }
}

/// Token count for LLM context windows
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct TokenCount(pub usize);

impl TokenCount {
    /// Create a new token count
    pub const fn new(count: usize) -> Self {
        Self(count)
    }

    /// Get the count
    pub fn get(&self) -> usize {
        self.0
    }

    /// Add token counts
    pub fn add(&self, other: TokenCount) -> Self {
        Self(self.0 + other.0)
    }

    /// Subtract token counts
    pub fn sub(&self, other: TokenCount) -> Option<Self> {
        self.0.checked_sub(other.0).map(Self)
    }

    /// Check if within limit
    pub fn is_within_limit(&self, limit: TokenCount) -> bool {
        self.0 <= limit.0
    }

    /// Calculate percentage of limit used
    pub fn percentage_of(&self, limit: TokenCount) -> f64 {
        if limit.0 == 0 {
            return 0.0;
        }
        (self.0 as f64 / limit.0 as f64) * 100.0
    }
}

impl Default for TokenCount {
    fn default() -> Self {
        Self(0)
    }
}

impl fmt::Display for TokenCount {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} tokens", self.0)
    }
}

/// UUID serialization helper
mod uuid_serde {
    use serde::{Deserialize, Deserializer, Serializer};
    use uuid::Uuid;

    pub fn serialize<S>(uuid: &Uuid, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&uuid.to_string())
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Uuid, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        Uuid::parse_str(&s).map_err(serde::de::Error::custom)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_typed_id() {
        let id1: TypedId<markers::Session> = TypedId::new();
        let id2: TypedId<markers::Session> = TypedId::new();
        assert_ne!(id1.uuid, id2.uuid);

        let parsed = TypedId::<markers::Session>::parse(&id1.to_string()).unwrap();
        assert_eq!(id1.uuid, parsed.uuid);
    }

    #[test]
    fn test_timestamp() {
        let now = Timestamp::now();
        let later = Timestamp::now();
        assert!(later.as_millis() >= now.as_millis());

        let duration = Duration::from_secs(60);
        let future = now.add(duration).unwrap();
        assert!(future.as_millis() > now.as_millis());
    }

    #[test]
    fn test_version() {
        let v1 = Version::new(1, 2, 3);
        let v2 = Version::new(1, 2, 4);
        let v3 = Version::new(1, 3, 0);

        assert!(v1 < v2);
        assert!(v2 < v3);
        assert!(v1.is_compatible_with(&v2));
        assert!(!v1.is_compatible_with(&Version::new(2, 0, 0)));
    }

    #[test]
    fn test_bounded_string() {
        type ShortString = BoundedString<10>;

        let s = ShortString::new("hello").unwrap();
        assert_eq!(s.as_str(), "hello");

        let long = "this is way too long";
        assert!(ShortString::new(long).is_err());
    }

    #[test]
    fn test_atomic_counter() {
        let counter = AtomicCounter::new();
        assert_eq!(counter.get(), 0);

        assert_eq!(counter.increment(), 1);
        assert_eq!(counter.increment(), 2);
        assert_eq!(counter.get(), 2);

        counter.add(10);
        assert_eq!(counter.get(), 12);
    }

    #[test]
    fn test_byte_size() {
        let bs = ByteSize::from_gb(1);
        assert_eq!(bs.as_bytes(), 1024 * 1024 * 1024);
        assert_eq!(bs.as_gb(), 1.0);

        let readable = ByteSize::from_bytes(1536).human_readable();
        assert!(readable.contains("KB"));
    }

    #[test]
    fn test_token_count() {
        let t1 = TokenCount::new(100);
        let t2 = TokenCount::new(50);

        assert_eq!(t1.add(t2).get(), 150);
        assert_eq!(t1.sub(t2).unwrap().get(), 50);
        assert!(t1.is_within_limit(TokenCount::new(200)));
        assert!(!t1.is_within_limit(TokenCount::new(50)));
    }
}
