//! Timeout management for async operations
//!
//! Provides:
//! - Configurable timeout policies
//! - Timeout groups
//! - Graceful timeout handling
//! - Deadline propagation

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::task::{Context, Poll, Waker};
use std::time::Duration;
use tokio::time::{Instant, Sleep};
use tracing::{debug, trace, warn};

/// Timeout configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeoutConfig {
    /// Default timeout duration
    pub default_timeout_secs: u64,
    /// Enable graceful timeout
    pub graceful_timeout: bool,
    /// Grace period after timeout
    pub grace_period_secs: u64,
    /// Global timeout limit
    pub max_timeout_secs: u64,
}

impl Default for TimeoutConfig {
    fn default() -> Self {
        Self {
            default_timeout_secs: 30,
            graceful_timeout: true,
            grace_period_secs: 5,
            max_timeout_secs: 300,
        }
    }
}

/// Timeout policy
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TimeoutPolicy {
    /// Cancel immediately on timeout
    Immediate,
    /// Wait for graceful shutdown
    Graceful,
    /// Extend timeout on activity
    ExtendOnActivity,
    /// No timeout
    None,
}

impl Default for TimeoutPolicy {
    fn default() -> Self {
        TimeoutPolicy::Graceful
    }
}

/// Timeout manager
pub struct TimeoutManager {
    /// Configuration
    config: TimeoutConfig,
    /// Active timeouts
    timeouts: dashmap::DashMap<u64, ActiveTimeout>,
    /// Timeout counter
    counter: AtomicU64,
    /// Timeout statistics
    stats: TimeoutStats,
}

/// Active timeout entry
#[derive(Debug)]
struct ActiveTimeout {
    /// Created at
    created_at: Instant,
    /// Expires at
    expires_at: Instant,
    /// Policy
    policy: TimeoutPolicy,
    /// Waker
    waker: Option<Waker>,
}

/// Timeout statistics
#[derive(Debug, Default)]
pub struct TimeoutStats {
    /// Total timeouts created
    pub total_timeouts: u64,
    /// Total timeouts triggered
    pub triggered_timeouts: u64,
    /// Total cancelled timeouts
    pub cancelled_timeouts: u64,
    /// Average timeout duration
    pub avg_timeout_ms: f64,
}

impl TimeoutManager {
    /// Create a new timeout manager
    pub fn new(config: TimeoutConfig) -> Self {
        Self {
            config,
            timeouts: dashmap::DashMap::new(),
            counter: AtomicU64::new(0),
            stats: TimeoutStats::default(),
        }
    }

    /// Create a timeout
    pub fn create_timeout(
        &self,
        duration: Duration,
        policy: TimeoutPolicy,
    ) -> Timeout {
        let id = self.counter.fetch_add(1, Ordering::SeqCst);
        let now = Instant::now();

        let active = ActiveTimeout {
            created_at: now,
            expires_at: now + duration,
            policy,
            waker: None,
        };

        self.timeouts.insert(id, active);
        self.stats.total_timeouts += 1;

        Timeout {
            id,
            manager: self,
            duration,
            policy,
        }
    }

    /// Create a timeout with default policy
    pub fn timeout(
        &self,
        duration: Duration
    ) -> Timeout {
        self.create_timeout(duration, self.config.default_timeout().into())
    }

    /// Cancel a timeout
    pub fn cancel_timeout(&self,
        id: u64
    ) {
        if self.timeouts.remove(&id).is_some() {
            self.stats.cancelled_timeouts += 1;
        }
    }

    /// Check if a timeout has expired
    pub fn check_timeout(
        &self,
        id: u64
    ) -> bool {
        if let Some(entry) = self.timeouts.get(&id) {
            if Instant::now() >= entry.expires_at {
                self.stats.triggered_timeouts += 1;
                return true;
            }
        }
        false
    }

    /// Get remaining time for a timeout
    pub fn remaining(
        &self,
        id: u64
    ) -> Option<Duration> {
        self.timeouts.get(&id).map(|entry| {
            let now = Instant::now();
            if entry.expires_at > now {
                entry.expires_at.duration_since(now)
            } else {
                Duration::ZERO
            }
        })
    }

    /// Extend a timeout
    pub fn extend(
        &self,
        id: u64,
        additional: Duration
    ) -> bool {
        if let Some(mut entry) = self.timeouts.get_mut(&id) {
            entry.expires_at += additional;
            if let Some(ref waker) = entry.waker {
                waker.wake_by_ref();
            }
            return true;
        }
        false
    }

    /// Get statistics
    pub fn stats(&self) -> &TimeoutStats {
        &self.stats
    }

