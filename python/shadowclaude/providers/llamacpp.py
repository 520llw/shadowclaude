"""
llama.cpp Local LLM Provider 实现
通过 llama.cpp 的 HTTP 服务器 API
"""

import json
import time
from typing import Dict, List, Optional, Any, Iterator, AsyncIterator
import httpx

from .base import (
    LLMProvider, LLMRequest, LLMResponse, StreamEvent, StreamEventType,
    TokenUsage, ServiceUnavailableError, ProviderError
)


class LlamaCppProvider(LLMProvider):
    """llama.cpp HTTP Server Provider"""
    
    # 默认使用本地 llama.cpp HTTP 服务器的地址
    DEFAULT_BASE_URL = "http://localhost:8080"
    
    def __init__(self, config):
        super().__init__(config)
        self.model_path = config.model_path
        self.n_ctx = config.n_ctx
        self.n_gpu_layers = config.n_gpu_layers
        self.n_batch = config.n_batch
        self.n_threads = config.n_threads
        self.base_url = getattr(config, 'base_url', self.DEFAULT_BASE_URL).rstrip("/")
        
        self._client = None
        self._async_client = None
        self._server_started = False
        
    @property
    def name(self) -> str:
        return "llamacpp"
    
    @property
    def supported_models(self) -> List[str]:
        # llama.cpp 支持任何 GGUF 格式的模型
        return ["local", "gguf", "llama", "mistral", "phi", "qwen", "deepseek"]
    
    def _get_client(self):
        """获取同步 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=httpx.Timeout(600.0, connect=10.0),
            )
        return self._client
    
    def _get_async_client(self):
        """获取异步 HTTP 客户端"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=httpx.Timeout(600.0, connect=10.0),
            )
        return self._async_client
    
    def _check_availability(self) -> bool:
        """检查 llama.cpp 服务是否可用"""
        try:
            response = self._get_client().get("/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            # 老版本 llama.cpp 可能没有 /health 端点
            response = self._get_client().get("/")
            return response.status_code == 200
        except Exception:
            return False
    
    def _handle_error(self, response: httpx.Response):
        """处理错误响应"""
        try:
            error_data = response.json()
            error_message = error_data.get("error", "Unknown error")
            if isinstance(error_message, dict):
                error_message = error_message.get("message", str(error_message))
        except:
            error_message = f"HTTP {response.status_code}: {response.text}"
        
        if response.status_code >= 500 or response.status_code in [0, 503]:
            raise ServiceUnavailableError(f"llama.cpp service unavailable: {error_message}")
        elif response.status_code == 404:
            raise ServiceUnavailableError(f"llama.cpp endpoint not found: {error_message}")
        else:
            raise ProviderError(f"llama.cpp error ({response.status_code}): {error_message}")
    
    def _build_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """构建 llama.cpp completion 请求体"""
        # llama.cpp 使用 /completion 端点，支持 prompt 格式
        # 需要将 messages 转换为 prompt
        prompt_parts = []
        
        if request.system:
            prompt_parts.append(f"System: {request.system}")
        
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            else:
                prompt_parts.append(content)
        
        prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        
        body = {
            "prompt": prompt,
            "stream": request.stream,
            "n_predict": request.max_tokens or -1,
            "temperature": request.temperature if request.temperature is not None else 0.7,
            "top_p": request.top_p if request.top_p is not None else 0.9,
            "top_k": request.top_k if request.top_k is not None else 40,
            "stop": request.stop_sequences or ["User:", "System:"],
        }
        
        return body
    
    def _build_chat_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """构建 llama.cpp chat completion 请求体（如果支持）"""
        # llama.cpp server 也支持 OpenAI 兼容的 /v1/chat/completions
        messages = []
        
        if request.system:
            messages.append({"role": "system", "content": request.system})
        
        for msg in request.messages:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })
        
        body = {
            "model": request.model,
            "messages": messages,
            "stream": request.stream,
            "max_tokens": request.max_tokens or -1,
            "temperature": request.temperature if request.temperature is not None else 0.7,
            "top_p": request.top_p if request.top_p is not None else 0.9,
            "top_k": request.top_k if request.top_k is not None else 40,
            "stop": request.stop_sequences or [],
        }
        
        return body
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        """非流式完成请求"""
        start_time = time.time()
        
        def _do_complete():
            # 优先尝试 OpenAI 兼容的 chat completions API
            body = self._build_chat_request_body(request)
            body["stream"] = False
            
            response = self._get_client().post("/v1/chat/completions", json=body)
            
            if response.status_code == 404:
                # 回退到原生 completion API
                body = self._build_request_body(request)
                body["stream"] = False
                response = self._get_client().post("/completion", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            # 处理 chat completions 格式
            if "choices" in data:
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                stop_reason = choice.get("finish_reason", "stop")
                
                usage_data = data.get("usage", {})
                usage = TokenUsage(
                    input_tokens=usage_data.get("prompt_tokens", 0),
                    output_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                )
            else:
                # 处理原生 completion 格式
                content = data.get("content", "")
                stop_reason = "stop" if data.get("stop") else None
                
                # 估算 token
                prompt_tokens = self.estimate_tokens(body.get("prompt", ""))
                completion_tokens = self.estimate_tokens(content)
                usage = TokenUsage(
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                )
            
            self._update_usage(usage)
            
            return LLMResponse(
                content=content,
                model=request.model,
                usage=usage,
                stop_reason=stop_reason,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        
        return self._execute_with_retry(_do_complete)
    
    def stream_complete(self, request: LLMRequest) -> Iterator[StreamEvent]:
        """流式完成请求"""
        start_time = time.time()
        
        def _do_stream():
            body = self._build_chat_request_body(request)
            
            yield StreamEvent.message_start("", request.model)
            
            response = self._get_client().post(
                "/v1/chat/completions",
                json=body,
            )
            
            use_chat_api = response.status_code != 404
            
            if not use_chat_api:
                body = self._build_request_body(request)
                response = self._get_client().post(
                    "/completion",
                    json=body,
                )
            
            if response.status_code != 200:
                error_text = response.read().decode()
                self._handle_error(httpx.Response(
                    status_code=response.status_code,
                    content=error_text.encode(),
                ))
            
            full_content = []
            input_tokens = 0
            output_tokens = 0
            
            if use_chat_api:
                # 流式 chat completions 格式
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
                        
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            full_content.append(content)
                            yield StreamEvent.content_delta(content)
                        
                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            if input_tokens == 0:
                                input_tokens = self.estimate_tokens(body.get("prompt", ""))
                            if output_tokens == 0:
                                output_tokens = self.estimate_tokens("".join(full_content))
                            
                            usage = TokenUsage(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=input_tokens + output_tokens,
                            )
                            self._update_usage(usage)
                            
                            yield StreamEvent.message_delta(
                                stop_reason=finish_reason,
                                usage={
                                    "input_tokens": input_tokens,
                                    "output_tokens": output_tokens,
                                }
                            )
                            
                            yield StreamEvent.message_stop({
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                            })
            else:
                # 原生 completion 流式格式
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    line = line.decode() if isinstance(line, bytes) else line
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        
                        content = data.get("content", "")
                        
                        if content:
                            full_content.append(content)
                            yield StreamEvent.content_delta(content)
                        
                        if data.get("stop"):
                            if input_tokens == 0:
                                input_tokens = self.estimate_tokens(body.get("prompt", ""))
                            if output_tokens == 0:
                                output_tokens = self.estimate_tokens("".join(full_content))
                            
                            usage = TokenUsage(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=input_tokens + output_tokens,
                            )
                            self._update_usage(usage)
                            
                            yield StreamEvent.message_delta(stop_reason="stop")
                            yield StreamEvent.message_stop({
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                            })
        
        try:
            yield from self._execute_with_retry(_do_stream)
        except Exception as e:
            yield StreamEvent.error(str(e), type(e).__name__)
    
    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        """异步非流式完成请求"""
        start_time = time.time()
        
        async def _do_complete():
            body = self._build_chat_request_body(request)
            body["stream"] = False
            
            client = self._get_async_client()
            response = await client.post("/v1/chat/completions", json=body)
            
            if response.status_code == 404:
                body = self._build_request_body(request)
                body["stream"] = False
                response = await client.post("/completion", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            if "choices" in data:
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                stop_reason = choice.get("finish_reason", "stop")
                
                usage_data = data.get("usage", {})
                usage = TokenUsage(
                    input_tokens=usage_data.get("prompt_tokens", 0),
                    output_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                )
            else:
                content = data.get("content", "")
                stop_reason = "stop" if data.get("stop") else None
                
                prompt_tokens = self.estimate_tokens(body.get("prompt", ""))
                completion_tokens = self.estimate_tokens(content)
                usage = TokenUsage(
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                )
            
            self._update_usage(usage)
            
            return LLMResponse(
                content=content,
                model=request.model,
                usage=usage,
                stop_reason=stop_reason,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        
        return await self._aexecute_with_retry(_do_complete)
    
    async def astream_complete(self, request: LLMRequest) -> AsyncIterator[StreamEvent]:
        """异步流式完成请求"""
        start_time = time.time()
        
        async def _do_stream():
            body = self._build_chat_request_body(request)
            
            yield StreamEvent.message_start("", request.model)
            
            client = self._get_async_client()
            
            response = await client.post("/v1/chat/completions", json=body)
            use_chat_api = response.status_code != 404
            
            if not use_chat_api:
                body = self._build_request_body(request)
                response = await client.post("/completion", json=body)
            
            if response.status_code != 200:
                error_text = await response.aread()
                self._handle_error(httpx.Response(
                    status_code=response.status_code,
                    content=error_text,
                ))
            
            full_content = []
            input_tokens = 0
            output_tokens = 0
            
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
                    
                    if use_chat_api:
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            full_content.append(content)
                            yield StreamEvent.content_delta(content)
                        
                        if choice.get("finish_reason"):
                            if input_tokens == 0:
                                input_tokens = self.estimate_tokens(body.get("prompt", ""))
                            if output_tokens == 0:
                                output_tokens = self.estimate_tokens("".join(full_content))
                            
                            usage = TokenUsage(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=input_tokens + output_tokens,
                            )
                            self._update_usage(usage)
                            
                            yield StreamEvent.message_delta(stop_reason=choice.get("finish_reason"))
                            yield StreamEvent.message_stop({
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                            })
                    else:
                        content = data.get("content", "")
                        
                        if content:
                            full_content.append(content)
                            yield StreamEvent.content_delta(content)
                        
                        if data.get("stop"):
                            if input_tokens == 0:
                                input_tokens = self.estimate_tokens(body.get("prompt", ""))
                            if output_tokens == 0:
                                output_tokens = self.estimate_tokens("".join(full_content))
                            
                            usage = TokenUsage(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=input_tokens + output_tokens,
                            )
                            self._update_usage(usage)
                            
                            yield StreamEvent.message_delta(stop_reason="stop")
                            yield StreamEvent.message_stop({
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                            })
        
        try:
            async for event in self._aexecute_with_retry(_do_stream):
                yield event
        except Exception as e:
            yield StreamEvent.error(str(e), type(e).__name__)
    
    def get_server_props(self) -> Dict[str, Any]:
        """获取服务器属性"""
        try:
            response = self._get_client().get("/props")
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            response = self._get_client().get("/health")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {"status": "unknown"}
