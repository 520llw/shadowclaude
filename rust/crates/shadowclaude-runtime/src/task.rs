//! Task management with cancellation support
//!
//! Provides:
//! - Background task management
//! - Task cancellation tokens
//! - Task handles
//! - Task lifecycle management

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::task::{Context, Poll, Waker};
use std::time::Duration;
use tokio::task::{AbortHandle, JoinError, JoinHandle};
use tokio::time::Instant;
use tracing::{debug, error, info, warn};
use uuid::Uuid;

/// Unique task identifier
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TaskId(pub Uuid);

impl TaskId {
    /// Create new task ID
    pub fn new() -> Self {
        Self(Uuid::new_v4())
    }
}

impl Default for TaskId {
    fn default() -> Self {
        Self::new()
    }
}

/// Task state
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TaskState {
    /// Task is pending
    Pending,
    /// Task is running
    Running,
    /// Task completed successfully
    Completed,
    /// Task failed
    Failed,
    /// Task was cancelled
    Cancelled,
}

impl TaskState {
    /// Check if task is active
    pub fn is_active(&self
    ) -> bool {
        matches!(self, TaskState::Pending | TaskState::Running)
    }

    /// Check if task is complete
    pub fn is_complete(&self
    ) -> bool {
        matches!(self, TaskState::Completed | TaskState::Failed | TaskState::Cancelled)
    }
}

/// Task information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskInfo {
    /// Task ID
    pub id: TaskId,
    /// Task name
    pub name: String,
    /// Current state
    pub state: TaskState,
    /// Created at
    pub created_at: Instant,
    /// Started at
    pub started_at: Option<Instant>,
    /// Completed at
    pub completed_at: Option<Instant>,
    /// Progress (0-100)
    pub progress: u8,
}

impl TaskInfo {
    /// Create new task info
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            id: TaskId::new(),
            name: name.into(),
            state: TaskState::Pending,
            created_at: Instant::now(),
            started_at: None,
            completed_at: None,
            progress: 0,
        }
    }

    /// Get duration
    pub fn duration(&self
    ) -> Option<Duration> {
        match (self.started_at, self.completed_at) {
            (Some(start), Some(end)) => Some(end.duration_since(start)),
            (Some(start), None) => Some(Instant::now().duration_since(start)),
            _ => None,
        }
    }
}

/// Cancellation token for cooperative cancellation
#[derive(Debug, Clone)]
pub struct TaskCancellation {
    /// Cancelled flag
    cancelled: Arc<AtomicBool>,
    /// Wakers to notify
    wakers: Arc<DashMap<TaskId, Waker>>,
}

impl TaskCancellation {
    /// Create a new cancellation token
    pub fn new() -> Self {
        Self {
            cancelled: Arc::new(AtomicBool::new(false)),
            wakers: Arc::new(DashMap::new()),
        }
    }

    /// Check if cancelled
    pub fn is_cancelled(&self
    ) -> bool {
        self.cancelled.load(Ordering::Relaxed)
    }

    /// Cancel the task
    pub fn cancel(&self
    ) {
        self.cancelled.store(true, Ordering::Relaxed);

        // Wake all waiting tasks
        for entry in self.wakers.iter() {
            entry.value().wake_by_ref();
        }
        self.wakers.clear();
    }

    /// Register a waker
    pub fn register_waker(
        &self,
        task_id: TaskId,
        waker: &Waker
    ) {
        self.wakers.insert(task_id, waker.clone());
    }

    /// Unregister a waker
    pub fn unregister_waker(
        &self,
        task_id: TaskId
    ) {
        self.wakers.remove(&task_id);
    }

    /// Create a child token
    pub fn child(&self
    ) -> Self {
        Self {
            cancelled: self.cancelled.clone(),
            wakers: Arc::new(DashMap::new()),
        }
    }
}

impl Default for TaskCancellation {
    fn default() -> Self {
        Self::new()
    }
}

impl Future for TaskCancellation {
    type Output = ();

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        if self.is_cancelled() {
            Poll::Ready(())
        } else {
            // Register waker
            Poll::Pending
        }
    }
}

