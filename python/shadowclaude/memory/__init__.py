"""
三层记忆系统 - Semantic / Episodic / Working
基于认知科学启发的记忆架构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import json
import hashlib
import numpy as np
from collections import deque


@dataclass
class MemoryEntry:
    """记忆条目"""
    content: str
    timestamp: datetime
    source: str  # 来源：对话、文件、Web 等
    importance: float = 1.0  # 重要性评分 0-1
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticMemory:
    """
    语义记忆 - 长期稳定知识
    
    存储：
    - 代码规范、最佳实践
    - 项目架构知识
    - 用户偏好（稳定的）
    
    特点：
    - 只写入高信号内容
    - 自动去重
    - RAG 检索
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".shadowclaude" / "semantic_memory"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.entries: Dict[str, MemoryEntry] = {}  # hash -> entry
        self._load_from_disk()
    
    def _load_from_disk(self):
        """从磁盘加载记忆"""
        memory_file = self.storage_path / "memory.json"
        if memory_file.exists():
            try:
                with open(memory_file) as f:
                    data = json.load(f)
                for entry_data in data.get("entries", []):
                    entry = MemoryEntry(
                        content=entry_data["content"],
                        timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                        source=entry_data["source"],
                        importance=entry_data.get("importance", 1.0),
                        metadata=entry_data.get("metadata", {})
                    )
                    entry_hash = self._hash_content(entry.content)
                    self.entries[entry_hash] = entry
            except Exception as e:
                print(f"Warning: Failed to load semantic memory: {e}")
    
    def _hash_content(self, content: str) -> str:
        """内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def add(self, content: str, source: str = "conversation", importance: float = 1.0):
        """
        添加语义记忆
        
        Args:
            content: 记忆内容
            source: 来源
            importance: 重要性 (0-1)
        """
        # 只存储高重要性内容
        if importance < 0.7:
            return
        
        content_hash = self._hash_content(content)
        
        # 检查是否已存在
        if content_hash in self.entries:
            # 更新重要性
            existing = self.entries[content_hash]
            existing.importance = max(existing.importance, importance)
            return
        
        entry = MemoryEntry(
            content=content,
            timestamp=datetime.now(),
            source=source,
            importance=importance
        )
        
        self.entries[content_hash] = entry
        self._persist()
    
    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """
        检索相关记忆（简化版，实际应使用向量相似度）
        
        Args:
            query: 查询文本
            top_k: 返回数量
        
        Returns:
            相关记忆列表
        """
        query_lower = query.lower()
        
        # 简单的关键词匹配（实际应使用向量搜索）
        scored_entries = []
        for entry in self.entries.values():
            score = 0.0
            
            # 关键词匹配
            entry_lower = entry.content.lower()
            query_words = set(query_lower.split())
            entry_words = set(entry_lower.split())
            common_words = query_words & entry_words
            
            if common_words:
                score += len(common_words) / len(query_words)
            
            # 重要性加权
            score *= entry.importance
            
            # 时间衰减（越新的越重要）
            days_old = (datetime.now() - entry.timestamp).days
            time_factor = 1.0 / (1 + days_old / 30)  # 30天衰减一半
            score *= time_factor
            
            if score > 0:
                scored_entries.append((score, entry))
        
        # 排序并返回 top_k
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored_entries[:top_k]]
    
    def consolidate(self):
        """
        记忆整合 - 去除冗余，合并相似记忆
        """
        # 简化实现：只保留高重要性记忆
        to_remove = [
            h for h, e in self.entries.items()
            if e.importance < 0.5 and (datetime.now() - e.timestamp).days > 90
        ]
        for h in to_remove:
            del self.entries[h]
        
        if to_remove:
            self._persist()
    
    def _persist(self):
        """持久化到磁盘"""
        memory_file = self.storage_path / "memory.json"
        data = {
            "entries": [
                {
                    "content": e.content,
                    "timestamp": e.timestamp.isoformat(),
                    "source": e.source,
                    "importance": e.importance,
                    "metadata": e.metadata
                }
                for e in self.entries.values()
            ]
        }
        with open(memory_file, 'w') as f:
            json.dump(data, f, indent=2)


class EpisodicMemory:
    """
    情景记忆 - 过去的对话序列
    
    存储：
    - 完整对话历史
    - 任务执行过程
    - 决策理由
    
    特点：
    - 按时间索引
    - 按需检索
    """
    
    def __init__(self, max_episodes: int = 100):
        self.episodes: deque = deque(maxlen=max_episodes)
        self.current_episode: List[Dict] = []
    
    def start_episode(self, context: Dict[str, Any]):
        """开始新的情景"""
        if self.current_episode:
            self.end_episode()
        
        self.current_episode = [{
            "type": "start",
            "timestamp": datetime.now().isoformat(),
            "context": context
        }]
    
    def add_event(self, event_type: str, content: Any):
        """添加事件到当前情景"""
        self.current_episode.append({
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "content": content
        })
    
    def end_episode(self, summary: Optional[str] = None):
        """结束当前情景"""
        if not self.current_episode:
            return
        
        self.current_episode.append({
            "type": "end",
            "timestamp": datetime.now().isoformat(),
            "summary": summary
        })
        
        self.episodes.append({
            "events": self.current_episode,
            "summary": summary
        })
        
        self.current_episode = []
    
    def retrieve_similar(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索相似的历史情景"""
        # 简化实现：返回最近的情景
        return list(self.episodes)[-top_k:]
    
    def get_recent_context(self, n_events: int = 10) -> str:
        """获取最近的情景上下文"""
        if not self.episodes:
            return "No previous episodes"
        
        recent = list(self.episodes)[-1]
        events = recent.get("events", [])
        
        context_parts = []
        for event in events[-n_events:]:
            if event["type"] == "user_message":
                context_parts.append(f"User: {event['content']}")
            elif event["type"] == "assistant_message":
                context_parts.append(f"Assistant: {event['content'][:200]}...")
        
        return "\n".join(context_parts)


