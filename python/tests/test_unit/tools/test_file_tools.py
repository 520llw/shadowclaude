"""
文件工具测试
测试 read_file, write_file, edit_file 等文件工具
"""

import pytest
from pathlib import Path
from shadowclaude.tools import ToolRegistry


class TestReadFileTool:
    """测试 read_file 工具"""
    
    def test_read_existing_file(self, tmp_path):
        """测试读取现有文件"""
        registry = ToolRegistry()
        
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        result = registry.execute("read_file", {"path": str(test_file)})
        
        assert result.success is True
        assert "Hello, World!" in result.output
    
    def test_read_nonexistent_file(self, tmp_path):
        """测试读取不存在的文件"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {"path": str(tmp_path / "nonexistent.txt")})
        
        assert result.success is False
    
    def test_read_with_offset(self, tmp_path):
        """测试带偏移读取"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")
        
        result = registry.execute("read_file", {
            "path": str(test_file),
            "offset": 1
        })
        
        assert result.success is True
        assert "Line 1" not in result.output
        assert "Line 2" in result.output
    
    def test_read_with_limit(self, tmp_path):
        """测试带限制读取"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")
        
        result = registry.execute("read_file", {
            "path": str(test_file),
            "limit": 2
        })
        
        assert result.success is True
        assert result.metadata["lines"] == 2


class TestWriteFileTool:
    """测试 write_file 工具"""
    
    def test_write_new_file(self, tmp_path):
        """测试写入新文件"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "new.txt"
        
        result = registry.execute("write_file", {
            "path": str(test_file),
            "content": "New content"
        })
        
        assert result.success is True
        assert test_file.exists()
        assert test_file.read_text() == "New content"
    
    def test_write_overwrites_existing(self, tmp_path):
        """测试写入覆盖现有文件"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "existing.txt"
        test_file.write_text("Old content")
        
        result = registry.execute("write_file", {
            "path": str(test_file),
            "content": "New content"
        })
        
        assert result.success is True
        assert test_file.read_text() == "New content"
    
    def test_write_creates_parent_dirs(self, tmp_path):
        """测试写入创建父目录"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "nested" / "dir" / "file.txt"
        
        result = registry.execute("write_file", {
            "path": str(test_file),
            "content": "Content"
        })
        
        assert result.success is True
        assert test_file.exists()


class TestEditFileTool:
    """测试 edit_file 工具"""
    
    def test_edit_single_occurrence(self, tmp_path):
        """测试编辑单处"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        
        result = registry.execute("edit_file", {
            "path": str(test_file),
            "old_string": "World",
            "new_string": "Universe"
        })
        
        assert result.success is True
        assert test_file.read_text() == "Hello Universe"
        assert result.metadata["replacements"] == 1
    
    def test_edit_all_occurrences(self, tmp_path):
        """测试编辑所有出现"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("foo bar foo baz foo")
        
        result = registry.execute("edit_file", {
            "path": str(test_file),
            "old_string": "foo",
            "new_string": "qux",
            "replace_all": True
        })
        
        assert result.success is True
        assert test_file.read_text() == "qux bar qux baz qux"
        assert result.metadata["replacements"] == 3
    
    def test_edit_nonexistent_string(self, tmp_path):
        """测试编辑不存在的字符串"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        
        result = registry.execute("edit_file", {
            "path": str(test_file),
            "old_string": "Nonexistent",
            "new_string": "Replacement"
        })
        
        assert result.success is False
    
    def test_edit_nonexistent_file(self, tmp_path):
        """测试编辑不存在的文件"""
        registry = ToolRegistry()
        
        result = registry.execute("edit_file", {
            "path": str(tmp_path / "nonexistent.txt"),
            "old_string": "old",
            "new_string": "new"
        })
        
        assert result.success is False


class TestGlobSearchTool:
    """测试 glob_search 工具"""
    
    def test_search_pattern(self, tmp_path):
        """测试搜索模式"""
        registry = ToolRegistry()
        
        # 创建测试文件
        (tmp_path / "file1.py").write_text("python")
        (tmp_path / "file2.py").write_text("python")
        (tmp_path / "file.txt").write_text("text")
        
        result = registry.execute("glob_search", {
            "pattern": "*.py",
            "path": str(tmp_path)
        })
        
        assert result.success is True
        assert ".py" in result.output
    
    def test_search_no_matches(self, tmp_path):
        """测试无匹配搜索"""
        registry = ToolRegistry()
        
        result = registry.execute("glob_search", {
            "pattern": "*.nonexistent",
            "path": str(tmp_path)
        })
        
        assert result.success is True
        assert result.output == "" or result.metadata["matches"] == 0


class TestGrepSearchTool:
    """测试 grep_search 工具"""
    
    def test_search_content(self, tmp_path):
        """测试搜索内容"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nFoo Bar\nHello Again")
        
        result = registry.execute("grep_search", {
            "pattern": "Hello",
            "path": str(tmp_path)
        })
        
        assert result.success is True
        assert "Hello" in result.output
    
    def test_search_with_context(self, tmp_path):
        """测试带上下文搜索"""
        registry = ToolRegistry()
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        
        result = registry.execute("grep_search", {
            "pattern": "Line 3",
            "path": str(tmp_path),
            "context": 1
        })
        
        assert result.success is True


