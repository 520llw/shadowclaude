//! Runtime executor with custom thread pool management
//!
//! Provides a high-level executor interface with:
//! - Custom thread pool configuration
//! - Metrics collection
//! - Graceful shutdown

use serde::{Deserialize, Serialize};
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::task::{Context, Poll};
use tokio::runtime::{Handle, Runtime};
use tokio::task::{JoinError, JoinHandle};
use tracing::{debug, error, info, warn};

/// Runtime configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeConfig {
    /// Number of worker threads
    pub worker_threads: usize,
    /// Max blocking threads
    pub max_blocking_threads: usize,
    /// Thread stack size in bytes
    pub thread_stack_size: usize,
    /// Thread keep-alive timeout in seconds
    pub thread_keep_alive_secs: u64,
    /// Enable IO driver
    pub enable_io: bool,
    /// Enable time driver
    pub enable_time: bool,
    /// Scheduler configuration
    pub scheduler: crate::scheduler::SchedulerConfig,
    /// Timeout configuration
    pub timeout: crate::timeout::TimeoutConfig,
}

impl Default for RuntimeConfig {
    fn default() -> Self {
        Self {
            worker_threads: num_cpus::get(),
            max_blocking_threads: 512,
            thread_stack_size: 2 * 1024 * 1024,
            thread_keep_alive_secs: 10,
            enable_io: true,
            enable_time: true,
            scheduler: crate::scheduler::SchedulerConfig::default(),
            timeout: crate::timeout::TimeoutConfig::default(),
        }
    }
}

/// Runtime executor
pub struct RuntimeExecutor {
    /// Inner Tokio runtime
    runtime: Option<Runtime>,
    /// Handle to the runtime
    handle: Handle,
    /// Configuration
    config: RuntimeConfig,
    /// Active tasks count
    active_tasks: AtomicU64,
    /// Completed tasks count
    completed_tasks: AtomicU64,
    /// Shutdown flag
    shutdown: AtomicBool,
}

impl RuntimeExecutor {
    /// Create a new runtime executor
    pub async fn new(config: RuntimeConfig) -> std::io::Result<Self> {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(config.worker_threads)
            .max_blocking_threads(config.max_blocking_threads)
            .thread_stack_size(config.thread_stack_size)
            .thread_keep_alive(tokio::time::Duration::from_secs(config.thread_keep_alive_secs))
            .enable_io()
            .enable_time()
            .build()?;

        let handle = runtime.handle().clone();

        info!(
            worker_threads = config.worker_threads,
            max_blocking = config.max_blocking_threads,
            "RuntimeExecutor created"
        );

        Ok(Self {
            runtime: Some(runtime),
            handle,
            config,
            active_tasks: AtomicU64::new(0),
            completed_tasks: AtomicU64::new(0),
            shutdown: AtomicBool::new(false),
        })
    }

    /// Spawn a task on the runtime
    pub fn spawn<F>(&self,
        future: F
    ) -> RuntimeJoinHandle<F::Output>
    where
        F: Future + Send + 'static,
        F::Output: Send + 'static,
    {
        if self.shutdown.load(Ordering::Relaxed) {
            panic!("Runtime is shutting down");
        }

        self.active_tasks.fetch_add(1, Ordering::Relaxed);

        let active = self.active_tasks.clone();
        let completed = self.completed_tasks.clone();

        let inner = self.handle.spawn(async move {
            let result = future.await;
            active.fetch_sub(1, Ordering::Relaxed);
            completed.fetch_add(1, Ordering::Relaxed);
            result
        });

        RuntimeJoinHandle { inner }
    }

    /// Spawn a blocking task
    pub fn spawn_blocking<F, R>(&self,
        func: F
    ) -> RuntimeJoinHandle<R>
    where
        F: FnOnce() -> R + Send + 'static,
        R: Send + 'static,
    {
        if self.shutdown.load(Ordering::Relaxed) {
            panic!("Runtime is shutting down");
        }

        self.active_tasks.fetch_add(1, Ordering::Relaxed);

        let active = self.active_tasks.clone();
        let completed = self.completed_tasks.clone();

        let inner = self.handle.spawn_blocking(move || {
            let result = func();
            active.fetch_sub(1, Ordering::Relaxed);
            completed.fetch_add(1, Ordering::Relaxed);
            result
        });

        RuntimeJoinHandle { inner }
    }

    /// Block on a future (for main thread)
    pub fn block_on<F>(&self,
        future: F
    ) -> F::Output
    where
        F: Future,
    {
        self.handle.block_on(future)
    }