class WorkingMemory:
    """
    工作记忆 - 当前任务的动态上下文
    
    存储：
    - 当前对话窗口
    - 临时变量
    - 工具输出缓存
    
    特点：
    - 容量有限（受限于模型上下文）
    - 超出时用指针代替内容
    """
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.messages: List[Dict] = []
        self.variables: Dict[str, Any] = {}
        self.tool_outputs: Dict[str, str] = {}
    
    def add_message(self, role: str, content: str):
        """添加消息到工作记忆"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 如果超出容量，压缩旧消息
        self._compress_if_needed()
    
    def _compress_if_needed(self):
        """如果超出容量，压缩旧消息"""
        # 简化估算：每个 token 约 4 个字符
        total_chars = sum(len(m["content"]) for m in self.messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens > self.max_tokens * 0.9:
            # 保留最近的消息，压缩旧的
            to_compress = self.messages[:-5]  # 保留最近 5 条
            self.messages = self.messages[-5:]
            
            # 添加压缩摘要
            if to_compress:
                summary = f"[Previous {len(to_compress)} messages compressed]"
                self.messages.insert(0, {
                    "role": "system",
                    "content": summary,
                    "compressed": True
                })
    
    def set_variable(self, key: str, value: Any):
        """设置临时变量"""
        self.variables[key] = value
    
    def get_variable(self, key: str) -> Optional[Any]:
        """获取临时变量"""
        return self.variables.get(key)
    
    def cache_tool_output(self, tool_name: str, tool_input: str, output: str):
        """缓存工具输出"""
        cache_key = f"{tool_name}:{hashlib.md5(tool_input.encode()).hexdigest()[:16]}"
        self.tool_outputs[cache_key] = output
    
    def get_cached_tool_output(self, tool_name: str, tool_input: str) -> Optional[str]:
        """获取缓存的工具输出"""
        cache_key = f"{tool_name}:{hashlib.md5(tool_input.encode()).hexdigest()[:16]}"
        return self.tool_outputs.get(cache_key)
    
    def clear(self):
        """清空工作记忆"""
        self.messages.clear()
        self.variables.clear()
        self.tool_outputs.clear()


class MemorySystem:
    """
    记忆系统管理器
    协调三层记忆的交互
    """
    
    def __init__(
        self,
        enable_semantic: bool = True,
        enable_episodic: bool = True,
        working_memory_size: int = 8000
    ):
        self.semantic = SemanticMemory() if enable_semantic else None
        self.episodic = EpisodicMemory() if enable_episodic else None
        self.working = WorkingMemory(max_tokens=working_memory_size)
    
    def add_to_semantic(self, content: str, importance: float = 1.0):
        """添加到语义记忆"""
        if self.semantic:
            self.semantic.add(content, importance=importance)
    
    def retrieve_context(self, query: str) -> str:
        """
        检索相关上下文（整合三层记忆）
        
        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        
        # 1. 语义记忆（最稳定的知识）
        if self.semantic:
            semantic_results = self.semantic.retrieve(query, top_k=3)
            if semantic_results:
                context_parts.append("## Relevant Knowledge")
                for entry in semantic_results:
                    context_parts.append(f"- {entry.content}")
        
        # 2. 情景记忆（相似的历史对话）
        if self.episodic:
            similar_episodes = self.episodic.retrieve_similar(query, top_k=2)
            if similar_episodes:
                context_parts.append("\n## Similar Past Conversations")
                for ep in similar_episodes:
                    if ep.get("summary"):
                        context_parts.append(f"- {ep['summary']}")
        
        # 3. 工作记忆（最近的上下文）
        if self.working.messages:
            recent = self.working.messages[-3:]  # 最近 3 条
            context_parts.append("\n## Recent Context")
            for msg in recent:
                role = msg["role"]
                content = msg["content"][:200]  # 截断
                context_parts.append(f"{role}: {content}...")
        
        return "\n".join(context_parts) if context_parts else "No relevant context found."
    
    def consolidate(self):
        """整合记忆系统"""
        if self.semantic:
            self.semantic.consolidate()
