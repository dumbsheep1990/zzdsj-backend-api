"""AI知识图谱API路由
提供AI知识图谱的创建、管理和可视化接口
"""

from typing import List, Dict, Any, Optional
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor
from app.frameworks.ai_knowledge_graph.adapters.storage_adapter import StorageAdapter
from app.frameworks.ai_knowledge_graph.utils.graph_utils import GraphUtils
from app.frameworks.ai_knowledge_graph.config import get_config
from app.utils.auth.core.jwt_handler import get_current_user
from app.schemas.users import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 请求模型
class CreateKnowledgeGraphRequest(BaseModel):
    """创建知识图谱请求"""
    text: str = Field(..., description="输入文本")
    graph_id: Optional[str] = Field(None, description="图谱ID，可选")
    enable_standardization: bool = Field(True, description="是否启用实体标准化")
    enable_inference: bool = Field(True, description="是否启用关系推断")
    save_visualization: bool = Field(True, description="是否保存可视化文件")

class ProcessDocumentsRequest(BaseModel):
    """处理文档请求"""
    documents: List[str] = Field(..., description="文档文本列表")
    graph_id: str = Field(..., description="图谱ID")
    enable_standardization: bool = Field(True, description="是否启用实体标准化")
    enable_inference: bool = Field(True, description="是否启用关系推断")

class QueryGraphRequest(BaseModel):
    """查询图谱请求"""
    graph_id: str = Field(..., description="图谱ID")
    query: str = Field(..., description="查询文本")
    top_k: int = Field(5, description="返回结果数量")

class ExportGraphRequest(BaseModel):
    """导出图谱请求"""
    graph_id: str = Field(..., description="图谱ID")
    format_type: str = Field("json", description="导出格式")


# 全局处理器实例
processor = None
storage_adapter = None

def get_processor() -> KnowledgeGraphProcessor:
    """获取知识图谱处理器"""
    global processor
    if processor is None:
        config = get_config()
        processor = KnowledgeGraphProcessor()
    return processor

def get_storage_adapter() -> StorageAdapter:
    """获取存储适配器"""
    global storage_adapter
    if storage_adapter is None:
        config = get_config()
        storage_adapter = StorageAdapter(config)
    return storage_adapter


@router.post("/create", summary="创建知识图谱")
async def create_knowledge_graph(
    request: CreateKnowledgeGraphRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """创建知识图谱
    
    Args:
        request: 创建请求
        current_user: 当前用户
        
    Returns:
        创建结果
    """
    try:
        logger.info(f"用户 {current_user.username} 请求创建知识图谱")
        
        # 获取处理器
        kg_processor = get_processor()
        
        # 更新配置
        config_updates = {
            "standardization_enabled": request.enable_standardization,
            "inference_enabled": request.enable_inference
        }
        kg_processor.update_config(config_updates)
        
        # 处理文本
        result = kg_processor.process_text(
            text=request.text,
            graph_id=request.graph_id,
            save_visualization=request.save_visualization,
            return_visualization=True
        )
        
        # 保存到存储
        if result.get("triples"):
            storage = get_storage_adapter()
            save_result = storage.save_knowledge_graph(
                graph_id=result["graph_id"],
                triples=result["triples"],
                metadata={
                    "created_by": current_user.id,
                    "user_name": current_user.username,
                    "config": config_updates
                }
            )
            result["storage_result"] = save_result
        
        logger.info(f"知识图谱创建成功: {result.get('graph_id')}")
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"创建知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建知识图谱失败: {str(e)}")


@router.post("/process-documents", summary="处理多个文档")
async def process_documents(
    request: ProcessDocumentsRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """处理多个文档创建知识图谱
    
    Args:
        request: 处理请求
        current_user: 当前用户
        
    Returns:
        处理结果
    """
    try:
        logger.info(f"用户 {current_user.username} 请求处理 {len(request.documents)} 个文档")
        
        # 获取处理器
        kg_processor = get_processor()
        
        # 转换文档格式
        documents = [{"text": doc} for doc in request.documents]
        
        # 处理文档
        result = kg_processor.process_documents(
            documents=documents,
            graph_id=request.graph_id
        )
        
        # 保存到存储
        if result.get("triples"):
            storage = get_storage_adapter()
            save_result = storage.save_knowledge_graph(
                graph_id=result["graph_id"],
                triples=result["triples"],
                metadata={
                    "created_by": current_user.id,
                    "user_name": current_user.username,
                    "document_count": len(request.documents)
                }
            )
            result["storage_result"] = save_result
        
        logger.info(f"文档处理完成: {result.get('graph_id')}")
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"处理文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理文档失败: {str(e)}")


