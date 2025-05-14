from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.repositories.agent_definition_repository import AgentDefinitionRepository
from app.schemas.agent_definition import (
    AgentDefinitionCreate, 
    AgentDefinitionResponse,
    AgentDefinitionUpdate
)
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=AgentDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_definition(
    definition: AgentDefinitionCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    创建新的智能体定义
    
    - **definition**: 智能体定义信息
    - 返回创建的智能体定义
    """
    try:
        # 设置创建者ID
        data = definition.dict()
        data["creator_id"] = current_user.id
        
        # 创建智能体定义
        repo = AgentDefinitionRepository()
        created_definition = await repo.create(data, db)
        
        return created_definition
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建智能体定义失败: {str(e)}"
        )

@router.get("/", response_model=List[AgentDefinitionResponse])
async def list_agent_definitions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_public: Optional[bool] = None,
    is_system: Optional[bool] = None,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    列出智能体定义
    
    - **skip**: 跳过数量
    - **limit**: 限制数量
    - **is_public**: 筛选公开智能体
    - **is_system**: 筛选系统智能体
    - **creator_id**: 筛选特定创建者的智能体
    - 返回智能体定义列表
    """
    try:
        # 如果没有指定创建者筛选，只返回当前用户的和公开的智能体
        if creator_id is None and not current_user.is_admin:
            # 构建查询逻辑：(creator_id = current_user.id OR is_public = True OR is_system = True)
            repo = AgentDefinitionRepository()
            definitions = await repo.get_all(
                db, skip=skip, limit=limit, 
                creator_id=current_user.id, is_public=True, is_system=True
            )
        else:
            # 管理员或指定了创建者，按请求参数筛选
            repo = AgentDefinitionRepository()
            definitions = await repo.get_all(
                db, skip=skip, limit=limit, 
                creator_id=creator_id, is_public=is_public, is_system=is_system
            )
        
        return definitions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体定义列表失败: {str(e)}"
        )

@router.get("/{definition_id}", response_model=AgentDefinitionResponse)
async def get_agent_definition(
    definition_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取特定智能体定义
    
    - **definition_id**: 智能体定义ID
    - 返回指定的智能体定义
    """
    try:
        repo = AgentDefinitionRepository()
        definition = await repo.get_by_id(definition_id, db)
        
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体定义: {definition_id}"
            )
        
        # 检查访问权限
        if (not definition.is_public and 
            not definition.is_system and 
            definition.creator_id != current_user.id and 
            not current_user.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此智能体定义"
            )
        
        return definition
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体定义失败: {str(e)}"
        )

@router.put("/{definition_id}", response_model=AgentDefinitionResponse)
async def update_agent_definition(
    definition_id: int,
    update_data: AgentDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    更新智能体定义
    
    - **definition_id**: 智能体定义ID
    - **update_data**: 更新数据
    - 返回更新后的智能体定义
    """
    try:
        repo = AgentDefinitionRepository()
        definition = await repo.get_by_id(definition_id, db)
        
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体定义: {definition_id}"
            )
        
        # 检查更新权限
        if definition.creator_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此智能体定义"
            )
        
        # 更新智能体定义
        updated_definition = await repo.update(definition_id, update_data.dict(exclude_unset=True), db)
        
        return updated_definition
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新智能体定义失败: {str(e)}"
        )

@router.delete("/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_definition(
    definition_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    删除智能体定义
    
    - **definition_id**: 智能体定义ID
    - 成功删除返回204状态码
    """
    try:
        repo = AgentDefinitionRepository()
        definition = await repo.get_by_id(definition_id, db)
        
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体定义: {definition_id}"
            )
        
        # 检查删除权限
        if definition.creator_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此智能体定义"
            )
        
        # 删除智能体定义
        await repo.delete(definition_id, db)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除智能体定义失败: {str(e)}"
        )
