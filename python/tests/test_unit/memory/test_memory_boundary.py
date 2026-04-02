"""
记忆系统边界测试
"""

import pytest
from shadowclaude.memory import SemanticMemory, EpisodicMemory, WorkingMemory


class TestMemoryBoundaries:
    """测试记忆边界"""
    
    def test_semantic_empty_content(self, tmp_path):
        """测试语义记忆空内容"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("", importance=0.8)
        assert len(memory.entries) == 1
    
    def test_semantic_very_long_content(self, tmp_path):
        """测试语义记忆超长内容"""
        memory = SemanticMemory(storage_path=tmp_path)
        long_content = "A" * 100000
        memory.add(long_content, importance=0.8)
        assert len(memory.entries) == 1
    
    def test_working_empty_message(self):
        """测试工作记忆空消息"""
        memory = WorkingMemory()
        memory.add_message("user", "")
        assert len(memory.messages) == 1


class TestMemoryUnicode:
    """测试记忆 Unicode"""
    
    def test_semantic_unicode_content(self, tmp_path):
        """测试语义记忆 Unicode 内容"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Unicode: 你好 🌍", importance=0.8)
        assert len(memory.entries) == 1
    
    def test_episodic_unicode_event(self):
        """测试情景记忆 Unicode 事件"""
        memory = EpisodicMemory()
        memory.start_episode({})
        memory.add_event("message", "Unicode: 你好 🌍")
        assert len(memory.current_episode) == 2
