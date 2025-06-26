"""
动态Agent API路由
支持根据前端配置动态创建和管理Agent
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.utils.core.database import get_db
from app.api.deps import get_current_user
from app.frameworks.agno.dynamic_agent_factory import get_agent_factory, create_dynamic_agent
from app.models.user import User

router = APIRouter()

class ModelConfigRequest(BaseModel):
    """模型配置请求"""
    model_id: Optional[str] = Field(None, description="模型ID，不指定则使用默认模型")
    type: str = Field("chat", description="模型类型：chat, embedding, rerank")

class ToolConfigRequest(BaseModel):
    """工具配置请求"""
    tool_id: str = Field(..., description="工具ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")

class KnowledgeBaseConfigRequest(BaseModel):
    """知识库配置请求"""
    knowledge_base_id: str = Field(..., description="知识库ID")

class AgentConfigRequest(BaseModel):
    """Agent配置请求"""
    name: str = Field(..., description="Agent名称")
    role: str = Field(..., description="Agent角色")
    description: Optional[str] = Field(None, description="Agent描述")
    instructions: Optional[List[str]] = Field(default_factory=list, description="Agent指令")
    model_config: ModelConfigRequest = Field(..., description="模型配置")
    tools: List[ToolConfigRequest] = Field(default_factory=list, description="工具配置")
    knowledge_bases: List[KnowledgeBaseConfigRequest] = Field(default_factory=list, description="知识库配置")
    show_tool_calls: bool = Field(True, description="是否显示工具调用")
    markdown: bool = Field(True, description="是否使用Markdown格式")
    max_loops: int = Field(10, description="最大循环次数")

class AgentQueryRequest(BaseModel):
    """Agent查询请求"""
    query: str = Field(..., description="查询内容")
    stream: bool = Field(False, description="是否流式响应")

class AgentResponse(BaseModel):
    """Agent响应"""
    agent_id: str
    name: str
    role: str
    status: str
    message: str

class QueryResponse(BaseModel):
    """查询响应"""
    response: str
    agent_id: str
    timestamp: str

# 全局Agent存储（在生产环境中应该使用数据库或缓存）
_active_agents: Dict[str, Any] = {}

@router.post("/create", response_model=AgentResponse)
async def create_dynamic_agent_endpoint(
    config: AgentConfigRequest,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建动态Agent
    
    根据前端配置动态创建Agent，支持：
    - 动态模型配置
    - 动态工具配置
    - 动态知识库配置
    """
    try:
        # 转换配置为内部格式
        agent_config = {
            "name": config.name,
            "role": config.role,
            "description": config.description,
            "instructions": config.instructions,
            "model_config": {
                "model_id": config.model_config.model_id,
                "type": config.model_config.type
            },
            "tools": [
                {
                    "tool_id": tool.tool_id,
                    "params": tool.params
                }
                for tool in config.tools
            ],
            "knowledge_bases": [
                {
                    "knowledge_base_id": kb.knowledge_base_id
                }
                for kb in config.knowledge_bases
            ],
            "show_tool_calls": config.show_tool_calls,
            "markdown": config.markdown,
            "max_loops": config.max_loops
        }
        
        # 创建动态Agent
        agent = await create_dynamic_agent(
            agent_config=agent_config,
            user_id=str(current_user.id),
            session_id=session_id
        )
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Agent创建失败"
            )
        
        # 生成Agent ID
        import uuid
        agent_id = str(uuid.uuid4())
        
        # 存储Agent实例
        _active_agents[agent_id] = {
            "agent": agent,
            "config": agent_config,
            "user_id": str(current_user.id),
            "session_id": session_id
        }
        
        return AgentResponse(
            agent_id=agent_id,
            name=config.name,
            role=config.role,
            status="created",
            message=f"Agent '{config.name}' 创建成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建Agent失败: {str(e)}"
        )

@router.post("/{agent_id}/query", response_model=QueryResponse)
async def query_agent(
    agent_id: str,
    request: AgentQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查询Agent
    
    向指定的Agent发送查询并获取响应
    """
    try:
        # 验证Agent存在
        if agent_id not in _active_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent不存在"
            )
        
        agent_data = _active_agents[agent_id]
        
        # 验证用户权限
        if agent_data["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此Agent"
            )
        
        agent = agent_data["agent"]
        
        # 执行查询
        if request.stream:
            # TODO: 实现流式响应
            response = await agent.aquery(request.query)
        else:
            response = await agent.aquery(request.query)
        
        from datetime import datetime
        return QueryResponse(
            response=response,
            agent_id=agent_id,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )

@router.get("/{agent_id}/status")
async def get_agent_status(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取Agent状态
    """
    try:
        if agent_id not in _active_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent不存在"
            )
        
        agent_data = _active_agents[agent_id]
        
        # 验证用户权限
        if agent_data["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此Agent"
            )
        
        config = agent_data["config"]
        
        return {
            "agent_id": agent_id,
            "name": config["name"],
            "role": config["role"],
            "status": "active",
            "tools_count": len(config["tools"]),
            "knowledge_bases_count": len(config["knowledge_bases"]),
            "model_type": config["model_config"]["type"],
            "session_id": agent_data["session_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取状态失败: {str(e)}"
        )

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除Agent
    """
    try:
        if agent_id not in _active_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent不存在"
            )
        
        agent_data = _active_agents[agent_id]
        
        # 验证用户权限
        if agent_data["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此Agent"
            )
        
        # 删除Agent
        del _active_agents[agent_id]
        
        return {
            "message": f"Agent {agent_id} 已删除",
            "agent_id": agent_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除Agent失败: {str(e)}"
        )

@router.get("/user/agents")
async def list_user_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的Agent列表
    """
    try:
        user_agents = []
        user_id = str(current_user.id)
        
        for agent_id, agent_data in _active_agents.items():
            if agent_data["user_id"] == user_id:
                config = agent_data["config"]
                user_agents.append({
                    "agent_id": agent_id,
                    "name": config["name"],
                    "role": config["role"],
                    "description": config.get("description", ""),
                    "status": "active",
                    "tools_count": len(config["tools"]),
                    "knowledge_bases_count": len(config["knowledge_bases"]),
                    "model_type": config["model_config"]["type"]
                })
        
        return {
            "agents": user_agents,
            "total": len(user_agents)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Agent列表失败: {str(e)}"
        )

@router.get("/available-models")
async def get_available_models(
    model_type: Optional[str] = "chat",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取可用的模型列表
    """
    try:
        from app.frameworks.agno.model_config_adapter import ModelType, get_model_adapter
        
        adapter = get_model_adapter()
        
        # 根据类型获取模型
        try:
            model_type_enum = ModelType(model_type)
        except ValueError:
            model_type_enum = ModelType.CHAT
        
        models = await adapter.get_models_by_type(model_type_enum)
        
        return {
            "models": [
                {
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "provider": model.provider.value,
                    "model_type": model.model_type.value,
                    "is_default": model.is_default,
                    "is_enabled": model.is_enabled,
                    "description": model.description
                }
                for model in models
            ],
            "total": len(models)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}"
        )

@router.get("/available-tools")
async def get_available_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户可用的工具列表
    """
    try:
        from app.services.tools.tool_service import ToolService
        
        tool_service = ToolService(db)
        tools = await tool_service.get_user_available_tools(str(current_user.id))
        
        return {
            "tools": [
                {
                    "tool_id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "framework": tool.framework,
                    "category": tool.category,
                    "is_enabled": tool.is_enabled
                }
                for tool in tools
            ],
            "total": len(tools)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具列表失败: {str(e)}"
        ) 