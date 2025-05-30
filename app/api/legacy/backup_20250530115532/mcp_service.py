"""
MCP服务管理API模块
提供MCP服务的部署、启动、停止、重启和状态查询等接口
[迁移桥接] - 该文件已迁移至 app/api/frontend/mcp/service.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.mcp.service import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/mcp_service.py，该文件已迁移至app/api/frontend/mcp/service.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)

# 创建路由器
router = APIRouter(prefix="/api/mcp-services", tags=["MCP服务管理"])

# 请求和响应模型
class MCPServiceStatusResponse(BaseModel):
    """MCP服务状态响应模型"""
    deployment_id: str
    name: str
    status: Dict[str, Any]
    service_port: Optional[int] = None
    image: Optional[str] = None
    container: Optional[str] = None
    created_at: Optional[str] = None
    description: Optional[str] = None

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
    limit: int = Query(100, ge=1, le=100)
):
    """列出所有MCP服务及其状态"""
    try:
        manager = get_mcp_service_manager()
        deployments = manager.list_deployments()
        
        # 格式化响应
        items = []
        for deployment in deployments[skip:skip+limit]:
            items.append({
                "deployment_id": deployment.get("deployment_id", ""),
                "name": deployment.get("name", ""),
                "status": deployment.get("status", {}),
                "service_port": deployment.get("service_port"),
                "image": deployment.get("image"),
                "container": deployment.get("container"),
                "created_at": deployment.get("created_at"),
                "description": deployment.get("description")
            })
        
        return {
            "items": items,
            "total": len(deployments)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取MCP服务列表失败: {str(e)}")

@router.get("/{deployment_id}", response_model=MCPServiceStatusResponse)
async def get_mcp_service(deployment_id: str):
    """获取指定MCP服务的详细信息"""
    try:
        manager = get_mcp_service_manager()
        deployment = manager.get_deployment(deployment_id)
        
        if not deployment:
            raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
        
        # 获取状态
        status = manager.get_deployment_status(deployment_id)
        
        return {
            "deployment_id": deployment.get("deployment_id", deployment_id),
            "name": deployment.get("name", ""),
            "status": status,
            "service_port": deployment.get("service_port"),
            "image": deployment.get("docker_image"),
            "container": deployment.get("container"),
            "created_at": deployment.get("created_at"),
            "description": deployment.get("description")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取MCP服务详情失败: {str(e)}")

@router.post("/{deployment_id}/start", response_model=MCPServiceActionResponse)
async def start_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks
):
    """启动指定的MCP服务"""
    try:
        manager = get_mcp_service_manager()
        
        # 检查部署是否存在
        deployment = manager.get_deployment(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
        
        # 在后台任务中启动服务
        result = await manager.start_deployment(deployment_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "status": result["status"],
            "message": result["message"],
            "details": result.get("details", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动MCP服务失败: {str(e)}")

@router.post("/{deployment_id}/stop", response_model=MCPServiceActionResponse)
async def stop_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks
):
    """停止指定的MCP服务"""
    try:
        manager = get_mcp_service_manager()
        
        # 检查部署是否存在
        deployment = manager.get_deployment(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
        
        # 在后台任务中停止服务
        result = await manager.stop_deployment(deployment_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "status": result["status"],
            "message": result["message"],
            "details": result.get("details", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止MCP服务失败: {str(e)}")

@router.post("/{deployment_id}/restart", response_model=MCPServiceActionResponse)
async def restart_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks
):
    """重启指定的MCP服务"""
    try:
        manager = get_mcp_service_manager()
        
        # 检查部署是否存在
        deployment = manager.get_deployment(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
        
        # 在后台任务中重启服务
        result = await manager.restart_deployment(deployment_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "status": result["status"],
            "message": result["message"],
            "details": result.get("details", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启MCP服务失败: {str(e)}")

@router.delete("/{deployment_id}", response_model=MCPServiceActionResponse)
async def delete_mcp_service(
    deployment_id: str,
    background_tasks: BackgroundTasks
):
    """删除指定的MCP服务"""
    try:
        manager = get_mcp_service_manager()
        
        # 检查部署是否存在
        deployment = manager.get_deployment(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
        
        # 在后台任务中删除服务
        result = await manager.delete_deployment(deployment_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "status": result["status"],
            "message": result["message"],
            "details": result.get("details", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除MCP服务失败: {str(e)}")

@router.get("/{deployment_id}/logs", response_model=MCPServiceLogsResponse)
async def get_mcp_service_logs(
    deployment_id: str,
    lines: int = Query(100, ge=1, le=1000)
):
    """获取指定MCP服务的日志"""
    try:
        manager = get_mcp_service_manager()
        
        # 检查部署是否存在
        deployment = manager.get_deployment(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
        
        # 获取日志
        result = await manager.get_deployment_logs(deployment_id, lines)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "status": result["status"],
            "message": result["message"],
            "logs": result.get("logs", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取MCP服务日志失败: {str(e)}")

@router.get("/{deployment_id}/health", response_model=MCPServiceHealthResponse)
async def check_mcp_service_health(deployment_id: str):
    """检查指定MCP服务的健康状态"""
    try:
        manager = get_mcp_service_manager()
        
        # 检查部署是否存在
        deployment = manager.get_deployment(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
        
        # 检查健康状态
        result = await manager.check_deployment_health(deployment_id)
        
        return {
            "health": result.get("health", "unknown"),
            "message": result.get("message", ""),
            "details": result.get("details")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查MCP服务健康状态失败: {str(e)}")


# MCP工具接口
@router.get("/tools", response_model=MCPToolListResponse)
async def list_mcp_tools(
    deployment_id: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """列出所有可用的MCP工具及描述"""
    try:
        # 获取工具仓库
        mcp_service_repo = MCPServiceRepository(db)
        mcp_tool_repo = MCPToolRepository(db)
        
        # 获取服务信息
        service_id = None
        service_info = {}
        
        if deployment_id:
            service = mcp_service_repo.get_by_deployment_id(deployment_id)
            if not service:
                raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
            service_id = service.id
            service_info = {service.id: {"name": service.name, "deployment_id": service.deployment_id}}
        else:
            # 获取所有服务信息
            services, _ = mcp_service_repo.get_all(skip=0, limit=1000)
            service_info = {s.id: {"name": s.name, "deployment_id": s.deployment_id} for s in services}
        
        # 查询工具
        tools, total = mcp_tool_repo.get_all(service_id=service_id, category=category, skip=skip, limit=limit)
        
        # 格式化响应
        items = []
        for tool in tools:
            if tool.service_id in service_info:
                service_data = service_info[tool.service_id]
                items.append({
                    "tool_name": tool.tool_name,
                    "description": tool.description,
                    "category": tool.category,
                    "service_id": tool.service_id,
                    "service_name": service_data["name"],
                    "deployment_id": service_data["deployment_id"],
                    "is_enabled": tool.is_enabled,
                    "schema": tool.schema,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                })
        
        return {
            "items": items,
            "total": total
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取MCP工具列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取MCP工具列表失败: {str(e)}")

@router.get("/tools/{tool_name}/schema", response_model=Dict[str, Any])
async def get_tool_schema(
    tool_name: str,
    deployment_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取MCP工具的JSON Schema定义"""
    try:
        # 获取工具仓库
        mcp_service_repo = MCPServiceRepository(db)
        mcp_tool_repo = MCPToolRepository(db)
        
        # 获取服务信息
        service_id = None
        if deployment_id:
            service = mcp_service_repo.get_by_deployment_id(deployment_id)
            if not service:
                raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
            service_id = service.id
            
            # 获取工具
            tool = mcp_tool_repo.get_by_name_and_service(service_id, tool_name)
            if not tool:
                raise HTTPException(status_code=404, detail=f"未找到MCP工具: {tool_name}")
            
            # 返回schema
            if not tool.schema:
                # 从工具服务获取schema
                manager = get_mcp_service_manager()
                schema = await manager.get_tool_schema(deployment_id, tool_name)
                
                # 更新数据库中的schema
                mcp_tool_repo.update_schema(tool.id, schema)
                
                return schema
            
            return tool.schema
        else:
            # 查询所有服务中的工具
            services, _ = mcp_service_repo.get_all(skip=0, limit=1000)
            
            for service in services:
                tool = mcp_tool_repo.get_by_name_and_service(service.id, tool_name)
                if tool and tool.schema:
                    return tool.schema
                    
            # 如果没有找到schema，尝试从第一个有此工具的服务获取
            for service in services:
                tool = mcp_tool_repo.get_by_name_and_service(service.id, tool_name)
                if tool:
                    # 从工具服务获取schema
                    manager = get_mcp_service_manager()
                    schema = await manager.get_tool_schema(service.deployment_id, tool_name)
                    
                    # 更新数据库中的schema
                    mcp_tool_repo.update_schema(tool.id, schema)
                    
                    return schema
            
            raise HTTPException(status_code=404, detail=f"未找到MCP工具: {tool_name}")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取工具Schema失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取工具Schema失败: {str(e)}")

