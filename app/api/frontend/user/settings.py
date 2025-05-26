"""
Frontend API - 用户设置接口
提供账户设置、隐私设置、通知设置、安全设置等功能
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

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

class AccountSettingsRequest(BaseModel):
    """账户设置请求模型"""
    language: Optional[str] = Field(None, description="界面语言: zh-CN, en-US")
    timezone: Optional[str] = Field(None, description="时区")
    theme: Optional[str] = Field(None, description="主题: light, dark, auto")
    default_assistant: Optional[str] = Field(None, description="默认助手ID")
    auto_save_conversations: Optional[bool] = Field(None, description="自动保存对话")
    conversation_history_limit: Optional[int] = Field(None, ge=10, le=1000, description="对话历史保留数量")


class PrivacySettingsRequest(BaseModel):
    """隐私设置请求模型"""
    profile_visibility: Optional[str] = Field(None, description="资料可见性: public, friends, private")
    allow_search_by_username: Optional[bool] = Field(None, description="允许通过用户名搜索")
    allow_search_by_email: Optional[bool] = Field(None, description="允许通过邮箱搜索")
    show_online_status: Optional[bool] = Field(None, description="显示在线状态")
    allow_friend_requests: Optional[bool] = Field(None, description="允许好友请求")
    data_usage_analytics: Optional[bool] = Field(None, description="允许数据使用分析")


class NotificationSettingsRequest(BaseModel):
    """通知设置请求模型"""
    email_notifications: Optional[bool] = Field(None, description="邮件通知")
    push_notifications: Optional[bool] = Field(None, description="推送通知")
    browser_notifications: Optional[bool] = Field(None, description="浏览器通知")
    new_message_notifications: Optional[bool] = Field(None, description="新消息通知")
    system_updates: Optional[bool] = Field(None, description="系统更新通知")
    marketing_emails: Optional[bool] = Field(None, description="营销邮件")
    weekly_digest: Optional[bool] = Field(None, description="周报")
    notification_sound: Optional[bool] = Field(None, description="通知声音")


class SecuritySettingsRequest(BaseModel):
    """安全设置请求模型"""
    two_factor_auth: Optional[bool] = Field(None, description="双因素认证")
    login_alerts: Optional[bool] = Field(None, description="登录提醒")
    session_timeout: Optional[int] = Field(None, ge=300, le=86400, description="会话超时时间（秒）")
    require_password_change: Optional[bool] = Field(None, description="要求定期更改密码")
    allow_multiple_sessions: Optional[bool] = Field(None, description="允许多设备同时登录")


class DataExportRequest(BaseModel):
    """数据导出请求模型"""
    data_types: List[str] = Field(..., description="导出数据类型: conversations, assistants, knowledge_bases, files")
    format: str = Field(default="json", description="导出格式: json, csv, xml")
    include_metadata: bool = Field(default=True, description="包含元数据")


# ================================
# 设置接口实现
# ================================

@router.get("/all", response_model=Dict[str, Any], summary="获取所有设置")
async def get_all_settings(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户的所有设置信息
    
    包括账户设置、隐私设置、通知设置和安全设置。
    """
    try:
        logger.info(f"Frontend API - 获取所有设置: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 获取所有设置
        all_settings = await user_service.get_user_settings(context.user.id)
        
        # 构建响应数据
        settings_data = {
            "account_settings": {
                "language": all_settings.get("language", "zh-CN"),
                "timezone": all_settings.get("timezone", "Asia/Shanghai"),
                "theme": all_settings.get("theme", "light"),
                "default_assistant": all_settings.get("default_assistant"),
                "auto_save_conversations": all_settings.get("auto_save_conversations", True),
                "conversation_history_limit": all_settings.get("conversation_history_limit", 100)
            },
            "privacy_settings": {
                "profile_visibility": all_settings.get("profile_visibility", "private"),
                "allow_search_by_username": all_settings.get("allow_search_by_username", True),
                "allow_search_by_email": all_settings.get("allow_search_by_email", False),
                "show_online_status": all_settings.get("show_online_status", False),
                "allow_friend_requests": all_settings.get("allow_friend_requests", True),
                "data_usage_analytics": all_settings.get("data_usage_analytics", True)
            },
            "notification_settings": {
                "email_notifications": all_settings.get("email_notifications", True),
                "push_notifications": all_settings.get("push_notifications", True),
                "browser_notifications": all_settings.get("browser_notifications", False),
                "new_message_notifications": all_settings.get("new_message_notifications", True),
                "system_updates": all_settings.get("system_updates", True),
                "marketing_emails": all_settings.get("marketing_emails", False),
                "weekly_digest": all_settings.get("weekly_digest", True),
                "notification_sound": all_settings.get("notification_sound", True)
            },
            "security_settings": {
                "two_factor_auth": all_settings.get("two_factor_auth", False),
                "login_alerts": all_settings.get("login_alerts", True),
                "session_timeout": all_settings.get("session_timeout", 3600),
                "require_password_change": all_settings.get("require_password_change", False),
                "allow_multiple_sessions": all_settings.get("allow_multiple_sessions", True)
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=settings_data,
            message="获取设置成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取设置失败"
        )


@router.put("/account", response_model=Dict[str, Any], summary="更新账户设置")
async def update_account_settings(
    request: AccountSettingsRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的账户设置
    
    包括语言、时区、主题、默认助手等设置。
    """
    try:
        logger.info(f"Frontend API - 更新账户设置: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 构建更新数据
        update_data = {}
        for field, value in request.dict().items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供需要更新的设置"
            )
        
        # 验证设置值
        if "language" in update_data:
            allowed_languages = ["zh-CN", "en-US", "ja-JP", "ko-KR"]
            if update_data["language"] not in allowed_languages:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的语言设置"
                )
        
        if "theme" in update_data:
            allowed_themes = ["light", "dark", "auto"]
            if update_data["theme"] not in allowed_themes:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的主题设置"
                )
        
        # 验证默认助手是否存在
        if "default_assistant" in update_data:
            assistant_service = container.get_assistant_service()
            assistant_exists = await assistant_service.check_assistant_access(
                update_data["default_assistant"],
                context.user.id
            )
            if not assistant_exists:
                raise HTTPException(
                    status_code=400,
                    detail="指定的默认助手不存在或无权访问"
                )
        
        # 更新设置
        update_result = await user_service.update_user_settings(
            context.user.id,
            "account_settings",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "settings": update_result.get("settings")
            },
            message="账户设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新账户设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="账户设置更新失败"
        )


@router.put("/privacy", response_model=Dict[str, Any], summary="更新隐私设置")
async def update_privacy_settings(
    request: PrivacySettingsRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的隐私设置
    
    包括资料可见性、搜索权限、在线状态等设置。
    """
    try:
        logger.info(f"Frontend API - 更新隐私设置: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 构建更新数据
        update_data = {}
        for field, value in request.dict().items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供需要更新的设置"
            )
        
        # 验证设置值
        if "profile_visibility" in update_data:
            allowed_visibility = ["public", "friends", "private"]
            if update_data["profile_visibility"] not in allowed_visibility:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的资料可见性设置"
                )
        
        # 更新设置
        update_result = await user_service.update_user_settings(
            context.user.id,
            "privacy_settings",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "隐私设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "settings": update_result.get("settings")
            },
            message="隐私设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新隐私设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="隐私设置更新失败"
        )


@router.put("/notifications", response_model=Dict[str, Any], summary="更新通知设置")
async def update_notification_settings(
    request: NotificationSettingsRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的通知设置
    
    包括邮件通知、推送通知、系统通知等设置。
    """
    try:
        logger.info(f"Frontend API - 更新通知设置: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 构建更新数据
        update_data = {}
        for field, value in request.dict().items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供需要更新的设置"
            )
        
        # 更新设置
        update_result = await user_service.update_user_settings(
            context.user.id,
            "notification_settings",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "通知设置更新失败")
            )
        
        # 如果关闭了邮件通知，同时关闭营销邮件和周报
        if "email_notifications" in update_data and not update_data["email_notifications"]:
            await user_service.update_user_settings(
                context.user.id,
                "notification_settings",
                {
                    "marketing_emails": False,
                    "weekly_digest": False
                }
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "settings": update_result.get("settings")
            },
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


@router.put("/security", response_model=Dict[str, Any], summary="更新安全设置")
async def update_security_settings(
    request: SecuritySettingsRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的安全设置
    
    包括双因素认证、会话超时、登录提醒等设置。
    """
    try:
        logger.info(f"Frontend API - 更新安全设置: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 构建更新数据
        update_data = {}
        for field, value in request.dict().items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供需要更新的设置"
            )
        
        # 如果启用双因素认证，需要先验证
        if "two_factor_auth" in update_data and update_data["two_factor_auth"]:
            # 检查是否已经验证过邮箱
            user_info = await user_service.get_user_profile(context.user.id)
            if not user_info.get("email_verified"):
                raise HTTPException(
                    status_code=400,
                    detail="启用双因素认证前需要先验证邮箱"
                )
        
        # 更新设置
        update_result = await user_service.update_user_settings(
            context.user.id,
            "security_settings",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "安全设置更新失败")
            )
        
        # 如果禁用了多设备登录，终止其他会话
        if "allow_multiple_sessions" in update_data and not update_data["allow_multiple_sessions"]:
            await user_service.terminate_other_sessions(context.user.id)
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "settings": update_result.get("settings"),
                "requires_reauth": "two_factor_auth" in update_data
            },
            message="安全设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新安全设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="安全设置更新失败"
        )


