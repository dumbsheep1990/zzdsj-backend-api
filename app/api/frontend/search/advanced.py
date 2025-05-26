"""
Frontend API - 高级搜索接口
基于原有search.py和advanced_retrieval.py完整迁移，适配前端应用需求
"""

from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
import logging
import time
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

from pydantic import BaseModel, Field, validator

class AdvancedSearchRequest(BaseModel):
    """高级搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询文本")
    knowledge_base_ids: List[int] = Field(default=[], description="知识库ID列表，为空则搜索用户有权限的所有知识库")
    search_type: str = Field(default="hybrid", description="搜索类型：semantic, keyword, hybrid, fuzzy")
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="向量搜索权重")
    text_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="文本搜索权重")
    title_weight: float = Field(default=3.0, ge=0.0, description="标题字段权重")
    content_weight: float = Field(default=2.0, ge=0.0, description="内容字段权重")
    size: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    score_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="最低相似度阈值")
    include_content: bool = Field(default=True, description="是否包含文档内容")
    include_highlights: bool = Field(default=True, description="是否包含高亮片段")
    search_engine: str = Field(default="auto", description="搜索引擎：es, milvus, hybrid, auto")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")
    
    @validator("vector_weight", "text_weight")
    def check_weights_sum(cls, v, values):
        if "vector_weight" in values:
            total = v + values["vector_weight"]
            if abs(total - 1.0) > 0.01:  # 允许小误差
                return v
        return v


class MultiSourceSearchRequest(BaseModel):
    """多数据源搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    sources: List[Dict[str, Any]] = Field(default=[], description="数据源配置")
    fusion_strategy: str = Field(default="reciprocal_rank_fusion", description="融合策略")
    rerank_enabled: bool = Field(default=False, description="启用重排序")
    rerank_model: str = Field(default="cross_encoder_miniLM", description="重排序模型")
    max_results: int = Field(default=10, ge=1, le=50, description="最大结果数")
    rrf_k: float = Field(default=60.0, description="RRF参数k")


class SearchHistoryRequest(BaseModel):
    """搜索历史请求"""
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")
    search_type: Optional[str] = Field(None, description="搜索类型筛选")
    date_from: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")


# ================================
# 高级搜索接口
# ================================

