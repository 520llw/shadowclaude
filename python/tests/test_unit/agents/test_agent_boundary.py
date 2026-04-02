"""
Agent 系统边界测试
"""

import pytest
from shadowclaude.agents import Coordinator, AgentType


class TestAgentBoundaries:
    """测试 Agent 边界"""
    
    def test_create_agent_empty_description(self):
        """测试创建空描述 Agent"""
        coordinator = Coordinator()
        task = coordinator.create_agent("", "Prompt")
        assert task.description == ""
    
    def test_create_agent_empty_prompt(self):
        """测试创建空提示 Agent"""
        coordinator = Coordinator()
        task = coordinator.create_agent("Task", "")
        assert task.prompt == ""
    
    def test_create_agent_unicode_name(self):
        """测试创建 Unicode 名称 Agent"""
        coordinator = Coordinator()
        task = coordinator.create_agent("任务 🌍", "Prompt")
        assert task.name == "任务 🌍"


class TestAgentLimits:
    """测试 Agent 限制"""
    
    def test_max_agents_creation(self):
        """测试最大 Agent 创建"""
        coordinator = Coordinator()
        
        # 创建大量 Agent
        for i in range(100):
            coordinator.create_agent(f"Agent {i}", "Task")
        
        assert len(coordinator._tasks) == 100
