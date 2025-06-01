"""
OWL工具 - 前端路由模块
提供OWL框架工具和工具包的管理接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.owl_tool import OwlTool, OwlToolkit
from app.services.owl_tool_service import OwlToolService
from app.services.user_service import UserService
from app.schemas.owl_tool import (
    ToolCreate, ToolUpdate, ToolResponse,
    ToolkitCreate, ToolkitUpdate, ToolkitResponse,
    ToolApiKeyConfig
)
from app.api.frontend.responses import ResponseFormatter

router = APIRouter()

@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED, summary="创建OWL工具")
async def create_tool(
    tool_data: ToolCreate,
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    创建新的OWL框架工具
    
    需要提供工具名称、描述、函数名称和工具包名称等信息
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 创建工具
        tool = await tool_service.register_tool(tool_data.dict(), current_user.id)
        return ResponseFormatter.format_success(
            data=tool,
            message="OWL工具创建成功",
            status_code=status.HTTP_201_CREATED
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"创建工具失败: {str(e)}",
            code=500
        )

@router.get("/", summary="获取OWL工具列表")
async def list_tools(
    skip: int = 0,
    limit: int = 100,
    toolkit_name: Optional[str] = None,
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取OWL框架工具列表
    
    可选择按工具包名称筛选
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 获取工具列表
        if toolkit_name:
            tools = await tool_service.list_tools_by_toolkit(toolkit_name)
        else:
            tools = await tool_service.list_tools(skip, limit)
            
        return ResponseFormatter.format_success(
            data=tools,
            message="获取OWL工具列表成功",
            metadata={
                "total": len(tools),
                "skip": skip,
                "limit": limit,
                "toolkit_name": toolkit_name
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具列表失败: {str(e)}",
            code=500
        )

@router.get("/enabled", summary="获取已启用的OWL工具列表")
async def list_enabled_tools(
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取已启用的OWL框架工具列表
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 获取已启用的工具列表
        tools = await tool_service.list_enabled_tools()
        return ResponseFormatter.format_success(
            data=tools,
            message="获取已启用的OWL工具列表成功",
            metadata={
                "total": len(tools)
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取已启用的工具列表失败: {str(e)}",
            code=500
        )

@router.get("/{tool_id}", response_model=ToolResponse, summary="获取OWL工具详情")
async def get_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取指定的OWL框架工具详情
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 获取工具
        tool = await tool_service.get_tool(tool_id, current_user.id)
        if not tool:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=tool,
            message="获取OWL工具详情成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具失败: {str(e)}",
            code=500
        )

@router.put("/{tool_id}", response_model=ToolResponse, summary="更新OWL工具")
async def update_tool(
    tool_data: ToolUpdate,
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    更新OWL框架工具
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 更新工具
        tool = await tool_service.update_tool(tool_id, tool_data.dict(exclude_unset=True), current_user.id)
        if not tool:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=tool,
            message="OWL工具更新成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"更新工具失败: {str(e)}",
            code=500
        )

@router.post("/{tool_id}/enable", response_model=ToolResponse, summary="启用OWL工具")
async def enable_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    启用OWL框架工具
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 启用工具
        tool = await tool_service.enable_tool(tool_id, current_user.id)
        if not tool:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=tool,
            message="OWL工具已启用"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"启用工具失败: {str(e)}",
            code=500
        )

@router.post("/{tool_id}/disable", response_model=ToolResponse, summary="禁用OWL工具")
async def disable_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    禁用OWL框架工具
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 禁用工具
        tool = await tool_service.disable_tool(tool_id, current_user.id)
        if not tool:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=tool,
            message="OWL工具已禁用"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"禁用工具失败: {str(e)}",
            code=500
        )

@router.post("/{tool_id}/api-key", response_model=ToolResponse, summary="配置工具API密钥")
async def configure_tool_api_key(
    api_key_config: ToolApiKeyConfig,
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    配置工具API密钥
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 配置API密钥
        tool = await tool_service.configure_tool_api_key(
            tool_id, api_key_config.dict(), current_user.id
        )
        if not tool:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=tool,
            message="API密钥配置成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"配置API密钥失败: {str(e)}",
            code=500
        )

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除OWL工具")
async def delete_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    删除OWL框架工具
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 删除工具
        success = await tool_service.delete_tool(tool_id, current_user.id)
        if not success:
            return ResponseFormatter.format_error(
                message="工具不存在或删除失败",
                code=404
            )
        return ResponseFormatter.format_success(
            data={"tool_id": tool_id},
            message="OWL工具已删除",
            status_code=status.HTTP_204_NO_CONTENT
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"删除工具失败: {str(e)}",
            code=500
        )

# 工具包管理接口

@router.post("/toolkits", response_model=ToolkitResponse, status_code=status.HTTP_201_CREATED, summary="创建工具包")
async def create_toolkit(
    toolkit_data: ToolkitCreate,
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    创建新的OWL框架工具包
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 创建工具包
        toolkit = await tool_service.register_toolkit(toolkit_data.dict(), current_user.id)
        return ResponseFormatter.format_success(
            data=toolkit,
            message="工具包创建成功",
            status_code=status.HTTP_201_CREATED
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"创建工具包失败: {str(e)}",
            code=500
        )

@router.get("/toolkits", summary="获取工具包列表")
async def list_toolkits(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取OWL框架工具包列表
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 获取工具包列表
        toolkits = await tool_service.list_toolkits(skip, limit)
        return ResponseFormatter.format_success(
            data=toolkits,
            message="获取工具包列表成功",
            metadata={
                "total": len(toolkits),
                "skip": skip,
                "limit": limit
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具包列表失败: {str(e)}",
            code=500
        )

@router.get("/toolkits/enabled", summary="获取已启用的工具包列表")
async def list_enabled_toolkits(
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取已启用的OWL框架工具包列表
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 获取已启用的工具包列表
        toolkits = await tool_service.list_enabled_toolkits()
        return ResponseFormatter.format_success(
            data=toolkits,
            message="获取已启用的工具包列表成功",
            metadata={
                "total": len(toolkits)
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取已启用的工具包列表失败: {str(e)}",
            code=500
        )

@router.get("/toolkits/{toolkit_id}", response_model=ToolkitResponse, summary="获取工具包详情")
async def get_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取指定的OWL框架工具包详情
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 获取工具包
        toolkit = await tool_service.get_toolkit(toolkit_id)
        if not toolkit:
            return ResponseFormatter.format_error(
                message="工具包不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=toolkit,
            message="获取工具包详情成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具包失败: {str(e)}",
            code=500
        )

@router.put("/toolkits/{toolkit_id}", response_model=ToolkitResponse, summary="更新工具包")
async def update_toolkit(
    toolkit_data: ToolkitUpdate,
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    更新OWL框架工具包
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 更新工具包
        toolkit = await tool_service.update_toolkit(
            toolkit_id, toolkit_data.dict(exclude_unset=True), current_user.id
        )
        if not toolkit:
            return ResponseFormatter.format_error(
                message="工具包不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=toolkit,
            message="工具包更新成功"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"更新工具包失败: {str(e)}",
            code=500
        )

@router.post("/toolkits/{toolkit_id}/enable", response_model=ToolkitResponse, summary="启用工具包")
async def enable_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    启用OWL框架工具包
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 启用工具包
        toolkit = await tool_service.enable_toolkit(toolkit_id, current_user.id)
        if not toolkit:
            return ResponseFormatter.format_error(
                message="工具包不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=toolkit,
            message="工具包已启用"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"启用工具包失败: {str(e)}",
            code=500
        )

@router.post("/toolkits/{toolkit_id}/disable", response_model=ToolkitResponse, summary="禁用工具包")
async def disable_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    禁用OWL框架工具包
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 禁用工具包
        toolkit = await tool_service.disable_toolkit(toolkit_id, current_user.id)
        if not toolkit:
            return ResponseFormatter.format_error(
                message="工具包不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=toolkit,
            message="工具包已禁用"
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"禁用工具包失败: {str(e)}",
            code=500
        )

@router.delete("/toolkits/{toolkit_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除工具包")
async def delete_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    删除OWL框架工具包
    """
    try:
        # 获取当前用户
        current_user = await user_service.get_current_user(db)
        if not current_user:
            return ResponseFormatter.format_error(
                message="未认证",
                code=401
            )
        
        # 删除工具包
        success = await tool_service.delete_toolkit(toolkit_id, current_user.id)
        if not success:
            return ResponseFormatter.format_error(
                message="工具包不存在或删除失败",
                code=404
            )
        return ResponseFormatter.format_success(
            data={"toolkit_id": toolkit_id},
            message="工具包已删除",
            status_code=status.HTTP_204_NO_CONTENT
        )
    except HTTPException as e:
        return ResponseFormatter.format_error(
            message=e.detail,
            code=e.status_code
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"删除工具包失败: {str(e)}",
            code=500
        ) 