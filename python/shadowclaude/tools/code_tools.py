"""
代码工具扩展模块
包含: LSP 集成, lint, format, code_review, complexity_analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import subprocess
import re
import ast


class CodeTools:
    """代码操作工具集合"""
    
    @staticmethod
    def get_all_specs(ToolSpec, ToolResult, PermissionMode):
        """获取所有代码工具规范"""
        
        def _handle_lsp(input_data: Dict) -> ToolResult:
            try:
                operation = input_data["operation"]
                file_path = Path(input_data["file_path"]).resolve()
                
                if not file_path.exists():
                    return ToolResult(success=False, output="", error=f"File not found: {file_path}")
                
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                if operation == "documentSymbol":
                    symbols = []
                    if file_path.suffix == '.py':
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                                    kind = "function" if isinstance(node, ast.FunctionDef) else "class"
                                    symbols.append({"name": node.name, "kind": kind, "line": node.lineno})
                        except:
                            pass
                    
                    lines = [f"Symbols ({len(symbols)} found):"]
                    for s in symbols:
                        lines.append(f"  {s['kind']} {s['name']} - Line {s['line']}")
                    return ToolResult(success=True, output="\n".join(lines), metadata={"symbols": symbols})
                
                return ToolResult(success=False, output="", error=f"Operation {operation} not fully implemented")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"LSP failed: {str(e)}")
        
        def _handle_lint(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                if not path.exists():
                    return ToolResult(success=False, output="", error=f"Path not found: {path}")
                
                # 尝试使用 ruff 或 flake8
                for linter in ["ruff", "flake8"]:
                    try:
                        cmd = [linter, str(path)]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        return ToolResult(success=result.returncode == 0, output=result.stdout or "No issues found",
                                        metadata={"linter": linter, "exit_code": result.returncode})
                    except FileNotFoundError:
                        continue
                
                return ToolResult(success=False, output="", error="No linter found. Install ruff or flake8.")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Lint failed: {str(e)}")
        
        def _handle_format(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                check = input_data.get("check", False)
                
                if not path.exists():
                    return ToolResult(success=False, output="", error=f"Path not found: {path}")
                
                # 尝试使用 black
                try:
                    cmd = ["black"]
                    if check:
                        cmd.append("--check")
                    cmd.append(str(path))
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    return ToolResult(success=result.returncode == 0, output=result.stdout or "Formatted successfully",
                                    metadata={"formatter": "black", "check_only": check})
                except FileNotFoundError:
                    return ToolResult(success=False, output="", error="black not found. Install with: pip install black")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Format failed: {str(e)}")
        
        def _handle_code_review(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                focus = input_data.get("focus", ["security"])
                
                issues = []
                
                if path.is_file():
                    files = [path]
                else:
                    files = list(path.rglob("*.py"))
                
                for f in files:
                    try:
                        content = f.read_text(encoding='utf-8', errors='ignore')
                        lines = content.split('\n')
                        
                        if "security" in focus:
                            for i, line in enumerate(lines, 1):
                                if re.search(r'(password|secret|key)\s*=\s*["\'][^"\']+["\']', line, re.I):
                                    issues.append({"file": str(f), "line": i, "severity": "high",
                                                 "category": "security", "message": "Possible hardcoded credential"})
                        
                        if "maintainability" in focus:
                            for i, line in enumerate(lines, 1):
                                if len(line) > 120:
                                    issues.append({"file": str(f), "line": i, "severity": "low",
                                                 "category": "maintainability", "message": "Line too long"})
                    except:
                        continue
                
                lines = [f"Code Review: {len(issues)} issues found"]
                for issue in issues[:20]:
                    lines.append(f"[{issue['severity'].upper()}] {issue['file']}:{issue['line']} - {issue['message']}")
                
                return ToolResult(success=True, output="\n".join(lines), metadata={"issues": len(issues)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Code review failed: {str(e)}")
        
        def _handle_complexity_analysis(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                
                files = [path] if path.is_file() else list(path.rglob("*.py"))
                
                results = []
                for f in files:
                    try:
                        content = f.read_text(encoding='utf-8', errors='ignore')
                        lines = content.split('\n')
                        total = len(lines)
                        code = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
                        results.append({"file": str(f), "total": total, "code": code})
                    except:
                        continue
                
                lines = ["Complexity Analysis:"]
                for r in results:
                    lines.append(f"  {r['file']}: {r['total']} lines, {r['code']} code")
                
                return ToolResult(success=True, output="\n".join(lines),
                                metadata={"files_analyzed": len(results)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Analysis failed: {str(e)}")
        
        return [
            ToolSpec(name="lsp", description="Language Server Protocol operations",
                    input_schema={"type": "object", "properties": {"operation": {"type": "string"}, "file_path": {"type": "string"}}, "required": ["operation", "file_path"]},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_lsp),
            ToolSpec(name="lint", description="Run code linting",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "fix": {"type": "boolean"}}, "required": ["path"]},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_lint),
            ToolSpec(name="format", description="Format code files",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "check": {"type": "boolean"}}, "required": ["path"]},
                    required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_format),
            ToolSpec(name="code_review", description="Perform automated code review",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "focus": {"type": "array"}}, "required": ["path"]},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_code_review),
            ToolSpec(name="complexity_analysis", description="Analyze code complexity metrics",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "metrics": {"type": "array"}}, "required": ["path"]},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_complexity_analysis),
        ]
