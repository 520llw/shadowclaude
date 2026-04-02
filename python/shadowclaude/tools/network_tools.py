"""
网络工具扩展模块
包含: curl, download, upload
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import urllib.request
import urllib.parse
import json
import os


class NetworkTools:
    """网络操作工具集合"""
    
    DEFAULT_USER_AGENT = "ShadowClaude/0.1"
    
    @staticmethod
    def get_all_specs(ToolSpec, ToolResult, PermissionMode):
        """获取所有网络工具规范"""
        
        def _handle_curl(input_data: Dict) -> ToolResult:
            try:
                url = input_data["url"]
                method = input_data.get("method", "GET")
                headers = input_data.get("headers", {})
                json_body = input_data.get("json_body")
                timeout = input_data.get("timeout", 30)
                
                if not url.startswith(('http://', 'https://')):
                    url = 'http://' + url
                
                req_headers = {'User-Agent': NetworkTools.DEFAULT_USER_AGENT}
                req_headers.update(headers)
                
                req_body = None
                if json_body:
                    req_body = json.dumps(json_body).encode('utf-8')
                    req_headers['Content-Type'] = 'application/json'
                
                req = urllib.request.Request(url, data=req_body, headers=req_headers, method=method)
                
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8', errors='replace')
                    
                output_lines = [f"HTTP {response.status}", f"URL: {url}"]
                output_lines.append(f"\nBody ({len(content)} bytes):")
                output_lines.append(content[:5000])
                if len(content) > 5000:
                    output_lines.append(f"... ({len(content) - 5000} more)")
                
                return ToolResult(success=True, output="\n".join(output_lines),
                                metadata={"status": response.status, "url": url})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Request failed: {str(e)}")
        
        def _handle_download(input_data: Dict) -> ToolResult:
            try:
                url = input_data["url"]
                output_path_str = input_data.get("output")
                
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                if not output_path_str:
                    filename = os.path.basename(urllib.parse.urlparse(url).path) or "download"
                    output_path = Path("./" + filename)
                else:
                    output_path = Path(output_path_str)
                
                output_path = output_path.resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                urllib.request.urlretrieve(url, output_path)
                
                size = output_path.stat().st_size
                return ToolResult(success=True, output=f"Downloaded: {output_path} ({size} bytes)",
                                metadata={"path": str(output_path), "size": size})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Download failed: {str(e)}")
        
        def _handle_upload(input_data: Dict) -> ToolResult:
            try:
                url = input_data["url"]
                file_path = input_data.get("file")
                
                if not file_path:
                    return ToolResult(success=False, output="", error="File path required")
                
                path = Path(file_path)
                if not path.exists():
                    return ToolResult(success=False, output="", error=f"File not found: {path}")
                
                import mimetypes
                content_type = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
                
                with open(path, 'rb') as f:
                    data = f.read()
                
                req_headers = {'User-Agent': NetworkTools.DEFAULT_USER_AGENT}
                req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
                
                with urllib.request.urlopen(req, timeout=60) as response:
                    content = response.read().decode('utf-8', errors='replace')
                
                return ToolResult(success=True, output=f"Uploaded: {path.name}\nResponse: {content[:500]}",
                                metadata={"file": str(path), "size": len(data)})
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Upload failed: {str(e)}")
        
        return [
            ToolSpec(name="curl", description="Make HTTP requests with full control",
                    input_schema={"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}, "headers": {"type": "object"}, "json_body": {"type": "object"}}, "required": ["url"]},
                    required_permission=PermissionMode.READ_ONLY, handler=_handle_curl),
            ToolSpec(name="download", description="Download files from URLs",
                    input_schema={"type": "object", "properties": {"url": {"type": "string"}, "output": {"type": "string"}}, "required": ["url"]},
                    required_permission=PermissionMode.WORKSPACE_WRITE, handler=_handle_download),
            ToolSpec(name="upload", description="Upload files to remote servers",
                    input_schema={"type": "object", "properties": {"url": {"type": "string"}, "file": {"type": "string"}}, "required": ["url"]},
                    required_permission=PermissionMode.DANGER_FULL_ACCESS, handler=_handle_upload),
        ]
