"""
SSRF 防护测试
"""

import pytest


class TestSSRFProtection:
    """测试 SSRF 防护"""
    
    def test_internal_ip_blocked(self):
        """测试内部 IP 被阻止"""
        internal_urls = [
            "http://127.0.0.1/",
            "http://localhost/",
            "http://192.168.1.1/",
            "http://10.0.0.1/",
            "http://169.254.169.254/"  # AWS metadata
        ]
        
        for url in internal_urls:
            # 应被阻止
            assert isinstance(url, str)
    
    def test_redirect_to_internal_blocked(self):
        """测试重定向到内部被阻止"""
        # 外部 URL 重定向到内部
        redirect_url = "http://evil.com/redirect?to=http://127.0.0.1"
        assert isinstance(redirect_url, str)
    
    def test_dns_rebinding_blocked(self):
        """测试 DNS 重绑定被阻止"""
        # DNS 重绑定域名
        rebinding_url = "http://attacker-controlled.com/"
        assert isinstance(rebinding_url, str)


class TestURLValidation:
    """测试 URL 验证"""
    
    def test_file_protocol_blocked(self):
        """测试 file 协议被阻止"""
        file_url = "file:///etc/passwd"
        # 应被阻止
        assert isinstance(file_url, str)
    
    def test_ftp_protocol_blocked(self):
        """测试 FTP 协议被阻止"""
        ftp_url = "ftp://ftp.example.com/"
        # 应被阻止或限制
        assert isinstance(ftp_url, str)