    /// Create deadline
    pub fn deadline(
        &self,
        timeout: Duration
    ) -> Deadline {
        let now = Instant::now();
        Deadline {
            expires_at: now + timeout,
        }
    }
}

impl std::fmt::Debug for TimeoutManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TimeoutManager")
            .field("active_timeouts", &self.timeouts.len())
            .field("config", &self.config)
            .finish()
    }
}

/// Timeout future
pub struct Timeout<'a> {
    /// Timeout ID
    id: u64,
    /// Manager reference
    manager: &'a TimeoutManager,
    /// Duration
    duration: Duration,
    /// Policy
    policy: TimeoutPolicy,
}

impl<'a> Timeout<'a> {
    /// Cancel this timeout
    pub fn cancel(self
    ) {
        self.manager.cancel_timeout(self.id);
    }

    /// Get remaining time
    pub fn remaining(&self
    ) -> Option<Duration> {
        self.manager.remaining(self.id)
    }

    /// Extend this timeout
    pub fn extend(&self,
        additional: Duration
    ) -> bool {
        self.manager.extend(self.id, additional)
    }
}

impl<'a> Future for Timeout<'a> {
    type Output = ();

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        if self.manager.check_timeout(self.id) {
            Poll::Ready(())
        } else {
            // Store waker for notification
            if let Some(mut entry) = self.manager.timeouts.get_mut(&self.id) {
                entry.waker = Some(cx.waker().clone());
            }
            Poll::Pending
        }
    }
}

impl<'a> Drop for Timeout<'a> {
    fn drop(&mut self
    ) {
        self.manager.cancel_timeout(self.id);
    }
}

/// Deadline for tracking absolute timeouts
#[derive(Debug, Clone, Copy)]
pub struct Deadline {
    /// When the deadline expires
    expires_at: Instant,
}

impl Deadline {
    /// Create a deadline from now
    pub fn after(duration: Duration
    ) -> Self {
        Self {
            expires_at: Instant::now() + duration,
        }
    }

    /// Create a deadline from a timestamp
    pub fn at(instant: Instant
    ) -> Self {
        Self { expires_at: instant }
    }

    /// Check if deadline has passed
    pub fn is_expired(&self
    ) -> bool {
        Instant::now() >= self.expires_at
    }

    /// Get remaining time
    pub fn remaining(&self
    ) -> Duration {
        let now = Instant::now();
        if self.expires_at > now {
            self.expires_at.duration_since(now)
        } else {
            Duration::ZERO
        }
    }

    /// Get elapsed time since deadline
    pub fn elapsed(&self
    ) -> Duration {
        let now = Instant::now();
        if now > self.expires_at {
            now.duration_since(self.expires_at)
        } else {
            Duration::ZERO
        }
    }

    /// Extend the deadline
    pub fn extend(&mut self,
        additional: Duration
    ) {
        self.expires_at += additional;
    }

    /// Convert to timeout
    pub fn into_timeout(&self
    ) -> tokio::time::Timeout<Sleep> {
        tokio::time::timeout_at(self.expires_at, tokio::time::sleep_until(self.expires_at))
    }
}

/// Timeout group for managing multiple timeouts
pub struct TimeoutGroup {
    /// Timeouts in this group
    timeouts: Vec<u64>,
    /// Manager reference
    manager: Arc<TimeoutManager>,
}

impl TimeoutGroup {
    /// Create a new timeout group
    pub fn new(manager: Arc<TimeoutManager>) -> Self {
        Self {
            timeouts: Vec::new(),
            manager,
        }
    }

    /// Add a timeout to the group
    pub fn add(
        &mut self,
        duration: Duration,
        policy: TimeoutPolicy
    ) -> Timeout {
        let timeout = self.manager.create_timeout(duration, policy);
        self.timeouts.push(timeout.id);
        timeout
    }

    /// Cancel all timeouts in the group
    pub fn cancel_all(&self
    ) {
        for id in &self.timeouts {
            self.manager.cancel_timeout(*id);
        }
    }

    /// Check if any timeout has expired
    pub fn any_expired(&self
    ) -> bool {
        self.timeouts.iter().any(|id| self.manager.check_timeout(*id))
    }
}

/// Timeout-aware wrapper for futures
pub struct TimeoutWrapper<F> {
    /// Inner future
    future: F,
    /// Timeout
    timeout: Pin<Box<Sleep>>,
}

impl<F> TimeoutWrapper<F> {
    /// Create a new timeout wrapper
    pub fn new(future: F, timeout: Duration) -> Self {
        Self {
            future,
            timeout: Box::pin(tokio::time::sleep(timeout)),
        }
    }
}

