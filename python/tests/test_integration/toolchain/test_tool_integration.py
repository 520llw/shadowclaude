"""
工具链集成测试
测试工具链的集成工作流
"""

import pytest
from shadowclaude.tools import ToolRegistry
from pathlib import Path


class TestFileToolChain:
    """测试文件工具链"""
    
    def test_search_read_edit_chain(self, tmp_path):
        """测试搜索-读取-编辑链"""
        registry = ToolRegistry()
        
        # 1. 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('hello')\n")
        
        # 2. 搜索文件
        search_result = registry.execute("glob_search", {
            "pattern": "*.py",
            "path": str(tmp_path)
        })
        assert search_result.success
        
        # 3. 读取文件
        read_result = registry.execute("read_file", {
            "path": str(test_file)
        })
        assert read_result.success
        
        # 4. 编辑文件
        edit_result = registry.execute("edit_file", {
            "path": str(test_file),
            "old_string": "print('hello')",
            "new_string": "print('world')"
        })
        assert edit_result.success
        
        # 5. 验证编辑
        content = test_file.read_text()
        assert "world" in content
    
    def test_grep_read_chain(self, tmp_path):
        """测试搜索-读取链"""
        registry = ToolRegistry()
        
        # 创建文件
        test_file = tmp_path / "code.py"
        test_file.write_text("TODO: fix this bug\nTODO: add tests\n")
        
        # 搜索 TODO
        grep_result = registry.execute("grep_search", {
            "pattern": "TODO",
            "path": str(tmp_path)
        })
        assert grep_result.success
        assert "TODO" in grep_result.output


class TestWebToolChain:
    """测试 Web 工具链"""
    
    def test_search_fetch_chain(self):
        """测试搜索-获取链"""
        registry = ToolRegistry()
        
        # 搜索
        search_result = registry.execute("WebSearch", {
            "query": "Python documentation"
        })
        
        # 即使网络不可用，也应该返回结果对象
        assert isinstance(search_result.success, bool)


class TestTaskToolChain:
    """测试任务工具链"""
    
    def test_todo_agent_chain(self, tmp_path):
        """测试待办-Agent 链"""
        import os
        os.chdir(tmp_path)
        
        registry = ToolRegistry()
        
        # 1. 创建待办
        todo_result = registry.execute("TodoWrite", {
            "todos": [
                {"content": "Explore codebase", "activeForm": "default", "status": "in_progress"}
            ]
        })
        assert todo_result.success
        
        # 2. 创建 Agent 执行
        agent_result = registry.execute("Agent", {
            "description": "Explore task",
            "prompt": "Explore the codebase",
            "subagent_type": "Explore"
        })
        assert agent_result.success


class TestToolErrorPropagation:
    """测试工具错误传播"""
    
    def test_failed_tool_returns_error(self):
        """测试失败工具返回错误"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {"path": "/nonexistent"})
        
        assert result.success is False
        assert result.error is not None
    
    def test_error_metadata_included(self):
        """测试错误包含元数据"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {"path": "/nonexistent"})
        
        assert result.metadata is not None


class TestToolPerformanceIntegration:
    """测试工具性能集成"""
    
    def test_multiple_tool_calls_performance(self, tmp_path):
        """测试多工具调用性能"""
        import time
        registry = ToolRegistry()
        
        # 创建测试文件
        for i in range(10):
            (tmp_path / f"file{i}.txt").write_text(f"content {i}")
        
        start = time.time()
        
        for i in range(10):
            registry.execute("read_file", {"path": str(tmp_path / f"file{i}.txt")})
        
        elapsed = time.time() - start
        
        assert elapsed < 2.0
