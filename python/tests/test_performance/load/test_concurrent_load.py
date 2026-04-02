"""
并发性能测试
"""

import pytest
import concurrent.futures
import time
from shadowclaude.query_engine import QueryEngine
from shadowclaude.agents import Coordinator


class TestConcurrentQueries:
    """测试并发查询"""
    
    def test_10_concurrent_queries(self):
        """测试 10 个并发查询"""
        engines = [QueryEngine() for _ in range(10)]
        
        def query(engine):
            return engine.submit_message("Test")
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(query, engines))
        elapsed = time.time() - start
        
        assert len(results) == 10
        assert elapsed < 5.0
    
    def test_50_concurrent_queries(self):
        """测试 50 个并发查询"""
        engines = [QueryEngine() for _ in range(50)]
        
        def query(engine):
            return engine.submit_message("Test")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(query, engines))
        
        assert len(results) == 50


class TestConcurrentAgents:
    """测试并发 Agent"""
    
    def test_concurrent_agent_creation(self):
        """测试并发 Agent 创建"""
        coordinator = Coordinator()
        
        def create(i):
            return coordinator.create_agent(f"Agent {i}", "Task")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            tasks = list(executor.map(create, range(50)))
        
        assert len(tasks) == 50
