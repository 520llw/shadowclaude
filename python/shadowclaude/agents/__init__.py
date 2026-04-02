"""
Agent 系统 - Coordinator + Swarm 多 Agent 协作
基于 Claude Code 的 Agent Swarm 架构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Set
from enum import Enum
from pathlib import Path
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class AgentType(Enum):
    """Agent 类型"""
    EXPLORE = "Explore"           # 探索型：只读搜索
    PLAN = "Plan"                 # 规划型：TODO + 结构化输出
    VERIFICATION = "Verification" # 验证型：可执行测试
    GENERAL = "general-purpose"   # 通用型：全权限


class AgentStatus(Enum):
    """Agent 状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """Agent 任务定义"""
    agent_id: str
    name: str
    description: str
    prompt: str
    agent_type: AgentType
    model: Optional[str] = None
    parent_id: Optional[str] = None  # 父 Agent ID
    allowed_tools: Optional[Set[str]] = None
    
    # 运行时状态
    status: AgentStatus = AgentStatus.PENDING
    output: str = ""
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class SwarmResult:
    """Swarm 执行结果"""
    results: Dict[str, AgentTask]  # agent_id -> result
    completed_count: int
    failed_count: int
    total_duration_ms: int


class PermissionManager:
    """
    六层权限防线
    基于 Claude Code 的纵深防御设计
    """
    
    # 各类型 Agent 允许的工具
    TOOL_WHITELIST = {
        AgentType.EXPLORE: {
            "read_file", "glob_search", "grep_search",
            "WebFetch", "WebSearch", "ToolSearch"
        },
        AgentType.PLAN: {
            "read_file", "TodoWrite", "StructuredOutput"
        },
        AgentType.VERIFICATION: {
            "read_file", "bash", "TodoWrite", "glob_search"
        },
        AgentType.GENERAL: {
            "read_file", "write_file", "edit_file",
            "bash", "Agent", "TodoWrite", "glob_search", "grep_search"
        }
    }
    
    def get_allowed_tools(self, agent_type: AgentType) -> Set[str]:
        """获取 Agent 类型允许的工具"""
        return self.TOOL_WHITELIST.get(agent_type, set())
    
    def check_permission(self, agent_type: AgentType, tool_name: str) -> bool:
        """检查 Agent 是否有权限使用工具"""
        allowed = self.get_allowed_tools(agent_type)
        return tool_name in allowed


