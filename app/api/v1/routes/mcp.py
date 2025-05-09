"""
MCP工具链API路由
提供统一的MCP工具链接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
import logging

from app.models.database import get_db
from app.api.v1.dependencies import ResponseFormatter, get_agent_adapter, get_request_context
from app.messaging.adapters.agent import AgentAdapter
from app.messaging.core.models import (
    Message as CoreMessage, MessageRole, TextMessage, MCPToolMessage
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/tools/search")
async def search_tools(
    query: str,
    agent_adapter: AgentAdapter = Depends(get_agent_adapter),
    db: Session = Depends(get_db)
):
    """
    搜索可用的MCP工具
    """
    try:
        # 在这里应该实现MCP工具搜索逻辑
        # 示例实现
        tools = [
            {
                "id": "tool-search",
                "name": "搜索工具",
                "description": "搜索互联网获取信息",
                "type": "search"
            },
            {
                "id": "tool-calculator",
                "name": "计算器",
                "description": "执行数学计算",
                "type": "utility"
            }
        ]
        
        return ResponseFormatter.format_success(tools)
    except Exception as e:
        logger.error(f"搜索工具错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"搜索工具出错: {str(e)}")


@router.post("/tools/execute")
async def execute_tool(
    tool_id: str,
    parameters: Dict[str, Any],
    agent_adapter: AgentAdapter = Depends(get_agent_adapter),
    db: Session = Depends(get_db)
):
    """
    执行MCP工具
    """
    try:
        # 在这里应该实现MCP工具执行逻辑
        # 示例实现
        result = {
            "tool_id": tool_id,
            "status": "success",
            "result": f"执行工具 {tool_id} 的结果"
        }
        
        return ResponseFormatter.format_success(result)
    except Exception as e:
        logger.error(f"执行工具错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"执行工具出错: {str(e)}")


@router.post("/chat")
async def mcp_chat(
    message: str,
    tool_ids: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    stream: bool = False,
    agent_adapter: AgentAdapter = Depends(get_agent_adapter),
    db: Session = Depends(get_db)
):
    """
    使用MCP工具进行对话
    """
    # 创建用户消息
    user_message = TextMessage(
        content=message,
        role=MessageRole.USER
    )
    
    # 准备MCP工具参数
    tools_config = {
        "enabled_tools": tool_ids or [],
        "conversation_id": conversation_id
    }
    
    # 使用统一消息系统处理请求
    try:
        # 选择适当的回复格式
        if stream:
            # 异步处理返回SSE流
            return await agent_adapter.to_sse_response(
                messages=[user_message],
                tools_config=tools_config,
                memory_key=f"mcp_conversation_{conversation_id}" if conversation_id else None
            )
        else:
            # 同步处理返回JSON
            response_messages = await agent_adapter.process_messages(
                messages=[user_message],
                tools_config=tools_config,
                memory_key=f"mcp_conversation_{conversation_id}" if conversation_id else None
            )
            
            # 使用OpenAI兼容格式返回结果
            return ResponseFormatter.format_openai_compatible(response_messages)
    except Exception as e:
        logger.error(f"MCP对话处理错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP对话处理出错: {str(e)}")


@router.post("/chat/stream")
async def mcp_chat_stream(
    message: str,
    tool_ids: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    agent_adapter: AgentAdapter = Depends(get_agent_adapter),
    db: Session = Depends(get_db)
):
    """
    流式MCP对话接口，返回SSE格式的响应流
    """
    return await mcp_chat(message, tool_ids, conversation_id, True, agent_adapter, db)
