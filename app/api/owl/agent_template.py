from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.repositories.agent_template_repository import AgentTemplateRepository
from app.repositories.agent_definition_repository import AgentDefinitionRepository
from app.schemas.agent_template import (
    AgentTemplateCreate, 
    AgentTemplateResponse, 
    AgentTemplateUpdate,
    TemplateInstantiationRequest,
    TemplateInstantiationResponse
)
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=AgentTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_template(
    template: AgentTemplateCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    创建新的智能体模板
    
    - **template**: 智能体模板信息
    - 返回创建的智能体模板
    """
    try:
        # 设置创建者ID
        data = template.dict()
        data["creator_id"] = current_user.id
        
        # 创建智能体模板
        repo = AgentTemplateRepository()
        created_template = await repo.create(data, db)
        
        return created_template
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建智能体模板失败: {str(e)}"
        )

@router.get("/", response_model=List[AgentTemplateResponse])
async def list_agent_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = None,
    base_agent_type: Optional[str] = None,
    is_system: Optional[bool] = None,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    列出智能体模板
    
    - **skip**: 跳过数量
    - **limit**: 限制数量
    - **category**: 按分类筛选
    - **base_agent_type**: 按基础智能体类型筛选
    - **is_system**: 是否系统模板
    - **creator_id**: 按创建者筛选
    - 返回智能体模板列表
    """
    try:
        repo = AgentTemplateRepository()
        templates = await repo.get_all(
            db, skip=skip, limit=limit,
            category=category, base_agent_type=base_agent_type,
            is_system=is_system, creator_id=creator_id
        )
        
        return templates
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体模板列表失败: {str(e)}"
        )

@router.get("/{template_id}", response_model=AgentTemplateResponse)
async def get_agent_template(
    template_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取特定智能体模板
    
    - **template_id**: 模板ID
    - 返回指定的智能体模板
    """
    try:
        repo = AgentTemplateRepository()
        template = await repo.get_by_id(template_id, db)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体模板: {template_id}"
            )
        
        return template
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能体模板失败: {str(e)}"
        )

@router.put("/{template_id}", response_model=AgentTemplateResponse)
async def update_agent_template(
    template_id: int,
    update_data: AgentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    更新智能体模板
    
    - **template_id**: 模板ID
    - **update_data**: 更新数据
    - 返回更新后的智能体模板
    """
    try:
        repo = AgentTemplateRepository()
        template = await repo.get_by_id(template_id, db)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体模板: {template_id}"
            )
        
        # 检查更新权限
        if template.creator_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此智能体模板"
            )
        
        # 更新智能体模板
        updated_template = await repo.update(template_id, update_data.dict(exclude_unset=True), db)
        
        return updated_template
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新智能体模板失败: {str(e)}"
        )

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    删除智能体模板
    
    - **template_id**: 模板ID
    - 成功删除返回204状态码
    """
    try:
        repo = AgentTemplateRepository()
        template = await repo.get_by_id(template_id, db)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体模板: {template_id}"
            )
        
        # 检查删除权限
        if template.creator_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此智能体模板"
            )
        
        # 删除智能体模板
        await repo.delete(template_id, db)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除智能体模板失败: {str(e)}"
        )

@router.post("/{template_id}/instantiate", response_model=TemplateInstantiationResponse)
async def instantiate_template(
    template_id: int,
    request: TemplateInstantiationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    基于模板实例化智能体定义
    
    - **template_id**: 模板ID
    - **request**: 实例化请求参数
    - 返回创建的智能体定义ID和名称
    """
    try:
        # 获取模板
        template_repo = AgentTemplateRepository()
        template = await template_repo.get_by_id(template_id, db)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体模板: {template_id}"
            )
        
        # 准备智能体定义数据
        definition_data = {
            "name": request.name,
            "description": request.description or template.description,
            "base_agent_type": template.base_agent_type,
            "is_public": request.is_public,
            "creator_id": current_user.id,
            "configuration": template.configuration,
            "system_prompt": template.system_prompt_template
        }
        
        # 应用参数替换（如果有）
        if request.parameters and template.system_prompt_template:
            for key, value in request.parameters.items():
                placeholder = f"{{{key}}}"
                if placeholder in definition_data["system_prompt"]:
                    definition_data["system_prompt"] = definition_data["system_prompt"].replace(
                        placeholder, str(value)
                    )
        
        # 如果模板有推荐工具，添加工具配置
        if template.recommended_tools:
            definition_data["tools"] = template.recommended_tools
        
        # 如果模板有示例工作流，添加工作流定义
        if template.example_workflow:
            definition_data["workflow_definition"] = template.example_workflow
        
        # 创建智能体定义
        definition_repo = AgentDefinitionRepository()
        created_definition = await definition_repo.create(definition_data, db)
        
        return TemplateInstantiationResponse(
            definition_id=created_definition.id,
            name=created_definition.name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"实例化智能体模板失败: {str(e)}"
        )
