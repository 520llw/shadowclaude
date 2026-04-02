"""
部署工具扩展模块
包含: docker_build, docker_run, ssh_exec
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import subprocess


class DeployTools:
    """部署操作工具集合"""
    
    @staticmethod
    def get_all_specs(ToolSpec, ToolResult, PermissionMode):
        """获取所有部署工具规范"""
        
        def _handle_docker_build(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                tag = input_data.get("tag")
                
                dockerfile = path / "Dockerfile"
                if not dockerfile.exists():
                    return ToolResult(success=False, output="", error=f"Dockerfile not found: {dockerfile}")
                
                cmd = ["docker", "build"]
                if tag:
                    cmd.extend(["-t", tag])
                cmd.append(str(path))
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                
                output = result.stdout
                if result.stderr:
                    output += f"\n{result.stderr}"
                
                return ToolResult(success=result.returncode == 0, output=output[-3000:],
                                metadata={"tag": tag, "exit_code": result.returncode})
            except FileNotFoundError:
                return ToolResult(success=False, output="", error="Docker not found")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Docker build failed: {str(e)}")
        
        def _handle_docker_run(input_data: Dict) -> ToolResult:
            try:
                image = input_data["image"]
                name = input_data.get("name")
                ports = input_data.get("ports", [])
                detach = input_data.get("detach", False)
                
                cmd = ["docker", "run"]
                if detach:
                    cmd.append("-d")
                if name:
                    cmd.extend(["--name", name])
                for port in ports:
                    cmd.extend(["-p", port])
                cmd.append(image)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                return ToolResult(success=result.returncode == 0,
                                output=result.stdout or result.stderr,
                                metadata={"container": result.stdout.strip() if result.stdout else None})
            except FileNotFoundError:
                return ToolResult(success=False, output="", error="Docker not found")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Docker run failed: {str(e)}")
        
        def _handle_ssh_exec(input_data: Dict) -> ToolResult:
            try:
                host = input_data["host"]
                command = input_data["command"]
                user = input_data.get("user", "root")
                key_file = input_data.get("key_file")
                
                cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
                if key_file:
                    cmd.extend(["-i", key_file])
                cmd.append(f"{user}@{host}")
                cmd.append(command)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                output = result.stdout
                if result.stderr:
                    output += f"\n[stderr]:\n{result.stderr}"
                
                return ToolResult(success=result.returncode == 0, output=output,
                                metadata={"host": host, "exit_code": result.returncode})
            except FileNotFoundError:
                return ToolResult(success=False, output="", error="SSH not found")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"SSH failed: {str(e)}")
        
        return [
            ToolSpec(name="docker_build", description="Build Docker images",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "tag": {"type": "string"}}},
                    required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_docker_build),
            ToolSpec(name="docker_run", description="Run Docker containers",
                    input_schema={"type": "object", "properties": {"image": {"type": "string"}, "name": {"type": "string"}, "ports": {"type": "array"}, "detach": {"type": "boolean"}}, "required": ["image"]},
                    required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_docker_run),
            ToolSpec(name="ssh_exec", description="Execute commands via SSH",
                    input_schema={"type": "object", "properties": {"host": {"type": "string"}, "command": {"type": "string"}, "user": {"type": "string"}, "key_file": {"type": "string"}}, "required": ["host", "command"]},
                    required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_ssh_exec),
        ]
