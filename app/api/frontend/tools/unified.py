"""
统一工具API - 前端路由模块
提供统一的工具管理和执行API接口
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin_role
from app.models.user import User
from app.services.unified_tool_service import UnifiedToolService
from app.schemas.common import StandardResponse
from app.api.frontend.responses import ResponseFormatter

router = APIRouter()

@router.get("/", summary="获取所有工具列表")
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
    
    可按类型、启用状态和工具包筛选
    """
    try:
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
        
        return ResponseFormatter.format_success(
            data=tools,
            message="获取工具列表成功",
            metadata={
                "total": len(tools),
                "skip": skip,
                "limit": limit,
                "filters": {
                    "type": type,
                    "enabled_only": enabled_only,
                    "toolkit": toolkit
                }
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具列表失败: {str(e)}",
            code=500
        )

@router.get("/{tool_name}", summary="获取工具元数据")
async def get_tool_metadata(
    tool_name: str = Path(..., description="工具名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取工具元数据
    
    返回工具的详细信息和配置
    """
    try:
        service = UnifiedToolService(db)
        metadata = await service.get_tool_metadata(tool_name)
        return ResponseFormatter.format_success(
            data=metadata,
            message=f"获取工具 '{tool_name}' 元数据成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具元数据时出错: {str(e)}",
            code=500
        )

@router.post("/{tool_name}/execute", summary="执行工具")
async def execute_tool(
    tool_name: str = Path(..., description="工具名称"),
    parameters: Dict[str, Any] = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    执行指定的工具
    
    提供参数并获取执行结果
    """
    try:
        service = UnifiedToolService(db)
        result = await service.execute_tool(
            tool_name=tool_name,
            parameters=parameters,
            user_id=str(current_user.id)
        )
        return ResponseFormatter.format_success(
            data=result,
            message=f"工具 '{tool_name}' 执行成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"执行工具时出错: {str(e)}",
            code=500
        )

@router.get("/toolkits/list", summary="列出所有可用的工具包")
async def list_available_toolkits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    列出所有可用的工具包
    """
    try:
        service = UnifiedToolService(db)
        await service.initialize()
        
        toolkits = await service.get_available_toolkits()
        return ResponseFormatter.format_success(
            data=toolkits,
            message="获取工具包列表成功",
            metadata={
                "total": len(toolkits)
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具包列表时出错: {str(e)}",
            code=500
        )

@router.post("/toolkits/{toolkit_name}/load", summary="加载指定的工具包")
async def load_toolkit(
    toolkit_name: str = Path(..., description="工具包名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    加载指定的工具包
    
    仅管理员可执行此操作
    """
    try:
        service = UnifiedToolService(db)
        await service.initialize()
        
        result = await service.load_toolkit(toolkit_name, str(current_user.id))
        return ResponseFormatter.format_success(
            data=result,
            message=f"工具包 '{toolkit_name}' 已成功加载"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"加载工具包时出错: {str(e)}",
            code=500
        )

@router.get("/toolkits", summary="获取工具包列表")
async def list_toolkits(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    enabled_only: bool = Query(False, description="是否只返回已启用的工具包"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取工具包列表
    
    可选择只返回已启用的工具包
    """
    try:
        service = UnifiedToolService(db)
        await service.initialize()
        
        toolkits = await service.get_toolkits_for_user(str(current_user.id), skip, limit)
        
        # 如果需要只返回已启用的工具包
        if enabled_only:
            toolkits = [toolkit for toolkit in toolkits if toolkit.get("is_enabled", False)]
        
        return ResponseFormatter.format_success(
            data=toolkits,
            message="获取工具包列表成功",
            metadata={
                "total": len(toolkits),
                "skip": skip,
                "limit": limit,
                "enabled_only": enabled_only
            }
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具包列表时出错: {str(e)}",
            code=500
        )

@router.get("/toolkits/{toolkit_name}", summary="获取指定工具包的详细信息")
async def get_toolkit(
    toolkit_name: str = Path(..., description="工具包名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取指定工具包的详细信息
    
    包括工具包中包含的工具列表
    """
    try:
        service = UnifiedToolService(db)
        
        toolkit = await service.get_toolkit_by_name(toolkit_name)
        if not toolkit:
            return ResponseFormatter.format_error(
                message=f"工具包 '{toolkit_name}' 不存在",
                code=404
            )
            
        # 检查权限，非管理员只能查看启用的工具包
        is_admin = await service.permission_service.is_admin(str(current_user.id), service.db)
        if not is_admin and not toolkit.get("is_enabled", False):
            return ResponseFormatter.format_error(
                message=f"您没有权限访问工具包 '{toolkit_name}'",
                code=403
            )
        
        # 获取工具包中的工具
        tools = await service.get_toolkit_tools(toolkit_name)
        toolkit["tools"] = tools
        
        return ResponseFormatter.format_success(
            data=toolkit,
            message=f"获取工具包 '{toolkit_name}' 信息成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具包信息时出错: {str(e)}",
            code=500
        )

@router.patch("/toolkits/{toolkit_id}", summary="更新工具包信息")
async def update_toolkit(
    toolkit_id: str = Path(..., description="工具包ID"),
    update_data: Dict[str, Any] = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    更新工具包信息
    
    仅管理员可执行此操作
    """
    try:
        service = UnifiedToolService(db)
        
        updated_toolkit = await service.update_toolkit(toolkit_id, update_data, str(current_user.id))
        return ResponseFormatter.format_success(
            data=updated_toolkit,
            message="工具包更新成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"更新工具包时出错: {str(e)}",
            code=500
        )

@router.post("/toolkits/{toolkit_id}/enable", summary="启用工具包")
async def enable_toolkit(
    toolkit_id: str = Path(..., description="工具包ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    启用工具包
    
    仅管理员可执行此操作
    """
    try:
        service = UnifiedToolService(db)
        
        updated_toolkit = await service.enable_toolkit(toolkit_id, str(current_user.id))
        return ResponseFormatter.format_success(
            data=updated_toolkit,
            message="工具包已启用"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"启用工具包时出错: {str(e)}",
            code=500
        )

@router.post("/toolkits/{toolkit_id}/disable", summary="禁用工具包")
async def disable_toolkit(
    toolkit_id: str = Path(..., description="工具包ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    禁用工具包
    
    仅管理员可执行此操作
    """
    try:
        service = UnifiedToolService(db)
        
        updated_toolkit = await service.disable_toolkit(toolkit_id, str(current_user.id))
        return ResponseFormatter.format_success(
            data=updated_toolkit,
            message="工具包已禁用"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"禁用工具包时出错: {str(e)}",
            code=500
        )

@router.post("/task", summary="使用工具执行任务")
async def execute_task(
    task: str = Query(..., description="任务描述"),
    tools: Optional[List[str]] = Query(None, description="可用工具列表"),
    model: Optional[str] = Query(None, description="模型名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    使用工具执行任务
    
    提供任务描述和可选的工具列表
    """
    try:
        service = UnifiedToolService(db)
        await service.initialize()
        
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
        
        return ResponseFormatter.format_success(
            data=result,
            message="任务执行成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"执行任务时出错: {str(e)}",
            code=500
        )

@router.post("/owl", summary="创建OWL工具")
async def create_owl_tool(
    tool_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> Dict[str, Any]:
    """
    创建OWL工具
    
    仅管理员可执行此操作
    """
    try:
        service = UnifiedToolService(db)
        
        tool = await service.create_owl_tool(tool_data, str(current_user.id))
        return ResponseFormatter.format_success(
            data=tool,
            message="创建OWL工具成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"创建OWL工具时出错: {str(e)}",
            code=500
        )

@router.get("/owl/{tool_id}", summary="获取OWL工具详细信息")
async def get_owl_tool(
    tool_id: str = Path(..., description="工具ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取OWL工具详细信息
    """
    try:
        service = UnifiedToolService(db)
        
        tool = await service.get_owl_tool(tool_id, str(current_user.id))
        return ResponseFormatter.format_success(
            data=tool,
            message=f"获取OWL工具 '{tool_id}' 信息成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取OWL工具信息时出错: {str(e)}",
            code=500
        )

@router.get("/owl", summary="获取OWL工具列表")
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
    
    可按工具包名称和启用状态筛选
    """
    try:
        service = UnifiedToolService(db)
        
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
        
        return ResponseFormatter.format_success(
            data=result,
            message="获取OWL工具列表成功",
            metadata={
                "total": len(result),
                "skip": skip,
                "limit": limit,
                "filters": {
                    "toolkit_name": toolkit_name,
                    "enabled_only": enabled_only
                }
            }
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取OWL工具列表时出错: {str(e)}",
            code=500
        ) 