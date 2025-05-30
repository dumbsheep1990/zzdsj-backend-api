"""
敏感词管理API模块
提供敏感词的查询、添加、删除等功能
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from app.utils.sensitive_word_filter import get_sensitive_word_filter, SensitiveWordFilterType
from app.api.frontend.dependencies import ResponseFormatter, get_current_user, require_permission

router = APIRouter(prefix="/api/frontend/system/sensitive-words", tags=["敏感词管理"])

class SensitiveWordResponse(BaseModel):
    """敏感词响应模型"""
    words: List[str] = Field(..., description="敏感词列表")
    count: int = Field(..., description="敏感词数量")
    filter_type: str = Field(..., description="过滤器类型")


class SensitiveWordAddRequest(BaseModel):
    """添加敏感词请求模型"""
    word: str = Field(..., description="要添加的敏感词")


class SensitiveWordRemoveRequest(BaseModel):
    """删除敏感词请求模型"""
    word: str = Field(..., description="要删除的敏感词")


class SensitiveWordFilterTypeRequest(BaseModel):
    """设置过滤器类型请求模型"""
    filter_type: SensitiveWordFilterType = Field(..., description="过滤器类型")


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")


@router.get("/", response_model=SensitiveWordResponse)
async def get_sensitive_words():
    """
    获取所有敏感词
    
    返回当前系统中的敏感词列表、数量和过滤器类型
    """
    filter_instance = get_sensitive_word_filter()
    words = filter_instance.get_words()
    filter_type = filter_instance.get_filter_type()
    
    return ResponseFormatter.format_success({
        "words": words,
        "count": len(words),
        "filter_type": filter_type.value
    })


@router.post("/add", response_model=BaseResponse)
async def add_sensitive_word(
    request: SensitiveWordAddRequest,
    current_user = Depends(require_permission("system:sensitive_word:write"))
):
    """
    添加敏感词
    
    - **word**: 要添加的敏感词
    
    需要敏感词管理权限
    """
    filter_instance = get_sensitive_word_filter()
    word = request.word.strip()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="敏感词不能为空"
        )
    
    # 检查敏感词是否已存在
    words = filter_instance.get_words()
    if word in words:
        return ResponseFormatter.format_success({
            "success": False,
            "message": f"敏感词 '{word}' 已存在"
        })
    
    # 添加敏感词
    filter_instance.add_word(word)
    
    return ResponseFormatter.format_success({
        "success": True,
        "message": f"敏感词 '{word}' 添加成功"
    })


@router.post("/remove", response_model=BaseResponse)
async def remove_sensitive_word(
    request: SensitiveWordRemoveRequest,
    current_user = Depends(require_permission("system:sensitive_word:write"))
):
    """
    删除敏感词
    
    - **word**: 要删除的敏感词
    
    需要敏感词管理权限
    """
    filter_instance = get_sensitive_word_filter()
    word = request.word.strip()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="敏感词不能为空"
        )
    
    # 检查敏感词是否存在
    words = filter_instance.get_words()
    if word not in words:
        return ResponseFormatter.format_success({
            "success": False,
            "message": f"敏感词 '{word}' 不存在"
        })
    
    # 删除敏感词
    filter_instance.remove_word(word)
    
    return ResponseFormatter.format_success({
        "success": True,
        "message": f"敏感词 '{word}' 删除成功"
    })


@router.post("/set-filter-type", response_model=BaseResponse)
async def set_filter_type(
    request: SensitiveWordFilterTypeRequest,
    current_user = Depends(require_permission("system:sensitive_word:write"))
):
    """
    设置过滤器类型
    
    - **filter_type**: 过滤器类型，可选值为：
      - BLOCK: 完全阻止含有敏感词的内容
      - REPLACE: 将敏感词替换为 * 号
      - WARN: 仅警告，不阻止内容
    
    需要敏感词管理权限
    """
    filter_instance = get_sensitive_word_filter()
    
    try:
        filter_instance.set_filter_type(request.filter_type)
        return ResponseFormatter.format_success({
            "success": True,
            "message": f"过滤器类型设置为 '{request.filter_type.value}' 成功"
        })
    except Exception as e:
        return ResponseFormatter.format_success({
            "success": False,
            "message": f"设置过滤器类型失败: {str(e)}"
        })


@router.post("/clear-cache", response_model=BaseResponse)
async def clear_cache(
    current_user = Depends(require_permission("system:sensitive_word:admin"))
):
    """
    清空敏感词缓存
    
    需要敏感词管理员权限
    """
    filter_instance = get_sensitive_word_filter()
    
    try:
        filter_instance.clear_cache()
        return ResponseFormatter.format_success({
            "success": True,
            "message": "敏感词缓存清空成功"
        })
    except Exception as e:
        return ResponseFormatter.format_success({
            "success": False,
            "message": f"清空敏感词缓存失败: {str(e)}"
        })
