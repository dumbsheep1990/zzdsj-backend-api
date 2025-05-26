"""
[✅ 已迁移] 此文件已完成重构和迁移到 app/api/frontend/tools/unified.py
统一工具API模块
提供统一的工具管理和执行API接口
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin_role
from app.models.user import User
from app.services.unified_tool_service import UnifiedToolService
from app.schemas.common import StandardResponse

router = APIRouter(
    prefix="/tools",
    tags=["统一工具系统"],
    responses={401: {"description": "未授权"}, 403: {"description": "权限不足"}, 404: {"description": "资源不存在"}, 500: {"description": "服务器错误"}}
)

@router.get("/", response_model=Dict[str, Any])
async def list_all_tools(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    type: Optional[str] = Query(None, description="工具类型，可选值: owl, standard"),
    enabled_only: bool = Query(False, description="是否只返回已启用的工具"),
    toolkit: Optional[str] = Query(None, description="按工具包筛选，仅对OWL工具有效"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取所有工具列表
    """
    service = UnifiedToolService(db)
    
    # 根据类型参数确定是否包含各类型工具
    include_owl = type is None or type.lower() == "owl"
    include_standard = type is None or type.lower() == "standard"
    
    tools = await service.get_all_tools(
        skip=skip, 
        limit=limit, 
        include_owl=include_owl, 
        include_standard=include_standard,
        enabled_only=enabled_only
    )
    
    # 如果指定了工具包，筛选结果
    if toolkit and include_owl:
        tools = [tool for tool in tools if tool.get("type") == "owl" and tool.get("toolkit") == toolkit]
    
    return {
        "status": "success",
        "data": tools,
        "total": len(tools),
        "skip": skip,
        "limit": limit
    }

