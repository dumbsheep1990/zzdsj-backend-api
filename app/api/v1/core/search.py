"""
V1 API - 智能搜索接口
提供多种搜索功能，专门为第三方开发者设计
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
import logging
from enum import Enum

from app.api.v1.dependencies import (
    V1ServiceContainer, 
    V1Context, 
    V1DataFilter,
    get_v1_service_container,
    get_v1_context,
    APIKey
)
from app.api.shared.responses import ExternalResponseFormatter
from app.api.shared.validators import ValidatorFactory

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 枚举和常量
# ================================

class SearchType(str, Enum):
    """搜索类型枚举"""
    SEMANTIC = "semantic"      # 语义搜索
    KEYWORD = "keyword"        # 关键词搜索
    HYBRID = "hybrid"          # 混合搜索
    FUZZY = "fuzzy"           # 模糊搜索


class SortOrder(str, Enum):
    """排序方向枚举"""
    ASC = "asc"
    DESC = "desc"


# ================================
# 请求/响应模型
# ================================

class SearchRequest(BaseModel):
    """智能搜索请求模型"""
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    search_type: SearchType = Field(default=SearchType.SEMANTIC, description="搜索类型")
    sources: Optional[List[str]] = Field(None, description="搜索源（助手、知识库等）")
    filters: Optional[Dict[str, Any]] = Field(None, description="搜索过滤条件")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序方向")
    limit: int = Field(default=20, ge=1, le=100, description="返回结果数量")
    offset: int = Field(default=0, ge=0, description="偏移量")
    include_highlights: bool = Field(default=True, description="是否包含高亮信息")


class UniversalSearchRequest(BaseModel):
    """通用搜索请求模型"""
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    categories: Optional[List[str]] = Field(None, description="搜索分类")
    limit: int = Field(default=30, ge=1, le=100, description="返回结果数量")
    include_suggestions: bool = Field(default=True, description="是否包含搜索建议")


class SuggestionsRequest(BaseModel):
    """搜索建议请求模型"""
    query: str = Field(..., min_length=1, max_length=100, description="查询文本")
    limit: int = Field(default=10, ge=1, le=20, description="建议数量")
    source: Optional[str] = Field(None, description="建议来源")


# ================================
# API接口实现
# ================================

@router.post("/search", response_model=Dict[str, Any], summary="智能搜索")
async def intelligent_search(
    request: SearchRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    智能搜索功能
    
    支持语义搜索、关键词搜索、混合搜索等多种搜索模式。
    """
    try:
        logger.info(f"V1 API - 智能搜索: query={request.query[:50]}..., type={request.search_type}")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 构建搜索参数
        search_params = {
            "query": request.query,
            "search_type": request.search_type.value,
            "sources": request.sources,
            "filters": request.filters or {},
            "sort_by": request.sort_by,
            "sort_order": request.sort_order.value,
            "limit": request.limit,
            "offset": request.offset,
            "include_highlights": request.include_highlights,
            "api_mode": "v1_external"
        }
        
        # 执行搜索
        search_results = await search_service.intelligent_search(search_params)
        
        # 过滤搜索结果
        filtered_results = []
        for result in search_results.get("items", []):
            # 根据结果类型进行不同的过滤
            if result.get("type") == "assistant":
                filtered_result = V1DataFilter.filter_assistant_data(result)
            elif result.get("type") == "knowledge":
                filtered_result = V1DataFilter.filter_knowledge_data(result)
            elif result.get("type") == "chat":
                filtered_result = V1DataFilter.filter_chat_data(result)
            else:
                # 通用过滤
                filtered_result = {
                    key: value for key, value in result.items()
                    if key not in ["internal_id", "system_data", "private_info"]
                }
            
            filtered_results.append(filtered_result)
        
        # 构建响应
        response_data = {
            "query": request.query,
            "search_type": request.search_type.value,
            "results": filtered_results,
            "total": search_results.get("total", 0),
            "limit": request.limit,
            "offset": request.offset,
            "has_more": request.offset + request.limit < search_results.get("total", 0),
            "search_time": search_results.get("search_time", 0),
            "suggestions": search_results.get("suggestions", []) if request.include_highlights else []
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="搜索完成"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 智能搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="搜索失败"
        )


