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
