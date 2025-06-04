"""
助手模块：提供AI助手、智能体和问答助手等相关功能
"""

from fastapi import APIRouter

from app.api.frontend.assistants import assistant, manage, qa, agent

# 创建助手模块路由
router = APIRouter()

# 注册子路由
router.include_router(assistant.router, prefix="/ai", tags=["AI助手"])
router.include_router(manage.router, prefix="/manage", tags=["助手管理"])
router.include_router(qa.router, prefix="/qa", tags=["问答助手"])
router.include_router(agent.router, prefix="/agent", tags=["智能体服务"])

"""
智能体服务API: 提供智能体任务处理和工具调用的接口
"""


from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from app.utils.database import get_db
from app.services_new.agent_services_new import AgentService
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.api.dependencies import get_current_user, ResponseFormatter
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


class TaskRequest(BaseModel):
    """任务请求模型"""
    task: str = Field(..., min_length=1, description="任务描述")
    framework: Optional[str] = Field(None, description="使用的框架")
    tool_ids: Optional[List[str]] = Field(None, description="工具ID列表")
    parameters: Optional[Dict[str, Any]] = Field(None, description="额外参数")


class TaskResponse(BaseModel):
    """任务响应模型"""
    result: str = Field(..., description="任务结果")
    metadata: Dict[str, Any] = Field(..., description="元数据")


class ToolConfig(BaseModel):
    """工具配置模型"""
    tool_id: Optional[str] = Field(None, description="工具ID")
    tool_type: str = Field(..., description="工具类型: mcp, query_engine, function")
    tool_name: str = Field(..., description="工具名称")
    enabled: bool = Field(True, description="是否启用")
    settings: Optional[Dict[str, Any]] = Field(None, description="工具设置")


@router.post("/task", response_model=Dict[str, Any])
async def process_task(
        request: TaskRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    处理智能体任务

    支持多种框架和工具调用
    """
    try:
        service = AgentService(db)
        result, metadata = await service.process_task(
            task=request.task,
            framework=request.framework,
            tool_ids=request.tool_ids,
            parameters=request.parameters,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "result": result,
                "metadata": metadata
            },
            message="任务处理成功"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"处理任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="处理任务时出错")


@router.get("/frameworks", response_model=Dict[str, Any])
async def list_frameworks(db: Session = Depends(get_db)):
    """获取可用的智能体框架列表"""
    try:
        service = AgentService(db)
        frameworks = service.list_available_frameworks()

        return ResponseFormatter.format_success(
            data={
                "frameworks": frameworks,
                "total": len(frameworks)
            }
        )

    except Exception as e:
        logger.error(f"获取框架列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取框架列表时出错")


@router.post("/assistants/{assistant_id}/tools", response_model=Dict[str, Any])
async def configure_assistant_tools(
        assistant_id: int,
        tools: List[ToolConfig],
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    配置助手工具

    只有助手所有者可以配置
    """
    try:
        service = AgentService(db)
        configured_tools = await service.configure_agent_tools(
            agent_id=assistant_id,
            tool_configs=[tool.model_dump() for tool in tools],
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "tools": configured_tools,
                "count": len(configured_tools)
            },
            message="工具配置成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"配置助手工具失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="配置助手工具时出错")


@router.get("/assistants/{assistant_id}/tools", response_model=Dict[str, Any])
async def get_assistant_tools(
        assistant_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手工具配置"""
    try:
        service = AgentService(db)
        tools = await service.get_agent_tools(assistant_id)

        return ResponseFormatter.format_success(
            data={
                "tools": tools,
                "count": len(tools)
            }
        )

    except Exception as e:
        logger.error(f"获取助手工具配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取助手工具配置时出错")

"""
助手API管理模块: 提供与AI助手交互的端点，
支持各种模式（文本、图像、语音）和不同的接口格式
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
import logging

from app.utils.database import get_db
from app.services_new.assistant_service_new import AssistantService
from app.schemas.assistant import (
    AssistantCreate,
    AssistantUpdate,
    AssistantResponse,
    ConversationCreate,
    ConversationResponse,
    AssistantListResponse,
    ConversationListResponse
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.api.dependencies import get_current_user, ResponseFormatter
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_assistant(
        request: AssistantCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建新助手"""
    try:
        service = AssistantService(db)
        assistant = await service.create_assistant(
            data=request.model_dump(),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description,
                "model": assistant.model,
                "capabilities": assistant.capabilities,
                "is_public": assistant.is_public,
                "created_at": assistant.created_at.isoformat()
            },
            message="助手创建成功"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建助手失败")


@router.get("/", response_model=Dict[str, Any])
async def list_assistants(
        category: Optional[str] = Query(None, description="分类筛选"),
        capabilities: Optional[List[str]] = Query(None, description="能力筛选"),
        is_public: Optional[bool] = Query(None, description="公开性筛选"),
        search: Optional[str] = Query(None, description="搜索关键词"),
        tags: Optional[List[str]] = Query(None, description="标签筛选"),
        skip: int = Query(0, ge=0, description="跳过条数"),
        limit: int = Query(20, ge=1, le=100, description="返回条数"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手列表"""
    try:
        service = AssistantService(db)
        assistants, total = await service.get_assistants(
            skip=skip,
            limit=limit,
            user_id=current_user.id,
            category=category,
            capabilities=capabilities,
            is_public=is_public,
            search=search,
            tags=tags
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description,
                        "model": a.model,
                        "category": a.category,
                        "capabilities": a.capabilities,
                        "tags": a.tags,
                        "is_public": a.is_public,
                        "avatar_url": a.avatar_url,
                        "created_at": a.created_at.isoformat(),
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                        "owner_id": a.owner_id,
                        "is_owner": a.owner_id == current_user.id
                    }
                    for a in assistants
                ],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )

    except Exception as e:
        logger.error(f"获取助手列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取助手列表失败")


@router.get("/{assistant_id}", response_model=Dict[str, Any])
async def get_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        include_knowledge_bases: bool = Query(False, description="包含知识库信息"),
        include_statistics: bool = Query(False, description="包含统计信息"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手详情"""
    try:
        service = AssistantService(db)
        assistant = await service.get_assistant_by_id(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        if not assistant:
            raise HTTPException(status_code=404, detail="助手不存在")

        response_data = {
            "id": assistant.id,
            "name": assistant.name,
            "description": assistant.description,
            "model": assistant.model,
            "system_prompt": assistant.system_prompt,
            "capabilities": assistant.capabilities,
            "is_public": assistant.is_public,
            "category": assistant.category,
            "tags": assistant.tags,
            "avatar_url": assistant.avatar_url,
            "config": assistant.config,
            "created_at": assistant.created_at.isoformat(),
            "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None,
            "owner_id": assistant.owner_id,
            "is_owner": assistant.owner_id == current_user.id
        }

        # 添加知识库信息
        if include_knowledge_bases:
            knowledge_bases = await service.get_assistant_knowledge_bases(assistant_id)
            response_data["knowledge_bases"] = [
                {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "is_public": kb.is_public
                }
                for kb in knowledge_bases
            ]

        # 添加统计信息
        if include_statistics:
            stats = await service.get_assistant_statistics(assistant_id)
            response_data["statistics"] = stats

        return ResponseFormatter.format_success(data=response_data)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取助手详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取助手详情失败")


@router.put("/{assistant_id}", response_model=Dict[str, Any])
async def update_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        request: AssistantUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新助手信息"""
    try:
        service = AssistantService(db)
        assistant = await service.update_assistant(
            assistant_id=assistant_id,
            data=request.model_dump(exclude_unset=True),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description,
                "model": assistant.model,
                "updated_at": assistant.updated_at.isoformat()
            },
            message="助手更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新助手失败")


@router.delete("/{assistant_id}")
async def delete_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除助手"""
    try:
        service = AssistantService(db)
        success = await service.delete_assistant(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="删除助手失败")

        return ResponseFormatter.format_success(
            data={"assistant_id": assistant_id},
            message="助手删除成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除助手失败")


# ==================== 知识库管理接口 ====================

@router.post("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
async def link_knowledge_base(
        assistant_id: int = Path(..., description="助手ID"),
        knowledge_base_id: int = Path(..., description="知识库ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """关联知识库到助手"""
    try:
        service = AssistantService(db)
        success = await service.add_knowledge_base(
            assistant_id=assistant_id,
            knowledge_base_id=knowledge_base_id,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "assistant_id": assistant_id,
                "knowledge_base_id": knowledge_base_id
            },
            message="知识库关联成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"关联知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="关联知识库失败")


@router.delete("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
async def unlink_knowledge_base(
        assistant_id: int = Path(..., description="助手ID"),
        knowledge_base_id: int = Path(..., description="知识库ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """解除助手与知识库的关联"""
    try:
        service = AssistantService(db)
        success = await service.remove_knowledge_base(
            assistant_id=assistant_id,
            knowledge_base_id=knowledge_base_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="解除关联失败")

        return ResponseFormatter.format_success(
            data={
                "assistant_id": assistant_id,
                "knowledge_base_id": knowledge_base_id
            },
            message="已解除知识库关联"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"解除知识库关联失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="解除关联失败")


# ==================== 对话管理接口 ====================

@router.post("/{assistant_id}/conversations", response_model=Dict[str, Any])
async def create_conversation(
        assistant_id: int = Path(..., description="助手ID"),
        request: ConversationCreate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建对话"""
    try:
        # 确保 assistant_id 一致
        request.assistant_id = assistant_id

        service = AssistantService(db)
        conversation = await service.create_conversation(
            data=request,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": conversation.id,
                "assistant_id": conversation.assistant_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat()
            },
            message="对话创建成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建对话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建对话失败")


