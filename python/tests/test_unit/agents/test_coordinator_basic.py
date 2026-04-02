"""
Agent 系统测试 - Coordinator 基础
测试 Agent Swarm 协调器的基础功能
"""

import pytest
from shadowclaude.agents import (
    Coordinator, AgentTask, AgentType, AgentStatus,
    PermissionManager, SwarmResult
)


class TestCoordinatorInitialization:
    """测试协调器初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        coordinator = Coordinator()
        
        assert coordinator.max_workers == 5
        assert coordinator.permission_manager is not None
        assert len(coordinator._tasks) == 0
    
    def test_custom_max_workers(self):
        """测试自定义最大工作线程"""
        coordinator = Coordinator(max_workers=10)
        
        assert coordinator.max_workers == 10


class TestCreateAgent:
    """测试创建 Agent"""
    
    def test_create_basic_agent(self):
        """测试创建基础 Agent"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent(
            description="Test agent",
            prompt="Do something"
        )
        
        assert task is not None
        assert task.description == "Test agent"
        assert task.agent_type == AgentType.GENERAL
        assert task.status == AgentStatus.PENDING
    
    def test_create_typed_agent(self):
        """测试创建类型化 Agent"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent(
            description="Explore task",
            prompt="Search for files",
            agent_type=AgentType.EXPLORE
        )
        
        assert task.agent_type == AgentType.EXPLORE
    
    def test_create_named_agent(self):
        """测试创建命名 Agent"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent(
            description="Named task",
            prompt="Do something",
            name="MyAgent"
        )
        
        assert task.name == "MyAgent"
    
    def test_create_agent_generates_id(self):
        """测试创建 Agent 生成 ID"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent(
            description="Test",
            prompt="Test"
        )
        
        assert task.agent_id is not None
        assert task.agent_id.startswith("agent-")
    
    def test_create_agent_stores_in_tasks(self):
        """测试创建 Agent 存储在任务中"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent(
            description="Test",
            prompt="Test"
        )
        
        assert task.agent_id in coordinator._tasks


class TestPermissionManager:
    """测试权限管理器"""
    
    def test_get_allowed_tools_explore(self):
        """测试获取探索型 Agent 允许的工具"""
        pm = PermissionManager()
        
        tools = pm.get_allowed_tools(AgentType.EXPLORE)
        
        assert "read_file" in tools
        assert "glob_search" in tools
        assert "bash" not in tools
    
    def test_get_allowed_tools_plan(self):
        """测试获取规划型 Agent 允许的工具"""
        pm = PermissionManager()
        
        tools = pm.get_allowed_tools(AgentType.PLAN)
        
        assert "TodoWrite" in tools
        assert "bash" not in tools
    
    def test_get_allowed_tools_verification(self):
        """测试获取验证型 Agent 允许的工具"""
        pm = PermissionManager()
        
        tools = pm.get_allowed_tools(AgentType.VERIFICATION)
        
        assert "bash" in tools
        assert "read_file" in tools
    
    def test_get_allowed_tools_general(self):
        """测试获取通用型 Agent 允许的工具"""
        pm = PermissionManager()
        
        tools = pm.get_allowed_tools(AgentType.GENERAL)
        
        assert "bash" in tools
        assert "Agent" in tools
    
    def test_check_permission_allowed(self):
        """测试检查允许权限"""
        pm = PermissionManager()
        
        assert pm.check_permission(AgentType.EXPLORE, "read_file") is True
    
    def test_check_permission_denied(self):
        """测试检查拒绝权限"""
        pm = PermissionManager()
        
        assert pm.check_permission(AgentType.EXPLORE, "bash") is False


