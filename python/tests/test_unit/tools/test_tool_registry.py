"""
ToolRegistry 单元测试 - 基础功能
测试工具注册表的核心功能
"""

import pytest
from shadowclaude.tools import ToolRegistry, ToolSpec, ToolResult, PermissionMode


class TestToolRegistryInitialization:
    """测试工具注册表初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        registry = ToolRegistry()
        
        assert registry._tools is not None
        assert len(registry._tools) > 0  # 应注册内置工具
    
    def test_builtin_tools_registered(self):
        """测试内置工具已注册"""
        registry = ToolRegistry()
        tools = registry.list_tools()
        
        # 检查核心工具是否存在
        assert "read_file" in tools
        assert "write_file" in tools
        assert "bash" in tools
        assert "WebFetch" in tools
        assert "WebSearch" in tools


class TestToolRegistration:
    """测试工具注册"""
    
    def test_register_new_tool(self):
        """测试注册新工具"""
        registry = ToolRegistry()
        
        spec = ToolSpec(
            name="custom_tool",
            description="A custom tool",
            input_schema={"type": "object"},
            required_permission=PermissionMode.READ_ONLY
        )
        
        registry.register(spec)
        
        assert "custom_tool" in registry.list_tools()
    
    def test_register_duplicate_overwrites(self):
        """测试重复注册覆盖"""
        registry = ToolRegistry()
        
        spec1 = ToolSpec(
            name="test_tool",
            description="Original",
            input_schema={},
            required_permission=PermissionMode.READ_ONLY
        )
        spec2 = ToolSpec(
            name="test_tool",
            description="Updated",
            input_schema={},
            required_permission=PermissionMode.READ_ONLY
        )
        
        registry.register(spec1)
        registry.register(spec2)
        
        tool = registry.get("test_tool")
        assert tool.description == "Updated"
    
    def test_get_existing_tool(self):
        """测试获取现有工具"""
        registry = ToolRegistry()
        
        tool = registry.get("read_file")
        
        assert tool is not None
        assert tool.name == "read_file"
    
    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具"""
        registry = ToolRegistry()
        
        tool = registry.get("nonexistent_tool")
        
        assert tool is None


class TestToolListing:
    """测试工具列表"""
    
    def test_list_all_tools(self):
        """测试列出所有工具"""
        registry = ToolRegistry()
        
        tools = registry.list_tools()
        
        assert len(tools) >= 10  # 至少应有 10+ 工具
        assert isinstance(tools, list)
    
    def test_list_by_permission(self):
        """测试按权限列出工具"""
        registry = ToolRegistry()
        
        read_only = registry.list_tools(PermissionMode.READ_ONLY)
        workspace = registry.list_tools(PermissionMode.WORKSPACE_WRITE)
        danger = registry.list_tools(PermissionMode.DANGER_FULL_ACCESS)
        
        assert len(read_only) > 0
        assert len(danger) > 0
        # bash 应该在危险权限中
        assert "bash" in danger
    
    def test_get_tool_descriptions(self):
        """测试获取工具描述"""
        registry = ToolRegistry()
        
        descriptions = registry.get_tool_descriptions()
        
        assert len(descriptions) > 0
        assert all(isinstance(d, str) for d in descriptions)
        assert any("read_file" in d for d in descriptions)


