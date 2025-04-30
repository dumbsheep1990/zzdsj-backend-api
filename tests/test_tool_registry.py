"""
测试工具注册管理模块，验证不同框架的工具能否统一注册和管理
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import List, Dict, Any

from app.frameworks.llamaindex.adapters.tool_registry import (
    ToolRegistry, 
    global_tool_registry,
    register_default_tools
)
from app.frameworks.llamaindex.adapters.agno_tools import AgnoAgentTool
from app.frameworks.llamaindex.adapters.haystack_retriever import HaystackRetriever
from llama_index.core.tools import QueryEngineTool, BaseTool, ToolMetadata
from llama_index.core.query_engine import BaseQueryEngine


@pytest.fixture
def mock_agno_tool():
    """提供一个模拟的Agno工具"""
    mock_tool = MagicMock(spec=AgnoAgentTool)
    mock_tool.metadata = ToolMetadata(name="agno_tool", description="Agno工具")
    mock_tool.as_query_engine.return_value = MagicMock(spec=BaseQueryEngine)
    
    yield mock_tool


@pytest.fixture
def mock_haystack_retriever():
    """提供一个模拟的Haystack检索器"""
    mock_retriever = MagicMock(spec=HaystackRetriever)
    mock_engine = MagicMock(spec=BaseQueryEngine)
    mock_retriever.as_query_engine.return_value = mock_engine
    
    yield mock_retriever


@pytest.fixture
def mock_create_agno_tool():
    """模拟create_agno_tool函数"""
    with patch("app.frameworks.llamaindex.adapters.tool_registry.create_agno_tool") as mock_create:
        mock_tool = MagicMock(spec=AgnoAgentTool)
        mock_tool.metadata = ToolMetadata(name="knowledge_reasoning", description="复杂知识推理")
        mock_tool.as_query_engine.return_value = MagicMock(spec=BaseQueryEngine)
        mock_create.return_value = mock_tool
        
        yield mock_create


@pytest.fixture
def mock_create_haystack_retriever():
    """模拟create_haystack_retriever函数"""
    with patch("app.frameworks.llamaindex.adapters.tool_registry.create_haystack_retriever") as mock_create:
        mock_retriever = MagicMock(spec=HaystackRetriever)
        mock_retriever.as_query_engine.return_value = MagicMock(spec=BaseQueryEngine)
        mock_create.return_value = mock_retriever
        
        yield mock_create


class TestToolRegistry:
    """测试工具注册中心"""
    
    def test_tool_registry_initialization(self):
        """测试ToolRegistry初始化"""
        registry = ToolRegistry()
        assert registry._tools == {}
    
    def test_register_and_get_tool(self, mock_agno_tool):
        """测试注册和获取工具"""
        registry = ToolRegistry()
        
        # 注册工具
        registry.register_tool("test_tool", mock_agno_tool)
        
        # 获取工具
        tool = registry.get_tool("test_tool")
        
        # 验证
        assert tool == mock_agno_tool
        assert registry.list_tools() == ["test_tool"]
        assert registry.get_all_tools() == {"test_tool": mock_agno_tool}
    
    def test_get_query_engine_tools(self, mock_agno_tool, mock_haystack_retriever):
        """测试获取查询引擎工具"""
        registry = ToolRegistry()
        
        # 注册不同类型的工具
        registry.register_tool("agno", mock_agno_tool)
        registry.register_tool("haystack", mock_haystack_retriever)
        
        # 将工具直接作为QueryEngineTool注册
        engine = MagicMock(spec=BaseQueryEngine)
        query_engine_tool = QueryEngineTool(
            query_engine=engine,
            metadata=ToolMetadata(name="direct_tool", description="直接工具")
        )
        registry.register_tool("direct", query_engine_tool)
        
        # 获取QueryEngineTool列表
        tools = registry.get_query_engine_tools()
        
        # 验证
        assert len(tools) == 3
        assert all(isinstance(tool, QueryEngineTool) for tool in tools)
        
        # 验证工具名称
        tool_names = [tool.metadata.name for tool in tools]
        assert "agno_tool" in tool_names
        assert "direct_tool" in tool_names
    
    def test_global_tool_registry(self):
        """测试全局工具注册中心"""
        assert isinstance(global_tool_registry, ToolRegistry)
    
    def test_register_default_tools(self, mock_create_agno_tool, mock_create_haystack_retriever):
        """测试注册默认工具"""
        # 清空全局注册中心
        global_tool_registry._tools = {}
        
        # 注册默认工具
        updated_registry = register_default_tools(knowledge_base_id=1, model_name="test-model")
        
        # 验证调用
        mock_create_agno_tool.assert_called_once_with(
            knowledge_base_ids=[1],
            name="knowledge_reasoning",
            description="用于复杂知识推理和多步骤问答",
            model="test-model"
        )
        
        mock_create_haystack_retriever.assert_called_once_with(
            knowledge_base_id=1,
            model_name="test-model",
            top_k=3
        )
        
        # 验证注册
        assert len(updated_registry.list_tools()) == 2
        assert "knowledge_reasoning" in updated_registry.list_tools()
        assert "fact_extraction" in updated_registry.list_tools()
        
        # 验证返回的是全局注册中心
        assert updated_registry is global_tool_registry


if __name__ == "__main__":
    pytest.main(["-xvs", "test_tool_registry.py"])
