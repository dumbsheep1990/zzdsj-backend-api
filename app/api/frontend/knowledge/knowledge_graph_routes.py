"""
知识图谱API路由
支持知识库集成和独立图谱构建管理
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.dependencies import get_current_user
from app.schemas.knowledge_graph import (
    KnowledgeGraphCreate,
    KnowledgeGraphUpdate,
    KnowledgeGraphResponse,
    GraphVisualizationConfig,
    EntityExtractionConfig,
    FileSelectionRequest
)
from app.services.knowledge.knowledge_graph_service import KnowledgeGraphService
from app.utils.auth.core.user_auth import require_permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-graphs", tags=["知识图谱"])

# 服务依赖
from sqlalchemy.orm import Session
from app.utils.core.database import get_db

async def get_kg_service(db: Session = Depends(get_db)) -> KnowledgeGraphService:
    """获取集成了现有知识库服务的知识图谱服务实例"""
    return KnowledgeGraphService(db_session=db)

@router.get("/", response_model=List[KnowledgeGraphResponse])
async def list_knowledge_graphs(
    kb_id: Optional[int] = None,
    page: int = 1,
    size: int = 20,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取知识图谱列表"""
    try:
        logger.info(f"用户 {user.id} 获取知识图谱列表, kb_id={kb_id}")
        
        graphs = await kg_service.list_graphs(
            user_id=user.id,
            knowledge_base_id=kb_id,
            page=page,
            size=size
        )
        
        return graphs
        
    except Exception as e:
        logger.error(f"获取知识图谱列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取知识图谱列表失败")