class TestBashTool:
    """测试 bash 工具"""
    
    def test_execute_simple_command(self):
        """测试执行简单命令"""
        registry = ToolRegistry()
        
        result = registry.execute("bash", {
            "command": "echo 'Hello'"
        })
        
        assert result.success is True
        assert "Hello" in result.output
    
    def test_execute_invalid_command(self):
        """测试执行无效命令"""
        registry = ToolRegistry()
        
        result = registry.execute("bash", {
            "command": "nonexistent_command_12345"
        })
        
        assert result.success is False
    
    def test_execute_with_timeout(self):
        """测试带超时执行"""
        registry = ToolRegistry()
        
        result = registry.execute("bash", {
            "command": "sleep 5",
            "timeout": 100  # 100ms 超时
        })
        
        assert result.success is False
        assert "timeout" in result.error.lower()


class TestWebFetchTool:
    """测试 WebFetch 工具"""
    
    def test_fetch_url(self):
        """测试获取 URL"""
        registry = ToolRegistry()
        
        result = registry.execute("WebFetch", {
            "url": "https://example.com",
            "prompt": "Get content"
        })
        
        # 可能成功或失败，取决于网络
        assert isinstance(result, ToolResult)


class TestTodoWriteTool:
    """测试 TodoWrite 工具"""
    
    def test_write_todos(self, tmp_path):
        """测试写入待办"""
        registry = ToolRegistry()
        
        import os
        os.chdir(tmp_path)
        
        result = registry.execute("TodoWrite", {
            "todos": [
                {"content": "Task 1", "activeForm": "default", "status": "pending"},
                {"content": "Task 2", "activeForm": "default", "status": "completed"}
            ]
        })
        
        assert result.success is True
        assert "Task 1" in result.output
        assert "Task 2" in result.output


class TestAgentTool:
    """测试 Agent 工具"""
    
    def test_create_agent(self, tmp_path):
        """测试创建 Agent"""
        registry = ToolRegistry()
        
        import os
        os.chdir(tmp_path)
        
        result = registry.execute("Agent", {
            "description": "Test agent",
            "prompt": "Do something",
            "subagent_type": "Explore"
        })
        
        assert result.success is True
        assert "Agent created" in result.output


class TestToolSearch:
    """测试 ToolSearch 工具"""
    
    def test_search_tools(self):
        """测试搜索工具"""
        registry = ToolRegistry()
        
        result = registry.execute("ToolSearch", {
            "query": "file",
            "max_results": 5
        })
        
        assert result.success is True
        assert "read_file" in result.output or "Found" in result.output
    
    def test_search_no_results(self):
        """测试无结果搜索"""
        registry = ToolRegistry()
        
        result = registry.execute("ToolSearch", {
            "query": "nonexistent_tool_xyz"
        })
        
        assert result.success is True
