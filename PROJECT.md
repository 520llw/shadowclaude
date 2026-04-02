# Project ShadowClaude - 完整 Claude Code 复刻计划

基于 claw-code 开源架构，补全所有未发布功能，打造最强开源 AI 编程助手。

---

## 🎯 项目目标

**ShadowClaude** = claw-code 开源基础 + Claude Code 泄露源码精华 + 原创增强

### 核心特性
- ✅ 完整工具系统（40+ 工具）
- ✅ 三层记忆系统（Semantic/Episodic/Working）
- ✅ Prompt Cache 分段缓存
- ✅ Coordinator + Swarm 多 Agent 协作
- ✅ KAIROS 守护进程模式
- ✅ BUDDY 赛博宠物系统
- ✅ Undercover Mode 卧底模式
- ✅ 六层权限纵深防御

---

## 🏗️ 技术架构

```
shadowclaude/
├── crates/
│   ├── core/           # 核心运行时 (Rust)
│   ├── tools/          # 工具执行引擎
│   ├── memory/         # 三层记忆系统
│   ├── agents/         # Agent Swarm 协调器
│   ├── kairos/         # 守护进程模式
│   └── mcp/            # MCP 协议支持
├── python/
│   ├── shadowclaude/   # Python 绑定
│   ├── skills/         # Skill 系统
│   └── buddy/          # BUDDY 宠物系统
├── web/
│   └── ui/             # Web UI (React)
└── docs/
    └── architecture/   # 架构文档
```

---

## 📋 开发阶段

### Phase 1: 核心框架 (Week 1)
- [ ] Rust 项目初始化
- [ ] QueryEngine 基础实现
- [ ] 基础工具系统
- [ ] Python FFI 绑定

### Phase 2: 工具与记忆 (Week 2)
- [ ] 40+ 工具完整实现
- [ ] 三层记忆系统
- [ ] Prompt Cache 分段缓存
- [ ] 对话压缩系统

### Phase 3: Agent 系统 (Week 3)
- [ ] Coordinator 协调器
- [ ] Swarm Worker 子代理
- [ ] Agent 类型系统
- [ ] 权限管理

### Phase 4: 未发布功能 (Week 4)
- [ ] KAIROS 守护进程
- [ ] BUDDY 赛博宠物
- [ ] Undercover Mode
- [ ] AutoDream 记忆整合

### Phase 5: 完善与发布 (Week 5)
- [ ] Web UI
- [ ] 文档完善
- [ ] 测试覆盖
- [ ] 开源发布

---

## 🚀 立即开始

先创建项目骨架...