@router.get("/conversations", response_model=Dict[str, Any])
async def list_conversations(
        assistant_id: Optional[int] = Query(None, description="助手ID筛选"),
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取用户对话列表"""
    try:
        service = AssistantService(db)
        conversations, total = await service.get_user_conversations(
            user_id=current_user.id,
            assistant_id=assistant_id,
            skip=skip,
            limit=limit
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": c.id,
                        "assistant_id": c.assistant_id,
                        "title": c.title,
                        "created_at": c.created_at.isoformat(),
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None
                    }
                    for c in conversations
                ],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )

    except Exception as e:
        logger.error(f"获取对话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取对话列表失败")


# ==================== 统计接口 ====================

@router.get("/categories/statistics", response_model=Dict[str, Any])
async def get_category_statistics(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手分类统计"""
    try:
        service = AssistantService(db)
        categories = await service.get_category_statistics(user_id=current_user.id)

        return ResponseFormatter.format_success(
            data={
                "categories": categories,
                "total_categories": len(categories)
            }
        )

    except Exception as e:
        logger.error(f"获取分类统计失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取分类统计失败")


"""
问答助手路由：提供问答助手管理、问题卡片管理和文档关联操作
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from app.utils.database import get_db
from app.services_new.qa_service import QAService
from app.schemas.assistant_qa import (
    AssistantCreate, AssistantUpdate,
    QuestionCreate, QuestionUpdate,
    AnswerSettingsUpdate, DocumentSegmentSettingsUpdate
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.api.dependencies import get_current_user, ResponseFormatter
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 助手管理接口 ====================

@router.get("/assistants", response_model=Dict[str, Any])
async def list_assistants(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        status: Optional[str] = Query(None, description="状态过滤"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取问答助手列表"""
    try:
        service = QAService(db)
        assistants, total = await service.get_qa_assistants(
            skip=skip,
            limit=limit,
            user_id=current_user.id,
            status=status
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description,
                        "type": a.type,
                        "icon": a.icon,
                        "status": a.status,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None
                    }
                    for a in assistants
                ],
                "total": total
            }
        )

    except Exception as e:
        logger.error(f"获取问答助手列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问答助手列表失败")


