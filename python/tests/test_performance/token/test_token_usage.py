"""
Token 消耗测试
测试系统的 Token 使用效率
"""

import pytest
from shadowclaude.query_engine import QueryEngine, QueryEngineConfig
from shadowclaude.memory import MemorySystem


class TestTokenTracking:
    """测试 Token 追踪"""
    
    def test_query_tracks_input_tokens(self):
        """测试查询追踪输入 Token"""
        engine = QueryEngine()
        
        initial = engine.total_input_tokens
        engine.submit_message("Test message")
        
        assert engine.total_input_tokens > initial
    
    def test_query_tracks_output_tokens(self):
        """测试查询追踪输出 Token"""
        engine = QueryEngine()
        
        initial = engine.total_output_tokens
        engine.submit_message("Test message")
        
        assert engine.total_output_tokens > initial
    
    def test_result_includes_usage(self):
        """测试结果包含使用量"""
        engine = QueryEngine()
        
        result = engine.submit_message("Test")
        
        assert "input_tokens" in result.usage
        assert "output_tokens" in result.usage


class TestTokenEfficiency:
    """测试 Token 效率"""
    
    def test_short_query_efficiency(self):
        """测试短查询效率"""
        engine = QueryEngine()
        
        result = engine.submit_message("Hi")
        
        # 短查询应该使用较少 token
        assert result.usage["input_tokens"] < 500
    
    def test_long_query_scaling(self):
        """测试长查询扩展"""
        engine = QueryEngine()
        
        short_result = engine.submit_message("Hi")
        long_result = engine.submit_message("A" * 1000)
        
        # 长查询应使用更多 token
        assert long_result.usage["input_tokens"] >= short_result.usage["input_tokens"]


class TestBudgetManagement:
    """测试预算管理"""
    
    def test_budget_tracked_across_queries(self):
        """测试跨查询预算追踪"""
        engine = QueryEngine()
        
        for i in range(5):
            engine.submit_message(f"Query {i}")
        
        # 总 token 应该累加
        total = engine.total_input_tokens + engine.total_output_tokens
        assert total > 0
    
    def test_budget_not_exceeded_early(self):
        """测试预算未过早超支"""
        config = QueryEngineConfig(max_budget_tokens=1000000)
        engine = QueryEngine(config)
        
        for i in range(10):
            engine.submit_message(f"Query {i}")
        
        total = engine.total_input_tokens + engine.total_output_tokens
        assert total < engine.config.max_budget_tokens


class TestTokenOptimization:
    """测试 Token 优化"""
    
    def test_prompt_caching_reduces_tokens(self):
        """测试 Prompt 缓存减少 Token"""
        engine = QueryEngine()
        
        # 第一次构建
        segments1 = engine.build_prompt_segments("Test")
        static1 = sum(len(s.content) for s in segments1 if s.is_static)
        
        # 第二次构建（静态部分应相同）
        segments2 = engine.build_prompt_segments("Different")
        static2 = sum(len(s.content) for s in segments2 if s.is_static)
        
        # 静态部分应该相同
        assert static1 == static2
    
    def test_compression_reduces_context(self):
        """测试压缩减少上下文"""
        engine = QueryEngine()
        
        # 添加许多消息
        for i in range(20):
            engine.memory_system.working.add_message("user", f"Message {i}")
        
        # 获取上下文
        context = engine.memory_system.retrieve_context("test")
        
        # 上下文应被合理限制
        assert len(context) < 10000


class TestMemoryTokenUsage:
    """测试记忆 Token 使用"""
    
    def test_semantic_retrieval_token_efficiency(self, tmp_path):
        """测试语义检索 Token 效率"""
        memory = MemorySystem()
        memory.semantic.storage_path = tmp_path
        
        # 添加许多记忆
        for i in range(50):
            memory.add_to_semantic(f"Fact {i}", importance=0.8)
        
        # 检索应返回有限结果
        context = memory.retrieve_context("fact", )
        
        # 上下文大小应合理
        assert len(context) < 5000


class TestTokenLimits:
    """测试 Token 限制"""
    
    def test_working_memory_token_limit(self):
        """测试工作记忆 Token 限制"""
        from shadowclaude.memory import WorkingMemory
        
        memory = WorkingMemory(max_tokens=1000)
        
        # 添加超出限制的消息
        for i in range(20):
            memory.add_message("user", f"Message {i} with some content")
        
        # 消息应被压缩
        estimated_tokens = sum(len(m["content"]) for m in memory.messages) // 4
        assert estimated_tokens <= memory.max_tokens * 1.2  # 允许一些误差
