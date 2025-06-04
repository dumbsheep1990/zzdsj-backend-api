"""
Frontend API - 通知管理接口
提供实时通知、消息推送和设置管理功能
"""

from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
import json
import asyncio

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
# 请求/响应模型
# ================================

from pydantic import BaseModel, Field, validator

class NotificationCreateRequest(BaseModel):
    """通知创建请求"""
    title: str = Field(..., min_length=1, max_length=100, description="通知标题")
    content: str = Field(..., min_length=1, max_length=1000, description="通知内容")
    type: str = Field(..., description="通知类型：info, success, warning, error, system")
    priority: str = Field(default="normal", description="优先级：low, normal, high, urgent")
    category: str = Field(default="general", description="分类：general, system, chat, knowledge, assistant")
    action_url: Optional[str] = Field(None, description="点击跳转链接")
    action_data: Optional[Dict[str, Any]] = Field(None, description="操作数据")
    scheduled_time: Optional[str] = Field(None, description="定时发送时间")
    expires_at: Optional[str] = Field(None, description="过期时间")


class NotificationUpdateRequest(BaseModel):
    """通知更新请求"""
    is_read: Optional[bool] = Field(None, description="是否已读")
    is_archived: Optional[bool] = Field(None, description="是否归档")
    is_starred: Optional[bool] = Field(None, description="是否加星标")


class NotificationSettingsRequest(BaseModel):
    """通知设置请求"""
    enable_push: Optional[bool] = Field(None, description="启用推送通知")
    enable_email: Optional[bool] = Field(None, description="启用邮件通知")
    enable_in_app: Optional[bool] = Field(None, description="启用应用内通知")
    enable_desktop: Optional[bool] = Field(None, description="启用桌面通知")
    quiet_hours_start: Optional[str] = Field(None, description="免打扰开始时间")
    quiet_hours_end: Optional[str] = Field(None, description="免打扰结束时间")
    category_settings: Optional[Dict[str, Dict[str, bool]]] = Field(None, description="分类设置")


class BulkNotificationRequest(BaseModel):
    """批量通知请求"""
    notification_ids: List[int] = Field(..., min_items=1, description="通知ID列表")
    action: str = Field(..., description="操作：mark_read, mark_unread, archive, delete, star")


# ================================
# 通知管理接口
# ================================

