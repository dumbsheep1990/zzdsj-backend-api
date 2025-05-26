"""
Frontend API - 用户个性化偏好接口
提供AI助手偏好、交互偏好、界面偏好、学习偏好等功能
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

class AIPreferencesRequest(BaseModel):
    """AI偏好设置请求模型"""
    preferred_model: Optional[str] = Field(None, description="偏好的AI模型")
    response_style: Optional[str] = Field(None, description="回复风格: formal, casual, creative, technical")
    response_length: Optional[str] = Field(None, description="回复长度: short, medium, long, auto")
    creativity_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="创造性水平")
    precision_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="精确性水平")
    explanation_detail: Optional[str] = Field(None, description="解释详细程度: basic, detailed, expert")
    auto_suggestions: Optional[bool] = Field(None, description="自动建议")
    context_awareness: Optional[bool] = Field(None, description="上下文感知")


class InteractionPreferencesRequest(BaseModel):
    """交互偏好设置请求模型"""
    input_method: Optional[str] = Field(None, description="输入方式: text, voice, both")
    auto_complete: Optional[bool] = Field(None, description="自动补全")
    quick_replies: Optional[bool] = Field(None, description="快速回复")
    typing_indicators: Optional[bool] = Field(None, description="输入指示器")
    message_grouping: Optional[bool] = Field(None, description="消息分组")
    timestamp_format: Optional[str] = Field(None, description="时间戳格式: 12h, 24h, relative")
    message_reactions: Optional[bool] = Field(None, description="消息反应")
    keyboard_shortcuts: Optional[bool] = Field(None, description="键盘快捷键")


class UIPreferencesRequest(BaseModel):
    """界面偏好设置请求模型"""
    layout_style: Optional[str] = Field(None, description="布局风格: compact, comfortable, spacious")
    sidebar_position: Optional[str] = Field(None, description="侧边栏位置: left, right, hidden")
    chat_bubble_style: Optional[str] = Field(None, description="聊天气泡样式: modern, classic, minimal")
    font_size: Optional[str] = Field(None, description="字体大小: small, medium, large, extra-large")
    font_family: Optional[str] = Field(None, description="字体族: system, serif, sans-serif, monospace")
    color_scheme: Optional[str] = Field(None, description="配色方案: default, blue, green, purple, orange")
    animation_speed: Optional[str] = Field(None, description="动画速度: none, slow, normal, fast")
    density: Optional[str] = Field(None, description="信息密度: compact, normal, relaxed")


class LearningPreferencesRequest(BaseModel):
    """学习偏好设置请求模型"""
    learning_mode: Optional[bool] = Field(None, description="学习模式")
    adaptive_responses: Optional[bool] = Field(None, description="自适应回复")
    personal_knowledge: Optional[bool] = Field(None, description="个人知识学习")
    usage_analytics: Optional[bool] = Field(None, description="使用分析")
    feedback_collection: Optional[bool] = Field(None, description="反馈收集")
    recommendation_engine: Optional[bool] = Field(None, description="推荐引擎")
    conversation_history_learning: Optional[bool] = Field(None, description="对话历史学习")
    pattern_recognition: Optional[bool] = Field(None, description="模式识别")


class ContentPreferencesRequest(BaseModel):
    """内容偏好设置请求模型"""
    content_types: Optional[List[str]] = Field(None, description="偏好内容类型")
    topics_of_interest: Optional[List[str]] = Field(None, description="感兴趣话题")
    language_pairs: Optional[List[Dict[str, str]]] = Field(None, description="语言对")
    content_difficulty: Optional[str] = Field(None, description="内容难度: beginner, intermediate, advanced, expert")
    content_format: Optional[str] = Field(None, description="内容格式: text, markdown, rich_text")
    media_preferences: Optional[List[str]] = Field(None, description="媒体偏好")


class WorkflowPreferencesRequest(BaseModel):
    """工作流偏好设置请求模型"""
    default_workspace: Optional[str] = Field(None, description="默认工作空间")
    auto_organize: Optional[bool] = Field(None, description="自动整理")
    template_suggestions: Optional[bool] = Field(None, description="模板建议")
    collaboration_mode: Optional[str] = Field(None, description="协作模式: private, shared, public")
    backup_frequency: Optional[str] = Field(None, description="备份频率: never, daily, weekly, monthly")
    version_control: Optional[bool] = Field(None, description="版本控制")
    auto_save_interval: Optional[int] = Field(None, ge=30, le=3600, description="自动保存间隔（秒）")


# ================================
# 偏好接口实现
# ================================

@router.get("/all", response_model=Dict[str, Any], summary="获取所有偏好设置")
async def get_all_preferences(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户的所有个性化偏好设置
    
    包括AI偏好、交互偏好、界面偏好、学习偏好等。
    """
    try:
        logger.info(f"Frontend API - 获取所有偏好设置: user_id={context.user.id}")
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 获取所有偏好设置
        all_preferences = await user_service.get_user_preferences(context.user.id)
        
        # 构建响应数据
        preferences_data = {
            "ai_preferences": {
                "preferred_model": all_preferences.get("preferred_model"),
                "response_style": all_preferences.get("response_style", "casual"),
                "response_length": all_preferences.get("response_length", "medium"),
                "creativity_level": all_preferences.get("creativity_level", 0.7),
                "precision_level": all_preferences.get("precision_level", 0.8),
                "explanation_detail": all_preferences.get("explanation_detail", "detailed"),
                "auto_suggestions": all_preferences.get("auto_suggestions", True),
                "context_awareness": all_preferences.get("context_awareness", True)
            },
            "interaction_preferences": {
                "input_method": all_preferences.get("input_method", "text"),
                "auto_complete": all_preferences.get("auto_complete", True),
                "quick_replies": all_preferences.get("quick_replies", True),
                "typing_indicators": all_preferences.get("typing_indicators", True),
                "message_grouping": all_preferences.get("message_grouping", False),
                "timestamp_format": all_preferences.get("timestamp_format", "12h"),
                "message_reactions": all_preferences.get("message_reactions", True),
                "keyboard_shortcuts": all_preferences.get("keyboard_shortcuts", True)
            },
            "ui_preferences": {
                "layout_style": all_preferences.get("layout_style", "comfortable"),
                "sidebar_position": all_preferences.get("sidebar_position", "left"),
                "chat_bubble_style": all_preferences.get("chat_bubble_style", "modern"),
                "font_size": all_preferences.get("font_size", "medium"),
                "font_family": all_preferences.get("font_family", "system"),
                "color_scheme": all_preferences.get("color_scheme", "default"),
                "animation_speed": all_preferences.get("animation_speed", "normal"),
                "density": all_preferences.get("density", "normal")
            },
            "learning_preferences": {
                "learning_mode": all_preferences.get("learning_mode", True),
                "adaptive_responses": all_preferences.get("adaptive_responses", True),
                "personal_knowledge": all_preferences.get("personal_knowledge", False),
                "usage_analytics": all_preferences.get("usage_analytics", True),
                "feedback_collection": all_preferences.get("feedback_collection", True),
                "recommendation_engine": all_preferences.get("recommendation_engine", True),
                "conversation_history_learning": all_preferences.get("conversation_history_learning", True),
                "pattern_recognition": all_preferences.get("pattern_recognition", True)
            },
            "content_preferences": {
                "content_types": all_preferences.get("content_types", []),
                "topics_of_interest": all_preferences.get("topics_of_interest", []),
                "language_pairs": all_preferences.get("language_pairs", []),
                "content_difficulty": all_preferences.get("content_difficulty", "intermediate"),
                "content_format": all_preferences.get("content_format", "markdown"),
                "media_preferences": all_preferences.get("media_preferences", ["text", "images"])
            },
            "workflow_preferences": {
                "default_workspace": all_preferences.get("default_workspace"),
                "auto_organize": all_preferences.get("auto_organize", True),
                "template_suggestions": all_preferences.get("template_suggestions", True),
                "collaboration_mode": all_preferences.get("collaboration_mode", "private"),
                "backup_frequency": all_preferences.get("backup_frequency", "daily"),
                "version_control": all_preferences.get("version_control", False),
                "auto_save_interval": all_preferences.get("auto_save_interval", 300)
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=preferences_data,
            message="获取偏好设置成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取偏好设置失败"
        )


@router.put("/ai", response_model=Dict[str, Any], summary="更新AI偏好设置")
async def update_ai_preferences(
    request: AIPreferencesRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的AI偏好设置
    
    包括偏好模型、回复风格、创造性水平等。
    """
    try:
        logger.info(f"Frontend API - 更新AI偏好设置: user_id={context.user.id}")
        
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
                detail="没有提供需要更新的偏好设置"
            )
        
        # 验证设置值
        if "response_style" in update_data:
            allowed_styles = ["formal", "casual", "creative", "technical"]
            if update_data["response_style"] not in allowed_styles:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的回复风格"
                )
        
        if "response_length" in update_data:
            allowed_lengths = ["short", "medium", "long", "auto"]
            if update_data["response_length"] not in allowed_lengths:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的回复长度设置"
                )
        
        if "explanation_detail" in update_data:
            allowed_details = ["basic", "detailed", "expert"]
            if update_data["explanation_detail"] not in allowed_details:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的解释详细程度设置"
                )
        
        # 验证偏好模型是否可用
        if "preferred_model" in update_data:
            ai_service = container.get_ai_service()
            model_available = await ai_service.check_model_availability(
                update_data["preferred_model"],
                context.user.id
            )
            if not model_available:
                raise HTTPException(
                    status_code=400,
                    detail="指定的AI模型不可用"
                )
        
        # 更新偏好设置
        update_result = await user_service.update_user_preferences(
            context.user.id,
            "ai_preferences",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "AI偏好设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "preferences": update_result.get("preferences")
            },
            message="AI偏好设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新AI偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="AI偏好设置更新失败"
        )


@router.put("/interaction", response_model=Dict[str, Any], summary="更新交互偏好设置")
async def update_interaction_preferences(
    request: InteractionPreferencesRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的交互偏好设置
    
    包括输入方式、自动补全、快速回复等。
    """
    try:
        logger.info(f"Frontend API - 更新交互偏好设置: user_id={context.user.id}")
        
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
                detail="没有提供需要更新的偏好设置"
            )
        
        # 验证设置值
        if "input_method" in update_data:
            allowed_methods = ["text", "voice", "both"]
            if update_data["input_method"] not in allowed_methods:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的输入方式"
                )
        
        if "timestamp_format" in update_data:
            allowed_formats = ["12h", "24h", "relative"]
            if update_data["timestamp_format"] not in allowed_formats:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的时间戳格式"
                )
        
        # 更新偏好设置
        update_result = await user_service.update_user_preferences(
            context.user.id,
            "interaction_preferences",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "交互偏好设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "preferences": update_result.get("preferences")
            },
            message="交互偏好设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新交互偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="交互偏好设置更新失败"
        )


