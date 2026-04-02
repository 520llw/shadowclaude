# ShadowClaude API 使用指南

## REST API 详细说明

### 认证

所有 API 请求都需要认证：

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8080/api/v1/query
```

### 端点详解

#### 查询端点

**POST /api/v1/query**

请求体：
```json
{
  "message": "Hello",
  "context": {
    "session_id": "abc123"
  },
  "stream": false
}
```

响应：
```json
{
  "id": "resp_123",
  "content": "Hi there!",
  "tool_calls": [],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

#### 流式查询

**POST /api/v1/query/stream**

使用 SSE (Server-Sent Events)：

```javascript
const eventSource = new EventSource('/api/v1/query/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.chunk);
};
```

#### 会话管理

**GET /api/v1/sessions**

获取所有会话：

```json
{
  "sessions": [
    {
      "id": "session_1",
      "title": "Python Project",
      "created_at": "2026-04-02T10:00:00Z"
    }
  ]
}
```

**POST /api/v1/sessions**

创建新会话：

```json
{
  "title": "New Conversation"
}
```

**DELETE /api/v1/sessions/{id}**

删除会话。

#### 记忆管理

**POST /api/v1/memory/store**

存储记忆：

```json
{
  "content": "Python was created in 1991",
  "type": "semantic",
  "metadata": {
    "topic": "python",
    "confidence": 0.95
  }
}
```

**POST /api/v1/memory/retrieve**

检索记忆：

```json
{
  "query": "When was Python created?",
  "limit": 5
}
```

#### 工具执行

**POST /api/v1/tools/execute**

执行工具：

```json
{
  "tool": "read_file",
  "arguments": {
    "path": "/path/to/file.txt"
  }
}
```

### 错误处理

错误响应格式：

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "Missing required field: path",
    "details": {
      "field": "arguments.path"
    }
  }
}
```

错误代码列表：
- `UNAUTHORIZED`: 认证失败
- `FORBIDDEN`: 权限不足
- `NOT_FOUND`: 资源不存在
- `INVALID_ARGUMENT`: 参数错误
- `RATE_LIMITED`: 请求过于频繁
- `INTERNAL_ERROR`: 内部错误

## Python SDK 详细使用

### 客户端初始化

```python
import shadowclaude as sc

# 基本初始化
client = sc.Client()

# 带配置初始化
client = sc.Client(
    config=sc.Config.from_file("config.yaml"),
    llm_provider="anthropic"
)

# 自定义 LLM 客户端
from shadowclaude.llm import AnthropicClient

llm = AnthropicClient(
    api_key="your_key",
    model="claude-3-opus-20240229"
)
client = sc.Client(llm_client=llm)
```

### 查询处理

```python
# 简单查询
response = client.query("Hello!")
print(response.content)

# 带上下文查询
response = client.query(
    "What about it?",
    context={"topic": "Python"}
)

# 流式查询
async for chunk in client.query_stream("Tell me a story"):
    print(chunk.content, end="")

# 批量查询
queries = ["Q1", "Q2", "Q3"]
responses = await client.query_batch(queries)
```

### 工具使用

```python
# 执行内置工具
result = client.execute_tool("read_file", {
    "path": "README.md"
})

# 检查工具可用性
if client.has_tool("custom_tool"):
    result = client.execute_tool("custom_tool", args)

# 获取工具列表
tools = client.list_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")
```

### 记忆操作

```python
memory = client.get_memory()

# 存储
memory_id = memory.store(
    "Important fact",
    memory_type=sc.MemoryType.SEMANTIC,
    metadata={"topic": "important"}
)

# 检索
results = memory.retrieve(
    "query",
    limit=10,
    memory_types=[sc.MemoryType.SEMANTIC]
)

# 更新
memory.update(memory_id, new_content="Updated")

# 删除
memory.delete(memory_id)
```

### Agent 使用

```python
coordinator = client.get_coordinator()

# 注册 Agent
coordinator.register_agent(
    "code_reviewer",
    CodeReviewAgent()
)

# 分配任务
task = sc.Task(
    agent_type="code_reviewer",
    data={"code": "..."}
)
result = coordinator.dispatch(task)

# 批量分配
tasks = [task1, task2, task3]
results = coordinator.dispatch_batch(tasks)
```

### BUDDY 交互

```python
buddy = client.get_buddy()

# 简单交互
response = buddy.interact("Hello!")

# 获取状态
status = buddy.get_status()
print(f"Emotion: {status.emotion}")

# 设置情绪
buddy.set_emotion("happy")
```

## WebSocket 实时通信

### 连接建立

```python
import websockets
import json

async def connect():
    uri = "ws://localhost:8080/ws"
    async with websockets.connect(uri) as ws:
        # Authenticate
        await ws.send(json.dumps({
            "type": "auth",
            "token": "your_token"
        }))
        
        # Handle messages
        async for message in ws:
            data = json.loads(message)
            handle_message(data)
```

### 消息类型

#### 客户端消息

```python
# Query
{
    "type": "query",
    "id": "req_001",
    "payload": {
        "message": "Hello",
        "stream": True
    }
}

# Tool call
{
    "type": "tool_call",
    "id": "req_002",
    "payload": {
        "tool": "read_file",
        "arguments": {...}
    }
}

# Ping (keep alive)
{
    "type": "ping",
    "timestamp": 1234567890
}
```

#### 服务端消息

```python
# Response chunk
{
    "type": "query_chunk",
    "id": "req_001",
    "payload": {
        "content": "Hello",
        "done": False
    }
}

# Tool result
{
    "type": "tool_result",
    "id": "req_002",
    "payload": {
        "success": True,
        "output": "..."
    }
}

# Error
{
    "type": "error",
    "id": "req_001",
    "payload": {
        "code": "ERROR_CODE",
        "message": "Error description"
    }
}
```

## 高级用法

### 自定义中间件

```python
class LoggingMiddleware(sc.Middleware):
    async def process(self, query, next):
        print(f"Processing: {query}")
        result = await next(query)
        print(f"Completed: {result}")
        return result

client.add_middleware(LoggingMiddleware())
```

### 事件监听

```python
@client.on("query_start")
def on_query_start(event):
    print(f"Query started: {event.query}")

@client.on("query_complete")
def on_query_complete(event):
    print(f"Query completed in {event.duration}ms")

@client.on("tool_call")
def on_tool_call(event):
    print(f"Tool called: {event.tool_name}")
```

### 错误处理

```python
from shadowclaude.exceptions import (
    ToolError,
    LLMError,
    PermissionError
)

try:
    result = client.query("...")
except ToolError as e:
    print(f"Tool failed: {e.tool_name}")
except LLMError as e:
    print(f"LLM error: {e.message}")
except PermissionError as e:
    print(f"Permission denied: {e.action}")
```

### 性能监控

```python
# Enable profiling
client.enable_profiling()

# Get metrics
metrics = client.get_metrics()
print(f"Average latency: {metrics.avg_latency}ms")
print(f"Cache hit rate: {metrics.cache_hit_rate}")

# Export metrics
client.export_metrics("metrics.json")
```

---

*API 指南版本: 1.0.0 | 最后更新: 2026-04-02*
