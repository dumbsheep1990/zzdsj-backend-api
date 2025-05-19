"""
智能体服务模块
处理智能体定义、模板和运行管理相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.agent_definition import AgentDefinition
from app.models.agent_template import AgentTemplate
from app.models.agent_run import AgentRun
from app.repositories.agent_definition_repository import AgentDefinitionRepository
from app.repositories.agent_template_repository import AgentTemplateRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="agent", priority="high", description="智能体管理服务")
class AgentService:
    """智能体服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化智能体服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.definition_repository = AgentDefinitionRepository()
        self.template_repository = AgentTemplateRepository()
        self.run_repository = AgentRunRepository()
        self.permission_service = permission_service
    
    # ==================== 智能体定义管理 ====================
    
    async def create_agent_definition(self, definition_data: Dict[str, Any], user_id: str) -> AgentDefinition:
        """创建智能体定义
        
        Args:
            definition_data: 智能体定义数据
            user_id: 用户ID
            
        Returns:
            AgentDefinition: 创建的智能体定义实例
            
        Raises:
            HTTPException: 如果智能体名称已存在或没有权限
        """
        # 检查智能体名称是否已存在
        existing_definition = await self.definition_repository.get_by_name(
            definition_data.get("name"), self.db
        )
        if existing_definition:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"智能体名称 '{definition_data.get('name')}' 已存在"
            )
        
        # 创建智能体定义
        definition = await self.definition_repository.create(definition_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "agent_definition", definition.id, user_id
        )
        
        return definition
    
    async def get_agent_definition(self, definition_id: str, user_id: str) -> Optional[AgentDefinition]:
        """获取智能体定义
        
        Args:
            definition_id: 智能体定义ID
            user_id: 用户ID
            
        Returns:
            Optional[AgentDefinition]: 获取的智能体定义实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取智能体定义
        definition = await self.definition_repository.get_by_id(definition_id, self.db)
        if not definition:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "agent_definition", definition_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此智能体定义"
            )
        
        return definition
    
    async def get_agent_definition_by_name(self, name: str, user_id: str) -> Optional[AgentDefinition]:
        """通过名称获取智能体定义
        
        Args:
            name: 智能体名称
            user_id: 用户ID
            
        Returns:
            Optional[AgentDefinition]: 获取的智能体定义实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取智能体定义
        definition = await self.definition_repository.get_by_name(name, self.db)
        if not definition:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "agent_definition", definition.id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此智能体定义"
            )
        
        return definition
    
    async def list_agent_definitions(self, user_id: str, skip: int = 0, limit: int = 100) -> List[AgentDefinition]:
        """获取智能体定义列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[AgentDefinition]: 智能体定义列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有智能体定义
        if is_admin:
            return await self.definition_repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的智能体定义
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        agent_permissions = [p for p in user_permissions if p.resource_type == "agent_definition"]
        
        if not agent_permissions:
            return []
        
        # 获取有权限的智能体定义
        definition_ids = [p.resource_id for p in agent_permissions]
        definitions = []
        for definition_id in definition_ids:
            definition = await self.definition_repository.get_by_id(definition_id, self.db)
            if definition:
                definitions.append(definition)
        
        return definitions
    
    async def list_agent_definitions_by_type(self, agent_type: str, user_id: str) -> List[AgentDefinition]:
        """获取指定类型的智能体定义列表
        
        Args:
            agent_type: 智能体类型
            user_id: 用户ID
            
        Returns:
            List[AgentDefinition]: 智能体定义列表
        """
        # 获取指定类型的智能体定义
        all_definitions = await self.definition_repository.list_by_type(agent_type, self.db)
        
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        if is_admin:
            return all_definitions
        
        # 过滤用户有权限的智能体定义
        result = []
        for definition in all_definitions:
            has_permission = await self.permission_service.check_permission(
                "agent_definition", definition.id, user_id, "read"
            )
            
            if has_permission:
                result.append(definition)
        
        return result
    
    async def update_agent_definition(self, definition_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[AgentDefinition]:
        """更新智能体定义
        
        Args:
            definition_id: 智能体定义ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[AgentDefinition]: 更新后的智能体定义实例或None
            
        Raises:
            HTTPException: 如果没有权限或智能体定义不存在
        """
        # 获取智能体定义
        definition = await self.definition_repository.get_by_id(definition_id, self.db)
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体定义不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "agent_definition", definition_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此智能体定义"
            )
        
        # 更新智能体定义
        return await self.definition_repository.update(definition_id, update_data, self.db)
    
    async def delete_agent_definition(self, definition_id: str, user_id: str) -> bool:
        """删除智能体定义
        
        Args:
            definition_id: 智能体定义ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或智能体定义不存在
        """
        # 获取智能体定义
        definition = await self.definition_repository.get_by_id(definition_id, self.db)
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体定义不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "agent_definition", definition_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此智能体定义"
            )
        
        # 删除智能体定义
        return await self.definition_repository.delete(definition_id, self.db)
    
    # ==================== 智能体模板管理 ====================
    
    async def create_agent_template(self, template_data: Dict[str, Any], user_id: str) -> AgentTemplate:
        """创建智能体模板
        
        Args:
            template_data: 智能体模板数据
            user_id: 用户ID
            
        Returns:
            AgentTemplate: 创建的智能体模板实例
            
        Raises:
            HTTPException: 如果模板名称已存在或没有权限
        """
        # 检查模板名称是否已存在
        existing_template = await self.template_repository.get_by_name(
            template_data.get("name"), self.db
        )
        if existing_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"模板名称 '{template_data.get('name')}' 已存在"
            )
        
        # 创建智能体模板
        template = await self.template_repository.create(template_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "agent_template", template.id, user_id
        )
        
        return template
    
    async def get_agent_template(self, template_id: str, user_id: str) -> Optional[AgentTemplate]:
        """获取智能体模板
        
        Args:
            template_id: 智能体模板ID
            user_id: 用户ID
            
        Returns:
            Optional[AgentTemplate]: 获取的智能体模板实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取智能体模板
        template = await self.template_repository.get_by_id(template_id, self.db)
        if not template:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "agent_template", template_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此智能体模板"
            )
        
        return template
    
    async def list_agent_templates(self, user_id: str, skip: int = 0, limit: int = 100) -> List[AgentTemplate]:
        """获取智能体模板列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[AgentTemplate]: 智能体模板列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有智能体模板
        if is_admin:
            return await self.template_repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的智能体模板
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        template_permissions = [p for p in user_permissions if p.resource_type == "agent_template"]
        
        if not template_permissions:
            # 返回所有公共模板
            return await self.template_repository.list_public_templates(self.db)
        
        # 获取有权限的智能体模板
        template_ids = [p.resource_id for p in template_permissions]
        templates = []
        for template_id in template_ids:
            template = await self.template_repository.get_by_id(template_id, self.db)
            if template:
                templates.append(template)
        
        # 添加公共模板
        public_templates = await self.template_repository.list_public_templates(self.db)
        for template in public_templates:
            if template not in templates:
                templates.append(template)
        
        return templates
    
    async def update_agent_template(self, template_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[AgentTemplate]:
        """更新智能体模板
        
        Args:
            template_id: 智能体模板ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[AgentTemplate]: 更新后的智能体模板实例或None
            
        Raises:
            HTTPException: 如果没有权限或智能体模板不存在
        """
        # 获取智能体模板
        template = await self.template_repository.get_by_id(template_id, self.db)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体模板不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "agent_template", template_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此智能体模板"
            )
        
        # 更新智能体模板
        return await self.template_repository.update(template_id, update_data, self.db)
    
    async def delete_agent_template(self, template_id: str, user_id: str) -> bool:
        """删除智能体模板
        
        Args:
            template_id: 智能体模板ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或智能体模板不存在
        """
        # 获取智能体模板
        template = await self.template_repository.get_by_id(template_id, self.db)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体模板不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "agent_template", template_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此智能体模板"
            )
        
        # 删除智能体模板
        return await self.template_repository.delete(template_id, self.db)
    
    # ==================== 智能体运行管理 ====================
    
    async def create_agent_run(self, run_data: Dict[str, Any], user_id: str) -> AgentRun:
        """创建智能体运行记录
        
        Args:
            run_data: 智能体运行数据
            user_id: 用户ID
            
        Returns:
            AgentRun: 创建的智能体运行实例
        """
        # 设置用户ID
        run_data["user_id"] = user_id
        
        # 创建智能体运行记录
        return await self.run_repository.create(run_data, self.db)
    
    async def get_agent_run(self, run_id: str, user_id: str) -> Optional[AgentRun]:
        """获取智能体运行记录
        
        Args:
            run_id: 智能体运行ID
            user_id: 用户ID
            
        Returns:
            Optional[AgentRun]: 获取的智能体运行实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取智能体运行记录
        run = await self.run_repository.get_by_id(run_id, self.db)
        if not run:
            return None
        
        # 检查权限（只允许创建者或管理员查看）
        if run.user_id != user_id and not await self._check_admin_permission(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此智能体运行记录"
            )
        
        return run
    
    async def list_agent_runs_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[AgentRun]:
        """获取用户的智能体运行记录列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[AgentRun]: 智能体运行记录列表
        """
        return await self.run_repository.list_by_user(user_id, skip, limit, self.db)
    
    async def list_agent_runs_by_definition(self, definition_id: str, user_id: str, skip: int = 0, limit: int = 100) -> List[AgentRun]:
        """获取指定智能体定义的运行记录列表
        
        Args:
            definition_id: 智能体定义ID
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[AgentRun]: 智能体运行记录列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查智能体定义权限
        has_permission = await self.permission_service.check_permission(
            "agent_definition", definition_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此智能体定义的运行记录"
            )
        
        # 获取运行记录列表
        return await self.run_repository.list_by_definition(definition_id, skip, limit, self.db)
    
    async def update_agent_run_status(self, run_id: str, status: str, result: Dict[str, Any] = None, user_id: str = None) -> Optional[AgentRun]:
        """更新智能体运行状态
        
        Args:
            run_id: 智能体运行ID
            status: 新状态
            result: 运行结果（可选）
            user_id: 用户ID（可选，用于权限检查）
            
        Returns:
            Optional[AgentRun]: 更新后的智能体运行实例或None
            
        Raises:
            HTTPException: 如果没有权限或智能体运行不存在
        """
        # 获取智能体运行记录
        run = await self.run_repository.get_by_id(run_id, self.db)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体运行记录不存在"
            )
        
        # 如果提供了用户ID，检查权限
        if user_id and run.user_id != user_id and not await self._check_admin_permission(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此智能体运行记录"
            )
        
        # 更新数据
        update_data = {"status": status}
        if result:
            update_data["result"] = result
        
        # 更新智能体运行记录
        return await self.run_repository.update(run_id, update_data, self.db)
    
    async def delete_agent_run(self, run_id: str, user_id: str) -> bool:
        """删除智能体运行记录
        
        Args:
            run_id: 智能体运行ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或智能体运行不存在
        """
        # 获取智能体运行记录
        run = await self.run_repository.get_by_id(run_id, self.db)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="智能体运行记录不存在"
            )
        
        # 检查权限（只允许创建者或管理员删除）
        if run.user_id != user_id and not await self._check_admin_permission(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此智能体运行记录"
            )
        
        # 删除智能体运行记录
        return await self.run_repository.delete(run_id, self.db)
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        user = await user_service.get_by_id(user_id)
        return user and user.role == "admin"
