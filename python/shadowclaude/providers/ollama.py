"""
Ollama Local LLM Provider 实现
"""

import json
import time
from typing import Dict, List, Optional, Any, Iterator, AsyncIterator
import httpx

from .base import (
    LLMProvider, LLMRequest, LLMResponse, StreamEvent, StreamEventType,
    TokenUsage, ServiceUnavailableError, ProviderError
)


class OllamaProvider(LLMProvider):
    """Ollama 本地模型 Provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.base_url.rstrip("/")
        self._client = None
        self._async_client = None
        self._available_models: List[str] = []
        
    @property
    def name(self) -> str:
        return "ollama"
    
    @property
    def supported_models(self) -> List[str]:
        """动态获取可用模型列表"""
        if not self._available_models:
            self._refresh_models()
        return self._available_models or [
            "llama3.2",
            "llama3.2:1b",
            "codellama",
            "mistral",
            "mixtral",
            "qwen2.5",
            "deepseek-coder",
            "phi4",
            "gemma2",
        ]
    
    def _get_client(self):
        """获取同步 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=httpx.Timeout(300.0, connect=10.0),  # 本地模型可能需要更长时间
            )
        return self._client
    
    def _get_async_client(self):
        """获取异步 HTTP 客户端"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=httpx.Timeout(300.0, connect=10.0),
            )
        return self._async_client
    
    def _refresh_models(self):
        """刷新可用模型列表"""
        try:
            response = self._get_client().get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                self._available_models = [
                    model.get("name", "").replace(":latest", "")
                    for model in data.get("models", [])
                ]
        except Exception:
            pass
    
    def _check_availability(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            response = self._get_client().get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    def _handle_error(self, response: httpx.Response):
        """处理错误响应"""
        try:
            error_data = response.json()
            error_message = error_data.get("error", "Unknown error")
        except:
            error_message = f"HTTP {response.status_code}: {response.text}"
        
        if response.status_code >= 500 or response.status_code == 0:
            raise ServiceUnavailableError(f"Ollama service unavailable: {error_message}")
        else:
            raise ProviderError(f"Ollama error ({response.status_code}): {error_message}")
    
    def _build_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """构建请求体"""
        # 合并 messages 为单个 prompt（Ollama 格式）
        prompt_parts = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            else:
                prompt_parts.append(f"User: {content}")
        
        prompt = "\n\n".join(prompt_parts)
        
        body = {
            "model": request.model,
            "prompt": prompt,
            "stream": request.stream,
        }
        
        # 构建 options
        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.top_k is not None:
            options["top_k"] = request.top_k
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if request.stop_sequences:
            options["stop"] = request.stop_sequences
            
        if options:
            body["options"] = options
        
        return body
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        """非流式完成请求"""
        start_time = time.time()
        
        def _do_complete():
            body = self._build_request_body(request)
            body["stream"] = False
            
            response = self._get_client().post("/api/generate", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            content = data.get("response", "")
            
            # Ollama 不直接提供 token 统计，需要估算
            prompt_eval_count = data.get("prompt_eval_count", 0)
            eval_count = data.get("eval_count", 0)
            
            # 如果没有返回，进行估算
            if prompt_eval_count == 0:
                prompt_eval_count = self.estimate_tokens(body["prompt"])
            if eval_count == 0:
                eval_count = self.estimate_tokens(content)
            
            usage = TokenUsage(
                input_tokens=prompt_eval_count,
                output_tokens=eval_count,
                total_tokens=prompt_eval_count + eval_count,
            )
            
            self._update_usage(usage)
            
            return LLMResponse(
                content=content,
                model=request.model,
                usage=usage,
                stop_reason="stop" if data.get("done") else None,
                metadata={
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )
        
        return self._execute_with_retry(_do_complete)
    
    def stream_complete(self, request: LLMRequest) -> Iterator[StreamEvent]:
        """流式完成请求"""
        start_time = time.time()
        
        def _do_stream():
            body = self._build_request_body(request)
            
            yield StreamEvent.message_start("", request.model)
            
            with self._get_client().stream(
                "POST",
                "/api/generate",
                json=body,
            ) as response:
                if response.status_code != 200:
                    error_text = response.read().decode()
                    self._handle_error(httpx.Response(
                        status_code=response.status_code,
                        content=error_text.encode(),
                    ))
                
                full_response = []
                input_tokens = 0
                output_tokens = 0
                done = False
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    line = line.decode() if isinstance(line, bytes) else line
                    
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # 内容增量
                    content = data.get("response", "")
                    if content:
                        full_response.append(content)
                        yield StreamEvent.content_delta(content)
                    
                    # 更新 token 统计
                    if data.get("prompt_eval_count"):
                        input_tokens = data.get("prompt_eval_count")
                    if data.get("eval_count"):
                        output_tokens = data.get("eval_count")
                    
                    # 检查完成
                    if data.get("done"):
                        done = True
                        
                        # 如果没有返回 token 数，进行估算
                        if input_tokens == 0:
                            input_tokens = self.estimate_tokens(body["prompt"])
                        if output_tokens == 0:
                            output_tokens = self.estimate_tokens("".join(full_response))
                        
                        usage = TokenUsage(
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_tokens=input_tokens + output_tokens,
                        )
                        self._update_usage(usage)
                        
                        yield StreamEvent.message_delta(
                            stop_reason="stop",
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
            response = await client.post("/api/generate", json=body)
            
            if response.status_code != 200:
                self._handle_error(response)
            
            data = response.json()
            
            content = data.get("response", "")
            
            prompt_eval_count = data.get("prompt_eval_count", 0)
            eval_count = data.get("eval_count", 0)
            
            if prompt_eval_count == 0:
                prompt_eval_count = self.estimate_tokens(body["prompt"])
            if eval_count == 0:
                eval_count = self.estimate_tokens(content)
            
            usage = TokenUsage(
                input_tokens=prompt_eval_count,
                output_tokens=eval_count,
                total_tokens=prompt_eval_count + eval_count,
            )
            
            self._update_usage(usage)
            
            return LLMResponse(
                content=content,
                model=request.model,
                usage=usage,
                stop_reason="stop" if data.get("done") else None,
                duration_ms=int((time.time() - start_time) * 1000),
            )
        
        return await self._aexecute_with_retry(_do_complete)
    
    async def astream_complete(self, request: LLMRequest) -> AsyncIterator[StreamEvent]:
        """异步流式完成请求"""
        start_time = time.time()
        
        async def _do_stream():
            body = self._build_request_body(request)
            
            yield StreamEvent.message_start("", request.model)
            
            client = self._get_async_client()
            
            async with client.stream(
                "POST",
                "/api/generate",
                json=body,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    self._handle_error(httpx.Response(
                        status_code=response.status_code,
                        content=error_text,
                    ))
                
                full_response = []
                input_tokens = 0
                output_tokens = 0
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    content = data.get("response", "")
                    if content:
                        full_response.append(content)
                        yield StreamEvent.content_delta(content)
                    
                    if data.get("prompt_eval_count"):
                        input_tokens = data.get("prompt_eval_count")
                    if data.get("eval_count"):
                        output_tokens = data.get("eval_count")
                    
                    if data.get("done"):
                        if input_tokens == 0:
                            input_tokens = self.estimate_tokens(body["prompt"])
                        if output_tokens == 0:
                            output_tokens = self.estimate_tokens("".join(full_response))
                        
                        usage = TokenUsage(
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_tokens=input_tokens + output_tokens,
                        )
                        self._update_usage(usage)
                        
                        yield StreamEvent.message_delta(
                            stop_reason="stop",
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
        
        try:
            async for event in self._aexecute_with_retry(_do_stream):
                yield event
        except Exception as e:
            yield StreamEvent.error(str(e), type(e).__name__)
    
    def pull_model(self, model: str) -> Iterator[str]:
        """拉取模型"""
        def _do_pull():
            response = self._get_client().post(
                "/api/pull",
                json={"name": model},
                timeout=httpx.Timeout(600.0),
            )
            
            for line in response.iter_lines():
                if line:
                    line = line.decode() if isinstance(line, bytes) else line
                    try:
                        data = json.loads(line)
                        status = data.get("status", "")
                        progress = ""
                        if "completed" in data and "total" in data:
                            progress = f" ({data['completed']}/{data['total']})"
                        yield f"{status}{progress}"
                    except:
                        yield line
        
        yield from _do_pull()
    
    def list_models(self) -> List[Dict[str, Any]]:
        """列出本地可用模型"""
        try:
            response = self._get_client().get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "name": m.get("name", ""),
                        "size": m.get("size", 0),
                        "modified": m.get("modified_at", ""),
                    }
                    for m in data.get("models", [])
                ]
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to list models: {e}")
        return []