@router.put("/ui", response_model=Dict[str, Any], summary="更新界面偏好设置")
async def update_ui_preferences(
    request: UIPreferencesRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的界面偏好设置
    
    包括布局风格、字体、配色方案等。
    """
    try:
        logger.info(f"Frontend API - 更新界面偏好设置: user_id={context.user.id}")
        
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
                detail="没有提供需要更新的偏好设置"
            )
        
        # 验证设置值
        validation_rules = {
            "layout_style": ["compact", "comfortable", "spacious"],
            "sidebar_position": ["left", "right", "hidden"],
            "chat_bubble_style": ["modern", "classic", "minimal"],
            "font_size": ["small", "medium", "large", "extra-large"],
            "font_family": ["system", "serif", "sans-serif", "monospace"],
            "color_scheme": ["default", "blue", "green", "purple", "orange"],
            "animation_speed": ["none", "slow", "normal", "fast"],
            "density": ["compact", "normal", "relaxed"]
        }
        
        for field, value in update_data.items():
            if field in validation_rules and value not in validation_rules[field]:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的{field}设置值: {value}"
                )
        
        # 更新偏好设置
        update_result = await user_service.update_user_preferences(
            context.user.id,
            "ui_preferences",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "界面偏好设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "preferences": update_result.get("preferences")
            },
            message="界面偏好设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新界面偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="界面偏好设置更新失败"
        )


@router.put("/learning", response_model=Dict[str, Any], summary="更新学习偏好设置")
async def update_learning_preferences(
    request: LearningPreferencesRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的学习偏好设置
    
    包括学习模式、自适应回复、个人知识学习等。
    """
    try:
        logger.info(f"Frontend API - 更新学习偏好设置: user_id={context.user.id}")
        
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
                detail="没有提供需要更新的偏好设置"
            )
        
        # 如果关闭学习模式，同时关闭相关功能
        if "learning_mode" in update_data and not update_data["learning_mode"]:
            update_data.update({
                "adaptive_responses": False,
                "personal_knowledge": False,
                "conversation_history_learning": False,
                "pattern_recognition": False
            })
        
        # 更新偏好设置
        update_result = await user_service.update_user_preferences(
            context.user.id,
            "learning_preferences",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "学习偏好设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "preferences": update_result.get("preferences")
            },
            message="学习偏好设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新学习偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="学习偏好设置更新失败"
        )