impl<F: Future> Future for TimeoutWrapper<F> {
    type Output = Result<F::Output, TimeoutError>;

    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        // Check inner future first
        let future_pin = unsafe { Pin::new_unchecked(&mut self.future) };
        match future_pin.poll(cx) {
            Poll::Ready(result) => return Poll::Ready(Ok(result)),
            Poll::Pending => {}
        }

        // Check timeout
        match self.timeout.as_mut().poll(cx) {
            Poll::Ready(_) => Poll::Ready(Err(TimeoutError)),
            Poll::Pending => Poll::Pending,
        }
    }
}

/// Timeout error
#[derive(Debug, Clone, Copy)]
pub struct TimeoutError;

impl std::fmt::Display for TimeoutError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Operation timed out")
    }
}

impl std::error::Error for TimeoutError {}

/// Extension trait for adding timeout to futures
pub trait TimeoutExt: Future + Sized {
    /// Add a timeout to this future
    fn with_timeout(self, duration: Duration) -> TimeoutWrapper<Self>;

    /// Add a timeout with a deadline
    fn with_deadline(self, deadline: Deadline) -<TimeoutWrapper<Self>;
}

impl<F: Future> TimeoutExt for F {
    fn with_timeout(self, duration: Duration) -> TimeoutWrapper<Self> {
        TimeoutWrapper::new(self, duration)
    }

    fn with_deadline(self, deadline: Deadline) -> TimeoutWrapper<Self> {
        TimeoutWrapper::new(self, deadline.remaining())
    }
}

impl TimeoutConfig {
    /// Get default timeout as Duration
    fn default_timeout(&self) -> Duration {
        Duration::from_secs(self.default_timeout_secs)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_timeout() {
        let config = TimeoutConfig::default();
        let manager = TimeoutManager::new(config);

        let timeout = manager.timeout(Duration::from_millis(50));

        tokio::time::sleep(Duration::from_millis(60)).await;

        assert!(timeout.manager.check_timeout(timeout.id));
    }

    #[tokio::test]
    async fn test_timeout_cancel() {
        let config = TimeoutConfig::default();
        let manager = TimeoutManager::new(config);

        let timeout = manager.timeout(Duration::from_secs(60));
        timeout.cancel();

        assert!(!timeout.manager.check_timeout(timeout.id));
    }

    #[tokio::test]
    async fn test_deadline() {
        let deadline = Deadline::after(Duration::from_millis(50));

        assert!(!deadline.is_expired());
        assert!(deadline.remaining() > Duration::ZERO);

        tokio::time::sleep(Duration::from_millis(60)).await;

        assert!(deadline.is_expired());
        assert_eq!(deadline.remaining(), Duration::ZERO);
    }

    #[tokio::test]
    async fn test_deadline_extend() {
        let mut deadline = Deadline::after(Duration::from_millis(50));

        tokio::time::sleep(Duration::from_millis(30)).await;
        assert!(!deadline.is_expired());

        deadline.extend(Duration::from_millis(100));

        tokio::time::sleep(Duration::from_millis(50)).await;
        assert!(!deadline.is_expired());
    }

    #[tokio::test]
    async fn test_timeout_wrapper() {
        let future = async {
            tokio::time::sleep(Duration::from_secs(60)).await;
            42
        };

        let result = TimeoutWrapper::new(future, Duration::from_millis(50)).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_timeout_ext() {
        let future = async {
            tokio::time::sleep(Duration::from_secs(60)).await;
            42
        };

        let result = future.with_timeout(Duration::from_millis(50)).await;
        assert!(result.is_err());
    }

    #[test]
    fn test_timeout_group() {
        let config = TimeoutConfig::default();
        let manager = Arc::new(TimeoutManager::new(config));
        let mut group = TimeoutGroup::new(manager);

        group.add(Duration::from_secs(10), TimeoutPolicy::Immediate);
        group.add(Duration::from_secs(20), TimeoutPolicy::Graceful);

        group.cancel_all();
    }

    #[tokio::test]
    async fn test_timeout_stats() {
        let config = TimeoutConfig::default();
        let manager = TimeoutManager::new(config);

        let _ = manager.timeout(Duration::from_millis(10));
        let timeout = manager.timeout(Duration::from_millis(10));

        tokio::time::sleep(Duration::from_millis(20)).await;

        // Check triggered
        let _ = manager.check_timeout(timeout.id);

        let stats = manager.stats();
        assert!(stats.total_timeouts >= 2);
    }
}
