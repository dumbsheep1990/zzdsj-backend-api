"""
LightRAG知识库API模块
提供基于LightRAG的知识库管理端点
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.utils.common.logger import setup_logger
from app.utils.storage.object_storage import upload_file, get_file_url
from app.utils.core.database import get_db

from app.frameworks.lightrag.client import get_lightrag_client
from app.frameworks.lightrag.workdir_manager import get_workdir_manager
from app.frameworks.lightrag.api_client import get_lightrag_api_client
from app.utils.services.management import get_service_manager
from app.dependencies import get_lightrag_manager_dependency, get_lightrag_api_client_dependency
from app.api.frontend.dependencies import ResponseFormatter

logger = setup_logger("lightrag_api")
router = APIRouter()

# 数据模型
class WorkdirCreate(BaseModel):
    """创建工作目录请求模型"""
    name: str = Field(..., description="工作目录名称", example="project_knowledge")
    description: Optional[str] = Field(None, description="工作目录描述", example="项目知识库")

class TextUpload(BaseModel):
    """文本上传请求模型"""
    text: str = Field(..., description="文本内容")
    workdir: str = Field(..., description="工作目录", example="project_knowledge")
    description: Optional[str] = Field(None, description="文档描述")

class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="查询文本", example="什么是LightRAG?")
    workdir: str = Field(..., description="工作目录", example="project_knowledge")
    use_graph: bool = Field(True, description="是否使用图谱关系")
    top_k: int = Field(5, description="返回结果数量", ge=1, le=20)

class ServiceStatus(BaseModel):
    """服务状态响应模型"""
    name: str = Field(..., description="服务名称")
    status: str = Field(..., description="服务状态")
    version: Optional[str] = Field(None, description="服务版本")
    api_url: Optional[str] = Field(None, description="API地址")
    config: Optional[Dict[str, Any]] = Field(None, description="服务配置")

# API路由

@router.get("/status", response_model=ServiceStatus, summary="获取LightRAG服务状态")
async def get_service_status():
    """获取LightRAG服务状态"""
    client = get_lightrag_client()
    service_manager = get_service_manager()
    
    # 检查服务状态
    raw_status = service_manager.get_service_status("lightrag-api")
    
    # 构建响应
    status = ServiceStatus(
        name="LightRAG API",
        status=raw_status["status"],
        version="1.0.0",
        api_url="http://localhost:9621"
    )
    
    # 如果服务可用，获取配置
    if client.is_available():
        status.config = client.get_config()
    
    return ResponseFormatter.format_success(status)

@router.post("/service/start", response_model=Dict[str, Any], summary="启动LightRAG服务")
async def start_service():
    """启动LightRAG服务"""
    service_manager = get_service_manager()
    
    # 检查当前状态
    current_status = service_manager.get_service_status("lightrag-api")
    if current_status["status"] == "running":
        return ResponseFormatter.format_success(
            {"status": current_status},
            message="LightRAG服务已在运行"
        )
    
    # 启动服务
    success = service_manager.start_service("lightrag-api")
    updated_status = service_manager.get_service_status("lightrag-api")
    
    if success:
        return ResponseFormatter.format_success(
            {"status": updated_status},
            message="LightRAG服务启动成功"
        )
    else:
        return ResponseFormatter.format_error(
            {"status": updated_status},
            message="LightRAG服务启动失败"
        )

@router.post("/service/stop", response_model=Dict[str, Any], summary="停止LightRAG服务")
async def stop_service():
    """停止LightRAG服务"""
    service_manager = get_service_manager()
    
    # 检查当前状态
    current_status = service_manager.get_service_status("lightrag-api")
    if current_status["status"] != "running":
        return ResponseFormatter.format_success(
            {"status": current_status},
            message="LightRAG服务未在运行"
        )
    
    # 停止服务
    success = service_manager.stop_service("lightrag-api")
    updated_status = service_manager.get_service_status("lightrag-api")
    
    if success:
        return ResponseFormatter.format_success(
            {"status": updated_status},
            message="LightRAG服务停止成功"
        )
    else:
        return ResponseFormatter.format_error(
            {"status": updated_status},
            message="LightRAG服务停止失败"
        )

@router.post("/service/restart", response_model=Dict[str, Any], summary="重启LightRAG服务")
async def restart_service():
    """重启LightRAG服务"""
    service_manager = get_service_manager()
    
    # 重启服务
    success = service_manager.restart_service("lightrag-api")
    updated_status = service_manager.get_service_status("lightrag-api")
    
    if success:
        return ResponseFormatter.format_success(
            {"status": updated_status},
            message="LightRAG服务重启成功"
        )
    else:
        return ResponseFormatter.format_error(
            {"status": updated_status},
            message="LightRAG服务重启失败"
        )

@router.get("/workdirs", response_model=List[Dict[str, Any]], summary="获取工作目录列表")
async def list_workdirs():
    """获取所有可用的工作目录"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 获取工作目录列表
    graphs = client.list_graphs()
    result = []
    
    # 获取每个工作目录的详细信息
    for graph_id in graphs:
        try:
            stats = client.get_graph_stats(graph_id)
            result.append({
                "id": graph_id,
                "stats": stats
            })
        except Exception as e:
            logger.error(f"获取工作目录 {graph_id} 信息时出错: {str(e)}")
            result.append({
                "id": graph_id,
                "stats": {}
            })
    
    return ResponseFormatter.format_success(result)