@router.get("/tools/{tool_name}/examples", response_model=MCPToolExampleListResponse)
async def get_tool_examples(
    tool_name: str,
    deployment_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取MCP工具的参数示例"""
    try:
        # 获取工具仓库
        mcp_service_repo = MCPServiceRepository(db)
        mcp_tool_repo = MCPToolRepository(db)
        
        # 获取服务信息
        service_id = None
        if deployment_id:
            service = mcp_service_repo.get_by_deployment_id(deployment_id)
            if not service:
                raise HTTPException(status_code=404, detail=f"未找到MCP服务: {deployment_id}")
            service_id = service.id
            
            # 获取工具
            tool = mcp_tool_repo.get_by_name_and_service(service_id, tool_name)
            if not tool:
                raise HTTPException(status_code=404, detail=f"未找到MCP工具: {tool_name}")
            
            # 返回示例
            if not tool.examples:
                # 从工具服务获取示例
                manager = get_mcp_service_manager()
                examples = await manager.get_tool_examples(deployment_id, tool_name)
                
                # 更新数据库中的示例
                mcp_tool_repo.update_examples(tool.id, examples)
                
                return {"items": examples, "total": len(examples)}
            
            return {"items": tool.examples, "total": len(tool.examples)}
        else:
            # 查询所有服务中的工具
            services, _ = mcp_service_repo.get_all(skip=0, limit=1000)
            
            for service in services:
                tool = mcp_tool_repo.get_by_name_and_service(service.id, tool_name)
                if tool and tool.examples:
                    return {"items": tool.examples, "total": len(tool.examples)}
                    
            # 如果没有找到示例，尝试从第一个有此工具的服务获取
            for service in services:
                tool = mcp_tool_repo.get_by_name_and_service(service.id, tool_name)
                if tool:
                    # 从工具服务获取示例
                    manager = get_mcp_service_manager()
                    examples = await manager.get_tool_examples(service.deployment_id, tool_name)
                    
                    # 更新数据库中的示例
                    mcp_tool_repo.update_examples(tool.id, examples)
                    
                    return {"items": examples, "total": len(examples)}
            
            # 如果没有找到示例，返回空列表
            return {"items": [], "total": 0}
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取工具示例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取工具示例失败: {str(e)}")
