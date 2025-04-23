"""
MCP客户端模块
提供与外部MCP服务交互的客户端
"""

import logging
import json
import httpx
from typing import Dict, Any, Optional, List, Union, Callable
from pydantic import BaseModel

from .registry import ExternalMCPService, get_external_mcp

logger = logging.getLogger(__name__)

# MCP请求模型
class MCPRequest(BaseModel):
    """MCP请求模型"""
    tool_name: str
    parameters: Dict[str, Any] = {}
    timeout: Optional[float] = None
    context: Optional[Dict[str, Any]] = None

# MCP响应模型
class MCPResponse(BaseModel):
    """MCP响应模型"""
    status: str
    data: Any = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# MCP工具信息
class MCPToolInfo(BaseModel):
    """MCP工具信息"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = {}
    returns: Optional[Dict[str, Any]] = None

class MCPClient:
    """MCP客户端，用于与外部MCP服务交互"""
    
    def __init__(
        self,
        service: Union[str, ExternalMCPService],
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        初始化MCP客户端
        
        参数:
            service: MCP服务ID或服务实例
            api_key: API密钥，如果提供则覆盖服务中的API密钥
            timeout: 请求超时时间（秒）
        """
        # 如果提供了服务ID，获取服务实例
        if isinstance(service, str):
            service_instance = get_external_mcp(service)
            if not service_instance:
                raise ValueError(f"未找到MCP服务: {service}")
            self.service = service_instance
        else:
            self.service = service
        
        # 使用提供的API密钥或服务中的API密钥
        self.api_key = api_key or self.service.api_key
        self.timeout = timeout
        
        # 验证必要的信息
        if not self.api_key and self.service.auth_type == "api_key":
            raise ValueError(f"MCP服务 {self.service.name} 需要API密钥")
        
        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            base_url=self.service.api_url,
            timeout=self.timeout
        )
        
        # 缓存获取的工具列表
        self._tools_cache: Optional[List[MCPToolInfo]] = None
    
    async def get_tools(self, force_refresh: bool = False) -> List[MCPToolInfo]:
        """
        获取MCP服务支持的工具列表
        
        参数:
            force_refresh: 是否强制刷新缓存
            
        返回:
            工具信息列表
        """
        if self._tools_cache is not None and not force_refresh:
            return self._tools_cache
        
        try:
            headers = self._get_headers()
            
            # 调用工具列表API
            response = await self.client.get(
                "/tools",
                headers=headers
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 解析工具列表
            tools = []
            for tool_data in data.get("tools", []):
                tool = MCPToolInfo(
                    name=tool_data["name"],
                    description=tool_data.get("description"),
                    parameters=tool_data.get("parameters", {}),
                    returns=tool_data.get("returns")
                )
                tools.append(tool)
            
            # 更新缓存
            self._tools_cache = tools
            return tools
            
        except Exception as e:
            logger.error(f"获取MCP工具列表时出错: {str(e)}")
            return []
    
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = {},
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        调用MCP工具
        
        参数:
            tool_name: 工具名称
            parameters: 工具参数
            timeout: 调用超时时间
            context: 上下文信息
            
        返回:
            MCP响应
        """
        try:
            headers = self._get_headers()
            timeout_value = timeout or self.timeout
            
            # 构建请求负载
            payload = {
                "tool": tool_name,
                "parameters": parameters
            }
            
            if context:
                payload["context"] = context
            
            # 调用工具API
            response = await self.client.post(
                "/run",
                headers=headers,
                json=payload,
                timeout=timeout_value
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 解析响应
            return MCPResponse(
                status="success",
                data=data.get("result"),
                metadata=data.get("metadata")
            )
            
        except httpx.HTTPStatusError as e:
            # 处理HTTP错误
            error_message = f"HTTP错误: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_message = error_data["error"]
            except:
                pass
            
            return MCPResponse(
                status="error",
                error=error_message
            )
            
        except Exception as e:
            # 处理其他错误
            logger.error(f"调用MCP工具\"{tool_name}\"时出错: {str(e)}")
            return MCPResponse(
                status="error",
                error=f"调用出错: {str(e)}"
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 添加认证信息
        if self.service.auth_type == "api_key" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 添加自定义认证头
        if self.service.auth_headers:
            headers.update(self.service.auth_headers)
        
        return headers
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()

async def create_mcp_client(
    service_id: str,
    api_key: Optional[str] = None
) -> MCPClient:
    """
    创建MCP客户端实例
    
    参数:
        service_id: MCP服务ID
        api_key: 可选的API密钥
        
    返回:
        MCP客户端实例
    """
    client = MCPClient(service_id, api_key)
    return client
