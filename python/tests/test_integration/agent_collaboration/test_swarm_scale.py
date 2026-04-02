"""
Agent Swarm 规模测试
"""

import pytest
from shadowclaude.agents import Coordinator, AgentType


class TestSwarmScalability:
    """测试 Swarm 可扩展性"""
    
    def test_swarm_10_agents(self):
        """测试 10 个 Agent Swarm"""
        coordinator = Coordinator()
        
        tasks = [
            (f"Task {i}", f"Prompt {i}", AgentType.GENERAL)
            for i in range(10)
        ]
        
        result = coordinator.fork_agents(tasks, parallel=False)
        assert len(result.results) == 10
    
    def test_swarm_50_agents(self):
        """测试 50 个 Agent Swarm"""
        coordinator = Coordinator()
        
        tasks = [
            (f"Task {i}", f"Prompt {i}", AgentType.GENERAL)
            for i in range(50)
        ]
        
        result = coordinator.fork_agents(tasks, parallel=False)
        assert len(result.results) == 50


class TestSwarmComposition:
    """测试 Swarm 组成"""
    
    def test_mixed_type_swarm(self):
        """测试混合类型 Swarm"""
        coordinator = Coordinator()
        
        tasks = [
            ("Explore 1", "Search", AgentType.EXPLORE),
            ("Plan 1", "Plan", AgentType.PLAN),
            ("Verify 1", "Verify", AgentType.VERIFICATION),
            ("General 1", "General", AgentType.GENERAL),
        ]
        
        result = coordinator.fork_agents(tasks, parallel=False)
        assert len(result.results) == 4
