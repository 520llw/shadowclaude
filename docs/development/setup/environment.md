# ShadowClaude 开发环境搭建

本文档指导开发者搭建 ShadowClaude 的开发环境。

## 目录

1. [环境要求](#环境要求)
2. [获取源码](#获取源码)
3. [Rust 环境](#rust-环境)
4. [Python 环境](#python-环境)
5. [数据库设置](#数据库设置)
6. [构建项目](#构建项目)
7. [运行测试](#运行测试)
8. [IDE 配置](#ide-配置)

---

## 环境要求

### 必需

- **Rust**: 1.75.0 或更高版本
- **Python**: 3.9 或更高版本（用于 Python 绑定）
- **Git**: 2.30 或更高版本

### 推荐

- **Docker**: 用于运行数据库服务
- **Node.js**: 18+（用于 Web UI 开发）

---

## 获取源码

```bash
# 克隆仓库
git clone https://github.com/shadowclaude/shadowclaude.git
cd shadowclaude

# 初始化子模块（如有）
git submodule update --init --recursive
```

---

## Rust 环境

### 安装 Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 安装工具链组件

```bash
# 安装 nightly 工具链（用于某些特性）
rustup toolchain install nightly

# 安装组件
rustup component add rustfmt clippy

# 安装有用工具
cargo install cargo-watch cargo-expand cargo-edit
```

### 验证安装

```bash
rustc --version
cargo --version
```

---

## Python 环境

### 创建虚拟环境

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 安装 Python 依赖

```bash
cd python
pip install -e ".[dev]"
```

### 安装 maturin（用于构建 Rust 扩展）

```bash
pip install maturin
```

---

## 数据库设置

### 使用 Docker（推荐）

```bash
# 启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 服务包括：
# - Qdrant (向量数据库): localhost:6333
# - Neo4j (图数据库): localhost:7687
# - Redis (缓存): localhost:6379
```

### 手动安装

#### Qdrant

```bash
docker run -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

#### Neo4j

```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

#### Redis

```bash
docker run -p 6379:6379 redis:latest
```

---

## 构建项目

### 完整构建

```bash
# 构建所有 Rust 组件
cargo build --release

# 构建 Python 扩展
cd python && maturin develop
```

### 开发构建

```bash
# 快速构建（无优化）
cargo build

# 热重载开发
cargo watch -x run
```

### 构建特定组件

```bash
# 仅构建 core
cargo build -p shadowclaude-core

# 仅构建 tools
cargo build -p shadowclaude-tools
```

---

## 运行测试

### Rust 测试

```bash
# 运行所有测试
cargo test

# 运行特定测试
cargo test query_engine

# 包含集成测试
cargo test --all-features

# 生成覆盖率报告
cargo tarpaulin --out Html
```

### Python 测试

```bash
cd python
pytest

# 带覆盖率
pytest --cov=shadowclaude --cov-report=html
```

### 端到端测试

```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行 E2E 测试
cargo test --test e2e
```

---

## IDE 配置

### VS Code

推荐扩展：

```json
{
  "recommendations": [
    "rust-lang.rust-analyzer",
    "serayuzgur.crates",
    "vadimcn.vscode-lldb",
    "ms-python.python",
    "ms-python.black-formatter"
  ]
}
```

设置 `.vscode/settings.json`：

```json
{
  "rust-analyzer.cargo.features": "all",
  "rust-analyzer.checkOnSave.command": "clippy",
  "python.formatting.provider": "black",
  "python.linting.enabled": true
}
```

### JetBrains (RustRover/CLion)

1. 安装 Rust 插件
2. 配置工具链：Settings → Languages & Frameworks → Rust
3. 设置运行配置

### Vim/Neovim

推荐配置：

```lua
-- Using lazy.nvim
{
  'mrcjkb/rustaceanvim',
  ft = 'rust',
  config = function()
    -- 配置 LSP
  end
}
```

---

## 开发工作流

### 常用命令

```bash
# 格式化代码
cargo fmt

# 运行 clippy
cargo clippy --all-targets --all-features

# 生成文档
cargo doc --open

# 检查依赖
cargo tree
cargo outdated

# 安全审计
cargo audit
```

### Git 工作流

```bash
# 创建功能分支
git checkout -b feature/my-feature

# 提交更改
git add .
git commit -m "feat: add new feature"

# 推送分支
git push origin feature/my-feature

# 创建 Pull Request
gh pr create --title "Add new feature" --body "..."
```

---

## 调试

### Rust 调试

```bash
# 使用 cargo 运行
cargo run --bin shadowclaude -- --verbose

# 使用 LLDB
cargo build
debugger target/debug/shadowclaude
```

### Python 调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用调试器
python -m pdb -m shadowclaude
```

---

## 常见问题

### 编译错误

```bash
# 清理并重建
cargo clean
cargo build

# 更新依赖
cargo update
```

### 链接错误

```bash
# macOS: 安装 Xcode 命令行工具
xcode-select --install

# Linux: 安装开发库
sudo apt install build-essential libssl-dev pkg-config
```

### Python 绑定失败

```bash
# 重新安装 maturin
pip uninstall maturin
pip install maturin

# 重新构建
cd python
maturin develop --release
```

---

## 下一步

- [代码规范](./code-style.md)
- [贡献指南](./contributing.md)
- [架构文档](../architecture/system-design.md)

---

*文档版本: 1.0.0 | 最后更新: 2026-04-02*
