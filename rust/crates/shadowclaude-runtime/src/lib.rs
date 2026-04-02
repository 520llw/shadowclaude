//! ShadowClaude Runtime - Tokio-based async runtime
//!
//! This crate provides:
//! - Tokio async runtime integration
//! - Concurrency control (Semaphore, Mutex)
//! - Task scheduling
//! - Timeout and cancellation mechanisms
//! - Background task management

#![warn(missing_docs)]
#![warn(rust_2018_idioms)]

pub mod concurrency;
pub mod executor;
pub mod scheduler;
pub mod task;
pub mod timeout;

pub use concurrency::{ConcurrencyLimiter, LimitConfig, PrioritySemaphore};
pub use executor::{RuntimeConfig, RuntimeExecutor, RuntimeHandle};
pub use scheduler::{ScheduledTask, Scheduler, SchedulerConfig, TaskPriority};
pub use task::{BackgroundTask, TaskCancellation, TaskHandle, TaskManager};
pub use timeout::{TimeoutConfig, TimeoutManager, TimeoutPolicy};

use std::sync::Arc;
use tracing::info;

/// Runtime version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Initialize the runtime
pub fn init() {
    info!("ShadowClaude Runtime v{} initialized", VERSION);
}

/// Runtime builder
#[derive(Debug, Clone)]
pub struct RuntimeBuilder {
    /// Worker threads
    worker_threads: usize,
    /// Max blocking threads
    max_blocking_threads: usize,
    /// Thread stack size
    thread_stack_size: usize,
    /// Enable metrics
    enable_metrics: bool,
}

impl RuntimeBuilder {
    /// Create a new runtime builder
    pub fn new() -> Self {
        Self {
            worker_threads: num_cpus::get(),
            max_blocking_threads: 512,
            thread_stack_size: 2 * 1024 * 1024,
            enable_metrics: true,
        }
    }

    /// Set worker threads
    pub fn worker_threads(mut self, threads: usize) -> Self {
        self.worker_threads = threads;
        self
    }

    /// Set max blocking threads
    pub fn max_blocking_threads(mut self, threads: usize) -> Self {
        self.max_blocking_threads = threads;
        self
    }

    /// Set thread stack size
    pub fn thread_stack_size(mut self, size: usize) -> Self {
        self.thread_stack_size = size;
        self
    }

    /// Build the runtime
    pub fn build(self) -> std::io::Result<tokio::runtime::Runtime> {
        tokio::runtime::Builder::new_multi_thread()
            .worker_threads(self.worker_threads)
            .max_blocking_threads(self.max_blocking_threads)
            .thread_stack_size(self.thread_stack_size)
            .enable_all()
            .build()
    }
}

impl Default for RuntimeBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Runtime metrics
#[derive(Debug, Clone, Default)]
pub struct RuntimeMetrics {
    /// Active tasks
    pub active_tasks: usize,
    /// Completed tasks
    pub completed_tasks: u64,
    /// Failed tasks
    pub failed_tasks: u64,
    /// Cancelled tasks
    pub cancelled_tasks: u64,
    /// Average task duration in ms
    pub avg_task_duration_ms: f64,
    /// Queue depth
    pub queue_depth: usize,
}

/// Global runtime handle
#[derive(Debug, Clone)]
pub struct GlobalRuntime {
    /// Executor handle
    pub executor: Arc<RuntimeExecutor>,
    /// Task manager
    pub task_manager: Arc<TaskManager>,
    /// Scheduler
    pub scheduler: Arc<Scheduler>,
    /// Timeout manager
    pub timeout_manager: Arc<TimeoutManager>,
}

impl GlobalRuntime {
    /// Create a new global runtime
    pub async fn new(config: RuntimeConfig) -> std::io::Result<Self> {
        let executor = Arc::new(RuntimeExecutor::new(config.clone()).await?);
        let task_manager = Arc::new(TaskManager::new());
        let scheduler = Arc::new(Scheduler::new(config.scheduler).await?);
        let timeout_manager = Arc::new(TimeoutManager::new(config.timeout));

        Ok(Self {
            executor,
            task_manager,
            scheduler,
            timeout_manager,
        })
    }

    /// Get current metrics
    pub fn metrics(&self) -> RuntimeMetrics {
        RuntimeMetrics {
            active_tasks: self.task_manager.active_count(),
            completed_tasks: self.task_manager.completed_count(),
            failed_tasks: self.task_manager.failed_count(),
            cancelled_tasks: self.task_manager.cancelled_count(),
            avg_task_duration_ms: self.task_manager.avg_duration_ms(),
            queue_depth: self.scheduler.queue_depth(),
        }
    }

    /// Shutdown the runtime gracefully
    pub async fn shutdown(&self
    ) {
        self.task_manager.cancel_all().await;
        self.scheduler.shutdown().await;
        self.executor.shutdown().await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_runtime_builder() {
        let builder = RuntimeBuilder::new()
            .worker_threads(4)
            .max_blocking_threads(100);

        let rt = builder.build();
        assert!(rt.is_ok());
    }

    #[test]
    fn test_runtime_builder_default() {
        let builder = RuntimeBuilder::default();
        let rt = builder.build();
        assert!(rt.is_ok());
    }
}
