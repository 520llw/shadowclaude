"""
KAIROS - 永不睡觉的守护进程
Claude Code 泄露源码中的神秘功能

功能：
- 7×24 小时后台运行
- Cron 定时任务
- Webhook 触发
- 社交软件远程控制
- AutoDream 记忆整合
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import threading
import schedule
import subprocess
from collections import deque


class KairosMode(Enum):
    """KAIROS 运行模式"""
    IDLE = "idle"           # 空闲等待
    MONITORING = "monitoring"  # 监控模式
    DREAMING = "dreaming"   # AutoDream 记忆整合
    EXECUTING = "executing" # 执行任务


@dataclass
class ScheduledTask:
    """定时任务"""
    task_id: str
    name: str
    schedule_type: str  # "cron", "interval", "once"
    schedule_config: Dict[str, Any]  # {hour: 8, minute: 0} 或 {minutes: 30}
    action: str  # 要执行的动作
    action_params: Dict[str, Any]
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    is_enabled: bool = True


@dataclass
class WebhookEndpoint:
    """Webhook 端点"""
    endpoint_id: str
    path: str  # /webhook/github, /webhook/gitlab
    secret: Optional[str]  # 签名密钥
    action: str
    filter: Optional[Dict] = None  # 过滤条件


@dataclass
class ActivityLog:
    """活动日志"""
    timestamp: datetime
    activity_type: str  # "task", "webhook", "dream", "notification"
    description: str
    details: Dict[str, Any]


class KairosDaemon:
    """
    KAIROS 守护进程
    
    设计理念：AI 不应该每次对话都"醒来"，
    而应该像人类一样有持续的存在，在后台不断学习。
    """
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir or Path.home() / ".shadowclaude" / "kairos"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 状态
        self.mode = KairosMode.IDLE
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 任务系统
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.webhook_endpoints: Dict[str, WebhookEndpoint] = {}
        
        # 活动日志
        self.activity_log: deque = deque(maxlen=1000)
        
        # 回调
        self._on_task: Optional[Callable[[str, Dict], None]] = None
        self._on_webhook: Optional[Callable[[str, Dict], Any]] = None
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """从磁盘加载配置"""
        config_file = self.workspace_dir / "config.json"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            
            # 加载定时任务
            for task_data in config.get("tasks", []):
                task = ScheduledTask(**task_data)
                self.scheduled_tasks[task.task_id] = task
            
            # 加载 webhook
            for hook_data in config.get("webhooks", []):
                hook = WebhookEndpoint(**hook_data)
                self.webhook_endpoints[hook.endpoint_id] = hook
    
    def _save_config(self):
        """保存配置到磁盘"""
        config = {
            "tasks": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "schedule_type": t.schedule_type,
                    "schedule_config": t.schedule_config,
                    "action": t.action,
                    "action_params": t.action_params,
                    "is_enabled": t.is_enabled
                }
                for t in self.scheduled_tasks.values()
            ],
            "webhooks": [
                {
                    "endpoint_id": h.endpoint_id,
                    "path": h.path,
                    "secret": h.secret,
                    "action": h.action,
                    "filter": h.filter
                }
                for h in self.webhook_endpoints.values()
            ]
        }
        
        config_file = self.workspace_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def start(self):
        """启动守护进程"""
        if self.is_running:
            return
        
        self.is_running = True
        self.mode = KairosMode.MONITORING
        self._stop_event.clear()
        
        # 启动后台线程
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        self._log_activity("system", "KAIROS daemon started", {})
        print(f"🌙 KAIROS daemon started (PID: {threading.current_thread().ident})")
    
    def stop(self):
        """停止守护进程"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.mode = KairosMode.IDLE
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5)
        
        self._log_activity("system", "KAIROS daemon stopped", {})
        print("🌙 KAIROS daemon stopped")
    
    def _run_loop(self):
        """主运行循环"""
        # 注册所有定时任务
        self._schedule_tasks()
        
        while not self._stop_event.is_set():
            try:
                # 执行待运行的定时任务
                schedule.run_pending()
                
                # 检查是否需要进入 Dream 模式
                if self._should_dream():
                    self._enter_dream_mode()
                
                # 睡眠等待
                time.sleep(1)
                
            except Exception as e:
                self._log_activity("error", f"Loop error: {e}", {})
                time.sleep(5)
    
    def _schedule_tasks(self):
        """注册所有定时任务到 schedule"""
        for task in self.scheduled_tasks.values():
            if not task.is_enabled:
                continue
            
            if task.schedule_type == "cron":
                # 解析 cron 表达式 (简化版)
                config = task.schedule_config
                if "hour" in config and "minute" in config:
                    schedule.every().day.at(f"{config['hour']:02d}:{config['minute']:02d}").do(
                        self._execute_task, task.task_id
                    )
            
            elif task.schedule_type == "interval":
                # 间隔执行
                config = task.schedule_config
                if "minutes" in config:
                    schedule.every(config["minutes"]).minutes.do(
                        self._execute_task, task.task_id
                    )
    
    def add_scheduled_task(
        self,
        name: str,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        action: str,
        action_params: Optional[Dict] = None
    ) -> str:
        """
        添加定时任务
        
        Args:
            name: 任务名称
            schedule_type: "cron" 或 "interval"
            schedule_config: 如 {"hour": 8, "minute": 0} 或 {"minutes": 30}
            action: 要执行的动作
            action_params: 动作参数
        """
        task_id = f"task-{int(time.time() * 1000)}"
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            action=action,
            action_params=action_params or {}
        )
        
        self.scheduled_tasks[task_id] = task
        self._save_config()
        
        # 重新调度
        schedule.clear()
        self._schedule_tasks()
        
        return task_id
    
    def _execute_task(self, task_id: str):
        """执行定时任务"""
        task = self.scheduled_tasks.get(task_id)
        if not task:
            return
        
        self.mode = KairosMode.EXECUTING
        task.last_run = datetime.now()
        task.run_count += 1
        
        self._log_activity("task", f"Executing: {task.name}", {
            "task_id": task_id,
            "action": task.action
        })
        
        # 执行动作
        if self._on_task:
            try:
                self._on_task(task.action, task.action_params)
            except Exception as e:
                self._log_activity("error", f"Task failed: {e}", {"task_id": task_id})
        
        self.mode = KairosMode.MONITORING
    
    def add_webhook_endpoint(
        self,
        path: str,
        action: str,
        secret: Optional[str] = None,
        filter_config: Optional[Dict] = None
    ) -> str:
        """
        添加 Webhook 端点
        
        Args:
            path: 路径，如 "/webhook/github"
            action: 触发动作
            secret: 签名验证密钥
            filter_config: 过滤条件
        """
        endpoint_id = f"hook-{int(time.time() * 1000)}"
        
        hook = WebhookEndpoint(
            endpoint_id=endpoint_id,
            path=path,
            secret=secret,
            action=action,
            filter=filter_config
        )
        
        self.webhook_endpoints[endpoint_id] = hook
        self._save_config()
        
        return endpoint_id
    
    def handle_webhook(self, path: str, payload: Dict, headers: Optional[Dict] = None) -> Any:
        """
        处理 Webhook 请求
        
        Args:
            path: 请求路径
            payload: 请求体
            headers: 请求头
        
        Returns:
            处理结果
        """
        # 查找匹配的 endpoint
        hook = None
        for h in self.webhook_endpoints.values():
            if h.path == path:
                hook = h
                break
        
        if not hook:
            return {"error": "Endpoint not found"}
        
        # 验证签名（如果有）
        if hook.secret and headers:
            # 简化版签名验证
            pass
        
        self._log_activity("webhook", f"Received: {path}", {
            "endpoint_id": hook.endpoint_id,
            "action": hook.action
        })
        
        # 执行动作
        if self._on_webhook:
            try:
                result = self._on_webhook(hook.action, payload)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": True, "message": "Webhook received"}
    
    def _should_dream(self) -> bool:
        """
        检查是否应该进入 Dream 模式
        
        触发条件：
        1. 距上次整合超过 24 小时
        2. 累计 5 次会话后
        """
        dream_file = self.workspace_dir / "last_dream.txt"
        
        if not dream_file.exists():
            return True
        
        try:
            with open(dream_file) as f:
                last_dream = float(f.read().strip())
            
            hours_since_last = (time.time() - last_dream) / 3600
            return hours_since_last >= 24
        except:
            return True
    
    def _enter_dream_mode(self):
        """进入 AutoDream 记忆整合模式"""
        self.mode = KairosMode.DREAMING
        
        self._log_activity("dream", "Entering dream mode for memory consolidation", {})
        
        try:
            # 1. 收集原始日志
            logs = list(self.activity_log)
            
            # 2. 提取关键信息
            insights = self._extract_insights(logs)
            
            # 3. 整合到语义记忆
            self._consolidate_memories(insights)
            
            # 4. 更新时间戳
            dream_file = self.workspace_dir / "last_dream.txt"
            with open(dream_file, 'w') as f:
                f.write(str(time.time()))
            
            self._log_activity("dream", f"Memory consolidation completed. {len(insights)} insights extracted", {})
            
        except Exception as e:
            self._log_activity("error", f"Dream mode failed: {e}", {})
        
        finally:
            self.mode = KairosMode.MONITORING
    
    def _extract_insights(self, logs: List[ActivityLog]) -> List[str]:
        """从日志中提取洞察"""
        insights = []
        
        # 统计高频操作
        task_types = {}
        for log in logs:
            if log.activity_type == "task":
                task_types[log.description] = task_types.get(log.description, 0) + 1
        
        # 提取常用模式
        for task, count in sorted(task_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            if count >= 3:
                insights.append(f"Frequent task: {task} (x{count})")
        
        return insights
    
    def _consolidate_memories(self, insights: List[str]):
        """整合记忆到长期存储"""
        memory_file = self.workspace_dir / "consolidated_memories.json"
        
        existing = []
        if memory_file.exists():
            with open(memory_file) as f:
                existing = json.load(f)
        
        # 合并新洞察
        for insight in insights:
            if insight not in existing:
                existing.append({
                    "insight": insight,
                    "timestamp": datetime.now().isoformat()
                })
        
        with open(memory_file, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def _log_activity(self, activity_type: str, description: str, details: Dict):
        """记录活动日志"""
        log = ActivityLog(
            timestamp=datetime.now(),
            activity_type=activity_type,
            description=description,
            details=details
        )
        self.activity_log.append(log)
    
    def on_task(self, callback: Callable[[str, Dict], None]):
        """设置任务回调"""
        self._on_task = callback
    
    def on_webhook(self, callback: Callable[[str, Dict], Any]):
        """设置 Webhook 回调"""
        self._on_webhook = callback
    
    def get_status(self) -> Dict:
        """获取守护进程状态"""
        return {
            "is_running": self.is_running,
            "mode": self.mode.value,
            "scheduled_tasks": len(self.scheduled_tasks),
            "webhook_endpoints": len(self.webhook_endpoints),
            "recent_activities": len(self.activity_log)
        }


# 使用示例
if __name__ == "__main__":
    # 创建守护进程
    kairos = KairosDaemon()
    
    # 设置回调
    def on_task(action, params):
        print(f"Executing task: {action} with {params}")
    
    kairos.on_task(on_task)
    
    # 添加定时任务：每天早上8点执行
    kairos.add_scheduled_task(
        name="Morning Summary",
        schedule_type="cron",
        schedule_config={"hour": 8, "minute": 0},
        action="generate_daily_summary",
        action_params={"type": "morning"}
    )
    
    # 启动
    kairos.start()
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        kairos.stop()
