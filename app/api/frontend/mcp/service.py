"""
MCP服务管理API模块
提供MCP服务的部署、启动、停止、重启和状态查询等接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.mcp_service_manager import get_mcp_service_manager
from app.repositories.mcp import MCPServiceRepository, MCPToolRepository
from app.utils.database import get_db
from app.api.frontend.dependencies import ResponseFormatter, get_current_user, require_permission

# 创建路由器
router = APIRouter(prefix="/api/frontend/mcp/services", tags=["MCP服务管理"])

# 请求和响应模型
class MCPServiceStatusResponse(BaseModel):
    """MCP服务状态响应模型"""
    deployment_id: str
    name: str
    description: Optional[str] = None
    status: str
    last_status_change: Optional[datetime] = None
    endpoint: Optional[str] = None
    tools_count: int
    is_system: bool
    is_enabled: bool
    created_at: Optional[datetime] = None


class MCPServiceListResponse(BaseModel):
    """MCP服务列表响应模型"""
    items: List[MCPServiceStatusResponse]
    total: int


class MCPServiceActionResponse(BaseModel):
    """MCP服务操作响应模型"""
    status: str
    message: str
    details: Optional[str] = None


class MCPServiceLogsResponse(BaseModel):
    """MCP服务日志响应模型"""
    status: str
    message: str
    logs: Optional[str] = None


class MCPServiceHealthResponse(BaseModel):
    """MCP服务健康状态响应模型"""
    health: str
    message: str
    details: Optional[Dict[str, Any]] = None


class MCPToolDescription(BaseModel):
    """MCP工具描述响应模型"""
    tool_name: str
    description: Optional[str] = None
    category: str
    service_id: int
    service_name: str
    deployment_id: str
    is_enabled: bool
    schema: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MCPToolExample(BaseModel):
    """MCP工具示例响应模型"""
    tool_name: str
    parameters: Dict[str, Any]
    description: Optional[str] = None
    expected_result: Optional[Any] = None


class MCPToolListResponse(BaseModel):
    """MCP工具列表响应模型"""
    items: List[MCPToolDescription]
    total: int


class MCPToolExampleListResponse(BaseModel):
    """MCP工具示例列表响应模型"""
    items: List[MCPToolExample]
    total: int


# API接口
@router.get("/", response_model=MCPServiceListResponse)
async def list_mcp_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """
    列出所有MCP服务及其状态
    
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    
    返回MCP服务列表及其当前状态
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 获取服务列表
        services, total = await manager.list_services(skip, limit)
        
        return ResponseFormatter.format_success({
            "items": services,
            "total": total
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP服务列表失败: {str(e)}"
        )


@router.get("/{deployment_id}", response_model=MCPServiceStatusResponse)
async def get_mcp_service(
    deployment_id: str,
    current_user = Depends(get_current_user)
):
    """
    获取指定MCP服务的详细信息
    
    - **deployment_id**: 服务部署ID
    
    返回MCP服务的详细信息及当前状态
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 获取服务详情
        service = await manager.get_service(deployment_id)
        
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP服务 {deployment_id} 不存在"
            )
        
        return ResponseFormatter.format_success(service)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP服务详情失败: {str(e)}"
        )


@router.post("/{deployment_id}/start", response_model=MCPServiceActionResponse)
async def start_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_permission("mcp:service:manage"))
):
    """
    启动指定的MCP服务
    
    - **deployment_id**: 服务部署ID
    
    需要MCP服务管理权限
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 检查服务是否存在
        service = await manager.get_service(deployment_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP服务 {deployment_id} 不存在"
            )
        
        # 在后台启动服务
        background_tasks.add_task(manager.start_service, deployment_id)
        
        return ResponseFormatter.format_success({
            "status": "starting",
            "message": f"MCP服务 {deployment_id} 启动命令已发送",
            "details": f"服务将在后台启动，请稍后检查服务状态"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动MCP服务失败: {str(e)}"
        )


@router.post("/{deployment_id}/stop", response_model=MCPServiceActionResponse)
async def stop_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_permission("mcp:service:manage"))
):
    """
    停止指定的MCP服务
    
    - **deployment_id**: 服务部署ID
    
    需要MCP服务管理权限
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 检查服务是否存在
        service = await manager.get_service(deployment_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP服务 {deployment_id} 不存在"
            )
        
        # 在后台停止服务
        background_tasks.add_task(manager.stop_service, deployment_id)
        
        return ResponseFormatter.format_success({
            "status": "stopping",
            "message": f"MCP服务 {deployment_id} 停止命令已发送",
            "details": f"服务将在后台停止，请稍后检查服务状态"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止MCP服务失败: {str(e)}"
        )


@router.post("/{deployment_id}/restart", response_model=MCPServiceActionResponse)
async def restart_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_permission("mcp:service:manage"))
):
    """
    重启指定的MCP服务
    
    - **deployment_id**: 服务部署ID
    
    需要MCP服务管理权限
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 检查服务是否存在
        service = await manager.get_service(deployment_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP服务 {deployment_id} 不存在"
            )
        
        # 在后台重启服务
        background_tasks.add_task(manager.restart_service, deployment_id)
        
        return ResponseFormatter.format_success({
            "status": "restarting",
            "message": f"MCP服务 {deployment_id} 重启命令已发送",
            "details": f"服务将在后台重启，请稍后检查服务状态"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重启MCP服务失败: {str(e)}"
        )


@router.delete("/{deployment_id}", response_model=MCPServiceActionResponse)
async def delete_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_permission("mcp:service:delete"))
):
    """
    删除指定的MCP服务
    
    - **deployment_id**: 服务部署ID
    
    需要MCP服务删除权限
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 检查服务是否存在
        service = await manager.get_service(deployment_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP服务 {deployment_id} 不存在"
            )
        
        # 检查系统服务
        if service.get("is_system", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"系统MCP服务 {deployment_id} 不允许删除"
            )
        
        # 在后台删除服务
        background_tasks.add_task(manager.delete_service, deployment_id)
        
        return ResponseFormatter.format_success({
            "status": "deleting",
            "message": f"MCP服务 {deployment_id} 删除命令已发送",
            "details": f"服务将在后台删除，请稍后检查服务状态"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除MCP服务失败: {str(e)}"
        )


@router.get("/{deployment_id}/logs", response_model=MCPServiceLogsResponse)
async def get_mcp_service_logs(
    deployment_id: str,
    lines: int = Query(100, ge=1, le=1000),
    current_user = Depends(require_permission("mcp:service:view"))
):
    """
    获取指定MCP服务的日志
    
    - **deployment_id**: 服务部署ID
    - **lines**: 返回的最大日志行数
    
    需要MCP服务查看权限
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 检查服务是否存在
        service = await manager.get_service(deployment_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP服务 {deployment_id} 不存在"
            )
        
        # 获取服务日志
        logs = await manager.get_service_logs(deployment_id, lines)
        
        return ResponseFormatter.format_success({
            "status": "success",
            "message": f"获取MCP服务 {deployment_id} 日志成功",
            "logs": logs
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP服务日志失败: {str(e)}"
        )


@router.get("/{deployment_id}/health", response_model=MCPServiceHealthResponse)
async def check_mcp_service_health(
    deployment_id: str,
    current_user = Depends(get_current_user)
):
    """
    检查指定MCP服务的健康状态
    
    - **deployment_id**: 服务部署ID
    
    返回服务的健康状态信息
    """
    try:
        # 获取服务管理器
        manager = get_mcp_service_manager()
        
        # 检查服务是否存在
        service = await manager.get_service(deployment_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP服务 {deployment_id} 不存在"
            )
        
        # 检查服务健康状态
        health = await manager.check_service_health(deployment_id)
        
        return ResponseFormatter.format_success(health)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查MCP服务健康状态失败: {str(e)}"
        )


