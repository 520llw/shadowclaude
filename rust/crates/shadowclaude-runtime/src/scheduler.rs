//! Task scheduler with priority and cron support
//!
//! Provides:
//! - Delayed task execution
//! - Periodic/cron tasks
//! - Priority-based scheduling
//! - Task persistence

use crate::concurrency::Priority;
use chrono::{DateTime, Utc};
use cron::Schedule as CronSchedule;
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::cmp::Reverse;
use std::collections::BinaryHeap;
use std::future::Future;
use std::pin::Pin;
use std::str::FromStr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, oneshot, RwLock};
use tokio::task::JoinHandle;
use tracing::{debug, error, info, warn};
use uuid::Uuid;

/// Scheduler configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchedulerConfig {
    /// Max scheduled tasks
    pub max_tasks: usize,
    /// Worker thread count
    pub worker_threads: usize,
    /// Default task timeout
    pub default_timeout_secs: u64,
    /// Enable persistence
    pub enable_persistence: bool,
}

impl Default for SchedulerConfig {
    fn default() -> Self {
        Self {
            max_tasks: 10000,
            worker_threads: 4,
            default_timeout_secs: 300,
            enable_persistence: false,
        }
    }
}

/// Task priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum TaskPriority {
    /// Critical - run immediately
    Critical = 0,
    /// High priority
    High = 1,
    /// Normal priority
    Normal = 2,
    /// Low priority
    Low = 3,
    /// Background
    Background = 4,
}

impl Default for TaskPriority {
    fn default() -> Self {
        TaskPriority::Normal
    }
}

impl From<TaskPriority> for Priority {
    fn from(p: TaskPriority) -> Self {
        match p {
            TaskPriority::Critical => Priority::Critical,
            TaskPriority::High => Priority::High,
            TaskPriority::Normal => Priority::Normal,
            TaskPriority::Low => Priority::Low,
            TaskPriority::Background => Priority::Background,
        }
    }
}

/// Unique task ID
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TaskId(pub Uuid);

impl TaskId {
    /// Generate new task ID
    pub fn new() -> Self {
        Self(Uuid::new_v4())
    }
}

impl Default for TaskId {
    fn default() -> Self {
        Self::new()
    }
}

/// Scheduled task definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduledTask {
    /// Task ID
    pub id: TaskId,
    /// Task name
    pub name: String,
    /// Priority
    pub priority: TaskPriority,
    /// Schedule type
    pub schedule: ScheduleType,
    /// Max retries
    pub max_retries: u32,
    /// Task timeout
    pub timeout_secs: u64,
    /// Created at
    pub created_at: DateTime<Utc>,
    /// Metadata
    pub metadata: serde_json::Value,
}

impl ScheduledTask {
    /// Create a new one-time task
    pub fn once(name: impl Into<String>, run_at: DateTime<Utc>) -> Self {
        Self {
            id: TaskId::new(),
            name: name.into(),
            priority: TaskPriority::Normal,
            schedule: ScheduleType::Once { run_at },
            max_retries: 0,
            timeout_secs: 300,
            created_at: Utc::now(),
            metadata: serde_json::Value::Null,
        }
    }

    /// Create a periodic task
    pub fn periodic(
        name: impl Into<String>,
        interval: Duration,
    ) -> Self {
        Self {
            id: TaskId::new(),
            name: name.into(),
            priority: TaskPriority::Normal,
            schedule: ScheduleType::Periodic {
                interval,
                last_run: None,
            },
            max_retries: 0,
            timeout_secs: 300,
            created_at: Utc::now(),
            metadata: serde_json::Value::Null,
        }
    }

    /// Create a cron task
    pub fn cron(
        name: impl Into<String>,
        expression: &str,
    ) -> Result<Self, cron::error::Error> {
        let schedule = CronSchedule::from_str(expression)?;

        Ok(Self {
            id: TaskId::new(),
            name: name.into(),
            priority: TaskPriority::Normal,
            schedule: ScheduleType::Cron {
                expression: expression.to_string(),
                schedule,
            },
            max_retries: 0,
            timeout_secs: 300,
            created_at: Utc::now(),
            metadata: serde_json::Value::Null,
        })
    }

    /// Set priority
    pub fn with_priority(mut self, priority: TaskPriority) -> Self {
        self.priority = priority;
        self
    }

    /// Set max retries
    pub fn with_retries(mut self, retries: u32) -> Self {
        self.max_retries = retries;
        self
    }
}

/// Schedule types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum ScheduleType {
    /// Run once at specific time
    Once {
        /// When to run
        run_at: DateTime<Utc>,
    },
    /// Run periodically
    Periodic {
        /// Interval
        #[serde(with = "duration_serde")]
        interval: Duration,
        /// Last run time
        last_run: Option<DateTime<Utc>>,
    },
    /// Cron schedule
    Cron {
        /// Expression string
        expression: String,
        /// Parsed schedule
        #[serde(skip)]
        schedule: CronSchedule,
    },
}

