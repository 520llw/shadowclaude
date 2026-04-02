# ShadowClaude 用户指南 (中文版)

## 目录

1. [安装](#安装)
2. [快速开始](#快速开始)
3. [基本功能](#基本功能)
4. [高级功能](#高级功能)
5. [配置](#配置)
6. [故障排除](#故障排除)

---

## 安装

### 使用 pip 安装

```bash
pip install shadowclaude
```

### 使用 Homebrew 安装 (macOS/Linux)

```bash
brew install shadowclaude
```

### 使用 Cargo 安装

```bash
cargo install shadowclaude
```

---

## 快速开始

### 配置 API 密钥

```bash
export ANTHROPIC_API_KEY=your_api_key
```

### 启动 ShadowClaude

```bash
shadowclaude
```

### 执行单次查询

```bash
shadowclaude query "你好，ShadowClaude！"
```

---

## 基本功能

### 文件操作

```
> 读取 README.md
> 搜索所有 TODO 注释
> 编辑 src/main.rs 添加日志
```

### 终端命令

```
> 运行 cargo test
> 查看 git 状态
> 查找大文件
```

### Web 搜索

```
> 搜索 Python 3.12 新特性
> 获取 https://example.com 的内容
```

---

## 高级功能

### BUDDY 模式

```bash
shadowclaude --buddy
```

与赛博宠物对话：

```
> 你好！

你好呀！我是你的编程小伙伴～ 🐱
今天想一起写什么代码呢？
```

### KAIROS 守护进程

```bash
# 启动守护进程
shadowclaude daemon start

# 添加定时任务
shadowclaude daemon schedule "每天备份" --cron "0 2 * * *"

# 监控文件变化
shadowclaude daemon watch ./src --action "自动测试"
```

### Undercover 模式

```bash
shadowclaude --undercover
```

静默监控，自动建议。

---

## 配置

### 配置文件位置

- Linux/macOS: `~/.config/shadowclaude/config.yaml`
- Windows: `%APPDATA%\ShadowClaude\config.yaml`

### 基本配置

```yaml
llm:
  provider: anthropic
  api_key: ${ANTHROPIC_API_KEY}
  model: claude-3-opus-20240229

memory:
  enabled: true

tools:
  enabled:
    - read_file
    - write_file
    - bash
```

---

## 故障排除

### API 密钥错误

```
Error: LLM API key not configured
```

解决方案：

```bash
export ANTHROPIC_API_KEY=sk-xxx
```

### 命令未找到

```bash
which shadowclaude
```

确保安装路径在 PATH 中。

### 诊断工具

```bash
shadowclaude doctor
```

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
