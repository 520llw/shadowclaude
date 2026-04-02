"""
QueryEngine 缓存测试
测试 Prompt 缓存和优化功能
"""

import pytest
from shadowclaude.query_engine import QueryEngine, PromptSegment


class TestPromptCaching:
    """测试 Prompt 缓存"""
    
    def test_static_segment_cache_key(self):
        """测试静态段缓存键"""
        segment = PromptSegment(
            content="System prompt v1",
            is_static=True,
            cache_key="system_v1"
        )
        
        key = segment.compute_cache_key()
        assert key == "system_v1"
    
    def test_auto_generated_cache_key(self):
        """测试自动生成缓存键"""
        segment = PromptSegment(
            content="Some static content",
            is_static=True
        )
        
        key = segment.compute_cache_key()
        assert len(key) == 16
        assert key != segment.content
    
    def test_same_content_same_key(self):
        """测试相同内容相同键"""
        seg1 = PromptSegment(content="same", is_static=True)
        seg2 = PromptSegment(content="same", is_static=True)
        
        assert seg1.compute_cache_key() == seg2.compute_cache_key()
    
    def test_different_content_different_key(self):
        """测试不同内容不同键"""
        seg1 = PromptSegment(content="content1", is_static=True)
        seg2 = PromptSegment(content="content2", is_static=True)
        
        assert seg1.compute_cache_key() != seg2.compute_cache_key()
    
    def test_dynamic_segment_no_cache(self):
        """测试动态段无缓存"""
        segment = PromptSegment(content="dynamic", is_static=False)
        
        assert segment.cache_key is None


class TestCacheHitRatio:
    """测试缓存命中率"""
    
    def test_static_segments_cached(self):
        """测试静态段被缓存"""
        engine = QueryEngine()
        
        segments1 = engine.build_prompt_segments("Query 1")
        segments2 = engine.build_prompt_segments("Query 2")
        
        # 静态段应该有相同缓存键
        static1 = [s.cache_key for s in segments1 if s.is_static]
        static2 = [s.cache_key for s in segments2 if s.is_static]
        
        assert static1 == static2
    
    def test_dynamic_segments_not_cached(self):
        """测试动态段不被缓存"""
        engine = QueryEngine()
        
        segments1 = engine.build_prompt_segments("Query 1")
        segments2 = engine.build_prompt_segments("Query 2")
        
        # 动态段内容不同
        dynamic1 = [s.content for s in segments1 if not s.is_static]
        dynamic2 = [s.content for s in segments2 if not s.is_static]
        
        assert dynamic1 != dynamic2


class TestCacheInvalidation:
    """测试缓存失效"""
    
    def test_cache_persists_across_queries(self):
        """测试缓存跨查询持久"""
        engine = QueryEngine()
        
        # 多次查询
        for i in range(5):
            engine.build_prompt_segments(f"Query {i}")
        
        # 系统身份段应保持一致
        segments = engine.build_prompt_segments("Final")
        system_seg = next(s for s in segments if "ShadowClaude" in s.content)
        
        assert system_seg.cache_key is not None