@router.get("/list", summary="列出知识图谱")
async def list_knowledge_graphs(
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """列出所有知识图谱
    
    Args:
        current_user: 当前用户
        
    Returns:
        图谱列表
    """
    try:
        storage = get_storage_adapter()
        graphs = storage.list_knowledge_graphs()
        
        return {
            "success": True,
            "data": {
                "graphs": graphs,
                "count": len(graphs)
            }
        }
        
    except Exception as e:
        logger.error(f"列出知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出知识图谱失败: {str(e)}")


@router.get("/{graph_id}", summary="获取知识图谱")
async def get_knowledge_graph(
    graph_id: str,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """获取知识图谱数据
    
    Args:
        graph_id: 图谱ID
        current_user: 当前用户
        
    Returns:
        图谱数据
    """
    try:
        storage = get_storage_adapter()
        result = storage.load_knowledge_graph(graph_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "图谱不存在"))
        
        return {
            "success": True,
            "data": result["graph_data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识图谱失败: {str(e)}")


@router.post("/query", summary="查询知识图谱")
async def query_knowledge_graph(
    request: QueryGraphRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """查询知识图谱
    
    Args:
        request: 查询请求
        current_user: 当前用户
        
    Returns:
        查询结果
    """
    try:
        # 加载图谱数据
        storage = get_storage_adapter()
        load_result = storage.load_knowledge_graph(request.graph_id)
        
        if not load_result.get("success"):
            raise HTTPException(status_code=404, detail="图谱不存在")
        
        triples = load_result["graph_data"].get("triples", [])
        
        # 执行查询
        kg_processor = get_processor()
        from app.frameworks.ai_knowledge_graph.adapters.llamaindex_adapter import LlamaIndexAdapter
        
        adapter = LlamaIndexAdapter(get_config())
        results = adapter.query_knowledge_graph(
            query=request.query,
            triples=triples,
            top_k=request.top_k
        )
        
        return {
            "success": True,
            "data": {
                "query": request.query,
                "results": results,
                "count": len(results)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询知识图谱失败: {str(e)}")


@router.get("/{graph_id}/visualization", summary="获取图谱可视化")
async def get_visualization(
    graph_id: str,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """获取图谱可视化
    
    Args:
        graph_id: 图谱ID
        current_user: 当前用户
        
    Returns:
        可视化路径或内容
    """
    try:
        storage = get_storage_adapter()
        vis_path = storage.get_visualization_path(graph_id)
        
        if not vis_path:
            # 重新生成可视化
            load_result = storage.load_knowledge_graph(graph_id)
            if not load_result.get("success"):
                raise HTTPException(status_code=404, detail="图谱不存在")
            
            triples = load_result["graph_data"].get("triples", [])
            kg_processor = get_processor()
            vis_path = kg_processor.generate_visualization(triples)
        
        return {
            "success": True,
            "data": {
                "visualization_path": vis_path,
                "graph_id": graph_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可视化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取可视化失败: {str(e)}")


@router.post("/export", summary="导出知识图谱")
async def export_knowledge_graph(
    request: ExportGraphRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """导出知识图谱
    
    Args:
        request: 导出请求
        current_user: 当前用户
        
    Returns:
        导出结果
    """
    try:
        storage = get_storage_adapter()
        result = storage.export_to_format(
            graph_id=request.graph_id,
            format_type=request.format_type
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"导出知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出知识图谱失败: {str(e)}")


@router.delete("/{graph_id}", summary="删除知识图谱")
async def delete_knowledge_graph(
    graph_id: str,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """删除知识图谱
    
    Args:
        graph_id: 图谱ID
        current_user: 当前用户
        
    Returns:
        删除结果
    """
    try:
        storage = get_storage_adapter()
        result = storage.delete_knowledge_graph(graph_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "图谱不存在"))
        
        logger.info(f"用户 {current_user.username} 删除了知识图谱: {graph_id}")
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除知识图谱失败: {str(e)}")


@router.get("/{graph_id}/analytics", summary="获取图谱分析")
async def get_graph_analytics(
    graph_id: str,
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """获取图谱分析数据
    
    Args:
        graph_id: 图谱ID
        current_user: 当前用户
        
    Returns:
        分析数据
    """
    try:
        # 加载图谱数据
        storage = get_storage_adapter()
        load_result = storage.load_knowledge_graph(graph_id)
        
        if not load_result.get("success"):
            raise HTTPException(status_code=404, detail="图谱不存在")
        
        triples = load_result["graph_data"].get("triples", [])
        
        # 计算分析指标
        metrics = GraphUtils.calculate_graph_metrics(triples)
        communities = GraphUtils.detect_communities(triples)
        important_entities = GraphUtils.get_important_entities(triples, top_k=10)
        
        return {
            "success": True,
            "data": {
                "metrics": metrics,
                "communities": [list(community) for community in communities],
                "important_entities": important_entities,
                "graph_id": graph_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图谱分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图谱分析失败: {str(e)}") 