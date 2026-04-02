"""
测试工具扩展模块
包含: run_tests, coverage_report
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import subprocess
import sys
import os


class TestTools:
    """测试操作工具集合"""
    
    @staticmethod
    def get_all_specs(ToolSpec, ToolResult, PermissionMode):
        """获取所有测试工具规范"""
        
        def _handle_run_tests(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                framework = input_data.get("framework", "auto")
                verbose = input_data.get("verbose", True)
                
                if not path.exists():
                    return ToolResult(success=False, output="", error=f"Path not found: {path}")
                
                # 自动检测框架
                if framework == "auto":
                    if list(path.rglob("*.py")):
                        framework = "pytest"
                    elif list(path.rglob("*.js")):
                        framework = "jest"
                
                # 构建命令
                if framework == "pytest":
                    cmd = ["pytest", str(path)]
                    if verbose:
                        cmd.append("-v")
                elif framework == "unittest":
                    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(path)]
                elif framework == "jest":
                    cmd = ["jest", str(path)]
                else:
                    return ToolResult(success=False, output="", error=f"Unknown framework: {framework}")
                
                env = os.environ.copy()
                env['PYTHONPATH'] = str(path) if path.is_dir() else str(path.parent)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
                
                output = result.stdout
                if result.stderr:
                    output += f"\n{result.stderr}"
                
                return ToolResult(success=result.returncode == 0, output=output[:5000],
                                metadata={"framework": framework, "exit_code": result.returncode})
            except FileNotFoundError:
                return ToolResult(success=False, output="", error=f"Test framework not found")
            except subprocess.TimeoutExpired:
                return ToolResult(success=False, output="", error="Tests timed out")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Tests failed: {str(e)}")
        
        def _handle_coverage_report(input_data: Dict) -> ToolResult:
            try:
                path = Path(input_data.get("path", ".")).resolve()
                output_format = input_data.get("output_format", "text")
                fail_under = input_data.get("fail_under")
                
                # 使用 pytest-cov
                cmd = ["pytest", "--cov", str(path), "--cov-report=term"]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                output = result.stdout
                if result.stderr:
                    output += f"\n{result.stderr}"
                
                # 解析覆盖率
                import re
                match = re.search(r'(\d+)%', output)
                coverage = float(match.group(1)) if match else None
                
                success = result.returncode == 0
                if fail_under and coverage and coverage < fail_under:
                    success = False
                    output += f"\nCoverage {coverage}% below threshold {fail_under}%"
                
                return ToolResult(success=success, output=output[:5000],
                                metadata={"coverage_percent": coverage})
            except FileNotFoundError:
                return ToolResult(success=False, output="", error="pytest-cov not found")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Coverage failed: {str(e)}")
        
        return [
            ToolSpec(name="run_tests", description="Run test suites",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "framework": {"type": "string"}, "verbose": {"type": "boolean"}}},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_run_tests),
            ToolSpec(name="coverage_report", description="Generate coverage reports",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}, "output_format": {"type": "string"}, "fail_under": {"type": "number"}}},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_coverage_report),
        ]
