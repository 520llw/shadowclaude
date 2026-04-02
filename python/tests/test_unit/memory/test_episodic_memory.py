"""
EpisodicMemory 单元测试
测试情景记忆系统的核心功能
"""

import pytest
from datetime import datetime
from shadowclaude.memory import EpisodicMemory


class TestEpisodicMemoryInitialization:
    """测试情景记忆初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        memory = EpisodicMemory()
        
        assert memory.episodes.maxlen == 100
        assert len(memory.episodes) == 0
        assert memory.current_episode == []
    
    def test_custom_max_episodes(self):
        """测试自定义最大情景数"""
        memory = EpisodicMemory(max_episodes=50)
        
        assert memory.episodes.maxlen == 50


class TestEpisodicMemoryStartEpisode:
    """测试开始情景"""
    
    def test_start_episode_creates_new(self):
        """测试开始情景创建新记录"""
        memory = EpisodicMemory()
        
        memory.start_episode({"task": "coding"})
        
        assert len(memory.current_episode) == 1
        assert memory.current_episode[0]["type"] == "start"
    
    def test_start_episode_stores_context(self):
        """测试开始情景存储上下文"""
        memory = EpisodicMemory()
        context = {"task": "debug", "file": "main.py"}
        
        memory.start_episode(context)
        
        assert memory.current_episode[0]["context"] == context
    
    def test_start_episode_ends_previous(self):
        """测试开始新情景结束旧情景"""
        memory = EpisodicMemory()
        
        memory.start_episode({"task": "first"})
        memory.add_event("action", "did something")
        memory.start_episode({"task": "second"})
        
        # 旧情景应被保存
        assert len(memory.episodes) == 1
        assert len(memory.current_episode) == 1


class TestEpisodicMemoryAddEvent:
    """测试添加事件"""
    
    def test_add_event_to_current(self):
        """测试添加事件到当前情景"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        memory.add_event("user_message", "Hello")
        
        assert len(memory.current_episode) == 2
        assert memory.current_episode[1]["type"] == "user_message"
    
    def test_add_event_without_start(self):
        """测试未开始情景时添加事件"""
        memory = EpisodicMemory()
        
        memory.add_event("event", "data")
        
        # 应该添加到当前情景（即使未明确开始）
        assert len(memory.current_episode) == 1
    
    def test_add_event_stores_content(self):
        """测试添加事件存储内容"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        memory.add_event("tool_use", {"tool": "read_file", "args": {}})
        
        event = memory.current_episode[1]
        assert event["content"]["tool"] == "read_file"


class TestEpisodicMemoryEndEpisode:
    """测试结束情景"""
    
    def test_end_episode_saves_to_history(self):
        """测试结束情景保存到历史"""
        memory = EpisodicMemory()
        memory.start_episode({})
        memory.add_event("action", "test")
        
        memory.end_episode("Summary of episode")
        
        assert len(memory.episodes) == 1
        assert len(memory.current_episode) == 0
    
    def test_end_episode_adds_summary(self):
        """测试结束情景添加摘要"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        memory.end_episode("Task completed successfully")
        
        episode = list(memory.episodes)[0]
        assert episode["summary"] == "Task completed successfully"
    
    def test_end_episode_without_start(self):
        """测试未开始情景时结束"""
        memory = EpisodicMemory()
        
        memory.end_episode("summary")
        
        # 应该什么都不发生
        assert len(memory.episodes) == 0
    
    def test_end_episode_includes_end_event(self):
        """测试结束情景包含结束事件"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        memory.end_episode()
        
        episode = list(memory.episodes)[0]
        events = episode["events"]
        assert events[-1]["type"] == "end"


class TestEpisodicMemoryRetrieveSimilar:
    """测试检索相似情景"""
    
    def test_retrieve_similar_returns_recent(self):
        """测试检索相似返回最近情景"""
        memory = EpisodicMemory()
        
        for i in range(5):
            memory.start_episode({"task": f"task{i}"})
            memory.end_episode(f"Summary {i}")
        
        results = memory.retrieve_similar("query", top_k=3)
        
        assert len(results) == 3
    
    def test_retrieve_similar_with_no_episodes(self):
        """测试无情景时检索"""
        memory = EpisodicMemory()
        
        results = memory.retrieve_similar("query")
        
        assert results == []
    
    def test_retrieve_similar_returns_episodes(self):
        """测试检索返回情景列表"""
        memory = EpisodicMemory()
        memory.start_episode({"task": "coding"})
        memory.end_episode("Wrote some code")
        
        results = memory.retrieve_similar("coding")
        
        assert len(results) == 1
        assert "events" in results[0]


class TestEpisodicMemoryGetRecentContext:
    """测试获取近期上下文"""
    
    def test_get_recent_context_with_no_episodes(self):
        """测试无情景时获取上下文"""
        memory = EpisodicMemory()
        
        context = memory.get_recent_context()
        
        assert "No previous" in context
    
    def test_get_recent_context_returns_formatted(self):
        """测试获取格式化上下文"""
        memory = EpisodicMemory()
        memory.start_episode({})
        memory.add_event("user_message", "Hello")
        memory.add_event("assistant_message", "Hi there")
        memory.end_episode()
        
        context = memory.get_recent_context()
        
        assert "User:" in context or "user" in context.lower()
    
    def test_get_recent_context_limits_events(self):
        """测试上下文限制事件数"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        for i in range(20):
            memory.add_event("action", f"step {i}")
        
        memory.end_episode()
        
        context = memory.get_recent_context(n_events=5)
        
        # 应该只包含最近的事件
        lines = [l for l in context.split('\n') if l.strip()]
        assert len(lines) <= 10  # 允许一些格式行


