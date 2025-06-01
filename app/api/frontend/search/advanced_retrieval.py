"""
高级检索 - 前端路由模块
提供高级检索功能，支持多数据源检索和融合
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field
import logging
from sqlalchemy.orm import Session

from app.services.advanced_retrieval_service import get_advanced_retrieval_service, AdvancedRetrievalConfig, SourceWeight, FusionConfig, RerankConfig
from app.utils.core.database import get_db
from app.api.frontend.responses import ResponseFormatter

router = APIRouter()

logger = logging.getLogger(__name__)

class RetrievalRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="检索查询")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="数据源配置")
    fusion: Optional[Dict[str, Any]] = Field(None, description="融合配置")
    rerank: Optional[Dict[str, Any]] = Field(None, description="重排序配置")
    max_results: Optional[int] = Field(None, description="最大返回结果数")

@router.post("/search", summary="执行高级检索")
async def advanced_search(
    request: RetrievalRequest,
    db: Session = Depends(get_db)
):
    """
    执行高级检索
    
    支持多数据源融合和重排序配置
    """
    try:
        # 获取服务实例
        service = get_advanced_retrieval_service()
        
        # 构建配置
        config = AdvancedRetrievalConfig()
        
        # 设置数据源
        if request.sources:
            config.sources = [SourceWeight(**source) for source in request.sources]
        
        # 设置融合配置
        if request.fusion:
            config.fusion = FusionConfig(**request.fusion)
        
        # 设置重排序配置
        if request.rerank:
            config.rerank = RerankConfig(**request.rerank)
        
        # 设置最大结果数
        if request.max_results:
            config.max_results = request.max_results
        
        # 执行检索
        result = await service.retrieve(request.query, config)
        
        return ResponseFormatter.format_success(
            data=result,
            message="高级检索成功"
        )
        
    except Exception as e:
        logger.error(f"高级检索失败: {str(e)}")
        return ResponseFormatter.format_error(
            message=f"高级检索失败: {str(e)}",
            code=500
        )

@router.get("/config/fusion-strategies", summary="获取可用的融合策略")
async def get_fusion_strategies():
    """获取可用的融合策略列表"""
    try:
        strategies = [
            {
                "id": "weighted_sum",
                "name": "加权求和",
                "description": "对不同来源的分数进行加权求和"
            },
            {
                "id": "reciprocal_rank_fusion",
                "name": "倒数排名融合",
                "description": "基于排名的融合方法，适合不同分数体系"
            },
            {
                "id": "max_score",
                "name": "最大分数",
                "description": "选择每个文档在所有来源中的最高分数"
            },
            {
                "id": "linear_combination",
                "name": "线性组合",
                "description": "对分数进行归一化后线性组合"
            }
        ]
        
        return ResponseFormatter.format_success(
            data={"strategies": strategies},
            message="获取融合策略成功"
        )
        
    except Exception as e:
        logger.error(f"获取融合策略失败: {str(e)}")
        return ResponseFormatter.format_error(
            message=f"获取融合策略失败: {str(e)}",
            code=500
        )

@router.get("/config/rerank-models", summary="获取可用的重排序模型")
async def get_rerank_models():
    """获取可用于高级检索的重排序模型列表"""
    try:
        # 这里可以调用rerank模块的接口
        from app.api.frontend.search.rerank import list_rerank_models
        response = await list_rerank_models()
        
        # 提取数据部分返回
        if response and "data" in response and "models" in response["data"]:
            return ResponseFormatter.format_success(
                data={"models": response["data"]["models"]},
                message="获取重排序模型成功"
            )
        
        # 如果上面调用失败，返回默认模型列表
        default_models = [
            {
                "id": "cross_encoder_multilingual",
                "name": "多语言检索重排序模型",
                "type": "cross_encoder",
                "description": "支持中英文的多语言检索重排序模型"
            },
            {
                "id": "default",
                "name": "BM25重排序",
                "type": "default",
                "description": "基于BM25的本地重排序"
            }
        ]
        
        return ResponseFormatter.format_success(
            data={"models": default_models},
            message="获取重排序模型成功"
        )
        
    except Exception as e:
        logger.error(f"获取重排序模型失败: {str(e)}")
        return ResponseFormatter.format_error(
            message=f"获取重排序模型失败: {str(e)}",
            code=500
        )

@router.post("/analyze", summary="分析检索请求")
async def analyze_retrieval_request(
    request: RetrievalRequest
):
    """
    分析检索请求，返回执行计划
    
    用于调试和优化检索配置
    """
    try:
        # 获取服务实例
        service = get_advanced_retrieval_service()
        
        # 构建配置
        config = AdvancedRetrievalConfig()
        
        # 设置数据源
        if request.sources:
            config.sources = [SourceWeight(**source) for source in request.sources]
        
        # 设置融合配置
        if request.fusion:
            config.fusion = FusionConfig(**request.fusion)
        
        # 设置重排序配置
        if request.rerank:
            config.rerank = RerankConfig(**request.rerank)
        
        # 设置最大结果数
        if request.max_results:
            config.max_results = request.max_results
        
        # 分析执行计划（假设服务有此方法，如果没有可以模拟）
        analysis = {
            "query": request.query,
            "execution_plan": {
                "sources": [{"source_id": s.source_id, "weight": s.weight} for s in config.sources] if config.sources else [],
                "fusion_strategy": config.fusion.strategy if config.fusion else "weighted_sum",
                "rerank_enabled": config.rerank.enabled if config.rerank else False,
                "rerank_model": config.rerank.model_name if config.rerank and config.rerank.enabled else None,
                "max_results": config.max_results or 10
            },
            "estimated_performance": {
                "expected_latency_ms": 150,
                "expected_result_count": min(config.max_results or 10, 50)
            }
        }
        
        return ResponseFormatter.format_success(
            data=analysis,
            message="检索请求分析成功"
        )
        
    except Exception as e:
        logger.error(f"分析检索请求失败: {str(e)}")
        return ResponseFormatter.format_error(
            message=f"分析检索请求失败: {str(e)}",
            code=500
        ) 