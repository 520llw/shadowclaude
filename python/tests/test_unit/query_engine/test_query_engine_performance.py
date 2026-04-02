"""
QueryEngine 性能回归测试
"""

import pytest
import time
from shadowclaude.query_engine import QueryEngine


class TestPerformanceRegression:
    """测试性能回归"""
    
    def test_submit_message_under_100ms(self):
        """测试消息提交在 100ms 内"""
        engine = QueryEngine()
        
        start = time.time()
        engine.submit_message("Test")
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 100
    
    def test_prompt_build_under_1ms(self):
        """测试 Prompt 构建在 1ms 内"""
        engine = QueryEngine()
        
        start = time.time()
        engine.build_prompt_segments("Test")
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 1
