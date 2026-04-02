"""
OpenAI API Provider 实现
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


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key
        self.base_url = config.base_url.rstrip("/")
        self.organization = config.organization
        self._client = None
        self._async_client = None
        
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-4-32k",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4o",
            "gpt-4o-mini",
        ]
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers
    
    def _get_client(self):
        """获取同步 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client
    
    def _get_async_client(self):
        """获取异步 HTTP 客户端"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._async_client
    
    def _check_availability(self) -> bool:
        """检查 API 是否可用"""
        if not self.api_key:
            return False
        try:
            response = self._get_client().get("/models")
            return response.status_code == 200
        except Exception:
            return False
    
    def _handle_error(self, response: httpx.Response):
        """处理错误响应"""
        try:
            error_data = response.json()
            error = error_data.get("error", {})
            error_type = error.get("type", "")
            error_code = error.get("code", "")
            error_message = error.get("message", "Unknown error")
        except:
            error_type = "unknown"
            error_code = ""
            error_message = f"HTTP {response.status_code}: {response.text}"
        
        if response.status_code == 401:
            raise AuthenticationError(f"Invalid API key: {error_message}")
        elif response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        elif response.status_code == 404 or "model" in error_message.lower():
            raise ModelNotFoundError(f"Model not found: {error_message}")
        elif "context_length_exceeded" in error_code or response.status_code == 413:
            raise ContextLengthError(f"Context too long: {error_message}")
        elif response.status_code >= 500:
            raise ServiceUnavailableError(f"Service unavailable: {error_message}")
        else:
            raise ProviderError(f"API error ({response.status_code}): {error_message}")
    
    def _build_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """构建请求体"""
        # OpenAI 不支持 system 参数，需要添加到 messages 中
        messages = request.messages.copy()
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        
        body = {
            "model": request.model,
            "messages": messages,
        }
        
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.top_p is not None:
            body["top_p"] = request.top_p
        if request.stop_sequences:
            body["stop"] = request.stop_sequences
        if request.tools:
            body["tools"] = request.tools
            if request.tool_choice:
                body["tool_choice"] = request.tool_choice
        if request.stream:
            body["stream"] = True
            # OpenAI 流式响应包含使用统计
            body["stream_options"] = {"include_usage": True}
            
        return body
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        """非流式完成请求"""
        start_time = time.time()
        
        def _do_complete():
            body = self._build_request_body(request)
            body["stream"] = False
            
            response = self._get_client().post("/chat/completions", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            # 提取内容
            content = message.get("content", "")
            
            # 提取使用统计
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
            )
            usage.total_tokens = usage_data.get("total_tokens", usage.input_tokens + usage.output_tokens)
            
            self._update_usage(usage)
            
            # 提取工具调用
            tool_calls = []
            for tc in message.get("tool_calls", []):
                tool_calls.append({
                    "id": tc.get("id"),
                    "name": tc.get("function", {}).get("name"),
                    "input": json.loads(tc.get("function", {}).get("arguments", "{}")),
                })
            
            return LLMResponse(
                content=content or "",
                model=data.get("model", request.model),
                usage=usage,
                stop_reason=choice.get("finish_reason"),
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
                "/chat/completions",
                json=body,
            ) as response:
                if response.status_code != 200:
                    error_text = response.read().decode()
                    self._handle_error(httpx.Response(
                        status_code=response.status_code,
                        content=error_text.encode(),
                    ))
                
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
                        
                        # 检查是否是使用统计（OpenAI 在最后发送）
                        usage_data = data.get("usage")
                        if usage_data:
                            usage.input_tokens = usage_data.get("prompt_tokens", 0)
                            usage.output_tokens = usage_data.get("completion_tokens", 0)
                            usage.total_tokens = usage_data.get("total_tokens", 0)
                            continue
                        
                        # 处理选择项
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        
                        # 消息开始
                        if choice.get("index") == 0 and "role" in delta:
                            yield StreamEvent.message_start(
                                data.get("id", ""),
                                data.get("model", model)
                            )
                        
                        # 内容增量
                        content = delta.get("content", "")
                        if content:
                            yield StreamEvent.content_delta(content)
                        
                        # 工具调用
                        tool_calls = delta.get("tool_calls", [])
                        for tc in tool_calls:
                            if tc.get("function", {}).get("arguments"):
                                yield StreamEvent(
                                    type=StreamEventType.CONTENT_BLOCK_DELTA,
                                    data={
                                        "tool_call": tc,
                                        "delta": tc.get("function", {}).get("arguments", "")
                                    }
                                )
                        
                        # 完成原因
                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            yield StreamEvent.message_delta(
                                stop_reason=finish_reason,
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
            response = await client.post("/chat/completions", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            content = message.get("content", "")
            
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
            )
            usage.total_tokens = usage_data.get("total_tokens", usage.input_tokens + usage.output_tokens)
            
            self._update_usage(usage)
            
            return LLMResponse(
                content=content or "",
                model=data.get("model", request.model),
                usage=usage,
                stop_reason=choice.get("finish_reason"),
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
                "/chat/completions",
                json=body,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    self._handle_error(httpx.Response(
                        status_code=response.status_code,
                        content=error_text,
                    ))
                
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
                        
                        # 检查使用统计
                        usage_data = data.get("usage")
                        if usage_data:
                            usage.input_tokens = usage_data.get("prompt_tokens", 0)
                            usage.output_tokens = usage_data.get("completion_tokens", 0)
                            usage.total_tokens = usage_data.get("total_tokens", 0)
                            continue
                        
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        
                        if choice.get("index") == 0 and "role" in delta:
                            yield StreamEvent.message_start(
                                data.get("id", ""),
                                data.get("model", model)
                            )
                        
                        content = delta.get("content", "")
                        if content:
                            yield StreamEvent.content_delta(content)
                        
                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            yield StreamEvent.message_delta(
                                stop_reason=finish_reason,
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
