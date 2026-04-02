# ShadowClaude 配置说明

本文档详细描述 ShadowClaude 的所有配置选项。

## 配置文件位置

ShadowClaude 按以下顺序查找配置：

1. 命令行参数 `--config`
2. 环境变量 `SHADOWCLAUDE_CONFIG`
3. 当前目录 `./shadowclaude.yaml`
4. 用户配置目录：
   - macOS: `~/.config/shadowclaude/config.yaml`
   - Linux: `~/.config/shadowclaude/config.yaml`
   - Windows: `%APPDATA%\ShadowClaude\config.yaml`

## 配置示例

```yaml
# ShadowClaude 配置文件

# ═══════════════════════════════════════════════════
# LLM 配置
# ═══════════════════════════════════════════════════
llm:
  # LLM 提供商: anthropic, openai, gemini, local
  provider: anthropic
  
  # API 密钥（建议使用环境变量：${ANTHROPIC_API_KEY}）
  api_key: ${ANTHROPIC_API_KEY}
  
  # 模型名称
  model: claude-3-opus-20240229
  
  # 备用模型（主模型失败时使用）
  fallback_model: claude-3-sonnet-20240229
  
  # 温度参数 (0.0 - 1.0)
  temperature: 0.7
  
  # 最大 tokens
  max_tokens: 4096
  
  # 超时时间（秒）
  timeout: 120
  
  # 流式响应
  stream: true
  
  # 系统提示
  system_prompt: |
    You are ShadowClaude, an AI programming assistant.
    Be helpful, concise, and accurate.

# ═══════════════════════════════════════════════════
# 记忆系统配置
# ═══════════════════════════════════════════════════
memory:
  # 启用记忆系统
  enabled: true
  
  # 语义记忆（向量数据库）
  semantic:
    enabled: true
    provider: qdrant  # qdrant, pinecone, weaviate
    url: http://localhost:6333
    api_key: null
    collection: shadowclaude_semantic
    embedding_model: text-embedding-3-small
    embedding_dimensions: 1536
  
  # 情景记忆（图数据库）
  episodic:
    enabled: true
    provider: neo4j  # neo4j, dgraph
    url: bolt://localhost:7687
    username: neo4j
    password: ${NEO4J_PASSWORD}
  
  # 工作记忆（缓存）
  working:
    enabled: true
    provider: redis  # redis, memory
    url: redis://localhost:6379
    max_tokens: 4000
    compression_threshold: 0.8
  
  # AutoDream 配置
  autodream:
    enabled: true
    schedule: "0 2 * * *"  # 每天凌晨 2 点

# ═══════════════════════════════════════════════════
# 工具系统配置
# ═══════════════════════════════════════════════════
tools:
  # 启用的工具列表
  enabled:
    - read_file
    - write_file
    - edit_file
    - search_files
    - bash
    - web_fetch
    - web_search
  
  # 禁用的工具（优先级高于 enabled）
  disabled: []
  
  # 文件操作限制
  file:
    # 允许访问的目录
    allowed_paths:
      - "${HOME}/projects"
      - "${PWD}"
    
    # 禁止访问的目录
    denied_paths:
      - "${HOME}/.ssh"
      - "${HOME}/.config"
    
    # 允许的文件扩展名
    allowed_extensions:
      - "*.rs"
      - "*.py"
      - "*.js"
      - "*.ts"
      - "*.md"
      - "*.yaml"
      - "*.json"
    
    # 最大文件大小（MB）
    max_file_size: 10
  
  # 终端执行限制
  bash:
    # 需要确认的危险命令
    dangerous_commands:
      - "rm -rf"
      - "dd"
      - "mkfs"
    
    # 超时时间（秒）
    timeout: 60
    
    # 允许的环境变量
    allowed_env_vars:
      - "PATH"
      - "HOME"
      - "USER"

# ═══════════════════════════════════════════════════
# Agent 系统配置
# ═══════════════════════════════════════════════════
agents:
  enabled: true
  
  # Coordinator 配置
  coordinator:
    # 最大并发任务数
    max_concurrent_tasks: 5
    
    # 任务超时（秒）
    task_timeout: 300
    
    # 调度策略: balanced, greedy, round_robin
    strategy: balanced
  
  # Swarm 配置
  swarm:
    # Worker 数量
    worker_count: 3
    
    # 工作队列大小
    queue_size: 100

# ═══════════════════════════════════════════════════
# BUDDY 系统配置
# ═══════════════════════════════════════════════════
buddy:
  enabled: false
  
  # BUDDY 名称
  name: "Claudia"
  
  # 个性配置
  personality:
    type: friendly  # friendly, professional, playful, calm
    traits:
      - helpful
      - encouraging
    
    # 说话风格
    speech_style:
      formality: casual  # formal, casual, mixed
      emoji_usage: true
      verbosity: medium  # low, medium, high
  
  # 外观配置
  appearance:
    avatar: default
    theme_color: "#FF6B9D"

# ═══════════════════════════════════════════════════
# KAIROS 守护进程配置
# ═══════════════════════════════════════════════════
kairos:
  enabled: false
  
  # 套接字路径
  socket_path: /tmp/shadowclaude.sock
  
  # PID 文件
  pid_file: /var/run/shadowclaude.pid
  
  # 定时任务
  scheduled_jobs:
    - name: cleanup
      schedule: "0 0 * * *"
      command: cleanup_memory
    
    - name: backup
      schedule: "0 2 * * 0"
      command: backup_data
  
  # 文件监控
  file_watches:
    - path: "${PWD}/src"
      events: [modify, create]
      action: "notify"

# ═══════════════════════════════════════════════════
# Web UI 配置
# ═══════════════════════════════════════════════════
web:
  enabled: false
  
  # 监听地址
  host: 127.0.0.1
  port: 8080
  
  # HTTPS 配置
  ssl:
    enabled: false
    cert_path: null
    key_path: null
  
  # 认证配置
  auth:
    type: token  # token, oauth, none
    token: ${WEB_API_TOKEN}
  
  # CORS 配置
  cors:
    allowed_origins:
      - "http://localhost:3000"
    allowed_methods: [GET, POST, PUT, DELETE]

# ═══════════════════════════════════════════════════
# 日志配置
# ═══════════════════════════════════════════════════
logging:
  # 日志级别: trace, debug, info, warn, error
  level: info
  
  # 日志格式: json, pretty
  format: pretty
  
  # 日志输出
  output: stdout  # stdout, file, both
  
  # 日志文件路径（当 output 包含 file 时）
  file_path: "${HOME}/.local/share/shadowclaude/logs"
  
  # 日志轮转
  rotation:
    enabled: true
    max_size: 100MB
    max_files: 7

# ═══════════════════════════════════════════════════
# 界面配置
# ═══════════════════════════════════════════════════
ui:
  # 主题: dark, light, auto
  theme: dark
  
  # 语言
  language: en
  
  # 自动完成
  auto_complete: true
  
  # 语法高亮
  syntax_highlighting: true
  
  # 提示音效
  sound_effects: false

# ═══════════════════════════════════════════════════
# 隐私配置
# ═══════════════════════════════════════════════════
privacy:
  # 启用遥测
  telemetry: false
  
  # 收集使用数据
  analytics: false
  
  # 本地处理优先
  local_first: true
  
  # 数据保留天数
  data_retention_days: 30
```

