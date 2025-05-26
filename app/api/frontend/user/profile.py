"""
Frontend API - 用户资料管理接口
提供用户个人信息查看、编辑、头像上传等功能
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr
import logging
from datetime import datetime
import os
import uuid

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

class ProfileUpdateRequest(BaseModel):
    """用户资料更新请求模型"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    location: Optional[str] = Field(None, max_length=100, description="所在地")
    website: Optional[str] = Field(None, max_length=200, description="个人网站")
    company: Optional[str] = Field(None, max_length=100, description="公司")
    job_title: Optional[str] = Field(None, max_length=100, description="职位")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    birth_date: Optional[str] = Field(None, description="生日（YYYY-MM-DD）")
    gender: Optional[str] = Field(None, description="性别: male, female, other")


class EmailUpdateRequest(BaseModel):
    """邮箱更新请求模型"""
    new_email: EmailStr = Field(..., description="新邮箱")
    password: str = Field(..., description="当前密码确认")


class PhoneUpdateRequest(BaseModel):
    """手机号更新请求模型"""
    new_phone: str = Field(..., max_length=20, description="新手机号")
    verification_code: str = Field(..., max_length=6, description="验证码")


class SecurityInfoRequest(BaseModel):
    """安全信息查询请求模型"""
    include_login_history: bool = Field(default=True, description="是否包含登录历史")
    include_device_list: bool = Field(default=True, description="是否包含设备列表")


# ================================
# 用户资料接口实现
# ================================

@router.get("/info", response_model=Dict[str, Any], summary="获取用户资料")
async def get_user_profile(
    include_stats: bool = Field(default=False, description="是否包含统计信息"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取当前用户的详细资料信息
    
    返回用户的基本信息、扩展信息和统计数据。
    """
    try:
        logger.info(f"Frontend API - 获取用户资料: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 获取用户详细信息
        profile_data = await user_service.get_user_profile(
            context.user.id,
            include_stats=include_stats
        )
        
        if not profile_data:
            raise HTTPException(
                status_code=404,
                detail="用户信息不存在"
            )
        
        # 构建响应数据
        user_profile = {
            "basic_info": {
                "id": profile_data.get("id"),
                "username": profile_data.get("username"),
                "email": profile_data.get("email"),
                "nickname": profile_data.get("nickname"),
                "avatar_url": profile_data.get("avatar_url"),
                "email_verified": profile_data.get("email_verified", False),
                "phone_verified": profile_data.get("phone_verified", False)
            },
            "extended_info": {
                "bio": profile_data.get("bio"),
                "location": profile_data.get("location"),
                "website": profile_data.get("website"),
                "company": profile_data.get("company"),
                "job_title": profile_data.get("job_title"),
                "phone": profile_data.get("phone"),
                "birth_date": profile_data.get("birth_date"),
                "gender": profile_data.get("gender")
            },
            "account_info": {
                "created_at": profile_data.get("created_at"),
                "last_login": profile_data.get("last_login"),
                "status": profile_data.get("status", "active"),
                "role": profile_data.get("role", "user"),
                "subscription_type": profile_data.get("subscription_type", "free")
            }
        }
        
        # 添加统计信息
        if include_stats and profile_data.get("stats"):
            user_profile["statistics"] = {
                "total_conversations": profile_data["stats"].get("total_conversations", 0),
                "total_messages": profile_data["stats"].get("total_messages", 0),
                "total_assistants": profile_data["stats"].get("total_assistants", 0),
                "total_knowledge_bases": profile_data["stats"].get("total_knowledge_bases", 0),
                "tokens_used": profile_data["stats"].get("tokens_used", 0),
                "files_uploaded": profile_data["stats"].get("files_uploaded", 0),
                "active_days": profile_data["stats"].get("active_days", 0)
            }
        
        return InternalResponseFormatter.format_success(
            data=user_profile,
            message="获取用户资料成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 获取用户资料失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取用户资料失败"
        )


@router.put("/update", response_model=Dict[str, Any], summary="更新用户资料")
async def update_user_profile(
    request: ProfileUpdateRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的基本资料信息
    
    允许用户更新昵称、简介、联系方式等信息。
    """
    try:
        logger.info(f"Frontend API - 更新用户资料: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 构建更新数据（只包含非空字段）
        update_data = {}
        for field, value in request.dict().items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="没有提供需要更新的字段"
            )
        
        # 数据验证
        if "birth_date" in update_data:
            try:
                datetime.strptime(update_data["birth_date"], "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="生日格式错误，请使用YYYY-MM-DD格式"
                )
        
        if "gender" in update_data:
            if update_data["gender"] not in ["male", "female", "other"]:
                raise HTTPException(
                    status_code=400,
                    detail="性别值无效"
                )
        
        # 执行更新
        update_result = await user_service.update_user_profile(
            context.user.id,
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=update_result.get("message", "更新失败")
            )
        
        # 获取更新后的用户信息
        updated_profile = await user_service.get_user_profile(context.user.id)
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "profile": updated_profile
            },
            message="用户资料更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新用户资料失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="更新用户资料失败"
        )


