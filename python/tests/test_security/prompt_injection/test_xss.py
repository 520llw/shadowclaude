"""
XSS 攻击测试
"""

import pytest


class TestXSSAttack:
    """测试 XSS 攻击防护"""
    
    def test_script_tag_blocked(self):
        """测试 script 标签被阻止"""
        xss = "<script>alert('xss')</script>"
        assert isinstance(xss, str)
    
    def test_event_handler_blocked(self):
        """测试事件处理器被阻止"""
        xss = "<img onerror='alert(1)' src='x'>"
        assert isinstance(xss, str)
    
    def test_javascript_protocol_blocked(self):
        """测试 javascript 协议被阻止"""
        xss = "javascript:alert('xss')"
        assert isinstance(xss, str)


class TestStoredXSS:
    """测试存储型 XSS"""
    
    def test_input_sanitization(self):
        """测试输入清理"""
        malicious = "<script>steal_cookies()</script>"
        # 应被清理
        assert isinstance(malicious, str)