@router.post("/", response_model=KnowledgeGraphResponse)
async def create_knowledge_graph(
    graph_data: KnowledgeGraphCreate,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """创建新的知识图谱"""
    try:
        logger.info(f"用户 {user.id} 创建知识图谱: {graph_data.name}")
        
        # 创建图谱记录
        graph = await kg_service.create_graph(
            user_id=user.id,
            graph_data=graph_data
        )
        
        # 如果有文件，启动后台处理
        if graph_data.files:
            background_tasks.add_task(
                kg_service.process_files_async,
                graph.id,
                graph_data.files,
                graph_data.extraction_config
            )
        
        return graph
        
    except Exception as e:
        logger.error(f"创建知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建知识图谱失败")

@router.get("/{graph_id}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    graph_id: str,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取指定知识图谱详情"""
    try:
        graph = await kg_service.get_graph(graph_id, user.id)
        
        if not graph:
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        return graph
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取知识图谱失败")

@router.put("/{graph_id}", response_model=KnowledgeGraphResponse)
async def update_knowledge_graph(
    graph_id: str,
    graph_data: KnowledgeGraphUpdate,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """更新知识图谱"""
    try:
        graph = await kg_service.update_graph(graph_id, user.id, graph_data)
        
        if not graph:
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        return graph
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新知识图谱失败")

@router.delete("/{graph_id}")
async def delete_knowledge_graph(
    graph_id: str,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """删除知识图谱"""
    try:
        success = await kg_service.delete_graph(graph_id, user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        return {"message": "知识图谱已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除知识图谱失败")

@router.get("/{graph_id}/visualization", response_class=HTMLResponse)
async def get_graph_visualization(
    graph_id: str,
    config: Optional[str] = None,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取知识图谱可视化页面"""
    try:
        # 解析配置
        viz_config = GraphVisualizationConfig.parse_raw(config) if config else None
        
        # 生成可视化HTML
        html_content = await kg_service.generate_visualization(
            graph_id, user.id, viz_config
        )
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成图谱可视化失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成图谱可视化失败")

@router.post("/{graph_id}/upload-files")
async def upload_graph_files(
    graph_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    extraction_config: Optional[str] = None,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """为知识图谱上传文件并处理"""
    try:
        # 解析提取配置
        config = EntityExtractionConfig.parse_raw(extraction_config) if extraction_config else None
        
        # 保存文件
        file_paths = await kg_service.save_uploaded_files(graph_id, files)
        
        # 启动后台处理
        background_tasks.add_task(
            kg_service.process_files_async,
            graph_id,
            file_paths,
            config
        )
        
        return {
            "message": "文件上传成功，正在后台处理",
            "file_count": len(files),
            "files": file_paths
        }
        
    except Exception as e:
        logger.error(f"上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传文件失败")

@router.get("/{graph_id}/processing-status")
async def get_processing_status(
    graph_id: str,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取知识图谱处理状态"""
    try:
        status = await kg_service.get_processing_status(graph_id, user.id)
        return status
        
    except Exception as e:
        logger.error(f"获取处理状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取处理状态失败")

@router.post("/{graph_id}/export")
async def export_knowledge_graph(
    graph_id: str,
    format_type: str = "json",
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """导出知识图谱数据"""
    try:
        export_data = await kg_service.export_graph(graph_id, user.id, format_type)
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=knowledge_graph_{graph_id}.{format_type}"
            }
        )
        
    except Exception as e:
        logger.error(f"导出知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail="导出知识图谱失败")

# 知识库集成相关接口

@router.post("/knowledge-bases/{kb_id}/generate")
async def generate_kg_from_knowledge_base(
    kb_id: int,
    selection_request: FileSelectionRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """从知识库生成知识图谱"""
    try:
        logger.info(f"用户 {user.id} 从知识库 {kb_id} 生成知识图谱")
        
        # 创建图谱记录
        graph = await kg_service.create_graph_from_kb(
            user_id=user.id,
            knowledge_base_id=kb_id,
            file_selection=selection_request.file_ids,
            config=selection_request.extraction_config
        )
        
        # 启动后台处理
        background_tasks.add_task(
            kg_service.process_kb_files_async,
            graph.id,
            kb_id,
            selection_request.file_ids,
            selection_request.extraction_config
        )
        
        return {
            "graph_id": graph.id,
            "message": "知识图谱创建成功，正在后台处理",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"从知识库生成知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail="从知识库生成知识图谱失败")

@router.get("/knowledge-bases/{kb_id}/files")
async def get_knowledge_base_files(
    kb_id: int,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取知识库可用文件列表"""
    try:
        files = await kg_service.get_kb_files(kb_id, user.id)
        return files
        
    except Exception as e:
        logger.error(f"获取知识库文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取知识库文件失败")

@router.post("/{graph_id}/entities/extract")
async def extract_entities_manually(
    graph_id: str,
    text_content: Dict[str, Any],
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """手动提取实体和关系"""
    try:
        entities = await kg_service.extract_entities_from_text(
            graph_id=graph_id,
            text=text_content["text"],
            config=text_content.get("config")
        )
        
        return {"entities": entities}
        
    except Exception as e:
        logger.error(f"提取实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="提取实体失败")

@router.post("/{graph_id}/entities")
async def add_entities_manually(
    graph_id: str,
    entities_data: Dict[str, Any],
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """手动添加实体和关系"""
    try:
        result = await kg_service.add_entities_manually(
            graph_id=graph_id,
            entities=entities_data["entities"],
            relations=entities_data.get("relations", [])
        )
        
        return result
        
    except Exception as e:
        logger.error(f"添加实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加实体失败")

@router.get("/{graph_id}/analytics")
async def get_graph_analytics(
    graph_id: str,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取知识图谱分析数据"""
    try:
        analytics = await kg_service.analyze_graph(graph_id, user.id)
        return analytics
        
    except Exception as e:
        logger.error(f"获取图谱分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取图谱分析失败")

@router.post("/{graph_id}/optimize")
async def optimize_graph_layout(
    graph_id: str,
    optimization_config: Dict[str, Any],
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """优化图谱布局"""
    try:
        result = await kg_service.optimize_layout(
            graph_id, user.id, optimization_config
        )
        
        return result
        
    except Exception as e:
        logger.error(f"优化图谱布局失败: {str(e)}")
        raise HTTPException(status_code=500, detail="优化图谱布局失败")

# 新增的可视化相关接口

@router.post("/knowledge-bases/{kb_id}/visualize")
async def generate_kb_visualization(
    kb_id: int,
    request: Dict[str, Any],
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """从知识库生成知识图谱HTML可视化"""
    try:
        # 提取参数
        graph_name = request.get("graph_name", "default")
        visualization_type = request.get("visualization_type", "interactive")
        config = request.get("config", {})
        
        # 生成可视化
        result = await kg_service.generate_visualization(
            user_id=user.id,
            knowledge_base_id=kb_id,
            graph_name=graph_name,
            visualization_type=visualization_type,
            config=config
        )
        
        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "html_path": result.get("html_path"),
                    "html_content": result.get("html_content"),
                    "statistics": result.get("statistics", {}),
                    "triples_count": result.get("triples_count", 0),
                    "visualization_type": result.get("visualization_type"),
                    "graph_name": graph_name,
                    "knowledge_base_id": kb_id
                },
                "message": "可视化生成成功"
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "可视化生成失败")
            }
            
    except Exception as e:
        logger.error(f"生成可视化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成可视化失败: {str(e)}")

@router.get("/knowledge-bases/{kb_id}/statistics")
async def get_kb_graph_statistics(
    kb_id: int,
    graph_name: str = "default",
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取知识库图谱统计信息"""
    try:
        stats = await kg_service.get_graph_statistics(
            user_id=user.id,
            knowledge_base_id=kb_id,
            graph_name=graph_name
        )
        
        if "error" not in stats:
            return {
                "success": True,
                "data": stats,
                "message": "统计信息获取成功"
            }
        else:
            return {
                "success": False,
                "message": stats.get("error", "获取统计信息失败")
            }
            
    except Exception as e:
        logger.error(f"获取图谱统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图谱统计失败: {str(e)}")

@router.get("/knowledge-bases/{kb_id}/networkx/export")
async def export_kb_networkx_graph(
    kb_id: int,
    graph_name: str = "default",
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """导出知识库NetworkX图对象信息"""
    try:
        networkx_graph = await kg_service.export_networkx_graph(
            user_id=user.id,
            knowledge_base_id=kb_id,
            graph_name=graph_name
        )
        
        if networkx_graph:
            # 转换为可序列化的格式
            graph_info = {
                "nodes_count": networkx_graph.number_of_nodes(),
                "edges_count": networkx_graph.number_of_edges(),
                "nodes": list(networkx_graph.nodes()),
                "edges": [
                    {
                        "source": u,
                        "target": v,
                        "relationships": list(data.get("relationships", set())),
                        "confidence": data.get("confidence", 1.0),
                        "inferred": data.get("inferred", False)
                    }
                    for u, v, data in networkx_graph.edges(data=True)
                ],
                "is_connected": networkx_graph.number_of_nodes() > 0,
                "density": networkx_graph.number_of_edges() / max(1, networkx_graph.number_of_nodes() * (networkx_graph.number_of_nodes() - 1) / 2) if networkx_graph.number_of_nodes() > 1 else 0
            }
            
            return {
                "success": True,
                "data": graph_info,
                "message": "NetworkX图导出成功"
            }
        else:
            return {
                "success": False,
                "message": "NetworkX图导出失败或图为空"
            }
            
    except Exception as e:
        logger.error(f"导出NetworkX图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出NetworkX图失败: {str(e)}")

@router.get("/database/status")
async def get_database_status(
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取图数据库状态"""
    try:
        status = await kg_service.get_database_info()
        return {
            "success": True,
            "data": status,
            "message": "数据库状态获取成功"
        }
    except Exception as e:
        logger.error(f"获取数据库状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取数据库状态失败: {str(e)}")

# 新增的框架化可视化接口

@router.post("/framework-visualization", summary="框架化HTML可视化生成")
async def generate_framework_visualization(
    request: Dict[str, Any],
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    框架化HTML可视化生成
    支持前端传参自动化生成图谱视图
    """
    try:
        # 提取参数
        text = request.get("text", "")
        graph_id = request.get("graph_id")
        enable_standardization = request.get("enable_standardization", True)
        enable_inference = request.get("enable_inference", True)
        visualization_type = request.get("visualization_type", "enhanced")
        
        if not text and not graph_id:
            raise HTTPException(status_code=400, detail="必须提供文本内容或图谱ID")
        
        # 如果提供了图谱ID，直接生成可视化
        if graph_id:
            html_content = await kg_service.generate_visualization(
                graph_id=graph_id,
                user_id=user.id
            )
            
            return {
                "success": True,
                "data": {
                    "html_content": html_content,
                    "graph_id": graph_id,
                    "visualization_type": "enhanced"
                },
                "message": "可视化生成成功"
            }
        
        # 如果提供了文本，先创建图谱再生成可视化
        else:
            # 使用AI知识图谱框架处理文本
            from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor
            from app.frameworks.ai_knowledge_graph.config import get_config
            
            config = get_config()
            config.standardization_enabled = enable_standardization
            config.inference_enabled = enable_inference
            
            processor = KnowledgeGraphProcessor(config)
            
            # 处理文本并直接返回可视化
            result = processor.process_text(
                text=text,
                graph_id=None,
                save_visualization=False,
                return_visualization=True
            )
            
            if "visualization_html" in result:
                return {
                    "success": True,
                    "data": {
                        "html_content": result["visualization_html"],
                        "triples": result.get("triples", []),
                        "stats": result.get("stats", {}),
                        "visualization_type": visualization_type
                    },
                    "message": "图谱生成和可视化完成"
                }
            else:
                # 如果没有直接返回HTML，手动生成
                triples = result.get("triples", [])
                
                from app.frameworks.ai_knowledge_graph.core.visualizer import KnowledgeGraphVisualizer
                visualizer = KnowledgeGraphVisualizer(config)
                
                viz_result = visualizer.visualize_knowledge_graph(
                    triples=triples,
                    output_path=None,
                    visualization_type=visualization_type
                )
                
                if viz_result.get("success"):
                    return {
                        "success": True,
                        "data": {
                            "html_content": viz_result["html_content"],
                            "triples": triples,
                            "stats": viz_result.get("statistics", {}),
                            "visualization_type": visualization_type
                        },
                        "message": "图谱生成和可视化完成"
                    }
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"可视化生成失败: {viz_result.get('error')}"
                    )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"框架化可视化生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"可视化生成失败: {str(e)}")


@router.get("/framework-visualization/{graph_id}", response_class=HTMLResponse)
async def get_framework_visualization_html(
    graph_id: str,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    获取框架生成的HTML可视化页面
    """
    try:
        html_content = await kg_service.generate_visualization(
            graph_id=graph_id,
            user_id=user.id
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"获取HTML可视化失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取HTML可视化失败")


@router.post("/text-visualization", summary="文本直接可视化")
async def text_to_visualization(
    request: Dict[str, Any],
    user=Depends(get_current_user)
):
    """
    文本直接转换为知识图谱可视化
    完全基于框架的自动化流程
    """
    try:
        text = request.get("text", "")
        if not text.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        # 配置处理参数
        enable_standardization = request.get("enable_standardization", True)
        enable_inference = request.get("enable_inference", True)
        visualization_type = request.get("visualization_type", "enhanced")
        
        # 使用AI知识图谱框架
        from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor
        from app.frameworks.ai_knowledge_graph.config import get_config
        from app.frameworks.ai_knowledge_graph.core.visualizer import KnowledgeGraphVisualizer
        
        config = get_config()
        config.standardization_enabled = enable_standardization
        config.inference_enabled = enable_inference
        
        # 创建处理器和可视化器
        processor = KnowledgeGraphProcessor(config)
        visualizer = KnowledgeGraphVisualizer(config)
        
        # 提取三元组
        result = processor.process_text(
            text=text,
            save_visualization=False,
            return_visualization=False
        )
        
        triples = result.get("triples", [])
        if not triples:
            return {
                "success": False,
                "message": "未能从文本中提取到知识图谱",
                "data": {"triples": [], "html_content": ""}
            }
        
        # 生成可视化
        viz_result = visualizer.visualize_knowledge_graph(
            triples=triples,
            output_path=None,
            visualization_type=visualization_type
        )
        
        if viz_result.get("success"):
            return {
                "success": True,
                "data": {
                    "html_content": viz_result["html_content"],
                    "triples": triples,
                    "triples_count": len(triples),
                    "statistics": viz_result.get("statistics", {}),
                    "visualization_type": visualization_type
                },
                "message": f"成功生成包含{len(triples)}个关系的知识图谱"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"可视化生成失败: {viz_result.get('error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本可视化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/text-visualization-page", response_class=HTMLResponse)
async def get_text_visualization_page():
    """
    提供一个简单的测试页面用于文本可视化
    """
    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文本知识图谱可视化测试</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        textarea {
            width: 100%;
            height: 200px;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            resize: vertical;
        }
        .options {
            margin: 20px 0;
            display: flex;
            gap: 20px;
        }
        label {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #667eea;
            display: none;
        }
        .result.success {
            border-left-color: #28a745;
            background: #d4edda;
        }
        .result.error {
            border-left-color: #dc3545;
            background: #f8d7da;
        }
        iframe {
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🕸️ 知识图谱可视化测试</h1>
        
        <textarea id="textInput" placeholder="请输入要分析的文本...&#10;&#10;示例：&#10;张三是北京大学的教授。他研究人工智能。李四是张三的学生，专业是计算机科学。北京大学位于北京市。"></textarea>
        
        <div class="options">
            <label>
                <input type="checkbox" id="enableStandardization" checked>
                启用实体标准化
            </label>
            <label>
                <input type="checkbox" id="enableInference" checked>
                启用关系推理
            </label>
        </div>
        
        <button onclick="generateVisualization()" id="generateBtn">
            🚀 生成知识图谱
        </button>
        
        <div id="result" class="result">
            <h3 id="resultTitle">处理结果</h3>
            <p id="resultMessage"></p>
            <div id="visualizationContainer"></div>
        </div>
    </div>

    <script>
        async function generateVisualization() {
            const text = document.getElementById('textInput').value.trim();
            if (!text) {
                alert('请输入文本内容');
                return;
            }
            
            const btn = document.getElementById('generateBtn');
            const result = document.getElementById('result');
            const resultTitle = document.getElementById('resultTitle');
            const resultMessage = document.getElementById('resultMessage');
            const container = document.getElementById('visualizationContainer');
            
            // 显示加载状态
            btn.disabled = true;
            btn.textContent = '⏳ 处理中...';
            result.style.display = 'block';
            result.className = 'result';
            resultTitle.textContent = '正在处理...';
            resultMessage.textContent = '正在分析文本并生成知识图谱，请稍候...';
            container.innerHTML = '';
            
            try {
                const response = await fetch('/api/knowledge-graphs/text-visualization', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        enable_standardization: document.getElementById('enableStandardization').checked,
                        enable_inference: document.getElementById('enableInference').checked,
                        visualization_type: 'enhanced'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    result.className = 'result success';
                    resultTitle.textContent = '✅ 生成成功';
                    resultMessage.textContent = data.message;
                    
                    // 显示可视化
                    const iframe = document.createElement('iframe');
                    iframe.srcdoc = data.data.html_content;
                    container.appendChild(iframe);
                } else {
                    result.className = 'result error';
                    resultTitle.textContent = '❌ 生成失败';
                    resultMessage.textContent = data.message || '未知错误';
                }
                
            } catch (error) {
                result.className = 'result error';
                resultTitle.textContent = '❌ 请求失败';
                resultMessage.textContent = '网络请求失败: ' + error.message;
            } finally {
                btn.disabled = false;
                btn.textContent = '🚀 生成知识图谱';
            }
        }
        
        // 支持回车键提交
        document.getElementById('textInput').addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                generateVisualization();
            }
        });
    </script>
</body>
</html>'''
    
    return HTMLResponse(content=html_content)

# 场景一：知识库绑定场景 - 专用接口

@router.post("/knowledge-bases/{kb_id}/create-graph", summary="从知识库创建知识图谱")
async def create_graph_from_knowledge_base(
    kb_id: int,
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    场景一：从知识库创建知识图谱
    将知识库中的文件全部切分进行提取和关系创建
    """
    try:
        # 提取参数
        graph_name = request.get("name", f"知识库_{kb_id}_图谱")
        description = request.get("description", f"基于知识库{kb_id}生成的知识图谱")
        file_ids = request.get("file_ids", [])  # 空列表表示处理所有文件
        extraction_config = request.get("extraction_config", {})
        auto_generate_html = request.get("auto_generate_html", True)
        
        # 创建提取配置
        config = EntityExtractionConfig(**extraction_config)
        
        # 创建图谱记录
        graph_data = KnowledgeGraphCreate(
            name=graph_name,
            description=description,
            knowledge_base_id=kb_id,
            extraction_config=config,
            is_public=request.get("is_public", False),
            tags=request.get("tags", [])
        )
        
        graph = await kg_service.create_graph(user.id, graph_data)
        
        # 启动后台处理任务
        background_tasks.add_task(
            process_knowledge_base_files,
            kg_service,
            graph.id,
            kb_id,
            file_ids,
            config,
            auto_generate_html
        )
        
        return {
            "success": True,
            "data": {
                "graph_id": graph.id,
                "name": graph.name,
                "status": "processing",
                "knowledge_base_id": kb_id,
                "message": "知识图谱创建成功，正在后台处理知识库文件"
            }
        }
        
    except Exception as e:
        logger.error(f"从知识库创建知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("/knowledge-bases/{kb_id}/graphs", summary="获取知识库的所有图谱")
async def get_knowledge_base_graphs(
    kb_id: int,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取指定知识库的所有图谱"""
    try:
        graphs = await kg_service.get_graphs_by_knowledge_base(
            knowledge_base_id=kb_id,
            user_id=user.id
        )
        
        return {
            "success": True,
            "data": {
                "knowledge_base_id": kb_id,
                "graphs": graphs,
                "count": len(graphs)
            }
        }
        
    except Exception as e:
        logger.error(f"获取知识库图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/knowledge-bases/{kb_id}/generate-html", summary="为知识库图谱生成HTML可视化")
async def generate_kb_graph_html(
    kb_id: int,
    request: Dict[str, Any],
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    为知识库图谱生成HTML可视化
    基于已构建的图数据生成可供前端集成的HTML页面
    """
    try:
        graph_name = request.get("graph_name", "default")
        visualization_type = request.get("visualization_type", "enhanced")
        config = request.get("config", {})
        
        # 生成HTML可视化
        result = await kg_service.generate_visualization(
            user_id=user.id,
            knowledge_base_id=kb_id,
            graph_name=graph_name,
            visualization_type=visualization_type,
            config=config
        )
        
        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "html_content": result.get("html_content"),
                    "html_path": result.get("html_path"),
                    "statistics": result.get("statistics", {}),
                    "knowledge_base_id": kb_id,
                    "graph_name": graph_name,
                    "visualization_type": visualization_type
                },
                "message": "HTML可视化生成成功"
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "HTML生成失败")
            }
            
    except Exception as e:
        logger.error(f"生成知识库HTML可视化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"HTML生成失败: {str(e)}")


# 场景二：自定义创建场景 - 专用接口

@router.post("/custom/create-graph", summary="自定义创建知识图谱")
async def create_custom_knowledge_graph(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    场景二：自定义创建知识图谱
    不与知识库关联，知识图谱是单独的数据
    """
    try:
        # 提取参数
        name = request.get("name", "自定义知识图谱")
        description = request.get("description", "")
        text_content = request.get("text", "")
        files = request.get("files", [])  # 文件路径列表
        extraction_config = request.get("extraction_config", {})
        auto_generate_html = request.get("auto_generate_html", True)
        
        if not text_content and not files:
            raise HTTPException(status_code=400, detail="必须提供文本内容或文件")
        
        # 创建提取配置
        config = EntityExtractionConfig(**extraction_config)
        
        # 创建图谱记录（不关联知识库）
        graph_data = KnowledgeGraphCreate(
            name=name,
            description=description,
            knowledge_base_id=None,  # 关键：不关联知识库
            extraction_config=config,
            is_public=request.get("is_public", False),
            tags=request.get("tags", [])
        )
        
        graph = await kg_service.create_graph(user.id, graph_data)
        
        # 启动后台处理任务
        if text_content:
            # 处理文本内容
            background_tasks.add_task(
                process_custom_text,
                kg_service,
                graph.id,
                text_content,
                config,
                auto_generate_html
            )
        elif files:
            # 处理自定义文件
            background_tasks.add_task(
                process_custom_files,
                kg_service,
                graph.id,
                files,
                config,
                auto_generate_html
            )
        
        return {
            "success": True,
            "data": {
                "graph_id": graph.id,
                "name": graph.name,
                "status": "processing",
                "type": "custom",
                "message": "自定义知识图谱创建成功，正在后台处理"
            }
        }
        
    except Exception as e:
        logger.error(f"自定义创建知识图谱失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.post("/custom/instant-graph", summary="即时创建图谱并返回HTML")
async def create_instant_custom_graph(
    request: Dict[str, Any],
    user=Depends(get_current_user)
):
    """
    即时创建自定义知识图谱并直接返回HTML
    适用于快速预览和测试场景
    """
    try:
        text = request.get("text", "")
        if not text.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        # 配置参数
        enable_standardization = request.get("enable_standardization", True)
        enable_inference = request.get("enable_inference", True)
        visualization_type = request.get("visualization_type", "enhanced")
        
        # 使用AI知识图谱框架直接处理
        from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor
        from app.frameworks.ai_knowledge_graph.config import get_config
        from app.frameworks.ai_knowledge_graph.core.visualizer import KnowledgeGraphVisualizer
        
        config = get_config()
        config.standardization_enabled = enable_standardization
        config.inference_enabled = enable_inference
        
        # 创建处理器和可视化器
        processor = KnowledgeGraphProcessor(config)
        visualizer = KnowledgeGraphVisualizer(config)
        
        # 处理文本
        result = processor.process_text(
            text=text,
            save_visualization=False,
            return_visualization=False
        )
        
        triples = result.get("triples", [])
        if not triples:
            return {
                "success": False,
                "message": "未能从文本中提取到知识关系",
                "data": {"triples": [], "html_content": ""}
            }
        
        # 生成HTML可视化
        viz_result = visualizer.visualize_knowledge_graph(
            triples=triples,
            output_path=None,
            visualization_type=visualization_type
        )
        
        if viz_result.get("success"):
            return {
                "success": True,
                "data": {
                    "html_content": viz_result["html_content"],
                    "triples": triples,
                    "triples_count": len(triples),
                    "statistics": viz_result.get("statistics", {}),
                    "visualization_type": visualization_type,
                    "type": "instant_custom"
                },
                "message": f"即时生成包含{len(triples)}个关系的知识图谱"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"HTML生成失败: {viz_result.get('error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"即时图谱创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


# 统一的HTML生成接口

@router.get("/{graph_id}/html-visualization", response_class=HTMLResponse)
async def get_graph_html_visualization(
    graph_id: str,
    visualization_type: str = "enhanced",
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    获取任意图谱的HTML可视化页面
    统一处理知识库绑定和自定义创建两种场景
    """
    try:
        # 验证图谱权限
        graph = await kg_service.get_graph(graph_id, user.id)
        if not graph:
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        # 生成HTML可视化
        if graph.knowledge_base_id:
            # 知识库绑定场景
            html_content = await kg_service.generate_kb_visualization(
                graph_id=graph_id,
                user_id=user.id,
                visualization_type=visualization_type
            )
        else:
            # 自定义创建场景
            html_content = await kg_service.generate_custom_visualization(
                graph_id=graph_id,
                user_id=user.id,
                visualization_type=visualization_type
            )
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取HTML可视化失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取HTML可视化失败")


@router.post("/{graph_id}/regenerate-html", summary="重新生成HTML可视化")
async def regenerate_graph_html(
    graph_id: str,
    request: Dict[str, Any],
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    重新生成知识图谱的HTML可视化
    支持自定义可视化参数
    """
    try:
        # 验证权限
        graph = await kg_service.get_graph(graph_id, user.id)
        if not graph:
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        visualization_type = request.get("visualization_type", "enhanced")
        config = request.get("config", {})
        
        # 根据图谱类型选择生成方法
        if graph.knowledge_base_id:
            # 知识库绑定场景
            result = await kg_service.regenerate_kb_html(
                graph_id=graph_id,
                user_id=user.id,
                visualization_type=visualization_type,
                config=config
            )
        else:
            # 自定义创建场景
            result = await kg_service.regenerate_custom_html(
                graph_id=graph_id,
                user_id=user.id,
                visualization_type=visualization_type,
                config=config
            )
        
        return {
            "success": True,
            "data": {
                "html_content": result.get("html_content"),
                "statistics": result.get("statistics", {}),
                "graph_type": "knowledge_base" if graph.knowledge_base_id else "custom",
                "visualization_type": visualization_type
            },
            "message": "HTML可视化重新生成成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新生成HTML失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重新生成失败: {str(e)}")


# 后台处理任务函数

async def process_knowledge_base_files(
    kg_service: KnowledgeGraphService,
    graph_id: str,
    kb_id: int,
    file_ids: List[int],
    config: EntityExtractionConfig,
    auto_generate_html: bool = True
):
    """后台处理知识库文件"""
    try:
        # 处理知识库文件
        await kg_service.process_kb_files_async(
            graph_id=graph_id,
            knowledge_base_id=kb_id,
            file_ids=file_ids,
            config=config
        )
        
        # 自动生成HTML可视化
        if auto_generate_html:
            try:
                await kg_service.generate_kb_visualization(
                    graph_id=graph_id,
                    user_id=None,  # 系统生成
                    auto_save=True
                )
                logger.info(f"知识库图谱 {graph_id} HTML可视化自动生成完成")
            except Exception as e:
                logger.error(f"自动生成HTML失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"处理知识库文件失败: {str(e)}")


async def process_custom_text(
    kg_service: KnowledgeGraphService,
    graph_id: str,
    text: str,
    config: EntityExtractionConfig,
    auto_generate_html: bool = True
):
    """后台处理自定义文本"""
    try:
        # 处理文本内容
        await kg_service.process_text_async(
            graph_id=graph_id,
            text=text,
            config=config
        )
        
        # 自动生成HTML可视化
        if auto_generate_html:
            try:
                await kg_service.generate_custom_visualization(
                    graph_id=graph_id,
                    user_id=None,  # 系统生成
                    auto_save=True
                )
                logger.info(f"自定义图谱 {graph_id} HTML可视化自动生成完成")
            except Exception as e:
                logger.error(f"自动生成HTML失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"处理自定义文本失败: {str(e)}")


async def process_custom_files(
    kg_service: KnowledgeGraphService,
    graph_id: str,
    files: List[str],
    config: EntityExtractionConfig,
    auto_generate_html: bool = True
):
    """后台处理自定义文件"""
    try:
        # 处理自定义文件
        await kg_service.process_files_async(
            graph_id=graph_id,
            file_paths=files,
            config=config
        )
        
        # 自动生成HTML可视化
        if auto_generate_html:
            try:
                await kg_service.generate_custom_visualization(
                    graph_id=graph_id,
                    user_id=None,  # 系统生成
                    auto_save=True
                )
                logger.info(f"自定义图谱 {graph_id} HTML可视化自动生成完成")
            except Exception as e:
                logger.error(f"自动生成HTML失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"处理自定义文件失败: {str(e)}")


# 统一的图谱状态查询

@router.get("/{graph_id}/status", summary="获取图谱处理状态")
async def get_graph_status(
    graph_id: str,
    user=Depends(get_current_user),
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """获取图谱处理状态，支持两种场景"""
    try:
        graph = await kg_service.get_graph(graph_id, user.id)
        if not graph:
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        # 获取详细状态信息
        status_info = await kg_service.get_graph_status(graph_id)
        
        return {
            "success": True,
            "data": {
                "graph_id": graph_id,
                "name": graph.name,
                "status": graph.status,
                "type": "knowledge_base" if graph.knowledge_base_id else "custom",
                "knowledge_base_id": graph.knowledge_base_id,
                "processing_progress": status_info.get("processing_progress"),
                "statistics": status_info.get("statistics"),
                "html_available": status_info.get("html_available", False),
                "created_at": graph.created_at,
                "updated_at": graph.updated_at,
                "completed_at": graph.completed_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图谱状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}") 