/// Task handle for managing a spawned task
pub struct TaskHandle<T> {
    /// Inner join handle
    inner: JoinHandle<T>,
    /// Abort handle
    abort_handle: AbortHandle,
    /// Task info
    pub info: TaskInfo,
    /// Cancellation token
    cancellation: TaskCancellation,
}

impl<T> TaskHandle<T> {
    /// Create a new task handle
    pub fn new(inner: JoinHandle<T>, name: impl Into<String>) -> Self {
        let abort_handle = inner.abort_handle();
        let info = TaskInfo::new(name);
        let cancellation = TaskCancellation::new();

        Self {
            inner,
            abort_handle,
            info,
            cancellation,
        }
    }

    /// Abort the task
    pub fn abort(&self
    ) {
        self.abort_handle.abort();
        self.cancellation.cancel();
    }

    /// Check if task is finished
    pub fn is_finished(&self
    ) -> bool {
        self.inner.is_finished()
    }

    /// Check if task was aborted
    pub fn is_aborted(&self
    ) -> bool {
        self.abort_handle.is_aborted()
    }

    /// Get task ID
    pub fn id(&self
    ) -> TaskId {
        self.info.id
    }
}

impl<T> Future for TaskHandle<T> {
    type Output = Result<T, JoinError>;

    fn poll(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        Pin::new(&mut self.inner).poll(cx)
    }
}

/// Background task definition
pub struct BackgroundTask {
    /// Task ID
    pub id: TaskId,
    /// Task name
    pub name: String,
    /// Task future
    pub future: Pin<Box<dyn Future<Output = ()> + Send>>,
    /// Cancellation token
    pub cancellation: TaskCancellation,
}

impl BackgroundTask {
    /// Create a new background task
    pub fn new<F, Fut>(name: impl Into<String>, f: F) -> Self
    where
        F: FnOnce(TaskCancellation) -> Fut + Send + 'static,
        Fut: Future<Output = ()> + Send + 'static,
    {
        let cancellation = TaskCancellation::new();
        let future = Box::pin(f(cancellation.clone()));

        Self {
            id: TaskId::new(),
            name: name.into(),
            future,
            cancellation,
        }
    }

    /// Cancel the task
    pub fn cancel(&self
    ) {
        self.cancellation.cancel();
    }
}

/// Task manager for managing multiple tasks
pub struct TaskManager {
    /// Active tasks
    tasks: DashMap<TaskId, Box<dyn std::any::Any + Send + Sync>>,
    /// Completed task count
    completed: AtomicU64,
    /// Failed task count
    failed: AtomicU64,
    /// Cancelled task count
    cancelled: AtomicU64,
    /// Total duration
    total_duration_ms: AtomicU64,
}

impl TaskManager {
    /// Create a new task manager
    pub fn new() -> Self {
        Self {
            tasks: DashMap::new(),
            completed: AtomicU64::new(0),
            failed: AtomicU64::new(0),
            cancelled: AtomicU64::new(0),
            total_duration_ms: AtomicU64::new(0),
        }
    }

    /// Spawn a task
    pub fn spawn<F, T>(&self,
        name: impl Into<String>,
        future: F
    ) -> TaskHandle<T>
    where
        F: Future<Output = T> + Send + 'static,
        T: Send + 'static,
    {
        let handle = tokio::spawn(future);
        TaskHandle::new(handle, name)
    }

    /// Spawn a background task
    pub async fn spawn_background(&self,
        task: BackgroundTask
    ) {
        let cancellation = task.cancellation.clone();
        let id = task.id;

        tokio::spawn(async move {
            // Wait for cancellation or task completion
            tokio::select! {
                _ = task.future => {
                    info!(task_id = %id.0, "Background task completed");
                }
                _ = cancellation => {
                    info!(task_id = %id.0, "Background task cancelled");
                }
            }
        });
    }

    /// Cancel all tasks
    pub async fn cancel_all(&self
    ) {
        info!("Cancelling all tasks");

        // Clear all tasks
        self.tasks.clear();

        // Update stats
        self.cancelled.store(0, Ordering::Relaxed);
    }

    /// Get active task count
    pub fn active_count(&self
    ) -> usize {
        self.tasks.len()
    }

    /// Get completed count
    pub fn completed_count(&self
    ) -> u64 {
        self.completed.load(Ordering::Relaxed)
    }

