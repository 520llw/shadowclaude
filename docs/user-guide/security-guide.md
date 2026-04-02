# ShadowClaude 安全指南

## 概述

ShadowClaude 采用多层安全架构，保护用户代码和数据安全。

## 六层权限防御

### 第1层: 用户授权

所有敏感操作都需要用户显式授权。

```
ShadowClaude wants to:
• Delete file: temp.txt

Allow? [y/N] y
```

配置自动授权（谨慎使用）：

```yaml
permissions:
  auto_approve:
    - read_file
    - search_files
  require_approval:
    - write_file
    - bash
    - delete_file
```

### 第2层: 进程隔离

工具在隔离的沙箱中执行。

```rust
// 使用 Linux namespaces
unshare(CloneFlags::NEWNS | CloneFlags::NEWPID)?;

// 设置资源限制
setrlimit(Resource::RLIMIT_CPU, 60, 60)?;
setrlimit(Resource::RLIMIT_AS, 1_000_000_000, 1_000_000_000)?;
```

### 第3层: 文件系统 ACL

```yaml
tools:
  file:
    allowed_paths:
      - "${HOME}/projects"
      - "${PWD}"
    denied_paths:
      - "${HOME}/.ssh"
      - "${HOME}/.config"
      - "/etc"
      - "/usr/bin"
    allowed_extensions:
      - "*.py"
      - "*.rs"
      - "*.md"
    max_file_size: "10MB"
```

### 第4层: 工具权限

```yaml
tools:
  bash:
    allowed_commands:
      - "ls"
      - "cat"
      - "grep"
    denied_commands:
      - "rm -rf"
      - "dd"
      - "mkfs"
    timeout: 60
```

### 第5层: Agent 沙箱

```python
agent = client.create_agent(
    "code_analyzer",
    sandbox_config={
        "network": False,
        "filesystem": "readonly",
        "max_memory": "100MB",
    }
)
```

### 第6层: 应用安全

- 输入验证
- 输出编码
- SQL 注入防护
- XSS 防护

## Capability-Based 权限模型

### 能力令牌

```rust
pub struct CapabilityToken {
    capability: Capability,
    scope: Scope,
    expires_at: DateTime<Utc>,
    signature: Signature,
}

pub enum Capability {
    FileRead { paths: Vec<PathPattern> },
    FileWrite { paths: Vec<PathPattern> },
    CommandExecute { allowed_commands: Vec<String> },
    NetworkAccess { allowed_hosts: Vec<String> },
}
```

### 令牌颁发

```python
# 颁发能力令牌
token = client.issue_capability_token(
    capability="FileRead",
    scope="${HOME}/projects/*",
    expires_in=3600
)

# 使用令牌
client.with_token(token).execute_tool("read_file", {...})
```

## 数据安全

### 本地优先

ShadowClaude 默认本地处理，不发送数据到云端。

```yaml
privacy:
  local_first: true
  cloud_sync: false
```

### 数据加密

```yaml
security:
  encryption:
    at_rest: true
    algorithm: "AES-256-GCM"
    key_management: "local"
```

### 内存安全

Rust 的所有权系统保证内存安全：

```rust
// 编译时检查，无运行时开销
fn process_data(data: Vec<u8>) -> Result<Vec<u8>> {
    // 所有权转移，防止使用后释放
    let processed = transform(data)?;
    Ok(processed)
} // data 自动释放
```

## 网络安全

### TLS 配置

```yaml
server:
  tls:
    enabled: true
    cert_path: "/path/to/cert.pem"
    key_path: "/path/to/key.pem"
    min_version: "TLSv1.3"
```

### API 认证

```python
# Token 认证
client = sc.Client(
    auth=sc.TokenAuth("your_api_token")
)

# OAuth 认证
client = sc.Client(
    auth=sc.OAuthAuth(
        client_id="...",
        client_secret="..."
    )
)
```

### 请求限流

```yaml
rate_limit:
  enabled: true
  requests_per_minute: 60
  burst_size: 10
```

## 审计日志

### 日志配置

```yaml
logging:
  audit:
    enabled: true
    level: "info"
    events:
      - "tool_call"
      - "file_access"
      - "permission_grant"
      - "configuration_change"
```

### 日志格式

```json
{
  "timestamp": "2026-04-02T10:30:00Z",
  "level": "info",
  "event": "tool_call",
  "user": "user@example.com",
  "tool": "write_file",
  "arguments": {"path": "test.txt"},
  "result": "success"
}
```

## 安全配置最佳实践

### 1. 最小权限原则

只授予必要的权限：

```yaml
# 推荐
tools:
  enabled:
    - read_file
    - search_files

# 不推荐
tools:
  enabled: "all"
```

### 2. 定期轮换密钥

```bash
# 设置密钥过期
shadowclaude key rotate --ttl 30d
```

### 3. 启用审计

```yaml
logging:
  audit:
    enabled: true
    retention_days: 90
```

### 4. 网络隔离

```yaml
network:
  allowed_hosts:
    - "api.anthropic.com"
    - "localhost"
  blocked_hosts:
    - "*"
```

### 5. 定期安全扫描

```bash
# 依赖安全检查
cargo audit

# 代码安全检查
cargo clippy -- -W clippy::security
```

## 漏洞报告

发现安全漏洞请发送至：

```
security@shadowclaude.dev
```

请包含：
- 漏洞描述
- 复现步骤
- 影响范围
- 建议修复方案

## 合规性

### GDPR 合规

- 数据最小化
- 用户同意管理
- 数据可移植性
- 被遗忘权

### SOC 2 合规

- 访问控制
- 变更管理
- 备份恢复
- 监控告警

---

*安全指南版本: 1.0.0 | 最后更新: 2026-04-02*
