"""
助手API路由
提供统一的助手管理接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
from datetime import datetime

from app.models.database import get_db
from app.models.assistants import Assistant, AssistantTool, AssistantKnowledgeBase
from app.models.knowledge import KnowledgeBase
from app.schemas.assistants import (
    Assistant as AssistantSchema,
    AssistantCreate,
    AssistantUpdate,
    AssistantWithDetails,
    AssistantToolCreate,
    AssistantKnowledgeBaseCreate
)
from app.api.v1.dependencies import (
    get_agent_adapter, ResponseFormatter, get_request_context
)
from app.messaging.adapters.agent import AgentAdapter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[AssistantSchema])
async def get_assistants(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有助手，支持过滤和搜索
    """
    query = db.query(Assistant)
    
    if is_active is not None:
        query = query.filter(Assistant.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Assistant.name.ilike(search_term) | 
            Assistant.description.ilike(search_term)
        )
    
    assistants = query.order_by(Assistant.created_at.desc()).offset(skip).limit(limit).all()
    return ResponseFormatter.format_success(assistants)


@router.post("/", response_model=AssistantSchema)
async def create_assistant(
    assistant: AssistantCreate,
    db: Session = Depends(get_db)
):
    """
    创建新助手
    """
    # 创建助手记录
    db_assistant = Assistant(
        name=assistant.name,
        description=assistant.description,
        model=assistant.model,
        system_prompt=assistant.system_prompt,
        temperature=assistant.temperature,
        is_active=assistant.is_active,
        config=assistant.config or {},
        metadata=assistant.metadata or {}
    )
    
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    
    # 处理知识库关联
    if assistant.knowledge_base_ids:
        for kb_id in assistant.knowledge_base_ids:
            # 检查知识库是否存在
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                logger.warning(f"知识库ID {kb_id} 不存在，已跳过关联")
                continue
            
            # 创建关联
            kb_association = AssistantKnowledgeBase(
                assistant_id=db_assistant.id,
                knowledge_base_id=kb_id
            )
            db.add(kb_association)
        
        db.commit()
    
    # 处理工具关联
    if assistant.tools:
        for tool_data in assistant.tools:
            # 创建工具关联
            tool = AssistantTool(
                assistant_id=db_assistant.id,
                name=tool_data.name,
                description=tool_data.description,
                type=tool_data.type,
                config=tool_data.config or {}
            )
            db.add(tool)
        
        db.commit()
    
    return ResponseFormatter.format_success(db_assistant)


@router.get("/{assistant_id}", response_model=AssistantWithDetails)
async def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取助手详情
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="助手不存在")
    
    # 获取关联的工具
    tools = db.query(AssistantTool).filter(AssistantTool.assistant_id == assistant_id).all()
    
    # 获取关联的知识库
    kb_associations = db.query(AssistantKnowledgeBase).filter(
        AssistantKnowledgeBase.assistant_id == assistant_id
    ).all()
    
    kb_ids = [assoc.knowledge_base_id for assoc in kb_associations]
    knowledge_bases = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(kb_ids)).all() if kb_ids else []
    
    # 构建响应
    assistant_dict = assistant.__dict__.copy()
    if "_sa_instance_state" in assistant_dict:
        del assistant_dict["_sa_instance_state"]
    
    assistant_dict["tools"] = tools
    assistant_dict["knowledge_bases"] = knowledge_bases
    
    return ResponseFormatter.format_success(assistant_dict)


