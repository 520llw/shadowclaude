"""
LLM Provider 工厂 - 统一创建和管理 Provider 实例
"""

from typing import Dict, Type, Optional, List, Any
import os

from .base import LLMProvider
from ..config import (
    ConfigManager, ProviderType, ProviderConfig,
    AnthropicConfig, OpenAIConfig, OllamaConfig, LlamaCppConfig
)


class ProviderFactory:
    """Provider 工厂类"""
    
    _providers: Dict[ProviderType, Type[LLMProvider]] = {}
    _instances: Dict[ProviderType, LLMProvider] = {}
    
    @classmethod
    def register(cls, provider_type: ProviderType, provider_class: Type[LLMProvider]):
        """注册 Provider 类"""
        cls._providers[provider_type] = provider_class
    
    @classmethod
    def create(cls, provider_type: ProviderType, config: Optional[ProviderConfig] = None) -> LLMProvider:
        """创建 Provider 实例"""
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown provider type: {provider_type}")
        
        # 如果没有提供配置，从配置管理器获取
        if config is None:
            config_manager = ConfigManager()
            config = config_manager.get_provider(provider_type)
            if config is None:
                raise ValueError(f"No configuration found for provider: {provider_type}")
        
        provider_class = cls._providers[provider_type]
        return provider_class(config)
    
    @classmethod
    def get_or_create(cls, provider_type: ProviderType, config: Optional[ProviderConfig] = None) -> LLMProvider:
        """获取或创建 Provider 实例（单例模式）"""
        if provider_type not in cls._instances:
            cls._instances[provider_type] = cls.create(provider_type, config)
        return cls._instances[provider_type]
    
    @classmethod
    def clear_instances(cls):
        """清除所有缓存的实例"""
        cls._instances.clear()
    
    @classmethod
    def get_available_providers(cls) -> List[Dict[str, Any]]:
        """获取所有可用的 Provider 列表"""
        config_manager = ConfigManager()
        enabled = config_manager.get_enabled_providers()
        
        result = []
        for config in enabled:
            provider_type = config.type
            try:
                provider = cls.create(provider_type, config)
                health = provider.health_check()
                result.append({
                    "type": provider_type.value,
                    "name": provider.name,
                    "available": health["available"],
                    "models": health.get("models", []),
                    "priority": config.priority,
                })
            except Exception as e:
                result.append({
                    "type": provider_type.value,
                    "name": provider_type.value,
                    "available": False,
                    "error": str(e),
                    "priority": config.priority,
                })
        
        return sorted(result, key=lambda x: x["priority"])
    
    @classmethod
    def auto_select_provider(cls) -> Optional[LLMProvider]:
        """
        自动选择可用的 Provider
        按优先级顺序尝试，返回第一个可用的 Provider
        """
        config_manager = ConfigManager()
        enabled = config_manager.get_enabled_providers()
        
        for config in enabled:
            try:
                provider = cls.create(config.type, config)
                if provider.health_check()["available"]:
                    return provider
            except Exception:
                continue
        
        return None


# 延迟导入并注册 Provider
def _register_providers():
    """注册所有内置 Provider"""
    try:
        from .anthropic import AnthropicProvider
        ProviderFactory.register(ProviderType.ANTHROPIC, AnthropicProvider)
    except ImportError:
        pass
    
    try:
        from .openai import OpenAIProvider
        ProviderFactory.register(ProviderType.OPENAI, OpenAIProvider)
    except ImportError:
        pass
    
    try:
        from .ollama import OllamaProvider
        ProviderFactory.register(ProviderType.OLLAMA, OllamaProvider)
    except ImportError:
        pass
    
    try:
        from .llamacpp import LlamaCppProvider
        ProviderFactory.register(ProviderType.LLAMACPP, LlamaCppProvider)
    except ImportError:
        pass


# 模块加载时注册 Provider
_register_providers()