## 环境变量

所有配置项都可以通过环境变量覆盖：

```bash
# LLM 配置
export SHADOWCLAUDE_LLM_PROVIDER=anthropic
export SHADOWCLAUDE_LLM_API_KEY=sk-xxx
export SHADOWCLAUDE_LLM_MODEL=claude-3-opus

# 记忆配置
export SHADOWCLAUDE_MEMORY_SEMANTIC_URL=http://localhost:6333
export SHADOWCLAUDE_MEMORY_EPISODIC_URL=bolt://localhost:7687

# 功能开关
export SHADOWCLAUDE_BUDDY_ENABLED=true
export SHADOWCLAUDE_KAIROS_ENABLED=false

# 日志
export SHADOWCLAUDE_LOGGING_LEVEL=debug
```

## 配置验证

验证配置文件：

```bash
shadowclaude config validate
```

输出示例：

```
✓ Configuration is valid
  - LLM: anthropic/claude-3-opus-20240229
  - Memory: semantic ✓, episodic ✓, working ✓
  - Tools: 8 enabled
  - Agents: enabled
  - BUDDY: disabled
```

## 多环境配置

支持环境特定的配置文件：

```bash
# 开发环境
shadowclaude --config config.dev.yaml

# 生产环境
shadowclaude --config config.prod.yaml

# 或使用环境变量
export SHADOWCLAUDE_ENV=production
shadowclaude  # 自动加载 config.prod.yaml
```

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
