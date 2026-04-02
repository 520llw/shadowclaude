"""
资源竞争测试
"""

import pytest
import threading
import time
from shadowclaude.query_engine import QueryEngine


class TestResourceContention:
    """测试资源竞争"""
    
    def test_concurrent_memory_access(self, tmp_path):
        """测试并发内存访问"""
        from shadowclaude.memory import MemorySystem
        
        memory = MemorySystem()
        memory.semantic.storage_path = tmp_path
        
        errors = []
        
        def writer(i):
            try:
                memory.add_to_semantic(f"Item {i}", importance=0.8)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


class TestLockContention:
    """测试锁竞争"""
    
    def test_coordinator_thread_safety(self):
        """测试协调器线程安全"""
        from shadowclaude.agents import Coordinator
        
        coordinator = Coordinator()
        
        def create_agents():
            for i in range(10):
                coordinator.create_agent(f"Agent {i}", "Task")
        
        threads = [threading.Thread(target=create_agents) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(coordinator._tasks) == 50
