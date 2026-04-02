"""
系统工具扩展模块
包含: clipboard, screenshot, notification
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import subprocess
import platform


class SystemTools:
    """系统操作工具集合"""
    
    @staticmethod
    def get_all_specs(ToolSpec, ToolResult, PermissionMode):
        """获取所有系统工具规范"""
        
        system = platform.system()
        
        def _handle_clipboard(input_data: Dict) -> ToolResult:
            try:
                action = input_data.get("action", "read")
                content = input_data.get("content")
                
                if system == "Darwin":
                    if action == "read":
                        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
                        return ToolResult(success=True, output=result.stdout, metadata={"action": "read"})
                    elif action == "write":
                        result = subprocess.run(["pbcopy"], input=content, capture_output=True, text=True, timeout=5)
                        return ToolResult(success=True, output="Copied to clipboard", metadata={"action": "write"})
                elif system == "Linux":
                    if action == "read":
                        for cmd in [["xclip", "-o", "-selection", "clipboard"], ["xsel", "-o", "-b"]]:
                            try:
                                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                                if result.returncode == 0:
                                    return ToolResult(success=True, output=result.stdout)
                            except FileNotFoundError:
                                continue
                    elif action == "write":
                        for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "-b"]]:
                            try:
                                result = subprocess.run(cmd, input=content, capture_output=True, text=True, timeout=5)
                                if result.returncode == 0:
                                    return ToolResult(success=True, output="Copied to clipboard")
                            except FileNotFoundError:
                                continue
                
                return ToolResult(success=False, output="", error=f"Clipboard not supported on {system}")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Clipboard failed: {str(e)}")
        
        def _handle_screenshot(input_data: Dict) -> ToolResult:
            try:
                import time
                mode = input_data.get("mode", "full")
                output = input_data.get("output", f"/tmp/screenshot_{int(time.time())}.png")
                delay = input_data.get("delay", 0)
                
                if delay > 0:
                    time.sleep(delay)
                
                output_path = Path(output)
                
                if system == "Darwin":
                    cmd = ["screencapture", "-x", str(output_path)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                elif system == "Linux":
                    for tool in [["gnome-screenshot", "-f", str(output_path)],
                                 ["import", "-window", "root", str(output_path)],
                                 ["scrot", str(output_path)]]:
                        try:
                            result = subprocess.run(tool, capture_output=True, text=True, timeout=10)
                            if result.returncode == 0:
                                break
                        except FileNotFoundError:
                            continue
                else:
                    return ToolResult(success=False, output="", error=f"Screenshot not supported on {system}")
                
                if result.returncode == 0 and output_path.exists():
                    size = output_path.stat().st_size
                    return ToolResult(success=True, output=f"Screenshot saved: {output_path} ({size} bytes)",
                                    metadata={"path": str(output_path), "size": size})
                return ToolResult(success=False, output="", error=result.stderr)
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Screenshot failed: {str(e)}")
        
        def _handle_notification(input_data: Dict) -> ToolResult:
            try:
                title = input_data["title"]
                message = input_data["message"]
                urgency = input_data.get("urgency", "normal")
                
                if system == "Darwin":
                    script = f'display notification "{message}" with title "{title}"'
                    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
                elif system == "Linux":
                    try:
                        cmd = ["notify-send", title, message, "-u", urgency]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    except FileNotFoundError:
                        try:
                            result = subprocess.run(["dunstify", title, message], capture_output=True, text=True, timeout=10)
                        except FileNotFoundError:
                            return ToolResult(success=False, output="", error="notify-send not found")
                else:
                    return ToolResult(success=False, output="", error=f"Notification not supported on {system}")
                
                return ToolResult(success=result.returncode == 0, output=f"Notification sent: {title}",
                                metadata={"title": title})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Notification failed: {str(e)}")
        
        return [
            ToolSpec(name="clipboard", description="Read from or write to system clipboard",
                    input_schema={"type": "object", "properties": {"action": {"type": "string"}, "content": {"type": "string"}}},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_clipboard),
            ToolSpec(name="screenshot", description="Capture screenshots",
                    input_schema={"type": "object", "properties": {"mode": {"type": "string"}, "output": {"type": "string"}, "delay": {"type": "integer"}}},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_screenshot),
            ToolSpec(name="notification", description="Send desktop notifications",
                    input_schema={"type": "object", "properties": {"title": {"type": "string"}, "message": {"type": "string"}, "urgency": {"type": "string"}}, "required": ["title", "message"]},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_notification),
        ]
