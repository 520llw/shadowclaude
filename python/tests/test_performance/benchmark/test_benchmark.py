"""
性能基准测试
测试系统各组件的性能基准
"""

import pytest
import time
from shadowclaude.query_engine import QueryEngine, QueryEngineConfig
from shadowclaude.memory import SemanticMemory, EpisodicMemory, WorkingMemory
from shadowclaude.tools import ToolRegistry
from shadowclaude.agents import Coordinator


class BenchmarkMixin:
    """基准测试混入类"""
    
    def benchmark(self, func, iterations=100, warmup=10):
        """运行基准测试"""
        # 预热
        for _ in range(warmup):
            func()
        
        # 正式测试
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        return {
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times),
            "median": sorted(times)[len(times) // 2],
            "total": sum(times)
        }


class TestQueryEngineBenchmark(BenchmarkMixin):
    """测试 QueryEngine 性能基准"""
    
    def test_submit_message_benchmark(self):
        """测试消息提交性能"""
        engine = QueryEngine()
        
        def submit():
            engine.submit_message("Test message")
        
        stats = self.benchmark(submit, iterations=50, warmup=5)
        
        # 平均应在 100ms 以内
        assert stats["avg"] < 0.1, f"Average time {stats['avg']}s too slow"
        print(f"Submit message avg: {stats['avg']*1000:.2f}ms")
    
    def test_prompt_building_benchmark(self):
        """测试 Prompt 构建性能"""
        engine = QueryEngine()
        
        def build():
            engine.build_prompt_segments("Test prompt with some content")
        
        stats = self.benchmark(build, iterations=1000, warmup=100)
        
        # 应该非常快
        assert stats["avg"] < 0.001, f"Average time {stats['avg']}s too slow"
        print(f"Prompt build avg: {stats['avg']*1000:.2f}ms")
    
    def test_stream_submit_benchmark(self):
        """测试流式提交性能"""
        engine = QueryEngine()
        
        def stream():
            list(engine.stream_submit_message("Test"))
        
        stats = self.benchmark(stream, iterations=50, warmup=5)
        
        assert stats["avg"] < 0.1
        print(f"Stream submit avg: {stats['avg']*1000:.2f}ms")


