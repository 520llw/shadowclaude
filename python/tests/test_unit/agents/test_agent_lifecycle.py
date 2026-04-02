"""
Agent 生命周期测试
"""

import pytest
from shadowclaude.agents import Coordinator, AgentStatus, AgentType


class TestAgentCreation:
    """测试 Agent 创建"""
    
    def test_unique_ids_generated(self):
        """测试生成唯一 ID"""
        coordinator = Coordinator()
        
        ids = set()
        for i in range(100):
            task = coordinator.create_agent(f"Task {i}", "Prompt")
            ids.add(task.agent_id)
        
        assert len(ids) == 100
    
    def test_default_type_is_general(self):
        """测试默认类型为通用"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Test", "Test")
        
        assert task.agent_type == AgentType.GENERAL
    
    def test_allowed_tools_set_by_type(self):
        """测试按类型设置允许的工具"""
        coordinator = Coordinator()
        
        explore = coordinator.create_agent("Explore", "Test", agent_type=AgentType.EXPLORE)
        general = coordinator.create_agent("General", "Test", agent_type=AgentType.GENERAL)
        
        assert "bash" not in explore.allowed_tools
        assert "bash" in general.allowed_tools


class TestAgentExecution:
    """测试 Agent 执行"""
    
    def test_execution_updates_status(self):
        """测试执行更新状态"""
        coordinator = Coordinator()
        task = coordinator.create_agent("Test", "Test")
        
        assert task.status == AgentStatus.PENDING
        
        coordinator._run_agent(task.agent_id)
        
        assert task.status in [AgentStatus.COMPLETED, AgentStatus.FAILED]
    
    def test_execution_sets_timestamps(self):
        """测试执行设置时间戳"""
        coordinator = Coordinator()
        task = coordinator.create_agent("Test", "Test")
        
        coordinator._run_agent(task.agent_id)
        
        assert task.started_at is not None
        assert task.completed_at is not None
        assert task.completed_at >= task.started_at


class TestAgentCleanup:
    """测试 Agent 清理"""
    
    def test_tasks_stored_in_registry(self):
        """测试任务存储在注册表"""
        coordinator = Coordinator()
        task = coordinator.create_agent("Test", "Test")
        
        assert task.agent_id in coordinator._tasks
    
    def test_task_retrievable(self):
        """测试任务可检索"""
        coordinator = Coordinator()
        task = coordinator.create_agent("Test", "Test")
        
        summary = coordinator.get_task_summary(task.agent_id)
        
        assert summary is not None
        assert task.agent_id in summary
