"""
配置管理系统 - 统一管理 LLM Provider 配置
支持 config.json、环境变量、加密存储 API Key
"""

import os
import json
import base64
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, List
from enum import Enum
import hashlib
import secrets


class ProviderType(Enum):
    """支持的 Provider 类型"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    timeout: int = 120
    retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    streaming: bool = True


@dataclass
class ProviderConfig:
    """Provider 配置基类"""
    type: ProviderType
    enabled: bool = True
    priority: int = 0  # 优先级，数字越小优先级越高
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    default_model: str = ""


@dataclass
class AnthropicConfig(ProviderConfig):
    """Anthropic Claude 配置"""
    api_key: str = ""  # 加密存储
    base_url: str = "https://api.anthropic.com"
    api_version: str = "2023-06-01"
    
    def __post_init__(self):
        self.type = ProviderType.ANTHROPIC
        if not self.default_model:
            self.default_model = "claude-sonnet-4-6"
        if not self.models:
            self.models = {
                "claude-opus-4-7": ModelConfig(
                    name="claude-opus-4-7",
                    max_tokens=128000,
                    temperature=0.7
                ),
                "claude-sonnet-4-6": ModelConfig(
                    name="claude-sonnet-4-6",
                    max_tokens=64000,
                    temperature=0.7
                ),
                "claude-haiku-4-4": ModelConfig(
                    name="claude-haiku-4-4",
                    max_tokens=8192,
                    temperature=0.7
                ),
            }


@dataclass
class OpenAIConfig(ProviderConfig):
    """OpenAI 配置"""
    api_key: str = ""  # 加密存储
    base_url: str = "https://api.openai.com/v1"
    organization: str = ""
    
    def __post_init__(self):
        self.type = ProviderType.OPENAI
        if not self.default_model:
            self.default_model = "gpt-4-turbo"
        if not self.models:
            self.models = {
                "gpt-4-turbo": ModelConfig(
                    name="gpt-4-turbo",
                    max_tokens=128000,
                    temperature=0.7
                ),
                "gpt-4": ModelConfig(
                    name="gpt-4",
                    max_tokens=8192,
                    temperature=0.7
                ),
                "gpt-3.5-turbo": ModelConfig(
                    name="gpt-3.5-turbo",
                    max_tokens=16385,
                    temperature=0.7
                ),
            }


@dataclass
class OllamaConfig(ProviderConfig):
    """Ollama 本地模型配置"""
    base_url: str = "http://localhost:11434"
    
    def __post_init__(self):
        self.type = ProviderType.OLLAMA
        if not self.default_model:
            self.default_model = "llama3.2"
        if not self.models:
            self.models = {
                "llama3.2": ModelConfig(
                    name="llama3.2",
                    max_tokens=4096,
                    temperature=0.7
                ),
                "codellama": ModelConfig(
                    name="codellama",
                    max_tokens=4096,
                    temperature=0.7
                ),
                "mistral": ModelConfig(
                    name="mistral",
                    max_tokens=8192,
                    temperature=0.7
                ),
            }


@dataclass
class LlamaCppConfig(ProviderConfig):
    """llama.cpp 本地模型配置"""
    model_path: str = ""
    n_ctx: int = 4096
    n_gpu_layers: int = 0
    n_batch: int = 512
    n_threads: int = 4
    
    def __post_init__(self):
        self.type = ProviderType.LLAMACPP
        if not self.default_model:
            self.default_model = "local"
        if not self.models:
            self.models = {
                "local": ModelConfig(
                    name="local",
                    max_tokens=4096,
                    temperature=0.7
                ),
            }


class SecureStorage:
    """简单的加密存储系统（用于 API Key）
    
    使用 Fernet 对称加密，密钥存储在系统密钥环或环境变量中
    """
    
    def __init__(self):
        self._key = self._get_or_create_key()
        self._fernet = None
        
    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        # 优先从环境变量获取
        env_key = os.environ.get("SHADOWCLAUDE_ENCRYPTION_KEY")
        if env_key:
            return base64.urlsafe_b64decode(env_key)
        
        # 尝试从密钥文件获取
        key_path = Path.home() / ".shadowclaude" / ".key"
        if key_path.exists():
            with open(key_path, "rb") as f:
                return base64.urlsafe_b64decode(f.read())
        
        # 创建新密钥
        key = secrets.token_bytes(32)
        encoded_key = base64.urlsafe_b64encode(key)
        
        # 保存密钥
        key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(encoded_key)
        os.chmod(key_path, 0o600)
        
        return key
    
    def _get_fernet(self):
        """获取 Fernet 实例"""
        if self._fernet is None:
            from cryptography.fernet import Fernet
            self._fernet = Fernet(base64.urlsafe_b64encode(self._key))
        return self._fernet
    
    def encrypt(self, plaintext: str) -> str:
        """加密字符串"""
        try:
            f = self._get_fernet()
            encrypted = f.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except ImportError:
            # 如果没有 cryptography，使用简单的 base64（不安全，仅用于测试）
            return f"base64:{base64.b64encode(plaintext.encode()).decode()}"
    
    def decrypt(self, ciphertext: str) -> str:
        """解密字符串"""
        try:
            if ciphertext.startswith("base64:"):
                # 测试模式
                return base64.b64decode(ciphertext[7:]).decode()
            
            f = self._get_fernet()
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            return f.decrypt(encrypted).decode()
        except ImportError:
            return ""
    
    def mask_key(self, key: str) -> str:
        """掩码显示 API Key"""
        if not key:
            return ""
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"


class ConfigManager:
    """配置管理器
    
    支持以下配置来源（优先级从高到低）：
    1. 运行时参数
    2. 环境变量
    3. config.json
    4. 默认值
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self.secure_storage = SecureStorage()
        
        # 配置对象
        self.providers: Dict[ProviderType, ProviderConfig] = {}
        self.global_settings: Dict[str, Any] = {}
        
        # 加载配置
        self._load_config()
        
    def _default_config_path(self) -> str:
        """获取默认配置路径"""
        # 优先使用项目目录
        project_config = Path("/root/.openclaw/workspace/shadowclaude/python/config.json")
        if project_config.parent.exists():
            return str(project_config)
        
        # 其次使用用户目录
        user_config = Path.home() / ".shadowclaude" / "config.json"
        return str(user_config)
    
    def _load_config(self):
        """加载配置"""
        # 初始化默认配置
        self._init_default_providers()
        
        # 从文件加载
        if Path(self.config_path).exists():
            self._load_from_file()
        
        # 从环境变量加载（覆盖文件配置）
        self._load_from_env()
    
    def _init_default_providers(self):
        """初始化默认 Provider 配置"""
        self.providers = {
            ProviderType.ANTHROPIC: AnthropicConfig(
                enabled=False,
                priority=1
            ),
            ProviderType.OPENAI: OpenAIConfig(
                enabled=False,
                priority=2
            ),
            ProviderType.OLLAMA: OllamaConfig(
                enabled=True,
                priority=3
            ),
            ProviderType.LLAMACPP: LlamaCppConfig(
                enabled=False,
                priority=4
            ),
        }
    
    def _load_from_file(self):
        """从配置文件加载"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载全局设置
            self.global_settings = data.get("settings", {})
            
            # 加载 Provider 配置
            providers_data = data.get("providers", {})
            
            for provider_type in ProviderType:
                if provider_type.value in providers_data:
                    self._load_provider_config(provider_type, providers_data[provider_type.value])
                    
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
    
    def _load_provider_config(self, provider_type: ProviderType, data: Dict):
        """加载单个 Provider 配置"""
        enabled = data.get("enabled", False)
        priority = data.get("priority", 0)
        
        if provider_type == ProviderType.ANTHROPIC:
            api_key = data.get("api_key", "")
            if api_key.startswith("enc:"):
                api_key = self.secure_storage.decrypt(api_key[4:])
            
            self.providers[provider_type] = AnthropicConfig(
                enabled=enabled,
                priority=priority,
                api_key=api_key,
                base_url=data.get("base_url", "https://api.anthropic.com"),
                api_version=data.get("api_version", "2023-06-01"),
            )
            
        elif provider_type == ProviderType.OPENAI:
            api_key = data.get("api_key", "")
            if api_key.startswith("enc:"):
                api_key = self.secure_storage.decrypt(api_key[4:])
            
            self.providers[provider_type] = OpenAIConfig(
                enabled=enabled,
                priority=priority,
                api_key=api_key,
                base_url=data.get("base_url", "https://api.openai.com/v1"),
                organization=data.get("organization", ""),
            )
            
        elif provider_type == ProviderType.OLLAMA:
            self.providers[provider_type] = OllamaConfig(
                enabled=enabled,
                priority=priority,
                base_url=data.get("base_url", "http://localhost:11434"),
            )
            
        elif provider_type == ProviderType.LLAMACPP:
            self.providers[provider_type] = LlamaCppConfig(
                enabled=enabled,
                priority=priority,
                model_path=data.get("model_path", ""),
                n_ctx=data.get("n_ctx", 4096),
                n_gpu_layers=data.get("n_gpu_layers", 0),
                n_batch=data.get("n_batch", 512),
                n_threads=data.get("n_threads", 4),
            )
    
    def _load_from_env(self):
        """从环境变量加载（高优先级）"""
        # Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            config = self.providers.get(ProviderType.ANTHROPIC)
            if config:
                config.api_key = anthropic_key
                config.enabled = True
            else:
                self.providers[ProviderType.ANTHROPIC] = AnthropicConfig(
                    api_key=anthropic_key,
                    enabled=True,
                    priority=1
                )
        
        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            config = self.providers.get(ProviderType.OPENAI)
            if config:
                config.api_key = openai_key
                config.enabled = True
            else:
                self.providers[ProviderType.OPENAI] = OpenAIConfig(
                    api_key=openai_key,
                    enabled=True,
                    priority=2
                )
        
        # Ollama
        ollama_url = os.environ.get("OLLAMA_BASE_URL")
        if ollama_url:
            config = self.providers.get(ProviderType.OLLAMA)
            if config:
                config.base_url = ollama_url
                config.enabled = True
        
        # LlamaCpp
        llamacpp_path = os.environ.get("LLAMACPP_MODEL_PATH")
        if llamacpp_path:
            config = self.providers.get(ProviderType.LLAMACPP)
            if config:
                config.model_path = llamacpp_path
                config.enabled = True
    
    def save_config(self):
        """保存配置到文件"""
        # 构建配置字典
        data = {
            "settings": self.global_settings,
            "providers": {}
        }
        
        for provider_type, config in self.providers.items():
            provider_data = {
                "enabled": config.enabled,
                "priority": config.priority,
            }
            
            if isinstance(config, AnthropicConfig):
                provider_data["api_key"] = f"enc:{self.secure_storage.encrypt(config.api_key)}" if config.api_key else ""
                provider_data["base_url"] = config.base_url
                provider_data["api_version"] = config.api_version
                
            elif isinstance(config, OpenAIConfig):
                provider_data["api_key"] = f"enc:{self.secure_storage.encrypt(config.api_key)}" if config.api_key else ""
                provider_data["base_url"] = config.base_url
                provider_data["organization"] = config.organization
                
            elif isinstance(config, OllamaConfig):
                provider_data["base_url"] = config.base_url
                
            elif isinstance(config, LlamaCppConfig):
                provider_data["model_path"] = config.model_path
                provider_data["n_ctx"] = config.n_ctx
                provider_data["n_gpu_layers"] = config.n_gpu_layers
                provider_data["n_batch"] = config.n_batch
                provider_data["n_threads"] = config.n_threads
            
            data["providers"][provider_type.value] = provider_data
        
        # 确保目录存在
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_enabled_providers(self) -> List[ProviderConfig]:
        """获取启用的 Provider 列表（按优先级排序）"""
        return sorted(
            [p for p in self.providers.values() if p.enabled],
            key=lambda p: p.priority
        )
    
    def get_provider(self, provider_type: ProviderType) -> Optional[ProviderConfig]:
        """获取指定 Provider 配置"""
        return self.providers.get(provider_type)
    
    def get_model_config(self, provider_type: ProviderType, model_name: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        provider = self.providers.get(provider_type)
        if provider:
            return provider.models.get(model_name)
        return None
    
    def set_api_key(self, provider_type: ProviderType, api_key: str):
        """设置 API Key"""
        provider = self.providers.get(provider_type)
        if provider and hasattr(provider, 'api_key'):
            provider.api_key = api_key
            provider.enabled = bool(api_key)
    
    def create_config_template(self) -> str:
        """创建配置模板"""
        template = {
            "settings": {
                "default_provider": "anthropic",
                "default_model": "claude-sonnet-4-6",
                "log_level": "info",
                "request_timeout": 120,
                "max_retries": 3,
            },
            "providers": {
                "anthropic": {
                    "enabled": False,
                    "priority": 1,
                    "api_key": "",
                    "base_url": "https://api.anthropic.com",
                    "api_version": "2023-06-01"
                },
                "openai": {
                    "enabled": False,
                    "priority": 2,
                    "api_key": "",
                    "base_url": "https://api.openai.com/v1",
                    "organization": ""
                },
                "ollama": {
                    "enabled": True,
                    "priority": 3,
                    "base_url": "http://localhost:11434"
                },
                "llamacpp": {
                    "enabled": False,
                    "priority": 4,
                    "model_path": "/path/to/model.gguf",
                    "n_ctx": 4096,
                    "n_gpu_layers": 0,
                    "n_batch": 512,
                    "n_threads": 4
                }
            }
        }
        return json.dumps(template, indent=2, ensure_ascii=False)


# 全局配置实例
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


def reload_config():
    """重新加载配置"""
    global _config_instance
    _config_instance = ConfigManager()
