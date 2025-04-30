"""
LlamaIndex工具模块: 提供各类工具适配
用于将多种AI框架工具集成到LlamaIndex框架中，包括MCP工具、Agno代理和Haystack检索器
"""

from typing import List, Dict, Any, Optional, Union
from llama_index.core.tools import FunctionTool, ToolMetadata, QueryEngineTool, BaseTool
from llama_index.core.query_engine import QueryEngine
from llama_index.tools.mcp import MCPTool, MCPToolSpec
from app.frameworks.fastmcp.tools import get_tool, list_tools
from app.frameworks.fastmcp.server import get_mcp_server
import logging

# 导入Agno和Haystack适配器
from app.frameworks.llamaindex.adapters.agno_tools import create_agno_tool
from app.frameworks.llamaindex.adapters.haystack_retriever import create_haystack_retriever

logger = logging.getLogger(__name__)

def create_mcp_tool(tool_name: str) -> Optional[MCPTool]:
    """
    将FastMCP工具转换为LlamaIndex MCPTool
    
    参数:
        tool_name: MCP工具名称
        
    返回:
        LlamaIndex MCPTool实例
    """
    try:
        # 获取MCP工具
        tool_data = get_tool(tool_name)
        if not tool_data:
            logger.error(f"未找到MCP工具: {tool_name}")
            return None
        
        # 获取工具schema
        schema = tool_data.get("schema")
        if not schema:
            schema = get_tool_schema(tool_name)
        
        # 创建MCP工具规格
        tool_spec = MCPToolSpec(
            name=tool_data["name"],
            description=tool_data["description"],
            parameters=schema["parameters"] if schema else {},
        )
        
        # 创建MCP工具
        mcp_tool = MCPTool(
            spec=tool_spec,
            mcp_server_url="http://localhost:8000/api/mcp/tools"  # 使用本地MCP服务
        )
        
        return mcp_tool
    
    except Exception as e:
        logger.error(f"创建LlamaIndex MCP工具时出错: {str(e)}")
        return None

def get_all_mcp_tools(category: Optional[str] = None, tag: Optional[str] = None) -> List[MCPTool]:
    """
    获取所有MCP工具的LlamaIndex适配
    
    参数:
        category: 可选，按类别筛选
        tag: 可选，按标签筛选
        
    返回:
        LlamaIndex MCPTool列表
    """
    tools = []
    
    # 获取所有MCP工具
    mcp_tools = list_tools(category, tag)
    
    # 转换为LlamaIndex MCPTool
    for tool_data in mcp_tools:
        mcp_tool = create_mcp_tool(tool_data["name"])
        if mcp_tool:
            tools.append(mcp_tool)
    
    return tools

def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    从app.frameworks.fastmcp.tools获取工具schema
    
    参数:
        tool_name: 工具名称
        
    返回:
        工具schema
    """
    from app.frameworks.fastmcp.tools import get_tool_schema as fastmcp_get_tool_schema
    return fastmcp_get_tool_schema(tool_name)

# 新增函数: 创建各种工具的统一接口

def get_unified_tools(
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None,
    include_mcp: bool = True,
    include_agno: bool = True,
    include_haystack: bool = True,
    mcp_categories: Optional[List[str]] = None,
    mcp_tags: Optional[List[str]] = None
) -> List[Union[BaseTool, QueryEngine]]:
    """
    获取统一的工具集合，包含各种框架的工具
    
    参数:
        knowledge_base_id: 知识库ID
        model_name: 模型名称
        include_mcp: 是否包含MCP工具
        include_agno: 是否包含Agno工具
        include_haystack: 是否包含Haystack工具
        mcp_categories: MCP工具类别列表
        mcp_tags: MCP工具标签列表
        
    返回:
        工具列表
    """
    tools = []
    
    # 添加Agno工具
    if include_agno and knowledge_base_id:
        try:
            agno_tool = create_agno_tool(
                knowledge_base_ids=[knowledge_base_id],
                name="knowledge_reasoning",
                description="用于复杂知识推理和多步骤问答",
                model=model_name
            )
            tools.append(agno_tool)
        except Exception as e:
            logger.error(f"创建Agno工具时出错: {str(e)}")
    
    # 添加Haystack工具
    if include_haystack and knowledge_base_id:
        try:
            haystack_retriever = create_haystack_retriever(
                knowledge_base_id=knowledge_base_id,
                model_name=model_name,
                top_k=3
            )
            tools.append(haystack_retriever)
        except Exception as e:
            logger.error(f"创建Haystack检索器时出错: {str(e)}")
    
    # 添加MCP工具
    if include_mcp:
        try:
            for category in (mcp_categories or [None]):
                for tag in (mcp_tags or [None]):
                    mcp_tools = get_all_mcp_tools(category, tag)
                    tools.extend(mcp_tools)
        except Exception as e:
            logger.error(f"获取MCP工具时出错: {str(e)}")
    
    return tools

def get_unified_query_engine_tools(
    knowledge_base_id: Optional[int] = None,
    model_name: Optional[str] = None,
    include_mcp: bool = True,
    include_agno: bool = True,
    include_haystack: bool = True
) -> List[QueryEngineTool]:
    """
    获取统一的查询引擎工具列表，用于创建RouterQueryEngine
    
    参数:
        knowledge_base_id: 知识库ID
        model_name: 模型名称
        include_mcp: 是否包含MCP工具
        include_agno: 是否包含Agno工具
        include_haystack: 是否包含Haystack工具
        
    返回:
        QueryEngineTool列表
    """
    query_engine_tools = []
    
    # 获取所有工具
    tools = get_unified_tools(
        knowledge_base_id=knowledge_base_id,
        model_name=model_name,
        include_mcp=include_mcp,
        include_agno=include_agno,
        include_haystack=include_haystack
    )
    
    # 转换为QueryEngineTool
    for tool in tools:
        try:
            # 如果已经是QueryEngineTool则直接添加
            if isinstance(tool, QueryEngineTool):
                query_engine_tools.append(tool)
                continue
            
            # 如果是BaseTool则尝试转换为QueryEngine
            if isinstance(tool, BaseTool):
                if hasattr(tool, "as_query_engine"):
                    engine = tool.as_query_engine()
                    query_engine_tool = QueryEngineTool(
                        query_engine=engine,
                        metadata=ToolMetadata(
                            name=tool.metadata.name,
                            description=tool.metadata.description
                        )
                    )
                    query_engine_tools.append(query_engine_tool)
                
            # 如果是QueryEngine则包装为QueryEngineTool
            elif isinstance(tool, QueryEngine):
                name = getattr(tool, "metadata", {}).get("name", "query_engine")
                desc = getattr(tool, "metadata", {}).get("description", "查询引擎")
                
                query_engine_tool = QueryEngineTool(
                    query_engine=tool,
                    metadata=ToolMetadata(
                        name=name,
                        description=desc
                    )
                )
                query_engine_tools.append(query_engine_tool)
                
        except Exception as e:
            logger.error(f"转换为QueryEngineTool时出错: {str(e)}")
    
    return query_engine_tools
