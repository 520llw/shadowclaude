# ShadowClaude 工具集 - 完整文档

ShadowClaude 现已实现 **40+ 个工具**，完整覆盖 Claude Code 的核心功能。

## 工具分类概览

| 分类 | 工具数量 | 工具名称 |
|------|----------|----------|
| 文件操作 | 7 | read_file, write_file, edit_file, ls, cd, pwd, file_search |
| 搜索工具 | 2 | glob_search, grep_search |
| Web 工具 | 2 | WebFetch, WebSearch |
| Git 工具 | 6 | git_status, git_diff, git_commit, git_push, git_branch, git_log |
| 代码工具 | 5 | lsp, lint, format, code_review, complexity_analysis |
| 网络工具 | 3 | curl, download, upload |
| 数据库工具 | 2 | sql_query, db_migrate |
| 测试工具 | 2 | run_tests, coverage_report |
| 部署工具 | 3 | docker_build, docker_run, ssh_exec |
| 系统工具 | 3 | clipboard, screenshot, notification |
| 其他 | 3 | bash, TodoWrite, Agent, ToolSearch |

---

## 1. 文件操作工具

### read_file
读取文本文件内容。

```python
{
    "path": "/path/to/file.txt",
    "offset": 0,      # 可选：起始行号
    "limit": 100      # 可选：最大读取行数
}
```

### write_file
创建新文件或覆盖现有文件。

```python
{
    "path": "/path/to/file.txt",
    "content": "文件内容"
}
```

### edit_file
精确替换文件中的文本。

```python
{
    "path": "/path/to/file.txt",
    "old_string": "要被替换的文本",
    "new_string": "新的文本",
    "replace_all": false  # 可选：是否替换所有匹配项
}
```

### ls
列出目录内容。

```python
{
    "path": ".",              # 目录路径
    "show_hidden": false,     # 显示隐藏文件
    "recursive": false,       # 递归列出
    "sort_by": "name"         # 排序方式：name, size, mtime, type
}
```

### pwd
显示当前工作目录。

```python
{
    "resolve_symlinks": true  # 是否解析符号链接
}
```

### cd
切换工作目录。

```python
{
    "path": "/new/working/dir",
    "create_if_missing": false  # 不存在时是否创建
}
```

### file_search
高级文件搜索。

```python
{
    "path": ".",
    "name_pattern": "*.py",           # 文件名模式
    "content_pattern": "def main",    # 内容正则
    "file_type": "file",              # file, directory, symlink, any
    "min_size": 1024,                 # 最小文件大小
    "max_size": 1048576,              # 最大文件大小
    "modified_after": "2024-01-01",
    "modified_before": "2024-12-31",
    "exclude_patterns": ["node_modules", ".git"],
    "limit": 100
}
```

---

## 2. 搜索工具

### glob_search
使用 glob 模式查找文件。

```python
{
    "pattern": "**/*.py",
    "path": "./src"
}
```

### grep_search
使用正则表达式搜索文件内容。

```python
{
    "pattern": "import\s+(\w+)",
    "path": "./src",
    "glob": "*.py",
    "output_mode": "lines",   # lines, context, count
    "context": 3,             # 上下文行数
    "head_limit": 20          # 最大结果数
}
```

---

## 3. Web 工具

### WebFetch
获取网页内容。

```python
{
    "url": "https://example.com",
    "prompt": "提取文章标题"
}
```

### WebSearch
搜索网络信息。

```python
{
    "query": "Python 3.12 new features",
    "allowed_domains": ["python.org", "docs.python.org"],
    "blocked_domains": ["spam-site.com"]
}
```

### curl
HTTP 请求工具。

```python
{
    "url": "https://api.example.com/data",
    "method": "POST",
    "headers": {"Authorization": "Bearer token"},
    "json_body": {"key": "value"},
    "timeout": 30
}
```

### download
下载文件。

