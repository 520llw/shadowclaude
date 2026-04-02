//! Extended protocol features
//!
//! Additional protocol functionality:
//! - Connection pooling
//! - Retry logic
//! - Middleware support
//! - Metrics collection

use crate::{ProtocolError, ProtocolMessage, ProtocolResult};
use std::collections::VecDeque;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::{sleep, timeout};
use tracing::{debug, error, trace, warn};

/// Connection pool for efficient connection reuse
pub struct ConnectionPool<T> {
    /// Pool name
    name: String,
    /// Available connections
    available: Mutex<VecDeque<T>>,
    /// In-use connections count
    in_use: AtomicU64,
    /// Max connections
    max_size: usize,
    /// Semaphore for limiting
    semaphore: Semaphore,
    /// Factory function
    factory: Box<dyn Fn() -> std::pin::Pin<Box<dyn std::future::Future<Output = ProtocolResult<T>> + Send>> + Send + Sync>,
}

impl<T: Send + 'static> ConnectionPool<T> {
    /// Create a new connection pool
    pub fn new<F, Fut>(
        name: impl Into<String>,
        max_size: usize,
        factory: F,
    ) -> Self
    where
        F: Fn() -> Fut + Send + Sync + 'static,
        Fut: std::future::Future<Output = ProtocolResult<T>> + Send + 'static,
    {
        Self {
            name: name.into(),
            available: Mutex::new(VecDeque::with_capacity(max_size)),
            in_use: AtomicU64::new(0),
            max_size,
            semaphore: Semaphore::new(max_size),
            factory: Box::new(move || Box::pin(factory())),
        }
    }

    /// Acquire a connection
    pub async fn acquire(&self
    ) -> ProtocolResult<PooledConnection<T>> {
        let _permit = self.semaphore.acquire().await
            .map_err(|_| ProtocolError::Connection("Pool closed".to_string()))?;

        // Try to get existing connection
        let conn = {
            let mut available = self.available.lock().await;
            available.pop_front()
        };

        let conn = match conn {
            Some(c) => c,
            None => {
                // Create new connection
                (self.factory)().await?
            }
        };

        self.in_use.fetch_add(1, Ordering::Relaxed);

        Ok(PooledConnection {
            conn: Some(conn),
            pool: self,
        })
    }

    /// Return connection to pool
    async fn release(&self,
        conn: T
    ) {
        self.in_use.fetch_sub(1, Ordering::Relaxed);

        let mut available = self.available.lock().await;
        if available.len() < self.max_size {
            available.push_back(conn);
        }
        // Drop connection if pool is full
    }

    /// Get pool statistics
    pub async fn stats(&self) -> PoolStats {
        let available = self.available.lock().await.len();
        PoolStats {
            available,
            in_use: self.in_use.load(Ordering::Relaxed) as usize,
            max_size: self.max_size,
        }
    }
}

/// Pooled connection guard
pub struct PooledConnection<'a, T> {
    conn: Option<T>,
    pool: &'a ConnectionPool<T>,
}

impl<'a, T> PooledConnection<'a, T> {
    /// Get reference to connection
    pub fn get(&self) -> &T {
        self.conn.as_ref().unwrap()
    }

    /// Get mutable reference
    pub fn get_mut(&mut self) -> &mut T {
        self.conn.as_mut().unwrap()
    }
}

impl<'a, T: Send> Drop for PooledConnection<'a, T> {
    fn drop(&mut self
    ) {
        if let Some(conn) = self.conn.take() {
            let pool = self.pool;
            tokio::spawn(async move {
                pool.release(conn).await;
            });
        }
    }
}

impl<'a, T> std::ops::Deref for PooledConnection<'a, T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        self.get()
    }
}

impl<'a, T> std::ops::DerefMut for PooledConnection<'a, T> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        self.get_mut()
    }
}

/// Pool statistics
#[derive(Debug, Clone, Copy)]
pub struct PoolStats {
    /// Available connections
    pub available: usize,
    /// In-use connections
    pub in_use: usize,
    /// Max size
    pub max_size: usize,
}

