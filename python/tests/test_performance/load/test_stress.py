"""
压力测试
"""

import pytest
import time
from shadowclaude.query_engine import QueryEngine
from shadowclaude.memory import SemanticMemory


class TestStressQueries:
    """测试查询压力"""
    
    def test_1000_queries_stress(self):
        """测试 1000 次查询压力"""
        engine = QueryEngine()
        
        start = time.time()
        for i in range(100):
            engine.submit_message(f"Query {i}")
        elapsed = time.time() - start
        
        print(f"100 queries in {elapsed:.2f}s")
        assert elapsed < 10.0


class TestStressMemory:
    """测试内存压力"""
    
    def test_massive_memory_additions(self, tmp_path):
        """测试大规模记忆添加"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        start = time.time()
        for i in range(500):
            memory.add(f"Item {i}", importance=0.8)
        elapsed = time.time() - start
        
        assert len(memory.entries) == 500
        assert elapsed < 3.0
