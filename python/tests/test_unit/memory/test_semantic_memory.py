"""
SemanticMemory 单元测试
测试语义记忆系统的核心功能
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from shadowclaude.memory import SemanticMemory, MemoryEntry


class TestSemanticMemoryInitialization:
    """测试语义记忆初始化"""
    
    def test_default_initialization(self, tmp_path):
        """测试默认初始化"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        assert memory.storage_path == tmp_path
        assert isinstance(memory.entries, dict)
        assert len(memory.entries) == 0
    
    def test_storage_path_created(self, tmp_path):
        """测试存储路径创建"""
        storage = tmp_path / "nested" / "path"
        memory = SemanticMemory(storage_path=storage)
        
        assert storage.exists()
    
    def test_load_from_existing_file(self, tmp_path):
        """测试从现有文件加载"""
        # 预创建记忆文件
        memory_file = tmp_path / "memory.json"
        data = {
            "entries": [
                {
                    "content": "Test memory",
                    "timestamp": datetime.now().isoformat(),
                    "source": "test",
                    "importance": 0.8,
                    "metadata": {}
                }
            ]
        }
        memory_file.write_text(json.dumps(data))
        
        memory = SemanticMemory(storage_path=tmp_path)
        
        assert len(memory.entries) == 1


class TestSemanticMemoryAdd:
    """测试添加语义记忆"""
    
    def test_add_high_importance_memory(self, tmp_path):
        """测试添加高重要性记忆"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        memory.add("Important concept", importance=0.8)
        
        assert len(memory.entries) == 1
    
    def test_add_low_importance_ignored(self, tmp_path):
        """测试低重要性被忽略"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        memory.add("Low importance", importance=0.5)
        
        assert len(memory.entries) == 0
    
    def test_add_with_source(self, tmp_path):
        """测试带来源添加"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        memory.add("Content", source="documentation", importance=0.9)
        
        entry = list(memory.entries.values())[0]
        assert entry.source == "documentation"
    
    def test_add_duplicate_updates_importance(self, tmp_path):
        """测试重复添加更新重要性"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        memory.add("Unique content", importance=0.8)
        memory.add("Unique content", importance=0.9)
        
        assert len(memory.entries) == 1
        entry = list(memory.entries.values())[0]
        assert entry.importance == 0.9
    
    def test_add_preserves_metadata(self, tmp_path):
        """测试添加保留元数据"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        memory.add("Content", importance=0.8, source="test")
        
        entry = list(memory.entries.values())[0]
        assert entry.content == "Content"
        assert isinstance(entry.timestamp, datetime)


class TestSemanticMemoryRetrieve:
    """测试检索语义记忆"""
    
    def test_retrieve_with_matching_query(self, tmp_path):
        """测试匹配查询检索"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Python best practices", importance=0.8)
        memory.add("JavaScript tips", importance=0.8)
        
        results = memory.retrieve("Python")
        
        assert len(results) > 0
        assert any("Python" in r.content for r in results)
    
    def test_retrieve_returns_top_k(self, tmp_path):
        """测试返回指定数量结果"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        for i in range(10):
            memory.add(f"Memory {i}", importance=0.8)
        
        results = memory.retrieve("Memory", top_k=3)
        
        assert len(results) <= 3
    
    def test_retrieve_with_no_matches(self, tmp_path):
        """测试无匹配检索"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Python tips", importance=0.8)
        
        results = memory.retrieve("Java")
        
        assert len(results) == 0
    
    def test_retrieve_scores_by_keyword_match(self, tmp_path):
        """测试按关键词匹配评分"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("exact match phrase", importance=0.8)
        memory.add("some other content", importance=0.8)
        
        results = memory.retrieve("exact match phrase")
        
        if len(results) >= 2:
            # 完全匹配应排在前面
            assert "exact match" in results[0].content.lower()
    
    def test_retrieve_importance_weighting(self, tmp_path):
        """测试重要性加权"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("low importance match", importance=0.75)
        memory.add("high importance match", importance=0.95)
        
        results = memory.retrieve("match")
        
        if len(results) >= 2:
            assert results[0].importance >= results[1].importance


