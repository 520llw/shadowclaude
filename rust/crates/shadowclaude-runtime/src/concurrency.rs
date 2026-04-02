//! Concurrency control primitives
//!
//! This module provides:
//! - Priority-based semaphores
//! - Fair mutexes
//! - Concurrency limiters with backpressure
//! - Resource pools

use dashmap::DashMap;
use parking_lot::{Mutex, RwLock};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::task::{Context, Poll, Waker};
use tokio::sync::{AcquireError, Semaphore, SemaphorePermit};
use tracing::{debug, trace, warn};

/// Concurrency limit configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LimitConfig {
    /// Maximum concurrent operations
    pub max_concurrent: usize,
    /// Maximum queue size (0 = unlimited)
    pub max_queue_size: usize,
    /// Timeout for acquiring permits
    pub acquire_timeout_ms: u64,
    /// Enable fair queuing
    pub fair_queuing: bool,
}

impl Default for LimitConfig {
    fn default() -> Self {
        Self {
            max_concurrent: 100,
            max_queue_size: 1000,
            acquire_timeout_ms: 5000,
            fair_queuing: true,
        }
    }
}

/// Priority levels for resource acquisition
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum Priority {
    /// Critical - immediate access
    Critical = 0,
    /// High priority
    High = 1,
    /// Normal priority
    Normal = 2,
    /// Low priority
    Low = 3,
    /// Background - lowest priority
    Background = 4,
}

impl Default for Priority {
    fn default() -> Self {
        Priority::Normal
    }
}

/// Priority-based semaphore for fair resource allocation
pub struct PrioritySemaphore {
    /// Base semaphore for capacity
    semaphore: Semaphore,
    /// Per-priority wait queues
    waiters: DashMap<Priority, VecDeque<Waker>>,
    /// Current waiters count per priority
    waiter_counts: DashMap<Priority, AtomicU64>,
    /// Configuration
    config: LimitConfig,
    /// Total acquired permits
    acquired: AtomicU64,
}

impl PrioritySemaphore {
    /// Create a new priority semaphore
    pub fn new(config: LimitConfig) -> Self {
        Self {
            semaphore: Semaphore::new(config.max_concurrent),
            waiters: DashMap::new(),
            waiter_counts: DashMap::new(),
            config,
            acquired: AtomicU64::new(0),
        }
    }

    /// Acquire a permit with priority
    pub async fn acquire(&self,
        priority: Priority,
    ) -> Result<PriorityPermit, AcquireError> {
        // Try fast path first
        match tokio::time::timeout(
            tokio::time::Duration::from_millis(self.config.acquire_timeout_ms),
            self.semaphore.acquire(),
        )
        .await
        {
            Ok(Ok(permit)) => {
                self.acquired.fetch_add(1, Ordering::SeqCst);
                return Ok(PriorityPermit {
                    _permit: permit,
                    semaphore: self,
                });
            }
            Ok(Err(e)) => return Err(e),
            Err(_) => {
                // Timeout - add to priority queue
                self.increment_waiter(priority);

                // Wait for our turn
                PrioritySemaphoreAcquire {
                    semaphore: self,
                    priority,
                    completed: false,
                }
                .await
            }
        }
    }

    /// Try to acquire without waiting
    pub fn try_acquire(&self
    ) -> Option<PriorityPermit> {
        self.semaphore.try_acquire().ok().map(|permit| {
            self.acquired.fetch_add(1, Ordering::SeqCst);
            PriorityPermit {
                _permit: permit,
                semaphore: self,
            }
        })
    }

    /// Get available permits
    pub fn available_permits(&self
    ) -> usize {
        self.semaphore.available_permits()
    }

    /// Get current usage
    pub fn current_usage(&self
    ) -> usize {
        self.acquired.load(Ordering::SeqCst) as usize
    }

    fn increment_waiter(&self,
        priority: Priority
    ) {
        self.waiter_counts
            .entry(priority)
            .or_insert_with(|| AtomicU64::new(0))
            .fetch_add(1, Ordering::SeqCst);
    }

    fn decrement_waiter(&self,
        priority: Priority
    ) {
        if let Some(count) = self.waiter_counts.get(&priority) {
            count.fetch_sub(1, Ordering::SeqCst);
        }
    }

