# ShadowClaude 教程系列

本教程系列帮助您从入门到精通 ShadowClaude。

## 教程列表

### 初学者教程

1. [第1课: 初识 ShadowClaude](#第1课-初识-shadowclaude)
2. [第2课: 第一个查询](#第2课-第一个查询)
3. [第3课: 文件操作基础](#第3课-文件操作基础)
4. [第4课: 代码分析](#第4课-代码分析)
5. [第5课: Web 工具使用](#第5课-web-工具使用)

### 中级教程

6. [第6课: 记忆系统](#第6课-记忆系统)
7. [第7课: 自定义工具](#第7课-自定义工具)
8. [第8课: Agent 入门](#第8课-agent-入门)
9. [第9课: BUDDY 系统](#第9课-buddy-系统)
10. [第10课: KAIROS 定时任务](#第10课-kairos-定时任务)

### 高级教程

11. [第11课: 多 Agent 协作](#第11课-多-agent-协作)
12. [第12课: 高级记忆管理](#第12课-高级记忆管理)
13. [第13课: Undercover 模式](#第13课-undercover-模式)
14. [第14课: MCP 协议开发](#第14课-mcp-协议开发)
15. [第15课: 分布式部署](#第15课-分布式部署)

---

## 第1课: 初识 ShadowClaude

### 1.1 什么是 ShadowClaude

ShadowClaude 是一个 AI 编程助手，它结合了：
- 强大的大语言模型 (LLM)
- 丰富的工具系统
- 智能的记忆能力
- 灵活的 Agent 系统

### 1.2 安装

```bash
pip install shadowclaude
```

### 1.3 配置

创建配置文件 `~/.config/shadowclaude/config.yaml`：

```yaml
llm:
  provider: anthropic
  api_key: your_api_key_here
```

### 1.4 第一次运行

```bash
shadowclaude
```

你会看到欢迎界面，输入你的第一个问题即可开始。

---

## 第2课: 第一个查询

### 2.1 自然语言查询

```
> 什么是 Python 的装饰器？
```

ShadowClaude 会用自然语言解释这个概念。

### 2.2 代码生成

```
> 写一个 Python 函数计算斐波那契数列
```

ShadowClaude 会生成代码：

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

### 2.3 流式响应

使用 `--stream` 标志启用流式输出，可以看到实时生成的内容。

---

## 第3课: 文件操作基础

### 3.1 读取文件

```
> 读取 README.md
```

### 3.2 写入文件

```
> 创建一个新文件 config.yaml，内容为：
  数据库配置信息
```

### 3.3 搜索文件

```
> 搜索所有的 TODO 注释
```

### 3.4 文件编辑

```
> 在 main.py 中添加错误处理
```

---

## 第4课: 代码分析

### 4.1 代码解释

```
> 解释这段代码的作用 [粘贴代码]
```

### 4.2 代码审查

```
> 审查这个函数 [粘贴函数]
```

### 4.3 重构建议

```
> 如何改进这段代码的性能？
```

---

## 第5课: Web 工具使用

### 5.1 网页获取

```
> 获取 https://docs.python.org/3/ 的内容
```

### 5.2 网页搜索

```> 搜索 Python 3.12 的新特性
```

### 5.3 浏览器控制

```
> 打开 http://localhost:3000 并点击登录按钮
```

---

## 第6课: 记忆系统

### 6.1 自动记忆

ShadowClaude 会自动记住对话中的重要信息。

### 6.2 显式存储

```
> 记住：项目使用 Python 3.10
```

### 6.3 记忆检索

```
> 我们使用的是什么 Python 版本？
```

### 6.4 记忆类型

- **语义记忆**: 事实和知识
- **情景记忆**: 事件和经验
- **工作记忆**: 当前会话上下文

---

## 第7课: 自定义工具

### 7.1 创建工具

```python
from shadowclaude.tools import tool

@tool(name="calculate", description="计算数学表达式")
def calculate(expression: str) -> str:
    return str(eval(expression))
```

### 7.2 注册工具

```python
client.register_tool(calculate)
```

### 7.3 使用工具

```
> 计算 2 + 2
```

---

## 第8课: Agent 入门

### 8.1 什么是 Agent

Agent 是专门处理特定任务的智能实体。

### 8.2 内置 Agent

- `CodeAgent`: 代码相关任务
- `FileAgent`: 文件操作
- `TestAgent`: 测试生成

### 8.3 使用 Agent

```python
agent = client.get_agent("code")
result = agent.process("分析这段代码")
```

---

## 第9课: BUDDY 系统

### 9.1 启用 BUDDY

```bash
shadowclaude --buddy
```

### 9.2 与 BUDDY 交互

```
> 你好！

你好呀！我是 Claudia，你的编程小伙伴～
```

### 9.3 个性化 BUDDY

```python
from shadowclaude.buddy import Personality

personality = Personality(
    name="Alex",
    traits=["professional", "concise"]
)
```

---

## 第10课: KAIROS 定时任务

### 10.1 启动守护进程

```bash
shadowclaude daemon start
```

### 10.2 创建定时任务

```python
from shadowclaude.kairos import Job, Trigger

job = Job(
    name="backup",
    trigger=Trigger.cron("0 2 * * *"),
    action=backup_function
)
```

### 10.3 文件监控

```python
watcher.watch(
    path="./src",
    events=[EventType.MODIFY],
    action=run_tests
)
```

---

## 第11课: 多 Agent 协作

### 11.1 创建多个 Agent

```python
coordinator.register_agent("analyzer", AnalyzerAgent())
coordinator.register_agent("generator", GeneratorAgent())
coordinator.register_agent("reviewer", ReviewerAgent())
```

### 11.2 工作流定义

```python
workflow = coordinator.create_workflow()
workflow.add_step("analyze", depends_on=[])
workflow.add_step("generate", depends_on=["analyze"])
workflow.add_step("review", depends_on=["generate"])
```

### 11.3 执行工作流

```python
result = workflow.execute(task_data)
```

---

## 第12课: 高级记忆管理

### 12.1 自定义嵌入

```python
from shadowclaude.memory import Embedder

class CustomEmbedder(Embedder):
    def embed(self, text: str):
        # 自定义嵌入逻辑
        return embedding_vector
```

### 12.2 记忆关系

```python
memory.link(
    source=memory_id_1,
    target=memory_id_2,
    relation_type="related_to"
)
```

### 12.3 记忆导出

```python
memory.export_to_file("memories.json")
```

---

## 第13课: Undercover 模式

### 13.1 启用 Undercover

```bash
shadowclaude --undercover
```

### 13.2 配置触发器

```python
undercover.add_trigger(
    pattern=r"error|exception",
    action=suggest_fix
)
```

### 13.3 上下文感知

Undercover 会自动检测当前工作上下文并提供相关建议。

---

## 第14课: MCP 协议开发

### 14.1 创建 MCP Server

```python
from shadowclaude.mcp import McpServer

server = McpServer()

@server.tool("custom_tool")
def custom_tool(args):
    return {"result": "success"}

server.run()
```

### 14.2 连接 MCP Client

```python
client = McpClient.connect("localhost:8080")
tools = client.discover_tools()
```

---

## 第15课: 分布式部署

### 15.1 配置集群

```python
cluster = Cluster(name="production")
cluster.add_node(NodeConfig(id="node1", host="10.0.0.1"))
cluster.add_node(NodeConfig(id="node2", host="10.0.0.2"))
```

### 15.2 负载均衡

```python
cluster.configure_load_balancer(
    strategy="least_connections"
)
```

### 15.3 部署任务

```python
task = Task(
    description="大规模代码分析",
    distributed=True,
    partitions=10
)
result = cluster.submit(task)
```

---

## 结语

恭喜完成所有教程！您现在可以熟练使用 ShadowClaude 的各种功能了。

继续探索：
- 阅读 [API 文档](../api/)
- 查看 [示例代码](../examples/)
- 参与 [社区讨论](https://discord.gg/shadowclaude)

---

*教程版本: 1.0.0 | 最后更新: 2026-04-02*
