"""
工具适配器 - 将高级工具适配到各种框架接口

支持的框架：
- OWL框架
- AGNO框架
- MCP服务
- 内置工具系统
"""

from typing import List, Dict, Any, Optional, Union, Callable, Type
import inspect
import logging
import asyncio
from pydantic import BaseModel, create_model

from app.frameworks.owl.base_tool import BaseTool as OWLBaseTool
from app.frameworks.agno.base_tool import BaseTool as AGNOBaseTool
from app.tools.advanced.retrieval_tool import AdvancedRetrievalTool, RetrievalToolInput, RetrievalToolOutput

logger = logging.getLogger(__name__)

class OWLToolAdapter(OWLBaseTool):
    """OWL框架工具适配器"""
    
    name: str
    description: str
    args_schema: Type[BaseModel]
    returns: Type[BaseModel]
    
    def __init__(self, tool_instance):
        """初始化适配器"""
        super().__init__()
        self.tool_instance = tool_instance
        
        # 设置工具元数据
        metadata = tool_instance.get_tool_metadata()
        self.name = metadata.get("name", "advanced_tool")
        self.description = metadata.get("description", "高级工具")
        
        # 生成参数模式和返回模式
        self.args_schema = RetrievalToolInput
        self.returns = RetrievalToolOutput
    
    async def _call(self, params: RetrievalToolInput) -> RetrievalToolOutput:
        """执行工具调用"""
        result = await self.tool_instance.run_owl_tool(params.dict())
        
        # 构建返回值
        return RetrievalToolOutput(
            results=result.get("results", []),
            total=result.get("total", 0),
            source_distribution=result.get("source_distribution", {}),
            search_time_ms=result.get("search_time_ms", 0)
        )

class AGNOToolAdapter(AGNOBaseTool):
    """AGNO框架工具适配器"""
    
    def __init__(self, tool_instance):
        """初始化适配器"""
        self.tool_instance = tool_instance
        self._name = tool_instance.name
    
    @property
    def name(self) -> str:
        """工具名称"""
        return self._name
    
    @property
    def description(self) -> str:
        """工具描述"""
        metadata = self.tool_instance.get_tool_metadata()
        return metadata.get("description", "高级工具")
    
    async def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """执行工具调用"""
        params = {"query": query, **kwargs}
        return await self.tool_instance.run_agno_tool(**params)

class MCPToolAdapter:
    """MCP服务工具适配器"""
    
    def __init__(self, tool_instance):
        """初始化适配器"""
        self.tool_instance = tool_instance
        self.metadata = tool_instance.get_tool_metadata()
    
    def get_mcp_schema(self) -> Dict[str, Any]:
        """获取MCP服务模式"""
        return {
            "name": self.metadata.get("name"),
            "description": self.metadata.get("description"),
            "parameters": self.metadata.get("parameters")
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行MCP工具"""
        # 从kwargs中提取query
        query = kwargs.pop("query", "")
        return await self.tool_instance.run_mcp_tool(query, **kwargs)

def register_owl_tool(tool_instance) -> OWLToolAdapter:
    """将高级工具注册为OWL工具"""
    return OWLToolAdapter(tool_instance)

def register_agno_tool(tool_instance) -> AGNOToolAdapter:
    """将高级工具注册为AGNO工具"""
    return AGNOToolAdapter(tool_instance)

def register_mcp_tool(tool_instance) -> Dict[str, Any]:
    """将高级工具注册为MCP工具"""
    adapter = MCPToolAdapter(tool_instance)
    
    # 创建MCP服务定义
    tool_def = adapter.get_mcp_schema()
    tool_def["execute"] = adapter.execute
    
    return tool_def

def register_advanced_tools() -> Dict[str, Any]:
    """注册所有高级工具到各个框架"""
    from app.tools.advanced.retrieval_tool import get_advanced_retrieval_tool
    
    # 获取工具实例
    retrieval_tool = get_advanced_retrieval_tool()
    
    # 注册到各框架
    result = {
        "owl": {
            "advanced_retrieval": register_owl_tool(retrieval_tool)
        },
        "agno": {
            "advanced_retrieval": register_agno_tool(retrieval_tool)
        },
        "mcp": {
            "advanced_retrieval": register_mcp_tool(retrieval_tool)
        }
    }
    
    logger.info(f"已注册高级工具: {', '.join(result['owl'].keys())}")
    return result