class TestEpisodicMemoryMaxEpisodes:
    """测试最大情景数限制"""
    
    def test_max_episodes_enforced(self):
        """测试最大情景数强制执行"""
        memory = EpisodicMemory(max_episodes=3)
        
        for i in range(5):
            memory.start_episode({"task": i})
            memory.end_episode()
        
        assert len(memory.episodes) == 3
    
    def test_old_episodes_removed(self):
        """测试旧情景被移除"""
        memory = EpisodicMemory(max_episodes=2)
        
        memory.start_episode({"task": "first"})
        memory.end_episode("First summary")
        
        memory.start_episode({"task": "second"})
        memory.end_episode("Second summary")
        
        memory.start_episode({"task": "third"})
        memory.end_episode("Third summary")
        
        # 第一个应该被移除
        summaries = [ep.get("summary") for ep in memory.episodes]
        assert "First summary" not in summaries


class TestEpisodicMemoryTimestamps:
    """测试时间戳"""
    
    def test_events_have_timestamps(self):
        """测试事件有时间戳"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        event = memory.current_episode[0]
        
        assert "timestamp" in event
        # 应该是 ISO 格式
        assert isinstance(event["timestamp"], str)
    
    def test_timestamps_are_chronological(self):
        """测试时间戳按时间顺序"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        import time
        time.sleep(0.01)
        memory.add_event("action", "1")
        time.sleep(0.01)
        memory.add_event("action", "2")
        
        timestamps = [e["timestamp"] for e in memory.current_episode]
        assert timestamps[0] <= timestamps[1] <= timestamps[2]


class TestEpisodicMemoryEdgeCases:
    """测试边界情况"""
    
    def test_add_event_with_complex_content(self):
        """测试添加复杂内容事件"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        complex_content = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "null": None
        }
        
        memory.add_event("complex", complex_content)
        
        assert memory.current_episode[1]["content"] == complex_content
    
    def test_end_episode_twice(self):
        """测试两次结束情景"""
        memory = EpisodicMemory()
        memory.start_episode({})
        
        memory.end_episode("First")
        memory.end_episode("Second")  # 应该什么都不发生
        
        assert len(memory.episodes) == 1
    
    def test_retrieve_similar_with_unicode(self):
        """测试 Unicode 检索"""
        memory = EpisodicMemory()
        memory.start_episode({"task": "测试"})
        memory.end_episode("Unicode test")
        
        results = memory.retrieve_similar("测试")
        
        assert len(results) == 1
