"""
响应时间测试
"""

import pytest
import time
from shadowclaude.query_engine import QueryEngine


class TestResponseTime:
    """测试响应时间"""
    
    def test_single_query_response_time(self):
        """测试单查询响应时间"""
        engine = QueryEngine()
        
        start = time.time()
        engine.submit_message("Test")
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 200  # 200ms
    
    def test_streaming_response_time(self):
        """测试流式响应时间"""
        engine = QueryEngine()
        
        start = time.time()
        list(engine.stream_submit_message("Test"))
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 200
    
    def test_tool_execution_response_time(self):
        """测试工具执行响应时间"""
        engine = QueryEngine()
        
        start = time.time()
        engine.submit_message("Test", tools_allowed=["read_file"])
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 300
