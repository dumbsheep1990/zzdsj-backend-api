"""
敏感词管理API模块
提供敏感词的查询、添加、删除等功能
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.utils.sensitive_word_filter import get_sensitive_word_filter, SensitiveWordFilterType

router = APIRouter(prefix="/api/sensitive-words", tags=["敏感词管理"])

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
    """
    filter = get_sensitive_word_filter()
    await filter.initialize()
    
    words = filter.get_sensitive_words()
    
    return {
        "words": words,
        "count": len(words),
        "filter_type": filter.filter_type
    }


@router.post("/add", response_model=BaseResponse)
async def add_sensitive_word(request: SensitiveWordAddRequest):
    """
    添加敏感词
    """
    filter = get_sensitive_word_filter()
    await filter.initialize()
    
    word = request.word.strip()
    if not word:
        raise HTTPException(status_code=400, detail="敏感词不能为空")
    
    success = filter.add_sensitive_word(word)
    
    if success:
        return {
            "success": True,
            "message": f"成功添加敏感词: {word}"
        }
    else:
        return {
            "success": False,
            "message": f"添加敏感词失败，可能已存在: {word}"
        }


@router.post("/remove", response_model=BaseResponse)
async def remove_sensitive_word(request: SensitiveWordRemoveRequest):
    """
    删除敏感词
    """
    filter = get_sensitive_word_filter()
    await filter.initialize()
    
    word = request.word.strip()
    if not word:
        raise HTTPException(status_code=400, detail="敏感词不能为空")
    
    success = filter.remove_sensitive_word(word)
    
    if success:
        return {
            "success": True,
            "message": f"成功删除敏感词: {word}"
        }
    else:
        return {
            "success": False,
            "message": f"删除敏感词失败，可能不存在: {word}"
        }


@router.post("/set-filter-type", response_model=BaseResponse)
async def set_filter_type(request: SensitiveWordFilterTypeRequest):
    """
    设置过滤器类型
    """
    filter = get_sensitive_word_filter()
    await filter.initialize()
    
    success = filter.set_filter_type(request.filter_type)
    
    if success:
        return {
            "success": True,
            "message": f"成功设置过滤器类型为: {request.filter_type}"
        }
    else:
        return {
            "success": False,
            "message": f"设置过滤器类型失败，请检查第三方API配置"
        }


@router.post("/clear-cache", response_model=BaseResponse)
async def clear_cache():
    """
    清空敏感词缓存
    """
    filter = get_sensitive_word_filter()
    filter.clear_cache()
    
    return {
        "success": True,
        "message": "成功清空敏感词缓存"
    }
