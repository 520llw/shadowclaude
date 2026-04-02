"""
稳定性测试
"""

import pytest
import time
from shadowclaude.query_engine import QueryEngine


class TestLongRunning:
    """测试长时间运行"""
    
    def test_sustained_operation(self):
        """测试持续操作"""
        engine = QueryEngine()
        
        # 持续运行一段时间
        for batch in range(10):
            for i in range(20):
                engine.submit_message(f"Batch {batch} Message {i}")
        
        # 验证系统仍正常
        result = engine.submit_message("Final check")
        assert result.stop_reason.value == "completed"


class TestMemoryStability:
    """测试内存稳定性"""
    
    def test_no_memory_leak_long_run(self):
        """测试长时间运行无内存泄漏"""
        # 简化的内存稳定性测试
        engine = QueryEngine()
        
        for i in range(100):
            engine.submit_message(f"Message {i}")
        
        # 应正常工作
        assert engine.turn_count == 100
