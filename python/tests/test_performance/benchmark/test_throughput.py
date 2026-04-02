"""
吞吐量测试
"""

import pytest
import time
from shadowclaude.query_engine import QueryEngine


class TestThroughput:
    """测试吞吐量"""
    
    def test_queries_per_second(self):
        """测试每秒查询数"""
        engine = QueryEngine()
        
        count = 20
        start = time.time()
        
        for i in range(count):
            engine.submit_message(f"Query {i}")
        
        elapsed = time.time() - start
        qps = count / elapsed
        
        print(f"QPS: {qps:.2f}")
        assert qps > 5  # 至少 5 QPS
    
    def test_sustained_throughput(self):
        """测试持续吞吐量"""
        engine = QueryEngine()
        
        start = time.time()
        for i in range(50):
            engine.submit_message(f"Query {i}")
        elapsed = time.time() - start
        
        assert elapsed < 10  # 50 次查询在 10 秒内
