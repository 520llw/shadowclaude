"""
数据流测试
"""

import pytest
from shadowclaude.query_engine import QueryEngine


class TestDataFlow:
    """测试数据流"""
    
    def test_input_to_output_flow(self):
        """测试输入到输出流"""
        engine = QueryEngine()
        
        result = engine.submit_message("Input")
        
        # 输入应产生输出
        assert result.output is not None
        assert result.prompt == "Input"
    
    def test_tool_result_flow(self):
        """测试工具结果流"""
        engine = QueryEngine()
        
        result = engine.submit_message(
            "Use tool",
            tools_allowed=["read_file"]
        )
        
        assert isinstance(result.tool_calls, list)
        assert isinstance(result.matched_tools, tuple)
