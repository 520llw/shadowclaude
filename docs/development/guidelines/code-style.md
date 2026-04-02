# ShadowClaude 代码规范

本文档定义 ShadowClaude 项目的代码规范和质量标准。

## 目录

1. [Rust 规范](#rust-规范)
2. [Python 规范](#python-规范)
3. [文档规范](#文档规范)
4. [测试规范](#测试规范)
5. [提交规范](#提交规范)

---

## Rust 规范

### 代码格式

使用 `rustfmt` 自动格式化：

```bash
cargo fmt
```

配置 `.rustfmt.toml`：

```toml
edition = "2021"
max_width = 100
tab_spaces = 4
```

### 命名规范

| 项目 | 规范 | 示例 |
|------|------|------|
| 结构体/枚举 | PascalCase | `QueryEngine`, `ResponseType` |
| 函数/方法 | snake_case | `process_query`, `get_result` |
| 常量 | SCREAMING_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 模块 | snake_case | `query_engine`, `tool_registry` |
| 特征 | PascalCase | `Tool`, `Agent` |
| 生命周期 | 短名称 | `'a`, `'ctx` |
| 泛型参数 | 描述性 | `T`, `E`, `K`, `V` |

### 代码组织

```rust
// 文件结构示例: src/query_engine.rs

// 1. 导入
use std::collections::HashMap;
use crate::config::Config;

// 2. 常量
const DEFAULT_TIMEOUT: u64 = 30;

// 3. 类型定义
type QueryId = String;

// 4. 结构体定义
pub struct QueryEngine {
    config: Config,
    // ...
}

// 5. 实现块
impl QueryEngine {
    // 构造函数
    pub fn new(config: Config) -> Self {
        Self { config }
    }
    
    // 公共方法
    pub async fn process(&self, query: Query) -> Result<Response> {
        // ...
    }
    
    // 私有方法
    fn validate(&self, query: &Query) -> Result<()> {
        // ...
    }
}

// 6. 特征实现
impl Default for QueryEngine {
    fn default() -> Self {
        // ...
    }
}

// 7. 测试模块
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_query_engine() {
        // ...
    }
}
```

### 错误处理

```rust
// 使用 Result 类型
use anyhow::{Result, Context};

pub fn read_file(path: &Path) -> Result<String> {
    std::fs::read_to_string(path)
        .with_context(|| format!("Failed to read file: {}", path.display()))
}

// 自定义错误类型
#[derive(Debug, thiserror::Error)]
pub enum ShadowClaudeError {
    #[error("Configuration error: {0}")]
    Config(String),
    
    #[error("LLM API error: {status} - {message}")]
    Llm { status: u16, message: String },
    
    #[error(transparent)]
    Io(#[from] std::io::Error),
}
```

### 文档注释

```rust
/// 处理用户查询。
///
/// # Arguments
///
/// * `query` - 用户查询字符串
/// * `context` - 可选的上下文信息
///
/// # Returns
///
/// 返回 `Response` 或错误。
///
/// # Examples
///
/// ```
/// let engine = QueryEngine::new(config);
/// let response = engine.process("Hello").await?;
/// ```
///
/// # Errors
///
/// 当 LLM API 不可用时返回错误。
pub async fn process(&self, query: &str) -> Result<Response> {
    // ...
}
```

### Clippy 规则

启用所有警告：

```bash
cargo clippy --all-targets --all-features -- -D warnings
```

---

## Python 规范

### 代码格式

使用 `black` 和 `isort`：

```bash
black shadowclaude/
isort shadowclaude/
```

配置 `pyproject.toml`：

```toml
[tool.black]
line-length = 100
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 100
```

### 命名规范

| 项目 | 规范 | 示例 |
|------|------|------|
| 类 | PascalCase | `QueryEngine`, `MemoryManager` |
| 函数/变量 | snake_case | `process_query`, `memory_id` |
| 常量 | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| 私有 | 下划线前缀 | `_internal_func` |
| 模块 | 小写 | `query_engine.py` |
| 包 | 小写 | `shadowclaude` |

### 类型注解

```python
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class Query:
    content: str
    context: Optional[Dict[str, Any]] = None

class QueryEngine:
    def __init__(self, config: Config) -> None:
        self.config = config
    
    async def process(
        self,
        query: str,
        stream: bool = False
    ) -> Union[Response, AsyncIterator[Chunk]]:
        ...
```

### 文档字符串

使用 Google 风格：

```python
def process_query(query: str, context: Optional[dict] = None) -> Response:
    """Process a user query.
    
    Args:
        query: The user query string.
        context: Optional context information.
    
    Returns:
        A Response object containing the result.
    
    Raises:
        QueryError: If the query cannot be processed.
    
    Example:
        >>> response = engine.process_query("Hello")
        >>> print(response.content)
        "Hi there!"
    """
    ...
```

---

## 文档规范

### Markdown 规范

- 使用 ATX 风格的标题 (`#`)
- 代码块标注语言
- 表格对齐
- 使用 `-` 作为列表标记

### API 文档

```markdown
## 函数名

简短描述。

### 签名

```python
def function_name(param1: type, param2: type) -> return_type
```

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| param1 | `type` | - | 描述 |

### 返回

- `type`: 描述

### 示例

```python
result = function_name("value")
```
```

---

## 测试规范

### Rust 测试

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    // 单元测试
    #[test]
    fn test_add() {
        assert_eq!(add(2, 2), 4);
    }
    
    // 异步测试
    #[tokio::test]
    async fn test_async() {
        let result = async_function().await;
        assert!(result.is_ok());
    }
    
    // 集成测试标记
    #[test]
    #[ignore = "requires database"]
    fn test_integration() {
        // ...
    }
}
```

### Python 测试

```python
import pytest
from unittest.mock import Mock, patch

class TestQueryEngine:
    @pytest.fixture
    def engine(self):
        return QueryEngine(Config.default())
    
    def test_simple_query(self, engine):
        result = engine.process("test")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_async_query(self, engine):
        result = await engine.process_async("test")
        assert result.content == "expected"
    
    @pytest.mark.integration
    def test_with_llm(self, engine):
        # 需要 LLM API 的测试
        ...
```

### 测试覆盖率

- 单元测试覆盖率 > 80%
- 核心模块覆盖率 > 90%

---

## 提交规范

使用 Conventional Commits：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 |
| `docs` | 文档 |
| `style` | 格式（不影响代码运行）|
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试 |
| `chore` | 构建/工具 |

### 示例

```
feat(memory): add semantic memory support

Implement vector-based semantic memory using Qdrant.
Supports embedding generation and similarity search.

Closes #123
```

```
fix(tools): resolve file permission check

The permission check was incorrectly denying access to files
in the workspace root.

Fixes #456
```

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
