"""
Anthropic MCP提供商模块
提供Anthropic Claude特定的MCP客户端实现
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union, AsyncIterator

from ..types.base import ClientCapability
from ..types.chat import ChatMCPClient
from ..registry import get_external_mcp, ExternalMCPService
from .generic import GenericMCPClient

logger = logging.getLogger(__name__)

class AnthropicMCPClient(GenericMCPClient, ChatMCPClient):
    """Anthropic Claude MCP客户端实现"""
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        return [
            ClientCapability.CHAT,
            ClientCapability.TOOLS,
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
        调用Anthropic Claude工具
        
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
            
            # Claude特定的API格式
            payload = {
                "model": context.get("model", "claude-3-opus-20240229") if context else "claude-3-opus-20240229",
                "max_tokens": context.get("max_tokens", 1024) if context else 1024,
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text",
                                "text": context.get("system_prompt", "You are a helpful assistant.") if context else "You are a helpful assistant."
                            }
                        ]
                    }
                ],
                "tools": [
                    {
                        "name": tool_name,
                        "description": "A tool to perform specific operations",
                        "input_schema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ],
                "tool_choice": {"type": "tool", "name": tool_name}
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
                
                payload["tools"][0]["input_schema"]["properties"][key] = {"type": param_type}
            
            # 更新上下文消息
            if context and "messages" in context:
                payload["messages"] = context["messages"]
            
            # 调用Claude API
            response = await self.client.post(
                "/messages",
                headers=headers,
                json=payload,
                timeout=timeout_value
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 解析Claude响应
            tool_results = None
            if data.get("content") and len(data["content"]) > 0:
                for content in data["content"]:
                    if content.get("type") == "tool_use":
                        tool_results = content.get("input", {})
                        break
            
            if tool_results:
                return {
                    "status": "success",
                    "data": tool_results,
                    "metadata": {"model": data.get("model"), "id": data.get("id")}
                }
            else:
                return {
                    "status": "error",
                    "error": "未找到工具执行结果",
                    "metadata": {"model": data.get("model"), "id": data.get("id")}
                }
            
        except Exception as e:
            logger.error(f"调用Claude MCP工具\"{tool_name}\"时出错: {str(e)}")
            return {
                "status": "error",
                "error": f"调用Claude工具出错: {str(e)}"
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
        发送消息到Claude模型
        
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
            
            # 处理Claude的消息格式
            claude_messages = []
            system_prompt = None
            
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                # 处理系统消息
                if role == "system":
                    system_prompt = content
                    continue
                
                # 处理用户和助手消息
                claude_role = "user" if role == "user" else "assistant"
                
                # 处理内容格式
                if isinstance(content, str):
                    claude_content = [{"type": "text", "text": content}]
                elif isinstance(content, list):
                    claude_content = content
                else:
                    claude_content = [{"type": "text", "text": str(content)}]
                
                claude_messages.append({
                    "role": claude_role,
                    "content": claude_content
                })
            
            # 构建请求负载
            payload = {
                "model": model or "claude-3-opus-20240229",
                "messages": claude_messages
            }
            
            # 如果有系统提示，添加到第一个用户消息前
            if system_prompt and claude_messages and claude_messages[0]["role"] == "user":
                system_content = {"type": "text", "text": system_prompt}
                if isinstance(claude_messages[0]["content"], list):
                    claude_messages[0]["content"].insert(0, system_content)
                else:
                    claude_messages[0]["content"] = [system_content]
            
            if temperature is not None:
                payload["temperature"] = temperature
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            if tools:
                processed_tools = []
                for tool in tools:
                    processed_tool = {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("parameters", {"type": "object", "properties": {}})
                    }
                    processed_tools.append(processed_tool)
                
                payload["tools"] = processed_tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                payload[key] = value
            
            # 调用Claude聊天API
            response = await self.client.post(
                "/messages",
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
            
            # 处理Claude的内容格式
            if data.get("content"):
                result["message"] = {"role": "assistant", "content": data["content"]}
                result["stop_reason"] = data.get("stop_reason")
            
            return result
            
        except Exception as e:
            logger.error(f"发送Claude聊天消息时出错: {str(e)}")
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
        流式发送消息到Claude模型
        
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
            
            # 处理Claude的消息格式
            claude_messages = []
            system_prompt = None
            
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                # 处理系统消息
                if role == "system":
                    system_prompt = content
                    continue
                
                # 处理用户和助手消息
                claude_role = "user" if role == "user" else "assistant"
                
                # 处理内容格式
                if isinstance(content, str):
                    claude_content = [{"type": "text", "text": content}]
                elif isinstance(content, list):
                    claude_content = content
                else:
                    claude_content = [{"type": "text", "text": str(content)}]
                
                claude_messages.append({
                    "role": claude_role,
                    "content": claude_content
                })
            
            # 构建请求负载
            payload = {
                "model": model or "claude-3-opus-20240229",
                "messages": claude_messages,
                "stream": True
            }
            
            # 如果有系统提示，添加到第一个用户消息前
            if system_prompt and claude_messages and claude_messages[0]["role"] == "user":
                system_content = {"type": "text", "text": system_prompt}
                if isinstance(claude_messages[0]["content"], list):
                    claude_messages[0]["content"].insert(0, system_content)
                else:
                    claude_messages[0]["content"] = [system_content]
            
            if temperature is not None:
                payload["temperature"] = temperature
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            if tools:
                processed_tools = []
                for tool in tools:
                    processed_tool = {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("parameters", {"type": "object", "properties": {}})
                    }
                    processed_tools.append(processed_tool)
                
                payload["tools"] = processed_tools
            
            # 添加其他参数
            for key, value in kwargs.items():
                if key != "stream":  # 确保stream参数为True
                    payload[key] = value
            
            # 流式调用Claude聊天API
            async with self.client.stream(
                "POST",
                "/messages",
                headers=headers,
                json=payload,
                timeout=None  # 流式响应不应设置超时
            ) as response:
                response.raise_for_status()
                
                # 逐行处理流式响应
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "event: ping":
                        continue
                    
                    # Claude的流式响应格式
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            if data != "[DONE]":
                                logger.warning(f"无法解析Claude流式响应数据: {data}")
            
        except Exception as e:
            logger.error(f"流式发送Claude聊天消息时出错: {str(e)}")
            yield {
                "status": "error",
                "error": f"流式发送消息出错: {str(e)}"
            }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用的Claude模型列表
        
        返回:
            模型信息列表
        """
        # Claude API不提供模型列表端点，返回预定义列表
        return [
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "description": "Anthropic's most powerful model for highly complex tasks"
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "description": "Anthropic's balanced model for a wide range of tasks"
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "description": "Anthropic's fastest and most compact model for simple tasks"
            }
        ]

