"""
Anthropic Claude Provider 实现
"""

import json
import time
from typing import Dict, List, Optional, Any, Iterator, AsyncIterator
import httpx

from .base import (
    LLMProvider, LLMRequest, LLMResponse, StreamEvent, StreamEventType,
    TokenUsage, AuthenticationError, RateLimitError, ModelNotFoundError,
    ContextLengthError, ServiceUnavailableError, ProviderError
)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API Provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key
        self.base_url = config.base_url.rstrip("/")
        self.api_version = config.api_version
        self._client = None
        self._async_client = None
        
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "claude-opus-4-7",
            "claude-sonnet-4-6",
            "claude-haiku-4-4",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
        ]
    
    def _get_client(self):
        """获取同步 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.api_version,
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client
    
    def _get_async_client(self):
        """获取异步 HTTP 客户端"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.api_version,
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._async_client
    
    def _check_availability(self) -> bool:
        """检查 API 是否可用"""
        if not self.api_key:
            return False
        try:
            response = self._get_client().get("/v1/models")
            return response.status_code == 200
        except Exception:
            return False
    
    def _handle_error(self, response: httpx.Response):
        """处理错误响应"""
        try:
            error_data = response.json()
            error = error_data.get("error", {})
            error_type = error.get("type", "")
            error_message = error.get("message", "Unknown error")
        except:
            error_type = "unknown"
            error_message = f"HTTP {response.status_code}: {response.text}"
        
        if response.status_code == 401:
            raise AuthenticationError(f"Invalid API key: {error_message}")
        elif response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        elif response.status_code == 404:
            raise ModelNotFoundError(f"Model not found: {error_message}")
        elif response.status_code == 413:
            raise ContextLengthError(f"Context too long: {error_message}")
        elif response.status_code >= 500:
            raise ServiceUnavailableError(f"Service unavailable: {error_message}")
        else:
            raise ProviderError(f"API error ({response.status_code}): {error_message}")
    
    def _build_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """构建请求体"""
        body = {
            "model": request.model,
            "messages": self.format_messages(request.messages),
            "max_tokens": request.max_tokens or 4096,
        }
        
        if request.system:
            body["system"] = request.system
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.top_p is not None:
            body["top_p"] = request.top_p
        if request.top_k is not None:
            body["top_k"] = request.top_k
        if request.stop_sequences:
            body["stop_sequences"] = request.stop_sequences
        if request.tools:
            body["tools"] = request.tools
        if request.tool_choice:
            body["tool_choice"] = request.tool_choice
        if request.stream:
            body["stream"] = True
            
        return body
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        """非流式完成请求"""
        start_time = time.time()
        
        def _do_complete():
            body = self._build_request_body(request)
            body["stream"] = False
            
            response = self._get_client().post("/v1/messages", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            # 提取内容
            content_parts = []
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content_parts.append(block.get("text", ""))
            
            # 提取使用统计
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
            )
            usage.total_tokens = usage.input_tokens + usage.output_tokens
            
            self._update_usage(usage)
            
            # 提取工具调用
            tool_calls = []
            for block in data.get("content", []):
                if block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                    })
            
            return LLMResponse(
                content="".join(content_parts),
                model=data.get("model", request.model),
                usage=usage,
                stop_reason=data.get("stop_reason"),
                tool_calls=tool_calls,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        
        return self._execute_with_retry(_do_complete)
    
    def stream_complete(self, request: LLMRequest) -> Iterator[StreamEvent]:
        """流式完成请求"""
        start_time = time.time()
        
        def _do_stream():
            body = self._build_request_body(request)
            
            with self._get_client().stream(
                "POST",
                "/v1/messages",
                json=body,
            ) as response:
                if response.status_code != 200:
                    # 对于流式错误，我们需要先读取内容
                    error_text = response.read().decode()
                    self._handle_error(httpx.Response(
                        status_code=response.status_code,
                        content=error_text.encode(),
                    ))
                
                message_id = None
                model = request.model
                usage = TokenUsage()
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    line = line.decode() if isinstance(line, bytes) else line
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        
                        if data_str.strip() == "[DONE]":
                            continue
                        
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        
                        event_type = data.get("type")
                        
                        if event_type == "message_start":
                            message = data.get("message", {})
                            message_id = message.get("id")
                            model = message.get("model", model)
                            usage_data = message.get("usage", {})
                            usage.input_tokens = usage_data.get("input_tokens", 0)
                            
                            yield StreamEvent.message_start(message_id, model)
                        
                        elif event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield StreamEvent.content_delta(
                                    delta.get("text", ""),
                                    data.get("index", 0)
                                )
                        
                        elif event_type == "message_delta":
                            delta = data.get("delta", {})
                            usage_data = data.get("usage", {})
                            usage.output_tokens = usage_data.get("output_tokens", 0)
                            
                            yield StreamEvent.message_delta(
                                stop_reason=delta.get("stop_reason"),
                                usage={
                                    "input_tokens": usage.input_tokens,
                                    "output_tokens": usage.output_tokens,
                                }
                            )
                
                usage.total_tokens = usage.input_tokens + usage.output_tokens
                self._update_usage(usage)
                
                yield StreamEvent.message_stop({
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                })
        
        try:
            yield from self._execute_with_retry(_do_stream)
        except Exception as e:
            yield StreamEvent.error(str(e), type(e).__name__)
    
    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        """异步非流式完成请求"""
        start_time = time.time()
        
        async def _do_complete():
            body = self._build_request_body(request)
            body["stream"] = False
            
            client = self._get_async_client()
            response = await client.post("/v1/messages", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            # 提取内容
            content_parts = []
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content_parts.append(block.get("text", ""))
            
            # 提取使用统计
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
            )
            usage.total_tokens = usage.input_tokens + usage.output_tokens
            
            self._update_usage(usage)
            
            return LLMResponse(
                content="".join(content_parts),
                model=data.get("model", request.model),
                usage=usage,
                stop_reason=data.get("stop_reason"),
                duration_ms=int((time.time() - start_time) * 1000),
            )
        
        return await self._aexecute_with_retry(_do_complete)
    
    async def astream_complete(self, request: LLMRequest) -> AsyncIterator[StreamEvent]:
        """异步流式完成请求"""
        start_time = time.time()
        
        async def _do_stream():
            body = self._build_request_body(request)
            
            client = self._get_async_client()
            
            async with client.stream(
                "POST",
                "/v1/messages",
                json=body,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    self._handle_error(httpx.Response(
                        status_code=response.status_code,
                        content=error_text,
                    ))
                
                message_id = None
                model = request.model
                usage = TokenUsage()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        
                        if data_str.strip() == "[DONE]":
                            continue
                        
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        
                        event_type = data.get("type")
                        
                        if event_type == "message_start":
                            message = data.get("message", {})
                            message_id = message.get("id")
                            model = message.get("model", model)
                            usage_data = message.get("usage", {})
                            usage.input_tokens = usage_data.get("input_tokens", 0)
                            
                            yield StreamEvent.message_start(message_id, model)
                        
                        elif event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield StreamEvent.content_delta(
                                    delta.get("text", ""),
                                    data.get("index", 0)
                                )
                        
                        elif event_type == "message_delta":
                            delta = data.get("delta", {})
                            usage_data = data.get("usage", {})
                            usage.output_tokens = usage_data.get("output_tokens", 0)
                            
                            yield StreamEvent.message_delta(
                                stop_reason=delta.get("stop_reason"),
                                usage={
                                    "input_tokens": usage.input_tokens,
                                    "output_tokens": usage.output_tokens,
                                }
                            )
                
                usage.total_tokens = usage.input_tokens + usage.output_tokens
                self._update_usage(usage)
                
                yield StreamEvent.message_stop({
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                })
        
        try:
            async for event in self._aexecute_with_retry(_do_stream):
                yield event
        except Exception as e:
            yield StreamEvent.error(str(e), type(e).__name__)
    
    def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息为 Anthropic 格式"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Anthropic 只支持 user 和 assistant 角色
            if role == "system":
                continue  # system 消息单独处理
            
            formatted.append({
                "role": role,
                "content": content,
            })
        
        return formatted