impl ScheduleType {
    /// Get next run time
    pub fn next_run(&self
    ) -> Option<DateTime<Utc>> {
        let now = Utc::now();

        match self {
            ScheduleType::Once { run_at } => {
                if *run_at > now {
                    Some(*run_at)
                } else {
                    None
                }
            }
            ScheduleType::Periodic { interval, last_run } => {
                last_run.map(|t| t + chrono::Duration::from_std(*interval).unwrap_or_default())
                    .or(Some(now))
            }
            ScheduleType::Cron { schedule, .. } => {
                schedule.upcoming(Utc).next()
            }
        }
    }

    /// Check if should run now
    pub fn should_run(&self
    ) -> bool {
        match self.next_run() {
            Some(next) => next <= Utc::now(),
            None => false,
        }
    }

    /// Update after run
    pub fn after_run(&mut self
    ) {
        match self {
            ScheduleType::Periodic { last_run, .. } => {
                *last_run = Some(Utc::now());
            }
            _ => {}
        }
    }
}

/// Queue entry for internal scheduling
#[derive(Debug, Clone)]
struct QueueEntry {
    /// Next run time
    next_run: DateTime<Utc>,
    /// Priority
    priority: TaskPriority,
    /// Task ID
    task_id: TaskId,
}

impl PartialEq for QueueEntry {
    fn eq(&self, other: &Self) -> bool {
        self.next_run == other.next_run && self.priority == other.priority
    }
}

impl Eq for QueueEntry {}

impl PartialOrd for QueueEntry {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for QueueEntry {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        // Earlier time = higher priority
        self.next_run
            .cmp(&other.next_run)
            .then_with(|| self.priority.cmp(&other.priority))
    }
}

/// Task scheduler
pub struct Scheduler {
    /// Configuration
    config: SchedulerConfig,
    /// Task storage
    tasks: DashMap<TaskId, ScheduledTask>,
    /// Priority queue
    queue: RwLock<BinaryHeap<QueueEntry>>,
    /// Control channel
    control_tx: mpsc::Sender<SchedulerCommand>,
    /// Control receiver
    control_rx: RwLock<mpsc::Receiver<SchedulerCommand>>,
    /// Active task handles
    active_tasks: DashMap<TaskId, JoinHandle<()>>,
    /// Shutdown flag
    shutdown: Arc<AtomicBool>,
}

impl Scheduler {
    /// Create a new scheduler
    pub async fn new(config: SchedulerConfig) -> std::io::Result<Self> {
        let (control_tx, control_rx) = mpsc::channel(100);

        let scheduler = Self {
            config,
            tasks: DashMap::new(),
            queue: RwLock::new(BinaryHeap::new()),
            control_tx,
            control_rx: RwLock::new(control_rx),
            active_tasks: DashMap::new(),
            shutdown: Arc::new(AtomicBool::new(false)),
        };

        // Start scheduler loop
        scheduler.start_scheduler_loop().await;

        Ok(scheduler)
    }

    /// Schedule a task
    pub async fn schedule(
        &self,
        task: ScheduledTask,
    ) -> Result<TaskId, SchedulerError> {
        if self.tasks.len() >= self.config.max_tasks {
            return Err(SchedulerError::MaxTasksReached);
        }

        let next_run = task.schedule.next_run()
            .ok_or(SchedulerError::InvalidSchedule)?;

        let task_id = task.id;

        // Store task
        self.tasks.insert(task_id, task);

        // Add to queue
        let entry = QueueEntry {
            next_run,
            priority: TaskPriority::Normal,
            task_id,
        };
        self.queue.write().await.push(entry);

        // Notify scheduler
        let _ = self.control_tx.send(SchedulerCommand::NewTask).await;

        info!(task_id = %task_id.0, "Task scheduled");
        Ok(task_id)
    }

    /// Cancel a task
    pub async fn cancel(&self,
        task_id: TaskId
    ) -> bool {
        if let Some((_, task)) = self.tasks.remove(&task_id) {
            // Cancel if running
            if let Some((_, handle)) = self.active_tasks.remove(&task_id) {
                handle.abort();
            }

            info!(task_id = %task_id.0, "Task cancelled");
            true
        } else {
            false
        }
    }

    /// Get task info
    pub fn get_task(&self,
        task_id: TaskId
    ) -> Option<ScheduledTask> {
        self.tasks.get(&task_id).map(|t| t.clone())
    }

    /// List all tasks
    pub fn list_tasks(&self
    ) -> Vec<ScheduledTask> {
        self.tasks.iter().map(|t| t.clone()).collect()
    }

