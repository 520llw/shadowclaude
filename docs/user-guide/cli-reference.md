# ShadowClaude 命令行参考

## 全局选项

```bash
shadowclaude [GLOBAL_OPTIONS] [COMMAND] [ARGS]
```

### 全局选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `-c, --config` | 指定配置文件 | `--config ./custom.yaml` |
| `-v, --verbose` | 详细输出 | `--verbose` |
| `-q, --quiet` | 静默模式 | `--quiet` |
| `--version` | 显示版本 | `--version` |
| `--help` | 显示帮助 | `--help` |

## 命令列表

### 基本命令

#### query

执行单次查询。

```bash
shadowclaude query "Your question here"
shadowclaude query -f file.txt "Analyze this"
shadowclaude query --stream "Generate long content"
```

选项：
- `-f, --file`: 从文件读取输入
- `-s, --stream`: 启用流式输出
- `-o, --output`: 输出到文件

#### interactive

启动交互式会话（默认）。

```bash
shadowclaude
shadowclaude interactive
shadowclaude interactive --session mysession
```

### 配置命令

#### init

初始化配置。

```bash
shadowclaude init
shadowclaude init --force
shadowclaude init --global
```

#### config

管理配置。

```bash
shadowclaude config get llm.provider
shadowclaude config set llm.provider openai
shadowclaude config validate
shadowclaude config edit
```

### 工具命令

#### tools

管理工具。

```bash
shadowclaude tools list
shadowclaude tools info read_file
shadowclaude tools enable my_tool
shadowclaude tools disable my_tool
```

### 会话命令

#### sessions

管理会话。

```bash
shadowclaude sessions list
shadowclaude sessions create "New Project"
shadowclaude sessions switch session_id
shadowclaude sessions delete session_id
shadowclaude sessions export session_id --output backup.json
```

### 记忆命令

#### memory

管理记忆。

```bash
shadowclaude memory search "python"
shadowclaude memory store "Important fact"
shadowclaude memory clear
shadowclaude memory export --output memories.json
shadowclaude memory import memories.json
```

### BUDDY 命令

#### buddy

管理 BUDDY。

```bash
shadowclaude buddy chat
shadowclaude buddy status
shadowclaude buddy configure
shadowclaude buddy rename "New Name"
```

### 守护进程命令

#### daemon

管理 KAIROS 守护进程。

```bash
shadowclaude daemon start
shadowclaude daemon stop
shadowclaude daemon status
shadowclaude daemon restart

shadowclaude daemon schedule "backup" --cron "0 2 * * *"
shadowclaude daemon watch ./src --action "run_tests"

shadowclaude daemon jobs list
shadowclaude daemon jobs delete job_id
```

### 系统命令

#### doctor

诊断系统。

```bash
shadowclaude doctor
shadowclaude doctor --fix
```

#### update

更新 ShadowClaude。

```bash
shadowclaude update
shadowclaude update --check
```

#### bug-report

生成错误报告。

```bash
shadowclaude bug-report
shadowclaude bug-report --output report.txt
```

### Web 命令

#### web

启动 Web UI。

```bash
shadowclaude web
shadowclaude web --port 8080
shadowclaude web --host 0.0.0.0
```

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `SHADOWCLAUDE_CONFIG` | 配置文件路径 | `~/.config/sc/config.yaml` |
| `SHADOWCLAUDE_LOG_LEVEL` | 日志级别 | `debug` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | `sk-...` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-...` |

## 退出代码

| 代码 | 含义 |
|------|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 配置错误 |
| 3 | 网络错误 |
| 4 | 权限错误 |
| 130 | 用户中断 (Ctrl+C) |

---

*CLI 参考版本: 1.0.0 | 最后更新: 2026-04-02*
