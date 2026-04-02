"""
Mock 文件系统 - 模拟文件操作
"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import re
import fnmatch


@dataclass
class MockFile:
    """Mock 文件对象"""
    path: str
    content: str = ""
    is_directory: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    permissions: str = "644"
    
    def read_text(self) -> str:
        """读取文本内容"""
        return self.content
    
    def write_text(self, content: str):
        """写入文本内容"""
        self.content = content
        self.modified_at = datetime.now()
    
    def read_lines(self) -> List[str]:
        """按行读取"""
        return self.content.split('\n')
    
    @property
    def size(self) -> int:
        """文件大小"""
        return len(self.content.encode('utf-8'))


class MockFileSystem:
    """
    Mock 文件系统
    用于测试文件操作而无需真实文件系统
    """
    
    def __init__(self, root: str = "/mock"):
        self.root = root
        self._files: Dict[str, MockFile] = {}
        self._cwd = root
        
        # 创建根目录
        self._mkdir_p(root)
    
    def _normalize_path(self, path: str) -> str:
        """规范化路径"""
        if not path.startswith('/'):
            path = f"{self._cwd}/{path}"
        
        # 处理 .. 和 .
        parts = path.split('/')
        normalized = []
        for part in parts:
            if part == '..':
                if normalized:
                    normalized.pop()
            elif part and part != '.':
                normalized.append(part)
        
        return '/' + '/'.join(normalized)
    
    def _mkdir_p(self, path: str):
        """递归创建目录"""
        parts = path.split('/')
        current = ""
        for part in parts:
            if not part:
                continue
            current += f"/{part}"
            if current not in self._files:
                self._files[current] = MockFile(
                    path=current,
                    is_directory=True
                )
    
    def create_file(self, path: str, content: str = ""):
        """创建文件"""
        normalized = self._normalize_path(path)
        
        # 确保父目录存在
        parent = '/'.join(normalized.split('/')[:-1])
        if parent:
            self._mkdir_p(parent)
        
        self._files[normalized] = MockFile(
            path=normalized,
            content=content
        )
    
    def create_directory(self, path: str):
        """创建目录"""
        normalized = self._normalize_path(path)
        self._mkdir_p(normalized)
    
    def read_file(self, path: str, offset: int = 0, limit: Optional[int] = None) -> str:
        """读取文件"""
        normalized = self._normalize_path(path)
        
        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        
        file = self._files[normalized]
        if file.is_directory:
            raise IsADirectoryError(f"Path is a directory: {path}")
        
        lines = file.read_lines()
        
        if offset > 0:
            lines = lines[offset:]
        
        if limit is not None:
            lines = lines[:limit]
        
        return '\n'.join(lines)
    
    def write_file(self, path: str, content: str):
        """写入文件"""
        normalized = self._normalize_path(path)
        
        # 确保父目录存在
        parent = '/'.join(normalized.split('/')[:-1])
        if parent:
            self._mkdir_p(parent)
        
        if normalized in self._files and self._files[normalized].is_directory:
            raise IsADirectoryError(f"Path is a directory: {path}")
        
        self._files[normalized] = MockFile(
            path=normalized,
            content=content
        )
    
    def edit_file(self, path: str, old_string: str, new_string: str, replace_all: bool = False) -> int:
        """编辑文件内容"""
        normalized = self._normalize_path(path)
        
        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        
        file = self._files[normalized]
        content = file.content
        
        if replace_all:
            count = content.count(old_string)
            new_content = content.replace(old_string, new_string)
        else:
            if old_string not in content:
                raise ValueError(f"String not found in file: {old_string[:50]}...")
            count = 1
            new_content = content.replace(old_string, new_string, 1)
        
        file.write_text(new_content)
        return count
    
    def delete_file(self, path: str):
        """删除文件"""
        normalized = self._normalize_path(path)
        
        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        
        del self._files[normalized]
    
    def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        normalized = self._normalize_path(path)
        return normalized in self._files
    
    def is_directory(self, path: str) -> bool:
        """检查是否为目录"""
        normalized = self._normalize_path(path)
        return normalized in self._files and self._files[normalized].is_directory
    
    def is_file(self, path: str) -> bool:
        """检查是否为文件"""
        normalized = self._normalize_path(path)
        return normalized in self._files and not self._files[normalized].is_directory
    
    def glob_search(self, pattern: str, path: str = ".") -> List[str]:
        """Glob 搜索"""
        base_path = self._normalize_path(path)
        matches = []
        
        for file_path in self._files:
            if not file_path.startswith(base_path):
                continue
            
            relative = file_path[len(base_path):].lstrip('/')
            if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(file_path.split('/')[-1], pattern):
                if not self._files[file_path].is_directory:
                    matches.append(file_path)
        
        return matches
    
    def grep_search(
        self,
        pattern: str,
        path: str = ".",
        context: int = 0
    ) -> List[Dict]:
        """Grep 搜索"""
        base_path = self._normalize_path(path)
        matches = []
        regex = re.compile(pattern)
        
        for file_path, file in self._files.items():
            if file.is_directory:
                continue
            
            if not file_path.startswith(base_path):
                continue
            
            lines = file.read_lines()
            for i, line in enumerate(lines):
                if regex.search(line):
                    match_info = {
                        "file": file_path,
                        "line": i + 1,
                        "content": line,
                        "context": []
                    }
                    
                    # 添加上下文
                    start = max(0, i - context)
                    end = min(len(lines), i + context + 1)
                    match_info["context"] = lines[start:end]
                    
                    matches.append(match_info)
        
        return matches
    
    def list_directory(self, path: str = ".") -> List[str]:
        """列出目录内容"""
        normalized = self._normalize_path(path)
        
        if normalized not in self._files:
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not self._files[normalized].is_directory:
            raise NotADirectoryError(f"Path is not a directory: {path}")
        
        results = []
        for file_path in self._files:
            if file_path == normalized:
                continue
            
            # 检查是否是直接子项
            relative = file_path[len(normalized):].lstrip('/')
            if '/' not in relative:
                results.append(file_path)
        
        return results
    
    def get_file_size(self, path: str) -> int:
        """获取文件大小"""
        normalized = self._normalize_path(path)
        
        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        
        return self._files[normalized].size
    
    def reset(self):
        """重置文件系统"""
        self._files.clear()
        self._cwd = self.root
        self._mkdir_p(self.root)
    
    def snapshot(self) -> Dict[str, str]:
        """创建快照"""
        return {
            path: file.content
            for path, file in self._files.items()
            if not file.is_directory
        }
    
    def restore(self, snapshot: Dict[str, str]):
        """从快照恢复"""
        self.reset()
        for path, content in snapshot.items():
            self.create_file(path, content)
