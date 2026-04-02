"""
Mock HTTP 客户端 - 模拟网络请求
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse
import json
import re
import time


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class HTTPRequest:
    """HTTP 请求"""
    method: HTTPMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    timeout: float = 30.0


@dataclass
class HTTPResponse:
    """HTTP 响应"""
    status_code: int
    body: str
    headers: Dict[str, str] = field(default_factory=dict)
    latency_ms: int = 100
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return 200 <= self.status_code < 300
    
    def json(self) -> Any:
        """解析 JSON"""
        return json.loads(self.body)


@dataclass
class RequestExpectation:
    """请求预期"""
    method: HTTPMethod
    url_pattern: str
    response: HTTPResponse
    call_count: int = 0
    max_calls: Optional[int] = None


class MockHTTPClient:
    """
    Mock HTTP 客户端
    用于测试网络请求而不实际发送
    """
    
    def __init__(self):
        self._expectations: List[RequestExpectation] = []
        self._request_history: List[HTTPRequest] = []
        self._response_map: Dict[str, HTTPResponse] = {}
        self.default_response = HTTPResponse(
            status_code=200,
            body="OK",
            headers={"Content-Type": "text/plain"}
        )
        self._latency_range = (10, 100)  # ms
        
        # 统计
        self.total_requests = 0
        self.failed_requests = 0
    
    def expect_request(
        self,
        method: HTTPMethod,
        url_pattern: str,
        response: HTTPResponse,
        max_calls: Optional[int] = None
    ):
        """
        设置请求预期
        
        Args:
            method: HTTP 方法
            url_pattern: URL 匹配模式（支持正则）
            response: 返回的响应
            max_calls: 最大匹配次数
        """
        expectation = RequestExpectation(
            method=method,
            url_pattern=url_pattern,
            response=response,
            max_calls=max_calls
        )
        self._expectations.append(expectation)
    
    def set_response(self, url: str, response: HTTPResponse):
        """为特定 URL 设置响应"""
        self._response_map[url] = response
    
    def _find_response(self, request: HTTPRequest) -> HTTPResponse:
        """查找匹配的响应"""
        # 1. 检查精确匹配
        if request.url in self._response_map:
            return self._response_map[request.url]
        
        # 2. 检查预期
        for exp in self._expectations:
            if exp.method == request.method and re.search(exp.url_pattern, request.url):
                if exp.max_calls is None or exp.call_count < exp.max_calls:
                    exp.call_count += 1
                    return exp.response
        
        # 3. 返回默认
        return self.default_response
    
    def _simulate_latency(self):
        """模拟网络延迟"""
        min_lat, max_lat = self._latency_range
        latency = (min_lat + max_lat) // 2
        time.sleep(latency / 1000)
    
    def request(
        self,
        method: HTTPMethod,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        timeout: float = 30.0
    ) -> HTTPResponse:
        """发送 HTTP 请求"""
        request = HTTPRequest(
            method=method,
            url=url,
            headers=headers or {},
            body=body,
            timeout=timeout
        )
        
        self._request_history.append(request)
        self.total_requests += 1
        
        self._simulate_latency()
        
        response = self._find_response(request)
        
        if not response.is_success:
            self.failed_requests += 1
        
        return response
    
    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> HTTPResponse:
        """GET 请求"""
        return self.request(HTTPMethod.GET, url, headers, None, timeout)
    
    def post(
        self,
        url: str,
        body: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> HTTPResponse:
        """POST 请求"""
        headers = headers or {}
        if body and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        return self.request(HTTPMethod.POST, url, headers, body, timeout)
    
    def put(
        self,
        url: str,
        body: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> HTTPResponse:
        """PUT 请求"""
        return self.request(HTTPMethod.PUT, url, headers, body, timeout)
    
    def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> HTTPResponse:
        """DELETE 请求"""
        return self.request(HTTPMethod.DELETE, url, headers, None, timeout)
    
    def get_request_history(self) -> List[HTTPRequest]:
        """获取请求历史"""
        return self._request_history.copy()
    
    def get_last_request(self) -> Optional[HTTPRequest]:
        """获取最后一个请求"""
        return self._request_history[-1] if self._request_history else None
    
    def assert_requested(self, method: HTTPMethod, url_pattern: str):
        """断言特定请求被发送"""
        for req in self._request_history:
            if req.method == method and re.search(url_pattern, req.url):
                return True
        
        raise AssertionError(
            f"Expected {method.value} request to URL matching '{url_pattern}' was not made"
        )
    
    def assert_request_count(self, expected_count: int):
        """断言请求次数"""
        actual = len(self._request_history)
        assert actual == expected_count, \
            f"Expected {expected_count} requests, got {actual}"
    
    def assert_all_expectations_met(self):
        """断言所有预期都被满足"""
        for exp in self._expectations:
            if exp.max_calls and exp.call_count < exp.max_calls:
                raise AssertionError(
                    f"Expected {exp.max_calls} calls to {exp.method.value} {exp.url_pattern}, "
                    f"got {exp.call_count}"
                )
    
    def reset(self):
        """重置状态"""
        self._expectations.clear()
        self._request_history.clear()
        self._response_map.clear()
        self.total_requests = 0
        self.failed_requests = 0
    
    def set_latency_range(self, min_ms: int, max_ms: int):
        """设置延迟范围"""
        self._latency_range = (min_ms, max_ms)


class MockWebSocket:
    """Mock WebSocket 连接"""
    
    def __init__(self, url: str):
        self.url = url
        self._connected = False
        self._messages: List[Dict] = []
        self._received: List[str] = []
        self._handlers: Dict[str, List[Callable]] = {}
    
    def connect(self):
        """连接"""
        self._connected = True
    
    def disconnect(self):
        """断开连接"""
        self._connected = False
    
    def send(self, message: str):
        """发送消息"""
        self._received.append(message)
    
    def receive(self) -> str:
        """接收消息"""
        if self._messages:
            return json.dumps(self._messages.pop(0))
        return ""
    
    def queue_message(self, message: Dict):
        """队列消息"""
        self._messages.append(message)
    
    @property
    def is_connected(self) -> bool:
        """是否连接"""
        return self._connected
    
    def reset(self):
        """重置"""
        self._connected = False
        self._messages.clear()
        self._received.clear()
        self._handlers.clear()
