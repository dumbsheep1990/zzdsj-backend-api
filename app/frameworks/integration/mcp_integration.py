"""
MCP集成服务模块
负责将MCP工具与LlamaIndex框架集成
"""

from typing import List, Dict, Any, Optional
from llama_index.core.tools import BaseTool
from llama_index.tools.mcp import MCPTool
from app.frameworks.fastmcp.server import get_mcp_server
import logging

logger = logging.getLogger(__name__)

class MCPIntegrationService:
    """MCP集成服务"""
    
    def __init__(self):
        # 确保MCP服务器已启动
        self.mcp_server = get_mcp_server()
        self.api_base_url = "http://localhost:8000/api/mcp/tools"
    
    def get_tool_by_name(self, tool_name: str) -> Optional[MCPTool]:
        """根据名称获取MCP工具"""
        from app.frameworks.llamaindex.tools import create_mcp_tool
        return create_mcp_tool(tool_name)
    
    def get_all_tools(self, category: Optional[str] = None, tag: Optional[str] = None) -> List[MCPTool]:
        """获取所有MCP工具"""
        from app.frameworks.llamaindex.tools import get_all_mcp_tools
        return get_all_mcp_tools(category, tag)
    
    def create_external_mcp_tool(self, provider_id: str, tool_name: str) -> Optional[MCPTool]:
        """创建外部MCP工具的LlamaIndex适配"""
        try:
            # 获取MCP客户端
            from app.frameworks.fastmcp.integrations.client_factory import create_mcp_client
            client = create_mcp_client(provider_id)
            if not client:
                logger.error(f"无法创建MCP客户端: provider_id={provider_id}")
                return None
            
            # 获取工具schema
            tool_schema = client.get_tool_schema(tool_name)
            if not tool_schema:
                logger.error(f"无法获取工具schema: tool_name={tool_name}")
                return None
            
            # 创建MCP工具规格
            from llama_index.tools.mcp import MCPToolSpec
            tool_spec = MCPToolSpec(
                name=tool_name,
                description=tool_schema.get("description", f"External MCP tool: {tool_name}"),
                parameters=tool_schema.get("parameters", {})
            )
            
            # 创建MCP工具
            mcp_tool = MCPTool(
                spec=tool_spec,
                mcp_server_url=client.api_url
            )
            
            return mcp_tool
            
        except Exception as e:
            logger.error(f"创建外部MCP工具时出错: {str(e)}")
            return None
            
    def register_tool(self, tool_name: str, description: str, tool_function: callable) -> bool:
        """注册新的MCP工具"""
        try:
            from app.frameworks.fastmcp.tools import register_tool
            
            # 注册MCP工具
            decorated_func = register_tool(
                name=tool_name,
                description=description
            )(tool_function)
            
            logger.info(f"成功注册MCP工具: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"注册MCP工具时出错: {str(e)}")
            return False
            
    def get_mcp_server_status(self) -> Dict[str, Any]:
        """获取MCP服务器状态"""
        from app.frameworks.fastmcp.server import get_server_status
        return get_server_status()
        
    def restart_mcp_server(self) -> Dict[str, str]:
        """重启MCP服务器"""
        from app.frameworks.fastmcp.server import restart_server
        return restart_server()
