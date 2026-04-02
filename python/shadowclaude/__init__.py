# ShadowClaude - Python 核心实现
# 基于 claw-code 架构 + Claude Code 精华功能

__version__ = "0.1.0"
__author__ = "ShadowClaude Team"

from .query_engine import QueryEngine, QueryEngineConfig
from .tools import ToolRegistry, ToolExecution
from .memory import MemorySystem, SemanticMemory, EpisodicMemory, WorkingMemory
from .agents import Coordinator, SwarmWorker, AgentType
from .kairos import KairosDaemon
from .buddy import BuddySystem
from .undercover import UndercoverMode

__all__ = [
    "QueryEngine",
    "QueryEngineConfig",
    "ToolRegistry",
    "ToolExecution",
    "MemorySystem",
    "SemanticMemory",
    "EpisodicMemory",
    "WorkingMemory",
    "Coordinator",
    "SwarmWorker",
    "AgentType",
    "KairosDaemon",
    "BuddySystem",
    "UndercoverMode",
]
