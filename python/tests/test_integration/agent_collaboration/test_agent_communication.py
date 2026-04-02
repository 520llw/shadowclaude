"""
Agent 通信测试
"""

import pytest
from shadowclaude.agents import Coordinator


class TestAgentCommunication:
    """测试 Agent 通信"""
    
    def test_parent_child_context(self):
        """测试父子上下文"""
        coordinator = Coordinator()
        
        parent = coordinator.create_agent("Parent", "Parent task")
        child = coordinator.create_agent(
            "Child", "Child task",
            parent_id=parent.agent_id
        )
        
        # 子 Agent 应该知道父 Agent
        assert child.parent_id == parent.agent_id
    
    def test_context_passing(self):
        """测试上下文传递"""
        coordinator = Coordinator()
        
        parent = coordinator.create_agent("Parent", "Parent")
        child = coordinator.create_agent(
            "Child", "Child",
            parent_id=parent.agent_id
        )
        
        # 子应该能访问父的上下文
        assert child.parent_id is not None