@router.put("/content", response_model=Dict[str, Any], summary="更新内容偏好设置")
async def update_content_preferences(
    request: ContentPreferencesRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的内容偏好设置
    
    包括内容类型、感兴趣话题、内容难度等。
    """
    try:
        logger.info(f"Frontend API - 更新内容偏好设置: user_id={context.user.id}")
        
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
                detail="没有提供需要更新的偏好设置"
            )
        
        # 验证设置值
        if "content_difficulty" in update_data:
            allowed_difficulties = ["beginner", "intermediate", "advanced", "expert"]
            if update_data["content_difficulty"] not in allowed_difficulties:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的内容难度设置"
                )
        
        if "content_format" in update_data:
            allowed_formats = ["text", "markdown", "rich_text"]
            if update_data["content_format"] not in allowed_formats:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的内容格式设置"
                )
        
        # 更新偏好设置
        update_result = await user_service.update_user_preferences(
            context.user.id,
            "content_preferences",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "内容偏好设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "preferences": update_result.get("preferences")
            },
            message="内容偏好设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新内容偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="内容偏好设置更新失败"
        )


@router.put("/workflow", response_model=Dict[str, Any], summary="更新工作流偏好设置")
async def update_workflow_preferences(
    request: WorkflowPreferencesRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新用户的工作流偏好设置
    
    包括默认工作空间、自动整理、协作模式等。
    """
    try:
        logger.info(f"Frontend API - 更新工作流偏好设置: user_id={context.user.id}")
        
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
                detail="没有提供需要更新的偏好设置"
            )
        
        # 验证设置值
        if "collaboration_mode" in update_data:
            allowed_modes = ["private", "shared", "public"]
            if update_data["collaboration_mode"] not in allowed_modes:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的协作模式设置"
                )
        
        if "backup_frequency" in update_data:
            allowed_frequencies = ["never", "daily", "weekly", "monthly"]
            if update_data["backup_frequency"] not in allowed_frequencies:
                raise HTTPException(
                    status_code=400,
                    detail="不支持的备份频率设置"
                )
        
        # 验证默认工作空间是否存在
        if "default_workspace" in update_data:
            workspace_service = container.get_workspace_service()
            workspace_exists = await workspace_service.check_workspace_access(
                update_data["default_workspace"],
                context.user.id
            )
            if not workspace_exists:
                raise HTTPException(
                    status_code=400,
                    detail="指定的默认工作空间不存在或无权访问"
                )
        
        # 更新偏好设置
        update_result = await user_service.update_user_preferences(
            context.user.id,
            "workflow_preferences",
            update_data
        )
        
        if not update_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=update_result.get("message", "工作流偏好设置更新失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "updated_fields": list(update_data.keys()),
                "preferences": update_result.get("preferences")
            },
            message="工作流偏好设置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新工作流偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="工作流偏好设置更新失败"
        )


