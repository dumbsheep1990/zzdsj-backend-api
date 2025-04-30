"""
测试LlamaIndex路由模块，验证不同工具的统一调度和执行
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import List, Dict, Any

from app.frameworks.llamaindex.router import (
    QueryRouter,
    create_unified_engine,
    route_query
)
from app.frameworks.llamaindex.adapters.tool_registry import ToolRegistry, global_tool_registry
from llama_index.core.query_engine import RouterQueryEngine, BaseQueryEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ServiceContext
from llama_index.core.tools import QueryEngineTool


@pytest.fixture
def mock_service_context():
    """提供一个模拟的服务上下文"""
    with patch("app.frameworks.llamaindex.router.get_service_context") as mock_get_context:
        mock_context = MagicMock(spec=ServiceContext)
        mock_get_context.return_value = mock_context
        yield mock_context


@pytest.fixture
def mock_register_default_tools():
    """模拟register_default_tools函数"""
    with patch("app.frameworks.llamaindex.router.register_default_tools") as mock_register:
        # 创建一个模拟的工具注册中心
        registry = ToolRegistry()
        
        # 添加一些模拟工具
        mock_tool1 = MagicMock()
        mock_tool1.metadata.name = "tool1"
        registry.register_tool("tool1", mock_tool1)
        
        mock_tool2 = MagicMock()
        mock_tool2.metadata.name = "tool2"
        registry.register_tool("tool2", mock_tool2)
        
        # 设置返回值
        mock_register.return_value = registry
        yield mock_register


@pytest.fixture
def mock_router_query_engine():
    """模拟RouterQueryEngine"""
    with patch("app.frameworks.llamaindex.router.RouterQueryEngine") as mock_engine_class:
        mock_engine = MagicMock(spec=RouterQueryEngine)
        
        # 设置查询方法
        mock_response = MagicMock()
        mock_response.response = "测试回答"
        mock_response.source_nodes = [
            MagicMock(
                text="来源内容",
                metadata={"key": "value"},
                score=0.9,
                node_id="node123"
            )
        ]
        
        # 设置aquery方法
        mock_engine.aquery = AsyncMock(return_value=mock_response)
        
        # 设置achat方法
        mock_chat_response = MagicMock()
        mock_chat_response.message = MagicMock()
        mock_chat_response.message.content = "聊天回答"
        mock_engine.achat = AsyncMock(return_value=mock_chat_response)
        
        # 设置from_defaults方法返回mock_engine
        mock_engine_class.from_defaults.return_value = mock_engine
        
        yield mock_engine


class TestRouter:
    """测试路由模块"""
    
    def test_query_router_initialization(self, mock_service_context, mock_register_default_tools):
        """测试QueryRouter初始化"""
        router = QueryRouter(
            knowledge_base_id=1,
            model_name="test-model",
            use_multi_select=True
        )
        
        # 验证
        assert router.knowledge_base_id == 1
        assert router.model_name == "test-model"
        assert router.service_context == mock_service_context
        assert router.use_multi_select == True
        
        # 验证工具注册
        mock_register_default_tools.assert_called_once_with(1, "test-model")
    
    def test_get_router_engine(self, mock_service_context, mock_register_default_tools, mock_router_query_engine):
        """测试获取路由查询引擎"""
        router = QueryRouter(knowledge_base_id=1, model_name="test-model")
        
        # 获取路由引擎
        engine = router.get_router_engine()
        
        # 验证RouterQueryEngine.from_defaults的调用
        tools_registry = mock_register_default_tools.return_value
        tools = tools_registry.get_query_engine_tools()
        
        # 验证引擎创建
        from llama_index.core.query_engine import RouterQueryEngine
        RouterQueryEngine.from_defaults.assert_called_once()
        
        # 检查参数
        call_args = RouterQueryEngine.from_defaults.call_args[1]
        assert 'service_context' in call_args
        assert call_args['service_context'] == mock_service_context
        assert call_args['select_multi'] == True
        
        # 验证返回值
        assert engine == mock_router_query_engine
    
    @pytest.mark.asyncio
    async def test_query_with_history(self, mock_service_context, mock_register_default_tools, mock_router_query_engine):
        """测试带有历史记录的查询"""
        router = QueryRouter(knowledge_base_id=1, model_name="test-model")
        
        # 创建测试数据
        query = "测试查询"
        system_prompt = "你是一个助手"
        conversation_history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好，有什么可以帮助您的？"}
        ]
        
        # 执行查询
        result = await router.query(
            query_str=query,
            system_prompt=system_prompt,
            conversation_history=conversation_history
        )
        
        # 验证消息构建
        chat_call = mock_router_query_engine.achat.call_args[0][0]
        assert len(chat_call) == 4  # 系统消息 + 2个历史消息 + 当前查询
        
        # 验证消息内容和角色
        assert chat_call[0].role == MessageRole.SYSTEM
        assert chat_call[0].content == system_prompt
        assert chat_call[1].role == MessageRole.USER
        assert chat_call[1].content == "你好"
        assert chat_call[2].role == MessageRole.ASSISTANT
        assert chat_call[2].content == "您好，有什么可以帮助您的？"
        assert chat_call[3].role == MessageRole.USER
        assert chat_call[3].content == query
        
        # 验证结果格式
        assert result["answer"] == "聊天回答"
        assert "metadata" in result
        assert "sources" in result["metadata"]
        assert len(result["metadata"]["sources"]) == 1
        assert result["metadata"]["sources"][0]["content"] == "来源内容"
        assert result["metadata"]["sources"][0]["score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_create_unified_engine(self, mock_service_context, mock_register_default_tools, mock_router_query_engine):
        """测试创建统一引擎的便捷函数"""
        # 使用便捷函数
        engine = create_unified_engine(
            knowledge_base_id=2,
            model_name="custom-model",
            use_multi_select=False
        )
        
        # 验证RouterQueryEngine.from_defaults的调用
        from llama_index.core.query_engine import RouterQueryEngine
        RouterQueryEngine.from_defaults.assert_called()
        
        # 验证返回值
        assert engine == mock_router_query_engine
    
    @pytest.mark.asyncio
    async def test_route_query(self, mock_service_context, mock_register_default_tools, mock_router_query_engine):
        """测试路由查询的便捷函数"""
        # 使用便捷函数
        result = await route_query(
            query="快速查询",
            knowledge_base_id=3,
            model_name="quick-model",
            system_prompt="快速助手"
        )
        
        # 验证结果
        assert result["answer"] == "聊天回答"
        assert "metadata" in result
        assert "sources" in result["metadata"]


if __name__ == "__main__":
    pytest.main(["-xvs", "test_router.py"])
