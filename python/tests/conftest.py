"""
ShadowClaude 测试系统全局配置
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 测试配置
TEST_CONFIG = {
    "llm_mock": {
        "enabled": True,
        "response_delay_ms": 10,
        "default_model": "claude-sonnet-4-6-mock"
    },
    "memory": {
        "use_temp_storage": True,
        "cleanup_after_tests": True
    },
    "performance": {
        "benchmark_iterations": 100,
        "warmup_iterations": 10
    },
    "security": {
        "enable_injection_tests": True,
        "enable_permission_tests": True
    }
}

# 全局 Fixture
@pytest.fixture(autouse=True)
def setup_test_env():
    """每个测试前自动设置环境"""
    # 设置环境变量
    import os
    os.environ["SHADOWCLAUDE_TEST_MODE"] = "1"
    os.environ["SHADOWCLAUDE_MOCK_LLM"] = "1"
    
    yield
    
    # 清理
    pass

@pytest.fixture
def temp_dir(tmp_path):
    """提供临时目录"""
    return tmp_path

@pytest.fixture
def mock_llm_client():
    """提供 Mock LLM 客户端"""
    from tests.mocks.llm.mock_client import MockLLMClient
    return MockLLMClient()

@pytest.fixture
def mock_fs():
    """提供 Mock 文件系统"""
    from tests.mocks.fs.mock_fs import MockFileSystem
    return MockFileSystem()

@pytest.fixture
def mock_network():
    """提供 Mock 网络"""
    from tests.mocks.network.mock_http import MockHTTPClient
    return MockHTTPClient()
