"""
会话管理测试
"""

import pytest
from shadowclaude.query_engine import QueryEngine


class TestSessionManagement:
    """测试会话管理"""
    
    def test_session_isolation(self):
        """测试会话隔离"""
        engine1 = QueryEngine()
        engine2 = QueryEngine()
        
        engine1.submit_message("Message 1")
        
        assert engine1.turn_count == 1
        assert engine2.turn_count == 0
    
    def test_session_persistence(self):
        """测试会话持久性"""
        engine = QueryEngine()
        session_id = engine.session_id
        
        engine.submit_message("Message")
        
        # 会话 ID 应保持不变
        assert engine.session_id == session_id
    
    def test_multiple_sessions(self):
        """测试多会话"""
        engines = [QueryEngine() for _ in range(10)]
        
        session_ids = [e.session_id for e in engines]
        
        # 所有会话 ID 应唯一
        assert len(set(session_ids)) == 10