class TestMemoryBenchmark(BenchmarkMixin):
    """测试记忆系统性能基准"""
    
    def test_semantic_add_benchmark(self, tmp_path):
        """测试语义记忆添加性能"""
        memory = SemanticMemory(storage_path=tmp_path)
        counter = [0]
        
        def add():
            memory.add(f"Content {counter[0]}", importance=0.8)
            counter[0] += 1
        
        stats = self.benchmark(add, iterations=100, warmup=10)
        
        assert stats["avg"] < 0.01
        print(f"Semantic add avg: {stats['avg']*1000:.2f}ms")
    
    def test_semantic_retrieve_benchmark(self, tmp_path):
        """测试语义记忆检索性能"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        # 预填充数据
        for i in range(100):
            memory.add(f"Content about topic {i}", importance=0.8)
        
        def retrieve():
            memory.retrieve("topic", top_k=5)
        
        stats = self.benchmark(retrieve, iterations=1000, warmup=100)
        
        assert stats["avg"] < 0.001
        print(f"Semantic retrieve avg: {stats['avg']*1000:.2f}ms")
    
    def test_working_add_message_benchmark(self):
        """测试工作记忆添加消息性能"""
        memory = WorkingMemory()
        counter = [0]
        
        def add():
            memory.add_message("user", f"Message {counter[0]}")
            counter[0] += 1
        
        stats = self.benchmark(add, iterations=1000, warmup=100)
        
        assert stats["avg"] < 0.0001
        print(f"Working add avg: {stats['avg']*1000:.2f}ms")
    
    def test_episodic_add_event_benchmark(self):
        """测试情景记忆添加事件性能"""
        memory = EpisodicMemory()
        memory.start_episode({})
        counter = [0]
        
        def add():
            memory.add_event("action", f"Event {counter[0]}")
            counter[0] += 1
        
        stats = self.benchmark(add, iterations=1000, warmup=100)
        
        assert stats["avg"] < 0.0001
        print(f"Episodic add avg: {stats['avg']*1000:.2f}ms")


class TestToolsBenchmark(BenchmarkMixin):
    """测试工具系统性能基准"""
    
    def test_tool_registry_list_benchmark(self):
        """测试工具列表性能"""
        registry = ToolRegistry()
        
        def list_tools():
            registry.list_tools()
        
        stats = self.benchmark(list_tools, iterations=10000, warmup=1000)
        
        assert stats["avg"] < 0.00001
        print(f"List tools avg: {stats['avg']*1000:.2f}ms")
    
    def test_tool_get_benchmark(self):
        """测试工具获取性能"""
        registry = ToolRegistry()
        
        def get_tool():
            registry.get("read_file")
        
        stats = self.benchmark(get_tool, iterations=10000, warmup=1000)
        
        assert stats["avg"] < 0.00001
        print(f"Get tool avg: {stats['avg']*1000:.2f}ms")
    
    def test_tool_execute_read_benchmark(self, tmp_path):
        """测试工具执行性能"""
        registry = ToolRegistry()
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        def execute():
            registry.execute("read_file", {"path": str(test_file)})
        
        stats = self.benchmark(execute, iterations=100, warmup=10)
        
        assert stats["avg"] < 0.01
        print(f"Tool execute avg: {stats['avg']*1000:.2f}ms")


class TestAgentBenchmark(BenchmarkMixin):
    """测试 Agent 系统性能基准"""
    
    def test_create_agent_benchmark(self):
        """测试创建 Agent 性能"""
        coordinator = Coordinator()
        counter = [0]
        
        def create():
            coordinator.create_agent(f"Task {counter[0]}", "Prompt")
            counter[0] += 1
        
        stats = self.benchmark(create, iterations=1000, warmup=100)
        
        assert stats["avg"] < 0.001
        print(f"Create agent avg: {stats['avg']*1000:.2f}ms")
    
    def test_run_agent_benchmark(self):
        """测试运行 Agent 性能"""
        coordinator = Coordinator()
        counter = [0]
        agent_ids = []
        
        # 预创建 Agent
        for i in range(100):
            task = coordinator.create_agent(f"Task {i}", "Prompt")
            agent_ids.append(task.agent_id)
        
        def run():
            idx = counter[0] % len(agent_ids)
            coordinator._run_agent(agent_ids[idx])
            counter[0] += 1
        
        stats = self.benchmark(run, iterations=100, warmup=10)
        
        assert stats["avg"] < 0.01
        print(f"Run agent avg: {stats['avg']*1000:.2f}ms")


class TestSystemWideBenchmark(BenchmarkMixin):
    """测试系统级性能基准"""
    
    def test_full_query_workflow_benchmark(self):
        """测试完整查询工作流性能"""
        engine = QueryEngine()
        
        def workflow():
            engine.submit_message("Test query message")
        
        stats = self.benchmark(workflow, iterations=50, warmup=5)
        
        assert stats["avg"] < 0.1
        print(f"Full workflow avg: {stats['avg']*1000:.2f}ms")
    
    def test_memory_retrieval_workflow_benchmark(self, tmp_path):
        """测试记忆检索工作流性能"""
        from shadowclaude.memory import MemorySystem
        
        system = MemorySystem()
        system.semantic.storage_path = tmp_path
        
        # 预填充
        for i in range(50):
            system.add_to_semantic(f"Knowledge item {i}", importance=0.8)
        
        def retrieve():
            system.retrieve_context("knowledge")
        
        stats = self.benchmark(retrieve, iterations=100, warmup=10)
        
        assert stats["avg"] < 0.01
        print(f"Memory retrieve avg: {stats['avg']*1000:.2f}ms")


class TestScalabilityBenchmark:
    """测试可扩展性基准"""
    
    def test_memory_scalability(self, tmp_path):
        """测试记忆系统可扩展性"""
        memory = SemanticMemory(storage_path=tmp_path)
        
        # 添加大量数据
        start = time.time()
        for i in range(1000):
            memory.add(f"Content item {i} with some text", importance=0.8)
        add_time = time.time() - start
        
        # 检索
        start = time.time()
        for _ in range(100):
            memory.retrieve("content", top_k=10)
        retrieve_time = time.time() - start
        
        print(f"Add 1000 items: {add_time*1000:.2f}ms")
        print(f"Retrieve 100 times: {retrieve_time*1000:.2f}ms")
        
        assert add_time < 1.0
        assert retrieve_time < 1.0
    
    def test_agent_scalability(self):
        """测试 Agent 系统可扩展性"""
        coordinator = Coordinator()
        
        # 创建大量 Agent
        start = time.time()
        for i in range(500):
            coordinator.create_agent(f"Agent {i}", "Task")
        create_time = time.time() - start
        
        print(f"Create 500 agents: {create_time*1000:.2f}ms")
        
        assert create_time < 1.0
        assert len(coordinator._tasks) == 500
