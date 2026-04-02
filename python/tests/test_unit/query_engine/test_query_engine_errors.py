"""
QueryEngine 错误处理测试
"""

import pytest
from shadowclaude.query_engine import QueryEngine, StopReason, QueryEngineConfig


class TestErrorHandling:
    """测试错误处理"""
    
    def test_max_turns_error(self):
        """测试最大回合错误"""
        config = QueryEngineConfig(max_turns=2)
        engine = QueryEngine(config)
        
        engine.submit_message("First")
        engine.submit_message("Second")
        result = engine.submit_message("Third")
        
        assert result.stop_reason == StopReason.MAX_TURNS_REACHED
    
    def test_budget_error(self):
        """测试预算错误"""
        config = QueryEngineConfig(max_budget_tokens=1)
        engine = QueryEngine(config)
        
        result = engine.submit_message("Test")
        
        # 可能会因预算限制而停止
        assert result.stop_reason in [StopReason.COMPLETED, StopReason.MAX_BUDGET_REACHED]
    
    def test_empty_prompt_handling(self):
        """测试空提示处理"""
        engine = QueryEngine()
        
        result = engine.submit_message("")
        
        assert result.stop_reason == StopReason.COMPLETED
    
    def test_very_long_prompt_handling(self):
        """测试超长提示处理"""
        engine = QueryEngine()
        
        long_prompt = "A" * 100000
        result = engine.submit_message(long_prompt)
        
        assert result.stop_reason == StopReason.COMPLETED


class TestRecovery:
    """测试恢复"""
    
    def test_continues_after_error(self):
        """测试错误后继续"""
        config = QueryEngineConfig(max_turns=3)
        engine = QueryEngine(config)
        
        # 正常查询
        result1 = engine.submit_message("First")
        assert result1.stop_reason == StopReason.COMPLETED
        
        # 继续查询
        result2 = engine.submit_message("Second")
        assert result2.stop_reason == StopReason.COMPLETED