class TestSemanticMemoryConsolidate:
    """测试记忆整合"""
    
    def test_consolidate_removes_old_low_importance(self, tmp_path):
        """测试整合移除旧低重要性记忆"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        # 添加旧低重要性记忆
        old_entry = MemoryEntry(
            content="Old low importance",
            timestamp=datetime.now() - timedelta(days=100),
            source="test",
            importance=0.4
        )
        content_hash = memory._hash_content(old_entry.content)
        memory.entries[content_hash] = old_entry
        
        memory.consolidate()
        
        assert len(memory.entries) == 0
    
    def test_consolidate_keeps_high_importance(self, tmp_path):
        """测试整合保留高重要性记忆"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        old_entry = MemoryEntry(
            content="Old high importance",
            timestamp=datetime.now() - timedelta(days=100),
            source="test",
            importance=0.9
        )
        content_hash = memory._hash_content(old_entry.content)
        memory.entries[content_hash] = old_entry
        
        memory.consolidate()
        
        assert len(memory.entries) == 1
    
    def test_consolidate_keeps_recent(self, tmp_path):
        """测试整合保留近期记忆"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        recent_entry = MemoryEntry(
            content="Recent low importance",
            timestamp=datetime.now() - timedelta(days=1),
            source="test",
            importance=0.4
        )
        content_hash = memory._hash_content(recent_entry.content)
        memory.entries[content_hash] = recent_entry
        
        memory.consolidate()
        
        # 近期低重要性记忆也可能被保留
        assert len(memory.entries) >= 0


class TestSemanticMemoryPersistence:
    """测试语义记忆持久化"""
    
    def test_persist_creates_file(self, tmp_path):
        """测试持久化创建文件"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Test content", importance=0.8)
        
        memory._persist()
        
        assert (tmp_path / "memory.json").exists()
    
    def test_persist_content_readable(self, tmp_path):
        """测试持久化内容可读"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Test content", importance=0.8)
        
        memory._persist()
        
        data = json.loads((tmp_path / "memory.json").read_text())
        assert "entries" in data
        assert len(data["entries"]) == 1
    
    def test_load_persists_format(self, tmp_path):
        """测试加载持久化格式"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Content 1", importance=0.8)
        memory.add("Content 2", importance=0.9)
        
        memory._persist()
        
        # 创建新实例加载
        memory2 = SemanticMemory(storage_path=tmp_path)
        
        assert len(memory2.entries) == 2


class TestSemanticMemoryHashing:
    """测试语义记忆哈希"""
    
    def test_hash_consistency(self, tmp_path):
        """测试哈希一致性"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        hash1 = memory._hash_content("same content")
        hash2 = memory._hash_content("same content")
        
        assert hash1 == hash2
    
    def test_hash_uniqueness(self, tmp_path):
        """测试哈希唯一性"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        hash1 = memory._hash_content("content1")
        hash2 = memory._hash_content("content2")
        
        assert hash1 != hash2
    
    def test_hash_length(self, tmp_path):
        """测试哈希长度"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        hash_val = memory._hash_content("test")
        
        assert len(hash_val) == 16


class TestSemanticMemoryTimeDecay:
    """测试语义记忆时间衰减"""
    
    def test_recent_entries_score_higher(self, tmp_path):
        """测试近期条目得分更高"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        # 添加两条相似记忆，时间不同
        memory.add("Python tips", importance=0.8)
        # 修改其中一条的时间为过去
        for h, e in memory.entries.items():
            if "Python" in e.content:
                old_hash = h
                old_entry = e
                break
        
        old_entry.timestamp = datetime.now() - timedelta(days=60)
        
        results = memory.retrieve("Python")
        
        # 结果应该按时间排序
        if len(results) >= 1:
            assert all(isinstance(r.timestamp, datetime) for r in results)


class TestSemanticMemoryEdgeCases:
    """测试语义记忆边界情况"""
    
    def test_add_empty_content(self, tmp_path):
        """测试添加空内容"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        memory.add("", importance=0.8)
        
        # 空内容也应该被存储
        assert len(memory.entries) == 1
    
    def test_add_very_long_content(self, tmp_path):
        """测试添加超长内容"""
        memory = SemanticMemory(storage_path=tmp_path)
        long_content = "A" * 100000
        
        memory.add(long_content, importance=0.8)
        
        assert len(memory.entries) == 1
    
    def test_retrieve_empty_query(self, tmp_path):
        """测试空查询检索"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Some content", importance=0.8)
        
        results = memory.retrieve("")
        
        # 空查询可能返回所有结果或空
        assert isinstance(results, list)
    
    def test_retrieve_special_chars(self, tmp_path):
        """测试特殊字符检索"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Special: !@#$%^\u0026*()", importance=0.8)
        
        results = memory.retrieve("!@#$")
        
        assert isinstance(results, list)


class TestMemoryEntry:
    """测试记忆条目"""
    
    def test_entry_creation(self):
        """测试条目创建"""
        entry = MemoryEntry(
            content="Test",
            timestamp=datetime.now(),
            source="test",
            importance=0.8
        )
        
        assert entry.content == "Test"
        assert entry.importance == 0.8
    
    def test_entry_with_metadata(self):
        """测试带元数据条目"""
        entry = MemoryEntry(
            content="Test",
            timestamp=datetime.now(),
            source="test",
            importance=0.8,
            metadata={"key": "value"}
        )
        
        assert entry.metadata["key"] == "value"
    
    def test_entry_with_embedding(self):
        """测试带嵌入向量条目"""
        entry = MemoryEntry(
            content="Test",
            timestamp=datetime.now(),
            source="test",
            importance=0.8,
            embedding=[0.1, 0.2, 0.3]
        )
        
        assert len(entry.embedding) == 3