@router.post("/reset", response_model=Dict[str, Any], summary="重置偏好设置")
async def reset_preferences(
    category: str = Field(..., description="重置类别: ai, interaction, ui, learning, content, workflow, all"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    重置偏好设置为默认值
    
    可以选择重置特定类别或所有偏好设置。
    """
    try:
        logger.info(f"Frontend API - 重置偏好设置: user_id={context.user.id}, category={category}")
        
        # 验证重置类别
        allowed_categories = ["ai", "interaction", "ui", "learning", "content", "workflow", "all"]
        if category not in allowed_categories:
            raise HTTPException(
                status_code=400,
                detail="不支持的重置类别"
            )
        
        # 获取用户服务
        user_service = container.get_user_service()
        
        # 执行重置
        reset_result = await user_service.reset_user_preferences(
            context.user.id,
            category
        )
        
        if not reset_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=reset_result.get("message", "偏好设置重置失败")
            )
        
        return InternalResponseFormatter.format_success(
            data={
                "reset_category": category,
                "reset_fields": reset_result.get("reset_fields", []),
                "preferences": reset_result.get("preferences")
            },
            message=f"{category}偏好设置已重置为默认值"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 重置偏好设置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="偏好设置重置失败"
        )


@router.get("/recommendations", response_model=Dict[str, Any], summary="获取个性化推荐")
async def get_personalized_recommendations(
    category: Optional[str] = Field(None, description="推荐类别: assistants, content, features"),
    limit: int = Field(10, ge=1, le=50, description="推荐数量"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    基于用户偏好设置获取个性化推荐
    
    返回助手推荐、内容推荐、功能推荐等。
    """
    try:
        logger.info(f"Frontend API - 获取个性化推荐: user_id={context.user.id}")
        
        # 获取推荐服务
        recommendation_service = container.get_recommendation_service()
        
        # 获取用户偏好
        user_preferences = await container.get_user_service().get_user_preferences(context.user.id)
        
        # 生成推荐
        recommendations_result = await recommendation_service.generate_personalized_recommendations(
            user_id=context.user.id,
            category=category,
            preferences=user_preferences,
            limit=limit
        )
        
        return InternalResponseFormatter.format_success(
            data=recommendations_result,
            message="获取个性化推荐成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取个性化推荐失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取个性化推荐失败"
        ) 