    /// Get failed count
    pub fn failed_count(&self
    ) -> u64 {
        self.failed.load(Ordering::Relaxed)
    }

    /// Get cancelled count
    pub fn cancelled_count(&self
    ) -> u64 {
        self.cancelled.load(Ordering::Relaxed)
    }

    /// Get average duration
    pub fn avg_duration_ms(&self
    ) -> f64 {
        let completed = self.completed.load(Ordering::Relaxed);
        let total = self.total_duration_ms.load(Ordering::Relaxed);

        if completed > 0 {
            total as f64 / completed as f64
        } else {
            0.0
        }
    }
}

impl Default for TaskManager {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Debug for TaskManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TaskManager")
            .field("active", &self.active_count())
            .field("completed", &self.completed_count())
            .field("failed", &self.failed_count())
            .finish()
    }
}

/// Task progress tracker
#[derive(Debug, Clone)]
pub struct ProgressTracker {
    /// Current progress (0-100)
    progress: Arc<parking_lot::RwLock<u8>>,
    /// Cancellation token
    cancellation: TaskCancellation,
}

impl ProgressTracker {
    /// Create a new progress tracker
    pub fn new() -> Self {
        Self {
            progress: Arc::new(parking_lot::RwLock::new(0)),
            cancellation: TaskCancellation::new(),
        }
    }

    /// Get current progress
    pub fn progress(&self
    ) -> u8 {
        *self.progress.read()
    }

    /// Set progress
    pub fn set_progress(&self,
        value: u8
    ) {
        *self.progress.write() = value.min(100);
    }

    /// Increment progress
    pub fn increment(&self,
        delta: u8
    ) {
        let mut p = self.progress.write();
        *p = (*p + delta).min(100);
    }

    /// Cancel
    pub fn cancel(&self
    ) {
        self.cancellation.cancel();
    }

    /// Check if cancelled
    pub fn is_cancelled(&self
    ) -> bool {
        self.cancellation.is_cancelled()
    }
}

impl Default for ProgressTracker {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_task_cancellation() {
        let token = TaskCancellation::new();
        assert!(!token.is_cancelled());

        token.cancel();
        assert!(token.is_cancelled());
    }

    #[tokio::test]
    async fn test_task_handle() {
        let manager = TaskManager::new();

        let handle: TaskHandle<i32> = manager.spawn("test_task", async {
            tokio::time::sleep(Duration::from_millis(10)).await;
            42
        });

        assert!(!handle.is_finished());

        let result = handle.await.unwrap();
        assert_eq!(result, 42);
    }

    #[tokio::test]
    async fn test_task_abort() {
        let manager = TaskManager::new();

        let handle: TaskHandle<()> = manager.spawn("abortable_task", async {
            tokio::time::sleep(Duration::from_secs(60)).await;
        });

        handle.abort();

        tokio::time::sleep(Duration::from_millis(50)).await;
        assert!(handle.is_aborted());
    }

    #[tokio::test]
    async fn test_progress_tracker() {
        let tracker = ProgressTracker::new();

        assert_eq!(tracker.progress(), 0);

        tracker.set_progress(50);
        assert_eq!(tracker.progress(), 50);

        tracker.increment(30);
        assert_eq!(tracker.progress(), 80);

        tracker.increment(50); // Should cap at 100
        assert_eq!(tracker.progress(), 100);
    }

    #[tokio::test]
    async fn test_background_task() {
        let cancellation = TaskCancellation::new();
        let cancelled = cancellation.clone();

        let task = BackgroundTask::new("bg_task", move |cancel| async move {
            tokio::select! {
                _ = tokio::time::sleep(Duration::from_secs(60)) => {}
                _ = cancel => {}
            }
        });

        // Cancel the task
        cancelled.cancel();
        assert!(task.cancellation.is_cancelled());
    }

    #[test]
    fn test_task_state() {
        assert!(TaskState::Pending.is_active());
        assert!(TaskState::Running.is_active());
        assert!(!TaskState::Completed.is_active());
        assert!(TaskState::Completed.is_complete());
    }

    #[test]
    fn test_task_info() {
        let info = TaskInfo::new("test");
        assert_eq!(info.name, "test");
        assert_eq!(info.state, TaskState::Pending);
        assert_eq!(info.progress, 0);
    }
}
