"""
OWL框架工具API接口
提供OWL框架工具和工具包的管理接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.owl_tool import OwlTool, OwlToolkit
from app.services.owl_tool_service import OwlToolService
from app.services.user_service import UserService
from app.schemas.owl_tool import (
    ToolCreate, ToolUpdate, ToolResponse,
    ToolkitCreate, ToolkitUpdate, ToolkitResponse,
    ToolApiKeyConfig
)

router = APIRouter(
    prefix="/owl/tools",
    tags=["OWL工具"]
)


@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_data: ToolCreate,
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    创建新的OWL框架工具
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 创建工具
    try:
        tool = await tool_service.register_tool(tool_data.dict(), current_user.id)
        return tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工具失败: {str(e)}"
        )


@router.get("/", response_model=List[ToolResponse])
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
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 获取工具列表
    try:
        if toolkit_name:
            tools = await tool_service.list_tools_by_toolkit(toolkit_name)
        else:
            tools = await tool_service.list_tools(skip, limit)
        return tools
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具列表失败: {str(e)}"
        )


@router.get("/enabled", response_model=List[ToolResponse])
async def list_enabled_tools(
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取已启用的OWL框架工具列表
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 获取已启用的工具列表
    try:
        tools = await tool_service.list_enabled_tools()
        return tools
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取已启用的工具列表失败: {str(e)}"
        )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取指定的OWL框架工具
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 获取工具
    try:
        tool = await tool_service.get_tool(tool_id, current_user.id)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        return tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具失败: {str(e)}"
        )


@router.put("/{tool_id}", response_model=ToolResponse)
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
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 更新工具
    try:
        tool = await tool_service.update_tool(tool_id, tool_data.dict(exclude_unset=True), current_user.id)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        return tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新工具失败: {str(e)}"
        )


@router.post("/{tool_id}/enable", response_model=ToolResponse)
async def enable_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    启用OWL框架工具
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 启用工具
    try:
        tool = await tool_service.enable_tool(tool_id, current_user.id)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        return tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启用工具失败: {str(e)}"
        )


@router.post("/{tool_id}/disable", response_model=ToolResponse)
async def disable_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    禁用OWL框架工具
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 禁用工具
    try:
        tool = await tool_service.disable_tool(tool_id, current_user.id)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        return tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"禁用工具失败: {str(e)}"
        )


@router.post("/{tool_id}/api-key", response_model=ToolResponse)
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
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 配置API密钥
    try:
        tool = await tool_service.configure_tool_api_key(
            tool_id, api_key_config.dict(), current_user.id
        )
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        return tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置API密钥失败: {str(e)}"
        )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str = Path(..., title="工具ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    删除OWL框架工具
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 删除工具
    try:
        success = await tool_service.delete_tool(tool_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在或删除失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除工具失败: {str(e)}"
        )


# 工具包管理接口

@router.post("/toolkits", response_model=ToolkitResponse, status_code=status.HTTP_201_CREATED)
async def create_toolkit(
    toolkit_data: ToolkitCreate,
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    创建新的OWL框架工具包
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 创建工具包
    try:
        toolkit = await tool_service.register_toolkit(toolkit_data.dict(), current_user.id)
        return toolkit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工具包失败: {str(e)}"
        )


@router.get("/toolkits", response_model=List[ToolkitResponse])
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
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 获取工具包列表
    try:
        toolkits = await tool_service.list_toolkits(skip, limit)
        return toolkits
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具包列表失败: {str(e)}"
        )


@router.get("/toolkits/enabled", response_model=List[ToolkitResponse])
async def list_enabled_toolkits(
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取已启用的OWL框架工具包列表
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 获取已启用的工具包列表
    try:
        toolkits = await tool_service.list_enabled_toolkits()
        return toolkits
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取已启用的工具包列表失败: {str(e)}"
        )


@router.get("/toolkits/{toolkit_id}", response_model=ToolkitResponse)
async def get_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    获取指定的OWL框架工具包
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 获取工具包
    try:
        toolkit = await tool_service.get_toolkit(toolkit_id)
        if not toolkit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具包不存在"
            )
        return toolkit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具包失败: {str(e)}"
        )


@router.put("/toolkits/{toolkit_id}", response_model=ToolkitResponse)
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
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 更新工具包
    try:
        toolkit = await tool_service.update_toolkit(
            toolkit_id, toolkit_data.dict(exclude_unset=True), current_user.id
        )
        if not toolkit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具包不存在"
            )
        return toolkit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新工具包失败: {str(e)}"
        )


@router.post("/toolkits/{toolkit_id}/enable", response_model=ToolkitResponse)
async def enable_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    启用OWL框架工具包
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 启用工具包
    try:
        toolkit = await tool_service.enable_toolkit(toolkit_id, current_user.id)
        if not toolkit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具包不存在"
            )
        return toolkit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启用工具包失败: {str(e)}"
        )


@router.post("/toolkits/{toolkit_id}/disable", response_model=ToolkitResponse)
async def disable_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    禁用OWL框架工具包
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 禁用工具包
    try:
        toolkit = await tool_service.disable_toolkit(toolkit_id, current_user.id)
        if not toolkit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具包不存在"
            )
        return toolkit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"禁用工具包失败: {str(e)}"
        )


@router.delete("/toolkits/{toolkit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_toolkit(
    toolkit_id: str = Path(..., title="工具包ID"),
    db: Session = Depends(get_db),
    tool_service: OwlToolService = Depends(),
    user_service: UserService = Depends()
):
    """
    删除OWL框架工具包
    """
    # 获取当前用户
    current_user = await user_service.get_current_user(db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证"
        )
    
    # 删除工具包
    try:
        success = await tool_service.delete_toolkit(toolkit_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具包不存在或删除失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除工具包失败: {str(e)}"
        )