@router.post("/workdirs", response_model=Dict[str, Any], summary="创建工作目录")
async def create_workdir(workdir: WorkdirCreate):
    """创建新的工作目录"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 创建工作目录
    success = client.create_graph(workdir.name, workdir.description)
    
    if success:
        return ResponseFormatter.format_success({
            "workdir": {
                "id": workdir.name,
                "description": workdir.description
            }
        }, message=f"工作目录 {workdir.name} 创建成功")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建工作目录 {workdir.name} 失败")

@router.delete("/workdirs/{workdir_id}", response_model=Dict[str, Any], summary="删除工作目录")
async def delete_workdir(workdir_id: str):
    """删除工作目录"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 删除工作目录
    success = client.delete_graph(workdir_id)
    
    if success:
        return ResponseFormatter.format_success(None, message=f"工作目录 {workdir_id} 删除成功")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除工作目录 {workdir_id} 失败")

@router.get("/workdirs/{workdir_id}/stats", response_model=Dict[str, Any], summary="获取工作目录统计信息")
async def get_workdir_stats(workdir_id: str):
    """获取工作目录统计信息"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 获取工作目录统计信息
    try:
        stats = client.get_graph_stats(workdir_id)
        return ResponseFormatter.format_success({
            "workdir": workdir_id,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"获取工作目录 {workdir_id} 统计信息时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取工作目录 {workdir_id} 统计信息失败: {str(e)}")

@router.post("/documents/text", response_model=Dict[str, Any], summary="上传文本到知识库")
async def upload_text(text_upload: TextUpload):
    """上传文本到知识库"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 准备文档
    document = {
        "text": text_upload.text,
        "metadata": {
            "description": text_upload.description or "通过API上传的文本"
        }
    }
    
    # 处理文档
    try:
        task_id = client.process_documents(
            documents=[document],
            graph_id=text_upload.workdir
        )
        
        return ResponseFormatter.format_success({
            "task_id": task_id,
            "workdir": text_upload.workdir
        }, message="文本已添加到知识库")
    except Exception as e:
        logger.error(f"上传文本到知识库时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"上传文本到知识库失败: {str(e)}")

@router.post("/documents/file", response_model=Dict[str, Any], summary="上传文件到知识库")
async def upload_file(
    workdir: str = Form(..., description="工作目录"),
    file: UploadFile = File(..., description="上传的文件"),
    description: Optional[str] = Form(None, description="文档描述"),
    advanced_mode: bool = Form(False, description="是否启用高级模式直接存储到LightRAG工作目录")
):
    """上传文件到知识库，支持普通模式和高级模式
    
    - 高级模式：文件将直接存储到LightRAG工作目录中
    - 普通模式：文件将存储到系统的公共文件管理服务中
    """
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 读取文件内容
    try:
        file_content = await file.read()
        
        # 尝试检测文件编码并转换为文本
        try:
            # 先尝试utf-8解码
            file_text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                # 再尝试gbk解码
                file_text = file_content.decode("gbk")
            except UnicodeDecodeError:
                # 如果不是文本文件，返回错误
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只支持文本文件或无法识别文件编码")
    except Exception as e:
        logger.error(f"读取文件时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"读取文件失败: {str(e)}")
    
    # 准备文档
    document = {
        "text": file_text,
        "metadata": {
            "filename": file.filename,
            "description": description or f"上传的文件: {file.filename}"
        }
    }
    
    # 处理文件路径
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = secure_filename(file.filename)
    
    try:
        from app.utils.object_storage import upload_file as upload_to_storage, get_file_url
        from app.config import settings
        
        # 根据模式选择不同的存储路径
        if advanced_mode:
            # 高级模式：直接存储到LightRAG工作目录
            file_path = f"lightrag/{workdir}/{current_time}_{safe_filename}"
            
            # 重新定位到文件开始
            file.file.seek(0)
            
            # 上传到存储服务
            url = upload_to_storage(
                file_data=file.file,
                object_name=file_path,
                content_type=file.content_type
            )
            
            # 添加存储路径到元数据
            document["metadata"]["file_path"] = file_path
            document["metadata"]["file_url"] = url
            document["metadata"]["storage_mode"] = "lightrag_direct"
        else:
            # 普通模式：存储到系统的数据目录
            file_path = f"data/documents/lightrag/{workdir}/{current_time}_{safe_filename}"
            
            # 重新定位到文件开始
            file.file.seek(0)
            
            # 上传到存储服务
            url = upload_to_storage(
                file_data=file.file,
                object_name=file_path,
                content_type=file.content_type
            )
            
            # 添加存储路径到元数据
            document["metadata"]["file_path"] = file_path
            document["metadata"]["file_url"] = url
            document["metadata"]["storage_mode"] = "system_storage"
        
        # 处理文档
        task_id = client.process_documents(
            documents=[document],
            graph_id=workdir
        )
        
        return ResponseFormatter.format_success({
            "task_id": task_id,
            "workdir": workdir,
            "filename": file.filename,
            "file_url": url,
            "storage_mode": "lightrag_direct" if advanced_mode else "system_storage"
        }, message=f"文件 {file.filename} 已添加到知识库")
    except Exception as e:
        logger.error(f"上传文件到知识库时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"上传文件到知识库失败: {str(e)}")

@router.get("/tasks/{task_id}", response_model=Dict[str, Any], summary="获取任务状态")
async def get_task_status(task_id: str):
    """获取文档处理任务状态"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 获取任务状态
    status_info = client.get_task_status(task_id)
    
    if status_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"任务 {task_id} 不存在")
    
    return ResponseFormatter.format_success({
        "task_id": task_id,
        "status": status_info
    })

@router.post("/query", response_model=Dict[str, Any], summary="查询知识库")
async def query_knowledge(query_request: QueryRequest):
    """查询知识库"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 执行查询
    try:
        result = client.query(
            query_text=query_request.query,
            graph_id=query_request.workdir,
            top_k=query_request.top_k,
            use_graph_relations=query_request.use_graph
        )
        
        return ResponseFormatter.format_success({
            "workdir": query_request.workdir,
            "query": query_request.query,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        })
    except Exception as e:
        logger.error(f"查询知识库时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"查询知识库失败: {str(e)}")

# 流式查询接口
@router.post("/query/stream", summary="流式查询知识库")
async def query_knowledge_stream(query_request: QueryRequest):
    """使用流式响应查询知识库"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LightRAG服务不可用")
    
    # 执行查询
    try:
        # 开始流式响应生成器
        async def response_generator():
            # 先发送查询信息
            yield json.dumps({
                "type": "query_info",
                "data": {
                    "workdir": query_request.workdir,
                    "query": query_request.query,
                    "use_graph": query_request.use_graph,
                    "top_k": query_request.top_k
                }
            }) + "\n"
            
            # 执行查询
            result = client.query(
                query_text=query_request.query,
                graph_id=query_request.workdir,
                top_k=query_request.top_k,
                use_graph_relations=query_request.use_graph
            )
            
            # 发送答案
            yield json.dumps({
                "type": "answer",
                "data": {
                    "answer": result.get("answer", "")
                }
            }) + "\n"
            
            # 发送来源
            sources = result.get("sources", [])
            yield json.dumps({
                "type": "sources",
                "data": {
                    "count": len(sources),
                    "sources": sources
                }
            }) + "\n"
            
            # 发送完成信号
            yield json.dumps({
                "type": "done",
                "data": {
                    "timestamp": time.time()
                }
            }) + "\n"
        
        # 返回流式响应
        return StreamingResponse(
            response_generator(),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        logger.error(f"流式查询知识库时出错: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"流式查询知识库失败: {str(e)}")

# ====================== WorkdirManager API接口 ======================

class WorkdirCreateV2(BaseModel):
    """创建工作目录请求模型 (WorkdirManager版本)"""
    path: str = Field(..., description="工作目录路径", example="project_knowledge")
    display_name: str = Field(..., description="工作目录显示名称", example="项目知识库")
    description: Optional[str] = Field(None, description="工作目录描述", example="项目知识库")

class QueryRequestV2(BaseModel):
    """查询请求模型 (WorkdirManager版本)"""
    question: str = Field(..., description="查询问题", example="什么是LightRAG?")
    workdir: str = Field(..., description="工作目录路径", example="project_knowledge")
    mode: str = Field("hybrid", description="查询模式: hybrid, vector, graph")

@router.get("/v2/workdirs", response_model=List[Dict[str, Any]], summary="获取工作目录列表 (Server集成版)")
async def list_workdirs_v2(manager = Depends(get_lightrag_manager_dependency)):
    """列出所有工作目录 (WorkdirManager版本)"""
    workdirs = await manager.list_workdirs()
    return ResponseFormatter.format_success(workdirs)

@router.post("/v2/workdirs", response_model=Dict[str, Any], summary="创建工作目录 (Server集成版)")
async def create_workdir_v2(workdir: WorkdirCreateV2, manager = Depends(get_lightrag_manager_dependency)):
    """创建新的工作目录 (WorkdirManager版本)"""
    try:
        workdir_id = await manager.create_workdir(workdir.path, workdir.display_name, workdir.description)
        return ResponseFormatter.format_success({
            "workdir": {
                "id": workdir_id,
                "path": workdir.path,
                "display_name": workdir.display_name
            }
        }, message=f"工作目录 {workdir.display_name} 创建成功")
    except Exception as e:
        logger.error(f"创建工作目录失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建工作目录失败: {str(e)}")

@router.post("/v2/query", response_model=Dict[str, Any], summary="在指定工作目录执行查询 (Server集成版)")
async def query_v2(query_request: QueryRequestV2, manager = Depends(get_lightrag_manager_dependency)):
    """在指定工作目录执行查询 (WorkdirManager版本)"""
    try:
        result = await manager.query(query_request.workdir, query_request.question, query_request.mode)
        return ResponseFormatter.format_success({
            "workdir": query_request.workdir,
            "question": query_request.question,
            "result": result
        })
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"查询失败: {str(e)}")

@router.post("/v2/query/all", response_model=Dict[str, Any], summary="查询所有工作目录 (Server集成版)")
async def query_all_v2(
    question: str = Body(..., description="查询问题"),
    mode: str = Body("hybrid", description="查询模式"),
    manager = Depends(get_lightrag_manager_dependency)
):
    """查询所有工作目录 (WorkdirManager版本)"""
    try:
        results = await manager.query_all(question, mode)
        return ResponseFormatter.format_success({
            "question": question,
            "results": results
        })
    except Exception as e:
        logger.error(f"查询所有工作目录失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"查询所有工作目录失败: {str(e)}")

@router.get("/v2/graph", response_model=Dict[str, Any], summary="获取图谱数据 (Server集成版)")
async def get_graph_data(
    workdir: str = Query(..., description="工作目录路径"),
    api_client = Depends(get_lightrag_api_client_dependency)
):
    """获取指定工作目录的知识图谱数据 (WorkdirManager版本)"""
    try:
        result = api_client.get_graph_data(workdir)
        if not result.get("success", False):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取图谱数据失败: {result.get('error', '未知错误')}")
        return ResponseFormatter.format_success(result.get("data", {}))
    except Exception as e:
        logger.error(f"获取图谱数据失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取图谱数据失败: {str(e)}")

@router.get("/v2/graph/combined", response_model=Dict[str, Any], summary="获取合并图谱数据 (Server集成版)")
async def get_combined_graph_data(
    workdirs: List[str] = Query(..., description="工作目录路径列表"),
    api_client = Depends(get_lightrag_api_client_dependency)
):
    """获取多个工作目录的合并图谱数据 (WorkdirManager版本)"""
    try:
        result = api_client.get_combined_graph_data(workdirs)
        return ResponseFormatter.format_success(result)
    except Exception as e:
        logger.error(f"获取合并图谱数据失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取合并图谱数据失败: {str(e)}") 