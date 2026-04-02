# ShadowClaude 迁移指南

## 从 Claude Code 迁移

### 配置迁移

Claude Code 和 ShadowClaude 的配置格式不同：

**Claude Code:**
```json
{
  "api_key": "sk-...",
  "model": "claude-3-opus"
}
```

**ShadowClaude:**
```yaml
llm:
  provider: anthropic
  api_key: sk-...
  model: claude-3-opus-20240229
```

### 命令对比

| Claude Code | ShadowClaude | 说明 |
|-------------|--------------|------|
| `/config` | `shadowclaude config` | 配置管理 |
| `/memory` | `shadowclaude memory` | 记忆管理 |
| `/clear` | `clear` 或新会话 | 清空上下文 |
| `/exit` | `exit` 或 Ctrl+D | 退出 |

### 功能对比

| 功能 | Claude Code | ShadowClaude |
|------|-------------|--------------|
| 文件操作 | ✅ | ✅ |
| 终端执行 | ✅ | ✅ |
| 代码搜索 | ✅ | ✅ |
| 三层记忆 | ❌ | ✅ |
| 多 Agent | ❌ | ✅ |
| BUDDY | ❌ | ✅ |
| KAIROS | ❌ | ✅ |
| MCP | ❌ | ✅ |

## 从 GitHub Copilot 迁移

### 使用模式对比

**Copilot:**
- 编辑器内联建议
- Tab 接受建议

**ShadowClaude:**
- 自然语言交互
- 多轮对话
- 工具调用

### 工作流程迁移

1. **代码生成:**
   - Copilot: 写注释，等待建议
   - ShadowClaude: "生成排序函数"

2. **代码解释:**
   - Copilot: 无直接支持
   - ShadowClaude: "解释这段代码"

3. **代码重构:**
   - Copilot: 手动修改
   - ShadowClaude: "重构这个函数"

## 从其他 AI 助手迁移

### Cursor

**相似功能:**
- 代码编辑
- 终端集成
- Chat 界面

**ShadowClaude 优势:**
- 开源
- 本地优先
- 更强大的记忆系统

### Cody (Sourcegraph)

**相似功能:**
- 代码搜索
- 代码智能

**ShadowClaude 优势:**
- 多 Agent 协作
- BUDDY 陪伴系统
- 更强的工具系统

## 数据迁移

### 历史记录

```python
# 从其他工具导入历史
shadowclaude import-history \
  --from claude-code \
  --input ~/.claude/history.json
```

### 代码片段

```python
# 导入代码片段
shadowclaude import-snippets \
  --from copilot \
  --input snippets.json
```

## 最佳实践

### 1. 渐进式迁移

- 先并行使用
- 逐步增加 ShadowClaude 使用比例
- 完全切换后停用旧工具

### 2. 配置同步

- 导出旧工具配置
- 转换为 ShadowClaude 格式
- 验证功能等价性

### 3. 团队迁移

- 制定迁移计划
- 培训团队成员
- 建立新的工作流程

---

*迁移指南版本: 1.0.0 | 最后更新: 2026-04-02*
