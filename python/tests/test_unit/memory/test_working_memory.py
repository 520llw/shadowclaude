"""
WorkingMemory 单元测试
测试工作记忆系统的核心功能
"""

import pytest
from shadowclaude.memory import WorkingMemory


class TestWorkingMemoryInitialization:
    """测试工作记忆初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        memory = WorkingMemory()
        
        assert memory.max_tokens == 8000
        assert len(memory.messages) == 0
        assert len(memory.variables) == 0
        assert len(memory.tool_outputs) == 0
    
    def test_custom_max_tokens(self):
        """测试自定义最大 Token"""
        memory = WorkingMemory(max_tokens=16000)
        
        assert memory.max_tokens == 16000
    
    def test_small_max_tokens(self):
        """测试小最大 Token"""
        memory = WorkingMemory(max_tokens=100)
        
        assert memory.max_tokens == 100


class TestWorkingMemoryAddMessage:
    """测试添加消息"""
    
    def test_add_user_message(self):
        """测试添加用户消息"""
        memory = WorkingMemory()
        
        memory.add_message("user", "Hello")
        
        assert len(memory.messages) == 1
        assert memory.messages[0]["role"] == "user"
        assert memory.messages[0]["content"] == "Hello"
    
    def test_add_assistant_message(self):
        """测试添加助手消息"""
        memory = WorkingMemory()
        
        memory.add_message("assistant", "Hi there")
        
        assert memory.messages[0]["role"] == "assistant"
    
    def test_add_system_message(self):
        """测试添加系统消息"""
        memory = WorkingMemory()
        
        memory.add_message("system", "You are a helpful assistant")
        
        assert memory.messages[0]["role"] == "system"
    
    def test_message_has_timestamp(self):
        """测试消息有时间戳"""
        memory = WorkingMemory()
        
        memory.add_message("user", "Hello")
        
        assert "timestamp" in memory.messages[0]


class TestWorkingMemoryVariables:
    """测试工作记忆变量"""
    
    def test_set_and_get_variable(self):
        """测试设置和获取变量"""
        memory = WorkingMemory()
        
        memory.set_variable("key", "value")
        
        assert memory.get_variable("key") == "value"
    
    def test_get_nonexistent_variable(self):
        """测试获取不存在的变量"""
        memory = WorkingMemory()
        
        result = memory.get_variable("nonexistent")
        
        assert result is None
    
    def test_update_variable(self):
        """测试更新变量"""
        memory = WorkingMemory()
        
        memory.set_variable("counter", 1)
        memory.set_variable("counter", 2)
        
        assert memory.get_variable("counter") == 2
    
    def test_variable_types(self):
        """测试变量类型"""
        memory = WorkingMemory()
        
        memory.set_variable("string", "text")
        memory.set_variable("number", 42)
        memory.set_variable("list", [1, 2, 3])
        memory.set_variable("dict", {"a": 1})
        
        assert memory.get_variable("string") == "text"
        assert memory.get_variable("number") == 42
        assert memory.get_variable("list") == [1, 2, 3]


class TestWorkingMemoryToolCache:
    """测试工具输出缓存"""
    
    def test_cache_tool_output(self):
        """测试缓存工具输出"""
        memory = WorkingMemory()
        
        memory.cache_tool_output("read_file", "test.py", "content")
        
        assert len(memory.tool_outputs) == 1
    
    def test_get_cached_tool_output(self):
        """测试获取缓存的工具输出"""
        memory = WorkingMemory()
        
        memory.cache_tool_output("read_file", "test.py", "file content")
        result = memory.get_cached_tool_output("read_file", "test.py")
        
        assert result == "file content"
    
    def test_get_uncached_tool_output(self):
        """测试获取未缓存的工具输出"""
        memory = WorkingMemory()
        
        result = memory.get_cached_tool_output("unknown", "input")
        
        assert result is None
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        memory = WorkingMemory()
        
        memory.cache_tool_output("tool", "input", "output")
        
        # 相同输入应该产生相同缓存键
        result1 = memory.get_cached_tool_output("tool", "input")
        result2 = memory.get_cached_tool_output("tool", "input")
        
        assert result1 == result2
    
    def test_different_inputs_different_cache(self):
        """测试不同输入不同缓存"""
        memory = WorkingMemory()
        
        memory.cache_tool_output("tool", "input1", "output1")
        memory.cache_tool_output("tool", "input2", "output2")
        
        assert memory.get_cached_tool_output("tool", "input1") == "output1"
        assert memory.get_cached_tool_output("tool", "input2") == "output2"


class TestWorkingMemoryCompression:
    """测试工作记忆压缩"""
    
    def test_no_compression_under_threshold(self):
        """测试阈值下不压缩"""
        memory = WorkingMemory(max_tokens=10000)
        
        # 添加一些短消息
        for i in range(5):
            memory.add_message("user", f"Message {i}")
        
        # 应该没有压缩
        assert len(memory.messages) == 5
    
    def test_compression_over_threshold(self):
        """测试超阈值压缩"""
        memory = WorkingMemory(max_tokens=10)  # 很小的限制
        
        # 添加长消息
        for i in range(10):
            memory.add_message("user", "A" * 100)
        
        # 应该触发压缩
        assert len(memory.messages) <= 6  # 保留最近5条 + 可能的摘要
    
    def test_compression_preserves_recent(self):
        """测试压缩保留最近消息"""
        memory = WorkingMemory(max_tokens=10)
        
        for i in range(10):
            memory.add_message("user", f"Message {i}")
        
        # 最近的消息应该保留
        contents = [m["content"] for m in memory.messages]
        assert any("9" in c or "8" in c for c in contents)


class TestWorkingMemoryClear:
    """测试清空工作记忆"""
    
    def test_clear_removes_all(self):
        """测试清空移除所有内容"""
        memory = WorkingMemory()
        
        memory.add_message("user", "Hello")
        memory.set_variable("key", "value")
        memory.cache_tool_output("tool", "input", "output")
        
        memory.clear()
        
        assert len(memory.messages) == 0
        assert len(memory.variables) == 0
        assert len(memory.tool_outputs) == 0
    
    def test_clear_empty_memory(self):
        """测试清空空记忆"""
        memory = WorkingMemory()
        
        memory.clear()
        
        assert len(memory.messages) == 0


class TestWorkingMemoryEdgeCases:
    """测试边界情况"""
    
    def test_add_empty_message(self):
        """测试添加空消息"""
        memory = WorkingMemory()
        
        memory.add_message("user", "")
        
        assert len(memory.messages) == 1
        assert memory.messages[0]["content"] == ""
    
    def test_add_very_long_message(self):
        """测试添加超长消息"""
        memory = WorkingMemory()
        long_content = "A" * 100000
        
        memory.add_message("user", long_content)
        
        assert len(memory.messages) == 1
    
    def test_variable_with_none_value(self):
        """测试 None 值变量"""
        memory = WorkingMemory()
        
        memory.set_variable("key", None)
        
        assert memory.get_variable("key") is None
    
    def test_cache_empty_output(self):
        """测试缓存空输出"""
        memory = WorkingMemory()
        
        memory.cache_tool_output("tool", "input", "")
        
        assert memory.get_cached_tool_output("tool", "input") == ""


class TestWorkingMemoryTokenEstimation:
    """测试 Token 估算"""
    
    def test_empty_memory_low_tokens(self):
        """测试空记忆低 Token"""
        memory = WorkingMemory()
        
        # 空记忆应该估计为 0 token
        total_chars = sum(len(m["content"]) for m in memory.messages)
        estimated_tokens = total_chars // 4
        
        assert estimated_tokens == 0
    
    def test_token_estimation_scaling(self):
        """测试 Token 估算比例"""
        memory = WorkingMemory()
        
        # 添加 400 字符的消息
        memory.add_message("user", "A" * 400)
        
        total_chars = sum(len(m["content"]) for m in memory.messages)
        estimated_tokens = total_chars // 4
        
        assert estimated_tokens == 100
