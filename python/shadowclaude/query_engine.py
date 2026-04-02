"""
QueryEngine - 核心查询引擎
基于 Claude Code 的 QueryEngine.ts 架构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
from enum import Enum
import json
import hashlib
import time
from pathlib import Path


class StopReason(Enum):
    COMPLETED = "completed"
    MAX_TURNS_REACHED = "max_turns_reached"
    MAX_BUDGET_REACHED = "max_budget_reached"
    USER_INTERRUPT = "user_interrupt"
    ERROR = "error"


@dataclass
class TurnResult:
    """单次对话回合结果"""
    prompt: str
    output: str
    matched_commands: Tuple[str, ...]
    matched_tools: Tuple[str, ...]
    tool_calls: List[Dict[str, Any]]
    usage: Dict[str, int]
    stop_reason: StopReason
    duration_ms: int


@dataclass
class QueryEngineConfig:
    """查询引擎配置"""
    max_turns: int = 32
    max_budget_tokens: int = 200_000
    compact_after_turns: int = 12
    cache_static_prompt: bool = True
    enable_reflection: bool = True
    enable_auto_compact: bool = True
    enable_semantic_memory: bool = True
    enable_episodic_memory: bool = True
    enable_kairos: bool = False
    model: str = "claude-sonnet-4-6"
    
    # Prompt Cache 配置
    static_segment_size: int = 4000  # 静态段 token 数
    dynamic_segment_ratio: float = 0.6  # 动态段比例


@dataclass
class PromptSegment:
    """Prompt 分段（用于缓存优化）"""
    content: str
    is_static: bool  # True = 可缓存，False = 每次变化
    cache_key: Optional[str] = None
    
    def compute_cache_key(self) -> str:
        if self.cache_key:
            return self.cache_key
        return hashlib.md5(self.content.encode()).hexdigest()[:16]


class QueryEngine:
    """
    核心查询引擎 - TAOR 循环实现
    Think → Act → Observe → Repeat
    """
    
    def __init__(self, config: Optional[QueryEngineConfig] = None):
        self.config = config or QueryEngineConfig()
        self.session_id = self._generate_session_id()
        
        # 对话状态
        self.messages: List[Dict[str, Any]] = []
        self.turn_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        # 记忆系统（延迟初始化）
        self._memory_system = None
        self._tool_registry = None
        self._coordinator = None
        
        # Prompt 分段缓存
        self._static_segments: List[PromptSegment] = []
        self._dynamic_segments: List[PromptSegment] = []
        
        # 运行状态
        self._is_running = False
        self._current_turn = 0
        
    def _generate_session_id(self) -> str:
        """生成唯一会话 ID"""
        timestamp = int(time.time() * 1000000)
        return f"sc-{timestamp:015x}"
    
    @property
    def memory_system(self):
        """延迟初始化记忆系统"""
        if self._memory_system is None:
            from .memory import MemorySystem
            self._memory_system = MemorySystem(
                enable_semantic=self.config.enable_semantic_memory,
                enable_episodic=self.config.enable_episodic_memory,
            )
        return self._memory_system
    
    @property
    def tool_registry(self):
        """延迟初始化工具注册表"""
        if self._tool_registry is None:
            from .tools import ToolRegistry
            self._tool_registry = ToolRegistry()
        return self._tool_registry
    
    def build_prompt_segments(self, user_input: str, context: Optional[Dict] = None) -> List[PromptSegment]:
        """
        构建分段 Prompt（Prompt Cache 优化）
        
        静态段（可缓存）:
        - 系统身份定义
        - 工具基础描述
        - 安全规则
        
        动态段（不可缓存）:
        - 当前工作目录
        - Git 状态
        - 用户输入
        """
        segments = []
        
        # ===== 静态段 =====
        system_identity = """You are ShadowClaude, an AI programming assistant created by the ShadowClaude Team.
You are an expert in software engineering, code review, debugging, and system architecture.
You help users write, understand, and improve code."""
        
        segments.append(PromptSegment(
            content=system_identity,
            is_static=True,
            cache_key="system_identity_v1"
        ))
        
        # 工具描述（按字母排序确保确定性）
        tool_descriptions = self.tool_registry.get_tool_descriptions()
        tool_text = "\n\n".join(sorted(tool_descriptions))
        segments.append(PromptSegment(
            content=f"## Available Tools\n\n{tool_text}",
            is_static=True,
            cache_key=hashlib.md5(tool_text.encode()).hexdigest()[:16]
        ))
        
        # 安全规则
        safety_rules = """## Safety Rules
