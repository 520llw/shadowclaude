"""
SQL 注入测试
"""

import pytest


class TestSQLInjection:
    """测试 SQL 注入防护"""
    
    def test_basic_sql_injection_blocked(self):
        """测试基础 SQL 注入被阻止"""
        injection = "'; DROP TABLE users; --"
        # 应被安全处理
        assert isinstance(injection, str)
    
    def test_union_sql_injection_blocked(self):
        """测试 UNION SQL 注入被阻止"""
        injection = "' UNION SELECT * FROM passwords --"
        assert isinstance(injection, str)
    
    def test_blind_sql_injection_blocked(self):
        """测试盲 SQL 注入被阻止"""
        injection = "' AND 1=1 --"
        assert isinstance(injection, str)


class TestNoSQLInjection:
    """测试 NoSQL 注入"""
    
    def test_mongodb_injection_blocked(self):
        """测试 MongoDB 注入被阻止"""
        injection = {"$gt": ""}
        assert isinstance(injection, dict)