class TestAgentTask:
    """测试 Agent 任务"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = AgentTask(
            agent_id="agent-1",
            name="Test",
            description="Test task",
            prompt="Do this",
            agent_type=AgentType.GENERAL
        )
        
        assert task.agent_id == "agent-1"
        assert task.status == AgentStatus.PENDING
        assert task.output == ""
    
    def test_task_with_parent(self):
        """测试带子任务的父任务"""
        parent = AgentTask(
            agent_id="parent-1",
            name="Parent",
            description="Parent task",
            prompt="Parent",
            agent_type=AgentType.GENERAL
        )
        
        child = AgentTask(
            agent_id="child-1",
            name="Child",
            description="Child task",
            prompt="Child",
            agent_type=AgentType.GENERAL,
            parent_id=parent.agent_id
        )
        
        assert child.parent_id == parent.agent_id


class TestForkAgents:
    """测试 Fork 多个 Agent"""
    
    def test_fork_single_agent(self):
        """测试 Fork 单个 Agent"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([
            ("Task 1", "Do task 1", AgentType.GENERAL)
        ], parallel=False)
        
        assert isinstance(result, SwarmResult)
        assert len(result.results) == 1
    
    def test_fork_multiple_agents(self):
        """测试 Fork 多个 Agent"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([
            ("Task 1", "Do task 1", AgentType.GENERAL),
            ("Task 2", "Do task 2", AgentType.EXPLORE),
            ("Task 3", "Do task 3", AgentType.PLAN)
        ], parallel=False)
        
        assert len(result.results) == 3
    
    def test_fork_agents_serial(self):
        """测试串行 Fork Agent"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([
            ("Task 1", "Prompt 1", AgentType.GENERAL),
            ("Task 2", "Prompt 2", AgentType.GENERAL)
        ], parallel=False)
        
        assert result.completed_count >= 0
    
    def test_fork_sets_allowed_tools(self):
        """测试 Fork 设置允许的工具"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([
            ("Explore", "Search", AgentType.EXPLORE)
        ], parallel=False)
        
        task = list(result.results.values())[0]
        assert task.allowed_tools is not None
        assert "read_file" in task.allowed_tools


class TestSwarmResult:
    """测试 Swarm 结果"""
    
    def test_result_creation(self):
        """测试结果创建"""
        result = SwarmResult(
            results={},
            completed_count=0,
            failed_count=0,
            total_duration_ms=100
        )
        
        assert result.completed_count == 0
        assert result.total_duration_ms == 100


class TestAgentStatus:
    """测试 Agent 状态"""
    
    def test_status_values(self):
        """测试状态值"""
        assert AgentStatus.PENDING.value == "pending"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.CANCELLED.value == "cancelled"


class TestAgentType:
    """测试 Agent 类型"""
    
    def test_type_values(self):
        """测试类型值"""
        assert AgentType.EXPLORE.value == "Explore"
        assert AgentType.PLAN.value == "Plan"
        assert AgentType.VERIFICATION.value == "Verification"
        assert AgentType.GENERAL.value == "general-purpose"


class TestCoordinatorTaskSummary:
    """测试协调器任务摘要"""
    
    def test_get_task_summary(self):
        """测试获取任务摘要"""
        coordinator = Coordinator()
        task = coordinator.create_agent(
            description="Test task",
            prompt="Do something"
        )
        
        summary = coordinator.get_task_summary(task.agent_id)
        
        assert summary is not None
        assert task.agent_id in summary
        assert "Test task" in summary
    
    def test_get_nonexistent_task_summary(self):
        """测试获取不存在任务的摘要"""
        coordinator = Coordinator()
        
        summary = coordinator.get_task_summary("nonexistent")
        
        assert summary is None


class TestIntegrateResults:
    """测试整合结果"""
    
    def test_integrate_empty_results(self):
        """测试整合空结果"""
        coordinator = Coordinator()
        
        swarm_result = SwarmResult(
            results={},
            completed_count=0,
            failed_count=0,
            total_duration_ms=0
        )
        
        integrated = coordinator.integrate_results(swarm_result)
        
        assert isinstance(integrated, str)
        assert "Multi-Agent" in integrated
    
    def test_integrate_with_results(self):
        """测试整合有结果"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Test", "Test")
        task.status = AgentStatus.COMPLETED
        task.output = "Task output"
        
        swarm_result = SwarmResult(
            results={task.agent_id: task},
            completed_count=1,
            failed_count=0,
            total_duration_ms=100
        )
        
        integrated = coordinator.integrate_results(swarm_result)
        
        assert "Test" in integrated
        assert "completed" in integrated.lower()