    /// Run a future to completion
    pub async fn run<F>(&self,
        future: F
    ) -> F::Output
    where
        F: Future,
    {
        future.await
    }

    /// Get the runtime handle
    pub fn handle(&self
    ) -> &Handle {
        &self.handle
    }

    /// Get metrics
    pub fn metrics(&self) -> ExecutorMetrics {
        ExecutorMetrics {
            active_tasks: self.active_tasks.load(Ordering::Relaxed),
            completed_tasks: self.completed_tasks.load(Ordering::Relaxed),
            worker_threads: self.config.worker_threads,
        }
    }

    /// Shutdown the runtime gracefully
    pub async fn shutdown(&mut self
    ) {
        if self.shutdown.swap(true, Ordering::SeqCst) {
            return;
        }

        info!("Shutting down RuntimeExecutor");

        // Wait for active tasks to complete
        let start = std::time::Instant::now();
        let timeout = tokio::time::Duration::from_secs(30);

        while self.active_tasks.load(Ordering::Relaxed) > 0 {
            if start.elapsed() > timeout {
                warn!("Timeout waiting for tasks to complete");
                break;
            }
            tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        }

        if let Some(runtime) = self.runtime.take() {
            runtime.shutdown_background();
        }

        info!("RuntimeExecutor shutdown complete");
    }
}

impl Drop for RuntimeExecutor {
    fn drop(&mut self
    ) {
        if self.runtime.is_some() {
            self.runtime.take().unwrap().shutdown_background();
        }
    }
}

/// Join handle for runtime tasks
pub struct RuntimeJoinHandle<T> {
    inner: JoinHandle<T>,
}

impl<T> RuntimeJoinHandle<T> {
    /// Abort the task
    pub fn abort(&self
    ) {
        self.inner.abort();
    }

    /// Check if task is finished
    pub fn is_finished(&self
    ) -> bool {
        self.inner.is_finished()
    }
}

impl<T> Future for RuntimeJoinHandle<T> {
    type Output = Result<T, JoinError>;

    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        Pin::new(&mut self.inner).poll(cx)
    }
}

/// Executor metrics
#[derive(Debug, Clone, Copy)]
pub struct ExecutorMetrics {
    /// Active tasks
    pub active_tasks: u64,
    /// Completed tasks
    pub completed_tasks: u64,
    /// Worker threads
    pub worker_threads: usize,
}

/// Runtime handle for spawning tasks from anywhere
#[derive(Clone)]
pub struct RuntimeHandle {
    handle: Handle,
}

impl RuntimeHandle {
    /// Create from Tokio handle
    pub fn from_handle(handle: Handle) -> Self {
        Self { handle }
    }

    /// Spawn a task
    pub fn spawn<F>(&self,
        future: F
    ) -> JoinHandle<F::Output>
    where
        F: Future + Send + 'static,
        F::Output: Send + 'static,
    {
        self.handle.spawn(future)
    }

    /// Spawn blocking
    pub fn spawn_blocking<F, R>(&self,
        func: F
    ) -> JoinHandle<R>
    where
        F: FnOnce() -> R + Send + 'static,
        R: Send + 'static,
    {
        self.handle.spawn_blocking(func)
    }

    /// Current runtime handle
    pub fn current() -> Option<Self> {
        Handle::try_current().ok().map(Self::from_handle)
    }
}

impl std::fmt::Debug for RuntimeHandle {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RuntimeHandle").finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_executor_spawn() {
        let executor = RuntimeExecutor::new(RuntimeConfig::default())
            .await
            .unwrap();

        let handle = executor.spawn(async { 42 });
        let result = handle.await.unwrap();

        assert_eq!(result, 42);
    }

    #[tokio::test]
    async fn test_executor_spawn_blocking() {
        let executor = RuntimeExecutor::new(RuntimeConfig::default())
            .await
            .unwrap();

        let handle = executor.spawn_blocking(|| {
            std::thread::sleep(std::time::Duration::from_millis(10));
            42
        });
        let result = handle.await.unwrap();

        assert_eq!(result, 42);
    }

    #[tokio::test]
    async fn test_executor_metrics() {
        let executor = RuntimeExecutor::new(RuntimeConfig::default())
            .await
            .unwrap();

        let _handle1 = executor.spawn(async { tokio::time::sleep(tokio::time::Duration::from_millis(50)).await });
        let _handle2 = executor.spawn(async { tokio::time::sleep(tokio::time::Duration::from_millis(50)).await });

        tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;

        let metrics = executor.metrics();
        assert_eq!(metrics.worker_threads, num_cpus::get());
    }
}
