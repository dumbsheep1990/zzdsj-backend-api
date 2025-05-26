"""
重排序模型管理 - 前端路由模块
提供重排序模型列表、详情等功能
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Path, Query
import logging
import re

from app.config import settings
from app.api.frontend.responses import ResponseFormatter

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/", summary="获取重排序模型列表")
async def list_rerank_models():
    """获取可用的重排序模型列表"""
    try:
        # 从环境变量中获取模型信息
        models = []
        
        # 添加跨编码器模型
        if getattr(settings, "RERRANK_CROSS_ENCODER_MINIML_ENABLED", True):
            models.append({
                "id": "cross_encoder_miniLM",
                "name": "MiniLM-L6 检索重排序模型",
                "type": "cross_encoder",
                "description": "轻量级英文检索重排序模型",
                "is_local": True,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == "cross_encoder_miniLM"
            })
        
        if getattr(settings, "RERRANK_CROSS_ENCODER_MULTILINGUAL_ENABLED", True):
            models.append({
                "id": "cross_encoder_multilingual",
                "name": "多语言检索重排序模型",
                "type": "cross_encoder",
                "description": "支持中英文的多语言检索重排序模型",
                "is_local": True,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == "cross_encoder_multilingual"
            })
        
        # 添加OpenAI模型
        if getattr(settings, "RERRANK_OPENAI_ENABLED", False):
            models.append({
                "id": "openai_rerank",
                "name": "OpenAI重排序",
                "type": "api",
                "description": "OpenAI重排序API",
                "is_local": False,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == "openai_rerank"
            })
        
        # 添加百度模型
        if getattr(settings, "RERRANK_BAIDU_ENABLED", False):
            models.append({
                "id": "baidu_ernie_rerank",
                "name": "百度文心重排序",
                "type": "api",
                "description": "百度文心一言重排序API",
                "is_local": False,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == "baidu_ernie_rerank"
            })
        
        # 添加智谱模型
        if getattr(settings, "RERRANK_ZHIPU_ENABLED", False):
            models.append({
                "id": "zhipu_rerank",
                "name": "智谱重排序",
                "type": "api",
                "description": "智谱重排序API",
                "is_local": False,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == "zhipu_rerank"
            })
        
        # 添加默认BM25模型
        models.append({
            "id": "default",
            "name": "BM25重排序",
            "type": "default",
            "description": "基于BM25的本地重排序",
            "is_local": True,
            "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == "default" or not getattr(settings, "DEFAULT_RERANK_MODEL", "")
        })
        
        return ResponseFormatter.format_success(
            data={"models": models},
            message="获取重排序模型列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取重排序模型列表失败: {str(e)}")
        return ResponseFormatter.format_error(
            message=f"获取模型列表失败: {str(e)}",
            code=500
        )

@router.get("/{model_id}", summary="获取重排序模型详情")
async def get_rerank_model(model_id: str = Path(..., description="模型ID")):
    """获取特定重排序模型的详细信息"""
    try:
        # 检查模型是否存在
        model_info = None
        
        # 验证跨编码器模型
        if model_id == "cross_encoder_miniLM" and getattr(settings, "RERRANK_CROSS_ENCODER_MINIML_ENABLED", True):
            model_path = getattr(settings, "RERRANK_CROSS_ENCODER_MINIML_PATH", 
                               "cross-encoder/ms-marco-MiniLM-L-6-v2")
            model_info = {
                "id": model_id,
                "name": "MiniLM-L6 检索重排序模型",
                "type": "cross_encoder",
                "description": "轻量级英文检索重排序模型",
                "is_local": True,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == model_id,
                "metadata": {
                    "model_path": model_path,
                    "model_id": "",
                    "has_api_key": False,
                    "supported_languages": ["en"]
                }
            }
        
        elif model_id == "cross_encoder_multilingual" and getattr(settings, "RERRANK_CROSS_ENCODER_MULTILINGUAL_ENABLED", True):
            model_path = getattr(settings, "RERRANK_CROSS_ENCODER_MULTILINGUAL_PATH", 
                               "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
            model_info = {
                "id": model_id,
                "name": "多语言检索重排序模型",
                "type": "cross_encoder",
                "description": "支持中英文的多语言检索重排序模型",
                "is_local": True,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == model_id,
                "metadata": {
                    "model_path": model_path,
                    "model_id": "",
                    "has_api_key": False,
                    "supported_languages": ["zh", "en"]
                }
            }
        
        # 验证OpenAI模型
        elif model_id == "openai_rerank" and getattr(settings, "RERRANK_OPENAI_ENABLED", False):
            model_info = {
                "id": model_id,
                "name": "OpenAI重排序",
                "type": "api",
                "description": "OpenAI重排序API",
                "is_local": False,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == model_id,
                "metadata": {
                    "model_path": "",
                    "model_id": getattr(settings, "RERRANK_OPENAI_MODEL_ID", "text-embedding-3-large"),
                    "has_api_key": bool(getattr(settings, "OPENAI_API_KEY", "")),
                    "supported_languages": ["zh", "en", "es", "fr", "de", "ja", "ko"]
                }
            }
        
        # 验证百度模型
        elif model_id == "baidu_ernie_rerank" and getattr(settings, "RERRANK_BAIDU_ENABLED", False):
            model_info = {
                "id": model_id,
                "name": "百度文心重排序",
                "type": "api",
                "description": "百度文心一言重排序API",
                "is_local": False,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == model_id,
                "metadata": {
                    "model_path": "",
                    "model_id": getattr(settings, "RERRANK_BAIDU_MODEL_ID", "ernie-rerank"),
                    "has_api_key": bool(getattr(settings, "RERRANK_BAIDU_API_KEY", "")),
                    "supported_languages": ["zh", "en"]
                }
            }
        
        # 验证智谱模型
        elif model_id == "zhipu_rerank" and getattr(settings, "RERRANK_ZHIPU_ENABLED", False):
            model_info = {
                "id": model_id,
                "name": "智谱重排序",
                "type": "api",
                "description": "智谱重排序API",
                "is_local": False,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == model_id,
                "metadata": {
                    "model_path": "",
                    "model_id": getattr(settings, "RERRANK_ZHIPU_MODEL_ID", "rerank-8k"),
                    "has_api_key": bool(getattr(settings, "RERRANK_ZHIPU_API_KEY", "")),
                    "supported_languages": ["zh", "en"]
                }
            }
        
        # 验证默认模型
        elif model_id == "default":
            model_info = {
                "id": model_id,
                "name": "BM25重排序",
                "type": "default",
                "description": "基于BM25的本地重排序",
                "is_local": True,
                "is_default": getattr(settings, "DEFAULT_RERANK_MODEL", "") == model_id or not getattr(settings, "DEFAULT_RERANK_MODEL", ""),
                "metadata": {
                    "model_path": "",
                    "model_id": "bm25",
                    "has_api_key": False,
                    "supported_languages": ["zh", "en", "*"]
                }
            }
        
        if not model_info:
            return ResponseFormatter.format_error(
                message=f"找不到模型: {model_id}",
                code=404
            )
        
        return ResponseFormatter.format_success(
            data=model_info,
            message=f"获取模型 {model_id} 详情成功"
        )
        
    except Exception as e:
        logger.error(f"获取重排序模型详情失败: {str(e)}")
        return ResponseFormatter.format_error(
            message=f"获取模型详情失败: {str(e)}",
            code=500
        ) 