@router.put("/{assistant_id}", response_model=AssistantSchema)
async def update_assistant(
    assistant_id: int,
    assistant_update: AssistantUpdate,
    db: Session = Depends(get_db)
):
    """
    更新助手信息
    """
    db_assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="助手不存在")
    
    # 更新基本信息
    if assistant_update.name is not None:
        db_assistant.name = assistant_update.name
    
    if assistant_update.description is not None:
        db_assistant.description = assistant_update.description
    
    if assistant_update.model is not None:
        db_assistant.model = assistant_update.model
    
    if assistant_update.system_prompt is not None:
        db_assistant.system_prompt = assistant_update.system_prompt
    
    if assistant_update.temperature is not None:
        db_assistant.temperature = assistant_update.temperature
    
    if assistant_update.is_active is not None:
        db_assistant.is_active = assistant_update.is_active
    
    if assistant_update.config is not None:
        db_assistant.config = assistant_update.config
    
    if assistant_update.metadata is not None:
        # 合并元数据，保留现有字段
        db_assistant.metadata.update(assistant_update.metadata)
    
    db_assistant.updated_at = datetime.now()
    db.commit()
    
    # 处理知识库关联更新
    if assistant_update.knowledge_base_ids is not None:
        # 删除现有关联
        db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id
        ).delete()
        
        # 创建新关联
        for kb_id in assistant_update.knowledge_base_ids:
            kb_association = AssistantKnowledgeBase(
                assistant_id=assistant_id,
                knowledge_base_id=kb_id
            )
            db.add(kb_association)
        
        db.commit()
    
    # 处理工具关联更新
    if assistant_update.tools is not None:
        # 删除现有工具
        db.query(AssistantTool).filter(
            AssistantTool.assistant_id == assistant_id
        ).delete()
        
        # 创建新工具
        for tool_data in assistant_update.tools:
            tool = AssistantTool(
                assistant_id=assistant_id,
                name=tool_data.name,
                description=tool_data.description,
                type=tool_data.type,
                config=tool_data.config or {}
            )
            db.add(tool)
        
        db.commit()
    
    db.refresh(db_assistant)
    return ResponseFormatter.format_success(db_assistant)


@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除或停用助手
    """
    db_assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="助手不存在")
    
    if permanent:
        # 删除关联的工具
        db.query(AssistantTool).filter(
            AssistantTool.assistant_id == assistant_id
        ).delete()
        
        # 删除知识库关联
        db.query(AssistantKnowledgeBase).filter(
            AssistantKnowledgeBase.assistant_id == assistant_id
        ).delete()
        
        # 删除助手
        db.delete(db_assistant)
    else:
        # 仅停用助手
        db_assistant.is_active = False
        db_assistant.updated_at = datetime.now()
    
    db.commit()
    
    return ResponseFormatter.format_success(None, message=f"助手已{'删除' if permanent else '停用'}")


@router.post("/{assistant_id}/tools", response_model=Dict[str, Any])
async def add_assistant_tool(
    assistant_id: int,
    tool: AssistantToolCreate,
    db: Session = Depends(get_db)
):
    """
    为助手添加工具
    """
    # 检查助手是否存在
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="助手不存在")
    
    # 创建工具关联
    db_tool = AssistantTool(
        assistant_id=assistant_id,
        name=tool.name,
        description=tool.description,
        type=tool.type,
        config=tool.config or {}
    )
    
    db.add(db_tool)
    db.commit()
    db.refresh(db_tool)
    
    return ResponseFormatter.format_success(db_tool)


@router.delete("/{assistant_id}/tools/{tool_id}")
async def delete_assistant_tool(
    assistant_id: int,
    tool_id: int,
    db: Session = Depends(get_db)
):
    """
    删除助手的工具
    """
    # 检查工具是否存在
    tool = db.query(AssistantTool).filter(
        AssistantTool.assistant_id == assistant_id,
        AssistantTool.id == tool_id
    ).first()
    
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工具不存在")
    
    db.delete(tool)
    db.commit()
    
    return ResponseFormatter.format_success(None, message="工具已删除")


@router.post("/{assistant_id}/knowledge-bases")
async def add_assistant_knowledge_base(
    assistant_id: int,
    kb_association: AssistantKnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """
    关联助手和知识库
    """
    # 检查助手是否存在
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="助手不存在")
    
    # 检查知识库是否存在
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_association.knowledge_base_id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    
    # 检查关联是否已存在
    existing = db.query(AssistantKnowledgeBase).filter(
        AssistantKnowledgeBase.assistant_id == assistant_id,
        AssistantKnowledgeBase.knowledge_base_id == kb_association.knowledge_base_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="关联已存在")
    
    # 创建关联
    db_association = AssistantKnowledgeBase(
        assistant_id=assistant_id,
        knowledge_base_id=kb_association.knowledge_base_id
    )
    
    db.add(db_association)
    db.commit()
    db.refresh(db_association)
    
    return ResponseFormatter.format_success(db_association)


@router.delete("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
async def delete_assistant_knowledge_base(
    assistant_id: int,
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    删除助手与知识库的关联
    """
    # 检查关联是否存在
    association = db.query(AssistantKnowledgeBase).filter(
        AssistantKnowledgeBase.assistant_id == assistant_id,
        AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
    ).first()
    
    if not association:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关联不存在")
    
    db.delete(association)
    db.commit()
    
    return ResponseFormatter.format_success(None, message="知识库关联已删除")
