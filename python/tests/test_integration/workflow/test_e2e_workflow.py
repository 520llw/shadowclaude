"""
端到端工作流集成测试
测试完整的工作流程
"""

import pytest
from shadowclaude.query_engine import QueryEngine, StopReason
from shadowclaude.memory import MemorySystem
from shadowclaude.tools import ToolRegistry


class TestEndToEndBasicWorkflow:
    """测试基础端到端工作流"""
    
    def test_simple_query_workflow(self):
        """测试简单查询工作流"""
        engine = QueryEngine()
        
        # 执行查询
        result = engine.submit_message("Hello, how are you?")
        
        assert result.stop_reason == StopReason.COMPLETED
        assert result.output is not None
        assert result.duration_ms >= 0
    
    def test_query_with_context_workflow(self):
        """测试带上下文查询工作流"""
        engine = QueryEngine()
        context = {
            "cwd": "/test/project",
            "git_status": "main"
        }
        
        result = engine.submit_message(
            "What files are in the current directory?",
            context=context
        )
        
        assert result.stop_reason == StopReason.COMPLETED
    
    def test_multi_turn_workflow(self):
        """测试多轮工作流"""
        engine = QueryEngine()
        
        # 第一轮
        result1 = engine.submit_message("First message")
        assert result1.stop_reason == StopReason.COMPLETED
        
        # 第二轮
        result2 = engine.submit_message("Second message")
        assert result2.stop_reason == StopReason.COMPLETED
        
        assert engine.turn_count == 2


class TestEndToEndWithTools:
    """测试带工具的端到端工作流"""
    
    def test_query_with_file_read(self):
        """测试带文件读取的查询"""
        engine = QueryEngine()
        
        result = engine.submit_message(
            "Please read the file test.txt",
            tools_allowed=["read_file"]
        )
        
        assert result.stop_reason == StopReason.COMPLETED
        assert isinstance(result.matched_tools, tuple)
    
    def test_query_with_multiple_tools(self):
        """测试带多个工具的查询"""
        engine = QueryEngine()
        
        result = engine.submit_message(
            "Search for Python files and read them",
            tools_allowed=["glob_search", "read_file"]
        )
        
        assert result.stop_reason == StopReason.COMPLETED


class TestEndToEndWithMemory:
    """测试带记忆的端到端工作流"""
    
    def test_query_uses_semantic_memory(self, tmp_path):
        """测试查询使用语义记忆"""
        engine = QueryEngine()
        engine.memory_system.semantic.storage_path = tmp_path
        
        # 添加语义记忆
        engine.memory_system.add_to_semantic(
            "Python is a programming language",
            importance=0.8
        )
        
        # 查询
        result = engine.submit_message("Tell me about Python")
        
        assert result.stop_reason == StopReason.COMPLETED
    
    def test_query_uses_working_memory(self):
        """测试查询使用工作记忆"""
        engine = QueryEngine()
        
        # 添加工作记忆
        engine.memory_system.working.add_message(
            "user", "Previous question about Python"
        )
        
        # 查询
        result = engine.submit_message("What about JavaScript?")
        
        assert result.stop_reason == StopReason.COMPLETED


class TestStreamWorkflow:
    """测试流式工作流"""
    
    def test_stream_workflow_complete(self):
        """测试流式工作流完成"""
        engine = QueryEngine()
        
        events = list(engine.stream_submit_message("Test message"))
        
        # 应该有开始、增量、停止事件
        assert events[0]["type"] == "message_start"
        assert events[-1]["type"] == "message_stop"
    
    def test_stream_workflow_with_usage(self):
        """测试带使用信息的流式工作流"""
        engine = QueryEngine()
        
        events = list(engine.stream_submit_message("Test"))
        stop_event = events[-1]
        
        assert "usage" in stop_event
        assert "duration_ms" in stop_event


class TestWorkflowErrorHandling:
    """测试工作流错误处理"""
    
    def test_max_turns_workflow(self):
        """测试最大回合工作流"""
        from shadowclaude.query_engine import QueryEngineConfig
        
        config = QueryEngineConfig(max_turns=1)
        engine = QueryEngine(config)
        
        # 第一回合
        result1 = engine.submit_message("First")
        assert result1.stop_reason == StopReason.COMPLETED
        
        # 第二回合应被拒绝
        result2 = engine.submit_message("Second")
        assert result2.stop_reason == StopReason.MAX_TURNS_REACHED


class TestIntegrationWithAllSystems:
    """测试所有系统集成"""
    
    def test_full_system_integration(self, tmp_path):
        """测试完整系统集成"""
        # 创建引擎
        engine = QueryEngine()
        engine.memory_system.semantic.storage_path = tmp_path
        
        # 添加记忆
        engine.memory_system.add_to_semantic(
            "Important project knowledge",
            importance=0.9
        )
        
        # 添加工作记忆
        engine.memory_system.working.add_message(
            "user", "Current conversation context"
        )
        
        # 使用工具
        result = engine.submit_message(
            "Find information and process it",
            tools_allowed=["read_file", "glob_search"]
        )
        
        # 验证
        assert result.stop_reason == StopReason.COMPLETED
        assert engine.turn_count == 1


class TestWorkflowPerformance:
    """测试工作流性能"""
    
    def test_query_response_time(self):
        """测试查询响应时间"""
        import time
        
        engine = QueryEngine()
        
        start = time.time()
        result = engine.submit_message("Quick test")
        elapsed = (time.time() - start) * 1000
        
        # 应该在合理时间内完成
        assert elapsed < 1000  # 1秒
        assert result.duration_ms >= 0
    
    def test_multiple_queries_performance(self):
        """测试多查询性能"""
        import time
        
        engine = QueryEngine()
        
        start = time.time()
        for i in range(5):
            engine.submit_message(f"Query {i}")
        elapsed = time.time() - start
        
        # 5次查询应该很快
        assert elapsed < 3.0