    /// Get queue depth
    pub fn queue_depth(&self
    ) -> usize {
        self.queue.try_read().map(|q| q.len()).unwrap_or(0)
    }

    /// Shutdown the scheduler
    pub async fn shutdown(&self
    ) {
        self.shutdown.store(true, Ordering::SeqCst);

        // Cancel all active tasks
        for (task_id, (_, handle)) in self.active_tasks.clone().into_iter() {
            handle.abort();
            info!(task_id = %task_id.0, "Cancelled active task");
        }

        info!("Scheduler shutdown complete");
    }

    async fn start_scheduler_loop(&self
    ) {
        let shutdown = self.shutdown.clone();
        let tasks = self.tasks.clone();
        let queue = self.queue.clone();
        let active_tasks = self.active_tasks.clone();
        let mut control_rx = self.control_rx.write().await;

        tokio::spawn(async move {
            while !shutdown.load(Ordering::Relaxed) {
                tokio::select! {
                    _ = tokio::time::sleep(Duration::from_millis(100)) => {
                        Self::process_ready_tasks(&tasks,&queue,&active_tasks,&shutdown
                        ).await;
                    }
                    Some(cmd) = control_rx.recv() => {
                        match cmd {
                            SchedulerCommand::NewTask => {
                                Self::process_ready_tasks(&tasks,&queue,&active_tasks,&shutdown
                                ).await;
                            }
                            SchedulerCommand::Shutdown => break,
                        }
                    }
                }
            }
        });
    }

    async fn process_ready_tasks(
        tasks: &DashMap<TaskId, ScheduledTask>,
        queue: &RwLock<BinaryHeap<QueueEntry>>,
        active_tasks: &DashMap<TaskId, JoinHandle<()>>,
        shutdown: &AtomicBool,
    ) {
        let now = Utc::now();
        let mut ready_tasks = Vec::new();

        // Find ready tasks
        {
            let mut q = queue.write().await;
            while let Some(entry) = q.peek() {
                if entry.next_run <= now {
                    ready_tasks.push(q.pop().unwrap());
                } else {
                    break;
                }
            }
        }

        // Execute ready tasks
        for entry in ready_tasks {
            if shutdown.load(Ordering::Relaxed) {
                break;
            }

            if let Some(task) = tasks.get(&entry.task_id) {
                let task = task.clone();
                let handle = tokio::spawn(async move {
                    info!(task_id = %task.id.0, "Executing scheduled task");
                    // Task execution logic here
                    tokio::time::sleep(Duration::from_millis(10)).await;
                    info!(task_id = %task.id.0, "Task completed");
                });

                active_tasks.insert(entry.task_id, handle);
            }
        }
    }
}

/// Scheduler commands
enum SchedulerCommand {
    /// New task added
    NewTask,
    /// Shutdown
    Shutdown,
}

/// Scheduler errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchedulerError {
    /// Max tasks reached
    MaxTasksReached,
    /// Invalid schedule
    InvalidSchedule,
    /// Task not found
    TaskNotFound,
}

impl std::fmt::Display for SchedulerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SchedulerError::MaxTasksReached => write!(f, "Maximum tasks reached"),
            SchedulerError::InvalidSchedule => write!(f, "Invalid schedule"),
            SchedulerError::TaskNotFound => write!(f, "Task not found"),
        }
    }
}

impl std::error::Error for SchedulerError {}

/// Duration serialization helper
mod duration_serde {
    use serde::{Deserialize, Deserializer, Serializer};
    use std::time::Duration;

    pub fn serialize<S>(duration: &Duration, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_u64(duration.as_secs())
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Duration, D::Error>
    where
        D: Deserializer<'de>,
    {
        let secs = u64::deserialize(deserializer)?;
        Ok(Duration::from_secs(secs))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_schedule_type_once() {
        let future = Utc::now() + chrono::Duration::seconds(60);
        let schedule = ScheduleType::Once { run_at: future };

        assert!(schedule.next_run().is_some());
        assert!(!schedule.should_run());
    }

    #[test]
    fn test_schedule_type_periodic() {
        let schedule = ScheduleType::Periodic {
            interval: Duration::from_secs(60),
            last_run: None,
        };

        assert!(schedule.should_run());
    }

    #[test]
    fn test_cron_parsing() {
        let task = ScheduledTask::cron("test", "0 0 * * * *");
        assert!(task.is_ok());

        let task = ScheduledTask::cron("test", "invalid");
        assert!(task.is_err());
    }

    #[tokio::test]
    async fn test_scheduler() {
        let scheduler = Scheduler::new(SchedulerConfig::default())
            .await
            .unwrap();

        let task = ScheduledTask::once("test_task", Utc::now());
        let id = scheduler.schedule(task).await.unwrap();

        assert!(scheduler.get_task(id).is_some());

        scheduler.shutdown().await;
    }
}
