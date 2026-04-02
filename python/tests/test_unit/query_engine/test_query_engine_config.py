"""
QueryEngine 配置与边缘案例测试
"""

import pytest
from shadowclaude.query_engine import (
    QueryEngine, QueryEngineConfig, StopReason
)


class TestQueryEngineConfigVariations:
    """测试 QueryEngine 配置变体"""
    
    def test_minimal_config(self):
        """测试最小配置"""
        config = QueryEngineConfig(
            max_turns=1,
            max_budget_tokens=1000,
            enable_auto_compact=False
        )
        engine = QueryEngine(config)
        
        assert engine.config.max_turns == 1
        assert not engine.config.enable_auto_compact
    
    def test_maximal_config(self):
        """测试最大配置"""
        config = QueryEngineConfig(
            max_turns=1000,
            max_budget_tokens=10_000_000,
            compact_after_turns=100,
            cache_static_prompt=True,
            enable_reflection=True,
            enable_auto_compact=True,
            enable_semantic_memory=True,
            enable_episodic_memory=True,
            enable_kairos=True,
            model="claude-opus-4",
            static_segment_size=8000,
            dynamic_segment_ratio=0.8
        )
        engine = QueryEngine(config)
        
        assert engine.config.max_turns == 1000
        assert engine.config.enable_kairos is True
    
    def test_zero_turns_config(self):
        """测试零回合配置"""
        config = QueryEngineConfig(max_turns=0)
        engine = QueryEngine(config)
        
        result = engine.submit_message("Test")
        
        assert result.stop_reason == StopReason.MAX_TURNS_REACHED
    
    def test_disabled_memory_systems(self):
        """测试禁用记忆系统"""
        config = QueryEngineConfig(
            enable_semantic_memory=False,
            enable_episodic_memory=False
        )
        engine = QueryEngine(config)
        
        # 记忆系统应被禁用
        assert engine.config.enable_semantic_memory is False
        assert engine.config.enable_episodic_memory is False


class TestPromptSegmentCache:
    """测试 Prompt 段缓存"""
    
    def test_static_segments_cached(self):
        """测试静态段缓存"""
        engine = QueryEngine()
        segments1 = engine.build_prompt_segments("Test")
        segments2 = engine.build_prompt_segments("Test")
        
        # 静态段的缓存键应该相同
        static1 = [s.cache_key for s in segments1 if s.is_static and s.cache_key]
        static2 = [s.cache_key for s in segments2 if s.is_static and s.cache_key]
        
        assert static1 == static2
    
    def test_dynamic_segments_not_cached(self):
        """测试动态段不缓存"""
        engine = QueryEngine()
        
        segments = engine.build_prompt_segments("Test")
        dynamic = [s for s in segments if not s.is_static]
        
        for seg in dynamic:
            assert seg.cache_key is None
    
    def test_cache_key_consistency(self):
        """测试缓存键一致性"""
        from shadowclaude.query_engine import PromptSegment
        
        seg1 = PromptSegment(content="same", is_static=True)
        seg2 = PromptSegment(content="same", is_static=True)
        
        assert seg1.compute_cache_key() == seg2.compute_cache_key()
    
    def test_different_content_different_cache_keys(self):
        """测试不同内容不同缓存键"""
        from shadowclaude.query_engine import PromptSegment
        
        seg1 = PromptSegment(content="content1", is_static=True)
        seg2 = PromptSegment(content="content2", is_static=True)
        
        assert seg1.compute_cache_key() != seg2.compute_cache_key()


class TestComplexUserInputs:
    """测试复杂用户输入"""
    
    def test_code_input(self):
        """测试代码输入"""
        engine = QueryEngine()
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
        """
        
        result = engine.submit_message(code)
        
        assert result.stop_reason == StopReason.COMPLETED
    
    def test_multiline_input(self):
        """测试多行输入"""
        engine = QueryEngine()
        multiline = """Line 1
Line 2
Line 3
Line 4"""
        
        segments = engine.build_prompt_segments(multiline)
        user_segment = next(s for s in segments if "User Request" in s.content)
        
        assert multiline in user_segment.content
    
    def test_markdown_input(self):
        """测试 Markdown 输入"""
        engine = QueryEngine()
        markdown = """# Heading