@router.post("/reset", response_model=Dict[str, Any], summary="重置设置")
async def reset_settings(
    category: str = Field(..., description="重置类别: account, privacy, notifications, security, all"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    重置用户设置为默认值
    
    可以选择重置特定类别或所有设置。
    """
    try:
        logger.info(f"Frontend API - 重置设置: user_id={context.user.id}, category={category}")
        
        # 验证重置类别
        allowed_categories = ["account", "privacy", "notifications", "security", "all"]
        if category not in allowed_categories:
            raise HTTPException(
                status_code=400,
                detail="不支持的重置类别"
            )
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 执行重置
        reset_result = await user_service.reset_user_settings(
            context.user.id,
            category
        )
        
        if not reset_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=reset_result.get("message", "设置重置失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "reset_category": category,
                "reset_fields": reset_result.get("reset_fields", []),
                "settings": reset_result.get("settings")
            },
            message=f"{category}设置已重置为默认值"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 重置设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="设置重置失败"
        )


@router.post("/export", response_model=Dict[str, Any], summary="导出用户数据")
async def export_user_data(
    request: DataExportRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    导出用户数据
    
    允许用户导出自己的数据，包括对话、助手、知识库等。
    """
    try:
        logger.info(f"Frontend API - 导出用户数据: user_id={context.user.id}")
        
        # 验证数据类型
        allowed_types = ["conversations", "assistants", "knowledge_bases", "files", "settings", "profile"]
        invalid_types = [t for t in request.data_types if t not in allowed_types]
        if invalid_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的数据类型: {', '.join(invalid_types)}"
            )
        
        # 验证导出格式
        allowed_formats = ["json", "csv", "xml"]
        if request.format not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail="不支持的导出格式"
            )
        
        # 获取数据导出服务
        export_service = container.get_export_service()
        
        # 创建导出任务
        export_request = {
            "user_id": context.user.id,
            "data_types": request.data_types,
            "format": request.format,
            "include_metadata": request.include_metadata
        }
        
        export_result = await export_service.create_export_task(export_request)
        
        if not export_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=export_result.get("message", "导出任务创建失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "export_id": export_result["export_id"],
                "status": "processing",
                "data_types": request.data_types,
                "format": request.format,
                "estimated_completion": export_result.get("estimated_completion"),
                "download_url": None  # 处理完成后提供
            },
            message="数据导出任务已创建，请稍后查看导出状态"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 导出用户数据失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="数据导出失败"
        )


@router.get("/export/{export_id}/status", response_model=Dict[str, Any], summary="查看导出状态")
async def get_export_status(
    export_id: str,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    查看数据导出任务状态
    """
    try:
        logger.info(f"Frontend API - 查看导出状态: user_id={context.user.id}, export_id={export_id}")
        
        # 获取数据导出服务
        export_service = container.get_export_service()
        
        # 查询导出状态
        status_result = await export_service.get_export_status(export_id, context.user.id)
        
        if not status_result:
            raise HTTPException(
                status_code=404,
                detail="导出任务不存在"
            )
        
        return InternalResponseFormatter.format_success(
            data=status_result,
            message="获取导出状态成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 查看导出状态失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取导出状态失败"
        ) 