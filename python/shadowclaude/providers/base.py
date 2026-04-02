"""
LLM Provider 抽象层 - 统一的 LLM 调用接口
"""

import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, AsyncIterator, Iterator, Callable
from enum import Enum
import asyncio
from contextlib import asynccontextmanager


class StreamEventType(Enum):
    """流式事件类型"""
    MESSAGE_START = "message_start"
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    CONTENT_BLOCK_STOP = "content_block_stop"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    ERROR = "error"
    PING = "ping"


@dataclass
class StreamEvent:
    """流式事件"""
    type: StreamEventType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def message_start(cls, message_id: str, model: str) -> "StreamEvent":
        return cls(
            type=StreamEventType.MESSAGE_START,
            data={"message_id": message_id, "model": model}
        )
    
    @classmethod
    def content_delta(cls, delta: str, index: int = 0) -> "StreamEvent":
        return cls(
            type=StreamEventType.CONTENT_BLOCK_DELTA,
            data={"delta": delta, "index": index}
        )
    
    @classmethod
    def message_delta(cls, stop_reason: Optional[str] = None, usage: Optional[Dict] = None) -> "StreamEvent":
        return cls(
            type=StreamEventType.MESSAGE_DELTA,
            data={"stop_reason": stop_reason, "usage": usage or {}}
        )
    
    @classmethod
    def message_stop(cls, usage: Optional[Dict] = None) -> "StreamEvent":
        return cls(
            type=StreamEventType.MESSAGE_STOP,
            data={"usage": usage or {}}
        )
    
    @classmethod
    def error(cls, error: str, code: Optional[str] = None) -> "StreamEvent":
        return cls(
            type=StreamEventType.ERROR,
            data={"error": error, "code": code}
        )


@dataclass
class TokenUsage:
    """Token 使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, other: "TokenUsage") -> "TokenUsage":
        """累加使用统计"""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens + other.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens + other.cache_read_input_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class LLMResponse:
    """LLM 响应结果"""
    content: str
    model: str
    usage: TokenUsage
    stop_reason: Optional[str] = None
    finish_reason: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    
    @classmethod
    def from_stream_events(cls, events: List[StreamEvent], model: str) -> "LLMResponse":
        """从流式事件构建响应"""
        content_parts = []
        usage = TokenUsage()
        stop_reason = None
        
        for event in events:
            if event.type == StreamEventType.CONTENT_BLOCK_DELTA:
                content_parts.append(event.data.get("delta", ""))
            elif event.type == StreamEventType.MESSAGE_DELTA:
                stop_reason = event.data.get("stop_reason")
                usage_data = event.data.get("usage", {})
                usage = TokenUsage(
                    input_tokens=usage_data.get("input_tokens", 0),
                    output_tokens=usage_data.get("output_tokens", 0),
                )
            elif event.type == StreamEventType.MESSAGE_STOP:
                usage_data = event.data.get("usage", {})
                usage = TokenUsage(
                    input_tokens=usage_data.get("input_tokens", 0),
                    output_tokens=usage_data.get("output_tokens", 0),
                )
        
        return cls(
            content="".join(content_parts),
            model=model,
            usage=usage,
            stop_reason=stop_reason
        )


@dataclass
class LLMRequest:
    """LLM 请求参数"""
    messages: List[Dict[str, str]]
    model: str
    system: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    stream: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "model": self.model,
            "messages": self.messages,
            "stream": self.stream,
        }
        
        if self.system:
            data["system"] = self.system
        if self.max_tokens is not None:
            data["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            data["temperature"] = self.temperature
        if self.top_p is not None:
            data["top_p"] = self.top_p
        if self.top_k is not None:
            data["top_k"] = self.top_k
        if self.stop_sequences:
            data["stop_sequences"] = self.stop_sequences
        if self.tools:
            data["tools"] = self.tools
        if self.tool_choice:
            data["tool_choice"] = self.tool_choice
            
        return data


class RetryStrategy:
    """重试策略"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retryable_errors: Optional[List[str]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retryable_errors = retryable_errors or [
            "rate_limit",
            "timeout",
            "connection_error",
            "service_unavailable",
        ]
    
    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """判断是否应重试"""
        if attempt >= self.max_retries:
            return False
        
        error_str = str(error).lower()
        return any(retryable in error_str for retryable in self.retryable_errors)


