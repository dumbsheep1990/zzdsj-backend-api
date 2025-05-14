from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.repositories.tool_repository import ToolRepository
from app.schemas.tool import ToolCreate, ToolResponse, ToolUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool: ToolCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    创建新的工具
    
    - **tool**: 工具信息
    - 返回创建的工具
    """
    try:
        # 检查权限（只有管理员可以创建系统工具）
        if tool.is_system and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以创建系统工具"
            )
        
        # 设置创建者ID
        data = tool.dict()
        data["creator_id"] = current_user.id
        
        # 创建工具
        repo = ToolRepository()
        created_tool = await repo.create(data, db)
        
        return created_tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工具失败: {str(e)}"
        )

@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = None,
    tool_type: Optional[str] = None,
    is_system: Optional[bool] = None,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    列出工具
    
    - **skip**: 跳过数量
    - **limit**: 限制数量
    - **category**: 按分类筛选
    - **tool_type**: 按工具类型筛选
    - **is_system**: 是否系统工具
    - **creator_id**: 按创建者筛选
    - 返回工具列表
    """
    try:
        repo = ToolRepository()
        tools = await repo.get_all(
            db, skip=skip, limit=limit,
            category=category, tool_type=tool_type,
            is_system=is_system, creator_id=creator_id
        )
        
        return tools
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具列表失败: {str(e)}"
        )

@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取特定工具
    
    - **tool_id**: 工具ID
    - 返回指定的工具
    """
    try:
        repo = ToolRepository()
        tool = await repo.get_by_id(tool_id, db)
        
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到工具: {tool_id}"
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
    tool_id: int,
    update_data: ToolUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    更新工具
    
    - **tool_id**: 工具ID
    - **update_data**: 更新数据
    - 返回更新后的工具
    """
    try:
        repo = ToolRepository()
        tool = await repo.get_by_id(tool_id, db)
        
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到工具: {tool_id}"
            )
        
        # 检查更新权限
        if tool.creator_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此工具"
            )
        
        # 系统工具只能由管理员更新
        if tool.is_system and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以更新系统工具"
            )
        
        # 更新工具
        updated_tool = await repo.update(tool_id, update_data.dict(exclude_unset=True), db)
        
        return updated_tool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新工具失败: {str(e)}"
        )

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    删除工具
    
    - **tool_id**: 工具ID
    - 成功删除返回204状态码
    """
    try:
        repo = ToolRepository()
        tool = await repo.get_by_id(tool_id, db)
        
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到工具: {tool_id}"
            )
        
        # 检查删除权限
        if tool.creator_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此工具"
            )
        
        # 系统工具只能由管理员删除
        if tool.is_system and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以删除系统工具"
            )
        
        # 删除工具
        await repo.delete(tool_id, db)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除工具失败: {str(e)}"
        )