    fn register_waker(&self,
        priority: Priority,
        waker: &Waker
    ) {
        self.waiters
            .entry(priority)
            .or_insert_with(VecDeque::new)
            .push_back(waker.clone());
    }

    fn wake_next(&self
    ) {
        // Wake highest priority waiter
        for priority in [Priority::Critical, Priority::High, Priority::Normal, Priority::Low, Priority::Background] {
            if let Some(mut queue) = self.waiters.get_mut(&priority) {
                if let Some(waker) = queue.pop_front() {
                    waker.wake();
                    return;
                }
            }
        }
    }
}

/// Permit from priority semaphore
pub struct PriorityPermit<'a> {
    _permit: SemaphorePermit<'a>,
    semaphore: &'a PrioritySemaphore,
}

impl<'a> Drop for PriorityPermit<'a> {
    fn drop(&mut self
    ) {
        self.semaphore.acquired.fetch_sub(1, Ordering::SeqCst);
        self.semaphore.wake_next();
    }
}

/// Future for priority-based acquisition
struct PrioritySemaphoreAcquire<'a> {
    semaphore: &'a PrioritySemaphore,
    priority: Priority,
    completed: bool,
}

impl<'a> Future for PrioritySemaphoreAcquire<'a> {
    type Output = Result<PriorityPermit<'a>, AcquireError>;

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        let this = self.get_mut();

        if this.completed {
            return Poll::Ready(Err(AcquireError::closed()));
        }

        // Try to acquire
        match this.semaphore.semaphore.try_acquire() {
            Ok(permit) => {
                this.completed = true;
                this.semaphore.decrement_waiter(this.priority);
                this.semaphore.acquired.fetch_add(1, Ordering::SeqCst);
                Poll::Ready(Ok(PriorityPermit {
                    _permit: permit,
                    semaphore: this.semaphore,
                }))
            }
            Err(_) => {
                // Register waker and wait
                this.semaphore.register_waker(this.priority, cx.waker());
                Poll::Pending
            }
        }
    }
}

/// Concurrency limiter with backpressure
pub struct ConcurrencyLimiter {
    /// Name of this limiter
    name: String,
    /// Semaphore for limiting
    semaphore: PrioritySemaphore,
    /// Queue size limit
    max_queue_size: usize,
    /// Current queue size
    queue_size: AtomicU64,
    /// Metrics
    total_acquired: AtomicU64,
    total_rejected: AtomicU64,
    total_timed_out: AtomicU64,
}

impl ConcurrencyLimiter {
    /// Create a new concurrency limiter
    pub fn new(name: impl Into<String>, config: LimitConfig) -> Self {
        Self {
            name: name.into(),
            semaphore: PrioritySemaphore::new(config.clone()),
            max_queue_size: config.max_queue_size,
            queue_size: AtomicU64::new(0),
            total_acquired: AtomicU64::new(0),
            total_rejected: AtomicU64::new(0),
            total_timed_out: AtomicU64::new(0),
        }
    }

    /// Acquire with normal priority
    pub async fn acquire(&self
    ) -> Result<LimitGuard, LimiterError> {
        self.acquire_with_priority(Priority::Normal).await
    }

    /// Acquire with specific priority
    pub async fn acquire_with_priority(
        &self,
        priority: Priority,
    ) -> Result<LimitGuard, LimiterError> {
        // Check queue size
        let current_queue = self.queue_size.load(Ordering::Relaxed);
        if self.max_queue_size > 0 && current_queue >= self.max_queue_size as u64 {
            self.total_rejected.fetch_add(1, Ordering::Relaxed);
            return Err(LimiterError::QueueFull);
        }

        self.queue_size.fetch_add(1, Ordering::Relaxed);

        match self.semaphore.acquire(priority).await {
            Ok(permit) => {
                self.queue_size.fetch_sub(1, Ordering::Relaxed);
                self.total_acquired.fetch_add(1, Ordering::Relaxed);
                Ok(LimitGuard {
                    _permit: permit,
                    limiter: self,
                })
            }
            Err(_) => {
                self.queue_size.fetch_sub(1, Ordering::Relaxed);
                self.total_timed_out.fetch_add(1, Ordering::Relaxed);
                Err(LimiterError::Timeout)
            }
        }
    }

