# ShadowClaude 模块依赖图

本文档详细描述 ShadowClaude 各模块之间的依赖关系和交互方式。

## 总体依赖图

```mermaid
graph TB
    subgraph "Rust Core"
        core[shadowclaude-core]
        tools[shadowclaude-tools]
        memory[shadowclaude-memory]
        agents[shadowclaude-agents]
        kairos[shadowclaude-kairos]
        mcp[shadowclaude-mcp]
    end

    subgraph "Python Bindings"
        py[shadowclaude]
        skills[skills]
        buddy_py[buddy]
    end

    subgraph "Web Layer"
        web[shadowclaude-web]
        ui[React UI]
    end

    subgraph "External"
        llm[LLM APIs]
        vdb[Vector DB]
        gdb[Graph DB]
    end

    %% Rust 内部依赖
    core --> tools
    core --> memory
    core --> agents
    core --> kairos
    core --> mcp
    
    agents --> tools
    agents --> memory
    kairos --> agents
    mcp --> tools
    
    %% Python 依赖
    py -->|PyO3| core
    skills --> py
    buddy_py --> py
    
    %% Web 依赖
    web -->|HTTP| core
    ui -->|REST| web
    
    %% External
    core --> llm
    memory --> vdb
    memory --> gdb
```

## 核心模块依赖

### shadowclaude-core

```mermaid
graph LR
    core[shadowclaude-core]
    
    subgraph "Dependencies"
        tokio[tokio]
        serde[serde]
        tracing[tracing]
        anyhow[anyhow]
        reqwest[reqwest]
    end
    
    subgraph "Dependent Modules"
        tools[tools]
        memory[memory]
        agents[agents]
        kairos[kairos]
        mcp[mcp]
    end
    
    tokio --> core
    serde --> core
    tracing --> core
    anyhow --> core
    reqwest --> core
    
    core --> tools
    core --> memory
    core --> agents
    core --> kairos
    core --> mcp
```

### 依赖详情

| 模块 | 上游依赖 | 下游被依赖 |
|------|----------|------------|
| core | tokio, serde, tracing | tools, memory, agents, kairos, mcp, python |
| tools | core, regex, walkdir | agents, mcp |
| memory | core, qdrant-client, neo4rs | agents |
| agents | core, tools, memory | kairos, python |
| kairos | core, agents, notify | python |
| mcp | core, tools, serde_json | - |

## Python 绑定依赖

```mermaid
graph TB
    py[shadowclaude Python]
    
    subgraph "Internal"
        core_lib[core Rust lib]
        query[query_engine]
        config[config]
    end
    
    subgraph "Extensions"
        skills[skills module]
        buddy[buddy module]
        undercover[undercover module]
    end
    
    subgraph "External Python"
        pydantic[pydantic]
        fastapi[fastapi]
        httpx[httpx]
    end
    
    core_lib --> py
    query --> py
    config --> py
    
    py --> skills
    py --> buddy
    py --> undercover
    
    pydantic --> py
    fastapi --> py
    httpx --> py
```

## Web 层依赖

```mermaid
graph LR
    web[shadowclaude-web]
    
    subgraph "Backend"
        axum[axum]
        ws[tokio-tungstenite]
        tower[tower-http]
    end
    
    subgraph "Frontend"
        react[React]
        ts[TypeScript]
        tailwind[TailwindCSS]
    end
    
    axum --> web
    ws --> web
    tower --> web
    
    web -->|API| react
    react --> ts
    react --> tailwind
```

## 开发依赖图

```mermaid
graph TB
    subgraph "Development Tools"
        cargo[cargo]
        pytest[pytest]
        eslint[eslint]
    end
    
    subgraph "Testing"
        unit[Unit Tests]
        integration[Integration Tests]
        e2e[E2E Tests]
    end
    
    subgraph "CI/CD"
        github[GitHub Actions]
        docker[Docker]
        k8s[Kubernetes]
    end
    
    cargo --> unit
    pytest --> unit
    pytest --> integration
    
    unit --> github
    integration --> github
    e2e --> github
    
    github --> docker
    docker --> k8s
```

