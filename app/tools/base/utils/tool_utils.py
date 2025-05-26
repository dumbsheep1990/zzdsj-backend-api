"""
工具实用工具
提供工具管理、注册和获取功能，作为统一的工具集成层
"""

import logging
import re
from typing import List, Dict, Any, Optional, Union
from llama_index.core.tools import BaseTool, ToolMetadata, FunctionTool

logger = logging.getLogger(__name__)

# 全局工具注册表
_registered_tools: Dict[str, BaseTool] = {}

def register_tool(tool: BaseTool) -> None:
    """
    注册工具到全局工具注册表
    
    参数:
        tool: 要注册的工具实例
    """
    global _registered_tools
    tool_name = tool.metadata.name
    
    if tool_name in _registered_tools:
        logger.warning(f"工具 '{tool_name}' 已存在，将被覆盖")
        
    _registered_tools[tool_name] = tool
    logger.info(f"工具 '{tool_name}' 已注册")

def get_tool(name: str) -> Optional[BaseTool]:
    """
    根据名称获取工具
    
    参数:
        name: 工具名称
        
    返回:
        Optional[BaseTool]: 工具实例，如果不存在则为None
    """
    return _registered_tools.get(name)

def get_web_search_tool() -> BaseTool:
    """
    获取Web搜索工具实例
    
    返回:
        配置好的搜索工具
    """
    try:
        # 从全局工具注册表获取搜索工具，如果不存在则创建新的搜索工具
        if "web_search" in _registered_tools:
            return _registered_tools["web_search"]
        
        from app.tools.base.search import get_search_tool
        search_tool = get_search_tool()
        register_tool(search_tool)
        return search_tool
    
    except Exception as e:
        logger.error(f"获取Web搜索工具时出错: {str(e)}")
        # 创建一个空的函数工具作为备用
        def fallback_search(query: str) -> str:
            return f"搜索功能暂时不可用: {str(e)}"
        
        return FunctionTool.from_defaults(
            fn=fallback_search,
            name="web_search",
            description="搜索功能暂时不可用"
        )

def get_cot_reasoning_tool() -> BaseTool:
    """
    获取思维链(CoT)推理工具实例
    
    返回:
        配置好的思维链工具
    """
    try:
        # 从全局工具注册表获取CoT工具，如果不存在则创建新的CoT工具
        if "cot_reasoning" in _registered_tools:
            return _registered_tools["cot_reasoning"]
        
        from app.tools.advanced.reasoning import get_cot_tool
        cot_tool = get_cot_tool()
        register_tool(cot_tool)
        return cot_tool
    
    except Exception as e:
        logger.error(f"获取思维链工具时出错: {str(e)}")
        # 创建一个空的函数工具作为备用
        def fallback_cot(query: str) -> str:
            return f"思维链功能暂时不可用: {str(e)}"
        
        return FunctionTool.from_defaults(
            fn=fallback_cot,
            name="cot_reasoning",
            description="思维链功能暂时不可用"
        )

def get_deep_research_tool() -> BaseTool:
    """
    获取深度研究工具实例
    
    返回:
        配置好的深度研究工具
    """
    try:
        # 从全局工具注册表获取深度研究工具，如果不存在则创建新的工具
        if "deep_research" in _registered_tools:
            return _registered_tools["deep_research"]
        
        from app.tools.advanced.research import get_deep_research_tool
        deep_research_tool = get_deep_research_tool()
        register_tool(deep_research_tool)
        return deep_research_tool
    
    except Exception as e:
        logger.error(f"获取深度研究工具时出错: {str(e)}")
        # 创建一个空的函数工具作为备用
        def fallback_deep_research(query: str) -> str:
            return f"深度研究功能暂时不可用: {str(e)}"
        
        return FunctionTool.from_defaults(
            fn=fallback_deep_research,
            name="deep_research",
            description="深度研究功能暂时不可用"
        )

def get_all_tools() -> List[BaseTool]:
    """
    获取所有可用的工具集合
    
    返回:
        工具列表
    """
    tools = []
    
    # 获取所有已注册的工具
    global _registered_tools
    if _registered_tools:
        tools.extend(_registered_tools.values())
        return tools
    
    # 如果没有已注册的工具，则初始化基本工具集
    
    # 1. 添加Web搜索工具
    try:
        search_tool = get_web_search_tool()
        if search_tool and search_tool.name not in [t.name for t in tools]:
            tools.append(search_tool)
    except Exception as e:
        logger.error(f"加载Web搜索工具时出错: {str(e)}")
    
    # 2. 添加思维链工具
    try:
        cot_tool = get_cot_reasoning_tool()
        if cot_tool and cot_tool.name not in [t.name for t in tools]:
            tools.append(cot_tool)
    except Exception as e:
        logger.error(f"加载思维链工具时出错: {str(e)}")
    
    # 3. 添加深度研究工具
    try:
        deep_research_tool = get_deep_research_tool()
        if deep_research_tool and deep_research_tool.name not in [t.name for t in tools]:
            tools.append(deep_research_tool)
    except Exception as e:
        logger.error(f"加载深度研究工具时出错: {str(e)}")
    
    # 注册所有添加的工具
    for tool in tools:
        register_tool(tool)
    
    return tools

def create_simple_tool(
    func: callable,
    name: str,
    description: str
) -> BaseTool:
    """
    创建简单的函数工具
    
    参数:
        func: 工具函数
        name: 工具名称
        description: 工具描述
        
    返回:
        BaseTool: 创建的工具
    """
    tool = FunctionTool.from_defaults(
        fn=func,
        name=name,
        description=description
    )
    
    # 自动注册到工具注册表
    register_tool(tool)
    
    return tool
