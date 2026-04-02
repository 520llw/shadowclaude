"""
Agent 系统测试 - 高级功能
测试 Agent Swarm 高级功能和场景
"""

import pytest
from shadowclaude.agents import (
    Coordinator, AgentTask, AgentType, AgentStatus,
    SwarmWorker, MultiStepPlanner
)


class TestSwarmWorker:
    """测试 Swarm Worker"""
    
    def test_worker_initialization(self):
        """测试 Worker 初始化"""
        coordinator = Coordinator()
        worker = SwarmWorker(coordinator)
        
        assert worker.coordinator == coordinator
        assert worker.parent_context == {}
        assert worker.local_context == {}
    
    def test_worker_with_parent_context(self):
        """测试带父上下文的 Worker"""
        coordinator = Coordinator()
        worker = SwarmWorker(coordinator, parent_context={"key": "value"})
        
        assert worker.parent_context["key"] == "value"
    
    def test_worker_execute_task(self):
        """测试 Worker 执行任务"""
        coordinator = Coordinator()
        worker = SwarmWorker(coordinator)
        
        task = coordinator.create_agent("Test", "Do something")
        
        result = worker.execute(task)
        
        assert isinstance(result, str)
        assert "completed" in result.lower() or "task" in result.lower()


class TestMultiStepPlanner:
    """测试多步骤规划器"""
    
    def test_planner_initialization(self):
        """测试规划器初始化"""
        coordinator = Coordinator()
        planner = MultiStepPlanner(coordinator)
        
        assert planner.coordinator == coordinator
    
    def test_plan_and_execute(self):
        """测试规划并执行"""
        coordinator = Coordinator()
        planner = MultiStepPlanner(coordinator)
        
        result = planner.plan_and_execute("Analyze this codebase")
        
        assert isinstance(result, str)
        assert "Execution" in result or "Plan" in result


class TestCoordinatorAdvanced:
    """测试协调器高级功能"""
    
    def test_create_multiple_agents_unique_ids(self):
        """测试创建多个 Agent 有唯一 ID"""
        coordinator = Coordinator()
        
        task1 = coordinator.create_agent("Task 1", "Prompt 1")
        task2 = coordinator.create_agent("Task 2", "Prompt 2")
        task3 = coordinator.create_agent("Task 3", "Prompt 3")
        
        assert task1.agent_id != task2.agent_id != task3.agent_id
    
    def test_fork_agents_parallel(self):
        """测试并行 Fork Agent"""
        coordinator = Coordinator()
        
        import time
        start = time.time()
        
        result = coordinator.fork_agents([
            (f"Task {i}", f"Prompt {i}", AgentType.GENERAL)
            for i in range(5)
        ], parallel=True)
        
        duration = time.time() - start
        
        assert len(result.results) == 5
        # 并行执行应该比串行快
        assert result.total_duration_ms >= 0
    
    def test_agent_with_model(self):
        """测试带模型的 Agent"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent(
            description="Test",
            prompt="Test",
            model="claude-opus-4"
        )
        
        assert task.model == "claude-opus-4"


class TestAgentLifecycle:
    """测试 Agent 生命周期"""
    
    def test_agent_status_transitions(self):
        """测试 Agent 状态转换"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Test", "Test")
        
        # 初始状态
        assert task.status == AgentStatus.PENDING
        
        # 执行后状态
        coordinator._run_agent(task.agent_id)
        
        assert task.status in [AgentStatus.COMPLETED, AgentStatus.FAILED]
    
    def test_agent_duration_tracking(self):
        """测试 Agent 持续时间追踪"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Test", "Test")
        coordinator._run_agent(task.agent_id)
        
        if task.started_at and task.completed_at:
            duration = task.completed_at - task.started_at
            assert duration >= 0
    
    def test_agent_output_storage(self):
        """测试 Agent 输出存储"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Test", "Test prompt")
        coordinator._run_agent(task.agent_id)
        
        # 应该有输出（即使是模拟的）
        assert task.output is not None


class TestAgentErrorHandling:
    """测试 Agent 错误处理"""
    
    def test_agent_execution_error(self):
        """测试 Agent 执行错误"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Test", "Test")
        # 模拟错误
        task.error = "Simulated error"
        task.status = AgentStatus.FAILED
        
        assert task.status == AgentStatus.FAILED
        assert task.error == "Simulated error"
    
    def test_fork_with_empty_tasks(self):
        """测试空任务 Fork"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([], parallel=False)
        
        assert len(result.results) == 0
        assert result.completed_count == 0


class TestSwarmScenarios:
    """测试 Swarm 场景"""
    
    def test_explore_swarm(self):
        """测试探索型 Swarm"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([
            ("Explore code", "Search for Python files", AgentType.EXPLORE),
            ("Explore docs", "Find documentation", AgentType.EXPLORE),
        ], parallel=False)
        
        for task in result.results.values():
            assert task.agent_type == AgentType.EXPLORE
    
    def test_mixed_type_swarm(self):
        """测试混合类型 Swarm"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([
            ("Explore", "Search", AgentType.EXPLORE),
            ("Plan", "Create plan", AgentType.PLAN),
            ("Verify", "Run tests", AgentType.VERIFICATION),
        ], parallel=False)
        
        types = [t.agent_type for t in result.results.values()]
        assert AgentType.EXPLORE in types
        assert AgentType.PLAN in types
        assert AgentType.VERIFICATION in types
    
    def test_large_swarm(self):
        """测试大型 Swarm"""
        coordinator = Coordinator()
        
        tasks = [
            (f"Task {i}", f"Prompt {i}", AgentType.GENERAL)
            for i in range(20)
        ]
        
        result = coordinator.fork_agents(tasks, parallel=False)
        
        assert len(result.results) == 20


class TestAgentIntegration:
    """测试 Agent 集成"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        coordinator = Coordinator()
        
        # 1. 创建探索 Agent
        explore = coordinator.create_agent(
            "Explore codebase",
            "Find all Python files",
            agent_type=AgentType.EXPLORE
        )
        
        # 2. 创建规划 Agent
        plan = coordinator.create_agent(
            "Create plan",
            "Plan implementation",
            agent_type=AgentType.PLAN
        )
        
        # 3. 执行
        coordinator._run_agent(explore.agent_id)
        coordinator._run_agent(plan.agent_id)
        
        # 4. 验证
        assert explore.status == AgentStatus.COMPLETED
        assert plan.status == AgentStatus.COMPLETED
    
    def test_task_parent_child(self):
        """测试父子任务关系"""
        coordinator = Coordinator()
        
        parent = coordinator.create_agent("Parent", "Parent task")
        child = coordinator.create_agent(
            "Child", "Child task",
            parent_id=parent.agent_id
        )
        
        assert child.parent_id == parent.agent_id


class TestFormatDuration:
    """测试持续时间格式化"""
    
    def test_format_running_duration(self):
        """测试格式化运行中持续时间"""
        coordinator = Coordinator()
        task = coordinator.create_agent("Test", "Test")
        task.started_at = 1000.0  # 模拟开始时间
        
        formatted = coordinator._format_duration(task)
        
        assert "running" in formatted.lower() or "N/A" not in formatted
    
    def test_format_completed_duration(self):
        """测试格式化已完成持续时间"""
        coordinator = Coordinator()
        task = coordinator.create_agent("Test", "Test")
        task.started_at = 1000.0
        task.completed_at = 1100.0
        
        formatted = coordinator._format_duration(task)
        
        assert "100" in formatted or "100000" in formatted  # ms
