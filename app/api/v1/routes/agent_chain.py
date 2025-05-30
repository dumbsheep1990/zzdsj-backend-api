"""
Agent链调度API路由
负责管理和执行多Agent调度任务
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime

from app.models.database import get_db
from app.models.assistants import Assistant
from app.schemas.agent_chain import (
    AgentChainRequest,
    AgentChainResponse,
    AgentChainConfig,
    AgentChainStatus
)
from app.api.v1.dependencies import (
    ResponseFormatter, get_request_context, get_agent_adapter
)
from core.agent_chain.chain_executor import (
    AgentChainExecutor, get_agent_chain_executor
)
from app.messaging.core.models import MessageRole, TextMessage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/execute", response_model=Dict[str, Any])
async def execute_agent_chain(
    chain_request: AgentChainRequest,
    chain_executor: AgentChainExecutor = Depends(get_agent_chain_executor),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    执行Agent调用链，支持多Agent的链式调用
    """
    # 验证调用链配置
    if not chain_request.chain_id and not chain_request.chain_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供调用链ID或调用链配置"
        )
    
    # 获取调用链配置
    chain_config = None
    if chain_request.chain_id:
        # 从数据库或缓存中获取预定义的调用链配置
        # 实际实现应该从数据库加载，这里简化为示例配置
        chain_config = {
            "id": chain_request.chain_id,
            "name": "示例调用链",
            "description": "示例调用链配置",
            "execution_mode": "sequential",
            "agents": [
                {"id": 1, "name": "研究助手"},
                {"id": 2, "name": "回答助手"}
            ]
        }
    else:
        # 使用请求中提供的配置
        chain_config = chain_request.chain_config.dict()
    
    # 检查Agent是否存在
    agent_ids = [agent["id"] for agent in chain_config["agents"]]
    for agent_id in agent_ids:
        agent = db.query(Assistant).filter(Assistant.id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent ID {agent_id} 不存在"
            )
    
    # 准备调用链上下文
    context = chain_request.context or {}
    
    # 执行调用链
    try:
        # 根据请求决定是否使用流式响应
        if chain_request.stream:
            # 流式响应
            stream_result = await chain_executor.execute_chain(
                chain_config=chain_config,
                input_message=chain_request.input,
                user_id=chain_request.user_id,
                stream=True,
                context=context
            )
            
            # 返回SSE流
            return StreamingResponse(
                content=stream_result.get_async_content(),
                media_type="text/event-stream"
            )
        else:
            # 同步响应
            result_messages = await chain_executor.execute_chain(
                chain_config=chain_config,
                input_message=chain_request.input,
                user_id=chain_request.user_id,
                stream=False,
                context=context
            )
            
            # 使用OpenAI兼容格式返回结果
            openai_response = ResponseFormatter.format_openai_compatible(result_messages)
            return openai_response
            
    except Exception as e:
        logger.error(f"执行Agent调用链时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行Agent调用链时出错: {str(e)}"
        )


@router.post("/stream")
async def execute_agent_chain_stream(
    chain_request: AgentChainRequest,
    chain_executor: AgentChainExecutor = Depends(get_agent_chain_executor),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    流式执行Agent调用链，返回SSE格式的响应流
    """
    # 确保请求使用流模式
    chain_request.stream = True
    return await execute_agent_chain(chain_request, chain_executor, background_tasks, db)


@router.post("/config", response_model=AgentChainConfig)
async def create_agent_chain_config(
    chain_config: AgentChainConfig,
    db: Session = Depends(get_db)
):
    """
    创建新的Agent调用链配置
    """
    # 这里应该实现创建调用链配置的逻辑
    # 示例实现
    result = {
        "id": f"chain-{int(datetime.now().timestamp())}",
        "name": chain_config.name,
        "description": chain_config.description,
        "execution_mode": chain_config.execution_mode,
        "agents": chain_config.agents,
        "created_at": datetime.now().isoformat()
    }
    
    return ResponseFormatter.format_success(result)


@router.get("/configs", response_model=List[AgentChainConfig])
async def list_agent_chain_configs(
    db: Session = Depends(get_db)
):
    """
    获取所有Agent调用链配置
    """
    # 这里应该实现获取所有调用链配置的逻辑
    # 示例实现
    configs = [
        {
            "id": "chain-1",
            "name": "研究-回答调用链",
            "description": "先使用研究助手获取信息，再使用回答助手生成最终回答",
            "execution_mode": "sequential",
            "agents": [
                {"id": 1, "name": "研究助手"},
                {"id": 2, "name": "回答助手"}
            ],
            "created_at": "2023-05-01T12:00:00Z"
        },
        {
            "id": "chain-2",
            "name": "并行分析调用链",
            "description": "并行使用多个专家助手分析问题",
            "execution_mode": "parallel",
            "agents": [
                {"id": 3, "name": "技术专家"},
                {"id": 4, "name": "财务专家"},
                {"id": 5, "name": "法律专家"}
            ],
            "created_at": "2023-05-02T12:00:00Z"
        }
    ]
    
    return ResponseFormatter.format_success(configs)


@router.get("/configs/{chain_id}", response_model=AgentChainConfig)
async def get_agent_chain_config(
    chain_id: str,
    db: Session = Depends(get_db)
):
    """
    获取Agent调用链配置详情
    """
    # 这里应该实现获取特定调用链配置的逻辑
    # 示例实现
    config = {
        "id": chain_id,
        "name": "研究-回答调用链",
        "description": "先使用研究助手获取信息，再使用回答助手生成最终回答",
        "execution_mode": "sequential",
        "agents": [
            {"id": 1, "name": "研究助手"},
            {"id": 2, "name": "回答助手"}
        ],
        "created_at": "2023-05-01T12:00:00Z"
    }
    
    return ResponseFormatter.format_success(config)


@router.delete("/configs/{chain_id}")
async def delete_agent_chain_config(
    chain_id: str,
    db: Session = Depends(get_db)
):
    """
    删除Agent调用链配置
    """
    # 这里应该实现删除调用链配置的逻辑
    # 示例实现
    return ResponseFormatter.format_success(None, message=f"已删除调用链配置 {chain_id}")


@router.get("/status/{execution_id}", response_model=AgentChainStatus)
async def get_agent_chain_execution_status(
    execution_id: str,
    db: Session = Depends(get_db)
):
    """
    获取Agent调用链执行状态
    """
    # 这里应该实现获取调用链执行状态的逻辑
    # 示例实现
    status = {
        "execution_id": execution_id,
        "chain_id": "chain-1",
        "status": "completed",
        "progress": 100,
        "start_time": "2023-05-01T12:00:00Z",
        "end_time": "2023-05-01T12:01:00Z",
        "steps": [
            {
                "agent_id": 1,
                "agent_name": "研究助手",
                "status": "completed",
                "start_time": "2023-05-01T12:00:00Z",
                "end_time": "2023-05-01T12:00:30Z"
            },
            {
                "agent_id": 2,
                "agent_name": "回答助手",
                "status": "completed",
                "start_time": "2023-05-01T12:00:30Z",
                "end_time": "2023-05-01T12:01:00Z"
            }
        ]
    }
    
    return ResponseFormatter.format_success(status)