@router.get("/assistants/{assistant_id}", response_model=Dict[str, Any])
async def get_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        include_stats: bool = Query(False, description="包含统计信息"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取问答助手详情"""
    try:
        service = QAService(db)
        assistant = await service.get_qa_assistant(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        response_data = {
            "id": assistant.id,
            "name": assistant.name,
            "description": assistant.description,
            "type": assistant.type,
            "icon": assistant.icon,
            "status": assistant.status,
            "created_at": assistant.created_at.isoformat() if assistant.created_at else None,
            "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None,
            "config": assistant.config,
            "knowledge_base_id": assistant.knowledge_base_id
        }

        # 添加统计信息
        if include_stats:
            stats = await service.get_assistant_statistics(assistant_id)
            response_data["stats"] = stats

        return ResponseFormatter.format_success(data=response_data)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"获取问答助手详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问答助手详情失败")


@router.post("/assistants", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_assistant(
        assistant: AssistantCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建问答助手"""
    try:
        service = QAService(db)
        created = await service.create_qa_assistant(
            data=assistant.model_dump(),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": created.id,
                "name": created.name,
                "description": created.description,
                "type": created.type,
                "icon": created.icon,
                "status": created.status,
                "created_at": created.created_at.isoformat() if created.created_at else None
            },
            message="问答助手创建成功"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建问答助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建问答助手失败")


@router.put("/assistants/{assistant_id}", response_model=Dict[str, Any])
async def update_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        assistant: AssistantUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问答助手信息"""
    try:
        service = QAService(db)
        updated = await service.update_qa_assistant(
            assistant_id=assistant_id,
            data=assistant.model_dump(exclude_unset=True),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "name": updated.name,
                "description": updated.description,
                "updated_at": updated.updated_at.isoformat() if updated.updated_at else None
            },
            message="问答助手更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新问答助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新问答助手失败")


@router.delete("/assistants/{assistant_id}")
async def delete_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除问答助手"""
    try:
        service = QAService(db)
        success = await service.delete_qa_assistant(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="删除助手失败")

        return ResponseFormatter.format_success(
            data={"assistant_id": assistant_id},
            message="问答助手已成功删除"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除问答助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除问答助手失败")


# ==================== 问题管理接口 ====================

@router.get("/assistants/{assistant_id}/questions", response_model=Dict[str, Any])
async def list_questions(
        assistant_id: int = Path(..., description="助手ID"),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手的问题列表"""
    try:
        service = QAService(db)
        questions, total = await service.get_questions(
            assistant_id=assistant_id,
            skip=skip,
            limit=limit,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": q.id,
                        "question": q.question,
                        "answer": q.answer,
                        "category": q.category,
                        "views_count": q.views_count,
                        "created_at": q.created_at.isoformat() if q.created_at else None,
                        "updated_at": q.updated_at.isoformat() if q.updated_at else None
                    }
                    for q in questions
                ],
                "total": total
            }
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"获取问题列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问题列表失败")


@router.get("/questions/{question_id}", response_model=Dict[str, Any])
async def get_question(
        question_id: int = Path(..., description="问题ID"),
        include_document_segments: bool = Query(True, description="包含文档分段"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取问题详情"""
    try:
        service = QAService(db)
        question = await service.get_question(
            question_id=question_id,
            include_document_segments=include_document_segments,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(data={
            "id": question.id,
            "question": question.question,
            "answer": question.answer,
            "category": question.category,
            "views_count": question.views_count,
            "assistant_id": question.assistant_id,
            "created_at": question.created_at.isoformat() if question.created_at else None,
            "updated_at": question.updated_at.isoformat() if question.updated_at else None,
            "document_segments": [
                {
                    "id": seg.id,
                    "content": seg.content,
                    "metadata": seg.metadata
                }
                for seg in getattr(question, 'document_segments', [])
            ] if include_document_segments else None
        })

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"获取问题详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问题详情失败")


@router.post("/questions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_question(
        question: QuestionCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建问题"""
    try:
        service = QAService(db)
        created = await service.create_question(
            data=question.model_dump(),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": created.id,
                "question": created.question,
                "answer": created.answer,
                "category": created.category,
                "assistant_id": created.assistant_id,
                "created_at": created.created_at.isoformat() if created.created_at else None
            },
            message="问题创建成功"
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建问题失败")


@router.put("/questions/{question_id}", response_model=Dict[str, Any])
async def update_question(
        question_id: int = Path(..., description="问题ID"),
        question: QuestionUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问题信息"""
    try:
        service = QAService(db)
        updated = await service.update_question(
            question_id=question_id,
            data=question.model_dump(exclude_unset=True),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "question": updated.question,
                "answer": updated.answer,
                "updated_at": updated.updated_at.isoformat() if updated.updated_at else None
            },
            message="问题更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新问题失败")


@router.delete("/questions/{question_id}")
async def delete_question(
        question_id: int = Path(..., description="问题ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除问题"""
    try:
        service = QAService(db)
        success = await service.delete_question(
            question_id=question_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="删除问题失败")

        return ResponseFormatter.format_success(
            data={"question_id": question_id},
            message="问题已成功删除"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除问题失败")


# ==================== 问答功能接口 ====================

@router.post("/questions/{question_id}/answer", response_model=Dict[str, Any])
async def answer_question(
        question_id: int = Path(..., description="问题ID"),
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """回答问题"""
    try:
        service = QAService(db)
        answer = await service.answer_question(
            question_id=question_id,
            user_id=current_user.id if current_user else None
        )

        return ResponseFormatter.format_success(
            data={"answer": answer}
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"回答问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="回答问题失败")


# ==================== 设置管理接口 ====================

@router.put("/questions/{question_id}/answer-settings", response_model=Dict[str, Any])
async def update_answer_settings(
        question_id: int = Path(..., description="问题ID"),
        settings: AnswerSettingsUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问题回答设置"""
    try:
        service = QAService(db)
        updated = await service.update_answer_settings(
            question_id=question_id,
            answer_mode=settings.answer_mode,
            use_cache=settings.use_cache,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "answer_mode": getattr(updated, 'answer_mode', None),
                "use_cache": getattr(updated, 'use_cache', None)
            },
            message="回答设置更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"更新回答设置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新回答设置失败")


@router.put("/questions/{question_id}/document-settings", response_model=Dict[str, Any])
async def update_document_segment_settings(
        question_id: int = Path(..., description="问题ID"),
        settings: DocumentSegmentSettingsUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问题文档分段设置"""
    try:
        service = QAService(db)
        updated = await service.update_document_segment_settings(
            question_id=question_id,
            segment_ids=settings.segment_ids,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "segment_count": len(settings.segment_ids)
            },
            message="文档分段设置更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"更新文档分段设置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新文档分段设置失败")


# MVP/auth_new/dependencies_new.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.settings import settings
from app.db.base import AsyncSession, get_db
from app.auth.schemas import TokenData, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    # 实际应查询数据库获取用户信息（示例简化）
    return User(id=int(user_id), email="user@example.com", username="test_user")


# MVP/auth_new/schemas_new.py

from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: int | None = None

class User(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str      


"""
对话管理路由
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query, Path
from app.api.frontend.dependencies import ServiceContainer, get_service_container
from app.schemas.chat import ConversationCreate, ConversationUpdate
from app.api.shared.responses import ResponseFormatter

router = APIRouter()


@router.get("/conversations")
async def list_conversations(
        assistant_id: Optional[int] = Query(None),
        search: Optional[str] = Query(None),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """获取对话列表"""
    service = container.get_conversation_service()

    # 从认证中获取user_id（这里假设已经有认证中间件）
    user_id = 1  # TODO: 从认证上下文获取

    conversations = await service.list_conversations(
        user_id=user_id,
        assistant_id=assistant_id,
        search=search,
        skip=offset,
        limit=limit
    )

    return ResponseFormatter.success(
        data={
            "conversations": conversations,
            "total": len(conversations),
            "limit": limit,
            "offset": offset
        }
    )


@router.post("/conversations")
async def create_conversation(
        data: ConversationCreate,
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """创建对话"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    conversation = await service.create(data, user_id)

    return ResponseFormatter.success(
        data=conversation,
        message="对话创建成功"
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
        conversation_id: int = Path(...),
        include_messages: bool = Query(True),
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """获取对话详情"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    if include_messages:
        conversation = await service.get_with_messages(conversation_id, user_id)
    else:
        conversation = await service.get(conversation_id, user_id)

    if not conversation:
        raise NotFoundError("对话不存在")

    return ResponseFormatter.success(data=conversation)


@router.put("/conversations/{conversation_id}")
async def update_conversation(
        conversation_id: int = Path(...),
        data: ConversationUpdate,
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """更新对话"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    conversation = await service.update(conversation_id, data, user_id)

    if not conversation:
        raise NotFoundError("对话不存在")

    return ResponseFormatter.success(
        data=conversation,
        message="对话更新成功"
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
        conversation_id: int = Path(...),
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """删除对话"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    success = await service.delete(conversation_id, user_id)

    if not success:
        raise NotFoundError("对话不存在")

    return ResponseFormatter.success(
        data={"conversation_id": conversation_id},
        message="对话删除成功"
    )



"""
依赖注入管理器
"""
from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.compression_service import CompressionService


class ServiceContainer:
    """服务容器"""

    def __init__(self, db: Session):
        self.db = db
        self._services = {}

    def get_conversation_service(self) -> ConversationService:
        """获取对话服务"""
        if 'conversation' not in self._services:
            self._services['conversation'] = ConversationService(self.db)
        return self._services['conversation']

    def get_memory_service(self) -> MemoryService:
        """获取记忆服务"""
        if 'memory' not in self._services:
            self._services['memory'] = MemoryService(self.db)
        return self._services['memory']

    def get_compression_service(self) -> CompressionService:
        """获取压缩服务"""
        if 'compression' not in self._services:
            self._services['compression'] = CompressionService(self.db)
        return self._services['compression']


def get_service_container(db: Session = Depends(get_db)) -> ServiceContainer:
    """获取服务容器"""
    return ServiceContainer(db)


"""
自定义异常类，用于服务层的错误处理
"""


class BaseServiceError(Exception):
    """服务层基础异常类"""
    def __init__(self, message: str = "服务错误"):
        self.message = message
        super().__init__(self.message)


class NotFoundError(BaseServiceError):
    """资源未找到异常"""
    def __init__(self, message: str = "资源未找到"):
        super().__init__(message)


class PermissionError(BaseServiceError):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message)


class ValidationError(BaseServiceError):
    """数据验证异常"""
    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message)


class ConflictError(BaseServiceError):
    """资源冲突异常"""
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message)


class ExternalServiceError(BaseServiceError):
    """外部服务异常"""
    def __init__(self, message: str = "外部服务错误"):
        super().__init__(message)# 助手模块优化指南


from pydantic import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()  # 加载.env文件

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/dbname")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings

Base = declarative_base()

# 异步引擎和会话工厂
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """依赖：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


from fastapi import APIRouter
from .base import router as base_router
from .lightrag import router as lightrag_router

router = APIRouter(prefix="/knowledge", tags=["知识库"])

# 注册子路由
router.include_router(base_router)
router.include_router(lightrag_router, prefix="/lightrag", tags=["LightRAG"])


"""
统一的知识库基础API
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.deps import get_db, get_current_user
from app.services.knowledge import KnowledgeService
from app.schemas_new.knowledge_base import *
from app.utils.response import success_response, error_response

logger = logging.getLogger(__name__)
router = APIRouter()


# 依赖注入
def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)


# ========== 知识库管理 ==========
@router.post("/", response_model=BaseResponse)
async def create_knowledge_base(
        request: KnowledgeBaseCreate,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """创建知识库"""
    try:
        kb = await service.create_knowledge_base(request, current_user.id)
        return success_response(data=kb, message="知识库创建成功")
    except ValueError as e:
        return error_response(error=str(e), message="创建失败")
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        return error_response(error="内部错误", message="创建失败")


@router.get("/", response_model=BaseResponse)
async def list_knowledge_bases(
        page: int = 1,
        page_size: int = 20,
        type: Optional[KnowledgeBaseType] = None,
        search: Optional[str] = None,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """获取知识库列表"""
    try:
        result = await service.list_knowledge_bases(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            kb_type=type,
            search=search
        )
        return success_response(data=result)
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        return error_response(error="获取失败")


@router.get("/{kb_id}", response_model=BaseResponse)
async def get_knowledge_base(
        kb_id: str,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """获取知识库详情"""
    try:
        kb = await service.get_knowledge_base(kb_id, current_user.id)
        if not kb:
            return error_response(error="知识库不存在", message="未找到")
        return success_response(data=kb)
    except Exception as e:
        logger.error(f"获取知识库失败: {e}")
        return error_response(error="获取失败")


@router.delete("/{kb_id}", response_model=BaseResponse)
async def delete_knowledge_base(
        kb_id: str,
        permanent: bool = False,
        background_tasks: BackgroundTasks,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """删除知识库"""
    try:
        # 添加后台清理任务
        if permanent:
            background_tasks.add_task(service.cleanup_knowledge_base, kb_id)

        result = await service.delete_knowledge_base(kb_id, current_user.id, permanent)
        return success_response(message="知识库删除成功")
    except ValueError as e:
        return error_response(error=str(e), message="删除失败")
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        return error_response(error="删除失败")


# ========== 文档管理 ==========
@router.post("/{kb_id}/documents", response_model=BaseResponse)
async def upload_document(
        kb_id: str,
        request: DocumentUpload,
        file: Optional[UploadFile] = File(None),
        background_tasks: BackgroundTasks,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """上传文档到知识库"""
    try:
        # 验证权限
        if not await service.check_write_permission(kb_id, current_user.id):
            return error_response(error="无写入权限", message="权限不足")

        # 处理文件上传
        if file:
            file_url = await service.upload_file(file, kb_id)
            request.file_url = file_url

        # 添加文档
        document = await service.add_document(kb_id, request)

        # 后台处理
        if request.auto_chunk or request.auto_vectorize:
            background_tasks.add_task(
                service.process_document,
                kb_id,
                document.id,
                request.auto_chunk,
                request.auto_vectorize,
                request.auto_extract
            )

        return success_response(data=document, message="文档上传成功")
    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        return error_response(error="上传失败")


@router.delete("/{kb_id}/documents/{doc_id}", response_model=BaseResponse)
async def delete_document(
        kb_id: str,
        doc_id: str,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """删除文档"""
    try:
        # 验证权限
        if not await service.check_write_permission(kb_id, current_user.id):
            return error_response(error="无写入权限", message="权限不足")

        await service.delete_document(kb_id, doc_id)
        return success_response(message="文档删除成功")
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return error_response(error="删除失败")


# ========== 查询接口 ==========
@router.post("/query", response_model=BaseResponse)
async def query_knowledge(
        request: QueryRequest,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """查询知识库"""
    try:
        # 验证读取权限
        for kb_id in request.knowledge_base_ids:
            if not await service.check_read_permission(kb_id, current_user.id):
                return error_response(error=f"无权访问知识库 {kb_id}", message="权限不足")

        # 执行查询
        results = await service.query(request)
        return success_response(data=results)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        return error_response(error="查询失败")


from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import json

from app.services_new.lightrag import LightRAGService
from app.schemas_new.knowledge_base import *

router = APIRouter()


def get_lightrag_service() -> LightRAGService:
    return LightRAGService()


@router.post("/workdirs", response_model=BaseResponse)
async def create_workdir(
        name: str,
        description: Optional[str] = None,
        service: LightRAGService = Depends(get_lightrag_service),
        current_user=Depends(get_current_user)
):
    """创建LightRAG工作目录"""
    try:
        workdir = await service.create_workdir(name, description, current_user.id)
        return success_response(data=workdir, message="工作目录创建成功")
    except Exception as e:
        logger.error(f"创建工作目录失败: {e}")
        return error_response(error=str(e))


@router.get("/graph/{kb_id}", response_model=BaseResponse)
async def get_knowledge_graph(
        kb_id: str,
        service: LightRAGService = Depends(get_lightrag_service),
        current_user=Depends(get_current_user)
):
    """获取知识图谱数据"""
    try:
        graph_data = await service.get_graph_data(kb_id)
        return success_response(data=graph_data)
    except Exception as e:
        logger.error(f"获取图谱数据失败: {e}")
        return error_response(error="获取失败")


@router.post("/query/stream")
async def query_stream(
        request: QueryRequest,
        service: LightRAGService = Depends(get_lightrag_service),
        current_user=Depends(get_current_user)
):
    """流式查询接口"""

    async def generate():
        try:
            async for chunk in service.query_stream(request):
                yield json.dumps(chunk) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


"""
知识管理系统的 API 接口规范 和 数据验证规则。
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class KnowledgeBaseType(str, Enum):
    """知识库类型"""
    TRADITIONAL = "traditional"  # 传统向量知识库
    LIGHTRAG = "lightrag"  # LightRAG知识图谱
    HYBRID = "hybrid"  # 混合模式


class ChunkingStrategy(str, Enum):
    """切分策略"""
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"


class DocumentStatus(str, Enum):
    """文档状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# 基础请求/响应模型
class BaseRequest(BaseModel):
    """基础请求模型"""

    class Config:
        use_enum_values = True


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# 知识库相关模型
class KnowledgeBaseCreate(BaseRequest):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: KnowledgeBaseType = KnowledgeBaseType.TRADITIONAL
    config: Dict[str, Any] = Field(default_factory=dict)

    # 通用配置
    language: str = Field("zh", regex="^(zh|en)$")
    is_active: bool = True
    public_read: bool = False
    public_write: bool = False

    # 传统知识库配置
    chunking_strategy: Optional[ChunkingStrategy] = ChunkingStrategy.SENTENCE
    chunk_size: Optional[int] = Field(1000, ge=100, le=10000)
    chunk_overlap: Optional[int] = Field(200, ge=0, le=1000)
    embedding_model: Optional[str] = "text-embedding-ada-002"
    vector_store: Optional[str] = "chroma"


class DocumentUpload(BaseRequest):
    """文档上传请求"""
    title: str = Field(..., min_length=1, max_length=200)
    content: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 处理选项
    auto_chunk: bool = True
    auto_vectorize: bool = True
    auto_extract: bool = True  # 自动提取实体和关系

    @validator('content', 'file_url')
    def validate_content_or_file(cls, v, values):
        if not v and not values.get('content') and not values.get('file_url'):
            raise ValueError('必须提供 content 或 file_url')
        return v


class QueryRequest(BaseRequest):
    """查询请求"""
    query: str = Field(..., min_length=1, max_length=1000)
    knowledge_base_ids: List[str] = Field(..., min_items=1)

    # 查询选项
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.7, ge=0, le=1)
    include_metadata: bool = True

    # 高级选项
    use_reranking: bool = False
    use_graph_relations: bool = True  # 对于LightRAG
    query_mode: str = Field("hybrid", regex="^(vector|graph|hybrid)$")


"""
智能体服务层：处理智能体相关的业务逻辑
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
from sqlalchemy.orm import Session

from app.core.agent_manager import AgentManager
from app.core.exceptions import NotFoundError, ValidationError
from app.models.tools import Tool, AgentTool

logger = logging.getLogger(__name__)


class AgentService:
    """智能体服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.agent_manager = AgentManager()

    async def process_task(
            self,
            task: str,
            framework: Optional[str] = None,
            tool_ids: Optional[List[str]] = None,
            parameters: Optional[Dict[str, Any]] = None,
            user_id: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """处理智能体任务"""
        try:
            # 加载工具
            tools = []
            if tool_ids:
                tools = await self._load_tools(tool_ids, user_id)

            # 处理任务
            result, metadata = await self.agent_manager.process_task(
                task=task,
                use_framework=framework,
                tools=tools,
                parameters=parameters
            )

            # 记录任务历史
            await self._record_task_history(
                user_id=user_id,
                task=task,
                framework=framework,
                result=result,
                metadata=metadata
            )

            return result, metadata

        except Exception as e:
            logger.error(f"处理任务失败: {str(e)}", exc_info=True)
            raise ValidationError(f"任务处理失败: {str(e)}")

    async def _load_tools(self, tool_ids: List[str], user_id: Optional[int] = None) -> List[Any]:
        """加载指定的工具"""
        tools = []

        for tool_id in tool_ids:
            # 从数据库加载工具配置
            tool = self.db.query(Tool).filter(
                Tool.id == tool_id,
                Tool.is_active == True
            ).first()

            if not tool:
                logger.warning(f"工具未找到: {tool_id}")
                continue

            # 检查权限
            if user_id and tool.requires_permission:
                if not await self._check_tool_permission(tool_id, user_id):
                    logger.warning(f"用户 {user_id} 无权使用工具 {tool_id}")
                    continue

            # 实例化工具
            tool_instance = await self._instantiate_tool(tool)
            if tool_instance:
                tools.append(tool_instance)

        return tools

    async def _check_tool_permission(self, tool_id: str, user_id: int) -> bool:
        """检查用户是否有权限使用工具"""
        # TODO: 实现权限检查逻辑
        return True

    async def _instantiate_tool(self, tool: Tool) -> Optional[Any]:
        """实例化工具"""
        try:
            # 根据工具类型实例化
            if tool.type == "mcp":
                from app.frameworks.integration.mcp_integration import MCPIntegrationService
                mcp_service = MCPIntegrationService()
                return mcp_service.get_tool_by_name(tool.name)

            elif tool.type == "function":
                # TODO: 实现函数工具加载
                pass

            elif tool.type == "query_engine":
                # TODO: 实现查询引擎工具加载
                pass

            return None

        except Exception as e:
            logger.error(f"实例化工具失败 {tool.name}: {str(e)}")
            return None

    async def _record_task_history(
            self,
            user_id: Optional[int],
            task: str,
            framework: Optional[str],
            result: str,
            metadata: Dict[str, Any]
    ):
        """记录任务历史"""
        try:
            # TODO: 实现任务历史记录
            pass
        except Exception as e:
            logger.error(f"记录任务历史失败: {str(e)}")

    def list_available_frameworks(self) -> List[Dict[str, Any]]:
        """获取可用的智能体框架列表"""
        return self.agent_manager.list_available_frameworks()

    def list_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用的智能体工具列表"""
        # 从数据库获取工具列表
        tools = self.db.query(Tool).filter(Tool.is_active == True).all()

        tool_list = []
        for tool in tools:
            tool_list.append({
                "id": tool.id,
                "name": tool.name,
                "type": tool.type,
                "description": tool.description,
                "category": tool.category,
                "requires_permission": tool.requires_permission,
                "config": tool.config
            })

        # 添加内置工具
        builtin_tools = self.agent_manager.list_available_tools()
        tool_list.extend(builtin_tools)

        return tool_list

    async def configure_agent_tools(
            self,
            agent_id: int,
            tool_configs: List[Dict[str, Any]],
            user_id: int
    ) -> List[Dict[str, Any]]:
        """配置智能体工具"""
        # 验证智能体权限
        from app.services.assistant_service import AssistantService
        assistant_service = AssistantService(self.db)
        assistant = await assistant_service.get_assistant_by_id(agent_id, user_id)

        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以配置助手工具")

        # 清除现有配置
        self.db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()

        # 添加新配置
        configured_tools = []
        for config in tool_configs:
            agent_tool = AgentTool(
                agent_id=agent_id,
                tool_id=config.get("tool_id"),
                tool_type=config["tool_type"],
                tool_name=config["tool_name"],
                enabled=config.get("enabled", True),
                settings=config.get("settings", {})
            )
            self.db.add(agent_tool)

            configured_tools.append({
                "tool_type": agent_tool.tool_type,
                "tool_name": agent_tool.tool_name,
                "enabled": agent_tool.enabled,
                "settings": agent_tool.settings
            })

        try:
            self.db.commit()
            logger.info(f"配置智能体 {agent_id} 的工具成功")
            return configured_tools

        except Exception as e:
            self.db.rollback()
            logger.error(f"配置智能体工具失败: {str(e)}")
            raise ValidationError(f"配置工具失败: {str(e)}")

    async def get_agent_tools(self, agent_id: int) -> List[Dict[str, Any]]:
        """获取智能体工具配置"""
        agent_tools = self.db.query(AgentTool).filter(
            AgentTool.agent_id == agent_id
        ).all()

        tools = []
        for agent_tool in agent_tools:
            tools.append({
                "tool_id": agent_tool.tool_id,
                "tool_type": agent_tool.tool_type,
                "tool_name": agent_tool.tool_name,
                "enabled": agent_tool.enabled,
                "settings": agent_tool.settings
            })

        return tools


"""
助手服务层：统一处理所有助手相关的业务逻辑
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from app.models.assistant import Assistant, Conversation, Message, AssistantKnowledgeBase
from app.models.knowledge import KnowledgeBase
from app.schemas.assistant import (
    AssistantCreate, AssistantUpdate, AssistantResponse,
    ConversationCreate, ConversationResponse,
    MessageCreate, MessageResponse
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError

logger = logging.getLogger(__name__)


class AssistantService:
    """助手服务类"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 助手管理 ====================

    async def create_assistant(self, data: Dict[str, Any], user_id: int) -> Assistant:
        """创建助手"""
        try:
            # 设置所有者
            data['owner_id'] = user_id

            # 创建助手实例
            assistant = Assistant(**data)
            self.db.add(assistant)
            self.db.commit()
            self.db.refresh(assistant)

            logger.info(f"Created assistant: {assistant.id} for user: {user_id}")
            return assistant

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create assistant: {str(e)}")
            raise ValidationError(f"创建助手失败: {str(e)}")

    async def get_assistant_by_id(self, assistant_id: int, user_id: Optional[int] = None) -> Optional[Assistant]:
        """获取助手详情"""
        assistant = self.db.query(Assistant).filter(
            Assistant.id == assistant_id,
            Assistant.is_active == True
        ).first()

        if not assistant:
            return None

        # 权限检查：用户只能访问自己的助手或公开助手
        if user_id and not assistant.is_public and assistant.owner_id != user_id:
            raise PermissionError("无权访问该助手")

        return assistant

    async def get_assistants(
            self,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[int] = None,
            category: Optional[str] = None,
            capabilities: Optional[List[str]] = None,
            is_public: Optional[bool] = None,
            search: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> Tuple[List[Assistant], int]:
        """获取助手列表"""
        query = self.db.query(Assistant).filter(Assistant.is_active == True)

        # 用户过滤：用户可以看到自己的助手和公开助手
        if user_id:
            query = query.filter(
                or_(
                    Assistant.owner_id == user_id,
                    Assistant.is_public == True
                )
            )

        # 分类过滤
        if category:
            query = query.filter(Assistant.category == category)

        # 能力过滤
        if capabilities:
            for cap in capabilities:
                query = query.filter(Assistant.capabilities.contains([cap]))

        # 公开性过滤
        if is_public is not None:
            query = query.filter(Assistant.is_public == is_public)

        # 搜索过滤
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Assistant.name.ilike(search_pattern),
                    Assistant.description.ilike(search_pattern)
                )
            )

        # 标签过滤
        if tags:
            for tag in tags:
                query = query.filter(Assistant.tags.contains([tag]))

        # 获取总数
        total = query.count()

        # 分页
        assistants = query.offset(skip).limit(limit).all()

        return assistants, total

    async def update_assistant(self, assistant_id: int, data: Dict[str, Any], user_id: int) -> Assistant:
        """更新助手"""
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        # 权限检查：只有所有者可以更新
        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以更新助手")

        try:
            # 更新字段
            for key, value in data.items():
                if hasattr(assistant, key) and value is not None:
                    setattr(assistant, key, value)

            assistant.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(assistant)

            logger.info(f"Updated assistant: {assistant_id}")
            return assistant

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update assistant: {str(e)}")
            raise ValidationError(f"更新助手失败: {str(e)}")

    async def delete_assistant(self, assistant_id: int, user_id: int) -> bool:
        """删除助手（软删除）"""
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        # 权限检查：只有所有者可以删除
        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以删除助手")

        try:
            assistant.is_active = False
            assistant.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Deleted assistant: {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete assistant: {str(e)}")
            return False

    # ==================== 知识库管理 ====================

    async def add_knowledge_base(self, assistant_id: int, knowledge_base_id: int, user_id: int) -> bool:
        """关联知识库到助手"""
        # 验证助手
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以管理助手知识库")

        # 验证知识库
        knowledge_base = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.id == knowledge_base_id
        ).first()

        if not knowledge_base:
            raise NotFoundError("知识库不存在")

        # 验证用户是否有权限使用该知识库
        if not knowledge_base.is_public and knowledge_base.owner_id != user_id:
            raise PermissionError("无权使用该知识库")

        # 检查是否已关联
        existing = self.db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id,
            AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
        ).first()

        if existing:
            return True  # 已存在，直接返回成功

        try:
            # 创建关联
            link = AssistantKnowledgeBase(
                assistant_id=assistant_id,
                knowledge_base_id=knowledge_base_id
            )
            self.db.add(link)
            self.db.commit()

            logger.info(f"Linked knowledge base {knowledge_base_id} to assistant {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to link knowledge base: {str(e)}")
            raise ValidationError(f"关联知识库失败: {str(e)}")

    async def remove_knowledge_base(self, assistant_id: int, knowledge_base_id: int, user_id: int) -> bool:
        """解除助手与知识库的关联"""
        # 验证助手
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以管理助手知识库")

        # 查找关联
        link = self.db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id,
            AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
        ).first()

        if not link:
            raise NotFoundError("未找到关联关系")

        try:
            self.db.delete(link)
            self.db.commit()

            logger.info(f"Unlinked knowledge base {knowledge_base_id} from assistant {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to unlink knowledge base: {str(e)}")
            return False

    async def get_assistant_knowledge_bases(self, assistant_id: int) -> List[KnowledgeBase]:
        """获取助手关联的知识库列表"""
        links = self.db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id
        ).all()

        kb_ids = [link.knowledge_base_id for link in links]

        if not kb_ids:
            return []

        knowledge_bases = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.id.in_(kb_ids)
        ).all()

        return knowledge_bases

    async def clear_knowledge_bases(self, assistant_id: int, user_id: int) -> bool:
        """清除助手的所有知识库关联"""
        # 验证助手
        assistant = await self.get_assistant_by_id(assistant_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        if assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以管理助手知识库")

        try:
            self.db.query(AssistantKnowledgeBase).filter(
                AssistantKnowledgeBase.assistant_id == assistant_id
            ).delete()
            self.db.commit()

            logger.info(f"Cleared all knowledge bases for assistant {assistant_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear knowledge bases: {str(e)}")
            return False

    # ==================== 对话管理 ====================

    async def create_conversation(self, data: ConversationCreate, user_id: int) -> Conversation:
        """创建对话"""
        # 验证助手存在并有权限
        assistant = await self.get_assistant_by_id(data.assistant_id, user_id)
        if not assistant:
            raise NotFoundError("助手不存在")

        try:
            conversation = Conversation(
                assistant_id=data.assistant_id,
                user_id=user_id,
                title=data.title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                metadata=data.metadata or {}
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(f"Created conversation: {conversation.id}")
            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create conversation: {str(e)}")
            raise ValidationError(f"创建对话失败: {str(e)}")

    async def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """获取对话详情"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

        return conversation

    async def get_user_conversations(
            self,
            user_id: int,
            assistant_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[Conversation], int]:
        """获取用户对话列表"""
        query = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        )

        if assistant_id:
            query = query.filter(Conversation.assistant_id == assistant_id)

        total = query.count()
        conversations = query.order_by(
            Conversation.updated_at.desc()
        ).offset(skip).limit(limit).all()

        return conversations, total

    # ==================== 统计信息 ====================

    async def get_assistant_statistics(self, assistant_id: int) -> Dict[str, Any]:
        """获取助手统计信息"""
        # 使用次数
        usage_count = self.db.query(Conversation).filter(
            Conversation.assistant_id == assistant_id
        ).count()

        # 消息总数
        message_count = self.db.query(Message).join(Conversation).filter(
            Conversation.assistant_id == assistant_id
        ).count()

        # 用户数
        unique_users = self.db.query(Conversation.user_id).filter(
            Conversation.assistant_id == assistant_id
        ).distinct().count()

        return {
            "usage_count": usage_count,
            "message_count": message_count,
            "unique_users": unique_users,
            "last_used": None  # TODO: 从对话中获取最后使用时间
        }

    async def get_category_statistics(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取分类统计信息"""
        # 基础查询
        query = self.db.query(Assistant).filter(Assistant.is_active == True)

        if user_id:
            query = query.filter(
                or_(
                    Assistant.owner_id == user_id,
                    Assistant.is_public == True
                )
            )

        assistants = query.all()

        # 统计分类
        categories = {}
        for assistant in assistants:
            category = assistant.category or "未分类"

            if category not in categories:
                categories[category] = {
                    "name": category,
                    "count": 0,
                    "public_count": 0,
                    "private_count": 0,
                    "models": set(),
                    "capabilities": set()
                }

            categories[category]["count"] += 1

            if assistant.is_public:
                categories[category]["public_count"] += 1
            else:
                categories[category]["private_count"] += 1

            categories[category]["models"].add(assistant.model)

            if assistant.capabilities:
                for cap in assistant.capabilities:
                    categories[category]["capabilities"].add(cap)

        # 转换集合为列表
        result = []
        for category_data in categories.values():
            category_data["models"] = list(category_data["models"])
            category_data["capabilities"] = list(category_data["capabilities"])
            result.append(category_data)

        return result


"""
服务层基础类
"""
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
from sqlalchemy.orm import Session
import logging

T = TypeVar('T')


class BaseService(ABC, Generic[T]):
    """服务层基础类"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def create(self, data: dict) -> T:
        """创建资源"""
        pass

    @abstractmethod
    async def get(self, id: int) -> Optional[T]:
        """获取资源"""
        pass

    @abstractmethod
    async def update(self, id: int, data: dict) -> Optional[T]:
        """更新资源"""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """删除资源"""
        pass


"""
上下文压缩服务层
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.base import BaseService
from app.models.compression import CompressionTool, AgentCompressionConfig
from app.schemas.context_compression import (
    CompressionToolCreate,
    AgentCompressionConfigCreate,
    CompressionConfig,
    CompressedContextResult
)


class CompressionService(BaseService):
    """上下文压缩服务"""

    async def compress_context(
            self,
            content: str,
            query: Optional[str] = None,
            agent_id: Optional[int] = None,
            config: Optional[CompressionConfig] = None,
            model_name: Optional[str] = None
    ) -> CompressedContextResult:
        """压缩上下文"""
        # 如果指定了agent_id，获取其配置
        if agent_id and not config:
            agent_config = await self.get_agent_config_by_agent_id(agent_id)
            if agent_config:
                config = agent_config.config

        # 执行压缩逻辑
        # TODO: 实现实际的压缩逻辑
        compressed_content = content[:1000]  # 示例：简单截断

        return CompressedContextResult(
            original_length=len(content),
            compressed_length=len(compressed_content),
            content=compressed_content,
            compression_ratio=len(compressed_content) / len(content),
            metadata={"model": model_name} if model_name else {}
        )

    async def create_tool(self, data: CompressionToolCreate) -> CompressionTool:
        """创建压缩工具"""
        tool = CompressionTool(**data.dict())
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    async def get_tools(self, skip: int = 0, limit: int = 100) -> List[CompressionTool]:
        """获取压缩工具列表"""
        return self.db.query(CompressionTool).offset(skip).limit(limit).all()

    async def get_agent_config_by_agent_id(self, agent_id: int) -> Optional[AgentCompressionConfig]:
        """根据代理ID获取压缩配置"""
        return self.db.query(AgentCompressionConfig).filter(
            AgentCompressionConfig.agent_id == agent_id
        ).first()


"""
对话服务层
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.services.base import BaseService
from app.models.chat import Conversation, Message
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    ConversationWithMessages
)
from app.core.exceptions import NotFoundError, PermissionError


class ConversationService(BaseService[Conversation]):
    """对话服务"""

    async def create(self, data: ConversationCreate, user_id: int) -> Conversation:
        """创建对话"""
        try:
            # 添加用户ID到元数据
            metadata = data.metadata or {}
            metadata['user_id'] = user_id

            conversation = Conversation(
                assistant_id=data.assistant_id,
                title=data.title,
                metadata=metadata,
                created_at=datetime.utcnow()
            )

            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            self.logger.info(f"创建对话成功: id={conversation.id}, user_id={user_id}")
            return conversation

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"创建对话失败: {str(e)}")
            raise

    async def get(self, id: int, user_id: Optional[int] = None) -> Optional[Conversation]:
        """获取对话"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == id
        ).first()

        if not conversation:
            return None

        # 检查用户权限
        if user_id and not self._check_user_permission(conversation, user_id):
            raise PermissionError("无权访问该对话")

        return conversation

    async def update(self, id: int, data: ConversationUpdate, user_id: int) -> Optional[Conversation]:
        """更新对话"""
        conversation = await self.get(id, user_id)
        if not conversation:
            return None

        # 更新字段
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conversation, field, value)

        conversation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    async def delete(self, id: int, user_id: int) -> bool:
        """删除对话"""
        conversation = await self.get(id, user_id)
        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()

        return True

    async def list_conversations(
            self,
            user_id: int,
            assistant_id: Optional[int] = None,
            search: Optional[str] = None,
            skip: int = 0,
            limit: int = 20,
            order_by: str = "updated_at",
            order_desc: bool = True
    ) -> List[Conversation]:
        """获取对话列表"""
        query = self.db.query(Conversation)

        # 用户筛选
        query = query.filter(
            Conversation.metadata.op('->>')('user_id') == str(user_id)
        )

        # 助手筛选
        if assistant_id:
            query = query.filter(Conversation.assistant_id == assistant_id)

        # 搜索
        if search:
            query = query.filter(
                Conversation.title.ilike(f"%{search}%")
            )

        # 排序
        order_column = getattr(Conversation, order_by, Conversation.updated_at)
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        # 分页
        conversations = query.offset(skip).limit(limit).all()

        return conversations

    async def get_with_messages(
            self,
            id: int,
            user_id: int,
            message_limit: int = 50
    ) -> Optional[ConversationWithMessages]:
        """获取对话及其消息"""
        conversation = await self.get(id, user_id)
        if not conversation:
            return None

        # 获取消息
        messages = self.db.query(Message).filter(
            Message.conversation_id == id
        ).order_by(Message.created_at.desc()).limit(message_limit).all()

        # 反转消息顺序（从旧到新）
        messages.reverse()

        return ConversationWithMessages(
            **conversation.__dict__,
            messages=messages,
            message_count=len(messages)
        )

    def _check_user_permission(self, conversation: Conversation, user_id: int) -> bool:
        """检查用户权限"""
        if not conversation.metadata:
            return True

        conversation_user_id = conversation.metadata.get('user_id')
        return not conversation_user_id or int(conversation_user_id) == user_id


"""
统一知识库服务层
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import asyncio


class KnowledgeService:
    """统一的知识库服务"""

    def __init__(self, db: Session):
        self.db = db
        self._init_backends()

    def _init_backends(self):
        """初始化不同类型的后端"""
        self.backends = {
            KnowledgeBaseType.TRADITIONAL: TraditionalKBBackend(self.db),
            KnowledgeBaseType.LIGHTRAG: LightRAGBackend(self.db),
            KnowledgeBaseType.HYBRID: HybridKBBackend(self.db)
        }

    async def create_knowledge_base(self, request: KnowledgeBaseCreate, user_id: str) -> Dict:
        """创建知识库"""
        # 选择对应的后端
        backend = self.backends[request.type]

        # 创建知识库
        kb = await backend.create(request, user_id)

        # 记录审计日志
        await self._audit_log("create_kb", user_id, kb.id)

        return kb

    async def query(self, request: QueryRequest) -> List[Dict]:
        """统一查询接口"""
        results = []

        # 并发查询多个知识库
        tasks = []
        for kb_id in request.knowledge_base_ids:
            kb = await self.get_knowledge_base(kb_id)
            if kb:
                backend = self.backends[kb.type]
                tasks.append(backend.query(kb_id, request))

        # 等待所有查询完成
        all_results = await asyncio.gather(*tasks)

        # 合并和重排序结果
        for kb_results in all_results:
            results.extend(kb_results)

        # 根据分数重新排序
        results.sort(key=lambda x: x.get('score', 0), reverse=True)

        # 返回top_k结果
        return results[:request.top_k]

    async def check_read_permission(self, kb_id: str, user_id: str) -> bool:
        """检查读权限"""
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return False

        # 公开读或者是所有者
        return kb.public_read or kb.owner_id == user_id

    async def check_write_permission(self, kb_id: str, user_id: str) -> bool:
        """检查写权限"""
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return False

        # 公开写或者是所有者
        return kb.public_write or kb.owner_id == user_id


"""
记忆服务层
"""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.services.base import BaseService
from app.memory.manager import MemoryManager
from app.memory.interfaces import MemoryConfig, MemoryType
from app.schemas.memory import MemoryCreateRequest, MemoryQueryRequest


class MemoryService(BaseService):
    """记忆服务"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.memory_manager = MemoryManager()

    async def create(self, agent_id: str, config: Optional[MemoryConfig] = None) -> Dict[str, Any]:
        """创建代理记忆"""
        memory = await self.memory_manager.create_agent_memory(
            agent_id=agent_id,
            config=config,
            db=self.db
        )

        return self._format_memory_response(memory)

    async def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取代理记忆"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            return None

        return self._format_memory_response(memory)

    async def query(
            self,
            agent_id: str,
            query: str,
            top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """查询记忆内容"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        memory_items = await memory.query(query, top_k)

        return [
            {
                "key": key,
                "content": value,
                "relevance_score": score
            }
            for key, value, score in memory_items
        ]

    async def add_item(
            self,
            agent_id: str,
            key: str,
            value: Any
    ) -> Dict[str, Any]:
        """添加记忆项"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        await memory.add(key, value)

        return self._format_memory_response(memory)

    async def delete_item(self, agent_id: str, key: str) -> bool:
        """删除记忆项"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        return await memory.delete(key)

    async def clear(self, agent_id: str) -> Dict[str, Any]:
        """清空记忆"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        await memory.clear()

        return self._format_memory_response(memory)

    def _format_memory_response(self, memory) -> Dict[str, Any]:
        """格式化记忆响应"""
        return {
            "memory_id": memory.memory_id,
            "agent_id": memory.agent_id,
            "created_at": memory.created_at,
            "updated_at": memory.last_accessed,
            "config": memory.config.__dict__ if memory.config else None,
            "status": "active"
        }


"""
问答助手服务层：处理问答助手相关的业务逻辑
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.assistant_qa import QAAssistant, Question, DocumentSegment
from app.core.assistant_qa_manager import AssistantQAManager
from app.core.exceptions import NotFoundError, PermissionError, ValidationError

logger = logging.getLogger(__name__)


class QAService:
    """问答助手服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.qa_manager = AssistantQAManager(db)

    # ==================== 助手管理 ====================

    async def create_qa_assistant(self, data: Dict[str, Any], user_id: int) -> QAAssistant:
        """创建问答助手"""
        try:
            # 添加创建者信息
            data['owner_id'] = user_id
            data['created_by'] = user_id

            assistant = self.qa_manager.create_assistant(data)
            logger.info(f"Created QA assistant: {assistant.id} for user: {user_id}")
            return assistant

        except Exception as e:
            logger.error(f"Failed to create QA assistant: {str(e)}")
            raise ValidationError(f"创建问答助手失败: {str(e)}")

    async def get_qa_assistant(self, assistant_id: int, user_id: Optional[int] = None) -> QAAssistant:
        """获取问答助手详情"""
        assistant = self.qa_manager.get_assistant(assistant_id)

        if not assistant:
            raise NotFoundError("问答助手不存在")

        # 权限检查
        if user_id and hasattr(assistant, 'owner_id'):
            if assistant.owner_id != user_id and not getattr(assistant, 'is_public', False):
                raise PermissionError("无权访问该问答助手")

        return assistant

    async def get_qa_assistants(
            self,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[int] = None,
            status: Optional[str] = None
    ) -> Tuple[List[QAAssistant], int]:
        """获取问答助手列表"""
        assistants, total = await self.qa_manager.get_assistants(skip, limit)

        # 过滤用户可访问的助手
        if user_id:
            filtered = []
            for assistant in assistants:
                owner_id = getattr(assistant, 'owner_id', None)
                is_public = getattr(assistant, 'is_public', False)

                if owner_id == user_id or is_public:
                    filtered.append(assistant)

            assistants = filtered
            total = len(filtered)

        # 状态过滤
        if status:
            assistants = [a for a in assistants if a.status == status]
            total = len(assistants)

        return assistants, total

    async def update_qa_assistant(
            self,
            assistant_id: int,
            data: Dict[str, Any],
            user_id: int
    ) -> QAAssistant:
        """更新问答助手"""
        assistant = await self.get_qa_assistant(assistant_id)

        # 权限检查
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以更新问答助手")

        try:
            updated = self.qa_manager.update_assistant(assistant_id, data)
            logger.info(f"Updated QA assistant: {assistant_id}")
            return updated

        except Exception as e:
            logger.error(f"Failed to update QA assistant: {str(e)}")
            raise ValidationError(f"更新问答助手失败: {str(e)}")

    async def delete_qa_assistant(self, assistant_id: int, user_id: int) -> bool:
        """删除问答助手"""
        assistant = await self.get_qa_assistant(assistant_id)

        # 权限检查
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以删除问答助手")

        success = self.qa_manager.delete_assistant(assistant_id)
        if success:
            logger.info(f"Deleted QA assistant: {assistant_id}")
        return success

    # ==================== 问题管理 ====================

    async def create_question(self, data: Dict[str, Any], user_id: int) -> Question:
        """创建问题"""
        # 验证助手存在和权限
        assistant = await self.get_qa_assistant(data['assistant_id'], user_id)

        try:
            data['created_by'] = user_id
            question = await self.qa_manager.create_question(data)
            logger.info(f"Created question: {question.id}")
            return question

        except Exception as e:
            logger.error(f"Failed to create question: {str(e)}")
            raise ValidationError(f"创建问题失败: {str(e)}")

    async def get_question(
            self,
            question_id: int,
            include_document_segments: bool = True,
            user_id: Optional[int] = None
    ) -> Question:
        """获取问题详情"""
        question = self.qa_manager.get_question(question_id, include_document_segments)

        if not question:
            raise NotFoundError("问题不存在")

        # 验证访问权限
        if user_id:
            assistant = await self.get_qa_assistant(question.assistant_id, user_id)

        return question

    async def get_questions(
            self,
            assistant_id: int,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[int] = None
    ) -> Tuple[List[Question], int]:
        """获取问题列表"""
        # 验证助手访问权限
        if user_id:
            assistant = await self.get_qa_assistant(assistant_id, user_id)

        questions, total = await self.qa_manager.get_questions(assistant_id, skip, limit)
        return questions, total

    async def update_question(
            self,
            question_id: int,
            data: Dict[str, Any],
            user_id: int
    ) -> Question:
        """更新问题"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以更新问题")

        try:
            updated = await self.qa_manager.update_question(question_id, data)
            logger.info(f"Updated question: {question_id}")
            return updated

        except Exception as e:
            logger.error(f"Failed to update question: {str(e)}")
            raise ValidationError(f"更新问题失败: {str(e)}")

    async def delete_question(self, question_id: int, user_id: int) -> bool:
        """删除问题"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以删除问题")

        success = self.qa_manager.delete_question(question_id)
        if success:
            logger.info(f"Deleted question: {question_id}")
        return success

    # ==================== 问答功能 ====================

    async def answer_question(self, question_id: int, user_id: Optional[int] = None) -> str:
        """回答问题"""
        # 验证问题存在和权限
        question = await self.get_question(question_id, user_id=user_id)

        # 增加浏览次数
        question.views_count = (question.views_count or 0) + 1
        self.db.commit()

        # 生成答案
        answer = await self.qa_manager.answer_question(question_id)

        # 记录回答历史
        await self._record_answer_history(question_id, answer, user_id)

        return answer

    async def _record_answer_history(
            self,
            question_id: int,
            answer: str,
            user_id: Optional[int]
    ):
        """记录回答历史"""
        try:
            # TODO: 实现回答历史记录
            pass
        except Exception as e:
            logger.error(f"记录回答历史失败: {str(e)}")

    # ==================== 设置管理 ====================

    async def update_answer_settings(
            self,
            question_id: int,
            answer_mode: Optional[str],
            use_cache: Optional[bool],
            user_id: int
    ) -> Question:
        """更新问题回答设置"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以更新设置")

        updated = await self.qa_manager.update_answer_settings(
            question_id, answer_mode, use_cache
        )
        return updated

    async def update_document_segment_settings(
            self,
            question_id: int,
            segment_ids: List[int],
            user_id: int
    ) -> Question:
        """更新问题文档分段设置"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以更新设置")

        updated = await self.qa_manager.update_document_segment_settings(
            question_id, segment_ids
        )
        return updated

    # ==================== 统计功能 ====================

    async def get_assistant_statistics(self, assistant_id: int) -> Dict[str, Any]:
        """获取助手统计信息"""
        assistant = await self.get_qa_assistant(assistant_id)

        # 问题统计
        questions = self.db.query(Question).filter(
            Question.assistant_id == assistant_id
        ).all()

        total_questions = len(questions)
        total_views = sum(q.views_count or 0 for q in questions)

        # 按类别统计
        categories = {}
        for q in questions:
            cat = q.category or "未分类"
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        return {
            "total_questions": total_questions,
            "total_views": total_views,
            "categories": categories,
            "average_views": total_views / total_questions if total_questions > 0 else 0
        }


"""
统一响应格式
"""

from app.schemas.knowledge_base import BaseResponse
from datetime import datetime

def success_response(data=None, message="操作成功") -> BaseResponse:
    """成功响应"""
    return BaseResponse(
        success=True,
        message=message,
        data=data,
        error=None,
        timestamp=datetime.now()
    )

def error_response(error: str, message="操作失败") -> BaseResponse:
    """错误响应"""
    return BaseResponse(
        success=False,
        message=message,
        data=None,
        error=error,
        timestamp=datetime.now()
    )