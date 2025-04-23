"""
OpenAI MCP集成模块
提供与OpenAI MCP服务的集成
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union
from httpx import AsyncClient
from .client import MCPClient, MCPResponse
from .registry import get_external_mcp

logger = logging.getLogger(__name__)

class OpenAIMCPClient(MCPClient):
    """
    OpenAI MCP客户端
    针对OpenAI的特定实现
    """
    
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = {},
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        调用OpenAI MCP工具
        
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
                            return MCPResponse(
                                status="success",
                                data=function_args,
                                metadata={
                                    "model": data.get("model"),
                                    "id": data.get("id"),
                                    "tool_call_id": tool_call.get("id")
                                }
                            )
                        except:
                            continue
            
            return MCPResponse(
                status="error",
                error="未找到工具执行结果",
                metadata={"model": data.get("model"), "id": data.get("id")}
            )
            
        except Exception as e:
            logger.error(f"调用OpenAI MCP工具\"{tool_name}\"时出错: {str(e)}")
            return MCPResponse(
                status="error",
                error=f"调用OpenAI工具出错: {str(e)}"
            )

async def create_openai_client(
    service_id: str = "openai-gpt",
    api_key: Optional[str] = None
) -> OpenAIMCPClient:
    """
    创建OpenAI MCP客户端
    
    参数:
        service_id: 服务ID，默认为"openai-gpt"
        api_key: 可选的API密钥
        
    返回:
        OpenAI MCP客户端
    """
    service = get_external_mcp(service_id)
    if not service:
        from app.config import settings
        # 如果服务不存在，尝试使用配置中的值创建
        from .registry import register_external_mcp
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
    
    return OpenAIMCPClient(service, api_key)
