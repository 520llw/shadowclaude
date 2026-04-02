"""
工具系统边界测试
"""

import pytest
from shadowclaude.tools import ToolRegistry


class TestToolBoundaries:
    """测试工具边界"""
    
    def test_read_file_empty_path(self):
        """测试读取空路径"""
        registry = ToolRegistry()
        result = registry.execute("read_file", {"path": ""})
        assert isinstance(result.success, bool)
    
    def test_write_file_empty_content(self, tmp_path):
        """测试写入空内容"""
        registry = ToolRegistry()
        test_file = tmp_path / "empty.txt"
        result = registry.execute("write_file", {
            "path": str(test_file),
            "content": ""
        })
        assert result.success is True
    
    def test_bash_empty_command(self):
        """测试执行空命令"""
        registry = ToolRegistry()
        result = registry.execute("bash", {"command": ""})
        assert isinstance(result.success, bool)


class TestToolUnicode:
    """测试工具 Unicode"""
    
    def test_write_unicode_content(self, tmp_path):
        """测试写入 Unicode 内容"""
        registry = ToolRegistry()
        test_file = tmp_path / "unicode.txt"
        result = registry.execute("write_file", {
            "path": str(test_file),
            "content": "Unicode: 你好 🌍"
        })
        assert result.success is True
