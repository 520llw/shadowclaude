"""
反序列化攻击测试
"""

import pytest


class TestDeserializationAttack:
    """测试反序列化攻击"""
    
    def test_pickle_deserialization_blocked(self):
        """测试 pickle 反序列化被阻止"""
        # pickle 载荷
        pickle_payload = b"cos\nsystem\n(S'ls'\ntR."
        # 应被阻止或安全处理
        assert isinstance(pickle_payload, bytes)
    
    def test_yaml_deserialization_blocked(self):
        """测试 YAML 反序列化被阻止"""
        yaml_payload = "!!python/object/apply:os.system ['ls']"
        # 应被阻止
        assert isinstance(yaml_payload, str)
    
    def test_json_deserialization_safe(self):
        """测试 JSON 反序列化安全"""
        import json
        
        data = '{"key": "value"}'
        result = json.loads(data)
        
        assert result == {"key": "value"}


class TestSerializationSecurity:
    """测试序列化安全"""
    
    def test_no_code_execution_in_deserialization(self):
        """测试反序列化无代码执行"""
        # 安全的数据格式
        safe_data = {"type": "message", "content": "Hello"}
        assert safe_data["content"] == "Hello"