1. Never execute commands that could harm the system
2. Always ask for confirmation before destructive operations
3. Respect user privacy and data confidentiality"""
        
        segments.append(PromptSegment(
            content=safety_rules,
            is_static=True,
            cache_key="safety_rules_v1"
        ))
        
        # ===== 动态段 =====
        # 上下文信息
        context_parts = []
        if context:
            if 'cwd' in context:
                context_parts.append(f"Current directory: {context['cwd']}")
            if 'git_status' in context:
                context_parts.append(f"Git status: {context['git_status']}")
        
        context_text = "\n".join(context_parts) if context_parts else "No additional context"
        segments.append(PromptSegment(
            content=f"## Context\n\n{context_text}",
            is_static=False
        ))
        
        # 用户输入（永远动态）
        segments.append(PromptSegment(
            content=f"## User Request\n\n{user_input}",
            is_static=False
        ))
        
        return segments
    
    def compact_if_needed(self) -> bool:
        """
        对话压缩 - 当超过阈值时触发
        基于 Claude Code 的 9段式摘要
        """
        if len(self.messages) < self.config.compact_after_turns:
            return False
        
        if not self.config.enable_auto_compact:
            return False
        
        # 执行压缩
        from .memory.compact import CompactEngine
        compactor = CompactEngine()
        
        summary = compactor.compact_session(self.messages)
        
        # 保留最近的 2 条消息 + 摘要
        recent_messages = self.messages[-2:] if len(self.messages) >= 2 else self.messages
        self.messages = [
            {"role": "system", "content": f"## Previous Conversation Summary\n\n{summary}"},
            *recent_messages
        ]
        
        return True
    
    def submit_message(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        tools_allowed: Optional[List[str]] = None
    ) -> TurnResult:
        """
        提交消息并执行 TAOR 循环
        
        Returns:
            TurnResult: 包含输出、工具调用、token 使用等信息
        """
        start_time = time.time()
        
        # 检查预算
        if self.turn_count >= self.config.max_turns:
            return TurnResult(
                prompt=prompt,
                output="Maximum number of turns reached.",
                matched_commands=(),
                matched_tools=(),
                tool_calls=[],
                usage={"input_tokens": 0, "output_tokens": 0},
                stop_reason=StopReason.MAX_TURNS_REACHED,
                duration_ms=0
            )
        
        # 构建 Prompt
        segments = self.build_prompt_segments(prompt, context)
        full_prompt = self._assemble_prompt(segments)
        
        # 记录 token 使用（估算）
        input_tokens = len(full_prompt.split())  # 简化估算
        
        # 这里应该调用 LLM API
        # 为了演示，返回模拟结果
        output = self._mock_llm_call(full_prompt, tools_allowed)
        output_tokens = len(output.split())
        
        # 解析工具调用
        tool_calls = self._parse_tool_calls(output)
        
        # 执行工具
        executed_tools = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            
            if tools_allowed and tool_name not in tools_allowed:
                continue
            
            result = self.tool_registry.execute(tool_name, tool_input)
            executed_tools.append({
                "tool": tool_name,
                "input": tool_input,
                "output": result
            })
        
        # 更新状态
        self.turn_count += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        # 检查是否需要压缩
        self.compact_if_needed()
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return TurnResult(
            prompt=prompt,
            output=output,
            matched_commands=(),
            matched_tools=tuple(t["tool"] for t in executed_tools),
            tool_calls=executed_tools,
            usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
            stop_reason=StopReason.COMPLETED,
            duration_ms=duration_ms
        )
    
    def _assemble_prompt(self, segments: List[PromptSegment]) -> str:
        """组装分段 Prompt"""
        return "\n\n".join(segment.content for segment in segments)
    
    def _mock_llm_call(self, prompt: str, tools_allowed: Optional[List[str]]) -> str:
        """模拟 LLM 调用（实际应调用 API）"""
        # 实际实现中，这里会调用 Claude API
        return f"I've received your request. Let me help you with that.\n\nRequest length: {len(prompt)} chars"
    
    def _parse_tool_calls(self, output: str) -> List[Dict[str, Any]]:
        """从 LLM 输出中解析工具调用"""
        # 实际实现中，解析 XML/JSON 格式的工具调用
        # 例如: <tool_use>bash<parameter>ls</parameter></tool_use>
        return []
    
    def stream_submit_message(self, prompt: str, context: Optional[Dict] = None):
        """流式提交消息"""
        yield {"type": "message_start", "session_id": self.session_id}
        
        result = self.submit_message(prompt, context)
        
        yield {"type": "message_delta", "text": result.output}
        
        for tool_call in result.tool_calls:
            yield {"type": "tool_use", **tool_call}
        
        yield {
            "type": "message_stop",
            "usage": result.usage,
            "stop_reason": result.stop_reason.value,
            "duration_ms": result.duration_ms
        }
