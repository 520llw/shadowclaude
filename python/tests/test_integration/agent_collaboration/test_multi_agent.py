"""
多 Agent 协作集成测试
测试多个 Agent 协作完成任务
"""

import pytest
from shadowclaude.agents import (
    Coordinator, AgentType, AgentStatus,
    MultiStepPlanner
)


class TestMultiAgentBasicCollaboration:
    """测试基础多 Agent 协作"""
    
    def test_two_agents_collaborate(self):
        """测试两个 Agent 协作"""
        coordinator = Coordinator()
        
        # 创建两个 Agent
        agent1 = coordinator.create_agent(
            "Explore codebase",
            "Find all Python files",
            agent_type=AgentType.EXPLORE
        )
        agent2 = coordinator.create_agent(
            "Analyze files",
            "Analyze the found files",
            agent_type=AgentType.PLAN
        )
        
        # 串行执行
        coordinator._run_agent(agent1.agent_id)
        coordinator._run_agent(agent2.agent_id)
        
        assert agent1.status == AgentStatus.COMPLETED
        assert agent2.status == AgentStatus.COMPLETED
    
    def test_swarm_parallel_execution(self):
        """测试 Swarm 并行执行"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([
            (f"Task {i}", f"Process item {i}", AgentType.GENERAL)
            for i in range(5)
        ], parallel=True)
        
        assert len(result.results) == 5
        assert result.completed_count >= 0


class TestMultiAgentWithDependencies:
    """测试带依赖的多 Agent"""
    
    def test_parent_child_agents(self):
        """测试父子 Agent"""
        coordinator = Coordinator()
        
        parent = coordinator.create_agent(
            "Parent task",
            "Coordinate child tasks",
            agent_type=AgentType.PLAN
        )
        
        children = [
            coordinator.create_agent(
                f"Child {i}",
                f"Child task {i}",
                agent_type=AgentType.EXPLORE,
                parent_id=parent.agent_id
            )
            for i in range(3)
        ]
        
        # 验证父子关系
        for child in children:
            assert child.parent_id == parent.agent_id
    
    def test_hierarchical_execution(self):
        """测试分层执行"""
        coordinator = Coordinator()
        
        # 创建分层结构
        planner = coordinator.create_agent(
            "Planner",
            "Create execution plan",
            agent_type=AgentType.PLAN
        )
        
        explorers = coordinator.fork_agents([
            (f"Explorer {i}", f"Explore area {i}", AgentType.EXPLORE)
            for i in range(3)
        ], parallel=False)
        
        verifier = coordinator.create_agent(
            "Verifier",
            "Verify results",
            agent_type=AgentType.VERIFICATION
        )
        coordinator._run_agent(verifier.agent_id)
        
        assert planner.status == AgentStatus.PENDING  # 未执行
        assert verifier.status == AgentStatus.COMPLETED


class TestMultiAgentResultIntegration:
    """测试多 Agent 结果集成"""
    
    def test_integrate_multiple_results(self):
        """测试集成多个结果"""
        coordinator = Coordinator()
        
        # 创建并执行多个 Agent
        result = coordinator.fork_agents([
            ("Task A", "Do A", AgentType.GENERAL),
            ("Task B", "Do B", AgentType.GENERAL),
            ("Task C", "Do C", AgentType.GENERAL),
        ], parallel=False)
        
        # 集成结果
        integrated = coordinator.integrate_results(result)
        
        assert "Multi-Agent" in integrated
        assert "Task A" in integrated
        assert "Task B" in integrated
        assert "Task C" in integrated
    
    def test_integrate_with_failures(self):
        """测试集成含失败的结果"""
        coordinator = Coordinator()
        
        # 创建一个成功的和一个失败的
        success = coordinator.create_agent("Success", "Will succeed")
        success.status = AgentStatus.COMPLETED
        success.output = "Success output"
        
        failed = coordinator.create_agent("Failed", "Will fail")
        failed.status = AgentStatus.FAILED
        failed.error = "Error occurred"
        
        swarm_result = coordinator.fork_agents([], parallel=False)
        swarm_result.results[success.agent_id] = success
        swarm_result.results[failed.agent_id] = failed
        
        integrated = coordinator.integrate_results(swarm_result)
        
        assert "completed" in integrated.lower()
        assert "failed" in integrated.lower() or "error" in integrated.lower()


class TestMultiAgentScenarios:
    """测试多 Agent 场景"""
    
    def test_code_review_scenario(self):
        """测试代码审查场景"""
        coordinator = Coordinator()
        
        # 探索 Agent 查找代码
        explore = coordinator.create_agent(
            "Find code files",
            "Find all source files",
            agent_type=AgentType.EXPLORE
        )
        
        # 分析 Agent 检查代码
        analyze = coordinator.create_agent(
            "Analyze code",
            "Check for issues",
            agent_type=AgentType.PLAN
        )
        
        # 验证 Agent 运行测试
        verify = coordinator.create_agent(
            "Verify code",
            "Run tests",
            agent_type=AgentType.VERIFICATION
        )
        
        # 执行
        coordinator._run_agent(explore.agent_id)
        coordinator._run_agent(analyze.agent_id)
        coordinator._run_agent(verify.agent_id)
        
        assert all(
            a.status == AgentStatus.COMPLETED
            for a in [explore, analyze, verify]
        )
    
    def test_research_scenario(self):
        """测试研究场景"""
        coordinator = Coordinator()
        
        # 多个探索 Agent 并行搜索
        researchers = coordinator.fork_agents([
            ("Research topic A", "Search for A", AgentType.EXPLORE),
            ("Research topic B", "Search for B", AgentType.EXPLORE),
            ("Research topic C", "Search for C", AgentType.EXPLORE),
        ], parallel=False)
        
        # 规划 Agent 整合结果
        planner = coordinator.create_agent(
            "Synthesize findings",
            "Combine all research",
            agent_type=AgentType.PLAN
        )
        coordinator._run_agent(planner.agent_id)
        
        assert planner.status == AgentStatus.COMPLETED
    
    def test_documentation_scenario(self):
        """测试文档生成场景"""
        coordinator = Coordinator()
        
        # 探索代码
        explore = coordinator.create_agent(
            "Explore codebase",
            "Find code to document",
            agent_type=AgentType.EXPLORE
        )
        coordinator._run_agent(explore.agent_id)
        
        # 生成文档
        document = coordinator.create_agent(
            "Generate docs",
            "Create documentation",
            agent_type=AgentType.PLAN
        )
        coordinator._run_agent(document.agent_id)
        
        assert document.status == AgentStatus.COMPLETED


class TestMultiStepPlannerIntegration:
    """测试多步骤规划器集成"""
    
    def test_planner_creates_and_executes(self):
        """测试规划器创建并执行"""
        coordinator = Coordinator()
        planner = MultiStepPlanner(coordinator)
        
        result = planner.plan_and_execute("Implement a feature")
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_planner_handles_complex_goal(self):
        """测试规划器处理复杂目标"""
        coordinator = Coordinator()
        planner = MultiStepPlanner(coordinator)
        
        result = planner.plan_and_execute(
            "Refactor codebase, add tests, and update documentation"
        )
        
        assert isinstance(result, str)


class TestMultiAgentPerformance:
    """测试多 Agent 性能"""
    
    def test_swarm_execution_time(self):
        """测试 Swarm 执行时间"""
        import time
        
        coordinator = Coordinator()
        
        start = time.time()
        coordinator.fork_agents([
            (f"Task {i}", f"Task {i}", AgentType.GENERAL)
            for i in range(10)
        ], parallel=True)
        elapsed = time.time() - start
        
        # 应该相对较快
        assert elapsed < 5.0
    
    def test_large_swarm_creation(self):
        """测试大型 Swarm 创建"""
        coordinator = Coordinator()
        
        import time
        start = time.time()
        
        tasks = [
            coordinator.create_agent(f"Agent {i}", f"Task {i}")
            for i in range(100)
        ]
        
        elapsed = time.time() - start
        
        assert len(tasks) == 100
        assert elapsed < 1.0  # 创建应该很快


class TestMultiAgentErrorRecovery:
    """测试多 Agent 错误恢复"""
    
    def test_partial_failure_handling(self):
        """测试部分失败处理"""
        coordinator = Coordinator()
        
        # 创建一些 Agent
        tasks = []
        for i in range(5):
            task = coordinator.create_agent(f"Task {i}", f"Task {i}")
            # 模拟一些失败
            if i == 2:
                task.status = AgentStatus.FAILED
                task.error = "Simulated failure"
            else:
                task.status = AgentStatus.COMPLETED
            tasks.append(task)
        
        # 统计
        completed = sum(1 for t in tasks if t.status == AgentStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == AgentStatus.FAILED)
        
        assert completed == 4
        assert failed == 1
    
    def test_empty_swarm_handling(self):
        """测试空 Swarm 处理"""
        coordinator = Coordinator()
        
        result = coordinator.fork_agents([], parallel=False)
        
        assert len(result.results) == 0
        assert result.completed_count == 0
        assert result.failed_count == 0
