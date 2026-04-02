# ShadowClaude 示例代码

本目录包含 50+ 完整的示例项目，涵盖各种使用场景。

## 示例目录

### 基础示例 (basic/)

| 示例 | 说明 | 代码 |
|------|------|------|
| 01-hello-world | 最简单的 ShadowClaude 使用 | [查看](./basic/01-hello-world/) |
| 02-query-engine | 使用 QueryEngine 处理查询 | [查看](./basic/02-query-engine/) |
| 03-file-operations | 文件读写操作 | [查看](./basic/03-file-operations/) |
| 04-tool-execution | 工具执行 | [查看](./basic/04-tool-operations/) |
| 05-memory-basic | 基础记忆使用 | [查看](./basic/05-memory-basic/) |

### 中级示例 (intermediate/)

| 示例 | 说明 | 代码 |
|------|------|------|
| 01-custom-tools | 创建自定义工具 | [查看](./intermediate/01-custom-tools/) |
| 02-agent-basic | 基础 Agent 使用 | [查看](./intermediate/02-agent-basic/) |
| 03-buddy-setup | BUDDY 系统配置 | [查看](./intermediate/03-buddy-setup/) |
| 04-kairos-jobs | KAIROS 定时任务 | [查看](./intermediate/04-kairos-jobs/) |
| 05-web-integration | Web 集成 | [查看](./intermediate/05-web-integration/) |

### 高级示例 (advanced/)

| 示例 | 说明 | 代码 |
|------|------|------|
| 01-multi-agent | 多 Agent 协作 | [查看](./advanced/01-multi-agent/) |
| 02-memory-advanced | 高级记忆管理 | [查看](./advanced/02-memory-advanced/) |
| 03-undercover-mode | Undercover 模式 | [查看](./advanced/03-undercover-mode/) |
| 04-mcp-server | MCP 服务器开发 | [查看](./advanced/04-mcp-server/) |
| 05-distributed | 分布式部署 | [查看](./advanced/05-distributed/) |

### 集成示例 (integrations/)

| 示例 | 说明 | 代码 |
|------|------|------|
| 01-vscode-extension | VS Code 扩展 | [查看](./integrations/01-vscode-extension/) |
| 02-jupyter-notebook | Jupyter Notebook | [查看](./integrations/02-jupyter-notebook/) |
| 03-slack-bot | Slack 机器人 | [查看](./integrations/03-slack-bot/) |
| 04-discord-bot | Discord 机器人 | [查看](./integrations/04-discord-bot/) |
| 05-telegram-bot | Telegram 机器人 | [查看](./integrations/05-telegram-bot/) |

---

## 快速开始示例

### 示例 1: Hello World

```python
# basic/01-hello-world/main.py
import shadowclaude as sc

# 创建客户端
client = sc.Client()

# 发送查询
response = client.query("Hello, ShadowClaude!")
print(response.content)
```

### 示例 2: 文件分析

```python
# basic/03-file-operations/analyze_code.py
import shadowclaude as sc

client = sc.Client()

# 读取文件
with open('src/main.rs', 'r') as f:
    code = f.read()

# 分析代码
response = client.query(f"""
分析以下代码的质量：

```rust
{code}
```

请提供：
1. 代码结构评价
2. 潜在问题
3. 改进建议
""")

print(response.content)
```

### 示例 3: 自定义工具

```python
# intermediate/01-custom-tools/weather_tool.py
import shadowclaude as sc
from shadowclaude.tools import tool
import requests

@tool(
    name="get_weather",
    description="获取指定城市的天气信息"
)
def get_weather(city: str) -> str:
    """
    获取天气信息。
    
    Args:
        city: 城市名称，如 "北京"、"Shanghai"
    
    Returns:
        天气信息字符串
    """
    # 这里使用示例 API
    response = requests.get(
        f"https://api.weather.com/v1/current?city={city}"
    )
    data = response.json()
    
    return f"{city}: {data['temperature']}°C, {data['condition']}"

# 注册工具
client = sc.Client()
client.register_tool(get_weather)

# 使用工具
response = client.query("北京今天天气怎么样？")
print(response.content)
```

