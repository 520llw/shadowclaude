"""
记忆系统持久化测试
"""

import pytest
import json
from datetime import datetime
from shadowclaude.memory import SemanticMemory, MemorySystem


class TestSemanticMemoryPersistence:
    """测试语义记忆持久化"""
    
    def test_save_to_disk(self, tmp_path):
        """测试保存到磁盘"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Important fact", importance=0.9)
        
        memory._persist()
        
        assert (tmp_path / "memory.json").exists()
    
    def test_load_from_disk(self, tmp_path):
        """测试从磁盘加载"""
        # 创建并保存
        memory1 = SemanticMemory(storage_path=tmp_path)
        memory1.add("Fact 1", importance=0.8)
        memory1.add("Fact 2", importance=0.9)
        memory1._persist()
        
        # 新实例加载
        memory2 = SemanticMemory(storage_path=tmp_path)
        
        assert len(memory2.entries) == 2
    
    def test_persist_format(self, tmp_path):
        """测试持久化格式"""
        memory = SemanticMemory(storage_path=tmp_path)
        memory.add("Test content", importance=0.8, source="test")
        memory._persist()
        
        data = json.loads((tmp_path / "memory.json").read_text())
        
        assert "entries" in data
        assert len(data["entries"]) == 1
        assert data["entries"][0]["content"] == "Test content"
        assert "timestamp" in data["entries"][0]


class TestMemoryCorruption:
    """测试记忆损坏处理"""
    
    def test_handles_corrupted_file(self, tmp_path):
        """测试处理损坏文件"""
        # 写入损坏的 JSON
        (tmp_path / "memory.json").write_text("not valid json{")
        
        # 应优雅处理
        memory = SemanticMemory(storage_path=tmp_path)
        assert len(memory.entries) == 0
    
    def test_handles_missing_file(self, tmp_path):
        """测试处理缺失文件"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        # 无文件应正常初始化
        assert len(memory.entries) == 0


class TestMemoryMigration:
    """测试记忆迁移"""
    
    def test_version_handling(self, tmp_path):
        """测试版本处理"""
        # 创建带版本信息的旧格式
        old_data = {
            "version": "1.0",
            "entries": [
                {
                    "content": "Old entry",
                    "timestamp": datetime.now().isoformat(),
                    "source": "old",
                    "importance": 0.5
                }
            ]
        }
        (tmp_path / "memory.json").write_text(json.dumps(old_data))
        
        memory = SemanticMemory(storage_path=tmp_path)
        
        # 应能加载旧格式
        assert len(memory.entries) == 1