```python
{
    "url": "https://example.com/file.zip",
    "output": "./downloads/file.zip",
    "resume": true,
    "overwrite": false
}
```

### upload
上传文件。

```python
{
    "url": "https://api.example.com/upload",
    "file": "./data.csv",
    "field_name": "file"
}
```

---

## 4. Git 工具

### git_status
查看工作区状态。

```python
{
    "path": ".",
    "short": false,
    "branch": true
}
```

### git_diff
查看代码差异。

```python
{
    "path": ".",
    "staged": false,
    "from_commit": "HEAD~1",
    "to_commit": "HEAD",
    "stat": true
}
```

### git_commit
提交更改。

```python
{
    "path": ".",
    "message": "Add new feature",
    "all": true,          # 自动 stage 所有修改
    "amend": false        # 修改上一次提交
}
```

### git_push
推送到远程。

```python
{
    "path": ".",
    "remote": "origin",
    "branch": "main",
    "force": false,
    "force_with_lease": false
}
```

### git_branch
分支管理。

```python
{
    "path": ".",
    "action": "create",      # list, create, delete, rename
    "branch_name": "feature/new",
    "from": "main"
}
```

### git_log
查看提交历史。

```python
{
    "path": ".",
    "max_count": 10,
    "oneline": true,
    "graph": true,
    "author": "user@example.com"
}
```

---

## 5. 代码工具

### lsp
语言服务器协议操作。

```python
{
    "operation": "goToDefinition",  # goToDefinition, findReferences, hover, documentSymbol
    "file_path": "/path/to/file.py",
    "line": 42,
    "character": 15
}
```

### lint
代码检查。

```python
{
    "path": "./src",
    "linter": "auto",        # auto, pylint, flake8, ruff, eslint
    "fix": false,            # 自动修复
    "output_format": "text"  # text, json
}
```

### format
代码格式化。

```python
{
    "path": "./src",
    "formatter": "auto",     # auto, black, prettier, clang-format
    "check": false           # 仅检查不修改
}
```

### code_review
自动代码审查。

```python
{
    "path": "./src",
    "focus": ["security", "performance", "maintainability"],
    "severity": "medium",
    "output_format": "markdown"  # text, json, markdown
}
```

### complexity_analysis
复杂度分析。

```python
{
    "path": "./src",
    "metrics": ["cyclomatic", "loc"],
    "threshold": 10,
    "output_format": "table"
}
```

---

## 6. 数据库工具

### sql_query
执行 SQL 查询。

```python
{
    "connection": "./database.db",     # SQLite 文件路径或连接字符串
    "database_type": "sqlite",         # sqlite, postgresql, mysql
    "query": "SELECT * FROM users WHERE id = ?",
    "params": [1],
    "output_format": "table",          # table, json, csv
    "limit": 1000
}
```

### db_migrate
数据库迁移管理。

```python
{
    "connection": "./database.db",
    "action": "create",       # create, up, down, status, history
    "name": "add_users_table",
    "database_type": "sqlite"
}
```

---

## 7. 测试工具

### run_tests
运行测试套件。

```python
{
    "path": "./tests",
    "framework": "auto",      # auto, pytest, unittest, jest, cargo
    "pattern": "test_*.py",
    "coverage": true,
    "verbose": true,
    "fail_fast": false,
    "parallel": false
}
```

### coverage_report
生成覆盖率报告。

```python
{
    "path": "./src",
    "framework": "auto",
    "output_format": "html",   # text, html, json, xml
    "output_dir": "./coverage",
    "fail_under": 80           # 覆盖率低于 80% 则失败
}
```

---

## 8. 部署工具

### docker_build
构建 Docker 镜像。

```python
{
    "path": ".",
    "dockerfile": "Dockerfile",
    "tag": "myapp:latest",
    "build_args": {"VERSION": "1.0.0"},
    "no_cache": false,
    "platform": "linux/amd64",
    "target": "production"    # 多阶段构建目标
}
```