/// Retry configuration
#[derive(Debug, Clone, Copy)]
pub struct RetryConfig {
    /// Max retry attempts
    pub max_attempts: u32,
    /// Initial delay
    pub initial_delay: Duration,
    /// Max delay
    pub max_delay: Duration,
    /// Backoff multiplier
    pub backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(30),
            backoff_multiplier: 2.0,
        }
    }
}

/// Retry wrapper for operations
pub struct Retry {
    config: RetryConfig,
}

impl Retry {
    /// Create new retry wrapper
    pub fn new(config: RetryConfig) -> Self {
        Self { config }
    }

    /// Execute with retry
    pub async fn execute<F, Fut, T>(
        &self,
        operation: F,
    ) -> ProtocolResult<T>
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = ProtocolResult<T>>,
    {
        let mut attempts = 0u32;
        let mut delay = self.config.initial_delay;

        loop {
            match operation().await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    attempts += 1;

                    if attempts >= self.config.max_attempts || !e.is_retryable() {
                        return Err(e);
                    }

                    trace!("Retry attempt {} after {:?}", attempts, delay);
                    sleep(delay).await;

                    delay = std::cmp::min(
                        Duration::from_millis(
                            (delay.as_millis() as f64 * self.config.backoff_multiplier) as u64
                        ),
                        self.config.max_delay,
                    );
                }
            }
        }
    }
}

/// Middleware trait for request/response processing
#[async_trait::async_trait]
pub trait Middleware: Send + Sync {
    /// Process request
    async fn process_request(
        &self,
        request: ProtocolMessage,
    ) -> ProtocolResult<ProtocolMessage>;

    /// Process response
    async fn process_response(
        &self,
        response: ProtocolMessage,
    ) -> ProtocolResult<ProtocolMessage>;
}

/// Middleware chain
pub struct MiddlewareChain {
    middlewares: Vec<Box<dyn Middleware>>,
}

impl MiddlewareChain {
    /// Create new chain
    pub fn new() -> Self {
        Self {
            middlewares: Vec::new(),
        }
    }

    /// Add middleware
    pub fn add(&mut self,
        middleware: Box<dyn Middleware>
    ) {
        self.middlewares.push(middleware);
    }

    /// Process request through chain
    pub async fn process_request(
        &self,
        mut request: ProtocolMessage,
    ) -> ProtocolResult<ProtocolMessage> {
        for middleware in &self.middlewares {
            request = middleware.process_request(request).await?;
        }
        Ok(request)
    }

    /// Process response through chain
    pub async fn process_response(
        &self,
        mut response: ProtocolMessage,
    ) -> ProtocolResult<ProtocolMessage> {
        // Process in reverse order
        for middleware in self.middlewares.iter().rev() {
            response = middleware.process_response(response).await?;
        }
        Ok(response)
    }
}

impl Default for MiddlewareChain {
    fn default() -> Self {
        Self::new()
    }
}

/// Metrics collector
pub struct MetricsCollector {
    /// Total requests
    total_requests: AtomicU64,
    /// Successful requests
    successful_requests: AtomicU64,
    /// Failed requests
    failed_requests: AtomicU64,
    /// Total latency
    total_latency_ms: AtomicU64,
}

impl MetricsCollector {
    /// Create new collector
    pub fn new() -> Self {
        Self {
            total_requests: AtomicU64::new(0),
            successful_requests: AtomicU64::new(0),
            failed_requests: AtomicU64::new(0),
            total_latency_ms: AtomicU64::new(0),
        }
    }

    /// Record request
    pub fn record_request(&self,
        success: bool,
        latency_ms: u64
    ) {
        self.total_requests.fetch_add(1, Ordering::Relaxed);
        self.total_latency_ms.fetch_add(latency_ms, Ordering::Relaxed);

        if success {
            self.successful_requests.fetch_add(1, Ordering::Relaxed);
        } else {
            self.failed_requests.fetch_add(1, Ordering::Relaxed);
        }
    }

