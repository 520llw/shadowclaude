"""
负载测试
测试系统在高负载下的表现
"""

import pytest
import time
import concurrent.futures
from shadowclaude.query_engine import QueryEngine
from shadowclaude.memory import SemanticMemory, MemorySystem
from shadowclaude.agents import Coordinator


class TestQueryEngineLoad:
    """测试 QueryEngine 负载"""
    
    def test_concurrent_queries(self):
        """测试并发查询"""
        engines = [QueryEngine() for _ in range(10)]
        
        def query(engine, msg):
            return engine.submit_message(msg)
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(query, engines[i], f"Message {i}")
                for i in range(10)
            ]
            results = [f.result() for f in futures]
        elapsed = time.time() - start
        
        assert len(results) == 10
        assert elapsed < 5.0
    
    def test_rapid_fire_queries(self):
        """测试快速连续查询"""
        engine = QueryEngine()
        
        start = time.time()
        for i in range(50):
            engine.submit_message(f"Quick query {i}")
        elapsed = time.time() - start
        
        assert elapsed < 3.0
        assert engine.turn_count == 50


class TestMemoryLoad:
    """测试记忆系统负载"""
    
    def test_massive_semantic_additions(self, tmp_path):
        """测试大量语义记忆添加"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        start = time.time()
        for i in range(1000):
            memory.add(f"Knowledge item {i}", importance=0.8)
        elapsed = time.time() - start
        
        assert len(memory.entries) == 1000
        assert elapsed < 5.0
    
    def test_concurrent_memory_access(self, tmp_path):
        """测试并发记忆访问"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        # 预填充
        for i in range(100):
            memory.add(f"Item {i}", importance=0.8)
        
        def read_memory(query):
            return memory.retrieve(query, top_k=5)
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(read_memory, f"item {i}")
                for i in range(100)
            ]
            results = [f.result() for f in futures]
        elapsed = time.time() - start
        
        assert len(results) == 100
        assert elapsed < 2.0


class TestAgentLoad:
    """测试 Agent 负载"""
    
    def test_massive_agent_creation(self):
        """测试大量 Agent 创建"""
        coordinator = Coordinator()
        
        start = time.time()
        for i in range(500):
            coordinator.create_agent(f"Agent {i}", f"Task {i}")
        elapsed = time.time() - start
        
        assert len(coordinator._tasks) == 500
        assert elapsed < 2.0
    
    def test_large_swarm_execution(self):
        """测试大型 Swarm 执行"""
        coordinator = Coordinator()
        
        tasks = [
            (f"Task {i}", f"Process {i}", "general-purpose")
            for i in range(50)
        ]
        
        start = time.time()
        result = coordinator.fork_agents(tasks, parallel=True)
        elapsed = time.time() - start
        
        assert len(result.results) == 50
        assert elapsed < 5.0


class TestSystemStress:
    """测试系统压力"""
    
    def test_memory_pressure(self, tmp_path):
        """测试内存压力"""
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        # 添加大量大记忆
        large_content = "X" * 10000
        
        for i in range(100):
            system.add_to_semantic(f"Large item {i}: {large_content}", importance=0.8)
        
        # 系统仍应响应
        context = system.retrieve_context("test")
        assert isinstance(context, str)
    
    def test_combined_load(self, tmp_path):
        """测试组合负载"""
        from shadowclaude.memory import MemorySystem
        
        memory = MemorySystem()
        memory.semantic.storage_path = tmp_path
        engine = QueryEngine()
        coordinator = Coordinator()
        
        start = time.time()
        
        # 同时进行多种操作
        for i in range(20):
            memory.add_to_semantic(f"Item {i}", importance=0.8)
            engine.submit_message(f"Query {i}")
            coordinator.create_agent(f"Agent {i}", f"Task {i}")
        
        elapsed = time.time() - start
        
        assert elapsed < 5.0


class TestEndurance:
    """测试耐久性"""
    
    def test_sustained_operations(self, tmp_path):
        """测试持续操作"""
        engine = QueryEngine()
        engine.memory_system.semantic.storage_path = tmp_path
        
        # 持续运行多次操作
        for batch in range(5):
            for i in range(20):
                engine.submit_message(f"Batch {batch} Query {i}")
                engine.memory_system.add_to_semantic(
                    f"Knowledge {batch}-{i}",
                    importance=0.8
                )
        
        # 系统应仍正常工作
        result = engine.submit_message("Final query")
        assert result.stop_reason.value == "completed"
