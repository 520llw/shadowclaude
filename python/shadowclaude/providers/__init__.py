"""
ShadowClaude LLM Providers 模块

提供统一的 LLM Provider 抽象层，支持：
- Anthropic Claude API
- OpenAI API
- Ollama 本地模型
- llama.cpp 本地模型

使用示例：
    from shadowclaude.providers import ProviderFactory, LLMRequest
    from shadowclaude.config import ProviderType
    
    # 创建 Provider
    provider = ProviderFactory.create(ProviderType.ANTHROPIC)
    
    # 创建请求
    request = LLMRequest(
        messages=[{"role": "user", "content": "Hello!"}],
        model="claude-sonnet-4-6",
        max_tokens=1024,
    )
    
    # 同步调用
    response = provider.complete(request)
    print(response.content)
    
    # 流式调用
    for event in provider.stream_complete(request):
        if event.type == StreamEventType.CONTENT_BLOCK_DELTA:
            print(event.data["delta"], end="")
"""

from .base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    StreamEvent,
    StreamEventType,
    TokenUsage,
    RetryStrategy,
    ProviderError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    ContextLengthError,
    ServiceUnavailableError,
)

from .factory import ProviderFactory

# 可选导入具体 Provider 实现
try:
    from .anthropic import AnthropicProvider
except ImportError:
    AnthropicProvider = None

try:
    from .openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from .ollama import OllamaProvider
except ImportError:
    OllamaProvider = None

try:
    from .llamacpp import LlamaCppProvider
except ImportError:
    LlamaCppProvider = None


__all__ = [
    # 基础类
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "StreamEvent",
    "StreamEventType",
    "TokenUsage",
    "RetryStrategy",
    
    # 异常类
    "ProviderError",
    "AuthenticationError",
    "RateLimitError",
    "ModelNotFoundError",
    "ContextLengthError",
    "ServiceUnavailableError",
    
    # 工厂
    "ProviderFactory",
    
    # Provider 实现
    "AnthropicProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "LlamaCppProvider",
]


def list_providers() -> list:
    """列出所有可用的 Provider"""
    return ProviderFactory.get_available_providers()


def get_provider(provider_type: str = None) -> LLMProvider:
    """
    获取 Provider 实例
    
    Args:
        provider_type: Provider 类型名称，如 "anthropic", "openai", "ollama", "llamacpp"
                      如果为 None，则自动选择可用的 Provider
    
    Returns:
        LLMProvider 实例
    """
    from ..config import ProviderType
    
    if provider_type is None:
        return ProviderFactory.auto_select_provider()
    
    try:
        pt = ProviderType(provider_type.lower())
        return ProviderFactory.create(pt)
    except ValueError:
        raise ValueError(f"Unknown provider type: {provider_type}")