### docker_run
运行 Docker 容器。

```python
{
    "image": "myapp:latest",
    "name": "myapp-container",
    "ports": ["8080:80", "443:443"],
    "volumes": ["./data:/data"],
    "env": {"DATABASE_URL": "postgres://..."},
    "detach": true,
    "rm": false               # 退出后删除容器
}
```

### ssh_exec
SSH 远程执行。

```python
{
    "host": "192.168.1.100",
    "command": "ls -la /var/www",
    "user": "deploy",
    "port": 22,
    "key_file": "~/.ssh/id_rsa",
    "upload_files": [
        {"local": "./app.tar.gz", "remote": "/tmp/app.tar.gz"}
    ]
}
```

---

## 9. 系统工具

### clipboard
剪贴板操作。

```python
{
    "action": "read",      # read, write, clear
    "content": "文本内容"   # write 时必需
}
```

### screenshot
屏幕截图。

```python
{
    "mode": "full",        # full, window, region
    "output": "./screenshot.png",
    "format": "png",
    "delay": 3             # 延迟秒数
}
```

### notification
桌面通知。

```python
{
    "title": "任务完成",
    "message": "代码已部署到生产环境",
    "urgency": "normal",   # low, normal, critical
    "timeout": 5
}
```

---

## 10. 其他工具

### bash
执行 shell 命令。

```python
{
    "command": "ls -la",
    "timeout": 60,
    "description": "List files"
}
```

### TodoWrite
任务管理。

```python
{
    "todos": [
        {"content": "任务1", "status": "in_progress"},
        {"content": "任务2", "status": "pending"}
    ]
}
```

### Agent
创建子 Agent。

```python
{
    "description": "Code review agent",
    "prompt": "Review the code for security issues",
    "subagent_type": "Explore"
}
```

### ToolSearch
搜索可用工具。

```python
{
    "query": "git",
    "max_results": 10
}
```

---

## 快速示例

### 示例 1: 完整的代码审查流程

```python
# 1. 查看当前目录
ls {"path": "."}

# 2. 查找 Python 文件
glob_search {"pattern": "**/*.py"}

# 3. 运行代码检查
lint {"path": "./src", "linter": "ruff", "fix": true}

# 4. 格式化代码
format {"path": "./src", "formatter": "black"}

# 5. 运行测试
run_tests {"path": "./tests", "coverage": true}

# 6. 代码审查
code_review {
    "path": "./src",
    "focus": ["security", "performance"],
    "output_format": "markdown"
}
```

### 示例 2: Git 工作流

```python
# 1. 查看状态
git_status {"path": "."}

# 2. 查看差异
git_diff {"path": ".", "staged": false}

# 3. 提交
git_commit {
    "path": ".",
    "message": "feat: add new feature",
    "all": true
}

# 4. 推送
git_push {
    "path": ".",
    "remote": "origin",
    "branch": "main"
}
```

### 示例 3: Docker 部署

```python
# 1. 构建镜像
docker_build {
    "path": ".",
    "tag": "myapp:v1.0",
    "build_args": {"NODE_ENV": "production"}
}

# 2. 运行容器
docker_run {
    "image": "myapp:v1.0",
    "name": "myapp-prod",
    "ports": ["80:8080"],
    "detach": true,
    "restart": "always"
}
```

---

## 权限级别

| 级别 | 说明 | 对应工具 |
|------|------|----------|
| READ_ONLY | 只读操作 | read_file, ls, grep_search, git_status |
| WORKSPACE_WRITE | 工作区写入 | write_file, edit_file, git_commit, format |
| DANGER_FULL_ACCESS | 危险操作 | bash, ssh_exec, docker_run, sql_query |

---

## 工具统计

- **总工具数**: 40+
- **代码行数**: ~3000+ 行 Python 代码
- **测试覆盖率**: 待补充
- **支持平台**: Linux, macOS, Windows (部分工具)
