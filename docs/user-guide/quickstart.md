# ShadowClaude 快速开始

本指南帮助您在 5 分钟内开始使用 ShadowClaude。

## 目录

1. [第一步：安装](#第一步安装)
2. [第二步：配置](#第二步配置)
3. [第三步：开始对话](#第三步开始对话)
4. [第四步：使用工具](#第四步使用工具)
5. [第五步：探索功能](#第五步探索功能)

---

## 第一步：安装

选择适合您平台的安装方式：

```bash
# macOS/Linux (Homebrew)
brew install shadowclaude

# Python
pip install shadowclaude

# Rust
cargo install shadowclaude
```

验证安装：

```bash
shadowclaude --version
```

---

## 第二步：配置

### 设置 API 密钥

ShadowClaude 需要 LLM API 密钥才能工作：

```bash
# 方式 1：环境变量
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# 方式 2：配置文件
shadowclaude init
# 然后编辑 ~/.config/shadowclaude/config.yaml
```

### 配置文件示例

```yaml
# ~/.config/shadowclaude/config.yaml
llm:
  provider: anthropic
  api_key: ${ANTHROPIC_API_KEY}
  model: claude-3-opus-20240229

memory:
  enabled: true
  vector_store:
    type: qdrant
    url: http://localhost:6333

tools:
  enabled:
    - read_file
    - write_file
    - bash
    - web_fetch

ui:
  theme: dark
  auto_complete: true
```

---

## 第三步：开始对话

### 命令行界面

启动交互式会话：

```bash
shadowclaude
```

您将看到：

```
🌙 ShadowClaude v1.0.0
━━━━━━━━━━━━━━━━━━━━━━━━━

> 你好，ShadowClaude！

你好！我是 ShadowClaude，你的 AI 编程助手。
有什么我可以帮你的吗？

> _
```

### 执行单次查询

```bash
shadowclaude query "列出当前目录的文件"
```

### 使用文件作为输入

```bash
shadowclaude query -f code.py "解释这段代码"
```

---

## 第四步：使用工具

ShadowClaude 可以执行各种工具来帮助您。

### 文件操作

```
> 读取 README.md 文件

我将为您读取文件。

<tool_call>
read_file:0 {"path": "README.md"}
</tool_call>

文件内容：
...
```

### 终端命令

```
> 运行测试

我将为您运行测试。

<tool_call>
bash:1 {"command": "cargo test", "description": "Run tests"}
</tool_call>

测试输出：
...
```

### 代码搜索

```
> 搜索所有的 TODO 注释

<tool_call>
search:2 {"pattern": "TODO|FIXME", "glob": "*.{rs,py,js}"}
</tool_call>
```

---

## 第五步：探索功能

### 记忆功能

ShadowClaude 会自动记住对话内容：

```
> 记住我的名字叫 Alice

好的 Alice，我会记住你的名字。

> 我叫什么名字？

您叫 Alice。
```

### BUDDY 模式

启用赛博宠物：

```bash
shadowclaude --buddy
```

```
🐱 BUDDY: Claudia
━━━━━━━━━━━━━━━━━

你好呀！我是 Claudia，你的编程小伙伴～
今天想一起写什么代码呢？

> 我想学习 Rust

哇，Rust 很棒呢！ 🦀
让我来帮你规划学习路径...
```

### 守护进程模式

启动后台服务：

```bash
# 启动守护进程
shadowclaude daemon start

# 查看状态
shadowclaude daemon status

# 发送任务
shadowclaude daemon task "监控文件变化"
```

### Web 界面

启动 Web UI：

```bash
shadowclaude web --port 8080
```

然后在浏览器中打开 http://localhost:8080

---

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `shadowclaude` | 启动交互式会话 |
| `shadowclaude query "..."` | 执行单次查询 |
| `shadowclaude -f file.txt "..."` | 附带文件查询 |
| `shadowclaude --buddy` | BUDDY 模式 |
| `shadowclaude daemon start` | 启动守护进程 |
| `shadowclaude web` | 启动 Web UI |
| `shadowclaude config` | 编辑配置 |
| `shadowclaude doctor` | 诊断问题 |

---

## 下一步

- 📚 [用户手册完整版](../README.md)
- 🔧 [配置说明](./configuration.md)
- 💡 [示例代码](../examples/)
- 🐛 [故障排除](./troubleshooting.md)

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
