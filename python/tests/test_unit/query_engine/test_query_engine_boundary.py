"""
QueryEngine 边界测试
"""

import pytest
from shadowclaude.query_engine import QueryEngine


class TestBoundaryConditions:
    """测试边界条件"""
    
    def test_empty_string_input(self):
        """测试空字符串输入"""
        engine = QueryEngine()
        result = engine.submit_message("")
        assert result.stop_reason.value == "completed"
    
    def test_single_character_input(self):
        """测试单字符输入"""
        engine = QueryEngine()
        result = engine.submit_message("a")
        assert result.stop_reason.value == "completed"
    
    def test_max_length_input(self):
        """测试最大长度输入"""
        engine = QueryEngine()
        long_input = "A" * 10000
        result = engine.submit_message(long_input)
        assert result.stop_reason.value == "completed"


class TestUnicodeHandling:
    """测试 Unicode 处理"""
    
    def test_emoji_input(self):
        """测试 Emoji 输入"""
        engine = QueryEngine()
        result = engine.submit_message("Hello 🌍🎉")
        assert result.stop_reason.value == "completed"
    
    def test_chinese_input(self):
        """测试中文输入"""
        engine = QueryEngine()
        result = engine.submit_message("你好世界")
        assert result.stop_reason.value == "completed"
    
    def test_arabic_input(self):
        """测试阿拉伯语输入"""
        engine = QueryEngine()
        result = engine.submit_message("مرحبا")
        assert result.stop_reason.value == "completed"
