"""
LightRAG API接口
提供LightRAG知识图谱增强检索服务的接口
"""
from typing import Dict, List, Optional, Any, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse
import logging
import json
import time
from datetime import datetime
from werkzeug.utils import secure_filename
from pydantic import BaseModel, Field
from app.frameworks.lightrag.client import get_lightrag_client
from app.utils.service_manager import get_service_manager
from app.utils.logger import setup_logger

logger = setup_logger("lightrag_api")
router = APIRouter(prefix="/lightrag", tags=["LightRAG"])

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
    
    return status

@router.post("/service/start", response_model=Dict[str, Any], summary="启动LightRAG服务")
async def start_service():
    """启动LightRAG服务"""
    service_manager = get_service_manager()
    
    # 检查当前状态
    current_status = service_manager.get_service_status("lightrag-api")
    if current_status["status"] == "running":
        return {"success": True, "message": "LightRAG服务已在运行", "status": current_status}
    
    # 启动服务
    success = service_manager.start_service("lightrag-api")
    updated_status = service_manager.get_service_status("lightrag-api")
    
    if success:
        return {"success": True, "message": "LightRAG服务启动成功", "status": updated_status}
    else:
        return {"success": False, "message": "LightRAG服务启动失败", "status": updated_status}

@router.post("/service/stop", response_model=Dict[str, Any], summary="停止LightRAG服务")
async def stop_service():
    """停止LightRAG服务"""
    service_manager = get_service_manager()
    
    # 检查当前状态
    current_status = service_manager.get_service_status("lightrag-api")
    if current_status["status"] != "running":
        return {"success": True, "message": "LightRAG服务未在运行", "status": current_status}
    
    # 停止服务
    success = service_manager.stop_service("lightrag-api")
    updated_status = service_manager.get_service_status("lightrag-api")
    
    if success:
        return {"success": True, "message": "LightRAG服务停止成功", "status": updated_status}
    else:
        return {"success": False, "message": "LightRAG服务停止失败", "status": updated_status}

@router.post("/service/restart", response_model=Dict[str, Any], summary="重启LightRAG服务")
async def restart_service():
    """重启LightRAG服务"""
    service_manager = get_service_manager()
    
    # 重启服务
    success = service_manager.restart_service("lightrag-api")
    updated_status = service_manager.get_service_status("lightrag-api")
    
    if success:
        return {"success": True, "message": "LightRAG服务重启成功", "status": updated_status}
    else:
        return {"success": False, "message": "LightRAG服务重启失败", "status": updated_status}

@router.get("/workdirs", response_model=List[Dict[str, Any]], summary="获取工作目录列表")
async def list_workdirs():
    """获取所有可用的工作目录"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
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
    
    return result

@router.post("/workdirs", response_model=Dict[str, Any], summary="创建工作目录")
async def create_workdir(workdir: WorkdirCreate):
    """创建新的工作目录"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
    # 创建工作目录
    success = client.create_graph(workdir.name, workdir.description)
    
    if success:
        return {
            "success": True,
            "message": f"工作目录 {workdir.name} 创建成功",
            "workdir": {
                "id": workdir.name,
                "description": workdir.description
            }
        }
    else:
        raise HTTPException(status_code=500, detail=f"创建工作目录 {workdir.name} 失败")

@router.delete("/workdirs/{workdir_id}", response_model=Dict[str, Any], summary="删除工作目录")
async def delete_workdir(workdir_id: str):
    """删除工作目录"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
    # 删除工作目录
    success = client.delete_graph(workdir_id)
    
    if success:
        return {
            "success": True,
            "message": f"工作目录 {workdir_id} 删除成功"
        }
    else:
        raise HTTPException(status_code=500, detail=f"删除工作目录 {workdir_id} 失败")

@router.get("/workdirs/{workdir_id}/stats", response_model=Dict[str, Any], summary="获取工作目录统计信息")
async def get_workdir_stats(workdir_id: str):
    """获取工作目录统计信息"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
    # 获取工作目录统计信息
    try:
        stats = client.get_graph_stats(workdir_id)
        return {
            "success": True,
            "workdir": workdir_id,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取工作目录 {workdir_id} 统计信息时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取工作目录 {workdir_id} 统计信息失败: {str(e)}")

@router.post("/documents/text", response_model=Dict[str, Any], summary="上传文本到知识库")
async def upload_text(text_upload: TextUpload):
    """上传文本到知识库"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
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
        
        return {
            "success": True,
            "message": "文本已添加到知识库",
            "task_id": task_id,
            "workdir": text_upload.workdir
        }
    except Exception as e:
        logger.error(f"上传文本到知识库时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文本到知识库失败: {str(e)}")

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
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
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
                raise HTTPException(status_code=400, detail="只支持文本文件或无法识别文件编码")
    except Exception as e:
        logger.error(f"读取文件时出错: {str(e)}")
        raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
    
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
        
        return {
            "success": True,
            "message": f"文件 {file.filename} 已添加到知识库",
            "task_id": task_id,
            "workdir": workdir,
            "filename": file.filename,
            "file_url": url,
            "storage_mode": "lightrag_direct" if advanced_mode else "system_storage"
        }
    except Exception as e:
        logger.error(f"上传文件到知识库时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文件到知识库失败: {str(e)}")

@router.get("/tasks/{task_id}", response_model=Dict[str, Any], summary="获取任务状态")
async def get_task_status(task_id: str):
    """获取文档处理任务状态"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
    # 获取任务状态
    status = client.get_task_status(task_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    return {
        "success": True,
        "task_id": task_id,
        "status": status
    }

@router.post("/query", response_model=Dict[str, Any], summary="查询知识库")
async def query_knowledge(query_request: QueryRequest):
    """查询知识库"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
    # 执行查询
    try:
        result = client.query(
            query_text=query_request.query,
            graph_id=query_request.workdir,
            top_k=query_request.top_k,
            use_graph_relations=query_request.use_graph
        )
        
        return {
            "success": True,
            "workdir": query_request.workdir,
            "query": query_request.query,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        }
    except Exception as e:
        logger.error(f"查询知识库时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询知识库失败: {str(e)}")

@router.post("/query/stream", summary="流式查询知识库")
async def query_knowledge_stream(query_request: QueryRequest):
    """流式查询知识库，返回流式响应"""
    client = get_lightrag_client()
    
    if not client.is_available():
        raise HTTPException(status_code=503, detail="LightRAG服务不可用")
    
    # 执行流式查询
    try:
        # 获取流式响应
        response = client.query_stream(
            query_text=query_request.query,
            graph_id=query_request.workdir,
            top_k=query_request.top_k,
            use_graph_relations=query_request.use_graph
        )
        
        # 如果不是流式响应而是错误信息
        if isinstance(response, dict) and not response.get("success", True):
            raise HTTPException(status_code=500, detail=response.get("error", "流式查询失败"))
        
        # 创建一个生成器，用于流式返回内容
        async def response_generator():
            try:
                # 转发原始响应
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"流式响应处理错误: {str(e)}")
                # 返回错误信息
                yield f"流式响应处理错误: {str(e)}".encode()
        
        # 返回流式响应
        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"流式查询知识库时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"流式查询知识库失败: {str(e)}")