@router.post("/universal", response_model=Dict[str, Any], summary="通用搜索")
async def universal_search(
    request: UniversalSearchRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    通用搜索功能
    
    在所有可用资源中进行搜索，包括助手、知识库、对话等。
    """
    try:
        logger.info(f"V1 API - 通用搜索: query={request.query[:50]}...")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 构建搜索参数
        search_params = {
            "query": request.query,
            "categories": request.categories,
            "limit": request.limit,
            "include_suggestions": request.include_suggestions,
            "api_mode": "v1_external"
        }
        
        # 执行通用搜索
        search_results = await search_service.universal_search(search_params)
        
        # 按分类过滤结果
        categorized_results = {}
        for category, items in search_results.get("categorized_results", {}).items():
            filtered_items = []
            for item in items:
                if category == "assistants":
                    filtered_item = V1DataFilter.filter_assistant_data(item)
                elif category == "knowledge_bases":
                    filtered_item = V1DataFilter.filter_knowledge_data(item)
                elif category == "conversations":
                    filtered_item = V1DataFilter.filter_chat_data(item)
                else:
                    filtered_item = item
                
                filtered_items.append(filtered_item)
            
            categorized_results[category] = filtered_items
        
        # 构建响应
        response_data = {
            "query": request.query,
            "results": categorized_results,
            "total": search_results.get("total", 0),
            "categories": list(categorized_results.keys()),
            "search_time": search_results.get("search_time", 0)
        }
        
        # 添加搜索建议
        if request.include_suggestions:
            response_data["suggestions"] = search_results.get("suggestions", [])
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="通用搜索完成"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 通用搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="通用搜索失败"
        )


@router.get("/suggestions", response_model=Dict[str, Any], summary="获取搜索建议")
async def get_search_suggestions(
    query: str = Query(..., min_length=1, max_length=100, description="查询文本"),
    limit: int = Query(10, ge=1, le=20, description="建议数量"),
    source: Optional[str] = Query(None, description="建议来源"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取搜索建议
    
    基于输入文本提供搜索建议和自动补全。
    """
    try:
        logger.info(f"V1 API - 获取搜索建议: query={query}")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 构建建议参数
        suggestion_params = {
            "query": query,
            "limit": limit,
            "source": source,
            "api_mode": "v1_external"
        }
        
        # 获取搜索建议
        suggestions = await search_service.get_search_suggestions(suggestion_params)
        
        return ExternalResponseFormatter.format_success(
            data={
                "query": query,
                "suggestions": suggestions.get("suggestions", []),
                "count": len(suggestions.get("suggestions", [])),
                "source": source
            },
            message="获取搜索建议成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取搜索建议失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取搜索建议失败"
        )


@router.get("/trending", response_model=Dict[str, Any], summary="获取热门搜索")
async def get_trending_searches(
    category: Optional[str] = Query(None, description="搜索分类"),
    time_range: str = Query("24h", description="时间范围: 1h, 24h, 7d, 30d"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取热门搜索词
    
    返回一段时间内的热门搜索词和趋势。
    """
    try:
        logger.info(f"V1 API - 获取热门搜索: category={category}, time_range={time_range}")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 构建查询参数
        trending_params = {
            "category": category,
            "time_range": time_range,
            "limit": limit,
            "api_mode": "v1_external"
        }
        
        # 获取热门搜索
        trending_data = await search_service.get_trending_searches(trending_params)
        
        return ExternalResponseFormatter.format_success(
            data={
                "trending_searches": trending_data.get("trending", []),
                "category": category,
                "time_range": time_range,
                "generated_at": trending_data.get("generated_at"),
                "total": len(trending_data.get("trending", []))
            },
            message="获取热门搜索成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取热门搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取热门搜索失败"
        )


@router.post("/semantic", response_model=Dict[str, Any], summary="语义搜索")
async def semantic_search(
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询"),
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="相似度阈值"),
    domains: Optional[List[str]] = Field(None, description="搜索领域"),
    limit: int = Field(default=20, ge=1, le=50, description="返回结果数量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    语义搜索
    
    使用语义理解技术进行深度搜索。
    """
    try:
        logger.info(f"V1 API - 语义搜索: query={query[:50]}...")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 构建语义搜索参数
        semantic_params = {
            "query": query,
            "similarity_threshold": similarity_threshold,
            "domains": domains,
            "limit": limit,
            "api_mode": "v1_external"
        }
        
        # 执行语义搜索
        results = await search_service.semantic_search(semantic_params)
        
        # 过滤结果
        filtered_results = []
        for result in results.get("items", []):
            filtered_result = V1DataFilter.filter_knowledge_data(result)
            filtered_results.append(filtered_result)
        
        return ExternalResponseFormatter.format_success(
            data={
                "query": query,
                "results": filtered_results,
                "similarity_threshold": similarity_threshold,
                "total": len(filtered_results),
                "processing_time": results.get("processing_time", 0)
            },
            message="语义搜索完成"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 语义搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="语义搜索失败"
        )


@router.get("/history", response_model=Dict[str, Any], summary="搜索历史")
async def get_search_history(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    search_type: Optional[str] = Query(None, description="搜索类型筛选"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取搜索历史
    
    返回当前API用户的搜索历史记录。
    """
    try:
        logger.info("V1 API - 获取搜索历史")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 构建查询参数
        history_params = {
            "limit": limit,
            "offset": offset,
            "search_type": search_type,
            "api_mode": "v1_external"
        }
        
        # 获取搜索历史
        history_data = await search_service.get_search_history(history_params)
        
        # 过滤历史数据（移除敏感信息）
        filtered_history = []
        for item in history_data.get("items", []):
            filtered_item = {
                "query": item.get("query"),
                "search_type": item.get("search_type"),
                "timestamp": item.get("timestamp"),
                "results_count": item.get("results_count"),
                "search_time": item.get("search_time")
            }
            filtered_history.append(filtered_item)
        
        return ExternalResponseFormatter.format_success(
            data={
                "history": filtered_history,
                "total": history_data.get("total", 0),
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < history_data.get("total", 0)
            },
            message="获取搜索历史成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取搜索历史失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取搜索历史失败"
        )


@router.get("/categories", response_model=Dict[str, Any], summary="获取搜索分类")
async def get_search_categories(
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取搜索分类
    
    返回所有可用的搜索分类和说明。
    """
    try:
        logger.info("V1 API - 获取搜索分类")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 获取搜索分类
        categories = await search_service.get_search_categories(api_mode="v1_external")
        
        return ExternalResponseFormatter.format_success(
            data={"categories": categories},
            message="获取搜索分类成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取搜索分类失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取搜索分类失败"
        ) 