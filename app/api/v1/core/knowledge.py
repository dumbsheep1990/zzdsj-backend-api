"""
V1 API - 知识库查询接口
提供只读的知识查询功能，专门为第三方开发者设计
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import logging

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
# 请求/响应模型
# ================================

class KnowledgeQueryRequest(BaseModel):
    """知识库查询请求模型"""
    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    knowledge_base_id: Optional[str] = Field(None, description="指定知识库ID（可选）")
    limit: int = Field(default=10, ge=1, le=50, description="返回结果数量")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="相似度阈值")
    include_metadata: bool = Field(default=True, description="是否包含元数据")


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求模型"""
    query: str = Field(..., min_length=1, max_length=500, description="搜索文本")
    search_type: str = Field(default="semantic", description="搜索类型: semantic, keyword, hybrid")
    knowledge_bases: Optional[List[str]] = Field(None, description="指定知识库ID列表")
    filters: Optional[Dict[str, Any]] = Field(None, description="搜索过滤条件")
    limit: int = Field(default=20, ge=1, le=100, description="返回结果数量")


class DocumentQueryRequest(BaseModel):
    """文档查询请求模型"""
    document_id: str = Field(..., description="文档ID")
    include_content: bool = Field(default=True, description="是否包含文档内容")
    include_metadata: bool = Field(default=True, description="是否包含元数据")


# ================================
# API接口实现
# ================================