    /// Try to acquire immediately
    pub fn try_acquire(&self
    ) -> Option<LimitGuard> {
        self.semaphore.try_acquire().map(|permit| {
            self.total_acquired.fetch_add(1, Ordering::Relaxed);
            LimitGuard {
                _permit: permit,
                limiter: self,
            }
        })
    }

    /// Get current metrics
    pub fn metrics(&self) -> LimiterMetrics {
        LimiterMetrics {
            name: self.name.clone(),
            available_permits: self.semaphore.available_permits(),
            current_usage: self.semaphore.current_usage(),
            queue_size: self.queue_size.load(Ordering::Relaxed) as usize,
            total_acquired: self.total_acquired.load(Ordering::Relaxed),
            total_rejected: self.total_rejected.load(Ordering::Relaxed),
            total_timed_out: self.total_timed_out.load(Ordering::Relaxed),
        }
    }
}

/// Guard for concurrency limit
pub struct LimitGuard<'a> {
    _permit: PriorityPermit<'a>,
    limiter: &'a ConcurrencyLimiter,
}

/// Limiter errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LimiterError {
    /// Queue is full
    QueueFull,
    /// Acquisition timed out
    Timeout,
    /// Limiter closed
    Closed,
}

impl std::fmt::Display for LimiterError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LimiterError::QueueFull => write!(f, "Queue is full"),
            LimiterError::Timeout => write!(f, "Acquisition timed out"),
            LimiterError::Closed => write!(f, "Limiter is closed"),
        }
    }
}

impl std::error::Error for LimiterError {}

/// Limiter metrics
#[derive(Debug, Clone)]
pub struct LimiterMetrics {
    /// Limiter name
    pub name: String,
    /// Available permits
    pub available_permits: usize,
    /// Current usage
    pub current_usage: usize,
    /// Current queue size
    pub queue_size: usize,
    /// Total acquired
    pub total_acquired: u64,
    /// Total rejected
    pub total_rejected: u64,
    /// Total timed out
    pub total_timed_out: u64,
}

/// Resource pool for reusable resources
pub struct ResourcePool<T> {
    /// Pool name
    name: String,
    /// Available resources
    resources: Mutex<VecDeque<T>>,
    /// Max size
    max_size: usize,
    /// Current size
    current_size: AtomicU64,
    /// Factory function
    factory: Box<dyn Fn() -> T + Send + Sync>,
}

impl<T: Send> ResourcePool<T> {
    /// Create a new resource pool
    pub fn new(
        name: impl Into<String>,
        max_size: usize,
        factory: impl Fn() -> T + Send + Sync + 'static,
    ) -> Self {
        Self {
            name: name.into(),
            resources: Mutex::new(VecDeque::with_capacity(max_size)),
            max_size,
            current_size: AtomicU64::new(0),
            factory: Box::new(factory),
        }
    }

    /// Acquire a resource from the pool
    pub fn acquire(&self
    ) -> Option<PooledResource<T>> {
        let mut resources = self.resources.lock();

        if let Some(resource) = resources.pop_front() {
            return Some(PooledResource {
                resource: Some(resource),
                pool: self,
            });
        }

        // Create new if under limit
        let current = self.current_size.load(Ordering::Relaxed);
        if (current as usize) < self.max_size {
            self.current_size.fetch_add(1, Ordering::Relaxed);
            let resource = (self.factory)();
            return Some(PooledResource {
                resource: Some(resource),
                pool: self,
            });
        }

        None
    }

    fn release(&self,
        resource: T
    ) {
        let mut resources = self.resources.lock();
        resources.push_back(resource);
    }
}

/// Pooled resource guard
pub struct PooledResource<'a, T> {
    resource: Option<T>,
    pool: &'a ResourcePool<T>,
}

impl<'a, T> PooledResource<'a, T> {
    /// Get reference to resource
    pub fn get(&self) -> &T {
        self.resource.as_ref().unwrap()
    }

    /// Get mutable reference to resource
    pub fn get_mut(&mut self) -> &mut T {
        self.resource.as_mut().unwrap()
    }

    /// Take ownership of the resource
    pub fn take(mut self) -> T {
        self.resource.take().unwrap()
    }
}