class TestToolExecution:
    """测试工具执行"""
    
    def test_execute_existing_tool(self):
        """测试执行现有工具"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {"path": "test.txt"})
        
        assert isinstance(result, ToolResult)
    
    def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()
        
        result = registry.execute("nonexistent", {})
        
        assert result.success is False
        assert "Unknown tool" in result.error
    
    def test_execute_tool_without_handler(self):
        """测试执行无处理器的工具"""
        registry = ToolRegistry()
        
        spec = ToolSpec(
            name="no_handler",
            description="No handler",
            input_schema={},
            required_permission=PermissionMode.READ_ONLY,
            handler=None
        )
        registry.register(spec)
        
        result = registry.execute("no_handler", {})
        
        assert result.success is False
        assert "no handler" in result.error.lower()


class TestPermissionModes:
    """测试权限模式"""
    
    def test_permission_mode_values(self):
        """测试权限模式值"""
        assert PermissionMode.READ_ONLY.value == "read_only"
        assert PermissionMode.WORKSPACE_WRITE.value == "workspace_write"
        assert PermissionMode.DANGER_FULL_ACCESS.value == "danger_full_access"
    
    def test_tool_permission_assignment(self):
        """测试工具权限分配"""
        registry = ToolRegistry()
        
        read_tool = registry.get("read_file")
        write_tool = registry.get("write_file")
        bash_tool = registry.get("bash")
        
        assert read_tool.required_permission == PermissionMode.READ_ONLY
        assert write_tool.required_permission == PermissionMode.WORKSPACE_WRITE
        assert bash_tool.required_permission == PermissionMode.DANGER_FULL_ACCESS


class TestToolResult:
    """测试工具结果"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = ToolResult(
            success=True,
            output="Success output",
            metadata={"key": "value"}
        )
        
        assert result.success is True
        assert result.output == "Success output"
        assert result.error is None
    
    def test_failure_result(self):
        """测试失败结果"""
        result = ToolResult(
            success=False,
            output="",
            error="Something went wrong"
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
    
    def test_result_with_metadata(self):
        """测试带元数据的结果"""
        result = ToolResult(
            success=True,
            output="output",
            metadata={"lines": 10, "bytes": 100}
        )
        
        assert result.metadata["lines"] == 10


class TestToolSpec:
    """测试工具规范"""
    
    def test_spec_creation(self):
        """测试规范创建"""
        spec = ToolSpec(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"}
                }
            },
            required_permission=PermissionMode.READ_ONLY
        )
        
        assert spec.name == "test_tool"
        assert spec.handler is None
    
    def test_spec_with_handler(self):
        """测试带处理器的规范"""
        def handler(input_data):
            return ToolResult(success=True, output="handled")
        
        spec = ToolSpec(
            name="handler_tool",
            description="With handler",
            input_schema={},
            required_permission=PermissionMode.READ_ONLY,
            handler=handler
        )
        
        assert spec.handler is not None


class TestToolRegistryEdgeCases:
    """测试边界情况"""
    
    def test_execute_with_empty_input(self):
        """测试空输入执行"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {})
        
        # 应该返回结果（可能失败但有结果）
        assert isinstance(result, ToolResult)
    
    def test_execute_with_invalid_input(self):
        """测试无效输入执行"""
        registry = ToolRegistry()
        
        result = registry.execute("read_file", {"invalid_param": "value"})
        
        assert isinstance(result, ToolResult)
    
    def test_list_tools_empty_permission(self):
        """测试空权限列表工具"""
        registry = ToolRegistry()
        # 创建一个不存在的权限
        
        # 应该返回空列表或处理异常
        tools = registry.list_tools()
        assert isinstance(tools, list)


class TestBuiltinToolsPresence:
    """测试内置工具存在性"""
    
    def test_file_tools_present(self):
        """测试文件工具存在"""
        registry = ToolRegistry()
        
        assert registry.get("read_file") is not None
        assert registry.get("write_file") is not None
        assert registry.get("edit_file") is not None
        assert registry.get("glob_search") is not None
        assert registry.get("grep_search") is not None
    
    def test_web_tools_present(self):
        """测试 Web 工具存在"""
        registry = ToolRegistry()
        
        assert registry.get("WebFetch") is not None
        assert registry.get("WebSearch") is not None
    
    def test_task_tools_present(self):
        """测试任务工具存在"""
        registry = ToolRegistry()
        
        assert registry.get("TodoWrite") is not None
    
    def test_agent_tools_present(self):
        """测试 Agent 工具存在"""
        registry = ToolRegistry()
        
        assert registry.get("Agent") is not None
        assert registry.get("ToolSearch") is not None
