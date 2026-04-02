"""
QueryEngine 核心测试 - 基础功能
测试 QueryEngine 的初始化、配置和基本操作
"""

import pytest
from shadowclaude.query_engine import (
    QueryEngine, QueryEngineConfig, PromptSegment,
    StopReason, TurnResult
)


class TestQueryEngineInitialization:
    """测试 QueryEngine 初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        engine = QueryEngine()
        
        assert engine.config is not None
        assert engine.config.max_turns == 32
        assert engine.config.max_budget_tokens == 200000
        assert engine.session_id.startswith("sc-")
        assert len(engine.messages) == 0
        assert engine.turn_count == 0
    
    def test_custom_config_initialization(self):
        """测试自定义配置初始化"""
        config = QueryEngineConfig(
            max_turns=50,
            max_budget_tokens=500000,
            model="claude-opus-4"
        )
        engine = QueryEngine(config)
        
        assert engine.config.max_turns == 50
        assert engine.config.max_budget_tokens == 500000
        assert engine.config.model == "claude-opus-4"
    
    def test_session_id_uniqueness(self):
        """测试会话 ID 唯一性"""
        engine1 = QueryEngine()
        engine2 = QueryEngine()
        
        assert engine1.session_id != engine2.session_id
    
    def test_lazy_initialization_memory_system(self):
        """测试记忆系统延迟初始化"""
        engine = QueryEngine()
        
        # 访问前不应初始化
        assert engine._memory_system is None
        
        # 访问后应初始化
        memory = engine.memory_system
        assert memory is not None
        assert engine._memory_system is not None
    
    def test_lazy_initialization_tool_registry(self):
        """测试工具注册表延迟初始化"""
        engine = QueryEngine()
        
        assert engine._tool_registry is None
        
        registry = engine.tool_registry
        assert registry is not None
        assert engine._tool_registry is not None


class TestPromptSegment:
    """测试 Prompt 分段功能"""
    
    def test_static_segment_creation(self):
        """测试静态分段创建"""
        segment = PromptSegment(
            content="System identity",
            is_static=True,
            cache_key="system_v1"
        )
        
        assert segment.content == "System identity"
        assert segment.is_static is True
        assert segment.cache_key == "system_v1"
    
    def test_dynamic_segment_creation(self):
        """测试动态分段创建"""
        segment = PromptSegment(
            content="User input: test",
            is_static=False
        )
        
        assert segment.is_static is False
        assert segment.cache_key is None
    
    def test_cache_key_computation(self):
        """测试缓存键计算"""
        segment = PromptSegment(
            content="Test content",
            is_static=True
        )
        
        key = segment.compute_cache_key()
        assert len(key) == 16
        assert key != "Test content"  # 应为哈希值
    
    def test_cache_key_priority(self):
        """测试缓存键优先级"""
        segment = PromptSegment(
            content="Content",
            is_static=True,
            cache_key="explicit_key"
        )
        
        key = segment.compute_cache_key()
        assert key == "explicit_key"


class TestBuildPromptSegments:
    """测试 Prompt 分段构建"""
    
    def test_basic_segment_building(self):
        """测试基本分段构建"""
        engine = QueryEngine()
        segments = engine.build_prompt_segments("Hello")
        
        assert len(segments) >= 4  # system, tools, safety, context, user
        
        # 检查静态段
        static_segments = [s for s in segments if s.is_static]
        assert len(static_segments) >= 3
        
        # 检查动态段
        dynamic_segments = [s for s in segments if not s.is_static]
        assert len(dynamic_segments) >= 2
    
    def test_context_inclusion(self):
        """测试上下文包含"""
        engine = QueryEngine()
        context = {
            "cwd": "/test/path",
            "git_status": "main"
        }
        
        segments = engine.build_prompt_segments("Hello", context)
        
        # 找到上下文段
        context_segment = next(
            (s for s in segments if "Current directory" in s.content),
            None
        )
        assert context_segment is not None
        assert "/test/path" in context_segment.content
    
    def test_user_input_segment(self):
        """测试用户输入分段"""
        engine = QueryEngine()
        user_input = "Please analyze this code"
        
        segments = engine.build_prompt_segments(user_input)
        
        user_segment = next(
            (s for s in segments if "User Request" in s.content),
            None
        )
        assert user_segment is not None
        assert user_input in user_segment.content
        assert user_segment.is_static is False


class TestAssemblePrompt:
    """测试 Prompt 组装"""
    
    def test_assemble_empty_segments(self):
        """测试空分段组装"""
        engine = QueryEngine()
        result = engine._assemble_prompt([])
        assert result == ""
    
    def test_assemble_single_segment(self):
        """测试单分段组装"""
        engine = QueryEngine()
        segments = [PromptSegment(content="Hello", is_static=True)]
        
        result = engine._assemble_prompt(segments)
        assert result == "Hello"
    
    def test_assemble_multiple_segments(self):
        """测试多分段组装"""
        engine = QueryEngine()
        segments = [
            PromptSegment(content="Segment 1", is_static=True),
            PromptSegment(content="Segment 2", is_static=False)
        ]
        
        result = engine._assemble_prompt(segments)
        assert "Segment 1" in result
        assert "Segment 2" in result
        assert "\n\n" in result
    
    def test_segment_order_preserved(self):
        """测试分段顺序保持"""
        engine = QueryEngine()
        segments = [
            PromptSegment(content="First", is_static=True),
            PromptSegment(content="Second", is_static=True),
            PromptSegment(content="Third", is_static=True)
        ]
        
        result = engine._assemble_prompt(segments)
        first_idx = result.index("First")
        second_idx = result.index("Second")
        third_idx = result.index("Third")
        
        assert first_idx < second_idx < third_idx


class TestTurnResult:
    """测试回合结果"""
    
    def test_turn_result_creation(self):
        """测试回合结果创建"""
        result = TurnResult(
            prompt="Test prompt",
            output="Test output",
            matched_commands=("cmd1",),
            matched_tools=("tool1",),
            tool_calls=[],
            usage={"input_tokens": 100, "output_tokens": 50},
            stop_reason=StopReason.COMPLETED,
            duration_ms=150
        )
        
        assert result.prompt == "Test prompt"
        assert result.output == "Test output"
        assert result.stop_reason == StopReason.COMPLETED
        assert result.duration_ms == 150
    
    def test_stop_reason_enum(self):
        """测试停止原因枚举"""
        assert StopReason.COMPLETED.value == "completed"
        assert StopReason.MAX_TURNS_REACHED.value == "max_turns_reached"
        assert StopReason.MAX_BUDGET_REACHED.value == "max_budget_reached"
        assert StopReason.USER_INTERRUPT.value == "user_interrupt"
        assert StopReason.ERROR.value == "error"


class TestQueryEngineConfig:
    """测试 QueryEngine 配置"""
    
    def test_default_config_values(self):
        """测试默认配置值"""
        config = QueryEngineConfig()
        
        assert config.max_turns == 32
        assert config.max_budget_tokens == 200000
        assert config.compact_after_turns == 12
        assert config.cache_static_prompt is True
        assert config.enable_reflection is True
        assert config.enable_auto_compact is True
    
    def test_config_immutability_check(self):
        """测试配置修改"""
        config = QueryEngineConfig()
        config.max_turns = 100
        
        assert config.max_turns == 100


class TestSessionStateManagement:
    """测试会话状态管理"""
    
    def test_initial_state(self):
        """测试初始状态"""
        engine = QueryEngine()
        
        assert engine._is_running is False
        assert engine._current_turn == 0
        assert engine.total_input_tokens == 0
        assert engine.total_output_tokens == 0
    
    def test_token_tracking(self):
        """测试 Token 追踪"""
        engine = QueryEngine()
        
        # 模拟更新
        engine.total_input_tokens += 100
        engine.total_output_tokens += 50
        
        assert engine.total_input_tokens == 100
        assert engine.total_output_tokens == 50
    
    def test_turn_counting(self):
        """测试回合计数"""
        engine = QueryEngine()
        
        engine.turn_count += 1
        assert engine.turn_count == 1
        
        engine.turn_count += 1
        assert engine.turn_count == 2


class TestBudgetEnforcement:
    """测试预算执行"""
    
    def test_budget_not_exceeded(self):
        """测试预算未超支"""
        config = QueryEngineConfig(max_budget_tokens=1000)
        engine = QueryEngine(config)
        
        engine.total_input_tokens = 500
        
        # 应允许继续
        assert engine.total_input_tokens < engine.config.max_budget_tokens
    
    def test_budget_exceeded_check(self):
        """测试预算超支检查"""
        config = QueryEngineConfig(max_budget_tokens=100)
        engine = QueryEngine(config)
        
        engine.total_input_tokens = 150
        
        # 应检测到超支
        assert engine.total_input_tokens > engine.config.max_budget_tokens


class TestQueryEngineEdgeCases:
    """测试边界情况"""
    
    def test_empty_user_input(self):
        """测试空用户输入"""
        engine = QueryEngine()
        segments = engine.build_prompt_segments("")
        
        assert len(segments) > 0
    
    def test_very_long_user_input(self):
        """测试超长用户输入"""
        engine = QueryEngine()
        long_input = "A" * 10000
        
        segments = engine.build_prompt_segments(long_input)
        user_segment = next(s for s in segments if "User Request" in s.content)
        
        assert long_input in user_segment.content
    
    def test_special_characters_in_input(self):
        """测试特殊字符输入"""
        engine = QueryEngine()
        special_input = "Hello\n\t!@#$%^&*()"
        
        segments = engine.build_prompt_segments(special_input)
        user_segment = next(s for s in segments if "User Request" in s.content)
        
        assert special_input in user_segment.content
    
    def test_unicode_input(self):
        """测试 Unicode 输入"""
        engine = QueryEngine()
        unicode_input = "你好世界 🌍 привет"
        
        segments = engine.build_prompt_segments(unicode_input)
        user_segment = next(s for s in segments if "User Request" in s.content)
        
        assert unicode_input in user_segment.content