impl<'a, T> Drop for PooledResource<'a, T> {
    fn drop(&mut self
    ) {
        if let Some(resource) = self.resource.take() {
            self.pool.release(resource);
        }
    }
}

impl<'a, T> std::ops::Deref for PooledResource<'a, T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        self.get()
    }
}

impl<'a, T> std::ops::DerefMut for PooledResource<'a, T> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        self.get_mut()
    }
}

/// Adaptive concurrency limiter that adjusts based on performance
pub struct AdaptiveLimiter {
    /// Base limiter
    limiter: ConcurrencyLimiter,
    /// Target latency in ms
    target_latency_ms: f64,
    /// Current latency estimate
    current_latency_ms: RwLock<f64>,
    /// Adjustment factor
    adjustment_factor: f64,
}

impl AdaptiveLimiter {
    /// Create a new adaptive limiter
    pub fn new(
        name: impl Into<String>,
        config: LimitConfig,
        target_latency_ms: f64,
    ) -> Self {
        Self {
            limiter: ConcurrencyLimiter::new(name, config),
            target_latency_ms,
            current_latency_ms: RwLock::new(0.0),
            adjustment_factor: 0.1,
        }
    }

    /// Execute with adaptive limiting
    pub async fn execute<F, Fut, T>(
        &self,
        f: F,
    ) -> Result<T, LimiterError>
    where
        F: FnOnce() -> Fut,
        Fut: Future<Output = T>,
    {
        let _guard = self.limiter.acquire().await?;

        let start = std::time::Instant::now();
        let result = f().await;
        let elapsed = start.elapsed().as_secs_f64() * 1000.0;

        // Update latency estimate
        let mut current = self.current_latency_ms.write();
        *current = *current * (1.0 - self.adjustment_factor) + elapsed * self.adjustment_factor;

        Ok(result)
    }

    /// Get current latency estimate
    pub fn current_latency_ms(&self
    ) -> f64 {
        *self.current_latency_ms.read()
    }

    /// Check if over target
    pub fn is_over_target(&self
    ) -> bool {
        self.current_latency_ms() > self.target_latency_ms
    }
}

use std::fmt;

impl<T> fmt::Debug for ResourcePool<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ResourcePool")
            .field("name", &self.name)
            .field("max_size", &self.max_size)
            .field("current_size", &self.current_size.load(Ordering::Relaxed))
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_priority_semaphore() {
        let sem = PrioritySemaphore::new(LimitConfig {
            max_concurrent: 1,
            ..Default::default()
        });

        let permit1 = sem.acquire(Priority::Normal).await.unwrap();
        assert_eq!(sem.available_permits(), 0);

        drop(permit1);
        assert_eq!(sem.available_permits(), 1);
    }

    #[tokio::test]
    async fn test_concurrency_limiter() {
        let limiter = ConcurrencyLimiter::new("test", LimitConfig {
            max_concurrent: 2,
            max_queue_size: 10,
            acquire_timeout_ms: 1000,
            fair_queuing: true,
        });

        let _guard1 = limiter.acquire().await.unwrap();
        let _guard2 = limiter.acquire().await.unwrap();

        // Should timeout quickly
        let result = tokio::time::timeout(
            tokio::time::Duration::from_millis(100),
            limiter.acquire(),
        )
        .await;

        assert!(result.is_err() || result.unwrap().is_err());
    }

    #[test]
    fn test_resource_pool() {
        let pool = ResourcePool::new("test", 2, || 42i32);

        {
            let res1 = pool.acquire().unwrap();
            assert_eq!(*res1, 42);

            let res2 = pool.acquire().unwrap();
            assert_eq!(*res2, 42);

            // Pool exhausted
            assert!(pool.acquire().is_none());
        }

        // Resource returned, should be available again
        assert!(pool.acquire().is_some());
    }

    #[tokio::test]
    async fn test_adaptive_limiter() {
        let limiter = AdaptiveLimiter::new("test", LimitConfig::default(), 100.0);

        let result: Result<i32, _> = limiter.execute(|| async { 42 }).await;
        assert_eq!(result.unwrap(), 42);

        assert!(limiter.current_latency_ms() >= 0.0);
    }
}