class Coordinator:
    """
    Coordinator - Agent Swarm 协调器
    
    职责：
    1. 规划任务分解
    2. Fork 子 Agent
    3. 收集结果
    4. 整合输出
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.permission_manager = PermissionManager()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, AgentTask] = {}
        self._lock = threading.RLock()
    
    def create_agent(
        self,
        description: str,
        prompt: str,
        agent_type: AgentType = AgentType.GENERAL,
        name: Optional[str] = None,
        model: Optional[str] = None
    ) -> AgentTask:
        """
        创建新的 Agent 任务
        
        Args:
            description: 任务描述
            prompt: 完整提示
            agent_type: Agent 类型
            name: 可选名称
            model: 可选模型
        
        Returns:
            AgentTask 对象
        """
        agent_id = f"agent-{int(time.time() * 1000000)}"
        
        task = AgentTask(
            agent_id=agent_id,
            name=name or agent_id,
            description=description,
            prompt=prompt,
            agent_type=agent_type,
            model=model,
            allowed_tools=self.permission_manager.get_allowed_tools(agent_type)
        )
        
        with self._lock:
            self._tasks[agent_id] = task
        
        return task
    
    def fork_agents(
        self,
        tasks: List[Tuple[str, str, AgentType]],
        parallel: bool = True
    ) -> SwarmResult:
        """
        Fork 多个子 Agent 并行/串行执行
        
        Args:
            tasks: [(description, prompt, agent_type), ...]
            parallel: 是否并行执行
        
        Returns:
            SwarmResult
        """
        created_tasks = []
        for desc, prompt, agent_type in tasks:
            task = self.create_agent(desc, prompt, agent_type)
            created_tasks.append(task)
        
        start_time = time.time()
        
        if parallel:
            # 并行执行
            futures = {
                self._executor.submit(self._run_agent, task.agent_id): task.agent_id
                for task in created_tasks
            }
            
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    with self._lock:
                        self._tasks[agent_id].status = AgentStatus.FAILED
                        self._tasks[agent_id].error = str(e)
        else:
            # 串行执行
            for task in created_tasks:
                self._run_agent(task.agent_id)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 统计结果
        completed = sum(1 for t in self._tasks.values() 
                       if t.status == AgentStatus.COMPLETED)
        failed = sum(1 for t in self._tasks.values() 
                    if t.status == AgentStatus.FAILED)
        
        return SwarmResult(
            results={t.agent_id: t for t in created_tasks},
            completed_count=completed,
            failed_count=failed,
            total_duration_ms=duration_ms
        )
    
    def _run_agent(self, agent_id: str):
        """运行单个 Agent"""
        with self._lock:
            task = self._tasks.get(agent_id)
            if not task:
                return
            
            task.status = AgentStatus.RUNNING
            task.started_at = time.time()
        
        try:
            # 模拟 Agent 执行（实际应调用 LLM）
            # 这里简化处理，实际实现需要完整的 LLM 调用逻辑
            
            # 构建受限的提示
            restricted_prompt = self._build_restricted_prompt(task)
            
            # 执行（模拟）
            output = f"Agent {task.name} completed task:\n{task.prompt[:200]}..."
            
            with self._lock:
                task.output = output
                task.status = AgentStatus.COMPLETED
                task.completed_at = time.time()
                
        except Exception as e:
            with self._lock:
                task.error = str(e)
                task.status = AgentStatus.FAILED
                task.completed_at = time.time()
    
    def _build_restricted_prompt(self, task: AgentTask) -> str:
        """构建受限的 Agent 提示"""
        tools_list = ", ".join(sorted(task.allowed_tools or set()))
        
        return f"""You are a specialized sub-agent of type: {task.agent_type.value}

## Your Task
{task.description}

## Instructions
{task.prompt}

## Allowed Tools
You can ONLY use these tools: {tools_list}
If you need a tool not in this list, use ToolSearch to find it.

## Output Format
Provide your response in a structured format:
- Summary: Brief summary of findings
- Details: Detailed information
- Conclusion: Final conclusion or recommendation
"""
    
    def get_task_summary(self, agent_id: str) -> Optional[str]:
        """获取任务摘要"""
        with self._lock:
            task = self._tasks.get(agent_id)
            if not task:
                return None
            
            return f"""## Task Summary
- **ID**: {task.agent_id}
- **Name**: {task.name}
- **Type**: {task.agent_type.value}
- **Status**: {task.status.value}
- **Duration**: {self._format_duration(task)}ms