@router.get("/notifications", response_model=Dict[str, Any], summary="获取通知列表")
async def list_notifications(
    category: Optional[str] = Query(None, description="分类筛选"),
    type: Optional[str] = Query(None, description="类型筛选"),
    is_read: Optional[bool] = Query(None, description="已读状态筛选"),
    is_starred: Optional[bool] = Query(None, description="星标筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户通知列表
    
    支持多种筛选条件和分页
    """
    try:
        logger.info(f"Frontend API - 获取通知列表: user_id={context.user.id}")
        
        # 模拟通知数据
        notifications = [
            {
                "id": 1,
                "title": "新对话消息",
                "content": "AI助手'技术顾问'在对话中回复了您的问题",
                "type": "info",
                "priority": "normal",
                "category": "chat",
                "is_read": False,
                "is_starred": False,
                "is_archived": False,
                "created_at": datetime.now() - timedelta(minutes=30),
                "action_url": "/chat/conversations/123",
                "action_data": {"conversation_id": 123, "assistant_name": "技术顾问"},
                "metadata": {
                    "source": "chat_service",
                    "assistant_id": 5
                }
            },
            {
                "id": 2,
                "title": "文档处理完成",
                "content": "您上传的文档'API设计规范.pdf'已成功处理并添加到知识库",
                "type": "success",
                "priority": "normal",
                "category": "knowledge",
                "is_read": True,
                "is_starred": True,
                "is_archived": False,
                "created_at": datetime.now() - timedelta(hours=2),
                "action_url": "/knowledge/bases/1/documents",
                "action_data": {"knowledge_base_id": 1, "document_name": "API设计规范.pdf"},
                "metadata": {
                    "source": "document_service",
                    "processing_time": 45.2
                }
            },
            {
                "id": 3,
                "title": "系统维护通知",
                "content": "系统将于今晚22:00-23:00进行维护升级，期间服务可能暂时不可用",
                "type": "warning",
                "priority": "high",
                "category": "system",
                "is_read": False,
                "is_starred": False,
                "is_archived": False,
                "created_at": datetime.now() - timedelta(hours=6),
                "action_url": None,
                "action_data": {"maintenance_window": "22:00-23:00"},
                "metadata": {
                    "source": "system_admin",
                    "scheduled_time": "2024-01-01T22:00:00Z"
                }
            },
            {
                "id": 4,
                "title": "新功能发布",
                "content": "语音聊天功能已上线，您现在可以与AI助手进行语音对话了！",
                "type": "info",
                "priority": "normal",
                "category": "general",
                "is_read": True,
                "is_starred": False,
                "is_archived": False,
                "created_at": datetime.now() - timedelta(days=1),
                "action_url": "/features/voice-chat",
                "action_data": {"feature": "voice_chat"},
                "metadata": {
                    "source": "product_team",
                    "version": "v1.2.0"
                }
            },
            {
                "id": 5,
                "title": "助手训练完成",
                "content": "您的自定义助手'数据分析专家'训练完成，现在可以使用了",
                "type": "success",
                "priority": "normal",
                "category": "assistant",
                "is_read": False,
                "is_starred": True,
                "is_archived": False,
                "created_at": datetime.now() - timedelta(days=2),
                "action_url": "/assistants/7",
                "action_data": {"assistant_id": 7, "assistant_name": "数据分析专家"},
                "metadata": {
                    "source": "training_service",
                    "training_duration": "2h 15m"
                }
            }
        ]
        
        # 应用筛选条件
        filtered_notifications = []
        for notif in notifications:
            # 分类筛选
            if category and notif["category"] != category:
                continue
            
            # 类型筛选
            if type and notif["type"] != type:
                continue
            
            # 已读状态筛选
            if is_read is not None and notif["is_read"] != is_read:
                continue
            
            # 星标筛选
            if is_starred is not None and notif["is_starred"] != is_starred:
                continue
            
            filtered_notifications.append(notif)
        
        # 分页
        total = len(filtered_notifications)
        paginated_notifications = filtered_notifications[offset:offset + limit]
        
        # 统计信息
        stats = {
            "total": total,
            "unread_count": sum(1 for n in notifications if not n["is_read"]),
            "starred_count": sum(1 for n in notifications if n["is_starred"]),
            "by_category": {},
            "by_type": {}
        }
        
        # 分类统计
        for notif in notifications:
            category_key = notif["category"]
            type_key = notif["type"]
            
            if category_key not in stats["by_category"]:
                stats["by_category"][category_key] = {"total": 0, "unread": 0}
            stats["by_category"][category_key]["total"] += 1
            if not notif["is_read"]:
                stats["by_category"][category_key]["unread"] += 1
            
            if type_key not in stats["by_type"]:
                stats["by_type"][type_key] = 0
            stats["by_type"][type_key] += 1
        
        response_data = {
            "notifications": [
                {
                    **notif,
                    "created_at": notif["created_at"].isoformat()
                }
                for notif in paginated_notifications
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            },
            "stats": stats,
            "filters": {
                "category": category,
                "type": type,
                "is_read": is_read,
                "is_starred": is_starred
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取通知列表成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取通知列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取通知列表失败"
        )


@router.post("/notifications", response_model=Dict[str, Any], summary="创建通知")
async def create_notification(
    request: NotificationCreateRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    创建新通知（系统内部使用或管理员使用）
    """
    try:
        logger.info(f"Frontend API - 创建通知: user_id={context.user.id}, title={request.title}")
        
        # 创建通知数据
        notification_data = {
            "id": 6,  # 模拟新ID
            "title": request.title,
            "content": request.content,
            "type": request.type,
            "priority": request.priority,
            "category": request.category,
            "is_read": False,
            "is_starred": False,
            "is_archived": False,
            "created_at": datetime.now(),
            "action_url": request.action_url,
            "action_data": request.action_data or {},
            "scheduled_time": datetime.fromisoformat(request.scheduled_time) if request.scheduled_time else None,
            "expires_at": datetime.fromisoformat(request.expires_at) if request.expires_at else None,
            "user_id": context.user.id,
            "metadata": {
                "source": "frontend_api",
                "created_by": context.user.id
            }
        }
        
        # 如果设置了定时发送，添加到任务队列
        if notification_data["scheduled_time"]:
            try:
                # 创建定时任务
                task_data = {
                    "notification_id": notification_data["id"],
                    "user_id": context.user.id,
                    "scheduled_time": notification_data["scheduled_time"],
                    "title": notification_data["title"],
                    "content": notification_data["content"],
                    "type": notification_data["type"],
                    "priority": notification_data["priority"],
                    "category": notification_data["category"],
                    "action_url": notification_data.get("action_url"),
                    "action_data": notification_data.get("action_data"),
                    "created_at": datetime.now()
                }
                
                # 添加到队列管理器 (这里假设有一个全局的任务调度器)
                from app.core.scheduler import ScheduledTaskManager
                scheduler = ScheduledTaskManager()
                await scheduler.schedule_notification(task_data)
                
                logger.info(f"已添加定时通知任务: {notification_data['id']}, 发送时间: {notification_data['scheduled_time']}")
            except Exception as e:
                logger.error(f"添加定时任务失败: {str(e)}")
                # 定时任务失败不影响通知创建，但记录错误
        
        response_data = {
            **notification_data,
            "created_at": notification_data["created_at"].isoformat(),
            "scheduled_time": notification_data["scheduled_time"].isoformat() if notification_data["scheduled_time"] else None,
            "expires_at": notification_data["expires_at"].isoformat() if notification_data["expires_at"] else None
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="通知创建成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 创建通知失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="通知创建失败"
        )


@router.get("/notifications/{notification_id}", response_model=Dict[str, Any], summary="获取通知详情")
async def get_notification(
    notification_id: int = Path(..., description="通知ID"),
    mark_as_read: bool = Query(True, description="是否标记为已读"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取通知详细信息
    
    可选择是否在查看时自动标记为已读
    """
    try:
        logger.info(f"Frontend API - 获取通知详情: user_id={context.user.id}, notification_id={notification_id}")
        
        # 模拟获取通知详情
        notification = {
            "id": notification_id,
            "title": "新对话消息",
            "content": "AI助手'技术顾问'在对话中回复了您的问题：'关于Python异步编程的最佳实践，建议使用async/await语法...'",
            "type": "info",
            "priority": "normal",
            "category": "chat",
            "is_read": mark_as_read,  # 根据参数决定是否标记为已读
            "is_starred": False,
            "is_archived": False,
            "created_at": datetime.now() - timedelta(minutes=30),
            "read_at": datetime.now() if mark_as_read else None,
            "action_url": "/chat/conversations/123",
            "action_data": {
                "conversation_id": 123,
                "assistant_name": "技术顾问",
                "message_id": 456
            },
            "metadata": {
                "source": "chat_service",
                "assistant_id": 5,
                "related_entities": ["conversation:123", "assistant:5"]
            },
            "related_notifications": [2, 5]  # 相关通知ID
        }
        
        # 如果标记为已读，这里应该更新数据库
        if mark_as_read and not notification["is_read"]:
            try:
                # 更新已读状态
                notification_service = container.get_notification_service()
                update_result = await notification_service.mark_as_read(
                    notification_id=notification_id,
                    user_id=context.user.id,
                    read_at=datetime.now()
                )
                
                if update_result:
                    notification["is_read"] = True
                    notification["read_at"] = datetime.now()
                    logger.info(f"通知 {notification_id} 已标记为已读")
                else:
                    logger.warning(f"无法标记通知 {notification_id} 为已读")
            except Exception as e:
                logger.error(f"更新已读状态失败: {str(e)}")
                # 状态更新失败不影响获取详情
        
        response_data = {
            **notification,
            "created_at": notification["created_at"].isoformat(),
            "read_at": notification["read_at"].isoformat() if notification["read_at"] else None
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取通知详情成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取通知详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取通知详情失败"
        )


@router.put("/notifications/{notification_id}", response_model=Dict[str, Any], summary="更新通知")
async def update_notification(
    notification_id: int = Path(..., description="通知ID"),
    request: NotificationUpdateRequest = None,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新通知状态
    """
    try:
        logger.info(f"Frontend API - 更新通知: user_id={context.user.id}, notification_id={notification_id}")
        
        # 获取更新数据
        update_data = {
            key: value for key, value in request.model_dump(exclude_unset=True).items()
            if value is not None
        }
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供更新内容"
            )
        
        # 模拟更新结果
        updated_notification = {
            "id": notification_id,
            "is_read": update_data.get("is_read", False),
            "is_starred": update_data.get("is_starred", False),
            "is_archived": update_data.get("is_archived", False),
            "updated_at": datetime.now(),
            "read_at": datetime.now() if update_data.get("is_read") else None
        }
        
        response_data = {
            **updated_notification,
            "updated_at": updated_notification["updated_at"].isoformat(),
            "read_at": updated_notification["read_at"].isoformat() if updated_notification["read_at"] else None,
            "updated_fields": list(update_data.keys())
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="通知更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新通知失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="通知更新失败"
        )


@router.delete("/notifications/{notification_id}", response_model=Dict[str, Any], summary="删除通知")
async def delete_notification(
    notification_id: int = Path(..., description="通知ID"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    删除通知
    """
    try:
        logger.info(f"Frontend API - 删除通知: user_id={context.user.id}, notification_id={notification_id}")
        
        # 验证通知属于当前用户
        notification_service = container.get_notification_service()
        notification = await notification_service.get_notification_by_id(notification_id)
        
        if not notification:
            raise HTTPException(
                status_code=404,
                detail="通知不存在"
            )
        
        # 验证用户权限
        if hasattr(notification, 'user_id') and notification.user_id != context.user.id:
            raise HTTPException(
                status_code=403,
                detail="无权删除该通知"
            )
        
        # 执行实际的删除操作
        delete_result = await notification_service.delete_notification(
            notification_id=notification_id,
            user_id=context.user.id
        )
        
        if not delete_result:
            raise HTTPException(
                status_code=500,
                detail="删除操作失败"
            )
        
        logger.info(f"通知 {notification_id} 已成功删除")
        
        return InternalResponseFormatter.format_success(
            data={"notification_id": notification_id},
            message="通知删除成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 删除通知失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="通知删除失败"
        )


# ================================
# 批量操作接口
# ================================

@router.post("/notifications/bulk", response_model=Dict[str, Any], summary="批量操作通知")
async def bulk_notification_operation(
    request: BulkNotificationRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    批量操作通知
    
    支持批量标记已读、归档、删除等操作
    """
    try:
        logger.info(f"Frontend API - 批量操作通知: user_id={context.user.id}, action={request.action}, count={len(request.notification_ids)}")
        
        # 验证操作类型
        valid_actions = ["mark_read", "mark_unread", "archive", "delete", "star", "unstar"]
        if request.action not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"无效的操作类型，支持的操作：{', '.join(valid_actions)}"
            )
        
        # 验证通知数量限制
        if len(request.notification_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="批量操作的通知数量不能超过100个"
            )
        
        # 执行批量操作
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        for notification_id in request.notification_ids:
            try:
                # 验证通知属于当前用户
                notification_service = container.get_notification_service()
                notification = await notification_service.get_notification_by_id(notification_id)
                
                if not notification:
                    failed_count += 1
                    failed_ids.append(notification_id)
                    logger.warning(f"通知不存在: notification_id={notification_id}")
                    continue
                
                if hasattr(notification, 'user_id') and notification.user_id != context.user.id:
                    failed_count += 1
                    failed_ids.append(notification_id)
                    logger.warning(f"无权操作通知: notification_id={notification_id}")
                    continue
                
                # 执行实际的操作
                operation_result = False
                if request.action == "mark_read":
                    operation_result = await notification_service.mark_as_read(notification_id, context.user.id)
                elif request.action == "mark_unread":
                    operation_result = await notification_service.mark_as_unread(notification_id, context.user.id)
                elif request.action == "archive":
                    operation_result = await notification_service.archive_notification(notification_id, context.user.id)
                elif request.action == "delete":
                    operation_result = await notification_service.delete_notification(notification_id, context.user.id)
                elif request.action == "star":
                    operation_result = await notification_service.star_notification(notification_id, context.user.id)
                elif request.action == "unstar":
                    operation_result = await notification_service.unstar_notification(notification_id, context.user.id)
                
                if operation_result:
                    success_count += 1
                    # 记录审计日志
                    await notification_service.log_audit_action({
                        "action": f"bulk_{request.action}",
                        "notification_id": notification_id,
                        "user_id": context.user.id,
                        "timestamp": datetime.now(),
                        "metadata": {
                            "batch_operation": True,
                            "total_items": len(request.notification_ids)
                        }
                    })
                else:
                    failed_count += 1
                    failed_ids.append(notification_id)
                    
            except Exception as e:
                failed_count += 1
                failed_ids.append(notification_id)
                logger.warning(f"批量操作失败: notification_id={notification_id}, error={str(e)}")
        
        # 构建响应数据
        response_data = {
            "action": request.action,
            "total_requested": len(request.notification_ids),
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids,
            "processed_at": datetime.now().isoformat()
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message=f"批量操作完成，成功{success_count}个，失败{failed_count}个"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 批量操作通知失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="批量操作失败"
        )


# ================================
# 通知设置管理接口
# ================================

@router.get("/notifications/settings", response_model=Dict[str, Any], summary="获取通知设置")
async def get_notification_settings(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户的通知设置
    """
    try:
        logger.info(f"Frontend API - 获取通知设置: user_id={context.user.id}")
        
        # 模拟通知设置数据
        settings_data = {
            "enable_push": True,
            "enable_email": False,
            "enable_in_app": True,
            "enable_desktop": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "category_settings": {
                "chat": {
                    "enable_push": True,
                    "enable_email": False,
                    "enable_in_app": True,
                    "enable_desktop": True
                },
                "knowledge": {
                    "enable_push": False,
                    "enable_email": True,
                    "enable_in_app": True,
                    "enable_desktop": False
                },
                "system": {
                    "enable_push": True,
                    "enable_email": True,
                    "enable_in_app": True,
                    "enable_desktop": True
                },
                "assistant": {
                    "enable_push": True,
                    "enable_email": False,
                    "enable_in_app": True,
                    "enable_desktop": True
                },
                "general": {
                    "enable_push": False,
                    "enable_email": False,
                    "enable_in_app": True,
                    "enable_desktop": False
                }
            },
            "priority_settings": {
                "urgent": {
                    "bypass_quiet_hours": True,
                    "force_desktop": True
                },
                "high": {
                    "bypass_quiet_hours": False,
                    "force_desktop": False
                }
            },
            "delivery_settings": {
                "batch_notifications": False,
                "batch_interval_minutes": 15,
                "instant_for_mentions": True,
                "digest_enabled": True,
                "digest_frequency": "daily",
                "digest_time": "09:00"
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=settings_data,
            message="获取通知设置成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取通知设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取通知设置失败"
        )


@router.put("/notifications/settings", response_model=Dict[str, Any], summary="更新通知设置")
async def update_notification_settings(
    request: NotificationSettingsRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的通知设置
    """
    try:
        logger.info(f"Frontend API - 更新通知设置: user_id={context.user.id}")
        
        # 获取更新数据
        update_data = {
            key: value for key, value in request.model_dump(exclude_unset=True).items()
            if value is not None
        }
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供更新内容"
            )
        
        # 验证时间格式
        time_fields = ["quiet_hours_start", "quiet_hours_end"]
        for field in time_fields:
            if field in update_data:
                time_str = update_data[field]
                try:
                    datetime.strptime(time_str, "%H:%M")
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"时间格式错误，请使用HH:MM格式: {field}"
                    )
        
        # 实现实际的数据库更新逻辑
        try:
            notification_service = container.get_notification_service()
            
            # 更新用户通知设置
            update_result = await notification_service.update_user_notification_settings(
                user_id=context.user.id,
                settings=update_data
            )
            
            if not update_result:
                raise HTTPException(
                    status_code=500,
                    detail="更新设置失败"
                )
            
            # 记录设置变更日志
            await notification_service.log_settings_change({
                "user_id": context.user.id,
                "changed_fields": list(update_data.keys()),
                "old_values": {},  # 这里可以记录旧值
                "new_values": update_data,
                "timestamp": datetime.now(),
                "ip_address": getattr(context, 'ip_address', None),
                "user_agent": getattr(context, 'user_agent', None)
            })
            
            logger.info(f"通知设置已更新: user_id={context.user.id}, fields={list(update_data.keys())}")
        except Exception as e:
            logger.error(f"数据库更新失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="设置更新失败，请稍后重试"
            )
        
        response_data = {
            "updated_fields": list(update_data.keys()),
            "settings": update_data,
            "updated_at": datetime.now().isoformat()
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="通知设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新通知设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="通知设置更新失败"
        )


# ================================
# 实时通知WebSocket接口
# ================================

class NotificationConnectionManager:
    """通知连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """建立连接"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"用户 {user_id} 建立通知WebSocket连接")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """断开连接"""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                logger.info(f"用户 {user_id} 断开通知WebSocket连接")
            except ValueError:
                pass
    
    async def send_personal_notification(self, user_id: int, notification: Dict[str, Any]):
        """发送个人通知"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(notification))
                except Exception as e:
                    logger.error(f"发送通知失败: user_id={user_id}, error={str(e)}")
    
    async def send_broadcast_notification(self, notification: Dict[str, Any]):
        """发送广播通知"""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(notification))
                except Exception as e:
                    logger.error(f"发送广播通知失败: user_id={user_id}, error={str(e)}")


# 全局连接管理器
notification_manager = NotificationConnectionManager()


@router.websocket("/notifications/ws")
async def notification_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="用户认证令牌")
):
    """
    实时通知WebSocket连接
    
    客户端需要提供有效的认证令牌
    """
    try:
        # 验证token并获取用户信息
        try:
            from app.core.auth import JWTManager
            jwt_manager = JWTManager()
            
            # 验证和解析token
            payload = await jwt_manager.verify_token(token)
            user_id = payload.get("user_id")
            
            if not user_id:
                await websocket.close(code=1008, reason="Invalid token: missing user_id")
                return
                
            logger.info(f"WebSocket用户验证成功: user_id={user_id}")
            
        except Exception as e:
            logger.error(f"WebSocket token验证失败: {str(e)}")
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        await notification_manager.connect(websocket, user_id)
        
        # 发送连接确认消息
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "通知连接已建立",
            "timestamp": datetime.now().isoformat()
        }))
        
        # 保持连接并处理客户端消息
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理客户端消息
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                elif message.get("type") == "subscribe":
                    # 处理订阅特定类型的通知
                    categories = message.get("categories", [])
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "categories": categories,
                        "timestamp": datetime.now().isoformat()
                    }))
                
        except WebSocketDisconnect:
            notification_manager.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket连接错误: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


# ================================
# 辅助函数
# ================================

async def send_notification_to_user(user_id: int, notification: Dict[str, Any]):
    """向特定用户发送实时通知"""
    try:
        await notification_manager.send_personal_notification(user_id, notification)
    except Exception as e:
        logger.error(f"发送实时通知失败: user_id={user_id}, error={str(e)}")


async def send_broadcast_notification(notification: Dict[str, Any]):
    """发送广播通知给所有在线用户"""
    try:
        await notification_manager.send_broadcast_notification(notification)
    except Exception as e:
        logger.error(f"发送广播通知失败: error={str(e)}") 