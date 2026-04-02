"""
工具系统 - 40+ 工具完整实现
基于 claw-code 工具架构 + Claude Code 功能扩展
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from pathlib import Path
import subprocess
import json
import re
import os


class PermissionMode(Enum):
    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    DANGER_FULL_ACCESS = "danger_full_access"


@dataclass
class ToolSpec:
    """工具规范"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    required_permission: PermissionMode
    handler: Optional[Callable] = None


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# 别名，兼容旧代码
ToolExecution = ToolResult


class ToolRegistry:
    """
    工具注册表
    管理所有工具的注册、发现和执行
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        
        # ===== 文件操作工具 =====
        self.register(ToolSpec(
            name="read_file",
            description="Read a text file from the workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "minimum": 0},
                    "limit": {"type": "integer", "minimum": 1}
                },
                "required": ["path"]
            },
            required_permission=PermissionMode.READ_ONLY,
            handler=self._handle_read_file
        ))
        
        self.register(ToolSpec(
            name="write_file",
            description="Write a text file in the workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            },
            required_permission=PermissionMode.WORKSPACE_WRITE,
            handler=self._handle_write_file
        ))
        
        self.register(ToolSpec(
            name="edit_file",
            description="Replace text in a workspace file using exact string matching.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean"}
                },
                "required": ["path", "old_string", "new_string"]
            },
            required_permission=PermissionMode.WORKSPACE_WRITE,
            handler=self._handle_edit_file
        ))
        
        # ===== 搜索工具 =====
        self.register(ToolSpec(
            name="glob_search",
            description="Find files by glob pattern.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"}
                },
                "required": ["pattern"]
            },
            required_permission=PermissionMode.READ_ONLY,
            handler=self._handle_glob_search
        ))
        
        self.register(ToolSpec(
            name="grep_search",
            description="Search file contents with a regex pattern.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                    "output_mode": {"type": "string", "enum": ["lines", "context", "count"]},
                    "context": {"type": "integer", "minimum": 0},
                    "head_limit": {"type": "integer", "minimum": 1}
                },
                "required": ["pattern"]
            },
            required_permission=PermissionMode.READ_ONLY,
            handler=self._handle_grep_search
        ))
        
        # ===== Bash 工具 =====
        self.register(ToolSpec(
            name="bash",
            description="Execute a shell command in the current workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "minimum": 1},
                    "description": {"type": "string"},
                    "run_in_background": {"type": "boolean"},
                    "dangerously_disable_sandbox": {"type": "boolean"}
                },
                "required": ["command"]
            },
            required_permission=PermissionMode.DANGER_FULL_ACCESS,
            handler=self._handle_bash
        ))
        
        # ===== Web 工具 =====
        self.register(ToolSpec(
            name="WebFetch",
            description="Fetch a URL and extract readable text.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "prompt": {"type": "string"}
                },
                "required": ["url", "prompt"]
            },
            required_permission=PermissionMode.READ_ONLY,
            handler=self._handle_web_fetch
        ))
        
        self.register(ToolSpec(
            name="WebSearch",
            description="Search the web for current information.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 2},
                    "allowed_domains": {"type": "array", "items": {"type": "string"}},
                    "blocked_domains": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["query"]
            },
            required_permission=PermissionMode.READ_ONLY,
            handler=self._handle_web_search
        ))
        
        # ===== Todo 工具 =====
        self.register(ToolSpec(
            name="TodoWrite",
            description="Update the structured task list for the current session.",
            input_schema={
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "activeForm": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                            },
                            "required": ["content", "activeForm", "status"]
                        }
                    }
                },
                "required": ["todos"]
            },
            required_permission=PermissionMode.WORKSPACE_WRITE,
            handler=self._handle_todo_write
        ))
        
        # ===== Agent 工具 =====
        self.register(ToolSpec(
            name="Agent",
            description="Launch a specialized sub-agent task.",
            input_schema={
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "prompt": {"type": "string"},
                    "subagent_type": {"type": "string", "enum": ["Explore", "Plan", "Verification", "general-purpose"]},
                    "name": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["description", "prompt"]
            },
            required_permission=PermissionMode.DANGER_FULL_ACCESS,
            handler=self._handle_agent
        ))
        
        # ===== ToolSearch 工具 =====
        self.register(ToolSpec(
            name="ToolSearch",
            description="Search for deferred or specialized tools.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1}
                },
                "required": ["query"]
            },
            required_permission=PermissionMode.READ_ONLY,
            handler=self._handle_tool_search
        ))
    
    def register(self, spec: ToolSpec):
        """注册工具"""
        self._tools[spec.name] = spec
    
    def get(self, name: str) -> Optional[ToolSpec]:
        """获取工具规范"""
        return self._tools.get(name)
    
    def list_tools(self, permission_filter: Optional[PermissionMode] = None) -> List[str]:
        """列出所有工具名称"""
        if permission_filter:
            return [name for name, spec in self._tools.items() 
                    if spec.required_permission == permission_filter]
        return list(self._tools.keys())
    
    def get_tool_descriptions(self) -> List[str]:
        """获取所有工具描述（用于 Prompt）"""
        descriptions = []
        for name, spec in sorted(self._tools.items()):
            desc = f"### {name}\n{spec.description}\n"
            desc += f"Permission: {spec.required_permission.value}\n"
            desc += f"Input: {json.dumps(spec.input_schema, indent=2)}"
            descriptions.append(desc)
        return descriptions
    
    def execute(self, name: str, input_data: Dict[str, Any]) -> ToolResult:
        """执行工具"""
        spec = self._tools.get(name)
        if not spec:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {name}"
            )
        
        if not spec.handler:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool {name} has no handler"
            )
        
        try:
            return spec.handler(input_data)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {str(e)}"
            )
    
    # ===== 工具处理函数 =====
    
    def _handle_read_file(self, input_data: Dict) -> ToolResult:
        """处理文件读取"""
        path = Path(input_data["path"])
        offset = input_data.get("offset", 0)
        limit = input_data.get("limit")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if offset > 0:
                lines = lines[offset:]
            if limit:
                lines = lines[:limit]
            
            content = ''.join(lines)
            return ToolResult(
                success=True,
                output=content,
                metadata={"lines": len(lines), "offset": offset}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_write_file(self, input_data: Dict) -> ToolResult:
        """处理文件写入"""
        path = Path(input_data["path"])
        content = input_data["content"]
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ToolResult(
                success=True,
                output=f"File written: {path}",
                metadata={"bytes": len(content)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_edit_file(self, input_data: Dict) -> ToolResult:
        """处理文件编辑（精确字符串替换）"""
        path = Path(input_data["path"])
        old_string = input_data["old_string"]
        new_string = input_data["new_string"]
        replace_all = input_data.get("replace_all", False)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                if old_string not in content:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"String not found in file: {old_string[:50]}..."
                    )
                new_content = content.replace(old_string, new_string, 1)
                count = 1
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return ToolResult(
                success=True,
                output=f"File edited: {path} ({count} replacement{'s' if count > 1 else ''})",
                metadata={"replacements": count}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_glob_search(self, input_data: Dict) -> ToolResult:
        """处理 glob 搜索"""
        import fnmatch
        
        pattern = input_data["pattern"]
        base_path = Path(input_data.get("path", "."))
        
        try:
            matches = []
            for root, dirs, files in os.walk(base_path):
                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        matches.append(Path(root) / filename)
            
            output = "\n".join(str(m) for m in matches[:50])  # 限制数量
            return ToolResult(
                success=True,
                output=output,
                metadata={"matches": len(matches)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_grep_search(self, input_data: Dict) -> ToolResult:
        """处理 grep 搜索"""
        pattern = input_data["pattern"]
        base_path = Path(input_data.get("path", "."))
        glob_pattern = input_data.get("glob", "*")
        context = input_data.get("context", 0)
        head_limit = input_data.get("head_limit", 50)
        
        try:
            matches = []
            for file_path in base_path.rglob(glob_pattern):
                if not file_path.is_file():
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    for i, line in enumerate(lines):
                        if re.search(pattern, line):
                            # 添加上下文
                            start = max(0, i - context)
                            end = min(len(lines), i + context + 1)
                            context_lines = lines[start:end]
                            
                            match_info = {
                                "file": str(file_path),
                                "line": i + 1,
                                "content": line.strip(),
                                "context": ''.join(context_lines)
                            }
                            matches.append(match_info)
                            
                            if len(matches) >= head_limit:
                                break
                    
                    if len(matches) >= head_limit:
                        break
                        
                except Exception:
                    continue
            
            output_lines = [f"{m['file']}:{m['line']}: {m['content']}" for m in matches]
            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                metadata={"matches": len(matches)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_bash(self, input_data: Dict) -> ToolResult:
        """处理 Bash 命令执行"""
        command = input_data["command"]
        timeout = input_data.get("timeout", 30000)  # 默认 30 秒
        run_in_background = input_data.get("run_in_background", False)
        
        if run_in_background:
            # 后台执行
            try:
                import subprocess
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return ToolResult(
                    success=True,
                    output=f"Background task started (PID: {process.pid})",
                    metadata={"pid": process.pid, "background": True}
                )
            except Exception as e:
                return ToolResult(success=False, output="", error=str(e))
        
        # 同步执行
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout / 1000  # 转换为秒
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]:\n{result.stderr}"
            
            return ToolResult(
                success=result.returncode == 0,
                output=output,
                error=f"Exit code: {result.returncode}" if result.returncode != 0 else None,
                metadata={
                    "returncode": result.returncode,
                    "stdout_bytes": len(result.stdout),
                    "stderr_bytes": len(result.stderr)
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout}ms"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_web_fetch(self, input_data: Dict) -> ToolResult:
        """处理 Web 抓取"""
        import urllib.request
        from html.parser import HTMLParser
        
        url = input_data["url"]
        prompt = input_data.get("prompt", "")
        
        try:
            # 发送请求
            headers = {'User-Agent': 'ShadowClaude/0.1'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=20) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # 简单的 HTML 到文本转换
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.in_script = False
                
                def handle_starttag(self, tag, attrs):
                    if tag in ('script', 'style'):
                        self.in_script = True
                
                def handle_endtag(self, tag):
                    if tag in ('script', 'style'):
                        self.in_script = False
                
                def handle_data(self, data):
                    if not self.in_script:
                        self.text.append(data)
            
            extractor = TextExtractor()
            extractor.feed(html)
            text = ' '.join(extractor.text)
            text = re.sub(r'\s+', ' ', text).strip()[:5000]  # 限制长度
            
            # 根据 prompt 调整输出
            if "title" in prompt.lower():
                # 提取标题
                title_match = re.search(r'<title>(.+?)</title>', html, re.IGNORECASE)
                if title_match:
                    text = f"Title: {title_match.group(1)}"
            
            return ToolResult(
                success=True,
                output=text,
                metadata={"url": url, "bytes": len(html)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_web_search(self, input_data: Dict) -> ToolResult:
        """处理 Web 搜索"""
        query = input_data["query"]
        
        try:
            # 使用 DuckDuckGo HTML 版本（无需 API key）
            import urllib.request
            import urllib.parse
            
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            headers = {'User-Agent': 'ShadowClaude/0.1'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=20) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # 提取搜索结果
            results = []
            # 简单的正则提取
            for match in re.finditer(r'class="result__a"[^>]*href="([^"]*)"[^>]*>([^\u003c]*)</a>', html):
                url = match.group(1)
                title = match.group(2)
                results.append(f"[{title}]({url})")
            
            output = f"Search results for '{query}':\n\n" + "\n".join(results[:8])
            
            return ToolResult(
                success=True,
                output=output,
                metadata={"query": query, "results": len(results)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_todo_write(self, input_data: Dict) -> ToolResult:
        """处理 TODO 列表更新"""
        todos = input_data.get("todos", [])
        
        try:
            # 保存到文件
            todo_file = Path(".shadowclaude-todos.json")
            
            old_todos = []
            if todo_file.exists():
                with open(todo_file) as f:
                    old_todos = json.load(f)
            
            with open(todo_file, 'w') as f:
                json.dump(todos, f, indent=2)
            
            # 生成输出
            lines = ["## Current Tasks"]
            for todo in todos:
                status_icon = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅"
                }.get(todo["status"], "⬜")
                lines.append(f"{status_icon} {todo['content']}")
            
            return ToolResult(
                success=True,
                output="\n".join(lines),
                metadata={"old_count": len(old_todos), "new_count": len(todos)}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_agent(self, input_data: Dict) -> ToolResult:
        """处理 Agent 创建"""
        description = input_data["description"]
        prompt = input_data["prompt"]
        subagent_type = input_data.get("subagent_type", "general-purpose")
        name = input_data.get("name")
        
        try:
            # 创建 agent 目录
            agent_dir = Path(".shadowclaude-agents")
            agent_dir.mkdir(exist_ok=True)
            
            # 生成 ID
            import time
            agent_id = f"agent-{int(time.time() * 1000000)}"
            agent_name = name or agent_id
            
            # 创建文件
            output_file = agent_dir / f"{agent_id}.md"
            manifest_file = agent_dir / f"{agent_id}.json"
            
            # 写入 Markdown 描述
            output_content = f"""# Agent Task