# MCP工具接口
@router.get("/tools", response_model=MCPToolListResponse)
async def list_mcp_tools(
    deployment_id: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    列出所有可用的MCP工具及描述
    
    - **deployment_id**: 可选的服务部署ID过滤
    - **category**: 可选的类别过滤
    - **tag**: 可选的标签过滤
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    
    返回符合条件的MCP工具列表
    """
    try:
        # 获取工具仓库
        repo = MCPToolRepository(db)
        
        # 构建过滤条件
        filters = {}
        if deployment_id:
            filters["deployment_id"] = deployment_id
        if category:
            filters["category"] = category
        if tag:
            filters["tags"] = tag
        
        # 查询工具
        tools, total = await repo.list_tools(
            skip=skip,
            limit=limit,
            **filters
        )
        
        return ResponseFormatter.format_success({
            "items": tools,
            "total": total
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP工具列表失败: {str(e)}"
        )


@router.get("/tools/{tool_name}/schema")
async def get_tool_schema(
    tool_name: str,
    deployment_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取MCP工具的JSON Schema定义
    
    - **tool_name**: 工具名称
    - **deployment_id**: 可选的服务部署ID
    
    返回工具的JSON Schema定义
    """
    try:
        # 获取工具仓库
        repo = MCPToolRepository(db)
        
        # 构建查询条件
        filters = {"tool_name": tool_name}
        if deployment_id:
            filters["deployment_id"] = deployment_id
        
        # 查询工具
        tool = await repo.get_tool(**filters)
        
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP工具 {tool_name} 不存在"
            )
        
        # 获取工具schema
        schema = tool.get("schema", {})
        
        # 如果没有schema，获取服务中的schema
        if not schema and deployment_id:
            # 获取服务管理器
            manager = get_mcp_service_manager()
            
            # 获取工具schema
            try:
                schema = await manager.get_tool_schema(deployment_id, tool_name)
            except Exception:
                # 使用空schema
                schema = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
        
        return ResponseFormatter.format_success(schema)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP工具Schema失败: {str(e)}"
        )


@router.get("/tools/{tool_name}/examples", response_model=MCPToolExampleListResponse)
async def get_tool_examples(
    tool_name: str,
    deployment_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取MCP工具的参数示例
    
    - **tool_name**: 工具名称
    - **deployment_id**: 可选的服务部署ID
    
    返回工具的参数示例列表
    """
    try:
        # 获取工具仓库
        repo = MCPToolRepository(db)
        
        # 构建查询条件
        filters = {"tool_name": tool_name}
        if deployment_id:
            filters["deployment_id"] = deployment_id
        
        # 查询工具
        tool = await repo.get_tool(**filters)
        
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP工具 {tool_name} 不存在"
            )
        
        # 获取工具示例
        examples = await repo.get_tool_examples(tool["id"])
        
        return ResponseFormatter.format_success({
            "items": examples,
            "total": len(examples)
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP工具示例失败: {str(e)}"
        )
