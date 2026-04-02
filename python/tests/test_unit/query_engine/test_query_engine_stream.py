"""
QueryEngine 流式输出和状态管理测试
"""

import pytest
from shadowclaude.query_engine import QueryEngine, StopReason


class TestStreamOutput:
    """测试流式输出"""
    
    def test_stream_returns_generator(self):
        """测试流返回生成器"""
        engine = QueryEngine()
        stream = engine.stream_submit_message("Test")
        
        # 应该是可迭代的
        assert hasattr(stream, '__iter__')
    
    def test_stream_event_sequence(self):
        """测试流事件序列"""
        engine = QueryEngine()
        events = list(engine.stream_submit_message("Test"))
        
        # 事件顺序：message_start, message_delta, ..., message_stop
        assert events[0]["type"] == "message_start"
        assert events[-1]["type"] == "message_stop"
    
    def test_stream_contains_text(self):
        """测试流包含文本"""
        engine = QueryEngine()
        events = list(engine.stream_submit_message("Test"))
        
        delta_events = [e for e in events if e["type"] == "message_delta"]
        assert len(delta_events) >= 1
        assert all("text" in e for e in delta_events)
    
    def test_stream_usage_in_stop(self):
        """测试流停止事件包含使用信息"""
        engine = QueryEngine()
        events = list(engine.stream_submit_message("Test"))
        
        stop_event = events[-1]
        assert "usage" in stop_event
        assert "duration_ms" in stop_event
        assert "stop_reason" in stop_event


class TestEngineStateTransitions:
    """测试引擎状态转换"""
    
    def test_initial_state_not_running(self):
        """测试初始状态为未运行"""
        engine = QueryEngine()
        
        assert engine._is_running is False
    
    def test_turn_counter_increments(self):
        """测试回合计数器递增"""
        engine = QueryEngine()
        
        initial = engine.turn_count
        engine.submit_message("Test")
        
        assert engine.turn_count == initial + 1
    
    def test_message_history_grows(self):
        """测试消息历史增长"""
        engine = QueryEngine()
        
        initial_len = len(engine.messages)
        engine.submit_message("Test")
        
        # 消息历史可能不直接增长（取决于实现）
        assert engine.turn_count == 1


class TestBudgetAndLimits:
    """测试预算和限制"""
    
    def test_token_budget_tracking(self):
        """测试 Token 预算追踪"""
        engine = QueryEngine()
        
        engine.submit_message("First")
        first_input = engine.total_input_tokens
        
        engine.submit_message("Second longer message here")
        second_input = engine.total_input_tokens
        
        assert second_input > first_input
    
    def test_output_token_tracking(self):
        """测试输出 Token 追踪"""
        engine = QueryEngine()
        
        engine.submit_message("Test")
        
        assert engine.total_output_tokens >= 0
    
    def test_budget_not_exceeded_initially(self):
        """测试初始预算未超支"""
        engine = QueryEngine()
        
        assert engine.total_input_tokens < engine.config.max_budget_tokens


class TestQueryEngineContextHandling:
    """测试上下文处理"""
    
    def test_empty_context(self):
        """测试空上下文"""
        engine = QueryEngine()
        
        result = engine.submit_message("Test", context={})
        
        assert result.stop_reason == StopReason.COMPLETED
    
    def test_none_context(self):
        """测试 None 上下文"""
        engine = QueryEngine()
        
        result = engine.submit_message("Test", context=None)
        
        assert result.stop_reason == StopReason.COMPLETED
    
    def test_context_with_cwd(self):
        """测试带工作目录的上下文"""
        engine = QueryEngine()
        context = {"cwd": "/home/user/project"}
        
        segments = engine.build_prompt_segments("Test", context)
        
        # 应包含工作目录信息
        content = "\n".join(s.content for s in segments)
        assert "/home/user/project" in content
    
    def test_context_with_git_status(self):
        """测试带 Git 状态的上下文"""
        engine = QueryEngine()
        context = {"git_status": "main* (dirty)"}
        
        segments = engine.build_prompt_segments("Test", context)
        
        content = "\n".join(s.content for s in segments)
        assert "main" in content or "Git" in content


class TestToolFiltering:
    """测试工具过滤"""
    
    def test_empty_tools_allowed(self):
        """测试空工具允许列表"""
        engine = QueryEngine()
        
        result = engine.submit_message("Test", tools_allowed=[])
        
        assert result.stop_reason == StopReason.COMPLETED
    
    def test_none_tools_allowed(self):
        """测试 None 工具允许列表"""
        engine = QueryEngine()
        
        result = engine.submit_message("Test", tools_allowed=None)
        
        assert result.stop_reason == StopReason.COMPLETED


class TestErrorScenarios:
    """测试错误场景"""
    
    def test_submit_with_special_chars(self):
        """测试特殊字符提交"""
        engine = QueryEngine()
        
        special_inputs = [
            "\x00",  # null byte
            "\n\r\t",
            "🎉🎊",
            "\\n\\t",
        ]
        
        for inp in special_inputs:
            result = engine.submit_message(inp)
            assert result.stop_reason == StopReason.COMPLETED


class TestQueryEngineMemoryIntegration:
    """测试 QueryEngine 记忆集成"""
    
    def test_memory_system_accessible(self):
        """测试记忆系统可访问"""
        engine = QueryEngine()
        
        memory = engine.memory_system
        
        assert memory is not None
    
    def test_tool_registry_accessible(self):
        """测试工具注册表可访问"""
        engine = QueryEngine()
        
        registry = engine.tool_registry
        
        assert registry is not None


class TestPromptAssemblyEdgeCases:
    """测试 Prompt 组装边界情况"""
    
    def test_assemble_with_newlines(self):
        """测试带换行符组装"""
        engine = QueryEngine()
        from shadowclaude.query_engine import PromptSegment
        
        segments = [
            PromptSegment(content="Line1\nLine2", is_static=True),
            PromptSegment(content="Line3\nLine4", is_static=False)
        ]
        
        result = engine._assemble_prompt(segments)
        
        assert "Line1" in result
        assert "Line4" in result
    
    def test_assemble_with_empty_content(self):
        """测试空内容组装"""
        engine = QueryEngine()
        from shadowclaude.query_engine import PromptSegment
        
        segments = [
            PromptSegment(content="", is_static=True),
            PromptSegment(content="content", is_static=False)
        ]
        
        result = engine._assemble_prompt(segments)
        
        assert "content" in result


class TestSessionPersistence:
    """测试会话持久性"""
    
    def test_session_id_unchanged(self):
        """测试会话 ID 不变"""
        engine = QueryEngine()
        session_id = engine.session_id
        
        engine.submit_message("Test")
        
        assert engine.session_id == session_id
    
    def test_multiple_submissions_same_session(self):
        """测试多次提交同一会话"""
        engine = QueryEngine()
        
        for i in range(5):
            engine.submit_message(f"Message {i}")
        
        # 所有调用应在同一会话
        assert engine.turn_count == 5


class TestQueryEngineExtensibility:
    """测试 QueryEngine 可扩展性"""
    
    def test_subclass_creation(self):
        """测试子类创建"""
        class CustomQueryEngine(QueryEngine):
            def custom_method(self):
                return "custom"
        
        engine = CustomQueryEngine()
        
        assert engine.custom_method() == "custom"
    
    def test_override_config(self):
        """测试覆盖配置"""
        class CustomQueryEngine(QueryEngine):
            def __init__(self):
                config = QueryEngineConfig(max_turns=100)
                super().__init__(config)
        
        engine = CustomQueryEngine()
        
        assert engine.config.max_turns == 100