async def create_chat_client(
    service_id: str = "anthropic-claude",
    api_key: Optional[str] = None,
    **kwargs
) -> AnthropicMCPClient:
    """
    创建Anthropic Claude聊天客户端
    
    参数:
        service_id: 服务ID，默认为"anthropic-claude"
        api_key: API密钥
        **kwargs: 其他参数
        
    返回:
        Anthropic MCP客户端
    """
    service = get_external_mcp(service_id)
    if not service:
        from app.config import settings
        # 如果服务不存在，尝试使用配置中的值创建
        from ..registry import register_external_mcp
        service = register_external_mcp(
            id=service_id,
            name="Anthropic Claude",
            description="Anthropic的Claude模型MCP服务",
            provider="anthropic",
            api_url=settings.ANTHROPIC_API_BASE,
            api_key=api_key or settings.ANTHROPIC_API_KEY,
            capabilities=["chat", "tools", "retrieval"],
            metadata={
                "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
            }
        )
    
    return AnthropicMCPClient(service, api_key, **kwargs)

async def create_client(
    service_id: str = "anthropic-claude",
    api_key: Optional[str] = None,
    client_type: Optional[str] = None,
    **kwargs
) -> AnthropicMCPClient:
    """
    创建Anthropic MCP客户端
    
    参数:
        service_id: 服务ID，默认为"anthropic-claude"
        api_key: API密钥
        client_type: 客户端类型
        **kwargs: 其他参数
        
    返回:
        Anthropic MCP客户端
    """
    # Anthropic客户端目前只支持聊天功能
    return await create_chat_client(service_id, api_key, **kwargs)
