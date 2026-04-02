"""
Mock LLM Client - 模拟 LLM 提供商
"""

from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass, field
from enum import Enum
import json
import time
import re


class LLMResponseType(Enum):
    """LLM 响应类型"""
    COMPLETION = "completion"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    STREAM_CHUNK = "stream_chunk"


@dataclass
class MockLLMResponse:
    """Mock LLM 响应"""
    content: str
    response_type: LLMResponseType = LLMResponseType.COMPLETION
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: int = 100
    error: Optional[str] = None


@dataclass
class LLMCallRecord:
    """LLM 调用记录"""
    prompt: str
    system_prompt: Optional[str]
    tools: List[str]
    timestamp: float
    response: MockLLMResponse


class MockLLMClient:
    """
    Mock LLM 客户端
    用于测试时不调用真实 API
    """
    
    def __init__(self, model: str = "claude-sonnet-4-mock"):
        self.model = model
        self.call_history: List[LLMCallRecord] = []
        self._responses: List[MockLLMResponse] = []
        self._response_index = 0
        self._default_responses = self._init_default_responses()
        self.response_delay_ms = 10
        
        # 统计
        self.total_calls = 0
        self.total_tokens_in = 0
        self.total_tokens_out = 0
    
    def _init_default_responses(self) -> Dict[str, MockLLMResponse]:
        """初始化默认响应模板"""
        return {
            "greeting": MockLLMResponse(
                content="Hello! I'm ShadowClaude, ready to help you.",
                usage={"input_tokens": 50, "output_tokens": 20}
            ),
            "code_review": MockLLMResponse(
                content="The code looks good. Here are my suggestions...",
                usage={"input_tokens": 200, "output_tokens": 150}
            ),
            "tool_use": MockLLMResponse(
                content="I'll help you with that by using the appropriate tools.",
                response_type=LLMResponseType.TOOL_CALL,
                tool_calls=[{
                    "name": "read_file",
                    "input": {"path": "test.py"}
                }],
                usage={"input_tokens": 100, "output_tokens": 50}
            ),
            "error": MockLLMResponse(
                content="",
                response_type=LLMResponseType.ERROR,
                error="Rate limit exceeded",
                usage={"input_tokens": 0, "output_tokens": 0}
            )
        }
    
    def queue_response(self, response: MockLLMResponse):
        """队列一个响应"""
        self._responses.append(response)
    
    def queue_responses(self, responses: List[MockLLMResponse]):
        """队列多个响应"""
        self._responses.extend(responses)
    
    def clear_queue(self):
        """清空响应队列"""
        self._responses.clear()
        self._response_index = 0
    
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0
    ) -> MockLLMResponse:
        """模拟完成请求"""
        # 模拟延迟
        if self.response_delay_ms > 0:
            time.sleep(self.response_delay_ms / 1000)
        
        # 获取响应
        if self._response_index < len(self._responses):
            response = self._responses[self._response_index]
            self._response_index += 1
        else:
            response = self._generate_response_from_prompt(prompt, tools)
        
        # 记录调用
        record = LLMCallRecord(
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tools or [],
            timestamp=time.time(),
            response=response
        )
        self.call_history.append(record)
        self.total_calls += 1
        self.total_tokens_in += response.usage.get("input_tokens", 0)
        self.total_tokens_out += response.usage.get("output_tokens", 0)
        
        return response
    
    def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None
    ) -> Iterator[MockLLMResponse]:
        """模拟流式完成"""
        response = self.complete(prompt, system_prompt, tools)
        
        # 将内容分成多个 chunk
        words = response.content.split()
        for i, word in enumerate(words):
            chunk = MockLLMResponse(
                content=word + (" " if i < len(words) - 1 else ""),
                response_type=LLMResponseType.STREAM_CHUNK,
                usage={"input_tokens": 0, "output_tokens": 1} if i == 0 else {"input_tokens": 0, "output_tokens": 0}
            )
            yield chunk
        
        # 最后发送完整响应
        yield MockLLMResponse(
            content="",
            response_type=LLMResponseType.COMPLETION,
            tool_calls=response.tool_calls,
            usage={"input_tokens": 0, "output_tokens": 0}
        )
    
    def _generate_response_from_prompt(
        self,
        prompt: str,
        tools: Optional[List[str]]
    ) -> MockLLMResponse:
        """根据 prompt 生成响应"""
        prompt_lower = prompt.lower()
        
        # 基于关键词匹配响应
        if "hello" in prompt_lower or "hi" in prompt_lower:
            return self._default_responses["greeting"]
        
        if "review" in prompt_lower or "check" in prompt_lower:
            return self._default_responses["code_review"]
        
        if tools and len(tools) > 0:
            # 如果提供了工具，返回工具调用响应
            return self._default_responses["tool_use"]
        
        # 默认响应
        return MockLLMResponse(
            content=f"Processed: {prompt[:50]}...",
            usage={"input_tokens": len(prompt.split()), "output_tokens": 20}
        )
    
    def get_call_history(self) -> List[LLMCallRecord]:
        """获取调用历史"""
        return self.call_history.copy()
    
    def get_last_call(self) -> Optional[LLMCallRecord]:
        """获取最后一次调用"""
        return self.call_history[-1] if self.call_history else None
    
    def assert_called_with(self, expected_prompt_contains: str):
        """断言最后一次调用包含特定文本"""
        last_call = self.get_last_call()
        assert last_call is not None, "No calls were made"
        assert expected_prompt_contains in last_call.prompt, \
            f"Expected prompt to contain '{expected_prompt_contains}', got: {last_call.prompt}"
    
    def assert_tool_called(self, tool_name: str):
        """断言调用了特定工具"""
        last_call = self.get_last_call()
        assert last_call is not None, "No calls were made"
        response = last_call.response
        tool_names = [tc.get("name") for tc in response.tool_calls]
        assert tool_name in tool_names, \
            f"Expected tool '{tool_name}' to be called, got: {tool_names}"
    
    def reset(self):
        """重置状态"""
        self.call_history.clear()
        self._responses.clear()
        self._response_index = 0
        self.total_calls = 0
        self.total_tokens_in = 0
        self.total_tokens_out = 0


class MockLLMProvider:
    """
    Mock LLM 提供商工厂
    支持多个模型的 mock
    """
    
    SUPPORTED_MODELS = [
        "claude-sonnet-4",
        "claude-opus-4",
        "claude-haiku-4",
        "gpt-4",
        "gpt-3.5-turbo"
    ]
    
    def __init__(self):
        self._clients: Dict[str, MockLLMClient] = {}
    
    def get_client(self, model: str) -> MockLLMClient:
        """获取指定模型的客户端"""
        if model not in self._clients:
            self._clients[model] = MockLLMClient(model=model)
        return self._clients[model]
    
    def reset_all(self):
        """重置所有客户端"""
        for client in self._clients.values():
            client.reset()
