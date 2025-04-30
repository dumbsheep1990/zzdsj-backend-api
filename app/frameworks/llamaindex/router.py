"""
LlamaIndex路由模块: 提供统一的查询路由功能
根据查询类型和上下文智能选择合适的工具和引擎
"""

from typing import List, Dict, Any, Optional, Union
from llama_index.core.query_engine import RouterQueryEngine, QueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core import ServiceContext
from llama_index.core.llms import ChatMessage, MessageRole

from app.frameworks.llamaindex.core import get_service_context
from app.frameworks.llamaindex.adapters.tool_registry import (
    global_tool_registry, 
    register_default_tools
)


class QueryRouter:
    """
    场景路由器
    根据查询类型和上下文智能选择适当的处理引擎
    """
    
    def __init__(
        self, 
        knowledge_base_id: Optional[int] = None,
        model_name: Optional[str] = None,
        service_context: Optional[ServiceContext] = None,
        use_multi_select: bool = True
    ):
        """
        初始化路由器
        
        参数:
            knowledge_base_id: 知识库ID，用于初始化工具
            model_name: 模型名称，用于初始化服务上下文
            service_context: 可选的服务上下文，如果不提供会创建新的
            use_multi_select: 是否允许选择多个引擎
        """
        self.knowledge_base_id = knowledge_base_id
        self.model_name = model_name
        self.service_context = service_context or get_service_context(model_name)
        self.use_multi_select = use_multi_select
        
        # 确保工具注册表已初始化
        register_default_tools(knowledge_base_id, model_name)
    
    def get_router_engine(self) -> RouterQueryEngine:
        """
        获取路由查询引擎
        
        返回:
            配置好的路由查询引擎
        """
        # 获取所有查询引擎工具
        query_engine_tools = global_tool_registry.get_query_engine_tools()
        
        if not query_engine_tools:
            raise ValueError("没有可用的查询引擎工具")
        
        # 创建路由引擎
        router_engine = RouterQueryEngine.from_defaults(
            query_engine_tools=query_engine_tools,
            service_context=self.service_context,
            select_multi=self.use_multi_select
        )
        
        return router_engine
    
    async def query(
        self, 
        query_str: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        执行查询
        
        参数:
            query_str: 查询文本
            system_prompt: 系统提示
            conversation_history: 对话历史
            
        返回:
            包含答案和元数据的响应
        """
        # 获取路由引擎
        engine = self.get_router_engine()
        
        # 准备消息
        messages = []
        
        # 添加系统提示
        if system_prompt:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
        
        # 添加对话历史
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role == "user":
                    messages.append(ChatMessage(role=MessageRole.USER, content=content))
                elif role == "assistant":
                    messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=content))
                elif role == "system":
                    messages.append(ChatMessage(role=MessageRole.SYSTEM, content=content))
        
        # 添加当前查询
        messages.append(ChatMessage(role=MessageRole.USER, content=query_str))
        
        # 执行查询
        if hasattr(engine, "chat"):
            response = await engine.achat(messages)
            answer = response.message.content
        else:
            response = await engine.aquery(query_str)
            answer = response.response
        
        # 准备结果
        result = {
            "answer": answer,
            "metadata": {}
        }
        
        # 添加源文档(如果有)
        if hasattr(response, "source_nodes"):
            sources = []
            for node in response.source_nodes:
                sources.append({
                    "content": node.text,
                    "metadata": node.metadata,
                    "score": node.score if node.score is not None else 1.0,
                    "node_id": node.node_id if hasattr(node, "node_id") else None
                })
            result["metadata"]["sources"] = sources
        
        return result


def create_unified_engine(
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None,
    service_context: Optional[ServiceContext] = None,
    use_multi_select: bool = True
) -> RouterQueryEngine:
    """
    创建统一查询引擎
    这是一个便捷函数，用于快速创建并获取路由查询引擎
    
    参数:
        knowledge_base_id: 知识库ID
        model_name: 模型名称
        service_context: 服务上下文
        use_multi_select: 是否允许选择多个引擎
        
    返回:
        配置好的路由查询引擎
    """
    router = QueryRouter(
        knowledge_base_id=knowledge_base_id,
        model_name=model_name,
        service_context=service_context,
        use_multi_select=use_multi_select
    )
    return router.get_router_engine()


async def route_query(
    query: str,
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    路由并执行查询
    这是一个便捷函数，用于快速执行查询并获取结果
    
    参数:
        query: 查询文本
        knowledge_base_id: 知识库ID
        model_name: 模型名称
        system_prompt: 系统提示
        conversation_history: 对话历史
        
    返回:
        包含答案和元数据的响应
    """
    router = QueryRouter(
        knowledge_base_id=knowledge_base_id,
        model_name=model_name
    )
    
    return await router.query(
        query_str=query,
        system_prompt=system_prompt,
        conversation_history=conversation_history
    )
