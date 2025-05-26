"""
搜索管理 - 前端路由模块
提供统一的混合检索接口，支持跨知识库搜索、多引擎搜索、自定义参数
能够自动检测环境并适配最佳检索策略
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
import logging
import time

from app.services.hybrid_search_service import get_hybrid_search_service, SearchConfig
from app.services.unified_knowledge_service import get_unified_knowledge_service
from app.schemas.search import SearchRequest as SchemaSearchRequest, SearchResponse as SchemaSearchResponse, SearchResultItem, SearchStrategy
from app.utils.storage_detector import StorageDetector
from app.utils.database import get_db
from app.api.frontend.responses import ResponseFormatter

router = APIRouter()

logger = logging.getLogger(__name__)

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询文本")
    knowledge_base_ids: List[str] = Field(default=[], description="知识库ID列表，为空则搜索所有知识库")
    vector_weight: float = Field(default=0.7, description="向量搜索权重（0.0-1.0）")
    text_weight: float = Field(default=0.3, description="文本搜索权重（0.0-1.0）")
    title_weight: float = Field(default=3.0, description="标题字段权重")
    content_weight: float = Field(default=2.0, description="内容字段权重")
    size: int = Field(default=10, description="返回结果数量")
    search_engine: str = Field(default="auto", description="搜索引擎类型: es, milvus, hybrid, auto (自动检测)")
    hybrid_method: str = Field(default="weighted_sum", description="混合方法: weighted_sum, rank_fusion, cascade")
    embedding_model: Optional[str] = Field(default=None, description="用于生成查询向量的嵌入模型，为空则使用默认模型")
    filter_metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据过滤条件")
    include_content: bool = Field(default=True, description="是否包含文档内容")
    score_threshold: Optional[float] = Field(default=None, description="最低相似度阈值，低于此分数的结果将被过滤")
    
    @validator("vector_weight", "text_weight")
    def check_weights(cls, v):
        if v < 0 or v > 1:
            raise ValueError("权重必须在0到1之间")
        return v
        
    @validator("size")
    def check_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError("返回结果数量必须在1-100之间")
        return v

class SearchResult(BaseModel):
    """搜索结果模型"""
    id: str
    score: float
    document_id: str
    knowledge_base_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    vector_score: Optional[float] = None
    text_score: Optional[float] = None
    highlight: Optional[Dict[str, List[str]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResponse(BaseModel):
    """搜索响应模型"""
    results: List[SearchResult]
    total: int
    took: float
    query: str
    search_config: Dict[str, Any]
    strategy_used: str
    engine_used: str

@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    混合搜索接口，支持跨知识库搜索、混合检索和参数自定义
    具备自动检测环境并选择最佳搜索策略的能力
    """
    try:
        start_time = time.time()
        
        # 获取服务实例
        hybrid_search_service = get_hybrid_search_service()
        knowledge_service = get_unified_knowledge_service(db)
        
        # 检查知识库存在性
        if request.knowledge_base_ids:
            for kb_id in request.knowledge_base_ids:
                kb = await knowledge_service.get_knowledge_base(kb_id)
                if not kb:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, 
                        detail=f"知识库不存在: {kb_id}"
                    )
        
        # 创建搜索配置
        search_config = SearchConfig(
            query_text=request.query,
            query_vector=None,  # 不再在这里生成向量，交由服务内部处理
            knowledge_base_ids=request.knowledge_base_ids,
            vector_weight=request.vector_weight,
            text_weight=request.text_weight,
            title_weight=request.title_weight,
            content_weight=request.content_weight,
            size=request.size,
            search_engine=request.search_engine, # 可能为"auto"，由服务决定实际策略
            hybrid_method=request.hybrid_method,
            es_filter=request.filter_metadata,
            milvus_filter=None  # Milvus过滤表达式需要转换
        )
        
        # 执行搜索
        search_response = await hybrid_search_service.search(search_config)
        
        # 计算耗时
        end_time = time.time()
        took = (end_time - start_time) * 1000  # 毫秒
        
        # 转换为响应格式
        search_results = []
        
        for result in search_response.get("results", []):
            # 根据include_content决定是否包含内容
            content = result.get("content", "") if request.include_content else None
            
            # 应用分数阈值过滤
            score = result.get("score", 0.0)
            if request.score_threshold is not None and score < request.score_threshold:
                continue
                
            search_results.append(SearchResult(
                id=result.get("id", ""),
                score=score,
                document_id=result.get("document_id", ""),
                knowledge_base_id=result.get("knowledge_base_id", None),
                title=result.get("title", None),
                content=content,
                vector_score=result.get("vector_score", None),
                text_score=result.get("text_score", None),
                highlight=result.get("highlight", None),
                metadata=result.get("metadata", {})
            ))
        
        # 构造响应数据
        response_data = SearchResponse(
            results=search_results,
            total=len(search_results),
            took=search_response.get("search_time_ms", took),
            query=request.query,
            search_config={
                "vector_weight": request.vector_weight,
                "text_weight": request.text_weight,
                "search_engine": request.search_engine,
                "hybrid_method": request.hybrid_method,
                "knowledge_base_ids": request.knowledge_base_ids,
                "filter_metadata": request.filter_metadata
            },
            strategy_used=search_response.get("strategy_used", request.hybrid_method),
            engine_used=search_response.get("engine_used", "unknown")
        )
        
        # 格式化并返回响应
        return ResponseFormatter.format_success(
            response_data,
            message="搜索成功"
        )
        
    except Exception as e:
        logger.error(f"搜索时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"搜索失败: {str(e)}"
        )

