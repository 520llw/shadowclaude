"""
Agent 故障恢复测试
"""

import pytest
from shadowclaude.agents import Coordinator, AgentStatus


class TestAgentFailure:
    """测试 Agent 故障"""
    
    def test_agent_failure_handling(self):
        """测试 Agent 故障处理"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Failing", "Will fail")
        task.status = AgentStatus.FAILED
        task.error = "Simulated failure"
        
        assert task.status == AgentStatus.FAILED
        assert task.error is not None
    
    def test_partial_swarm_failure(self):
        """测试部分 Swarm 故障"""
        coordinator = Coordinator()
        
        # 创建成功和失败的混合
        success = coordinator.create_agent("Success", "Success")
        success.status = AgentStatus.COMPLETED
        
        failed = coordinator.create_agent("Failed", "Failed")
        failed.status = AgentStatus.FAILED
        
        completed = sum(1 for t in [success, failed] 
                       if t.status == AgentStatus.COMPLETED)
        
        assert completed == 1


class TestAgentRecovery:
    """测试 Agent 恢复"""
    
    def test_retry_failed_agent(self):
        """测试重试失败 Agent"""
        coordinator = Coordinator()
        
        task = coordinator.create_agent("Retry", "Task")
        task.status = AgentStatus.FAILED
        
        # 模拟重试
        task.status = AgentStatus.PENDING
        coordinator._run_agent(task.agent_id)
        
        assert task.status == AgentStatus.COMPLETED
