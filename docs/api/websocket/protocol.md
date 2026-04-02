# ShadowClaude WebSocket 协议文档

## 概述

ShadowClaude WebSocket API 提供实时双向通信能力，支持流式响应和服务器推送。

- **Endpoint**: `ws://localhost:8080/ws`
- **Protocol**: JSON-RPC 2.0
- **心跳**: 每 30 秒

## 连接

### 建立连接

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
  console.log('Connected');
  
  // 发送认证
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_api_token'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### 认证

连接建立后必须立即发送认证消息：

```json
{
  "type": "auth",
  "token": "your_api_token"
}
```

**响应:**

```json
{
  "type": "auth_response",
  "success": true,
  "session_id": "session_abc123"
}
```

## 消息类型

### 客户端消息

#### query

发送查询请求。

```json
{
  "type": "query",
  "id": "req_001",
  "payload": {
    "message": "Hello, ShadowClaude!",
    "context": {
      "session_id": "session_123"
    },
    "stream": true
  }
}
```

#### tool_call

执行工具。

```json
{
  "type": "tool_call",
  "id": "req_002",
  "payload": {
    "tool": "read_file",
    "arguments": {
      "path": "/path/to/file.txt"
    }
  }
}
```

#### ping

心跳消息。

```json
{
  "type": "ping",
  "timestamp": 1712049600
}
```

### 服务器消息

#### query_response

查询响应（非流式）。

```json
{
  "type": "query_response",
  "id": "req_001",
  "payload": {
    "content": "Hello! How can I help you?",
    "tool_calls": [],
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 8
    },
    "done": true
  }
}
```

#### query_chunk

流式响应块。

```json
{
  "type": "query_chunk",
  "id": "req_001",
  "payload": {
    "content": "Hello",
    "index": 0,
    "done": false
  }
}
```

#### tool_result

工具执行结果。

```json
{
  "type": "tool_result",
  "id": "req_002",
  "payload": {
    "success": true,
    "output": "file content here",
    "execution_time_ms": 50
  }
}
```

#### pong

心跳响应。

```json
{
  "type": "pong",
  "timestamp": 1712049600
}
```

#### error

错误消息。

```json
{
  "type": "error",
  "id": "req_001",
  "payload": {
    "code": "INVALID_ARGUMENT",
    "message": "Missing required argument",
    "details": {
      "field": "message"
    }
  }
}
```

#### notification

服务器推送通知。

```json
{
  "type": "notification",
  "payload": {
    "level": "info",
    "message": "Task completed",
    "data": {
      "task_id": "task_123"
    }
  }
}
```

## 完整示例

### 流式查询

```javascript
class ShadowClaudeClient {
  constructor(url, token) {
    this.ws = new WebSocket(url);
    this.token = token;
    this.pending = new Map();
    
    this.ws.onopen = () => {
      this.authenticate();
    };
    
    this.ws.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data));
    };
  }
  
  authenticate() {
    this.send({
      type: 'auth',
      token: this.token
    });
  }
  
  send(message) {
    this.ws.send(JSON.stringify(message));
  }
  
  async query(message, stream = true) {
    const id = `req_${Date.now()}`;
    
    return new Promise((resolve, reject) => {
      const chunks = [];
      
      this.pending.set(id, {
        resolve: (result) => {
          if (stream) {
            resolve(chunks.join(''));
          } else {
            resolve(result);
          }
        },
        reject,
        onChunk: stream ? (chunk) => {
          chunks.push(chunk);
          console.log('Chunk:', chunk);
        } : null
      });
      
      this.send({
        type: 'query',
        id,
        payload: { message, stream }
      });
    });
  }
  
  handleMessage(message) {
    const { type, id, payload } = message;
    
    if (type === 'error') {
      const pending = this.pending.get(id);
      if (pending) {
        pending.reject(new Error(payload.message));
        this.pending.delete(id);
      }
      return;
    }
    
    if (type === 'query_chunk') {
      const pending = this.pending.get(id);
      if (pending && pending.onChunk) {
        pending.onChunk(payload.content);
      }
      return;
    }
    
    if (type === 'query_response' && payload.done) {
      const pending = this.pending.get(id);
      if (pending) {
        pending.resolve(payload);
        this.pending.delete(id);
      }
      return;
    }
  }
}

// 使用示例
const client = new ShadowClaudeClient(
  'ws://localhost:8080/ws',
  'your_api_token'
);

await client.query('Write a Python function');
```

### 实时通知

```javascript
// 监听任务完成通知
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'notification') {
    const { level, message: msg, data } = message.payload;
    
    switch (level) {
      case 'info':
        console.log('ℹ️', msg);
        break;
      case 'warning':
        console.warn('⚠️', msg);
        break;
      case 'error':
        console.error('❌', msg);
        break;
      case 'success':
        console.log('✅', msg);
        break;
    }
  }
};
```

## 事件订阅

### 订阅系统事件

```json
{
  "type": "subscribe",
  "id": "sub_001",
  "payload": {
    "events": [
      "task.completed",
      "file.changed",
      "agent.status"
    ]
  }
}
```

### 取消订阅

```json
{
  "type": "unsubscribe",
  "id": "sub_001"
}
```

## 高级功能

### 多会话管理

```javascript
// 创建新会话
ws.send(JSON.stringify({
  type: 'session_create',
  id: 'req_003',
  payload: {
    title': 'New Conversation'
  }
}));

// 切换会话
ws.send(JSON.stringify({
  type: 'session_switch',
  id: 'req_004',
  payload: {
    session_id': 'session_456'
  }
}));
```

### 进度跟踪

```json
{
  "type": "progress",
  "id": "req_005",
  "payload": {
    "status": "processing",
    "progress": 50,
    "total": 100,
    "message': "Analyzing code..."
  }
}
```

## 协议规范

### 消息格式

```typescript
interface Message {
  type: string;
  id?: string;
  payload?: any;
  timestamp?: number;
}
```

### 类型定义

```typescript
// 请求类型
type RequestType = 
  | 'auth'
  | 'query'
  | 'tool_call'
  | 'subscribe'
  | 'unsubscribe'
  | 'session_create'
  | 'session_switch'
  | 'ping';

// 响应类型
type ResponseType = 
  | 'auth_response'
  | 'query_response'
  | 'query_chunk'
  | 'tool_result'
  | 'notification'
  | 'progress'
  | 'error'
  | 'pong';
```

## 最佳实践

1. **错误处理**: 始终处理可能的错误响应
2. **心跳机制**: 实现 ping/pong 保持连接
3. **重连逻辑**: 网络断开后自动重连
4. **消息确认**: 重要操作等待确认响应
5. **流式处理**: 大响应使用流式模式

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
