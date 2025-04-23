"""
Anthropic Claude MCP集成模块
提供与Anthropic Claude MCP服务的集成
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union
from httpx import AsyncClient
from .client import MCPClient, MCPResponse
from .registry import get_external_mcp

logger = logging.getLogger(__name__)

class ClaudeMCPClient(MCPClient):
    """
    Anthropic Claude MCP客户端
    针对Claude的特定实现
    """
    
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = {},
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        调用Claude MCP工具
        
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
                payload["tools"][0]["input_schema"]["properties"][key] = {"type": "string"}
            
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
                return MCPResponse(
                    status="success",
                    data=tool_results,
                    metadata={"model": data.get("model"), "id": data.get("id")}
                )
            else:
                return MCPResponse(
                    status="error",
                    error="未找到工具执行结果",
                    metadata={"model": data.get("model"), "id": data.get("id")}
                )
            
        except Exception as e:
            logger.error(f"调用Claude MCP工具\"{tool_name}\"时出错: {str(e)}")
            return MCPResponse(
                status="error",
                error=f"调用Claude工具出错: {str(e)}"
            )

async def create_claude_client(
    service_id: str = "anthropic-claude",
    api_key: Optional[str] = None
) -> ClaudeMCPClient:
    """
    创建Claude MCP客户端
    
    参数:
        service_id: 服务ID，默认为"anthropic-claude"
        api_key: 可选的API密钥
        
    返回:
        Claude MCP客户端
    """
    service = get_external_mcp(service_id)
    if not service:
        from app.config import settings
        # 如果服务不存在，尝试使用配置中的值创建
        from .registry import register_external_mcp
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
    
    return ClaudeMCPClient(service, api_key)
