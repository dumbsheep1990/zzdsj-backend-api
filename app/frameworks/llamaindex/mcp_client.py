"""
MCP工具客户端模块
提供与MCP服务的通信和工具调用功能
"""

from typing import Dict, Any, Optional, List, Union
import logging
import httpx
import json
import asyncio
from datetime import datetime

from app.frameworks.llamaindex.mcp_requests import MCPRequestBuilder

logger = logging.getLogger(__name__)

class MCPToolClient:
    """MCP工具客户端"""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8000/api/mcp/tools",
        timeout: float = 30.0
    ):
        """
        初始化MCP工具客户端
        
        参数:
            base_url: MCP服务基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.timeout = timeout
    
    async def call_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        调用MCP工具
        
        参数:
            tool_name: 工具名称
            params: 参数字典
            metadata: 元数据（可选）
            
        返回:
            工具执行结果
        """
        try:
            # 构建请求
            request = MCPRequestBuilder.build_tool_request(tool_name, params, metadata)
            
            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/{tool_name}",
                    json=request
                )
                
                # 检查响应状态
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                return MCPRequestBuilder.parse_response(result)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP工具调用HTTP错误: {str(e)}")
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_json = e.response.json()
                if "detail" in error_json:
                    error_detail = error_json["detail"]
            except:
                pass
            raise Exception(f"MCP工具调用失败: {error_detail}")
            
        except httpx.TimeoutException:
            logger.error(f"MCP工具调用超时: {tool_name}")
            raise Exception(f"MCP工具调用超时 (>{self.timeout}秒)")
            
        except Exception as e:
            logger.error(f"MCP工具调用出错: {str(e)}")
            raise Exception(f"MCP工具调用失败: {str(e)}")
    
    async def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        获取工具的JSON Schema
        
        参数:
            tool_name: 工具名称
            
        返回:
            工具的JSON Schema
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/{tool_name}/schema")
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"获取工具Schema失败: {str(e)}")
            raise Exception(f"获取工具Schema失败: {str(e)}")
    
    async def get_tool_examples(self, tool_name: str) -> List[Dict[str, Any]]:
        """
        获取工具的参数示例
        
        参数:
            tool_name: 工具名称
            
        返回:
            工具的参数示例列表
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/{tool_name}/examples")
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"获取工具示例失败: {str(e)}")
            raise Exception(f"获取工具示例失败: {str(e)}")
    
    async def list_tools(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        参数:
            category: 按类别筛选（可选）
            tag: 按标签筛选（可选）
            
        返回:
            工具信息列表
        """
        try:
            params = {}
            if category:
                params["category"] = category
            if tag:
                params["tag"] = tag
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"获取工具列表失败: {str(e)}")
            raise Exception(f"获取工具列表失败: {str(e)}")

# 创建全局客户端实例
_mcp_client_instance = None

def get_mcp_tool_client() -> MCPToolClient:
    """
    获取MCP工具客户端实例
    
    返回:
        MCPToolClient实例
    """
    global _mcp_client_instance
    if _mcp_client_instance is None:
        _mcp_client_instance = MCPToolClient()
    return _mcp_client_instance
