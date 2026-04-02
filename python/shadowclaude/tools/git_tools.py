"""
Git 操作工具扩展模块
包含: git_status, git_diff, git_commit, git_push, git_branch, git_log
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import subprocess
import re


class GitTools:
    """Git 操作工具集合"""
    
    @staticmethod
    def _run_git(args: List[str], cwd: Optional[Path] = None, timeout: int = 30):
        """运行 git 命令"""
        try:
            cmd = ["git"] + args
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)
    
    @staticmethod
    def _check_git_repo(path: Path):
        """检查路径是否是 git 仓库"""
        if not path.exists():
            return False, f"Path does not exist: {path}"
        code, stdout, _ = GitTools._run_git(["rev-parse", "--show-toplevel"], path)
        if code == 0:
            return True, stdout.strip()
        return False, "Not a git repository"
    
    @staticmethod
    def get_all_specs(ToolSpec, ToolResult, PermissionMode):
        """获取所有 Git 工具规范"""
        
        def _handle_git_status(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                is_repo, msg = GitTools._check_git_repo(path)
                if not is_repo:
                    return ToolResult(success=False, output="", error=msg)
                
                code, stdout, stderr = GitTools._run_git(["status", "--porcelain", "-b"], cwd=path)
                if code != 0:
                    return ToolResult(success=False, output="", error=stderr)
                
                output = stdout if stdout.strip() else "Working tree clean - no changes to commit."
                branch_code, branch_out, _ = GitTools._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
                current_branch = branch_out.strip() if branch_code == 0 else "unknown"
                
                return ToolResult(success=True, output=output,
                                metadata={"git_root": msg, "current_branch": current_branch})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"git status failed: {str(e)}")
        
        def _handle_git_diff(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                is_repo, msg = GitTools._check_git_repo(path)
                if not is_repo:
                    return ToolResult(success=False, output="", error=msg)
                
                staged = input_data.get("staged", False)
                args = ["diff"]
                if staged:
                    args.append("--staged")
                
                code, stdout, stderr = GitTools._run_git(args, cwd=path)
                if code != 0:
                    return ToolResult(success=False, output="", error=stderr)
                
                return ToolResult(success=True, output=stdout or "No differences found.",
                                metadata={"git_root": msg, "staged": staged})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"git diff failed: {str(e)}")
        
        def _handle_git_commit(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                is_repo, msg = GitTools._check_git_repo(path)
                if not is_repo:
                    return ToolResult(success=False, output="", error=msg)
                
                message = input_data["message"]
                all_changes = input_data.get("all", False)
                
                if all_changes:
                    GitTools._run_git(["add", "-A"], cwd=path)
                
                code, stdout, stderr = GitTools._run_git(["commit", "-m", message], cwd=path)
                if code != 0:
                    return ToolResult(success=False, output="", error=stderr)
                
                return ToolResult(success=True, output=f"Committed successfully\n{stdout}",
                                metadata={"git_root": msg})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"git commit failed: {str(e)}")
        
        def _handle_git_push(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                is_repo, msg = GitTools._check_git_repo(path)
                if not is_repo:
                    return ToolResult(success=False, output="", error=msg)
                
                remote = input_data.get("remote", "origin")
                branch = input_data.get("branch", "main")
                force = input_data.get("force", False)
                
                args = ["push", remote, branch]
                if force:
                    args.append("--force")
                
                code, stdout, stderr = GitTools._run_git(args, cwd=path)
                if code != 0:
                    return ToolResult(success=False, output="", error=stderr)
                
                return ToolResult(success=True, output=f"Pushed to {remote}/{branch}\n{stdout or stderr}",
                                metadata={"remote": remote, "branch": branch})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"git push failed: {str(e)}")
        
        def _handle_git_branch(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                is_repo, msg = GitTools._check_git_repo(path)
                if not is_repo:
                    return ToolResult(success=False, output="", error=msg)
                
                action = input_data.get("action", "list")
                
                if action == "list":
                    code, stdout, stderr = GitTools._run_git(["branch", "-v"], cwd=path)
                    return ToolResult(success=True, output=stdout or "No branches", metadata={})
                
                elif action == "create":
                    branch_name = input_data.get("branch_name")
                    if not branch_name:
                        return ToolResult(success=False, output="", error="branch_name required")
                    code, stdout, stderr = GitTools._run_git(["checkout", "-b", branch_name], cwd=path)
                    return ToolResult(success=True, output=f"Created branch: {branch_name}\n{stdout}",
                                    metadata={"branch": branch_name})
                
                elif action == "delete":
                    branch_name = input_data.get("branch_name")
                    if not branch_name:
                        return ToolResult(success=False, output="", error="branch_name required")
                    code, stdout, stderr = GitTools._run_git(["branch", "-d", branch_name], cwd=path)
                    return ToolResult(success=True, output=f"Deleted branch: {branch_name}",
                                    metadata={"deleted_branch": branch_name})
                
                return ToolResult(success=False, output="", error=f"Unknown action: {action}")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"git branch failed: {str(e)}")
        
        def _handle_git_log(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                is_repo, msg = GitTools._check_git_repo(path)
                if not is_repo:
                    return ToolResult(success=False, output="", error=msg)
                
                max_count = input_data.get("max_count", 10)
                oneline = input_data.get("oneline", False)
                
                args = ["log", f"-n {max_count}"]
                if oneline:
                    args.append("--oneline")
                
                code, stdout, stderr = GitTools._run_git(args, cwd=path)
                if code != 0:
                    return ToolResult(success=False, output="", error=stderr)
                
                return ToolResult(success=True, output=stdout or "No commits found",
                                metadata={"commits": len([l for l in stdout.split('\n') if l.strip()])})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"git log failed: {str(e)}")
        
        return [
            ToolSpec(name="git_status", description="Show the working tree status",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_git_status),
            ToolSpec(name="git_diff", description="Show changes between commits",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "staged": {"type": "boolean"}}},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_git_diff),
            ToolSpec(name="git_commit", description="Record changes to the repository",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "message": {"type": "string"}, "all": {"type": "boolean"}}, "required": ["message"]},
                    required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_git_commit),
            ToolSpec(name="git_push", description="Update remote refs",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "remote": {"type": "string"}, "branch": {"type": "string"}, "force": {"type": "boolean"}}},
                    required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_git_push),
            ToolSpec(name="git_branch", description="List, create, or delete branches",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "action": {"type": "string"}, "branch_name": {"type": "string"}}},
                    required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_git_branch),
            ToolSpec(name="git_log", description="Show commit logs",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "max_count": {"type": "integer"}, "oneline": {"type": "boolean"}}},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_git_log),
        ]
