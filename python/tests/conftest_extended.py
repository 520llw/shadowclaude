# conftest.py fixtures 扩展
"""
Pytest fixtures for ShadowClaude test suite
"""

import pytest


@pytest.fixture(scope="session")
def test_config():
    """全局测试配置"""
    return {
        "mock_llm": True,
        "mock_filesystem": True,
        "mock_network": True
    }


@pytest.fixture
def temp_workspace(tmp_path):
    """临时工作区"""
    return tmp_path


@pytest.fixture
def isolated_memory(tmp_path):
    """隔离的记忆系统"""
    from shadowclaude.memory import MemorySystem
    system = MemorySystem()
    system.semantic.storage_path = tmp_path
    return system
