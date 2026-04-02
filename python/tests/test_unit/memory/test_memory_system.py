"""
MemorySystem 集成测试
测试三层记忆系统的集成
"""

import pytest
from shadowclaude.memory import MemorySystem, SemanticMemory, EpisodicMemory, WorkingMemory


class TestMemorySystemInitialization:
    """测试记忆系统初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        system = MemorySystem()
        
        assert system.semantic is not None
        assert system.episodic is not None
        assert system.working is not None
    
    def test_disable_semantic(self):
        """测试禁用语义记忆"""
        system = MemorySystem(enable_semantic=False)
        
        assert system.semantic is None
        assert system.episodic is not None
    
    def test_disable_episodic(self):
        """测试禁用情景记忆"""
        system = MemorySystem(enable_episodic=False)
        
        assert system.semantic is not None
        assert system.episodic is None
    
    def test_disable_both(self):
        """测试禁用两种记忆"""
        system = MemorySystem(
            enable_semantic=False,
            enable_episodic=False
        )
        
        assert system.semantic is None
        assert system.episodic is None
        assert system.working is not None
    
    def test_custom_working_memory_size(self):
        """测试自定义工作记忆大小"""
        system = MemorySystem(working_memory_size=4000)
        
        assert system.working.max_tokens == 4000


class TestAddToSemantic:
    """测试添加到语义记忆"""
    
    def test_add_when_enabled(self, tmp_path):
        """测试启用时添加"""
        system = MemorySystem(enable_semantic=True)
        system.semantic.storage_path = tmp_path
        
        system.add_to_semantic("Important fact", importance=0.8)
        
        assert len(system.semantic.entries) == 1
    
    def test_add_when_disabled(self):
        """测试禁用时添加"""
        system = MemorySystem(enable_semantic=False)
        
        # 不应抛出异常
        system.add_to_semantic("Fact", importance=0.8)


class TestRetrieveContext:
    """测试检索上下文"""
    
    def test_retrieve_from_all_layers(self, tmp_path):
        """测试从所有层检索"""
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        # 添加语义记忆
        system.semantic.add("Python is great", importance=0.8)
        
        # 添加工作记忆消息
        system.working.add_message("user", "Tell me about Python")
        
        # 检索
        context = system.retrieve_context("Python")
        
        assert "Python" in context or "Relevant" in context or "Recent" in context
    
    def test_retrieve_with_disabled_layers(self):
        """测试禁用层时检索"""
        system = MemorySystem(
            enable_semantic=False,
            enable_episodic=False
        )
        
        system.working.add_message("user", "Hello")
        
        context = system.retrieve_context("Hello")
        
        assert isinstance(context, str)
    
    def test_retrieve_empty_result(self):
        """测试空结果检索"""
        system = MemorySystem()
        
        context = system.retrieve_context("nonexistent query xyz")
        
        # 应该有默认消息或空结果
        assert isinstance(context, str)
    
    def test_retrieve_includes_semantic(self, tmp_path):
        """测试检索包含语义记忆"""
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        system.semantic.add("Specific fact about coding", importance=0.9)
        
        context = system.retrieve_context("coding")
        
        assert "coding" in context.lower() or "fact" in context.lower()
    
    def test_retrieve_includes_working(self):
        """测试检索包含工作记忆"""
        system = MemorySystem()
        
        system.working.add_message("user", "Recent question about Python")
        
        context = system.retrieve_context("Python")
        
        assert "recent" in context.lower() or "python" in context.lower()


class TestConsolidate:
    """测试整合"""
    
    def test_consolidate_calls_semantic(self, tmp_path):
        """测试整合调用语义记忆"""
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        # 添加旧低重要性记忆
        from datetime import datetime, timedelta
        from shadowclaude.memory import MemoryEntry
        
        old_entry = MemoryEntry(
            content="Old memory",
            timestamp=datetime.now() - timedelta(days=100),
            source="test",
            importance=0.4
        )
        content_hash = system.semantic._hash_content(old_entry.content)
        system.semantic.entries[content_hash] = old_entry
        
        system.consolidate()
        
        # 旧记忆应该被清理
        assert len(system.semantic.entries) == 0
    
    def test_consolidate_when_semantic_disabled(self):
        """测试语义禁用时整合"""
        system = MemorySystem(enable_semantic=False)
        
        # 不应抛出异常
        system.consolidate()


class TestMemorySystemIntegration:
    """测试记忆系统集成场景"""
    
    def test_full_conversation_flow(self, tmp_path):
        """测试完整对话流程"""
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        # 模拟对话
        system.working.add_message("user", "What is Python?")
        system.working.add_message("assistant", "Python is a programming language")
        
        # 重要信息进入语义记忆
        system.add_to_semantic("Python is a programming language", importance=0.8)
        
        # 后续查询
        context = system.retrieve_context("programming")
        
        assert "Python" in context or "programming" in context.lower()
    
    def test_memory_layers_independence(self):
        """测试记忆层独立性"""
        system = MemorySystem()
        
        # 添加到工作记忆
        system.working.add_message("user", "Working memory content")
        
        # 不应影响其他层
        if system.semantic:
            assert len(system.semantic.entries) == 0
        if system.episodic:
            assert len(system.episodic.episodes) == 0


class TestMemorySystemEdgeCases:
    """测试边界情况"""
    
    def test_retrieve_with_empty_query(self):
        """测试空查询检索"""
        system = MemorySystem()
        
        context = system.retrieve_context("")
        
        assert isinstance(context, str)
    
    def test_retrieve_with_very_long_query(self):
        """测试超长查询检索"""
        system = MemorySystem()
        
        long_query = "A" * 10000
        context = system.retrieve_context(long_query)
        
        assert isinstance(context, str)
    
    def test_add_to_semantic_with_low_importance(self, tmp_path):
        """测试低重要性添加到语义记忆"""
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        system.add_to_semantic("Low importance", importance=0.5)
        
        # 低于阈值 (0.7) 不应添加
        assert len(system.semantic.entries) == 0


class TestMemorySystemPersistence:
    """测试记忆系统持久化"""
    
    def test_semantic_persistence(self, tmp_path):
        """测试语义记忆持久化"""
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        system.add_to_semantic("Persistent fact", importance=0.8)
        system.semantic._persist()
        
        # 创建新系统加载
        system2 = MemorySystem()
        system2.semantic.storage_path = tmp_path
        
        assert len(system2.semantic.entries) == 1
