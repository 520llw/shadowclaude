# ShadowClaude Python API 参考

本文档详细描述 ShadowClaude Python 包的所有公共 API。

## 目录

1. [Core API](#core-api)
2. [QueryEngine](#queryengine)
3. [Memory System](#memory-system)
4. [Tool System](#tool-system)
5. [Agent System](#agent-system)
6. [Configuration](#configuration)

---

## Core API

### `shadowclaude`

主模块入口。

```python
import shadowclaude as sc

# 获取版本
print(sc.__version__)

# 初始化客户端
client = sc.Client()
```

### `shadowclaude.Client`

ShadowClaude 主客户端类。

#### 构造函数

```python
Client(
    config: Config | None = None,
    llm_provider: str = "anthropic",
    memory_enabled: bool = True,
) -> Client
```

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config` | `Config \| None` | `None` | 配置对象 |
| `llm_provider` | `str` | `"anthropic"` | LLM 提供商 |
| `memory_enabled` | `bool` | `True` | 是否启用记忆 |

**示例:**

```python
from shadowclaude import Client, Config

config = Config.from_file("config.yaml")
client = Client(config=config)
```

#### 方法

##### `query()`

```python
async def query(
    self,
    message: str,
    context: dict[str, Any] | None = None,
    stream: bool = False,
) -> Response | AsyncIterator[Chunk]
```

处理用户查询。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `message` | `str` | - | 用户消息 |
| `context` | `dict \| None` | `None` | 附加上下文 |
| `stream` | `bool` | `False` | 是否流式响应 |

**返回:**
- `stream=False`: `Response` 对象
- `stream=True`: `AsyncIterator[Chunk]` 流式迭代器

**示例:**

```python
# 标准查询
response = await client.query("Hello, ShadowClaude!")
print(response.content)

# 流式查询
async for chunk in await client.query("Tell me a story", stream=True):
    print(chunk.content, end="", flush=True)
```

##### `execute_tool()`

```python
async def execute_tool(
    self,
    tool_name: str,
    arguments: dict[str, Any],
    check_permission: bool = True,
) -> ToolResult
```

执行指定工具。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tool_name` | `str` | - | 工具名称 |
| `arguments` | `dict` | - | 工具参数 |
| `check_permission` | `bool` | `True` | 是否检查权限 |

**返回:**
- `ToolResult`: 工具执行结果

**示例:**

```python
result = await client.execute_tool(
    "read_file",
    {"path": "/path/to/file.txt"}
)
print(result.output)
```

##### `register_tool()`

```python
def register_tool(
    self,
    tool: Tool | Callable,
    name: str | None = None,
) -> None
```

注册自定义工具。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tool` | `Tool \| Callable` | - | 工具对象或函数 |
| `name` | `str \| None` | `None` | 工具名称 |

**示例:**

```python
from shadowclaude import tool

@tool
def my_custom_tool(input: str) -> str:
    """My custom tool description."""
    return f"Processed: {input}"

client.register_tool(my_custom_tool)
```

##### `get_memory()`

```python
def get_memory(self) -> MemoryManager
```

获取记忆管理器。

**返回:**
- `MemoryManager`: 记忆管理器实例

---

## QueryEngine

### `shadowclaude.QueryEngine`

查询引擎核心类。

```python
from shadowclaude import QueryEngine

engine = QueryEngine(config=config)
```

#### 方法

##### `process()`

```python
async def process(
    self,
    query: Query,
    options: ProcessOptions | None = None,
) -> QueryResult
```

处理查询请求。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | `Query` | - | 查询对象 |
| `options` | `ProcessOptions \| None` | `None` | 处理选项 |

**示例:**

```python
from shadowclaude import Query, QueryType

query = Query(
    content="List files in current directory",
    type=QueryType.NATURAL_LANGUAGE,
)

result = await engine.process(query)
```

##### `add_middleware()`

```python
def add_middleware(
    self,
    middleware: Middleware,
    priority: int = 0,
) -> None
```

添加处理中间件。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `middleware` | `Middleware` | - | 中间件实例 |
| `priority` | `int` | `0` | 优先级（数字越小优先级越高） |

**示例:**

```python
class LoggingMiddleware(Middleware):
    async def process(self, query: Query, next):
        print(f"Processing: {query.content}")
        result = await next(query)
        print(f"Completed: {result.status}")
        return result

engine.add_middleware(LoggingMiddleware(), priority=0)
```

---

## Memory System

### `shadowclaude.memory.MemoryManager`

记忆管理器主类。

```python
from shadowclaude.memory import MemoryManager

memory = MemoryManager(
    semantic_config=SemanticMemoryConfig(),
    episodic_config=EpisodicMemoryConfig(),
)
```

#### 方法

##### `store()`

```python
async def store(
    self,
    content: str | Message,
    memory_type: MemoryType = MemoryType.AUTO,
    metadata: dict[str, Any] | None = None,
) -> MemoryId
```

存储记忆。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `content` | `str \| Message` | - | 记忆内容 |
| `memory_type` | `MemoryType` | `AUTO` | 记忆类型 |
| `metadata` | `dict \| None` | `None` | 元数据 |

**返回:**
- `MemoryId`: 记忆唯一标识

**示例:**

```python
memory_id = await memory.store(
    "Python is a programming language",
    memory_type=MemoryType.SEMANTIC,
    metadata={"topic": "programming", "language": "python"},
)
```

##### `retrieve()`

```python
async def retrieve(
    self,
    query: str,
    limit: int = 10,
    memory_types: list[MemoryType] | None = None,
    filters: dict[str, Any] | None = None,
) -> list[Memory]
```

检索记忆。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | `str` | - | 查询字符串 |
| `limit` | `int` | `10` | 返回数量限制 |
| `memory_types` | `list[MemoryType] \| None` | `None` | 记忆类型过滤 |
| `filters` | `dict \| None` | `None` | 元数据过滤 |

**返回:**
- `list[Memory]`: 记忆列表

**示例:**

```python
memories = await memory.retrieve(
    "programming languages",
    limit=5,
    memory_types=[MemoryType.SEMANTIC],
)

for mem in memories:
    print(f"{mem.content} (score: {mem.score})")
```

##### `get_working_memory()`

```python
def get_working_memory(self) -> WorkingMemory
```

获取工作记忆。

**返回:**
- `WorkingMemory`: 工作记忆实例

### `shadowclaude.memory.WorkingMemory`

工作记忆管理类。

#### 方法

##### `add_message()`

```python
def add_message(
    self,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None
```

添加消息到工作记忆。

##### `get_context()`

```python
def get_context(
    self,
    max_tokens: int = 4000,
) -> list[Message]
```

获取上下文消息。

##### `clear()`

```python
def clear(self) -> None
```

清空工作记忆。

---

## Tool System

### `shadowclaude.tools.Tool`

工具基类。

```python
from shadowclaude.tools import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "My tool description"
    
    async def execute(self, **kwargs) -> ToolResult:
        # Tool implementation
        return ToolResult(output="result")
```

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 工具名称 |
| `description` | `str` | 工具描述 |
| `parameters` | `dict` | 参数 JSON Schema |

### `shadowclaude.tools.tool` (装饰器)

工具装饰器。

```python
from shadowclaude.tools import tool

@tool(
    name="greet",
    description="Greet a person",
)
def greet_tool(name: str, greeting: str = "Hello") -> str:
    """
    Greet someone.
    
    Args:
        name: Person's name
        greeting: Greeting message
    
    Returns:
        Greeting string
    """
    return f"{greeting}, {name}!"
```

### `shadowclaude.tools.ToolRegistry`

工具注册表。

#### 方法

##### `register()`

```python
def register(self, tool: Tool | Callable) -> None
```

注册工具。

##### `get()`

```python
def get(self, name: str) -> Tool
```

获取工具。

##### `list_tools()`

```python
def list_tools(self) -> list[ToolInfo]
```

列出所有工具。

---

## Agent System

### `shadowclaude.agents.Coordinator`

Agent 协调器。

```python
from shadowclaude.agents import Coordinator

coordinator = Coordinator()
```

#### 方法

##### `register_agent()`

```python
def register_agent(
    self,
    agent: Agent,
    agent_type: AgentType,
) -> AgentId
```

注册 Agent。

**参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent` | `Agent` | Agent 实例 |
| `agent_type` | `AgentType` | Agent 类型 |

**返回:**
- `AgentId`: Agent 标识

##### `dispatch()`

```python
async def dispatch(
    self,
    task: Task,
    strategy: DispatchStrategy = DispatchStrategy.BALANCED,
) -> TaskResult
```

分发任务。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `task` | `Task` | - | 任务对象 |
| `strategy` | `DispatchStrategy` | `BALANCED` | 调度策略 |

### `shadowclaude.agents.Agent`

Agent 基类。

```python
from shadowclaude.agents import Agent

class MyAgent(Agent):
    def __init__(self):
        super().__init__(name="my_agent")
    
    async def handle(self, task: Task) -> TaskResult:
        # Handle task
        return TaskResult(success=True, output="result")
```

---

## Configuration

### `shadowclaude.config.Config`

配置类。

```python
from shadowclaude.config import Config

config = Config.from_file("config.yaml")
# 或
config = Config.from_dict({
    "llm": {
        "provider": "anthropic",
        "api_key": "...",
    },
    "memory": {
        "enabled": True,
    },
})
```

#### 类方法

##### `from_file()`

```python
@classmethod
def from_file(cls, path: str | Path) -> Config
```

从文件加载配置。

支持格式: YAML, JSON, TOML

##### `from_env()`

```python
@classmethod
def from_env(cls, prefix: str = "SHADOWCLAUDE") -> Config
```

从环境变量加载配置。

**示例:**

```bash
export SHADOWCLAUDE_LLM_PROVIDER=anthropic
export SHADOWCLAUDE_LLM_API_KEY=...
```

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `llm` | `LLMConfig` | LLM 配置 |
| `memory` | `MemoryConfig` | 记忆配置 |
| `tools` | `ToolsConfig` | 工具配置 |
| `agents` | `AgentsConfig` | Agent 配置 |

---

## BUDDY System

### `shadowclaude.buddy.Buddy`

赛博宠物类。

```python
from shadowclaude.buddy import Buddy

buddy = Buddy(
    name="Claudia",
    personality=Personality.friendly(),
)
```

#### 方法

##### `interact()`

```python
async def interact(self, input: str) -> BuddyResponse
```

与 BUDDY 交互。

**示例:**

```python
response = await buddy.interact("Hello!")
print(response.message)
print(response.emotion)
```

##### `get_status()`

```python
def get_status(self) -> BuddyStatus
```

获取 BUDDY 状态。

---

## Exception Handling

### 异常类

```python
from shadowclaude.exceptions import (
    ShadowClaudeError,  # 基础异常
    ConfigurationError,  # 配置错误
    ToolError,          # 工具执行错误
    MemoryError,        # 记忆操作错误
    AgentError,         # Agent 错误
    LLMError,           # LLM 调用错误
    PermissionError,    # 权限错误
)

# 使用示例
try:
    result = await client.query("...")
except ToolError as e:
    print(f"Tool failed: {e.tool_name}")
except LLMError as e:
    print(f"LLM error: {e.message}")
```

---

## Types

### 常用类型定义

```python
from shadowclaude.types import (
    # 基础类型
    Message,
    Response,
    Chunk,
    Query,
    QueryResult,
    
    # 工具类型
    Tool,
    ToolResult,
    ToolInfo,
    
    # 记忆类型
    Memory,
    MemoryId,
    MemoryType,
    
    # Agent 类型
    Agent,
    AgentId,
    AgentType,
    Task,
    TaskResult,
)
```

---

*文档版本: 1.0.0 | Python 版本: >=3.9 | 最后更新: 2026-04-02*