## 功能模块关系

### 记忆系统内部依赖

```mermaid
graph TB
    subgraph "Memory System"
        sm[Semantic Memory]
        em[Episodic Memory]
        wm[Working Memory]
        mm[Memory Manager]
    end
    
    subgraph "Storage"
        vdb[(Vector DB)]
        gdb[(Graph DB)]
        redis[(Redis)]
    end
    
    mm --> sm
    mm --> em
    mm --> wm
    
    sm --> vdb
    em --> gdb
    wm --> redis
```

### Agent 系统依赖

```mermaid
graph TB
    subgraph "Agent System"
        coord[Coordinator]
        swarm[Swarm Manager]
        agent1[Code Agent]
        agent2[File Agent]
        agent3[Web Agent]
    end
    
    subgraph "Shared Resources"
        tools[Tool Registry]
        memory[Memory System]
        cache[Prompt Cache]
    end
    
    coord --> swarm
    swarm --> agent1
    swarm --> agent2
    swarm --> agent3
    
    agent1 --> tools
    agent1 --> memory
    agent2 --> tools
    agent2 --> memory
    agent3 --> tools
    agent3 --> memory
    
    coord --> cache
```

### BUDDY 系统依赖

```mermaid
graph TB
    subgraph "BUDDY System"
        buddy[BUDDY Core]
        emotion[Emotion Engine]
        growth[Growth System]
        memory[Buddy Memory]
    end
    
    subgraph "Extensions"
        voice[Voice Module]
        avatar[Avatar Module]
        chat[Chat Module]
    end
    
    buddy --> emotion
    buddy --> growth
    buddy --> memory
    
    buddy --> voice
    buddy --> avatar
    buddy --> chat
    
    emotion --> chat
    memory --> chat
```

## 构建依赖

### Cargo.toml 依赖关系

```mermaid
flowchart TB
    subgraph "Workspace Root"
        workspace[Cargo.toml<br/>workspace.members]
    end
    
    subgraph "Crates"
        core[Cargo.toml<br/>shadowclaude-core]
        tools[Cargo.toml<br/>shadowclaude-tools]
        memory[Cargo.toml<br/>shadowclaude-memory]
        agents[Cargo.toml<br/>shadowclaude-agents]
        kairos[Cargo.toml<br/>shadowclaude-kairos]
        mcp[Cargo.toml<br/>shadowclaude-mcp]
    end
    
    workspace --> core
    workspace --> tools
    workspace --> memory
    workspace --> agents
    workspace --> kairos
    workspace --> mcp
    
    core -. optional .> tools
    core -. optional .> memory
    agents --> core
    agents --> tools
    agents --> memory
    kairos --> core
    kairos --> agents
```

### Python setup.py 依赖

```mermaid
flowchart LR
    setup[setup.py] --> install[
        install_requires:
        - pydantic>=2.0
        - httpx>=0.24
        - typer>=0.9
    ]
    
    setup --> extra[
        extras_require:
        - web: fastapi, uvicorn
        - dev: pytest, black, mypy
    ]
    
    install --> runtime[Runtime Dependencies]
    extra --> optional[Optional Dependencies]
```

## 版本兼容性矩阵

| 模块 | Rust 版本 | Python 版本 | 兼容性 |
|------|-----------|-------------|--------|
| core | >= 1.75 | - | ✅ Stable |
| tools | >= 1.75 | - | ✅ Stable |
| memory | >= 1.75 | - | ✅ Stable |
| agents | >= 1.75 | >= 3.9 | ✅ Stable |
| kairos | >= 1.75 | >= 3.9 | ✅ Stable |
| mcp | >= 1.75 | >= 3.9 | ✅ Stable |
| python | - | >= 3.9 | ✅ Stable |

## 依赖升级策略

1. **核心依赖**: tokio, serde 等基础库跟随最新稳定版本
2. **功能依赖**: qdrant-client, neo4rs 等功能库每季度评估升级
3. **Python 依赖**: 遵循语义化版本，小版本自动升级
4. **安全更新**: 关键安全漏洞 24 小时内修复

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