@router.post("/query", response_model=Dict[str, Any], summary="查询知识库")
async def query_knowledge(
    request: KnowledgeQueryRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    查询知识库内容
    
    使用语义搜索从知识库中查找相关信息。
    """
    try:
        logger.info(f"V1 API - 查询知识库: query={request.query[:50]}...")
        
        # 数据验证
        validated_data = ValidatorFactory.validate_data("v1_knowledge_query", {
            "query": request.query,
            "knowledge_base_id": request.knowledge_base_id,
            "limit": request.limit
        })
        
        # 获取知识库服务
        knowledge_service = container.get_knowledge_service()
        
        # 构建查询参数
        query_params = {
            "query": validated_data["query"],
            "knowledge_base_id": request.knowledge_base_id,
            "limit": request.limit,
            "similarity_threshold": request.similarity_threshold,
            "include_metadata": request.include_metadata,
            "api_mode": "v1_external"
        }
        
        # 执行查询
        results = await knowledge_service.query_knowledge(query_params)
        
        # 过滤结果数据
        filtered_results = []
        for result in results.get("items", []):
            filtered_result = V1DataFilter.filter_knowledge_data(result)
            filtered_results.append(filtered_result)
        
        # 构建响应
        response_data = {
            "query": request.query,
            "results": filtered_results,
            "total": len(filtered_results),
            "knowledge_base_id": request.knowledge_base_id,
            "similarity_threshold": request.similarity_threshold,
            "processing_time": results.get("processing_time", 0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="知识库查询成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 知识库查询失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="知识库查询失败"
        )


@router.post("/search", response_model=Dict[str, Any], summary="搜索知识库")
async def search_knowledge(
    request: KnowledgeSearchRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    搜索知识库内容
    
    支持语义搜索、关键词搜索和混合搜索。
    """
    try:
        logger.info(f"V1 API - 搜索知识库: query={request.query[:50]}..., type={request.search_type}")
        
        # 获取搜索服务
        search_service = container.get_search_service()
        
        # 构建搜索参数
        search_params = {
            "query": request.query,
            "search_type": request.search_type,
            "knowledge_bases": request.knowledge_bases,
            "filters": request.filters or {},
            "limit": request.limit,
            "api_mode": "v1_external"
        }
        
        # 执行搜索
        results = await search_service.search_knowledge(search_params)
        
        # 过滤搜索结果
        filtered_results = []
        for result in results.get("items", []):
            filtered_result = V1DataFilter.filter_knowledge_data(result)
            filtered_results.append(filtered_result)
        
        # 构建响应
        response_data = {
            "query": request.query,
            "search_type": request.search_type,
            "results": filtered_results,
            "total": results.get("total", 0),
            "knowledge_bases": request.knowledge_bases,
            "processing_time": results.get("processing_time", 0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="知识库搜索成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 知识库搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="知识库搜索失败"
        )


@router.get("/knowledge-bases", response_model=Dict[str, Any], summary="获取知识库列表")
async def list_knowledge_bases(
    is_public: bool = Query(True, description="是否只显示公开知识库"),
    category: Optional[str] = Query(None, description="知识库分类"),
    limit: int = Query(20, ge=1, le=50, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取可用的知识库列表
    
    返回第三方开发者可以查询的知识库信息。
    """
    try:
        logger.info(f"V1 API - 获取知识库列表: is_public={is_public}, category={category}")
        
        # 获取知识库服务
        knowledge_service = container.get_knowledge_service()
        
        # 构建查询参数
        query_params = {
            "is_public": is_public,
            "category": category,
            "limit": limit,
            "offset": offset,
            "api_mode": "v1_external"
        }
        
        # 查询知识库列表
        knowledge_bases_data = await knowledge_service.list_public_knowledge_bases(query_params)
        
        # 过滤知识库数据
        filtered_knowledge_bases = []
        for kb in knowledge_bases_data.get("items", []):
            filtered_kb = V1DataFilter.filter_knowledge_data(kb)
            filtered_knowledge_bases.append(filtered_kb)
        
        # 构建响应
        response_data = {
            "knowledge_bases": filtered_knowledge_bases,
            "total": knowledge_bases_data.get("total", 0),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < knowledge_bases_data.get("total", 0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="获取知识库列表成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取知识库列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取知识库列表失败"
        )


@router.get("/knowledge-bases/{knowledge_base_id}", response_model=Dict[str, Any], summary="获取知识库详情")
async def get_knowledge_base(
    knowledge_base_id: str,
    include_stats: bool = Query(False, description="是否包含统计信息"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取指定知识库的详细信息
    
    返回知识库的基本信息、描述和统计数据。
    """
    try:
        logger.info(f"V1 API - 获取知识库详情: knowledge_base_id={knowledge_base_id}")
        
        # 获取知识库服务
        knowledge_service = container.get_knowledge_service()
        
        # 查询知识库详情
        kb_data = await knowledge_service.get_knowledge_base_public_info(
            knowledge_base_id, 
            include_stats=include_stats,
            api_mode="v1_external"
        )
        
        if not kb_data:
            raise HTTPException(
                status_code=404,
                detail="知识库不存在或不可访问"
            )
        
        # 过滤知识库数据
        filtered_kb = V1DataFilter.filter_knowledge_data(kb_data)
        
        return ExternalResponseFormatter.format_success(
            data=filtered_kb,
            message="获取知识库详情成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取知识库详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取知识库详情失败"
        )


@router.get("/documents/{document_id}", response_model=Dict[str, Any], summary="获取文档详情")
async def get_document(
    document_id: str,
    include_content: bool = Query(True, description="是否包含文档内容"),
    include_metadata: bool = Query(True, description="是否包含元数据"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取指定文档的详细信息
    
    返回文档的内容、元数据和相关信息。
    """
    try:
        logger.info(f"V1 API - 获取文档详情: document_id={document_id}")
        
        # 获取知识库服务
        knowledge_service = container.get_knowledge_service()
        
        # 查询文档详情
        doc_data = await knowledge_service.get_document_public_info(
            document_id,
            include_content=include_content,
            include_metadata=include_metadata,
            api_mode="v1_external"
        )
        
        if not doc_data:
            raise HTTPException(
                status_code=404,
                detail="文档不存在或不可访问"
            )
        
        # 过滤文档数据
        filtered_doc = V1DataFilter.filter_knowledge_data(doc_data)
        
        return ExternalResponseFormatter.format_success(
            data=filtered_doc,
            message="获取文档详情成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取文档详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取文档详情失败"
        )


@router.get("/knowledge-bases/{knowledge_base_id}/documents", response_model=Dict[str, Any], summary="获取知识库文档列表")
async def list_knowledge_base_documents(
    knowledge_base_id: str,
    document_type: Optional[str] = Query(None, description="文档类型筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取指定知识库的文档列表
    
    返回知识库中的文档信息，支持按类型筛选。
    """
    try:
        logger.info(f"V1 API - 获取知识库文档列表: knowledge_base_id={knowledge_base_id}")
        
        # 获取知识库服务
        knowledge_service = container.get_knowledge_service()
        
        # 构建查询参数
        query_params = {
            "knowledge_base_id": knowledge_base_id,
            "document_type": document_type,
            "limit": limit,
            "offset": offset,
            "api_mode": "v1_external"
        }
        
        # 查询文档列表
        documents_data = await knowledge_service.list_knowledge_base_documents(query_params)
        
        if not documents_data:
            raise HTTPException(
                status_code=404,
                detail="知识库不存在或不可访问"
            )
        
        # 过滤文档数据
        filtered_documents = []
        for doc in documents_data.get("items", []):
            filtered_doc = V1DataFilter.filter_knowledge_data(doc)
            filtered_documents.append(filtered_doc)
        
        # 构建响应
        response_data = {
            "knowledge_base_id": knowledge_base_id,
            "documents": filtered_documents,
            "total": documents_data.get("total", 0),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < documents_data.get("total", 0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="获取文档列表成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取文档列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取文档列表失败"
        )


@router.get("/categories", response_model=Dict[str, Any], summary="获取知识库分类")
async def get_knowledge_base_categories(
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取知识库分类列表
    
    返回所有可用的知识库分类和统计信息。
    """
    try:
        logger.info("V1 API - 获取知识库分类")
        
        # 获取知识库服务
        knowledge_service = container.get_knowledge_service()
        
        # 查询分类信息
        categories = await knowledge_service.get_knowledge_base_categories(api_mode="v1_external")
        
        return ExternalResponseFormatter.format_success(
            data={"categories": categories},
            message="获取知识库分类成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取知识库分类失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取知识库分类失败"
        )


@router.post("/recommend", response_model=Dict[str, Any], summary="知识推荐")
async def recommend_knowledge(
    query: str = Field(..., min_length=1, max_length=500, description="查询文本"),
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息"),
    limit: int = Field(default=10, ge=1, le=20, description="推荐数量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context_obj: V1Context = Depends(get_v1_context)
):
    """
    基于查询内容推荐相关知识
    
    使用AI技术推荐相关的知识内容和文档。
    """
    try:
        logger.info(f"V1 API - 知识推荐: query={query[:50]}...")
        
        # 获取知识库服务
        knowledge_service = container.get_knowledge_service()
        
        # 构建推荐参数
        recommend_params = {
            "query": query,
            "context": context or {},
            "limit": limit,
            "api_mode": "v1_external"
        }
        
        # 获取推荐结果
        recommendations = await knowledge_service.recommend_knowledge(recommend_params)
        
        # 过滤推荐数据
        filtered_recommendations = []
        for rec in recommendations.get("items", []):
            filtered_rec = V1DataFilter.filter_knowledge_data(rec)
            filtered_recommendations.append(filtered_rec)
        
        # 构建响应
        response_data = {
            "query": query,
            "recommendations": filtered_recommendations,
            "total": len(filtered_recommendations),
            "algorithm": recommendations.get("algorithm", "semantic"),
            "confidence": recommendations.get("confidence", 0.0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="知识推荐成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 知识推荐失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="知识推荐失败"
        ) 