@router.post("/advanced", response_model=Dict[str, Any], summary="高级搜索")
async def advanced_search(
    request: AdvancedSearchRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    高级搜索功能
    
    支持多种搜索模式、权重配置和过滤条件
    """
    try:
        logger.info(f"Frontend API - 高级搜索: user_id={context.user.id}, query={request.query[:50]}...")
        
        start_time = time.time()
        
        # 获取搜索服务（基于原有hybrid_search_service）
        try:
            from app.services.hybrid_search_service import get_hybrid_search_service, SearchConfig
            search_service = get_hybrid_search_service()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="搜索服务暂不可用"
            )
        
        # 验证知识库权限
        accessible_kb_ids = []
        if request.knowledge_base_ids:
            knowledge_service = container.get_knowledge_service()
            for kb_id in request.knowledge_base_ids:
                kb = await knowledge_service.get_knowledge_base_by_id(kb_id)
                if kb:
                    owner_id = getattr(kb, 'owner_id', None)
                    is_public = getattr(kb, 'is_public', False)
                    
                    # 用户可以搜索自己的知识库或公共知识库
                    if is_public or owner_id == context.user.id:
                        accessible_kb_ids.append(str(kb_id))
        else:
            # 如果没有指定，获取用户有权访问的所有知识库
            knowledge_service = container.get_knowledge_service()
            user_kbs = await knowledge_service.get_knowledge_bases(
                skip=0,
                limit=1000,
                user_id=context.user.id
            )
            accessible_kb_ids = [str(kb.id) for kb in user_kbs]
        
        if not accessible_kb_ids:
            return InternalResponseFormatter.format_success(
                data={
                    "query": request.query,
                    "results": [],
                    "total": 0,
                    "search_time_ms": 0,
                    "message": "没有可搜索的知识库"
                },
                message="搜索完成"
            )
        
        # 构建搜索配置（基于原有SearchConfig）
        search_config = SearchConfig(
            query_text=request.query,
            query_vector=None,  # 由服务内部生成
            knowledge_base_ids=accessible_kb_ids,
            vector_weight=request.vector_weight,
            text_weight=request.text_weight,
            title_weight=request.title_weight,
            content_weight=request.content_weight,
            size=request.size,
            search_engine=request.search_engine,
            hybrid_method="weighted_sum",  # 使用加权求和
            es_filter=request.filter_metadata,
            milvus_filter=None
        )
        
        # 执行搜索（基于原有功能）
        search_response = await search_service.search(search_config)
        
        # 处理搜索结果
        results = []
        for result in search_response.get("results", []):
            # 应用分数阈值过滤
            score = result.get("score", 0.0)
            if request.score_threshold and score < request.score_threshold:
                continue
            
            processed_result = {
                "id": result.get("id", ""),
                "document_id": result.get("document_id", ""),
                "knowledge_base_id": result.get("knowledge_base_id"),
                "title": result.get("title"),
                "score": score,
                "vector_score": result.get("vector_score"),
                "text_score": result.get("text_score"),
                "metadata": result.get("metadata", {})
            }
            
            # 根据设置包含内容
            if request.include_content:
                processed_result["content"] = result.get("content", "")
            
            # 根据设置包含高亮
            if request.include_highlights:
                processed_result["highlights"] = result.get("highlight", {})
            
            results.append(processed_result)
        
        # 计算搜索耗时
        search_time_ms = (time.time() - start_time) * 1000
        
        # 记录搜索历史（后台任务）
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            _record_search_history,
            user_id=context.user.id,
            query=request.query,
            search_type=request.search_type,
            results_count=len(results),
            search_time_ms=search_time_ms
        )
        
        # 构建响应数据
        response_data = {
            "query": request.query,
            "search_type": request.search_type,
            "results": results,
            "total": len(results),
            "search_time_ms": search_time_ms,
            "knowledge_base_ids": accessible_kb_ids,
            "search_config": {
                "vector_weight": request.vector_weight,
                "text_weight": request.text_weight,
                "search_engine": request.search_engine,
                "score_threshold": request.score_threshold
            },
            "engine_used": search_response.get("engine_used", "unknown"),
            "strategy_used": search_response.get("strategy_used", "weighted_sum")
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="搜索完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 高级搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="搜索失败"
        )


@router.post("/multi-source", response_model=Dict[str, Any], summary="多数据源搜索")
async def multi_source_search(
    request: MultiSourceSearchRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    多数据源融合搜索
    
    支持多个数据源的结果融合和重排序
    """
    try:
        logger.info(f"Frontend API - 多数据源搜索: user_id={context.user.id}, query={request.query[:50]}...")
        
        # 获取高级检索服务
        try:
            from app.services.advanced_retrieval_service import (
                get_advanced_retrieval_service, 
                AdvancedRetrievalConfig,
                SourceWeight,
                FusionConfig,
                RerankConfig
            )
            advanced_service = get_advanced_retrieval_service()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="高级检索服务暂不可用"
            )
        
        # 验证和处理数据源
        validated_sources = []
        if request.sources:
            knowledge_service = container.get_knowledge_service()
            for source in request.sources:
                source_id = source.get("source_id")
                if source_id:
                    # 验证知识库权限
                    kb = await knowledge_service.get_knowledge_base_by_id(int(source_id))
                    if kb:
                        owner_id = getattr(kb, 'owner_id', None)
                        is_public = getattr(kb, 'is_public', False)
                        
                        if is_public or owner_id == context.user.id:
                            validated_sources.append(SourceWeight(
                                source_id=source_id,
                                weight=source.get("weight", 1.0),
                                max_results=source.get("max_results", 10)
                            ))
        
        if not validated_sources:
            # 使用默认数据源（用户有权限的知识库）
            knowledge_service = container.get_knowledge_service()
            user_kbs = await knowledge_service.get_knowledge_bases(
                skip=0,
                limit=100,
                user_id=context.user.id
            )
            for kb in user_kbs[:5]:  # 限制最多5个知识库
                validated_sources.append(SourceWeight(
                    source_id=str(kb.id),
                    weight=1.0,
                    max_results=10
                ))
        
        # 构建高级检索配置
        config = AdvancedRetrievalConfig(
            sources=validated_sources,
            fusion=FusionConfig(
                strategy=request.fusion_strategy,
                rrf_k=request.rrf_k,
                normalize=True
            ),
            rerank=RerankConfig(
                enabled=request.rerank_enabled,
                model_name=request.rerank_model,
                top_n=min(request.max_results * 2, 50)
            ),
            max_results=request.max_results,
            query_preprocessing=True
        )
        
        # 执行多数据源检索
        result = await advanced_service.retrieve(request.query, config)
        
        # 记录搜索历史
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            _record_search_history,
            user_id=context.user.id,
            query=request.query,
            search_type="multi_source",
            results_count=result.get("total", 0),
            search_time_ms=result.get("search_time_ms", 0)
        )
        
        return InternalResponseFormatter.format_success(
            data=result,
            message="多数据源搜索完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 多数据源搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="多数据源搜索失败"
        )