@router.get("/knowledge_bases", response_model=List[Dict[str, Any]])
async def list_searchable_knowledge_bases(
    db: Session = Depends(get_db)
):
    """
    获取可搜索的知识库列表
    """
    try:
        knowledge_service = get_unified_knowledge_service(db)
        knowledge_bases = await knowledge_service.get_knowledge_bases(is_active=True)
        
        result = [
            {
                "id": kb["id"],
                "name": kb["name"],
                "description": kb["description"],
                "document_count": kb["stats"]["document_count"],
                "created_at": kb["created_at"],
                "updated_at": kb["updated_at"]
            }
            for kb in knowledge_bases
        ]
        
        return ResponseFormatter.format_success(
            result,
            message="获取可搜索知识库列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取可搜索知识库列表时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"获取知识库列表失败: {str(e)}"
        )

@router.post("/reindex_knowledge_base", status_code=status.HTTP_202_ACCEPTED)
async def reindex_knowledge_base(
    kb_id: str = Body(..., embed=True),
    rebuild_vectors: bool = Body(False, embed=True),
    force_recreate: bool = Body(False, embed=True),
    db: Session = Depends(get_db)
):
    """
    重新索引知识库，可选是否重建向量
    """
    try:
        knowledge_service = get_unified_knowledge_service(db)
        hybrid_search_service = get_hybrid_search_service()
        
        # 检查知识库是否存在
        kb = await knowledge_service.get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"知识库不存在: {kb_id}"
            )
        
        # 创建知识库索引
        await hybrid_search_service.create_knowledge_base_index(kb_id, kb["name"], kb["description"])
        
        # 获取所有文档
        documents = await knowledge_service.get_documents(kb_id, limit=10000)  # 使用统一服务获取文档
        
        indexed_count = 0
        for doc in documents:
            try:
                # 如果需要重建向量
                if rebuild_vectors:
                    from app.utils.embedding_utils import get_embedding
                    vector = await get_embedding(doc.content, model_name=kb.get("embedding_model", "text-embedding-ada-002"))
                else:
                    # 使用现有向量（如果有的话）
                    vector = getattr(doc, 'vector', None)
                    if not vector:
                        # 如果没有向量，则生成一个
                        from app.utils.embedding_utils import get_embedding
                        vector = await get_embedding(doc.content, model_name=kb.get("embedding_model", "text-embedding-ada-002"))
                    
                # 索引文档
                await hybrid_search_service.index_document(
                    kb_id=kb_id,
                    doc_id=doc.id,
                    chunk_id=f"{doc.id}_chunk_0",  # 简化的块ID
                    title=doc.title or "",
                    content=doc.content or "",
                    vector=vector,
                    metadata=doc.metadata or {}
                )
                indexed_count += 1
            except Exception as doc_error:
                logger.warning(f"索引文档 {doc.id} 失败: {str(doc_error)}")
                continue
        
        return ResponseFormatter.format_success(
            {"indexed_count": indexed_count},
            message=f"已重新索引知识库 {kb_id} 的 {indexed_count} 个文档"
        )
        
    except Exception as e:
        logger.error(f"重新索引知识库时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"重新索引知识库失败: {str(e)}"
        )

@router.get("/storage_info", response_model=Dict[str, Any])
async def get_storage_info():
    """
    获取当前环境的存储引擎信息和可用状态
    """
    try:
        storage_info = StorageDetector.get_vector_store_info()
        return ResponseFormatter.format_success(
            storage_info,
            message="获取存储信息成功"
        )
    except Exception as e:
        logger.error(f"获取存储信息时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取存储信息失败: {str(e)}"
        )

@router.post("/schema_adapter")
async def convert_search_request(
    request: SchemaSearchRequest
) -> Dict[str, Any]:
    """
    将标准搜索请求模式转换为内部搜索请求
    这对于前端或外部系统集成很有用
    """
    try:
        # 将外部模式转换为内部搜索请求
        internal_request = SearchRequest(
            query=request.query,
            knowledge_base_ids=request.knowledge_base_ids or [],
            vector_weight=request.vector_weight,
            text_weight=request.text_weight,
            size=request.top_k,
            search_engine="auto",  # 默认使用自动检测
            hybrid_method=request.strategy.value if hasattr(request.strategy, 'value') else "weighted_sum",
            filter_metadata=request.filter_metadata,
            include_content=request.include_content
        )
        
        return ResponseFormatter.format_success(
            {
                "internal_request": internal_request.dict(),
                "message": "成功转换为内部搜索请求格式"
            },
            message="请求格式转换成功"
        )
        
    except Exception as e:
        logger.error(f"转换搜索请求时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"转换搜索请求失败: {str(e)}"
        ) 