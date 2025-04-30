"""
工具注册管理模块: 统一管理和注册来自不同框架的工具
提供一个中心化的接口来获取和使用各种工具
"""

from typing import Dict, Any, List, Optional, Union
from llama_index.core.tools import BaseTool, QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import QueryEngine

from app.frameworks.llamaindex.adapters.agno_tools import AgnoAgentTool, create_agno_tool
from app.frameworks.llamaindex.adapters.haystack_retriever import HaystackRetriever, create_haystack_retriever

class ToolRegistry:
    """
    工具注册中心
    提供统一的接口来管理和使用各种工具
    """
    
    def __init__(self):
        """初始化工具注册中心"""
        self._tools: Dict[str, Union[BaseTool, QueryEngine]] = {}
    
    def register_tool(self, name: str, tool: Union[BaseTool, QueryEngine]) -> None:
        """
        注册工具
        
        参数:
            name: 工具名称
            tool: 工具实例
        """
        self._tools[name] = tool
    
    def get_tool(self, name: str) -> Optional[Union[BaseTool, QueryEngine]]:
        """
        获取工具
        
        参数:
            name: 工具名称
            
        返回:
            工具实例，如果不存在则返回None
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有注册的工具
        
        返回:
            工具名称列表
        """
        return list(self._tools.keys())
    
    def get_all_tools(self) -> Dict[str, Union[BaseTool, QueryEngine]]:
        """
        获取所有工具
        
        返回:
            工具字典，键为工具名称，值为工具实例
        """
        return self._tools
    
    def get_query_engine_tools(self) -> List[QueryEngineTool]:
        """
        获取所有QueryEngineTool工具
        用于创建RouterQueryEngine
        
        返回:
            QueryEngineTool列表
        """
        query_engine_tools = []
        
        for name, tool in self._tools.items():
            # 如果已经是QueryEngineTool类型
            if isinstance(tool, QueryEngineTool):
                query_engine_tools.append(tool)
            
            # 如果是BaseTool类型，则尝试转换
            elif isinstance(tool, BaseTool) and hasattr(tool, "as_query_engine"):
                engine = tool.as_query_engine()
                query_engine_tools.append(
                    QueryEngineTool(
                        query_engine=engine,
                        metadata=ToolMetadata(
                            name=tool.metadata.name,
                            description=tool.metadata.description
                        )
                    )
                )
            
            # 如果是QueryEngine类型，则包装
            elif isinstance(tool, QueryEngine):
                query_engine_tools.append(
                    QueryEngineTool(
                        query_engine=tool,
                        metadata=ToolMetadata(
                            name=name,
                            description=f"查询引擎: {name}"
                        )
                    )
                )
        
        return query_engine_tools


# 创建全局工具注册中心
global_tool_registry = ToolRegistry()


def register_default_tools(
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None
) -> ToolRegistry:
    """
    注册默认工具到全局注册中心
    
    参数:
        knowledge_base_id: 知识库ID
        model_name: 模型名称
        
    返回:
        更新后的工具注册中心
    """
    # 如果有知识库ID，则注册Agno工具
    if knowledge_base_id:
        agno_tool = create_agno_tool(
            knowledge_base_ids=[knowledge_base_id],
            name="knowledge_reasoning",
            description="用于复杂知识推理和多步骤问答",
            model=model_name
        )
        global_tool_registry.register_tool("knowledge_reasoning", agno_tool)
    
    # 如果有知识库ID，则注册Haystack工具
    if knowledge_base_id:
        haystack_retriever = create_haystack_retriever(
            knowledge_base_id=knowledge_base_id,
            model_name=model_name,
            top_k=3
        )
        global_tool_registry.register_tool("fact_extraction", haystack_retriever)
    
    # 可以在这里注册更多默认工具
    
    return global_tool_registry
