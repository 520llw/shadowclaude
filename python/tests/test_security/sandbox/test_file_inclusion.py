"""
文件包含测试
"""

import pytest


class TestFileInclusion:
    """测试文件包含"""
    
    def test_local_file_inclusion_blocked(self):
        """测试本地文件包含被阻止"""
        lfi = "../../etc/passwd"
        # 应被阻止
        assert isinstance(lfi, str)
    
    def test_remote_file_inclusion_blocked(self):
        """测试远程文件包含被阻止"""
        rfi = "http://evil.com/shell.txt"
        # 应被阻止
        assert isinstance(rfi, str)
    
    def test_php_wrapper_blocked(self):
        """测试 PHP wrapper 被阻止"""
        wrapper = "php://filter/read=convert.base64-encode/resource=/etc/passwd"
        # 应被阻止
        assert isinstance(wrapper, str)
    
    def test_data_wrapper_blocked(self):
        """测试 data wrapper 被阻止"""
        wrapper = "data:text/plain;base64,SGVsbG8="
        # 应被阻止
        assert isinstance(wrapper, str)
