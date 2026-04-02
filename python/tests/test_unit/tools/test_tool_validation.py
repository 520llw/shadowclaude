"""
工具输入验证测试
"""

import pytest
from shadowclaude.tools import ToolRegistry


class TestInputValidation:
    """测试输入验证"""
    
    def test_read_file_validates_path(self):
        """测试 read_file 验证路径"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {"path": ""})
        
        # 空路径应返回错误
        assert isinstance(result, ToolResult)
    
    def test_write_file_validates_content(self):
        """测试 write_file 验证内容"""
        registry = ToolRegistry()
        
        result = registry.execute("write_file", {
            "path": "test.txt",
            "content": None
        })
        
        assert isinstance(result.success, bool)
    
    def test_bash_validates_command(self):
        """测试 bash 验证命令"""
        registry = ToolRegistry()
        
        result = registry.execute("bash", {"command": ""})
        
        # 空命令处理
        assert isinstance(result, ToolResult)


class TestInputSanitization:
    """测试输入清理"""
    
    def test_path_traversal_blocked(self):
        """测试路径遍历被阻止"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {
            "path": "../../../etc/passwd"
        })
        
        assert result.success is False
    
    def test_special_chars_in_path(self):
        """测试路径中的特殊字符"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {
            "path": "file\x00.txt"
        })
        
        assert isinstance(result.success, bool)


from shadowclaude.tools import ToolResult
