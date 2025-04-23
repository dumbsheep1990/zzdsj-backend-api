"""
通用MCP提供商模块
提供通用的MCP客户端实现，适用于大多数标准MCP服务
"""

import logging
import json
import httpx
from typing import Dict, Any, Optional, List, Union, AsyncIterator

from ..types.base import BaseMCPClient, ClientCapability
from ..types.chat import ChatMCPClient
from ..registry import get_external_mcp, ExternalMCPService

logger = logging.getLogger(__name__)

class GenericMCPClient(BaseMCPClient):
    """通用MCP客户端实现"""
    
    def __init__(
        self,
        service: Union[str, ExternalMCPService],
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        初始化通用MCP客户端
        
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
        
        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            base_url=self.service.api_url,
            timeout=self.timeout
        )
        
        # 缓存工具列表
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        caps = []
        for cap_str in self.service.capabilities:
            try:
                # 尝试将字符串转换为枚举
                cap = ClientCapability(cap_str)
                caps.append(cap)
            except ValueError:
                # 如果无法转换，则忽略
                pass
        
        # 确保至少有TOOLS能力
        if not caps:
            caps.append(ClientCapability.TOOLS)
        
        return caps
    
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = {},
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
            return {
                "status": "success",
                "data": data.get("result"),
                "metadata": data.get("metadata")
            }
            
        except httpx.HTTPStatusError as e:
            # 处理HTTP错误
            error_message = f"HTTP错误: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_message = error_data["error"]
            except:
                pass
            
            return {
                "status": "error",
                "error": error_message
            }
            
        except Exception as e:
            # 处理其他错误
            logger.error(f"调用MCP工具\"{tool_name}\"时出错: {str(e)}")
            return {
                "status": "error",
                "error": f"调用出错: {str(e)}"
            }
    
    async def get_tools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        参数:
            force_refresh: 是否强制刷新缓存
            
        返回:
            工具描述列表
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
                tool = {
                    "name": tool_data["name"],
                    "description": tool_data.get("description", ""),
                    "parameters": tool_data.get("parameters", {})
                }
                tools.append(tool)
            
            # 更新缓存
            self._tools_cache = tools
            return tools
            
        except Exception as e:
            logger.error(f"获取MCP工具列表时出错: {str(e)}")
            return []
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
    
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

class GenericChatMCPClient(GenericMCPClient, ChatMCPClient):
    """通用聊天MCP客户端实现"""
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        caps = super().capabilities
        
        # 确保具有聊天能力
        if ClientCapability.CHAT not in caps:
            caps.append(ClientCapability.CHAT)
        
        return caps
    
    async def send_message(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送消息到聊天模型
        
        参数:
            messages: 消息列表，每条消息包含role和content
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            tools: 可用工具列表
            **kwargs: 其他参数
            
        返回:
            模型响应
        """
        try:
            headers = self._get_headers()
            
            # 构建请求负载
            payload = {
                "messages": messages,
            }
            
            if model:
                payload["model"] = model
            
            if temperature is not None:
                payload["temperature"] = temperature
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            if tools:
                payload["tools"] = tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                payload[key] = value
            
            # 调用聊天API
            response = await self.client.post(
                "/chat",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"发送聊天消息时出错: {str(e)}")
            return {
                "status": "error",
                "error": f"发送消息出错: {str(e)}"
            }
    
    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式发送消息到聊天模型
        
        参数:
            messages: 消息列表，每条消息包含role和content
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            tools: 可用工具列表
            **kwargs: 其他参数
            
        返回:
            模型响应流迭代器
        """
        try:
            headers = self._get_headers()
            
            # 构建请求负载
            payload = {
                "messages": messages,
                "stream": True
            }
            
            if model:
                payload["model"] = model
            
            if temperature is not None:
                payload["temperature"] = temperature
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            if tools:
                payload["tools"] = tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                payload[key] = value
            
            # 流式调用聊天API
            async with self.client.stream(
                "POST",
                "/chat",
                headers=headers,
                json=payload,
                timeout=None  # 流式响应不应设置超时
            ) as response:
                response.raise_for_status()
                
                # 逐行处理流式响应
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    
                    # 解析SSE格式
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析流式响应数据: {data}")
            
        except Exception as e:
            logger.error(f"流式发送聊天消息时出错: {str(e)}")
            yield {
                "status": "error",
                "error": f"流式发送消息出错: {str(e)}"
            }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用的聊天模型列表
        
        返回:
            模型信息列表
        """
        try:
            headers = self._get_headers()
            
            # 调用模型列表API
            response = await self.client.get(
                "/models",
                headers=headers
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data.get("models", [])
            
        except Exception as e:
            logger.error(f"获取模型列表时出错: {str(e)}")
            return []

async def create_client(
    service_id: str,
    api_key: Optional[str] = None,
    client_type: Optional[str] = None,
    **kwargs
) -> Union[GenericMCPClient, GenericChatMCPClient]:
    """
    创建通用MCP客户端
    
    参数:
        service_id: 服务ID
        api_key: API密钥
        client_type: 客户端类型 (chat, image, map, data)
        **kwargs: 其他参数
        
    返回:
        MCP客户端实例
    """
    service = get_external_mcp(service_id)
    if not service:
        raise ValueError(f"未找到MCP服务: {service_id}")
    
    # 根据类型创建不同的客户端
    if client_type == "chat" or "chat" in service.capabilities:
        return GenericChatMCPClient(service, api_key, **kwargs)
    
    # 默认返回通用客户端
    return GenericMCPClient(service, api_key, **kwargs)