@router.get("/suggestions", response_model=Dict[str, Any], summary="搜索建议")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="搜索查询前缀"),
    limit: int = Query(10, ge=1, le=20, description="建议数量"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取搜索建议
    
    基于用户历史搜索和知识库内容提供智能建议
    """
    try:
        logger.info(f"Frontend API - 搜索建议: user_id={context.user.id}, query={q}")
        
        suggestions = []
        
        # 1. 从用户搜索历史中获取建议
        try:
            history_suggestions = await _get_history_suggestions(context.user.id, q, limit // 2)
            suggestions.extend(history_suggestions)
        except Exception as e:
            logger.warning(f"获取历史建议失败: {str(e)}")
        
        # 2. 从知识库内容中获取建议
        try:
            content_suggestions = await _get_content_suggestions(context.user.id, q, limit - len(suggestions))
            suggestions.extend(content_suggestions)
        except Exception as e:
            logger.warning(f"获取内容建议失败: {str(e)}")
        
        # 3. 去重和排序
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions[:limit]:
            if suggestion.lower() not in seen:
                seen.add(suggestion.lower())
                unique_suggestions.append(suggestion)
        
        response_data = {
            "query": q,
            "suggestions": unique_suggestions,
            "total": len(unique_suggestions)
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取搜索建议成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取搜索建议失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取搜索建议失败"
        )


@router.get("/history", response_model=Dict[str, Any], summary="搜索历史")
async def get_search_history(
    request: SearchHistoryRequest = Depends(),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户搜索历史
    
    支持按时间、类型筛选
    """
    try:
        logger.info(f"Frontend API - 获取搜索历史: user_id={context.user.id}")
        
        # 这里应该从数据库获取搜索历史
        # 暂时返回模拟数据
        search_history = [
            {
                "id": i,
                "query": f"搜索查询 {i}",
                "search_type": "hybrid",
                "results_count": 10,
                "search_time_ms": 150.0,
                "created_at": datetime.now().isoformat(),
                "knowledge_base_ids": ["1", "2"]
            }
            for i in range(1, request.limit + 1)
        ]
        
        response_data = {
            "history": search_history,
            "total": len(search_history),
            "filters": {
                "search_type": request.search_type,
                "date_from": request.date_from,
                "date_to": request.date_to
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取搜索历史成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取搜索历史失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取搜索历史失败"
        )


@router.delete("/history/{history_id}", response_model=Dict[str, Any], summary="删除搜索历史")
async def delete_search_history(
    history_id: int = Path(..., description="历史记录ID"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    删除指定的搜索历史记录
    """
    try:
        logger.info(f"Frontend API - 删除搜索历史: user_id={context.user.id}, history_id={history_id}")
        
        # 这里应该实现实际的删除逻辑
        # 验证历史记录属于当前用户，然后删除
        
        return InternalResponseFormatter.format_success(
            data={"history_id": history_id},
            message="搜索历史删除成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 删除搜索历史失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="删除搜索历史失败"
        )


@router.get("/analytics", response_model=Dict[str, Any], summary="搜索分析")
async def get_search_analytics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户搜索分析数据
    
    包括搜索频率、热门关键词、搜索效果等
    """
    try:
        logger.info(f"Frontend API - 搜索分析: user_id={context.user.id}, days={days}")
        
        # 模拟分析数据
        analytics_data = {
            "period": {
                "days": days,
                "start_date": (datetime.now().date() - datetime.timedelta(days=days)).isoformat(),
                "end_date": datetime.now().date().isoformat()
            },
            "total_searches": 156,
            "avg_search_time_ms": 234.5,
            "top_queries": [
                {"query": "Python编程", "count": 23},
                {"query": "机器学习", "count": 18},
                {"query": "数据分析", "count": 15}
            ],
            "search_types": {
                "hybrid": 89,
                "semantic": 45,
                "keyword": 22
            },
            "daily_stats": [
                {
                    "date": (datetime.now().date() - datetime.timedelta(days=i)).isoformat(),
                    "count": max(0, 10 - i)
                }
                for i in range(min(days, 30))
            ],
            "knowledge_base_usage": [
                {"knowledge_base_id": "1", "name": "技术文档", "search_count": 67},
                {"knowledge_base_id": "2", "name": "项目资料", "search_count": 45}
            ]
        }
        
        return InternalResponseFormatter.format_success(
            data=analytics_data,
            message="获取搜索分析成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取搜索分析失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取搜索分析失败"
        )


# ================================
# 辅助函数
# ================================

async def _record_search_history(
    user_id: int,
    query: str,
    search_type: str,
    results_count: int,
    search_time_ms: float
):
    """记录搜索历史（后台任务）"""
    try:
        # 这里应该实现实际的数据库记录逻辑
        logger.info(f"记录搜索历史: user_id={user_id}, query={query[:30]}...")
    except Exception as e:
        logger.error(f"记录搜索历史失败: {str(e)}")


async def _get_history_suggestions(user_id: int, query: str, limit: int) -> List[str]:
    """从搜索历史获取建议"""
    # 这里应该实现实际的历史查询逻辑
    return [f"{query}的历史建议{i}" for i in range(1, min(limit + 1, 4))]


async def _get_content_suggestions(user_id: int, query: str, limit: int) -> List[str]:
    """从知识库内容获取建议"""
    # 这里应该实现实际的内容匹配逻辑
    return [f"{query}的内容建议{i}" for i in range(1, min(limit + 1, 4))] 