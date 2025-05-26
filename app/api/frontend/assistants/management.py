"""
Frontend API - 助手管理接口
基于原有assistant.py、assistants.py、assistant_qa.py完整迁移，适配前端应用需求
"""

from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime

from app.api.frontend.dependencies import (
    FrontendServiceContainer,
    FrontendContext,
    get_frontend_service_container,
    get_frontend_context
)
from app.api.shared.responses import InternalResponseFormatter
from app.api.shared.validators import ValidatorFactory

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 请求/响应模型（基于原有模型扩展）
# ================================

from pydantic import BaseModel, Field

class AssistantCreateRequest(BaseModel):
    """助手创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="助手名称")
    description: Optional[str] = Field(None, max_length=500, description="助手描述")
    model: str = Field(..., description="使用的模型")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    capabilities: List[str] = Field(default=[], description="助手能力")
    knowledge_base_ids: List[int] = Field(default=[], description="关联的知识库ID")
    is_public: bool = Field(False, description="是否公开")
    category: Optional[str] = Field(None, description="助手分类")
    tags: List[str] = Field(default=[], description="标签")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置信息")


class AssistantUpdateRequest(BaseModel):
    """助手更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[List[str]] = None
    knowledge_base_ids: Optional[List[int]] = None
    is_public: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    avatar_url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AssistantTestRequest(BaseModel):
    """助手测试请求"""
    message: str = Field(..., min_length=1, description="测试消息")
    include_knowledge: bool = Field(True, description="是否包含知识库")
    max_tokens: Optional[int] = Field(None, description="最大生成tokens")


# ================================
# 助手管理接口
# ================================

