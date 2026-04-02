# ShadowClaude FAQ

## 一般问题

### Q: ShadowClaude 是什么？

ShadowClaude 是一个 AI 编程助手框架，提供代码生成、分析、重构等功能。它基于 Rust 和 Python 构建，具有高性能、可扩展的特点。

### Q: ShadowClaude 和 Claude Code 有什么区别？

ShadowClaude 是独立开发的开源项目，虽然参考了 Claude Code 的功能设计，但具有以下特点：
- 开源免费
- Rust 核心，性能更高
- 三层记忆系统
- 多 Agent 协作
- BUDDY 赛博宠物系统
- KAIROS 守护进程模式

### Q: ShadowClaude 支持哪些 LLM？

目前支持：
- Anthropic Claude (推荐)
- OpenAI GPT
- Google Gemini
- 本地模型 (通过 Ollama)

### Q: ShadowClaude 是免费的吗？

ShadowClaude 本身是开源免费的，但使用 LLM API 可能需要支付相应费用。

## 安装问题

### Q: 如何安装 ShadowClaude？

最简单的方式：

```bash
pip install shadowclaude
```

其他方式见 [安装指南](../installation/)。

### Q: 安装失败怎么办？

1. 检查 Python 版本 (>= 3.9)
2. 升级 pip: `pip install --upgrade pip`
3. 使用虚拟环境
4. 查看 [故障排除](../troubleshooting.md)

### Q: 支持 Windows 吗？

支持！可以通过 pip、winget 或 scoop 安装。

## 配置问题

### Q: 如何配置 API 密钥？

方式一：环境变量
```bash
export ANTHROPIC_API_KEY=sk-xxx
```

方式二：配置文件
```yaml
# ~/.config/shadowclaude/config.yaml
llm:
  api_key: sk-xxx
```

### Q: 配置文件在哪里？

- Linux/macOS: `~/.config/shadowclaude/config.yaml`
- Windows: `%APPDATA%\ShadowClaude\config.yaml`

### Q: 如何切换 LLM 提供商？

```yaml
llm:
  provider: openai  # 或 anthropic, gemini
  api_key: your_key
```

## 使用问题

### Q: 如何读取文件？

```
> 读取 README.md
```

或

```python
result = client.execute_tool("read_file", {"path": "README.md"})
```

### Q: 如何生成代码？

```
> 写一个 Python 函数计算斐波那契数列
```

### Q: 如何搜索代码？

```
> 搜索所有的 TODO 注释
```

### Q: 如何运行终端命令？

```
> 运行 ls -la
```

## 记忆系统

### Q: ShadowClaude 能记住对话吗？

是的，ShadowClaude 具有三层记忆系统：
- 语义记忆：长期知识
- 情景记忆：事件和经验
- 工作记忆：当前会话上下文

### Q: 如何清空记忆？

```bash
shadowclaude memory clear
```

### Q: 记忆存储在哪里？

- 语义记忆：向量数据库 (Qdrant/Pinecone)
- 情景记忆：图数据库 (Neo4j)
- 工作记忆：Redis/内存

### Q: 如何导出记忆？

```python
memory.export_to_file("memories.json")
```

## 工具系统

### Q: 有哪些内置工具？

40+ 工具，包括：
- 文件操作：read_file, write_file, search_files
- 终端：bash, process
- 代码：grep, lint, format
- Web：web_fetch, web_search

### Q: 如何添加自定义工具？

```python
from shadowclaude.tools import tool

@tool(name="my_tool")
def my_tool(arg: str):
    return result

client.register_tool(my_tool)
```

### Q: 工具执行安全吗？

是的，ShadowClaude 具有六层权限防御：
1. 用户授权
2. 进程隔离
3. 文件 ACL
4. 工具权限
5. Agent 沙箱
6. 应用安全

## Agent 系统

### Q: 什么是 Agent？

Agent 是专门处理特定任务的智能实体，如代码分析、测试生成等。

### Q: 如何使用 Agent？

```python
coordinator = client.get_coordinator()
result = coordinator.dispatch(Task(
    agent_type="code",
    data={"code": "..."}
))
```