    /// Get snapshot
    pub fn snapshot(&self) -> MetricsSnapshot {
        let total = self.total_requests.load(Ordering::Relaxed);
        let success = self.successful_requests.load(Ordering::Relaxed);
        let failed = self.failed_requests.load(Ordering::Relaxed);
        let latency = self.total_latency_ms.load(Ordering::Relaxed);

        MetricsSnapshot {
            total_requests: total,
            successful_requests: success,
            failed_requests: failed,
            avg_latency_ms: if total > 0 { latency / total } else { 0 },
            success_rate: if total > 0 { success as f64 / total as f64 } else { 0.0 },
        }
    }
}

impl Default for MetricsCollector {
    fn default() -> Self {
        Self::new()
    }
}

/// Metrics snapshot
#[derive(Debug, Clone, Copy)]
pub struct MetricsSnapshot {
    /// Total requests
    pub total_requests: u64,
    /// Successful requests
    pub successful_requests: u64,
    /// Failed requests
    pub failed_requests: u64,
    /// Average latency
    pub avg_latency_ms: u64,
    /// Success rate
    pub success_rate: f64,
}

/// Rate limiter with token bucket
pub struct TokenBucket {
    /// Tokens per second
    rate: f64,
    /// Bucket capacity
    capacity: f64,
    /// Current tokens
    tokens: Mutex<f64>,
    /// Last update
    last_update: Mutex<std::time::Instant>,
}

impl TokenBucket {
    /// Create new token bucket
    pub fn new(rate: f64, capacity: f64) -> Self {
        Self {
            rate,
            capacity,
            tokens: Mutex::new(capacity),
            last_update: Mutex::new(std::time::Instant::now()),
        }
    }

    /// Try to acquire tokens
    pub async fn acquire(&self,
        amount: f64
    ) -> bool {
        let mut tokens = self.tokens.lock().await;
        let mut last = self.last_update.lock().await;

        // Add tokens based on time elapsed
        let now = std::time::Instant::now();
        let elapsed = now.duration_since(*last).as_secs_f64();
        *tokens = (*tokens + elapsed * self.rate).min(self.capacity);
        *last = now;

        if *tokens >= amount {
            *tokens -= amount;
            true
        } else {
            false
        }
    }

    /// Get current tokens
    pub async fn available(&self
    ) -> f64 {
        *self.tokens.lock().await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_retry_success() {
        let retry = Retry::new(RetryConfig {
            max_attempts: 3,
            ..Default::default()
        });

        let counter = std::sync::atomic::AtomicU32::new(0);
        let result: Result<i32, _> = retry.execute(|| async {
            let count = counter.fetch_add(1, Ordering::Relaxed);
            if count < 2 {
                Err(ProtocolError::Connection("fail".to_string()))
            } else {
                Ok(42)
            }
        }).await;

        assert_eq!(result.unwrap(), 42);
        assert_eq!(counter.load(Ordering::Relaxed), 3);
    }

    #[tokio::test]
    async fn test_retry_exhausted() {
        let retry = Retry::new(RetryConfig {
            max_attempts: 2,
            initial_delay: Duration::from_millis(1),
            ..Default::default()
        });

        let result: Result<i32, _> = retry.execute(|| async {
            Err::<_, ProtocolError>(Err(ProtocolError::Connection("fail".to_string())))
        }).await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_token_bucket() {
        let bucket = TokenBucket::new(10.0, 5.0);

        assert!(bucket.acquire(3.0).await);
        assert!(bucket.acquire(2.0).await);
        assert!(!bucket.acquire(1.0).await); // Bucket empty

        // Wait for refill
        tokio::time::sleep(Duration::from_millis(200)).await;
        assert!(bucket.acquire(1.0).await);
    }

    #[test]
    fn test_metrics_collector() {
        let metrics = MetricsCollector::new();

        metrics.record_request(true, 100);
        metrics.record_request(true, 200);
        metrics.record_request(false, 50);

        let snapshot = metrics.snapshot();
        assert_eq!(snapshot.total_requests, 3);
        assert_eq!(snapshot.successful_requests, 2);
        assert_eq!(snapshot.failed_requests, 1);
        assert_eq!(snapshot.avg_latency_ms, 116); // (100+200+50)/3
    }
}
