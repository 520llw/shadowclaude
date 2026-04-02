# ShadowClaude REST API 规范

## 概述

ShadowClaude REST API 提供 HTTP 接口与 ShadowClaude 服务进行交互。

- **Base URL**: `http://localhost:8080/api/v1`
- **Content-Type**: `application/json`
- **认证**: Bearer Token

## 认证

所有 API 请求都需要在 Header 中携带认证令牌：

```http
Authorization: Bearer <your_api_token>
```

## 端点

### 查询

#### POST /query

发送查询请求。

**请求体:**

```json
{
  "message": "Hello, ShadowClaude!",
  "context": {
    "session_id": "session_123",
    "workspace": "/path/to/workspace"
  },
  "stream": false
}
```

**响应:**

```json
{
  "id": "resp_abc123",
  "content": "Hello! How can I help you today?",
  "tool_calls": [],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  },
  "created_at": "2026-04-02T10:30:00Z"
}
```

#### POST /query/stream

流式查询。

**请求体:** 同 `/query`

**响应:** SSE 流

```
event: message
data: {"chunk": "Hello", "done": false}

event: message
data: {"chunk": "!", "done": false}

event: message
data: {"chunk": "", "done": true, "usage": {...}}
```

### 会话管理

#### GET /sessions

获取会话列表。

**查询参数:**

- `limit`: 返回数量 (默认 20, 最大 100)
- `offset`: 偏移量

**响应:**

```json
{
  "sessions": [
    {
      "id": "session_123",
      "title": "Python Project Help",
      "message_count": 15,
      "created_at": "2026-04-02T10:00:00Z",
      "updated_at": "2026-04-02T10:30:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### GET /sessions/{id}

获取会话详情。

**响应:**

```json
{
  "id": "session_123",
  "title": "Python Project Help",
  "messages": [
    {
      "role": "user",
      "content": "Hello!",
      "timestamp": "2026-04-02T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Hello! How can I help?",
      "timestamp": "2026-04-02T10:00:01Z"
    }
  ],
  "metadata": {
    "workspace": "/path/to/project"
  }
}
```

#### POST /sessions

创建新会话。

**请求体:**

```json
{
  "title": "New Conversation",
  "metadata": {
    "workspace": "/path/to/workspace"
  }
}
```

**响应:**

```json
{
  "id": "session_456",
  "title": "New Conversation",
  "created_at": "2026-04-02T11:00:00Z"
}
```

#### DELETE /sessions/{id}

删除会话。

**响应:**

```json
{
  "success": true
}
```

### 记忆管理

#### POST /memory/store

存储记忆。

**请求体:**

```json
{
  "content": "Python is a programming language",
  "type": "semantic",
  "metadata": {
    "topic": "programming",
    "language": "python"
  }
}
```

**响应:**

```json
{
  "id": "mem_abc123",
  "stored_at": "2026-04-02T10:30:00Z"
}
```

#### POST /memory/retrieve

检索记忆。

**请求体:**

```json
{
  "query": "programming languages",
  "limit": 10,
  "types": ["semantic", "episodic"],
  "filters": {
    "language": "python"
  }
}
```

**响应:**

```json
{
  "memories": [
    {
      "id": "mem_abc123",
      "content": "Python is a programming language",
      "type": "semantic",
      "score": 0.95,
      "metadata": {
        "topic": "programming",
        "language": "python"
      }
    }
  ],
  "total": 1
}
```

#### DELETE /memory/{id}

删除记忆。

**响应:**

```json
{
  "success": true
}
```

### 工具执行

#### POST /tools/execute

执行工具。

**请求体:**

```json
{
  "tool": "read_file",
  "arguments": {
    "path": "/path/to/file.txt"
  },
  "async": false
}
```

**响应:**

```json
{
  "success": true,
  "output": "file content here",
  "execution_time_ms": 50
}
```

#### GET /tools

获取可用工具列表。

**响应:**

```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read a file from disk",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "File path"
          }
        },
        "required": ["path"]
      }
    }
  ]
}
```

### Agent 管理

#### GET /agents

获取 Agent 列表。

**响应:**

```json
{
  "agents": [
    {
      "id": "agent_001",
      "name": "CodeAgent",
      "type": "code",
      "status": "idle",
      "capabilities": ["code_analysis", "refactoring"]
    }
  ]
}
```

#### POST /agents/{id}/task

分配任务给 Agent。

**请求体:**

```json
{
  "description": "Refactor this function",
  "context": {
    "file": "/path/to/file.py",
    "function": "my_function"
  },
  "priority": "normal"
}
```

**响应:**

```json
{
  "task_id": "task_123",
  "status": "queued",
  "estimated_time": "30s"
}
```

#### GET /agents/{id}/status

获取 Agent 状态。

**响应:**

```json
{
  "id": "agent_001",
  "status": "working",
  "current_task": "task_123",
  "queue_size": 2,
  "uptime_seconds": 3600
}
```

### BUDDY 系统

#### GET /buddy/status

获取 BUDDY 状态。

**响应:**

```json
{
  "name": "Claudia",
  "emotion": "happy",
  "emotion_intensity": 0.8,
  "relationship_level": 5,
  "last_interaction": "2026-04-02T10:00:00Z"
}
```

#### POST /buddy/interact

与 BUDDY 交互。

**请求体:**

```json
{
  "message": "Hello, how are you?"
}
```

**响应:**

```json
{
  "response": "I'm doing great! Thanks for asking. ❤️",
  "emotion": "happy",
  "action": "wave"
}
```

### 系统管理

#### GET /health

健康检查。

**响应:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "components": {
    "llm": "connected",
    "memory": "connected",
    "tools": "ready"
  }
}
```

#### GET /metrics

获取指标数据。

**响应:**

```json
{
  "queries_total": 1000,
  "queries_per_minute": 10,
  "average_latency_ms": 500,
  "tool_executions": {
    "read_file": 500,
    "write_file": 100
  },
  "memory_usage": {
    "semantic": 1000,
    "episodic": 500,
    "working": 50
  }
}
```

## 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "The 'path' argument is required",
    "details": {
      "field": "arguments.path"
    }
  }
}
```

### 错误代码

| 代码 | HTTP 状态 | 说明 |
|------|-----------|------|
| `UNAUTHORIZED` | 401 | 认证失败 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `INVALID_ARGUMENT` | 400 | 参数错误 |
| `RATE_LIMITED` | 429 | 请求过于频繁 |
| `INTERNAL_ERROR` | 500 | 内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## OpenAPI 规范

完整的 OpenAPI 3.0 规范：

```yaml
openapi: 3.0.0
info:
  title: ShadowClaude API
  version: 1.0.0
  description: ShadowClaude REST API 规范

servers:
  - url: http://localhost:8080/api/v1
    description: Local development server

security:
  - bearerAuth: []

paths:
  /query:
    post:
      summary: Send a query
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QueryRequest'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryResponse'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer

  schemas:
    QueryRequest:
      type: object
      properties:
        message:
          type: string
        context:
          type: object
        stream:
          type: boolean
      required:
        - message

    QueryResponse:
      type: object
      properties:
        id:
          type: string
        content:
          type: string
        tool_calls:
          type: array
          items:
            $ref: '#/components/schemas/ToolCall'
        usage:
          $ref: '#/components/schemas/Usage'

    ToolCall:
      type: object
      properties:
        name:
          type: string
        arguments:
          type: object

    Usage:
      type: object
      properties:
        prompt_tokens:
          type: integer
        completion_tokens:
          type: integer
        total_tokens:
          type: integer
```

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