@router.get("/{tool_name}", response_model=Dict[str, Any])
async def get_tool_metadata(
    tool_name: str = Path(..., description="工具名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取工具元数据
    """
    service = UnifiedToolService(db)
    
    try:
        metadata = await service.get_tool_metadata(tool_name)
        return {
            "status": "success",
            "data": metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具元数据时出错: {str(e)}"
        )

@router.post("/{tool_name}/execute", response_model=Dict[str, Any])
async def execute_tool(
    tool_name: str = Path(..., description="工具名称"),
    parameters: Dict[str, Any] = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    执行指定的工具
    """
    service = UnifiedToolService(db)
    
    try:
        result = await service.execute_tool(
            tool_name=tool_name,
            parameters=parameters,
            user_id=str(current_user.id)
        )
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行工具时出错: {str(e)}"
        )

@router.get("/toolkits/list", response_model=Dict[str, Any])
async def list_available_toolkits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    列出所有可用的工具包
    """
    service = UnifiedToolService(db)
    await service.initialize()
    
    try:
        toolkits = await service.get_available_toolkits()
        return {
            "status": "success",
            "data": toolkits,
            "total": len(toolkits)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具包列表时出错: {str(e)}"
        )

@router.post("/toolkits/{toolkit_name}/load", response_model=StandardResponse)
async def load_toolkit(
    toolkit_name: str = Path(..., description="工具包名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> StandardResponse:
    """
    加载指定的工具包
    """
    service = UnifiedToolService(db)
    await service.initialize()
    
    try:
        result = await service.load_toolkit(toolkit_name, str(current_user.id))
        return {
            "status": "success",
            "message": f"工具包 '{toolkit_name}' 已成功加载",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载工具包时出错: {str(e)}"
        )

@router.get("/toolkits", response_model=Dict[str, Any])
async def list_toolkits(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    enabled_only: bool = Query(False, description="是否只返回已启用的工具包"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取工具包列表
    """
    service = UnifiedToolService(db)
    await service.initialize()
    
    try:
        toolkits = await service.get_toolkits_for_user(str(current_user.id), skip, limit)
        
        # 如果需要只返回已启用的工具包
        if enabled_only:
            toolkits = [toolkit for toolkit in toolkits if toolkit.get("is_enabled", False)]
        
        return {
            "status": "success",
            "data": toolkits,
            "total": len(toolkits),
            "skip": skip,
            "limit": limit
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具包列表时出错: {str(e)}"
        )

@router.get("/toolkits/{toolkit_name}", response_model=Dict[str, Any])
async def get_toolkit(
    toolkit_name: str = Path(..., description="工具包名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取指定工具包的详细信息
    """
    service = UnifiedToolService(db)
    
    try:
        toolkit = await service.get_toolkit_by_name(toolkit_name)
        if not toolkit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具包 '{toolkit_name}' 不存在"
            )
            
        # 检查权限，非管理员只能查看启用的工具包
        is_admin = await service.permission_service.is_admin(str(current_user.id), service.db)
        if not is_admin and not toolkit.get("is_enabled", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"您没有权限访问工具包 '{toolkit_name}'"
            )
        
        # 获取工具包中的工具
        tools = await service.get_toolkit_tools(toolkit_name)
        toolkit["tools"] = tools
        
        return {
            "status": "success",
            "data": toolkit
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具包信息时出错: {str(e)}"
        )

@router.patch("/toolkits/{toolkit_id}", response_model=Dict[str, Any])
async def update_toolkit(
    toolkit_id: str = Path(..., description="工具包ID"),
    update_data: Dict[str, Any] = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    更新工具包信息
    """
    service = UnifiedToolService(db)
    
    try:
        updated_toolkit = await service.update_toolkit(toolkit_id, update_data, str(current_user.id))
        return {
            "status": "success",
            "data": updated_toolkit,
            "message": "工具包更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新工具包时出错: {str(e)}"
        )

@router.post("/toolkits/{toolkit_id}/enable", response_model=Dict[str, Any])
async def enable_toolkit(
    toolkit_id: str = Path(..., description="工具包ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    启用工具包
    """
    service = UnifiedToolService(db)
    
    try:
        updated_toolkit = await service.enable_toolkit(toolkit_id, str(current_user.id))
        return {
            "status": "success",
            "data": updated_toolkit,
            "message": "工具包已启用"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启用工具包时出错: {str(e)}"
        )

@router.post("/toolkits/{toolkit_id}/disable", response_model=Dict[str, Any])
async def disable_toolkit(
    toolkit_id: str = Path(..., description="工具包ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    禁用工具包
    """
    service = UnifiedToolService(db)
    
    try:
        updated_toolkit = await service.disable_toolkit(toolkit_id, str(current_user.id))
        return {
            "status": "success",
            "data": updated_toolkit,
            "message": "工具包已禁用"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"禁用工具包时出错: {str(e)}"
        )

@router.post("/task", response_model=Dict[str, Any])
async def execute_task(
    task: str = Query(..., description="任务描述"),
    tools: Optional[List[str]] = Query(None, description="可用工具列表"),
    model: Optional[str] = Query(None, description="模型名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    使用工具执行任务
    """
    service = UnifiedToolService(db)
    await service.initialize()
    
    try:
        # 构建模型配置
        model_config = None
        if model:
            model_config = {"model": model}
            
        # 使用通用任务处理方法
        result = await service.process_task_with_tools(
            task=task,
            tools=tools,
            model_config=model_config,
            user_id=str(current_user.id)
        )
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行任务时出错: {str(e)}"
        )

@router.post("/owl", response_model=Dict[str, Any])
async def create_owl_tool(
    tool_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    创建OWL工具
    """
    service = UnifiedToolService(db)
    
    try:
        tool = await service.create_owl_tool(tool_data, str(current_user.id))
        return {
            "status": "success",
            "data": tool,
            "message": "创建OWL工具成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建OWL工具时出错: {str(e)}"
        )

@router.get("/owl/{tool_id}", response_model=Dict[str, Any])
async def get_owl_tool(
    tool_id: str = Path(..., description="工具ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取OWL工具详细信息
    """
    service = UnifiedToolService(db)
    
    try:
        tool = await service.get_owl_tool(tool_id, str(current_user.id))
        return {
            "status": "success",
            "data": tool
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取OWL工具信息时出错: {str(e)}"
        )

@router.get("/owl", response_model=Dict[str, Any])
async def list_owl_tools(
    toolkit_name: Optional[str] = Query(None, description="工具包名称"),
    enabled_only: bool = Query(False, description="是否只返回已启用的工具"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取OWL工具列表
    """
    service = UnifiedToolService(db)
    
    try:
        # 确定查询条件
        filters = {}
        if toolkit_name:
            filters["toolkit_name"] = toolkit_name
        if enabled_only:
            filters["is_enabled"] = True
            
        tools = await service.owl_tool_service.list_tools(skip=skip, limit=limit, filters=filters)
        
        # 将工具转换为响应格式
        result = []
        for tool in tools:
            result.append({
                "id": str(tool.id),
                "name": tool.name,
                "description": tool.description,
                "toolkit_name": tool.toolkit_name,
                "function_name": tool.function_name,
                "is_enabled": tool.is_enabled,
                "requires_api_key": tool.requires_api_key,
                "source": "database"
            })
        
        return {
            "status": "success",
            "data": result,
            "total": len(result),
            "skip": skip,
            "limit": limit
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取OWL工具列表时出错: {str(e)}"
        )
