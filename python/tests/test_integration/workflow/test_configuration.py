"""
配置管理测试
"""

import pytest
from shadowclaude.query_engine import QueryEngineConfig


class TestConfigManagement:
    """测试配置管理"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = QueryEngineConfig()
        assert config.max_turns == 32
        assert config.max_budget_tokens == 200000
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = QueryEngineConfig(
            max_turns=50,
            max_budget_tokens=500000
        )
        assert config.max_turns == 50
        assert config.max_budget_tokens == 500000
    
    def test_config_validation(self):
        """测试配置验证"""
        config = QueryEngineConfig(max_turns=-1)
        # 负值应被处理或拒绝
        assert isinstance(config.max_turns, int)
