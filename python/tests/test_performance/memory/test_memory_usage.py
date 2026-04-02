"""
内存使用测试
测试系统的内存使用情况
"""

import pytest
import sys
from shadowclaude.query_engine import QueryEngine
from shadowclaude.memory import SemanticMemory, MemorySystem
from shadowclaude.agents import Coordinator


class TestMemoryFootprint:
    """测试内存占用"""
    
    def test_query_engine_memory(self):
        """测试 QueryEngine 内存"""
        import tracemalloc
        
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        
        engine = QueryEngine()
        
        after = tracemalloc.take_snapshot()
        diff = after.compare_to(before, 'lineno')
        
        # 获取总增加
        total_increase = sum(stat.size_diff for stat in diff if stat.size_diff > 0)
        
        # 应该小于 10MB
        assert total_increase < 10 * 1024 * 1024
        
        tracemalloc.stop()
    
    def test_semantic_memory_growth(self, tmp_path):
        """测试语义记忆增长"""
        import tracemalloc
        
        memory = SemanticMemory(storage_path=tmp_path)
        
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        
        # 添加大量记忆
        for i in range(100):
            memory.add(f"Content item {i}", importance=0.8)
        
        after = tracemalloc.take_snapshot()
        diff = after.compare_to(before, 'lineno')
        
        total_increase = sum(stat.size_diff for stat in diff if stat.size_diff > 0)
        
        # 100 条记忆应小于 5MB
        assert total_increase < 5 * 1024 * 1024
        
        tracemalloc.stop()


class TestMemoryLeak:
    """测试内存泄漏"""
    
    def test_no_memory_leak_in_queries(self):
        """测试查询无内存泄漏"""
        import tracemalloc
        
        engine = QueryEngine()
        
        # 预热
        for _ in range(10):
            engine.submit_message("Test")
        
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        
        # 运行多次
        for _ in range(100):
            engine.submit_message("Test")
        
        after = tracemalloc.take_snapshot()
        diff = after.compare_to(before, 'lineno')
        
        # 内存增长应很小
        total_increase = sum(stat.size_diff for stat in diff if stat.size_diff > 0)
        assert total_increase < 10 * 1024 * 1024  # 10MB
        
        tracemalloc.stop()
    
    def test_no_memory_leak_in_agent_creation(self):
        """测试 Agent 创建无内存泄漏"""
        import tracemalloc
        
        coordinator = Coordinator()
        
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        
        # 创建和丢弃大量 Agent
        for i in range(200):
            task = coordinator.create_agent(f"Task {i}", "Prompt")
            # 引用应该能被垃圾回收
        
        after = tracemalloc.take_snapshot()
        diff = after.compare_to(before, 'lineno')
        
        total_increase = sum(stat.size_diff for stat in diff if stat.size_diff > 0)
        # 应该限制在合理范围内
        assert total_increase < 20 * 1024 * 1024
        
        tracemalloc.stop()


class TestMemoryEfficiency:
    """测试内存效率"""
    
    def test_large_object_handling(self):
        """测试大对象处理"""
        memory = MemorySystem()
        
        # 添加大对象
        large_content = "X" * 1000000  # 1MB
        memory.working.add_message("user", large_content)
        
        # 系统应仍能工作
        result = memory.retrieve_context("test")
        assert isinstance(result, str)
    
    def test_memory_cleanup_after_clear(self):
        """测试清理后内存释放"""
        from shadowclaude.memory import WorkingMemory
        
        memory = WorkingMemory()
        
        # 填充数据
        for i in range(100):
            memory.add_message("user", f"Message {i}")
            memory.set_variable(f"key{i}", f"value{i}")
        
        # 清理
        memory.clear()
        
        # 内存应该被释放
        assert len(memory.messages) == 0
        assert len(memory.variables) == 0
        assert len(memory.tool_outputs) == 0


class TestMemoryLimits:
    """测试内存限制"""
    
    def test_working_memory_size_limit(self):
        """测试工作记忆大小限制"""
        from shadowclaude.memory import WorkingMemory
        
        memory = WorkingMemory(max_tokens=1000)
        
        # 添加超出限制的内容
        for i in range(50):
            memory.add_message("user", f"Message {i} with content")
        
        # 应触发压缩
        estimated_tokens = sum(len(m["content"]) for m in memory.messages) // 4
        assert estimated_tokens <= memory.max_tokens * 1.5
    
    def test_episodic_memory_max_episodes(self):
        """测试情景记忆最大情景数"""
        from shadowclaude.memory import EpisodicMemory
        
        memory = EpisodicMemory(max_episodes=10)
        
        # 添加超出限制的情景
        for i in range(20):
            memory.start_episode({"task": i})
            memory.end_episode()
        
        # 应限制在 max_episodes
        assert len(memory.episodes) == 10
