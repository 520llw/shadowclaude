# ShadowClaude

The Open Source AI Coding Assistant - 基于 Claude Code 泄露源码精华实现

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)

---

## 🎯 项目简介

ShadowClaude 是 Claude Code 的开源复刻实现，包含：
- ✅ 完整的 **QueryEngine** 核心引擎
- ✅ **三层记忆系统** (Semantic/Episodic/Working)
- ✅ **Agent Swarm** 多 Agent 协作
- ✅ **40+ 内置工具**
- ✅ **Prompt Cache** 分段缓存优化
- ✅ **KAIROS** 守护进程模式
- ✅ **BUDDY** 赛博宠物系统
- ✅ **Undercover Mode** 卧底模式

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/520llw/shadowclaude.git
cd shadowclaude/python

# 安装依赖
pip install -e .

# 或者从 PyPI 安装 (未来)
pip install shadowclaude
```

### 使用

```bash
# 交互模式
shadowclaude

# 一次性提问
shadowclaude "帮我修复这个 bug"

# 启动 BUDDY 宠物
shadowclaude --buddy

# 启动 KAIROS 守护进程
shadowclaude --kairos-start

# 激活卧底模式
shadowclaude --undercover
```

---

## 🏗️ 架构

```
shadowclaude/
├── query_engine.py      # 核心引擎 (TAOR 循环)
├── memory/              # 三层记忆系统
│   ├── semantic.py      # 长期语义记忆
│   ├── episodic.py      # 情景记忆
│   └── working.py       # 工作记忆
├── tools/               # 40+ 工具系统
├── agents/              # Agent Swarm
├── kairos/              # 守护进程
├── buddy/               # 赛博宠物
└── undercover/          # 卧底模式
```

---

## ✨ 核心功能

### 1. QueryEngine - 核心引擎

基于 **TAOR 循环** (Think → Act → Observe → Repeat)

```python
from shadowclaude import QueryEngine, QueryEngineConfig

config = QueryEngineConfig(
    model="claude-sonnet-4-6",
    max_turns=32,
    enable_semantic_memory=True
)

engine = QueryEngine(config)
result = engine.submit_message("帮我分析这个代码")
print(result.output)
```

### 2. 三层记忆系统

- **Semantic Memory**: 长期知识，RAG 检索
- **Episodic Memory**: 对话历史，按需拉取
- **Working Memory**: 当前上下文，自动压缩

### 3. Agent Swarm

```python
from shadowclaude.agents import Coordinator, AgentType

coordinator = Coordinator()

# Fork 多个子 Agent 并行执行
results = coordinator.fork_agents([
    ("Explore codebase", "Find all TODOs", AgentType.EXPLORE),
    ("Plan refactoring", "Design new structure", AgentType.PLAN),
], parallel=True)
```

### 4. BUDDY 赛博宠物

```bash
shadowclaude --buddy
```

18 种物种，5 级稀有度，5 维属性！

### 5. KAIROS 守护进程

7×24 小时在线，支持：
- Cron 定时任务
- Webhook 触发
- AutoDream 记忆整合

### 6. Undercover Mode

在公共仓库自动激活，剥离 AI 特征：
- 移除 "As an AI" 等声明
- 添加人类特征（拼写错误、非正式用语）
- 模仿项目代码风格

---

## 📊 与 Claude Code 对比

| 特性 | Claude Code | ShadowClaude |
|------|-------------|--------------|
| 开源 | ❌ | ✅ |
| 三层记忆 | ✅ | ✅ |
| Agent Swarm | ✅ | ✅ |
| KAIROS | ✅ | ✅ |
| BUDDY | ✅ | ✅ |
| Undercover | ✅ | ✅ |
| Prompt Cache | ✅ | ✅ |
| 价格 | $20/月 | 免费 |

---

## 🛣️ 路线图

- [x] 核心引擎
- [x] 记忆系统
- [x] 工具系统
- [x] Agent 系统
- [x] KAIROS
- [x] BUDDY
- [x] Undercover Mode
- [ ] Web UI
- [ ] VS Code 插件
- [ ] MCP 完整支持
- [ ] 更多 LLM Provider

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- 基于 Claude Code 泄露源码架构设计
- 参考 claw-code 开源实现
- 致敬 Anthropic Claude 团队

---

**免责声明**: 本项目为学习研究目的，与 Anthropic 无关。