### Q: 可以创建自定义 Agent 吗？

可以：

```python
class MyAgent(Agent):
    def handle(self, task):
        return TaskResult(...)

coordinator.register_agent("my", MyAgent())
```

## BUDDY 系统

### Q: BUDDY 是什么？

BUDDY 是 ShadowClaude 的赛博宠物系统，提供情感陪伴和个性化交互。

### Q: 如何启用 BUDDY？

```bash
shadowclaude --buddy
```

### Q: 可以自定义 BUDDY 吗？

可以：

```python
from shadowclaude.buddy import Personality

buddy = sc.Buddy(personality=Personality(
    name="Alex",
    traits=["friendly"]
))
```

## KAIROS 守护进程

### Q: KAIROS 是什么？

KAIROS 是 ShadowClaude 的守护进程模式，支持定时任务和文件监控。

### Q: 如何启动守护进程？

```bash
shadowclaude daemon start
```

### Q: 如何创建定时任务？

```python
from shadowclaude.kairos import Job, Trigger

job = Job(
    name="backup",
    trigger=Trigger.cron("0 2 * * *"),
    action=backup_function
)
kairos.schedule(job)
```

## 性能问题

### Q: ShadowClaude 运行很慢怎么办？

1. 启用缓存：
```yaml
cache:
  enabled: true
```

2. 使用更快的模型
3. 检查系统资源
4. 禁用不必要的功能

### Q: 如何减少 API 调用成本？

1. 启用 Prompt 缓存
2. 使用本地模型
3. 批量处理请求
4. 设置合理的 max_tokens

### Q: 内存占用过高怎么办？

1. 限制工作记忆大小：
```yaml
memory:
  working:
    max_tokens: 2000
```

2. 清理缓存
3. 减少并发任务

## 安全问题

### Q: ShadowClaude 会泄露我的代码吗？

不会。ShadowClaude：
- 本地处理优先
- 不发送代码到第三方（除非使用 LLM API）
- 支持离线使用

### Q: 如何限制文件访问？

```yaml
tools:
  file:
    allowed_paths:
      - "${HOME}/projects"
```

### Q: 如何禁用危险工具？

```yaml
tools:
  disabled:
    - bash
```

## 开发问题

### Q: 如何参与开发？

1. Fork 仓库
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

详见 [贡献指南](../../development/guidelines/contributing.md)。

### Q: 如何构建源码？

```bash
git clone https://github.com/shadowclaude/shadowclaude.git
cd shadowclaude
cargo build --release
```

### Q: 如何运行测试？

```bash
# Rust 测试
cargo test

# Python 测试
cd python && pytest
```

## 集成问题

### Q: 可以和 VS Code 集成吗？

可以，有官方 VS Code 扩展。

### Q: 可以在 Jupyter Notebook 中使用吗？

可以，使用 Magic 命令：

```python
%shadowclaude explain this code
```

### Q: 可以部署为 Slack/Discord 机器人吗？

可以，有示例代码展示如何集成。

## 故障排除

### Q: 遇到错误怎么办？

1. 运行诊断：
```bash
shadowclaude doctor
```

2. 查看日志：
```bash
shadowclaude --verbose
```

3. 检查 [故障排除指南](../troubleshooting.md)

### Q: 如何报告 Bug？

```bash
shadowclaude bug-report
```

或在 GitHub 创建 Issue。

### Q: 如何获取帮助？

- 查看文档
- 加入 Discord 社区
- 在 GitHub 创建 Issue
- 发送邮件至 support@shadowclaude.dev

## 其他问题

### Q: ShadowClaude 会开源吗？

已经开源！代码在 GitHub 上。

### Q: 有商业支持吗？

有，联系 enterprise@shadowclaude.dev。

### Q: 路线图是什么？

查看 GitHub Projects 了解开发计划。

### Q: 如何更新 ShadowClaude？

```bash
pip install -U shadowclaude
```

---

*FAQ 版本: 1.0.0 | 最后更新: 2026-04-02*
