# ShadowClaude 性能优化指南

## 概述

本文档介绍如何优化 ShadowClaude 的性能，包括缓存策略、并发优化、内存管理等。

## 缓存优化

### Prompt Cache

Prompt Cache 是 ShadowClaude 最重要的性能优化手段。

#### 工作原理

```
用户查询 → 分段 → 哈希计算 → 缓存查找 → 命中则复用/未命中则生成
```

#### 配置

```yaml
cache:
  enabled: true
  strategy: "segmented"  # segmented, full, or hybrid
  segments:
    system_prompt:
      ttl: 86400  # 24 hours
      max_size: "10MB"
    tools_definition:
      ttl: 3600   # 1 hour
      max_size: "5MB"
    history_context:
      ttl: 600    # 10 minutes
      max_size: "50MB"
```

#### 命中率优化

1. **稳定的系统提示**: 减少系统提示的变化
2. **工具定义缓存**: 工具定义变化不频繁
3. **上下文压缩**: 减少历史上下文的变化

### 文件缓存

```yaml
cache:
  file:
    enabled: true
    max_size: "100MB"
    ttl: 300  # 5 minutes
    patterns:
      - "*.md"
      - "*.py"
      - "*.rs"
```

### 向量缓存

```python
# 配置向量缓存
memory.configure_cache(
    embedding_cache_size=10000,
    search_result_cache_size=1000
)
```

## 并发优化

### 异步处理

```python
# 使用异步 API
async def process_queries(queries):
    tasks = [
        client.query_async(q)
        for q in queries
    ]
    return await asyncio.gather(*tasks)
```

### 并行工具执行

```python
# 配置并行度
client.configure(
    max_concurrent_tools=5
)

# 批量执行
results = await client.execute_tools_batch([
    {"tool": "read_file", "args": {...}},
    {"tool": "search", "args": {...}},
])
```

### 线程池

```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

# 提交任务
futures = [
    executor.submit(client.query, q)
    for q in queries
]
results = [f.result() for f in futures]
```

## 内存优化

### 工作记忆限制

```yaml
memory:
  working:
    max_tokens: 4000
    compression_threshold: 0.8
    eviction_policy: "lru"
```

### 自动压缩

```python
# 配置压缩策略
memory.configure_compression(
    strategy="importance",
    target_ratio=0.5
)
```

### 内存监控

```python
# 获取内存使用
stats = memory.get_stats()
print(f"Semantic: {stats.semantic_size}MB")
print(f"Episodic: {stats.episodic_size}MB")
print(f"Working: {stats.working_size}MB")
```

## LLM 优化

### 模型选择

| 模型 | 速度 | 质量 | 成本 | 适用场景 |
|------|------|------|------|----------|
| claude-3-opus | 慢 | 最高 | 高 | 复杂任务 |
| claude-3-sonnet | 中 | 高 | 中 | 一般任务 |
| claude-3-haiku | 快 | 中 | 低 | 简单任务 |

```yaml
llm:
  model: claude-3-sonnet  # 平衡选择
  fallback_model: claude-3-haiku
```

### 参数调优

```yaml
llm:
  temperature: 0.7  # 创意 vs 确定性
  max_tokens: 2000  # 响应长度限制
  top_p: 0.9        # 采样多样性
```

### 流式输出

```python
# 使用流式响应减少等待时间
async for chunk in client.query_stream("..."):
    process_chunk(chunk)
```

## 批处理优化

### 智能批处理

```python
# 自动批处理相似请求
batch_processor = client.create_batch_processor(
    batch_size=10,
    max_latency_ms=100
)

# 提交任务
result = await batch_processor.submit(query)
```

### 预加载

```python
# 预加载常用提示
client.preload_prompts([
    "code_explanation_template",
    "bug_fix_template",
])
```

## 数据库优化

### Qdrant 优化

```yaml
memory:
  semantic:
    indexing:
      on_disk: true
      hnsw:
        m: 16
        ef_construct: 100
```

### Neo4j 优化

```yaml
memory:
  episodic:
    indexes:
      - "CREATE INDEX ON :Event(timestamp)"
      - "CREATE INDEX ON :Entity(name)"
```

### Redis 优化

```yaml
memory:
  working:
    redis:
      maxmemory: "256mb"
      maxmemory_policy: "allkeys-lru"
```

## 网络优化

### 连接池

```python
# 配置 HTTP 连接池
client.configure_http(
    pool_connections=20,
    pool_maxsize=50
)
```

### 请求压缩

```yaml
http:
  compression: true
  compress_threshold: "1KB"
```

### 重试策略

```yaml
http:
  retries:
    total: 3
    backoff_factor: 0.3
    status_forcelist: [500, 502, 503, 504]
```

## 监控和诊断

### 性能指标

```python
# 收集指标
metrics = client.collect_metrics(duration=60)

# 关键指标
print(f"Query latency: {metrics.query_latency}ms")
print(f"Cache hit rate: {metrics.cache_hit_rate}%")
print(f"Tool execution time: {metrics.tool_time}ms")
print(f"LLM tokens/sec: {metrics.tokens_per_sec}")
```

### 慢查询分析

```python
# 识别慢查询
slow_queries = client.analyze_slow_queries(
    threshold_ms=1000
)

for query in slow_queries:
    print(f"Slow query: {query.text}")
    print(f"Time: {query.duration}ms")
    print(f"Bottleneck: {query.bottleneck}")
```

### 性能剖析

```bash
# 使用 cProfile
python -m cProfile -o profile.stats main.py

# 使用 py-spy
py-spy record -o profile.svg -- python main.py
```

## 最佳实践

### 1. 合理使用缓存

- 对稳定内容启用缓存
- 设置合适的 TTL
- 监控缓存命中率

### 2. 优化 Prompt

- 减少不必要的上下文
- 使用简洁的指令
- 避免重复信息

### 3. 批量处理

- 合并相似请求
- 使用批处理 API
- 异步执行独立任务

### 4. 资源限制

- 设置内存上限
- 限制并发数
- 监控资源使用

### 5. 选择合适的模型

- 简单任务用轻量级模型
- 复杂任务用强大模型
- 考虑成本和速度平衡

## 性能测试

### 基准测试

```python
import time
import statistics

def benchmark_query(query, n=100):
    times = []
    for _ in range(n):
        start = time.time()
        client.query(query)
        times.append(time.time() - start)
    
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times),
        "min": min(times),
        "max": max(times),
    }
```

### 负载测试

```bash
# 使用 locust
locust -f load_test.py --host=http://localhost:8080
```

### 性能目标

| 指标 | 目标 | 优秀 |
|------|------|------|
| 查询延迟 | < 500ms | < 200ms |
| 流式首字节 | < 100ms | < 50ms |
| 缓存命中率 | > 60% | > 80% |
| 内存使用 | < 500MB | < 200MB |

---

*优化指南版本: 1.0.0 | 最后更新: 2026-04-02*