## Output
{task.output[:500] if task.output else "(No output yet)"}
"""
    
    def _format_duration(self, task: AgentTask) -> str:
        """格式化持续时间"""
        if task.started_at and task.completed_at:
            return f"{int((task.completed_at - task.started_at) * 1000)}"
        elif task.started_at:
            return f"{int((time.time() - task.started_at) * 1000)} (running)"
        return "N/A"
    
    def integrate_results(self, swarm_result: SwarmResult) -> str:
        """
        整合 Swarm 结果
        
        将多个 Agent 的输出合并成连贯的回复
        """
        parts = ["## Multi-Agent Analysis Results\n"]
        
        for agent_id, task in swarm_result.results.items():
            parts.append(f"\n### {task.name} ({task.agent_type.value})")
            parts.append(f"Status: {task.status.value}")
            
            if task.output:
                parts.append(f"\n{task.output[:300]}...")
            
            if task.error:
                parts.append(f"\n⚠️ Error: {task.error}")
        
        parts.append(f"\n---")
        parts.append(f"Completed: {swarm_result.completed_count}/{len(swarm_result.results)}")
        parts.append(f"Failed: {swarm_result.failed_count}")
        parts.append(f"Duration: {swarm_result.total_duration_ms}ms")
        
        return "\n".join(parts)


class SwarmWorker:
    """
    Swarm Worker - 实际执行任务的子 Agent
    
    在隔离的上下文中运行，只保留结论
    """
    
    def __init__(self, coordinator: Coordinator, parent_context: Optional[Dict] = None):
        self.coordinator = coordinator
        self.parent_context = parent_context or {}
        self.local_context: Dict[str, Any] = {}
    
    def execute(
        self,
        task: AgentTask,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        执行任务
        
        Args:
            task: AgentTask
            on_progress: 进度回调
        
        Returns:
            任务输出
        """
        if on_progress:
            on_progress(f"Starting {task.name}...")
        
        # 模拟执行
        # 实际实现中，这里会调用 LLM API
        
        # 构建完整的执行上下文
        execution_prompt = self._build_execution_prompt(task)
        
        # 执行任务（模拟）
        output = f"Task completed. Found relevant information about: {task.description}"
        
        if on_progress:
            on_progress("Task completed.")
        
        return output
    
    def _build_execution_prompt(self, task: AgentTask) -> str:
        """构建执行提示"""
        return f"""## Execution Context
{json.dumps(self.parent_context, indent=2)}

## Your Task
{task.description}

## Instructions
{task.prompt}

## Constraints
- Use only allowed tools: {task.allowed_tools}
- Focus on the specific task
- Provide concise, actionable output
"""


class MultiStepPlanner:
    """
    多步骤规划器
    
    将复杂任务分解为多个步骤，每个步骤由一个 Agent 执行
    """
    
    def __init__(self, coordinator: Coordinator):
        self.coordinator = coordinator
    
    def plan_and_execute(self, goal: str, context: Optional[Dict] = None) -> str:
        """
        规划并执行多步骤任务
        
        Args:
            goal: 目标描述
            context: 上下文信息
        
        Returns:
            执行结果
        """
        # Step 1: Plan Agent 创建计划
        plan_task = self.coordinator.create_agent(
            description="Create execution plan",
            prompt=f"""Goal: {goal}

Break this goal into 3-5 concrete steps.
For each step, specify:
1. What needs to be done
2. What tools are needed
3. Expected output

Return as JSON array of steps.""",
            agent_type=AgentType.PLAN,
            name="Planner"
        )
        
        # 执行规划
        self.coordinator._run_agent(plan_task.agent_id)
        
        # 解析计划
        steps = self._parse_plan(plan_task.output)
        
        # Step 2: 为每个步骤创建 Agent
        step_tasks = []
        for i, step in enumerate(steps):
            task = self.coordinator.create_agent(
                description=step["description"],
                prompt=step["instructions"],
                agent_type=AgentType.GENERAL,
                name=f"Step-{i+1}"
            )
            step_tasks.append(task)
        
        # Step 3: 串行执行（步骤之间有依赖）
        results = []
        for task in step_tasks:
            self.coordinator._run_agent(task.agent_id)
            results.append({
                "step": task.name,
                "output": task.output,
                "status": task.status.value
            })
        
        # Step 4: 整合结果
        summary = self._summarize_results(goal, results)
        
        return summary
    
    def _parse_plan(self, plan_output: str) -> List[Dict]:
        """解析计划输出"""
        # 尝试解析 JSON
        try:
            # 查找 JSON 块
            import re
            json_match = re.search(r'\[.*?\]', plan_output, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # 回退：返回默认步骤
        return [
            {"description": "Analyze requirements", "instructions": "Understand the goal"},
            {"description": "Execute task", "instructions": "Complete the main work"},
            {"description": "Verify results", "instructions": "Check the output"}
        ]
    
    def _summarize_results(self, goal: str, results: List[Dict]) -> str:
        """总结执行结果"""
        lines = [f"## Execution Results for: {goal}\n"]
        
        for result in results:
            lines.append(f"### {result['step']}")
            lines.append(f"Status: {result['status']}")
            lines.append(f"Output: {result['output'][:200]}...")
            lines.append("")
        
        return "\n".join(lines)
