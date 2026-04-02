"""
文件操作工具扩展模块
包含: ls, cd, pwd, file_search
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import os
import stat
import fnmatch
import json
from datetime import datetime


class FileTools:
    """文件操作工具集合"""
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes is None:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}PB"
    
    @staticmethod
    def get_all_specs(ToolSpec, ToolResult, PermissionMode):
        """获取所有文件工具规范"""
        
        # ===== ls 工具 =====
        def _handle_ls(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                show_hidden = input_data.get("show_hidden", False)
                recursive = input_data.get("recursive", False)
                sort_by = input_data.get("sort_by", "name")
                
                if not path.exists():
                    return ToolResult(success=False, output="", error=f"Directory not found: {path}")
                if not path.is_dir():
                    return ToolResult(success=False, output="", error=f"Not a directory: {path}")
                if not os.access(path, os.R_OK):
                    return ToolResult(success=False, output="", error=f"Permission denied: {path}")
                
                entries = []
                
                if recursive:
                    for root, dirs, files in os.walk(path):
                        root_path = Path(root)
                        level = len(root_path.relative_to(path).parts)
                        indent = "  " * level
                        
                        for d in sorted(dirs):
                            if not show_hidden and d.startswith("."):
                                continue
                            entries.append(f"{indent}📁 {d}/")
                        
                        for f in sorted(files):
                            if not show_hidden and f.startswith("."):
                                continue
                            file_path = root_path / f
                            try:
                                stat_info = file_path.stat()
                                size = FileTools._format_size(stat_info.st_size)
                                mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                                entries.append(f"{indent}📄 {f} ({size}, {mtime})")
                            except:
                                entries.append(f"{indent}📄 {f}")
                else:
                    try:
                        items = list(path.iterdir())
                    except PermissionError:
                        return ToolResult(success=False, output="", error=f"Permission denied accessing: {path}")
                    
                    dirs = [p for p in items if p.is_dir()]
                    files = [p for p in items if p.is_file()]
                    
                    if not show_hidden:
                        dirs = [d for d in dirs if not d.name.startswith(".")]
                        files = [f for f in files if not f.name.startswith(".")]
                    
                    if sort_by == "name":
                        dirs = sorted(dirs, key=lambda x: x.name.lower())
                        files = sorted(files, key=lambda x: x.name.lower())
                    elif sort_by == "size":
                        files = sorted(files, key=lambda x: x.stat().st_size if x.exists() else 0)
                    elif sort_by == "mtime":
                        files = sorted(files, key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)
                    
                    entries.append(f"📂 {path}")
                    entries.append("")
                    
                    for d in dirs:
                        try:
                            stat_info = d.stat()
                            mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                            entries.append(f"  📁 {d.name}/ (dir, {mtime})")
                        except:
                            entries.append(f"  📁 {d.name}/")
                    
                    for f in files:
                        try:
                            stat_info = f.stat()
                            size = FileTools._format_size(stat_info.st_size)
                            mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                            entries.append(f"  📄 {f.name} ({size}, {mtime})")
                        except:
                            entries.append(f"  📄 {f.name}")
                
                output = "\n".join(entries)
                return ToolResult(success=True, output=output, metadata={"path": str(path)})
                
            except Exception as e:
                return ToolResult(success=False, output="", error=f"ls failed: {str(e)}")
        
        # ===== pwd 工具 =====
        def _handle_pwd(input_data: Dict) -> ToolResult:
            try:
                resolve = input_data.get("resolve_symlinks", True)
                if resolve:
                    cwd = Path.cwd().resolve()
                else:
                    cwd = Path.cwd()
                return ToolResult(success=True, output=str(cwd), metadata={"cwd": str(cwd)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"pwd failed: {str(e)}")
        
        # ===== cd 工具 =====
        def _handle_cd(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data["path"]).expanduser()
                create_if_missing = input_data.get("create_if_missing", False)
                
                if not path.is_absolute():
                    path = Path.cwd() / path
                path = path.resolve()
                
                if not path.exists():
                    if create_if_missing:
                        try:
                            path.mkdir(parents=True, exist_ok=True)
                        except PermissionError:
                            return ToolResult(success=False, output="", error=f"Permission denied creating directory: {path}")
                    else:
                        return ToolResult(success=False, output="", error=f"Directory does not exist: {path}")
                
                if not path.is_dir():
                    return ToolResult(success=False, output="", error=f"Not a directory: {path}")
                if not os.access(path, os.X_OK):
                    return ToolResult(success=False, output="", error=f"Permission denied accessing directory: {path}")
                
                old_cwd = Path.cwd()
                os.chdir(path)
                new_cwd = Path.cwd()
                
                return ToolResult(success=True, output=f"Changed directory: {old_cwd} -> {new_cwd}",
                                metadata={"old_cwd": str(old_cwd), "new_cwd": str(new_cwd)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"cd failed: {str(e)}")
        
        # ===== file_search 工具 =====
        def _handle_file_search(input_data: Dict) -> ToolResult:
            try:
                import re
                from datetime import datetime as dt
                
                base_path = Path(input_data.get("path", ".")).resolve()
                name_pattern = input_data.get("name_pattern")
                content_pattern = input_data.get("content_pattern")
                file_type = input_data.get("file_type", "file")
                max_depth = input_data.get("max_depth")
                exclude_patterns = input_data.get("exclude_patterns", ["node_modules", ".git", "__pycache__"])
                limit = input_data.get("limit", 100)
                
                content_regex = None
                if content_pattern:
                    try:
                        content_regex = re.compile(content_pattern, re.MULTILINE)
                    except re.error as e:
                        return ToolResult(success=False, output="", error=f"Invalid regex: {e}")
                
                matches = []
                
                for root, dirs, files in os.walk(base_path):
                    current_depth = len(Path(root).relative_to(base_path).parts)
                    if max_depth and current_depth >= max_depth:
                        del dirs[:]
                        continue
                    
                    dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, p) for p in exclude_patterns)]
                    
                    entries = []
                    if file_type in ("file", "any"):
                        entries.extend(files)
                    if file_type in ("directory", "any"):
                        entries.extend([f"{d}/" for d in dirs])
                    
                    for entry in entries:
                        if name_pattern and not fnmatch.fnmatch(entry.rstrip("/"), name_pattern):
                            continue
                        
                        full_path = Path(root) / entry.rstrip("/")
                        
                        if content_regex and full_path.is_file():
                            try:
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    if not content_regex.search(f.read()):
                                        continue
                            except:
                                continue
                        
                        try:
                            stat_info = full_path.stat()
                            matches.append({
                                "path": str(full_path.relative_to(base_path)),
                                "size": stat_info.st_size if full_path.is_file() else None,
                            })
                        except:
                            continue
                        
                        if len(matches) >= limit:
                            break
                    
                    if len(matches) >= limit:
                        break
                
                lines = [f"Found {len(matches)} matching files:"]
                for m in matches[:50]:
                    size_str = FileTools._format_size(m["size"]) if m["size"] else "<dir>"
                    lines.append(f"  {m['path']} ({size_str})")
                
                return ToolResult(success=True, output="\n".join(lines), metadata={"total": len(matches)})
                
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Search failed: {str(e)}")
        
        # 返回所有工具规范
        return [
            ToolSpec(
                name="ls",
                description="List files and directories with detailed information including permissions, size, and modification time.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "show_hidden": {"type": "boolean", "default": False},
                        "recursive": {"type": "boolean", "default": False},
                        "sort_by": {"type": "string", "enum": ["name", "size", "mtime", "type"], "default": "name"}
                    }
                },
                required_permission=PermissionMode.READ_ONLY,
                handler=_handle_ls
            ),
            ToolSpec(
                name="pwd",
                description="Print the current working directory path.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "resolve_symlinks": {"type": "boolean", "default": True}
                    }
                },
                required_permission=PermissionMode.READ_ONLY,
                handler=_handle_pwd
            ),
            ToolSpec(
                name="cd",
                description="Change the current working directory.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "create_if_missing": {"type": "boolean", "default": False}
                    },
                    "required": ["path"]
                },
                required_permission=PermissionMode.WORKSPACE_WRITE,
                handler=_handle_cd
            ),
            ToolSpec(
                name="file_search",
                description="Advanced file search with multiple criteria including name patterns, content, size, and date filters.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                        "name_pattern": {"type": "string"},
                        "content_pattern": {"type": "string"},
                        "file_type": {"type": "string", "enum": ["file", "directory", "symlink", "any"], "default": "file"},
                        "max_depth": {"type": "integer"},
                        "exclude_patterns": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "default": 100}
                    }
                },
                required_permission=PermissionMode.READ_ONLY,
                handler=_handle_file_search
            ),
        ]