@router.get("/assistants", response_model=Dict[str, Any], summary="获取助手列表")
async def list_assistants(
    category: Optional[str] = Query(None, description="分类筛选"),
    capabilities: Optional[List[str]] = Query(None, description="能力筛选"),
    is_public: Optional[bool] = Query(None, description="公开性筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[List[str]] = Query(None, description="标签筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户可访问的助手列表
    
    支持多种筛选条件和搜索
    """
    try:
        logger.info(f"Frontend API - 获取助手列表: user_id={context.user.id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 获取助手列表（基于原有功能）
        assistants = await assistant_service.get_assistants(
            skip=offset,
            limit=limit,
            capabilities=capabilities,
            user_id=context.user.id  # 添加用户筛选
        )
        
        # 应用筛选条件
        filtered_assistants = []
        for assistant in assistants:
            # 分类筛选
            if category and getattr(assistant, 'category', None) != category:
                continue
            
            # 公开性筛选（用户可以看到自己的所有助手 + 公开助手）
            if is_public is not None:
                assistant_is_public = getattr(assistant, 'is_public', False)
                if assistant_is_public != is_public:
                    continue
            
            # 搜索筛选
            if search and search.lower() not in assistant.name.lower():
                if not assistant.description or search.lower() not in assistant.description.lower():
                    continue
            
            # 标签筛选
            if tags:
                assistant_tags = getattr(assistant, 'tags', [])
                if not any(tag in assistant_tags for tag in tags):
                    continue
            
            filtered_assistants.append(assistant)
        
        # 构建响应数据
        response_data = {
            "assistants": [
                {
                    "id": assistant.id,
                    "name": assistant.name,
                    "description": assistant.description,
                    "model": assistant.model,
                    "category": getattr(assistant, 'category', None),
                    "capabilities": getattr(assistant, 'capabilities', []),
                    "tags": getattr(assistant, 'tags', []),
                    "is_public": getattr(assistant, 'is_public', False),
                    "avatar_url": getattr(assistant, 'avatar_url', None),
                    "created_at": assistant.created_at.isoformat() if assistant.created_at else None,
                    "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None,
                    "usage_count": getattr(assistant, 'usage_count', 0),
                    "rating": getattr(assistant, 'rating', 0),
                    "owner_id": getattr(assistant, 'owner_id', None),
                    "is_owner": getattr(assistant, 'owner_id', None) == context.user.id
                }
                for assistant in filtered_assistants
            ],
            "total": len(filtered_assistants),
            "limit": limit,
            "offset": offset,
            "filters": {
                "category": category,
                "capabilities": capabilities,
                "is_public": is_public,
                "search": search,
                "tags": tags
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取助手列表成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取助手列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手列表失败"
        )


@router.post("/assistants", response_model=Dict[str, Any], summary="创建助手")
async def create_assistant(
    request: AssistantCreateRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    创建新的AI助手
    
    支持关联知识库和自定义配置
    """
    try:
        logger.info(f"Frontend API - 创建助手: user_id={context.user.id}, name={request.name}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 验证知识库是否存在（如果指定了）
        if request.knowledge_base_ids:
            knowledge_service = container.get_knowledge_service()
            for kb_id in request.knowledge_base_ids:
                kb = await knowledge_service.get_knowledge_base_by_id(kb_id)
                if not kb:
                    raise HTTPException(
                        status_code=404,
                        detail=f"知识库 {kb_id} 不存在"
                    )
                
                # 验证用户是否有权限使用该知识库
                owner_id = getattr(kb, 'owner_id', None)
                is_public = getattr(kb, 'is_public', False)
                
                if not is_public and owner_id != context.user.id:
                    raise HTTPException(
                        status_code=403,
                        detail=f"无权使用知识库 {kb_id}"
                    )
        
        # 构建助手创建数据（基于原有模型）
        assistant_data = {
            "name": request.name,
            "description": request.description,
            "model": request.model,
            "system_prompt": request.system_prompt,
            "capabilities": request.capabilities,
            "is_public": request.is_public,
            "category": request.category,
            "tags": request.tags,
            "avatar_url": request.avatar_url,
            "config": request.config,
            "owner_id": context.user.id,  # 设置所有者
            "metadata": {
                "created_via": "frontend_api",
                "user_id": context.user.id,
                "knowledge_base_ids": request.knowledge_base_ids
            }
        }
        
        # 创建助手（基于原有功能）
        assistant = await assistant_service.create_assistant(assistant_data)
        
        # 关联知识库（如果指定）
        if request.knowledge_base_ids:
            for kb_id in request.knowledge_base_ids:
                await assistant_service.add_knowledge_base(assistant.id, kb_id)
        
        # 构建响应数据
        response_data = {
            "id": assistant.id,
            "name": assistant.name,
            "description": assistant.description,
            "model": assistant.model,
            "capabilities": getattr(assistant, 'capabilities', []),
            "is_public": getattr(assistant, 'is_public', False),
            "category": getattr(assistant, 'category', None),
            "tags": getattr(assistant, 'tags', []),
            "avatar_url": getattr(assistant, 'avatar_url', None),
            "created_at": assistant.created_at.isoformat() if assistant.created_at else None,
            "config": getattr(assistant, 'config', {}),
            "knowledge_base_ids": request.knowledge_base_ids,
            "status": "created"
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="助手创建成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 创建助手失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="助手创建失败"
        )


@router.get("/assistants/{assistant_id}", response_model=Dict[str, Any], summary="获取助手详情")
async def get_assistant(
    assistant_id: int = Path(..., description="助手ID"),
    include_config: bool = Query(False, description="包含配置信息"),
    include_knowledge_bases: bool = Query(False, description="包含关联知识库"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取助手详细信息
    
    包含基本信息、配置和关联的知识库
    """
    try:
        logger.info(f"Frontend API - 获取助手详情: user_id={context.user.id}, assistant_id={assistant_id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 获取助手详情（基于原有功能）
        assistant = await assistant_service.get_assistant_by_id(assistant_id)
        if not assistant:
            raise HTTPException(
                status_code=404,
                detail="助手不存在"
            )
        
        # 验证访问权限（用户可以访问自己的助手或公开助手）
        owner_id = getattr(assistant, 'owner_id', None)
        is_public = getattr(assistant, 'is_public', False)
        
        if not is_public and owner_id != context.user.id:
            raise HTTPException(
                status_code=403,
                detail="无权访问该助手"
            )
        
        # 构建响应数据
        response_data = {
            "id": assistant.id,
            "name": assistant.name,
            "description": assistant.description,
            "model": assistant.model,
            "capabilities": getattr(assistant, 'capabilities', []),
            "is_public": getattr(assistant, 'is_public', False),
            "category": getattr(assistant, 'category', None),
            "tags": getattr(assistant, 'tags', []),
            "avatar_url": getattr(assistant, 'avatar_url', None),
            "created_at": assistant.created_at.isoformat() if assistant.created_at else None,
            "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None,
            "usage_count": getattr(assistant, 'usage_count', 0),
            "rating": getattr(assistant, 'rating', 0),
            "owner_id": owner_id,
            "is_owner": owner_id == context.user.id
        }
        
        # 添加配置信息（如果需要且有权限）
        if include_config and owner_id == context.user.id:
            response_data["config"] = getattr(assistant, 'config', {})
            response_data["system_prompt"] = getattr(assistant, 'system_prompt', None)
        
        # 添加关联知识库信息（如果需要）
        if include_knowledge_bases:
            # 获取关联的知识库
            knowledge_bases = []
            metadata = getattr(assistant, 'metadata', {})
            kb_ids = metadata.get('knowledge_base_ids', [])
            
            if kb_ids:
                knowledge_service = container.get_knowledge_service()
                for kb_id in kb_ids:
                    kb = await knowledge_service.get_knowledge_base_by_id(kb_id)
                    if kb:
                        knowledge_bases.append({
                            "id": kb.id,
                            "name": kb.name,
                            "description": kb.description,
                            "is_public": getattr(kb, 'is_public', False)
                        })
            
            response_data["knowledge_bases"] = knowledge_bases
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取助手详情成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 获取助手详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手详情失败"
        )


@router.put("/assistants/{assistant_id}", response_model=Dict[str, Any], summary="更新助手")
async def update_assistant(
    assistant_id: int = Path(..., description="助手ID"),
    request: AssistantUpdateRequest = None,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新助手信息
    
    只有所有者可以更新
    """
    try:
        logger.info(f"Frontend API - 更新助手: user_id={context.user.id}, assistant_id={assistant_id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 验证助手是否存在和权限
        assistant = await assistant_service.get_assistant_by_id(assistant_id)
        if not assistant:
            raise HTTPException(
                status_code=404,
                detail="助手不存在"
            )
        
        # 验证所有者权限
        owner_id = getattr(assistant, 'owner_id', None)
        if owner_id != context.user.id:
            raise HTTPException(
                status_code=403,
                detail="只有所有者可以更新助手"
            )
        
        # 构建更新数据
        update_data = {}
        for field, value in request.model_dump(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供更新内容"
            )
        
        # 如果更新了知识库，验证权限
        if 'knowledge_base_ids' in update_data:
            knowledge_service = container.get_knowledge_service()
            for kb_id in update_data['knowledge_base_ids']:
                kb = await knowledge_service.get_knowledge_base_by_id(kb_id)
                if not kb:
                    raise HTTPException(
                        status_code=404,
                        detail=f"知识库 {kb_id} 不存在"
                    )
                
                # 验证权限
                kb_owner_id = getattr(kb, 'owner_id', None)
                is_public = getattr(kb, 'is_public', False)
                
                if not is_public and kb_owner_id != context.user.id:
                    raise HTTPException(
                        status_code=403,
                        detail=f"无权使用知识库 {kb_id}"
                    )
        
        # 更新助手（基于原有功能）
        updated_assistant = await assistant_service.update_assistant(assistant_id, update_data)
        
        # 更新知识库关联（如果需要）
        if 'knowledge_base_ids' in update_data:
            # 清除现有关联
            await assistant_service.clear_knowledge_bases(assistant_id)
            
            # 添加新关联
            for kb_id in update_data['knowledge_base_ids']:
                await assistant_service.add_knowledge_base(assistant_id, kb_id)
        
        # 构建响应数据
        response_data = {
            "id": updated_assistant.id,
            "name": updated_assistant.name,
            "description": updated_assistant.description,
            "model": updated_assistant.model,
            "capabilities": getattr(updated_assistant, 'capabilities', []),
            "is_public": getattr(updated_assistant, 'is_public', False),
            "category": getattr(updated_assistant, 'category', None),
            "tags": getattr(updated_assistant, 'tags', []),
            "updated_at": updated_assistant.updated_at.isoformat() if updated_assistant.updated_at else None
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="助手更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新助手失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="助手更新失败"
        )


@router.delete("/assistants/{assistant_id}", response_model=Dict[str, Any], summary="删除助手")
async def delete_assistant(
    assistant_id: int = Path(..., description="助手ID"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    删除助手
    
    只有所有者可以删除，将永久删除助手及其配置
    """
    try:
        logger.info(f"Frontend API - 删除助手: user_id={context.user.id}, assistant_id={assistant_id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 验证助手是否存在和权限
        assistant = await assistant_service.get_assistant_by_id(assistant_id)
        if not assistant:
            raise HTTPException(
                status_code=404,
                detail="助手不存在"
            )
        
        # 验证所有者权限
        owner_id = getattr(assistant, 'owner_id', None)
        if owner_id != context.user.id:
            raise HTTPException(
                status_code=403,
                detail="只有所有者可以删除助手"
            )
        
        # 删除助手（基于原有功能）
        success = await assistant_service.delete_assistant(assistant_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="助手删除失败"
            )
        
        return InternalResponseFormatter.format_success(
            data={"assistant_id": assistant_id},
            message="助手删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 删除助手失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="助手删除失败"
        )


# ================================
# 助手测试和交互功能（基于原有assistant_qa.py迁移）
# ================================

@router.post("/assistants/{assistant_id}/test", response_model=Dict[str, Any], summary="测试助手")
async def test_assistant(
    assistant_id: int = Path(..., description="助手ID"),
    request: AssistantTestRequest = None,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    测试助手功能
    
    发送测试消息并获取响应，用于验证助手效果
    """
    try:
        logger.info(f"Frontend API - 测试助手: user_id={context.user.id}, assistant_id={assistant_id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 验证助手是否存在和权限
        assistant = await assistant_service.get_assistant_by_id(assistant_id)
        if not assistant:
            raise HTTPException(
                status_code=404,
                detail="助手不存在"
            )
        
        # 验证访问权限
        owner_id = getattr(assistant, 'owner_id', None)
        is_public = getattr(assistant, 'is_public', False)
        
        if not is_public and owner_id != context.user.id:
            raise HTTPException(
                status_code=403,
                detail="无权测试该助手"
            )
        
        # 获取聊天服务进行测试
        chat_service = container.get_chat_service()
        
        # 创建临时对话用于测试
        from app.schemas.chat import ConversationCreate, ChatRequest
        
        test_conversation_data = ConversationCreate(
            assistant_id=assistant_id,
            title=f"测试对话 - {assistant.name}",
            metadata={
                "user_id": context.user.id,
                "is_test": True,
                "created_via": "frontend_api_test"
            }
        )
        
        test_conversation = await chat_service.create_conversation(test_conversation_data)
        
        # 构建测试聊天请求
        test_chat_request = ChatRequest(
            assistant_id=assistant_id,
            conversation_id=test_conversation.id,
            message=request.message,
            user_id=context.user.id,
            stream=False,
            metadata={
                "include_knowledge": request.include_knowledge,
                "max_tokens": request.max_tokens,
                "is_test": True
            }
        )
        
        # 执行测试聊天
        response = await chat_service.process_chat(test_chat_request, None)
        
        # 构建测试结果
        test_result = {
            "assistant_id": assistant_id,
            "test_message": request.message,
            "response": response.response if hasattr(response, 'response') else str(response),
            "test_time": datetime.now().isoformat(),
            "metadata": {
                "tokens_used": getattr(response, 'tokens_used', 0),
                "processing_time": getattr(response, 'processing_time', 0),
                "model": assistant.model,
                "include_knowledge": request.include_knowledge,
                "conversation_id": test_conversation.id
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=test_result,
            message="助手测试完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 测试助手失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="助手测试失败"
        )


@router.get("/assistants/categories", response_model=Dict[str, Any], summary="获取助手分类")
async def get_assistant_categories(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取所有助手分类及统计信息
    """
    try:
        logger.info(f"Frontend API - 获取助手分类: user_id={context.user.id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 获取用户可访问的所有助手
        all_assistants = await assistant_service.get_assistants(
            skip=0,
            limit=1000,  # 获取大量数据进行统计
            user_id=context.user.id
        )
        
        # 统计分类信息
        categories = {}
        for assistant in all_assistants:
            category = getattr(assistant, 'category', None) or "未分类"
            
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
            
            is_public = getattr(assistant, 'is_public', False)
            if is_public:
                categories[category]["public_count"] += 1
            else:
                categories[category]["private_count"] += 1
            
            categories[category]["models"].add(assistant.model)
            
            capabilities = getattr(assistant, 'capabilities', [])
            for cap in capabilities:
                categories[category]["capabilities"].add(cap)
        
        # 转换集合为列表
        for category_data in categories.values():
            category_data["models"] = list(category_data["models"])
            category_data["capabilities"] = list(category_data["capabilities"])
        
        response_data = {
            "categories": list(categories.values()),
            "total_categories": len(categories),
            "total_assistants": len(all_assistants)
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取助手分类成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取助手分类失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手分类失败"
        ) 