- Item 1
- Item 2
```python
print("hello")
```"""
        
        result = engine.submit_message(markdown)
        
        assert result.stop_reason == StopReason.COMPLETED


class TestSessionIsolation:
    """测试会话隔离"""
    
    def test_sessions_independent(self):
        """测试会话独立"""
        engine1 = QueryEngine()
        engine2 = QueryEngine()
        
        engine1.submit_message("Message to engine1")
        
        assert engine1.turn_count == 1
        assert engine2.turn_count == 0
    
    def test_different_session_ids(self):
        """测试不同会话 ID"""
        engine1 = QueryEngine()
        engine2 = QueryEngine()
        
        assert engine1.session_id != engine2.session_id
    
    def test_messages_not_shared(self):
        """测试消息不共享"""
        engine1 = QueryEngine()
        engine2 = QueryEngine()
        
        engine1.messages.append({"role": "user", "content": "test"})
        
        assert len(engine1.messages) == 1
        assert len(engine2.messages) == 0


class TestTokenEstimation:
    """测试 Token 估算"""
    
    def test_token_count_positive(self):
        """测试 Token 计数为正"""
        engine = QueryEngine()
        
        result = engine.submit_message("Hello world")
        
        assert result.usage["input_tokens"] > 0
        assert result.usage["output_tokens"] >= 0
    
    def test_longer_input_more_tokens(self):
        """测试更长输入更多 Token"""
        engine = QueryEngine()
        
        result1 = engine.submit_message("Hi")
        result2 = engine.submit_message("Hello world this is a longer message")
        
        # 更长输入应该有更多 token（简化估算）
        assert result2.usage["input_tokens"] >= result1.usage["input_tokens"]


class TestConcurrentAccess:
    """测试并发访问（模拟）"""
    
    def test_multiple_engines_concurrent(self):
        """测试多个引擎并发"""
        engines = [QueryEngine() for _ in range(10)]
        
        for i, engine in enumerate(engines):
            result = engine.submit_message(f"Message {i}")
            assert result.stop_reason == StopReason.COMPLETED
    
    def test_session_id_uniqueness_many(self):
        """测试大量会话 ID 唯一性"""
        session_ids = [QueryEngine().session_id for _ in range(100)]
        
        assert len(set(session_ids)) == len(session_ids)


class TestQueryEngineWithVariousModels:
    """测试不同模型配置"""
    
    def test_sonnet_model_config(self):
        """测试 Sonnet 模型配置"""
        config = QueryEngineConfig(model="claude-sonnet-4")
        engine = QueryEngine(config)
        
        assert engine.config.model == "claude-sonnet-4"
    
    def test_opus_model_config(self):
        """测试 Opus 模型配置"""
        config = QueryEngineConfig(model="claude-opus-4")
        engine = QueryEngine(config)
        
        assert engine.config.model == "claude-opus-4"


class TestTurnResultVariations:
    """测试回合结果变体"""
    
    def test_result_with_no_tools(self):
        """测试无工具结果"""
        result = TurnResult(
            prompt="test",
            output="output",
            matched_commands=(),
            matched_tools=(),
            tool_calls=[],
            usage={"input_tokens": 10, "output_tokens": 5},
            stop_reason=StopReason.COMPLETED,
            duration_ms=100
        )
        
        assert len(result.matched_tools) == 0
        assert len(result.tool_calls) == 0
    
    def test_result_with_tools(self):
        """测试有工具结果"""
        result = TurnResult(
            prompt="test",
            output="output",
            matched_commands=("cmd",),
            matched_tools=("tool1", "tool2"),
            tool_calls=[{"tool": "tool1", "output": "result"}],
            usage={"input_tokens": 10, "output_tokens": 5},
            stop_reason=StopReason.COMPLETED,
            duration_ms=100
        )
        
        assert len(result.matched_tools) == 2
        assert len(result.tool_calls) == 1
    
    def test_result_all_stop_reasons(self):
        """测试所有停止原因"""
        for reason in StopReason:
            result = TurnResult(
                prompt="test",
                output="",
                matched_commands=(),
                matched_tools=(),
                tool_calls=[],
                usage={},
                stop_reason=reason,
                duration_ms=0
            )
            assert result.stop_reason == reason


# 导入 TurnResult
from shadowclaude.query_engine import TurnResult
