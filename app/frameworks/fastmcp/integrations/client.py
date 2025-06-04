"""
MCP客户端模块
提供与外部MCP服务交互的客户端
"""

import logging
import json
import asyncio
import time
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
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        connection_pool_size: int = 10
    ):
        """
        初始化MCP客户端
        
        参数:
            service: MCP服务ID或服务实例
            api_key: API密钥，如果提供则覆盖服务中的API密钥
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间（秒）
            connection_pool_size: 连接池大小
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
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 验证必要的信息
        if not self.api_key and self.service.auth_type == "api_key":
            raise ValueError(f"MCP服务 {self.service.name} 需要API密钥")
        
        # 创建HTTP客户端（连接池）
        limits = httpx.Limits(max_connections=connection_pool_size, max_keepalive_connections=5)
        self.client = httpx.AsyncClient(
            base_url=self.service.api_url,
            timeout=self.timeout,
            limits=limits
        )
        
        # 缓存获取的工具列表
        self._tools_cache: Optional[List[MCPToolInfo]] = None
        self._last_health_check: Optional[float] = None
        self._health_check_interval: float = 300.0  # 5分钟
        self._is_healthy: bool = True
    
    async def health_check(self, force: bool = False) -> bool:
        """
        检查MCP服务健康状态
        
        参数:
            force: 是否强制检查，忽略缓存时间
            
        返回:
            服务是否健康
        """
        current_time = time.time()
        
        # 如果不强制检查且距离上次检查时间不足间隔，返回缓存结果
        if not force and self._last_health_check:
            if current_time - self._last_health_check < self._health_check_interval:
                return self._is_healthy
        
        try:
            headers = self._get_headers()
            
            # 尝试调用健康检查端点
            response = await self.client.get(
                "/health",
                headers=headers,
                timeout=10.0  # 健康检查使用较短超时
            )
            
            self._is_healthy = response.status_code == 200
            self._last_health_check = current_time
            
            if not self._is_healthy:
                logger.warning(f"MCP服务 {self.service.name} 健康检查失败: {response.status_code}")
            
            return self._is_healthy
            
        except Exception as e:
            logger.error(f"MCP服务 {self.service.name} 健康检查异常: {str(e)}")
            self._is_healthy = False
            self._last_health_check = current_time
            return False
    
    async def _retry_request(
        self,
        request_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        带重试机制的请求执行
        
        参数:
            request_func: 请求函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        返回:
            请求结果
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # 如果不是第一次尝试，检查服务健康状态
                if attempt > 0:
                    await asyncio.sleep(self.retry_delay * attempt)
                    
                    # 检查服务健康状态
                    if not await self.health_check(force=True):
                        logger.warning(f"MCP服务 {self.service.name} 不健康，跳过重试")
                        break
                
                return await request_func(*args, **kwargs)
                
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"MCP请求超时（尝试 {attempt + 1}/{self.max_retries + 1}）: {str(e)}")
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                # 对于某些错误码不进行重试
                if e.response.status_code in [400, 401, 403, 404]:
                    logger.error(f"MCP请求失败（不重试）: {e.response.status_code}")
                    break
                logger.warning(f"MCP请求失败（尝试 {attempt + 1}/{self.max_retries + 1}）: {e.response.status_code}")
                
            except Exception as e:
                last_exception = e
                logger.warning(f"MCP请求异常（尝试 {attempt + 1}/{self.max_retries + 1}）: {str(e)}")
        
        # 所有重试都失败了，抛出最后一个异常
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("所有重试都失败了")

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
        
        async def _get_tools_request():
            headers = self._get_headers()
            
            # 调用工具列表API
            response = await self.client.get(
                "/tools",
                headers=headers
            )
            
            response.raise_for_status()
            return response.json()
        
        try:
            data = await self._retry_request(_get_tools_request)
            
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
        async def _call_tool_request():
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
            return response.json()
        
        try:
            data = await self._retry_request(_call_tool_request)
            
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
            "Accept": "application/json",
            "User-Agent": f"ZZDSJ-FastMCP-Client/1.0"
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
    api_key: Optional[str] = None,
    **kwargs
) -> MCPClient:
    """
    创建MCP客户端实例
    
    参数:
        service_id: MCP服务ID
        api_key: 可选的API密钥
        **kwargs: 其他客户端配置参数
        
    返回:
        MCP客户端实例
    """
    client = MCPClient(service_id, api_key, **kwargs)
    
    # 执行初始健康检查
    await client.health_check(force=True)
    
    return client