@router.post("/avatar", response_model=Dict[str, Any], summary="上传用户头像")
async def upload_avatar(
    avatar: UploadFile = File(..., description="头像文件"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    上传用户头像
    
    支持JPG、PNG、GIF格式，文件大小限制5MB。
    """
    try:
        logger.info(f"Frontend API - 上传用户头像: user_id={context.user.id}")
        
        # 文件格式验证
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif"]
        if avatar.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="不支持的文件格式，请上传JPG、PNG或GIF格式的图片"
            )
        
        # 文件大小验证（5MB）
        if avatar.size > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="文件大小不能超过5MB"
            )
        
        # 获取文件存储服务
        file_service = container.get_file_service()
        
        # 生成唯一文件名
        file_extension = os.path.splitext(avatar.filename)[1]
        unique_filename = f"avatar_{context.user.id}_{uuid.uuid4().hex}{file_extension}"
        
        # 上传文件
        upload_result = await file_service.upload_file(
            file_content=await avatar.read(),
            filename=unique_filename,
            content_type=avatar.content_type,
            folder="avatars",
            user_id=context.user.id
        )
        
        if not upload_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail="文件上传失败"
            )
        
        avatar_url = upload_result["file_url"]
        
        # 更新用户头像URL
        user_service = container.get_user_service()
        update_result = await user_service.update_user_profile(
            context.user.id,
            {"avatar_url": avatar_url}
        )
        
        if not update_result.get("success"):
            # 如果更新失败，删除已上传的文件
            await file_service.delete_file(upload_result["file_id"])
            raise HTTPException(
                status_code=500,
                detail="头像保存失败"
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "avatar_url": avatar_url,
                "file_id": upload_result["file_id"],
                "file_size": avatar.size,
                "uploaded_at": datetime.now().isoformat()
            },
            message="头像上传成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 上传头像失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="头像上传失败"
        )


@router.delete("/avatar", response_model=Dict[str, Any], summary="删除用户头像")
async def delete_avatar(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    删除用户头像，恢复为默认头像
    """
    try:
        logger.info(f"Frontend API - 删除用户头像: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 获取当前用户信息
        user_info = await user_service.get_user_profile(context.user.id)
        current_avatar = user_info.get("avatar_url")
        
        # 清除用户头像URL
        update_result = await user_service.update_user_profile(
            context.user.id,
            {"avatar_url": None}
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail="头像删除失败"
            )
        
        # 删除文件（如果是自定义头像）
        if current_avatar and "avatars/" in current_avatar:
            try:
                file_service = container.get_file_service()
                await file_service.delete_file_by_url(current_avatar)
            except Exception as e:
                logger.warning(f"删除头像文件失败: {str(e)}")
        
        return InternalResponseFormatter.format_success(
            data={"avatar_deleted": True},
            message="头像删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 删除头像失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="头像删除失败"
        )


@router.put("/email", response_model=Dict[str, Any], summary="更新邮箱")
async def update_email(
    request: EmailUpdateRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户邮箱
    
    需要验证当前密码并发送邮箱验证邮件。
    """
    try:
        logger.info(f"Frontend API - 更新邮箱: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 验证当前密码
        password_valid = await user_service.verify_password(
            context.user.id,
            request.password
        )
        
        if not password_valid:
            raise HTTPException(
                status_code=400,
                detail="当前密码错误"
            )
        
        # 检查新邮箱是否已被使用
        email_exists = await user_service.check_email_exists(request.new_email)
        if email_exists:
            raise HTTPException(
                status_code=400,
                detail="邮箱已被其他用户使用"
            )
        
        # 更新邮箱并发送验证邮件
        update_result = await user_service.update_user_email(
            context.user.id,
            request.new_email
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "邮箱更新失败")
            )
        
        # 发送验证邮件
        verification_result = await user_service.send_email_verification(
            context.user.id,
            request.new_email
        )
        
        return InternalResponseFormatter.format_success(
            data={
                "email_updated": True,
                "new_email": request.new_email,
                "verification_sent": verification_result.get("sent", False),
                "verification_required": True
            },
            message="邮箱更新成功，请查看新邮箱验证邮件"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新邮箱失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="邮箱更新失败"
        )


@router.get("/security", response_model=Dict[str, Any], summary="获取安全信息")
async def get_security_info(
    include_login_history: bool = Field(default=True, description="是否包含登录历史"),
    include_device_list: bool = Field(default=True, description="是否包含设备列表"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户的安全信息
    
    包括登录历史、设备列表、安全设置等。
    """
    try:
        logger.info(f"Frontend API - 获取安全信息: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 获取基本安全信息
        security_info = await user_service.get_user_security_info(context.user.id)
        
        security_data = {
            "account_security": {
                "email_verified": security_info.get("email_verified", False),
                "phone_verified": security_info.get("phone_verified", False),
                "two_factor_enabled": security_info.get("two_factor_enabled", False),
                "password_last_changed": security_info.get("password_last_changed"),
                "account_locked": security_info.get("account_locked", False)
            },
            "recent_activity": {
                "last_login": security_info.get("last_login"),
                "last_password_change": security_info.get("last_password_change"),
                "failed_login_attempts": security_info.get("failed_login_attempts", 0)
            }
        }
        
        # 添加登录历史
        if include_login_history:
            login_history = await user_service.get_login_history(
                context.user.id,
                limit=10
            )
            security_data["login_history"] = login_history.get("history", [])
        
        # 添加设备列表
        if include_device_list:
            device_list = await user_service.get_user_devices(context.user.id)
            security_data["devices"] = device_list.get("devices", [])
        
        return InternalResponseFormatter.format_success(
            data=security_data,
            message="获取安全信息成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取安全信息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取安全信息失败"
        )


@router.delete("/account", response_model=Dict[str, Any], summary="删除账户")
async def delete_account(
    password: str = Field(..., description="当前密码确认"),
    confirmation: str = Field(..., description="确认文本（必须输入'DELETE'）"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    删除用户账户
    
    永久删除用户账户及所有相关数据，此操作不可恢复。
    """
    try:
        logger.info(f"Frontend API - 删除账户: user_id={context.user.id}")
        
        # 确认文本验证
        if confirmation != "DELETE":
            raise HTTPException(
                status_code=400,
                detail="请输入正确的确认文本'DELETE'"
            )
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 验证密码
        password_valid = await user_service.verify_password(
            context.user.id,
            password
        )
        
        if not password_valid:
            raise HTTPException(
                status_code=400,
                detail="密码错误"
            )
        
        # 执行账户删除
        delete_result = await user_service.delete_user_account(
            context.user.id,
            reason="user_request"
        )
        
        if not delete_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=delete_result.get("message", "账户删除失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "account_deleted": True,
                "deleted_at": datetime.now().isoformat(),
                "data_retention_days": delete_result.get("data_retention_days", 30)
            },
            message="账户已成功删除"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 删除账户失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="账户删除失败"
        ) 