### 示例 4: Agent 协作

```python
# intermediate/02-agent-basic/multi_agent.py
import shadowclaude as sc
from shadowclaude.agents import Agent, Task

# 定义代码分析 Agent
class CodeAnalyzer(Agent):
    def handle(self, task: Task):
        # 分析代码逻辑
        analysis = self.analyze(task.data['code'])
        return {'analysis': analysis}

# 定义测试生成 Agent
class TestGenerator(Agent):
    def handle(self, task: Task):
        # 基于分析生成测试
        tests = self.generate_tests(task.data['analysis'])
        return {'tests': tests}

# 创建协调器
client = sc.Client()
coordinator = client.get_coordinator()

# 注册 Agents
coordinator.register_agent(CodeAnalyzer())
coordinator.register_agent(TestGenerator())

# 分配任务
task = Task(
    description="为这段代码生成测试",
    data={'code': '...'}
)

result = coordinator.dispatch(task)
print(result)
```

### 示例 5: BUDDY 交互

```python
# intermediate/03-buddy-setup/chat_with_buddy.py
import shadowclaude as sc
from shadowclaude.buddy import Personality

# 配置 BUDDY 个性
personality = Personality(
    name="Claudia",
    traits=["friendly", "helpful", "enthusiastic"],
    speech_style="casual"
)

# 创建 BUDDY
buddy = sc.Buddy(personality=personality)

# 交互
while True:
    user_input = input("You: ")
    if user_input.lower() == 'exit':
        break
    
    response = buddy.interact(user_input)
    print(f"{buddy.name}: {response.message}")
```

### 示例 6: KAIROS 定时任务

```python
# intermediate/04-kairos-jobs/scheduled_tasks.py
import shadowclaude as sc
from shadowclaude.kairos import Job, Trigger

# 创建 KAIROS 客户端
kairos = sc.Kairos()

# 定义备份任务
backup_job = Job(
    name="daily_backup",
    trigger=Trigger.cron("0 2 * * *"),  # 每天凌晨 2 点
    action=lambda: backup_memory()
)

# 定义清理任务
cleanup_job = Job(
    name="cleanup_old_memories",
    trigger=Trigger.interval(hours=6),
    action=lambda: cleanup_memories(days=30)
)

# 注册任务
kairos.schedule(backup_job)
kairos.schedule(cleanup_job)

# 启动守护进程
kairos.start()
```

### 示例 7: WebSocket 实时通信

```python
# intermediate/05-web-integration/websocket_client.py
import asyncio
import websockets
import json

async def chat_with_shadowclaude():
    uri = "ws://localhost:8080/ws"
    
    async with websockets.connect(uri) as ws:
        # 认证
        await ws.send(json.dumps({
            "type": "auth",
            "token": "your_api_token"
        }))
        
        # 发送查询
        await ws.send(json.dumps({
            "type": "query",
            "id": "req_001",
            "payload": {
                "message": "Hello!",
                "stream": True
            }
        }))
        
        # 接收流式响应
        async for message in ws:
            data = json.loads(message)
            
            if data['type'] == 'query_chunk':
                print(data['payload']['content'], end='', flush=True)
            elif data['payload'].get('done'):
                print()
                break

asyncio.run(chat_with_shadowclaude())
```

---

## 运行示例

每个示例目录包含：

- `main.py` - 主程序
- `README.md` - 说明文档
- `requirements.txt` - 依赖
- `config.yaml` - 配置文件（可选）

运行示例：

```bash
cd examples/basic/01-hello-world
pip install -r requirements.txt
python main.py
```

---

## 贡献示例

欢迎贡献新的示例！请遵循以下结构：

```
examples/
├── category/
│   └── XX-example-name/
│       ├── main.py          # 主要代码
│       ├── README.md        # 详细说明
│       ├── requirements.txt # 依赖
│       └── config.yaml      # 配置（可选）
```

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
