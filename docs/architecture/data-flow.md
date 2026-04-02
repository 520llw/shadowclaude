# ShadowClaude 数据流图

本文档详细描述 ShadowClaude 系统中数据的流动路径和处理过程。

## 目录

1. [用户查询数据流](#用户查询数据流)
2. [记忆存储数据流](#记忆存储数据流)
3. [工具执行数据流](#工具执行数据流)
4. [Agent 协作数据流](#agent-协作数据流)
5. [缓存系统数据流](#缓存系统数据流)

---

## 用户查询数据流

### 标准查询流程

```mermaid
flowchart TD
    A[用户输入] --> B{输入类型}
    B -->|文本| C[自然语言处理]
    B -->|命令| D[命令解析器]
    B -->|代码| E[代码分析器]
    
    C --> F[意图识别]
    D --> F
    E --> F
    
    F --> G[QueryEngine]
    G --> H[上下文构建]
    
    H --> I[记忆检索]
    I --> J{找到相关记忆?}
    J -->|是| K[注入记忆]
    J -->|否| L[继续处理]
    
    K --> M[Prompt 构建]
    L --> M
    
    M --> N{Prompt 缓存?}
    N -->|命中| O[使用缓存]
    N -->|未命中| P[发送到 LLM]
    
    O --> Q[生成响应]
    P --> Q
    
    Q --> R{需要工具?}
    R -->|是| S[工具编排]
    R -->|否| T[直接返回]
    
    S --> U[执行工具]
    U --> V[工具结果处理]
    V --> W[重新生成响应]
    W --> T
    
    T --> X[记忆存储]
    X --> Y[返回用户]
```

### 数据转换过程

```mermaid
flowchart LR
    subgraph "输入层"
        A[原始输入<br/>string]
    end
    
    subgraph "处理层"
        B[Tokenized<br/>Vec<Token>]
        C[结构化数据<br/>InputIntent]
        D[Embedding<br/>Vec<f32>]
    end
    
    subgraph "输出层"
        E[LLM Response<br/>string]
        F[结构化输出<br/>ActionPlan]
        G[最终响应<br/>Response]
    end
    
    A -->|Tokenizer| B
    B -->|Parser| C
    C -->|Embedder| D
    D -->|Prompt Builder| E
    E -->|Output Parser| F
    F -->|Formatter| G
```

---

## 记忆存储数据流

### 三层记忆存储流程

```mermaid
flowchart TD
    A[对话/事件] --> B{记忆分类器}
    
    B -->|事实/知识| C[语义记忆]
    B -->|事件/经验| D[情景记忆]
    B -->|临时上下文| E[工作记忆]
    
    subgraph "语义记忆处理"
        C --> F[内容提取]
        F --> G[Embedding]
        G --> H[元数据标注]
        H --> I[(Vector DB)]
    end
    
    subgraph "情景记忆处理"
        D --> J[事件提取]
        J --> K[关系构建]
        K --> L[时序标注]
        L --> M[(Graph DB)]
    end
    
    subgraph "工作记忆处理"
        E --> N[Token 计数]
        N --> O{超过限制?}
        O -->|是| P[压缩/淘汰]
        O -->|否| Q[直接存储]
        P --> R[(Redis)]
        Q --> R
    end
```

### 记忆检索流程

```mermaid
flowchart TD
    A[查询请求] --> B[查询分析]
    B --> C[生成 Embedding]
    
    C --> D[并行检索]
    
    subgraph "并行检索"
        D --> E[语义记忆检索]
        D --> F[情景记忆检索]
        D --> G[工作记忆检索]
    end
    
    E --> H[向量相似度搜索]
    F --> I[图遍历查询]
    G --> J[缓存读取]
    
    H --> K[结果聚合]
    I --> K
    J --> K
    
    K --> L[重排序]
    L --> M[去重过滤]
    M --> N[结果格式化]
    N --> O[返回上下文]
```

### 记忆同步流程

```mermaid
sequenceDiagram
    participant WM as Working Memory
    participant EM as Episodic Memory
    participant SM as Semantic Memory
    participant Auto as AutoDream

    WM->>WM: 定期压缩
    WM->>EM: 重要事件同步
    EM->>SM: 模式提取
    
    Auto->>WM: 读取短期记忆
    Auto->>EM: 读取情景记忆
    Auto->>Auto: 梦境整合
    Auto->>SM: 知识固化
```

---

## 工具执行数据流

### 工具调用流程

```mermaid
flowchart TD
    A[LLM 工具调用请求] --> B[参数验证]
    B --> C{验证通过?}
    C -->|否| D[返回错误]
    C -->|是| E[权限检查]
    
    E --> F{需要授权?}
    F -->|是| G[请求用户确认]
    F -->|否| H[查找工具]
    
    G --> I{用户确认?}
    I -->|否| J[拒绝执行]
    I -->|是| H
    
    H --> K[工具执行]
    K --> L[沙箱运行]
    L --> M[结果捕获]
    M --> N[结果格式化]
    N --> O[返回 LLM]
    
    D --> P[错误处理]
    J --> P
```

### 工具结果处理流程

```mermaid
flowchart LR
    A[原始输出<br/>string/bytes] --> B{输出类型}
    
    B -->|文本| C[文本清理]
    B -->|JSON| D[JSON 解析]
    B -->|二进制| E[Base64 编码]
    B -->|错误| F[错误提取]
    
    C --> G[截断/摘要]
    D --> H[结构化转换]
    E --> I[文件引用]
    F --> J[错误分类]
    
    G --> K[ToolResult]
    H --> K
    I --> K
    J --> K
    
    K --> L[LLM Context]
```

### 批量工具执行流程

```mermaid
flowchart TD
    A[多个工具调用] --> B[依赖分析]
    B --> C[构建 DAG]
    C --> D[拓扑排序]
    
    D --> E{并行可能?}
    E -->|是| F[并行执行]
    E -->|否| G[串行执行]
    
    subgraph "并行执行"
        F --> H[Worker Pool]
        H --> I[Tool 1]
        H --> J[Tool 2]
        H --> K[Tool N]
    end
    
    I --> L[结果合并]
    J --> L
    K --> L
    G --> L
    
    L --> M[按序返回]
```

---

## Agent 协作数据流

### 多 Agent 任务分配

```mermaid
flowchart TD
    A[复杂任务] --> B[Coordinator]
    B --> C[任务分解]
    C --> D[子任务 1]
    C --> E[子任务 2]
    C --> F[子任务 3]
    
    D --> G{Agent 选择}
    E --> H{Agent 选择}
    F --> I{Agent 选择}
    
    G -->|代码任务| J[Code Agent]
    H -->|文件任务| K[File Agent]
    I -->|分析任务| L[Analyzer Agent]
    
    subgraph "并行执行"
        J --> M[结果收集]
        K --> M
        L --> M
    end
    
    M --> N[结果整合]
    N --> O[质量检查]
    O --> P{通过?}
    P -->|否| Q[重新分配]
    Q --> G
    P -->|是| R[最终输出]
```

### Agent 间通信

```mermaid
sequenceDiagram
    participant Coord as Coordinator
    participant A1 as Agent 1
    participant Bus as Message Bus
    participant A2 as Agent 2
    participant A3 as Agent 3

    Coord->>A1: 分配任务
    A1->>Bus: 发布中间结果
    
    Bus->>A2: 订阅相关消息
    Bus->>A3: 订阅相关消息
    
    A2->>A2: 处理依赖数据
    A3->>A3: 处理依赖数据
    
    A2->>Bus: 发布结果
    A3->>Bus: 发布结果
    
    Bus->>Coord: 收集结果
    Coord->>Coord: 整合输出
```

---

## 缓存系统数据流

### 多级缓存查询

```mermaid
flowchart TD
    A[数据请求] --> B{L1 Cache?}
    B -->|命中| C[返回数据]
    B -->|未命中| D{L2 Cache?}
    
    D -->|命中| E[更新 L1]
    D -->|未命中| F{L3 Cache?}
    
    F -->|命中| G[更新 L2/L1]
    F -->|未命中| H[从源获取]
    
    H --> I[更新所有缓存层]
    E --> C
    G --> C
    I --> C
```

### Prompt 缓存流程

```mermaid
flowchart TD
    A[Prompt 构建] --> B[分段处理]
    
    subgraph "分段缓存"
        B --> C[System Prompt]
        B --> D[Tools Definition]
        B --> E[History Context]
        B --> F[Current Query]
    end
    
    C --> G{缓存?}
    D --> H{缓存?}
    E --> I{缓存?}
    
    G -->|是| J[使用缓存 ID]
    G -->|否| K[计算 Hash]
    
    H -->|是| L[使用缓存 ID]
    H -->|否| M[计算 Hash]
    
    I -->|是| N[使用缓存 ID]
    I -->|否| O[计算 Hash]
    
    J --> P[组装完整 Prompt]
    L --> P
    N --> P
    K --> P
    M --> P
    O --> P
    
    P --> Q[发送到 LLM]
```

### 缓存失效策略

```mermaid
flowchart TD
    A[数据变更事件] --> B{变更类型}
    
    B -->|文件修改| C[文件缓存]
    B -->|配置更新| D[配置缓存]
    B -->|记忆更新| E[记忆缓存]
    B -->|工具更新| F[工具缓存]
    
    C --> G[清除相关缓存]
    D --> H[清除配置缓存]
    E --> I[清除记忆缓存]
    F --> J[清除工具缓存]
    
    G --> K[通知订阅者]
    H --> K
    I --> K
    J --> K
    
    K --> L[刷新缓存]
```

---

## WebSocket 实时数据流

### 实时通信流程

```mermaid
sequenceDiagram
    participant Client as Web Client
    participant WS as WebSocket Server
    participant QE as QueryEngine
    participant LLM as LLM Provider

    Client->>WS: 建立连接
    WS->>QE: 初始化会话
    
    Client->>WS: 发送查询
    WS->>QE: 处理查询
    
    loop 流式响应
        QE->>LLM: 请求生成
        LLM-->>QE: 流式返回
        QE-->>WS: 转发 token
        WS-->>Client: 实时显示
    end
    
    QE-->>WS: 完成信号
    WS-->>Client: 结束标记
```

---

## 数据持久化流

### 会话持久化

```mermaid
flowchart TD
    A[会话数据] --> B{持久化策略}
    
    B -->|实时| C[同步写入]
    B -->|批量| D[缓冲写入]
    B -->|延迟| E[定时写入]
    
    C --> F[WAL Log]
    D --> G[批量提交]
    E --> H[定时任务]
    
    F --> I[(SQLite/PostgreSQL)]
    G --> I
    H --> I
    
    I --> J[索引更新]
    J --> K[备份同步]
```

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