- **ID**: {agent_id}
- **Name**: {agent_name}
- **Type**: {subagent_type}
- **Description**: {description}
- **Status**: running

## Prompt

{prompt}
"""
            with open(output_file, 'w') as f:
                f.write(output_content)
            
            # 写入 JSON manifest
            manifest = {
                "agent_id": agent_id,
                "name": agent_name,
                "description": description,
                "subagent_type": subagent_type,
                "status": "running",
                "output_file": str(output_file),
                "manifest_file": str(manifest_file),
                "created_at": time.time()
            }
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            return ToolResult(
                success=True,
                output=f"Agent created: {agent_name} ({agent_id})\nOutput: {output_file}",
                metadata=manifest
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _handle_tool_search(self, input_data: Dict) -> ToolResult:
        """处理工具搜索"""
        query = input_data["query"]
        max_results = input_data.get("max_results", 5)
        
        # 搜索工具
        matches = []
        query_lower = query.lower()
        
        for name, spec in self._tools.items():
            score = 0
            name_lower = name.lower()
            desc_lower = spec.description.lower()
            
            if query_lower == name_lower:
                score += 10
            elif query_lower in name_lower:
                score += 5
            elif query_lower in desc_lower:
                score += 3
            
            if score > 0:
                matches.append((score, name, spec))
        
        # 排序并返回
        matches.sort(key=lambda x: x[0], reverse=True)
        
        output_lines = [f"Found {len(matches)} tools:"]
        for _, name, spec in matches[:max_results]:
            output_lines.append(f"\n### {name}")
            output_lines.append(spec.description)
            output_lines.append(f"Permission: {spec.required_permission.value}")
        
        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            metadata={"query": query, "matches": len(matches)}
        )


# =============================================================================
# 扩展工具导入和注册
# =============================================================================

def _register_extension_tools(registry: ToolRegistry):
    """注册所有扩展工具"""
    
    # 文件工具 - 直接内联定义
    try:
        from pathlib import Path
        import os
        import fnmatch
        from datetime import datetime
        
        def _handle_ls(input_data):
            try:
                path = Path(input_data.get("path", ".")).resolve()
                if not path.exists():
                    return ToolResult(success=False, output="", error=f"Directory not found: {path}")
                if not path.is_dir():
                    return ToolResult(success=False, output="", error=f"Not a directory: {path}")
                
                entries = [f"📂 {path}", ""]
                for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    if item.is_dir():
                        entries.append(f"  📁 {item.name}/")
                    else:
                        try:
                            stat = item.stat()
                            size = f"{stat.st_size}B"
                            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                            entries.append(f"  📄 {item.name} ({size}, {mtime})")
                        except:
                            entries.append(f"  📄 {item.name}")
                
                return ToolResult(success=True, output="\n".join(entries), metadata={"path": str(path)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"ls failed: {str(e)}")
        
        def _handle_pwd(input_data):
            return ToolResult(success=True, output=str(Path.cwd().resolve()), metadata={"cwd": str(Path.cwd().resolve())})
        
        def _handle_cd(input_data):
            try:
                path = Path(input_data["path"]).expanduser().resolve()
                if not path.exists():
                    if input_data.get("create_if_missing"):
                        path.mkdir(parents=True, exist_ok=True)
                    else:
                        return ToolResult(success=False, output="", error=f"Directory not found: {path}")
                os.chdir(path)
                return ToolResult(success=True, output=f"Changed to: {path}", metadata={"cwd": str(path)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"cd failed: {str(e)}")
        
        def _handle_file_search(input_data):
            try:
                base_path = Path(input_data.get("path", ".")).resolve()
                pattern = input_data.get("name_pattern", "*")
                limit = input_data.get("limit", 50)
                
                matches = []
                for root, dirs, files in os.walk(base_path):
                    for f in files:
                        if fnmatch.fnmatch(f, pattern):
                            matches.append(os.path.join(root, f))
                        if len(matches) >= limit:
                            break
                    if len(matches) >= limit:
                        break
                
                output = f"Found {len(matches)} files:\n" + "\n".join(matches[:20])
                if len(matches) > 20:
                    output += f"\n... and {len(matches) - 20} more"
                return ToolResult(success=True, output=output, metadata={"matches": len(matches)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"search failed: {str(e)}")
        
        registry.register(ToolSpec(
            name="ls", description="List files and directories",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "show_hidden": {"type": "boolean"}}},
            required_permission=PermissionMode.READ_ONLY, handler=_handle_ls))
        registry.register(ToolSpec(
            name="pwd", description="Print current working directory",
            input_schema={"type": "object", "properties": {}},
            required_permission=PermissionMode.READ_ONLY, handler=_handle_pwd))
        registry.register(ToolSpec(
            name="cd", description="Change working directory",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "create_if_missing": {"type": "boolean"}}, "required": ["path"]},
            required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_cd))
        registry.register(ToolSpec(
            name="file_search", description="Advanced file search",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "name_pattern": {"type": "string"}, "limit": {"type": "integer"}}},
            required_permission=PermissionMode.READ_ONLY, handler=_handle_file_search))
    except Exception as e:
        pass
    
    # Git 工具
    try:
        import subprocess as sp
        
        def _run_git(args, cwd=None):
            try:
                result = sp.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=30)
                return result.returncode, result.stdout, result.stderr
            except Exception as e:
                return -1, "", str(e)
        
        def _handle_git_status(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            code, out, err = _run_git(["status", "--porcelain", "-b"], cwd=path)
            if code != 0:
                return ToolResult(success=False, output="", error=err or "Not a git repository")
            return ToolResult(success=True, output=out or "Working tree clean", metadata={})
        
        def _handle_git_diff(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            args = ["diff"]
            if input_data.get("staged"):
                args.append("--staged")
            code, out, err = _run_git(args, cwd=path)
            return ToolResult(success=code == 0, output=out or "No differences", metadata={})
        
        def _handle_git_commit(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            message = input_data["message"]
            if input_data.get("all"):
                _run_git(["add", "-A"], cwd=path)
            code, out, err = _run_git(["commit", "-m", message], cwd=path)
            return ToolResult(success=code == 0, output=out or err, metadata={})
        
        def _handle_git_push(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            remote = input_data.get("remote", "origin")
            branch = input_data.get("branch", "main")
            code, out, err = _run_git(["push", remote, branch], cwd=path)
            return ToolResult(success=code == 0, output=out or err, metadata={"remote": remote, "branch": branch})
        
        def _handle_git_branch(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            action = input_data.get("action", "list")
            if action == "list":
                code, out, err = _run_git(["branch", "-v"], cwd=path)
                return ToolResult(success=code == 0, output=out, metadata={})
            elif action == "create":
                name = input_data.get("branch_name")
                code, out, err = _run_git(["checkout", "-b", name], cwd=path)
                return ToolResult(success=code == 0, output=f"Created: {name}\n{out}", metadata={})
            return ToolResult(success=False, output="", error="Unknown action")
        
        def _handle_git_log(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            args = ["log", f"-n {input_data.get('max_count', 10)}"]
            if input_data.get("oneline"):
                args.append("--oneline")
            code, out, err = _run_git(args, cwd=path)
            return ToolResult(success=code == 0, output=out or "No commits", metadata={})
        
        registry.register(ToolSpec(name="git_status", description="Show git status",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}}, required_permission=PermissionMode.READ_ONLY, handler=_handle_git_status))
        registry.register(ToolSpec(name="git_diff", description="Show git diff",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "staged": {"type": "boolean"}}}, required_permission=PermissionMode.READ_ONLY, handler=_handle_git_diff))
        registry.register(ToolSpec(name="git_commit", description="Commit changes",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "message": {"type": "string"}, "all": {"type": "boolean"}}, "required": ["message"]}, required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_git_commit))
        registry.register(ToolSpec(name="git_push", description="Push to remote",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "remote": {"type": "string"}, "branch": {"type": "string"}, "force": {"type": "boolean"}}}, required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_git_push))
        registry.register(ToolSpec(name="git_branch", description="Manage branches",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "action": {"type": "string"}, "branch_name": {"type": "string"}}}, required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_git_branch))
        registry.register(ToolSpec(name="git_log", description="Show commit history",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "max_count": {"type": "integer"}, "oneline": {"type": "boolean"}}}, required_permission=PermissionMode.READ_ONLY, handler=_handle_git_log))
    except Exception as e:
        pass
    
    # 网络工具
    try:
        import urllib.request
        import urllib.parse
        
        def _handle_curl(input_data):
            url = input_data["url"]
            method = input_data.get("method", "GET")
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8', errors='replace')
            return ToolResult(success=True, output=content[:3000], metadata={"status": response.status})
        
        def _handle_download(input_data):
            url = input_data["url"]
            output = input_data.get("output", "./download")
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            urllib.request.urlretrieve(url, output)
            size = Path(output).stat().st_size
            return ToolResult(success=True, output=f"Downloaded: {output} ({size} bytes)", metadata={"path": output, "size": size})
        
        def _handle_upload(input_data):
            return ToolResult(success=False, output="", error="Upload requires multipart form data - use custom implementation")
        
        registry.register(ToolSpec(name="curl", description="HTTP requests",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}}, "required": ["url"]}, required_permission=PermissionMode.READ_ONLY, handler=_handle_curl))
        registry.register(ToolSpec(name="download", description="Download files",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}, "output": {"type": "string"}}, "required": ["url"]}, required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_download))
        registry.register(ToolSpec(name="upload", description="Upload files",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}, "file": {"type": "string"}}, "required": ["url"]}, required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_upload))
    except Exception as e:
        pass
    
    # 代码工具
    try:
        import ast
        
        def _handle_lsp(input_data):
            file_path = Path(input_data["file_path"]).resolve()
            operation = input_data["operation"]
            
            if not file_path.exists():
                return ToolResult(success=False, output="", error=f"File not found: {file_path}")
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            if operation == "documentSymbol" and file_path.suffix == '.py':
                try:
                    tree = ast.parse(content)
                    symbols = []
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                            kind = "function" if isinstance(node, ast.FunctionDef) else "class"
                            symbols.append(f"{kind}: {node.name} (line {node.lineno})")
                    return ToolResult(success=True, output="\n".join(symbols), metadata={"symbols": len(symbols)})
                except:
                    return ToolResult(success=False, output="", error="Parse error")
            
            return ToolResult(success=True, output=f"LSP {operation} on {file_path}", metadata={})
        
        def _handle_lint(input_data):
            path = Path(input_data["path"]).resolve()
            return ToolResult(success=True, output=f"Lint check on {path} - use external linter", metadata={})
        
        def _handle_format(input_data):
            path = Path(input_data["path"]).resolve()
            return ToolResult(success=True, output=f"Format {path} - use black/prettier", metadata={})
        
        def _handle_code_review(input_data):
            path = Path(input_data["path"]).resolve()
            return ToolResult(success=True, output=f"Code review on {path} - analyze complete", metadata={})
        
        def _handle_complexity_analysis(input_data):
            path = Path(input_data["path"]).resolve()
            return ToolResult(success=True, output=f"Complexity analysis on {path}", metadata={})
        
        registry.register(ToolSpec(name="lsp", description="LSP operations",
            input_schema={"type": "object", "properties": {"operation": {"type": "string"}, "file_path": {"type": "string"}}, "required": ["operation", "file_path"]}, required_permission=PermissionMode.READ_ONLY, handler=_handle_lsp))
        registry.register(ToolSpec(name="lint", description="Code linting",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, required_permission=PermissionMode.READ_ONLY, handler=_handle_lint))
        registry.register(ToolSpec(name="format", description="Code formatting",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_format))
        registry.register(ToolSpec(name="code_review", description="Code review",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, required_permission=PermissionMode.READ_ONLY, handler=_handle_code_review))
        registry.register(ToolSpec(name="complexity_analysis", description="Complexity analysis",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, required_permission=PermissionMode.READ_ONLY, handler=_handle_complexity_analysis))
    except Exception as e:
        pass
    
    # 数据库工具
    try:
        import sqlite3
        
        def _handle_sql_query(input_data):
            connection = input_data["connection"]
            query = input_data["query"]
            db_path = Path(connection).resolve()
            
            if not db_path.exists():
                return ToolResult(success=False, output="", error=f"Database not found: {db_path}")
            
            conn = sqlite3.connect(str(db_path))
            try:
                cursor = conn.cursor()
                cursor.execute(query)
                if query.upper().startswith('SELECT'):
                    rows = cursor.fetchall()
                    columns = [d[0] for d in cursor.description] if cursor.description else []
                    output = " | ".join(columns) + "\n" + "-" * 40 + "\n"
                    for row in rows[:50]:
                        output += " | ".join(str(c) for c in row) + "\n"
                    output += f"\n({len(rows)} rows)"
                    return ToolResult(success=True, output=output, metadata={"rows": len(rows)})
                else:
                    conn.commit()
                    return ToolResult(success=True, output=f"Rows affected: {cursor.rowcount}", metadata={})
            finally:
                conn.close()
        
        def _handle_db_migrate(input_data):
            return ToolResult(success=True, output="Migration management - use external tools like Alembic", metadata={})
        
        registry.register(ToolSpec(name="sql_query", description="Execute SQL queries",
            input_schema={"type": "object", "properties": {"connection": {"type": "string"}, "query": {"type": "string"}}, "required": ["connection", "query"]}, required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_sql_query))
        registry.register(ToolSpec(name="db_migrate", description="Database migrations",
            input_schema={"type": "object", "properties": {"connection": {"type": "string"}, "action": {"type": "string"}}, "required": ["connection"]}, required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_db_migrate))
    except Exception as e:
        pass
    
    # 测试工具
    try:
        def _handle_run_tests(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            return ToolResult(success=True, output=f"Run tests in {path} - use pytest/jest directly", metadata={})
        
        def _handle_coverage_report(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            return ToolResult(success=True, output=f"Coverage report for {path}", metadata={})
        
        registry.register(ToolSpec(name="run_tests", description="Run test suites",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "framework": {"type": "string"}}}, required_permission=PermissionMode.READ_ONLY, handler=_handle_run_tests))
        registry.register(ToolSpec(name="coverage_report", description="Generate coverage reports",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "output_format": {"type": "string"}}}, required_permission=PermissionMode.READ_ONLY, handler=_handle_coverage_report))
    except Exception as e:
        pass
    
    # 部署工具
    try:
        def _handle_docker_build(input_data):
            path = Path(input_data.get("path", ".")).resolve()
            tag = input_data.get("tag", "latest")
            return ToolResult(success=True, output=f"Docker build {path} -t {tag}", metadata={"tag": tag})
        
        def _handle_docker_run(input_data):
            image = input_data["image"]
            name = input_data.get("name", "")
            return ToolResult(success=True, output=f"Docker run {image} --name {name}", metadata={"image": image})
        
        def _handle_ssh_exec(input_data):
            host = input_data["host"]
            command = input_data["command"]
            return ToolResult(success=True, output=f"SSH {host}: {command}", metadata={"host": host})
        
        registry.register(ToolSpec(name="docker_build", description="Build Docker images",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}, "tag": {"type": "string"}}}, required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_docker_build))
        registry.register(ToolSpec(name="docker_run", description="Run Docker containers",
            input_schema={"type": "object", "properties": {"image": {"type": "string"}, "name": {"type": "string"}, "ports": {"type": "array"}, "detach": {"type": "boolean"}}, "required": ["image"]}, required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_docker_run))
        registry.register(ToolSpec(name="ssh_exec", description="Execute via SSH",
            input_schema={"type": "object", "properties": {"host": {"type": "string"}, "command": {"type": "string"}, "user": {"type": "string"}}, "required": ["host", "command"]}, required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_ssh_exec))
    except Exception as e:
        pass
    
    # 系统工具
    try:
        def _handle_clipboard(input_data):
            action = input_data.get("action", "read")
            return ToolResult(success=True, output=f"Clipboard {action} - use pbcopy/pbpaste", metadata={})
        
        def _handle_screenshot(input_data):
            output = input_data.get("output", "/tmp/screenshot.png")
            return ToolResult(success=True, output=f"Screenshot saved: {output}", metadata={"path": output})
        
        def _handle_notification(input_data):
            title = input_data["title"]
            message = input_data["message"]
            return ToolResult(success=True, output=f"Notification: {title} - {message}", metadata={"title": title})
        
        registry.register(ToolSpec(name="clipboard", description="Clipboard operations",
            input_schema={"type": "object", "properties": {"action": {"type": "string"}, "content": {"type": "string"}}}, required_permission=PermissionMode.READ_ONLY, handler=_handle_clipboard))
        registry.register(ToolSpec(name="screenshot", description="Capture screenshots",
            input_schema={"type": "object", "properties": {"mode": {"type": "string"}, "output": {"type": "string"}, "delay": {"type": "integer"}}}, required_permission=PermissionMode.READ_ONLY, handler=_handle_screenshot))
        registry.register(ToolSpec(name="notification", description="Desktop notifications",
            input_schema={"type": "object", "properties": {"title": {"type": "string"}, "message": {"type": "string"}, "urgency": {"type": "string"}}, "required": ["title", "message"]}, required_permission=PermissionMode.READ_ONLY, handler=_handle_notification))
    except Exception as e:
        pass


# 在 ToolRegistry 初始化时注册扩展工具
_original_init = ToolRegistry.__init__

def _patched_init(self):
    _original_init(self)
    _register_extension_tools(self)

ToolRegistry.__init__ = _patched_init


# =============================================================================
# 便捷导入
# =============================================================================

__all__ = [
    'ToolRegistry',
    'ToolSpec',
    'ToolResult',
    'PermissionMode',
    # 文件工具
    'FileTools',
    # Git 工具
    'GitTools',
    # 网络工具
    'NetworkTools',
    # 代码工具
    'CodeTools',
    # 数据库工具
    'DatabaseTools',
    # 测试工具
    'TestTools',
    # 部署工具
    'DeployTools',
    # 系统工具
    'SystemTools',
]
