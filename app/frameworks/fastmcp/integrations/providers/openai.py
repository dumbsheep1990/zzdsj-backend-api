"""
OpenAI MCP提供商模块
提供OpenAI特定的MCP客户端实现
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union, AsyncIterator

from ..types.base import ClientCapability
from ..types.chat import ChatMCPClient
from ..registry import get_external_mcp, ExternalMCPService
from .generic import GenericMCPClient

logger = logging.getLogger(__name__)

class OpenAIMCPClient(GenericMCPClient, ChatMCPClient):
    """OpenAI MCP客户端实现"""
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        return [
            ClientCapability.CHAT,
            ClientCapability.TOOLS,
            ClientCapability.EMBEDDINGS,
            ClientCapability.RETRIEVAL
        ]
    
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = {},
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用OpenAI工具
        
        参数:
            tool_name: 工具名称
            parameters: 工具参数
            timeout: 调用超时时间
            context: 上下文信息
            
        返回:
            工具返回结果
        """
        try:
            headers = self._get_headers()
            timeout_value = timeout or self.timeout
            
            # OpenAI特定的API格式
            payload = {
                "model": context.get("model", "gpt-4o") if context else "gpt-4o",
                "max_tokens": context.get("max_tokens", 1024) if context else 1024,
                "messages": [
                    {
                        "role": "system", 
                        "content": context.get("system_prompt", "You are a helpful assistant.") if context else "You are a helpful assistant."
                    },
                    {
                        "role": "user",
                        "content": "Please use the provided tool to complete this task."
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": "A tool to perform specific operations",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    }
                ],
                "tool_choice": {"type": "function", "function": {"name": tool_name}}
            }
            
            # 添加参数
            for key, value in parameters.items():
                param_type = "string"
                if isinstance(value, int):
                    param_type = "integer"
                elif isinstance(value, float):
                    param_type = "number"
                elif isinstance(value, bool):
                    param_type = "boolean"
                elif isinstance(value, list):
                    param_type = "array"
                elif isinstance(value, dict):
                    param_type = "object"
                
                payload["tools"][0]["function"]["parameters"]["properties"][key] = {"type": param_type}
                payload["tools"][0]["function"]["parameters"]["required"].append(key)
            
            # 更新上下文消息
            if context and "messages" in context:
                # 保留系统消息
                system_messages = [msg for msg in payload["messages"] if msg["role"] == "system"]
                user_messages = context["messages"]
                payload["messages"] = system_messages + user_messages
            
            # 调用OpenAI API
            response = await self.client.post(
                "/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout_value
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 解析OpenAI响应
            tool_calls = None
            if data.get("choices") and len(data["choices"]) > 0:
                if data["choices"][0].get("message", {}).get("tool_calls"):
                    tool_calls = data["choices"][0]["message"]["tool_calls"]
            
            if tool_calls:
                for tool_call in tool_calls:
                    if tool_call.get("function", {}).get("name") == tool_name:
                        try:
                            function_args = json.loads(tool_call["function"].get("arguments", "{}"))
                            return {
                                "status": "success",
                                "data": function_args,
                                "metadata": {
                                    "model": data.get("model"),
                                    "id": data.get("id"),
                                    "tool_call_id": tool_call.get("id")
                                }
                            }
                        except:
                            continue
            
            return {
                "status": "error",
                "error": "未找到工具执行结果",
                "metadata": {"model": data.get("model"), "id": data.get("id")}
            }
            
        except Exception as e:
            logger.error(f"调用OpenAI MCP工具\"{tool_name}\"时出错: {str(e)}")
            return {
                "status": "error",
                "error": f"调用OpenAI工具出错: {str(e)}"
            }
    
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
        发送消息到OpenAI模型
        
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
                "model": model or "gpt-4o"
            }
            
            if temperature is not None:
                payload["temperature"] = temperature
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            if tools:
                processed_tools = []
                for tool in tools:
                    processed_tool = {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                        }
                    }
                    processed_tools.append(processed_tool)
                
                payload["tools"] = processed_tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                payload[key] = value
            
            # 调用聊天API
            response = await self.client.post(
                "/chat/completions",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 处理响应
            result = {
                "id": data.get("id"),
                "model": data.get("model"),
                "usage": data.get("usage", {})
            }
            
            if data.get("choices") and len(data["choices"]) > 0:
                choice = data["choices"][0]
                result["message"] = choice.get("message", {})
                result["finish_reason"] = choice.get("finish_reason")
            
            return result
            
        except Exception as e:
            logger.error(f"发送OpenAI聊天消息时出错: {str(e)}")
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
        流式发送消息到OpenAI模型
        
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
                "model": model or "gpt-4o",
                "stream": True
            }
            
            if temperature is not None:
                payload["temperature"] = temperature
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            if tools:
                processed_tools = []
                for tool in tools:
                    processed_tool = {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                        }
                    }
                    processed_tools.append(processed_tool)
                
                payload["tools"] = processed_tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key != "stream":  # 确保stream参数为True
                    payload[key] = value
            
            # 流式调用聊天API
            async with self.client.stream(
                "POST",
                "/chat/completions",
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
                            logger.warning(f"无法解析OpenAI流式响应数据: {data}")
            
        except Exception as e:
            logger.error(f"流式发送OpenAI聊天消息时出错: {str(e)}")
            yield {
                "status": "error",
                "error": f"流式发送消息出错: {str(e)}"
            }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用的OpenAI模型列表
        
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
            
            return data.get("data", [])
            
        except Exception as e:
            logger.error(f"获取OpenAI模型列表时出错: {str(e)}")
            return []

async def create_chat_client(
    service_id: str = "openai-gpt",
    api_key: Optional[str] = None,
    **kwargs
) -> OpenAIMCPClient:
    """
    创建OpenAI聊天客户端
    
    参数:
        service_id: 服务ID，默认为"openai-gpt"
        api_key: API密钥
        **kwargs: 其他参数
        
    返回:
        OpenAI MCP客户端
    """
    service = get_external_mcp(service_id)
    if not service:
        from app.config import settings
        # 如果服务不存在，尝试使用配置中的值创建
        from ..registry import register_external_mcp
        service = register_external_mcp(
            id=service_id,
            name="OpenAI GPT",
            description="OpenAI的GPT模型MCP服务",
            provider="openai",
            api_url=settings.OPENAI_API_BASE,
            api_key=api_key or settings.OPENAI_API_KEY,
            capabilities=["chat", "tools", "embeddings", "retrieval"],
            metadata={
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            }
        )
    
    return OpenAIMCPClient(service, api_key, **kwargs)

async def create_client(
    service_id: str = "openai-gpt",
    api_key: Optional[str] = None,
    client_type: Optional[str] = None,
    **kwargs
) -> OpenAIMCPClient:
    """
    创建OpenAI MCP客户端
    
    参数:
        service_id: 服务ID，默认为"openai-gpt"
        api_key: API密钥
        client_type: 客户端类型
        **kwargs: 其他参数
        
    返回:
        OpenAI MCP客户端
    """
    # OpenAI客户端目前只支持聊天功能
    return await create_chat_client(service_id, api_key, **kwargs)
