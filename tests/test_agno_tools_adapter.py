"""
测试Agno适配器，验证能否将Agno代理封装为LlamaIndex工具
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import List, Dict, Any

from app.frameworks.llamaindex.adapters.agno_tools import (
    AgnoAgentTool,
    create_agno_tool
)
from app.frameworks.agno.agent import AgnoAgent
from llama_index.core.tools import BaseTool, QueryEngineTool
from llama_index.core.query_engine import BaseQueryEngine


@pytest.fixture
def mock_agno_agent():
    """模拟AgnoAgent"""
    with patch("app.frameworks.llamaindex.adapters.agno_tools.AgnoAgent") as mock_agent_class:
        mock_agent = MagicMock(spec=AgnoAgent)
        
        # 设置异步查询方法的返回值
        mock_agent.query = AsyncMock(return_value={"response": "模拟Agno回答"})
        
        # 设置AgnoAgent构造函数返回mock_agent
        mock_agent_class.return_value = mock_agent
        
        yield mock_agent


@pytest.fixture
def mock_knowledge_agent():
    """模拟create_knowledge_agent函数"""
    with patch("app.frameworks.llamaindex.adapters.agno_tools.create_knowledge_agent") as mock_create:
        mock_agent = MagicMock(spec=AgnoAgent)
        mock_agent.query = AsyncMock(return_value={"response": "模拟知识代理回答"})
        mock_create.return_value = mock_agent
        
        yield mock_create


class TestAgnoAdapter:
    """测试Agno适配器"""
    
    def test_agno_agent_tool_initialization(self, mock_agno_agent):
        """测试AgnoAgentTool初始化"""
        # 创建工具
        tool = AgnoAgentTool(
            agent=mock_agno_agent,
            name="test_tool",
            description="测试工具"
        )
        
        # 验证
        assert tool.agent == mock_agno_agent
        assert tool.metadata.name == "test_tool"
        assert tool.metadata.description == "测试工具"
    
    @pytest.mark.asyncio
    async def test_agno_agent_tool_call(self, mock_agno_agent):
        """测试AgnoAgentTool调用"""
        # 创建工具
        tool = AgnoAgentTool(
            agent=mock_agno_agent,
            name="test_tool",
            description="测试工具"
        )
        
        # 调用工具
        response = await tool("测试查询")
        
        # 验证
        mock_agno_agent.query.assert_called_once_with("测试查询", None)
        assert response == "模拟Agno回答"
    
    @pytest.mark.asyncio
    async def test_agno_agent_tool_with_conversation_id(self, mock_agno_agent):
        """测试带有会话ID的AgnoAgentTool调用"""
        # 创建工具
        tool = AgnoAgentTool(
            agent=mock_agno_agent,
            name="test_tool",
            description="测试工具"
        )
        
        # 调用工具
        response = await tool("测试查询", conversation_id="test-123")
        
        # 验证
        mock_agno_agent.query.assert_called_once_with("测试查询", "test-123")
        assert response == "模拟Agno回答"
    
    def test_as_query_engine(self, mock_agno_agent):
        """测试转换为QueryEngine"""
        # 创建工具
        tool = AgnoAgentTool(
            agent=mock_agno_agent,
            name="test_tool",
            description="测试工具"
        )
        
        # 转换为QueryEngine
        engine = tool.as_query_engine()
        
        # 验证
        assert isinstance(engine, BaseQueryEngine)
    
    @pytest.mark.asyncio
    async def test_create_agno_tool(self, mock_knowledge_agent):
        """测试create_agno_tool工厂函数"""
        # 使用工厂函数
        tool = create_agno_tool(
            knowledge_base_ids=[1, 2],
            name="knowledge_tool",
            description="知识工具",
            model="test-model"
        )
        
        # 验证create_knowledge_agent的调用
        mock_knowledge_agent.assert_called_once_with(
            knowledge_base_ids=[1, 2],
            model="test-model"
        )
        
        # 验证工具属性
        assert isinstance(tool, AgnoAgentTool)
        assert tool.metadata.name == "knowledge_tool"
        assert tool.metadata.description == "知识工具"


if __name__ == "__main__":
    pytest.main(["-xvs", "test_agno_tools_adapter.py"])
