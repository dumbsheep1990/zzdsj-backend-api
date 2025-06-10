"""
工具API路由
提供统一的工具注册、发现和执行接口
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
import logging

from ...abstractions import (
    ToolExecutionRequest, ToolDiscoveryRequest, ToolExecutionResponse,
    ToolCategory, ToolExecutionContext
)
from ...registry import RegistryManager, RegistryConfig
from .bridge import APIToolBridge

# 配置路由
router = APIRouter(prefix="/tools", tags=["tools"])
logger = logging.getLogger(__name__)

# 全局注册管理器实例
_registry_manager: Optional[RegistryManager] = None


async def get_registry_manager() -> RegistryManager:
    """获取注册管理器实例"""
    global _registry_manager
    
    if _registry_manager is None:
        config = RegistryConfig(
            auto_initialize=True,
            enable_health_check=True,
            enable_metrics=True,
            log_level="INFO"
        )
        _registry_manager = RegistryManager(config)
        await _registry_manager.initialize()
    
    if not _registry_manager.is_ready:
        raise HTTPException(status_code=503, detail="Tool registry not ready")
    
    return _registry_manager


async def get_api_bridge(registry_manager: RegistryManager = Depends(get_registry_manager)) -> APIToolBridge:
    """获取API桥接器实例"""
    return APIToolBridge(registry_manager)


@router.get("/", summary="获取工具API概览")
async def get_tools_overview(bridge: APIToolBridge = Depends(get_api_bridge)):
    """获取工具API的基本信息和统计"""
    try:
        stats = await bridge.get_overview()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Failed to get tools overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tools overview")


@router.get("/discover", summary="发现可用工具")
async def discover_tools(
    category: Optional[str] = Query(None, description="工具分类过滤"),
    provider: Optional[str] = Query(None, description="提供方过滤"),
    tags: Optional[str] = Query(None, description="标签过滤(逗号分隔)"),
    bridge: APIToolBridge = Depends(get_api_bridge)
):
    """发现系统中所有可用的工具"""
    try:
        # 构建过滤器
        filters = {}
        if provider:
            filters["provider"] = provider
        if tags:
            filters["tags"] = tags.split(",")
        
        # 构建分类过滤
        categories = []
        if category:
            try:
                categories = [ToolCategory(category)]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        # 发现工具
        tools = await bridge.discover_tools(filters, categories)
        
        return JSONResponse(content={
            "success": True,
            "count": len(tools),
            "tools": [tool.to_dict() for tool in tools]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to discover tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover tools")


@router.get("/providers", summary="获取所有提供方")
async def get_providers(bridge: APIToolBridge = Depends(get_api_bridge)):
    """获取所有已注册的工具提供方"""
    try:
        providers = await bridge.get_providers()
        return JSONResponse(content={
            "success": True,
            "providers": providers
        })
    except Exception as e:
        logger.error(f"Failed to get providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get providers")


@router.get("/categories", summary="获取所有工具分类")
async def get_categories():
    """获取所有支持的工具分类"""
    try:
        categories = [{"value": cat.value, "name": cat.value.replace("_", " ").title()} 
                     for cat in ToolCategory]
        return JSONResponse(content={
            "success": True,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to get categories")


@router.get("/{tool_name}", summary="获取工具详细信息")
async def get_tool_info(
    tool_name: str,
    bridge: APIToolBridge = Depends(get_api_bridge)
):
    """获取指定工具的详细信息"""
    try:
        tool_spec = await bridge.get_tool_spec(tool_name)
        if not tool_spec:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        return JSONResponse(content={
            "success": True,
            "tool": tool_spec.to_dict()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool info for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tool info")


@router.post("/execute", summary="执行工具")
async def execute_tool(
    request: ToolExecutionRequest,
    background_tasks: BackgroundTasks,
    bridge: APIToolBridge = Depends(get_api_bridge)
) -> ToolExecutionResponse:
    """执行指定的工具"""
    try:
        # 创建执行上下文
        context = ToolExecutionContext()
        if request.context:
            # 合并请求中的上下文
            for key, value in request.context.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        
        if request.timeout:
            context.timeout = request.timeout
        
        # 执行工具
        result = await bridge.execute_tool(
            tool_name=request.tool_name,
            params=request.params,
            context=context
        )
        
        # 返回响应
        return ToolExecutionResponse(
            success=result.is_success(),
            execution_id=result.execution_id,
            tool_name=result.tool_name,
            status=result.status.value,
            data=result.data,
            error=result.error,
            duration_ms=result.duration_ms,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Failed to execute tool {request.tool_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.get("/executions/{execution_id}/status", summary="获取执行状态")
async def get_execution_status(
    execution_id: str,
    bridge: APIToolBridge = Depends(get_api_bridge)
):
    """获取工具执行状态"""
    try:
        status = await bridge.get_execution_status(execution_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
        
        return JSONResponse(content={
            "success": True,
            "execution_id": execution_id,
            "status": status.value
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status for {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get execution status")


@router.get("/executions/{execution_id}/result", summary="获取执行结果")
async def get_execution_result(
    execution_id: str,
    bridge: APIToolBridge = Depends(get_api_bridge)
):
    """获取工具执行结果"""
    try:
        result = await bridge.get_execution_result(execution_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Execution result {execution_id} not found")
        
        return JSONResponse(content={
            "success": True,
            "result": result.to_dict()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution result for {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get execution result")


@router.get("/stats", summary="获取工具系统统计信息")
async def get_tools_stats(bridge: APIToolBridge = Depends(get_api_bridge)):
    """获取工具系统的统计信息"""
    try:
        stats = await bridge.get_comprehensive_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Failed to get tools stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tools stats")


@router.get("/health", summary="工具系统健康检查")
async def health_check(bridge: APIToolBridge = Depends(get_api_bridge)):
    """检查工具系统的健康状态"""
    try:
        health_status = await bridge.health_check()
        
        # 根据健康状态返回相应的HTTP状态码
        if health_status.get("healthy", False):
            return JSONResponse(content=health_status)
        else:
            return JSONResponse(
                content=health_status,
                status_code=503  # Service Unavailable
            )
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "healthy": False,
                "error": str(e),
                "timestamp": None
            },
            status_code=503
        ) 