class LLMProvider(ABC):
    """
    LLM Provider 抽象基类
    
    所有 LLM Provider 必须实现此接口
    """
    
    def __init__(self, config: Any):
        self.config = config
        self._retry_strategy = RetryStrategy(
            max_retries=getattr(config, 'retries', 3),
            base_delay=getattr(config, 'retry_delay', 1.0),
            backoff_factor=getattr(config, 'retry_backoff', 2.0),
        )
        self._total_usage = TokenUsage()
        self._session_usage = TokenUsage()
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass
    
    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """
        非流式完成请求
        
        Args:
            request: LLM 请求参数
            
        Returns:
            LLM 响应结果
        """
        pass
    
    @abstractmethod
    def stream_complete(self, request: LLMRequest) -> Iterator[StreamEvent]:
        """
        流式完成请求
        
        Args:
            request: LLM 请求参数
            
        Yields:
            流式事件
        """
        pass
    
    @abstractmethod
    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        """异步非流式完成请求"""
        pass
    
    @abstractmethod
    async def astream_complete(self, request: LLMRequest) -> AsyncIterator[StreamEvent]:
        """异步流式完成请求"""
        pass
    
    def is_model_supported(self, model: str) -> bool:
        """检查模型是否受支持"""
        return model in self.supported_models
    
    def get_token_usage(self) -> TokenUsage:
        """获取总 Token 使用统计"""
        return self._total_usage
    
    def get_session_usage(self) -> TokenUsage:
        """获取当前会话 Token 使用统计"""
        return self._session_usage
    
    def reset_session_usage(self):
        """重置会话 Token 统计"""
        self._session_usage = TokenUsage()
    
    def _update_usage(self, usage: TokenUsage):
        """更新 Token 使用统计"""
        self._total_usage = self._total_usage.add(usage)
        self._session_usage = self._session_usage.add(usage)
    
    def _execute_with_retry(self, fn: Callable, *args, **kwargs):
        """带重试机制执行函数"""
        attempt = 0
        last_error = None
        
        while attempt <= self._retry_strategy.max_retries:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if not self._retry_strategy.should_retry(e, attempt):
                    raise
                
                delay = self._retry_strategy.calculate_delay(attempt)
                time.sleep(delay)
                attempt += 1
        
        raise last_error
    
    async def _aexecute_with_retry(self, fn: Callable, *args, **kwargs):
        """异步带重试机制执行函数"""
        attempt = 0
        last_error = None
        
        while attempt <= self._retry_strategy.max_retries:
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if not self._retry_strategy.should_retry(e, attempt):
                    raise
                
                delay = self._retry_strategy.calculate_delay(attempt)
                await asyncio.sleep(delay)
                attempt += 1
        
        raise last_error
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            包含状态信息的字典
        """
        return {
            "name": self.name,
            "available": self._check_availability(),
            "models": self.supported_models,
            "usage": {
                "input_tokens": self._total_usage.input_tokens,
                "output_tokens": self._total_usage.output_tokens,
                "total_tokens": self._total_usage.total_tokens,
            }
        }
    
    @abstractmethod
    def _check_availability(self) -> bool:
        """检查 Provider 是否可用"""
        pass
    
    def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        格式化消息（可由子类覆盖）
        
        Args:
            messages: 原始消息列表
            
        Returns:
            格式化后的消息列表
        """
        return messages
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算 Token 数量（简化版）
        
        Args:
            text: 输入文本
            
        Returns:
            估算的 Token 数量
        """
        # 简单估算：英文约 4 字符/token，中文约 1 字符/token
        # 实际应使用 tiktoken 或其他 tokenizer
        words = len(text.split())
        chars = len(text)
        return max(words, chars // 4) + chars // 10


class ProviderError(Exception):
    """Provider 错误基类"""
    pass


class AuthenticationError(ProviderError):
    """认证错误"""
    pass


class RateLimitError(ProviderError):
    """速率限制错误"""
    pass


class ModelNotFoundError(ProviderError):
    """模型未找到错误"""
    pass


class ContextLengthError(ProviderError):
    """上下文长度超限错误"""
    pass


class ServiceUnavailableError(ProviderError):
    """服务不可用错误"""
    pass
