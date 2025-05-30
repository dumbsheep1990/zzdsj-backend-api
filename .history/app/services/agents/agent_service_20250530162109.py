"""
智能体服务模块
处理智能体定义、模板和运行管理相关的业务逻辑
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.agent_definition import AgentDefinition
from app.models.agent_template import AgentTemplate
from app.models.agent_run import AgentRun

# 导入核心业务逻辑层
from app.core.agents.agent_manager import AgentManager

from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="agent", priority="high", description="智能体管理服务")
class AgentService:
    """智能体服务类 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化智能体服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.permission_service = permission_service
        
        # 使用核心业务逻辑层
        self.agent_manager = AgentManager(db)
    
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
        try:
            # 使用核心业务逻辑层创建智能体定义
            result = await self.agent_manager.create_agent_definition(
                name=definition_data.get("name"),
                description=definition_data.get("description", ""),
                agent_type=definition_data.get("agent_type", "assistant"),
                config=definition_data.get("config", {}),
                capabilities=definition_data.get("capabilities", []),
                user_id=user_id
            )
            
            if not result["success"]:
                if result.get("error_code") == "NAME_EXISTS":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"智能体名称 '{definition_data.get('name')}' 已存在"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result["error"]
                    )
            
            # 转换为旧的数据模型格式（兼容性）
            def_data = result["data"]
            definition = AgentDefinition(
                id=def_data["id"],
                name=def_data["name"],
                description=def_data["description"],
                agent_type=def_data["agent_type"],
                config=def_data["config"],
                capabilities=def_data["capabilities"],
                is_active=def_data["is_active"],
                created_at=def_data["created_at"],
                updated_at=def_data["updated_at"]
            )
            
            # 为创建者分配所有者权限
            await self.permission_service.ensure_owner_permission(
                "agent_definition", definition.id, user_id
            )
            
            return definition
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建智能体定义失败: {str(e)}"
            )
    
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
        try:
            # 使用核心业务逻辑层获取智能体定义
            result = await self.agent_manager.get_agent_definition(definition_id)
            
            if not result["success"]:
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
            
            # 转换为旧的数据模型格式（兼容性）
            def_data = result["data"]
            definition = AgentDefinition(
                id=def_data["id"],
                name=def_data["name"],
                description=def_data["description"],
                agent_type=def_data["agent_type"],
                config=def_data["config"],
                capabilities=def_data["capabilities"],
                is_active=def_data["is_active"],
                created_at=def_data["created_at"],
                updated_at=def_data["updated_at"]
            )
            
            return definition
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取智能体定义失败: {str(e)}"
            )
    
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
        try:
            # 使用核心业务逻辑层获取智能体定义列表并查找
            result = await self.agent_manager.list_agent_definitions(skip=0, limit=1000)
            
            if not result["success"]:
                return None
            
            # 查找匹配的定义
            target_definition = None
            for def_data in result["data"]["definitions"]:
                if def_data["name"] == name:
                    target_definition = def_data
                    break
            
            if not target_definition:
                return None
            
            # 检查权限
            has_permission = await self.permission_service.check_permission(
                "agent_definition", target_definition["id"], user_id, "read"
            ) or await self._check_admin_permission(user_id)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限访问此智能体定义"
                )
            
            # 转换为旧的数据模型格式（兼容性）
            definition = AgentDefinition(
                id=target_definition["id"],
                name=target_definition["name"],
                description=target_definition["description"],
                agent_type=target_definition["agent_type"],
                is_active=target_definition["is_active"],
                created_at=target_definition["created_at"],
                updated_at=target_definition["updated_at"]
            )
            
            return definition
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"通过名称获取智能体定义失败: {str(e)}"
            )
    
    async def list_agent_definitions(self, user_id: str, skip: int = 0, limit: int = 100) -> List[AgentDefinition]:
        """获取智能体定义列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[AgentDefinition]: 智能体定义列表
        """
        try:
            # 检查是否为管理员
            is_admin = await self._check_admin_permission(user_id)
            
            # 使用核心业务逻辑层获取智能体定义列表
            result = await self.agent_manager.list_agent_definitions(skip=skip, limit=limit)
            
            if not result["success"]:
                return []
            
            # 管理员可以查看所有智能体定义
            if is_admin:
                definitions = []
                for def_data in result["data"]["definitions"]:
                    definition = AgentDefinition(
                        id=def_data["id"],
                        name=def_data["name"],
                        description=def_data["description"],
                        agent_type=def_data["agent_type"],
                        is_active=def_data["is_active"],
                        created_at=def_data["created_at"],
                        updated_at=def_data["updated_at"]
                    )
                    definitions.append(definition)
                return definitions
            
            # 获取用户有权限的智能体定义
            user_permissions = await self.permission_service.list_user_permissions(user_id)
            agent_permissions = [p for p in user_permissions if p.resource_type == "agent_definition"]
            
            if not agent_permissions:
                return []
            
            # 过滤有权限的智能体定义
            permission_ids = set(p.resource_id for p in agent_permissions)
            definitions = []
            
            for def_data in result["data"]["definitions"]:
                if def_data["id"] in permission_ids:
                    definition = AgentDefinition(
                        id=def_data["id"],
                        name=def_data["name"],
                        description=def_data["description"],
                        agent_type=def_data["agent_type"],
                        is_active=def_data["is_active"],
                        created_at=def_data["created_at"],
                        updated_at=def_data["updated_at"]
                    )
                    definitions.append(definition)
            
            return definitions
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取智能体定义列表失败: {str(e)}"
            )
    
    async def list_agent_definitions_by_type(self, agent_type: str, user_id: str) -> List[AgentDefinition]:
        """获取指定类型的智能体定义列表
        
        Args:
            agent_type: 智能体类型
            user_id: 用户ID
            
        Returns:
            List[AgentDefinition]: 智能体定义列表
        """
        try:
            # 使用核心业务逻辑层获取智能体定义列表
            result = await self.agent_manager.list_agent_definitions(skip=0, limit=1000)
            
            if not result["success"]:
                return []
            
            # 过滤指定类型的定义
            filtered_definitions = [
                def_data for def_data in result["data"]["definitions"]
                if def_data["agent_type"] == agent_type
            ]
            
            # 检查是否为管理员
            is_admin = await self._check_admin_permission(user_id)
            
            if is_admin:
                definitions = []
                for def_data in filtered_definitions:
                    definition = AgentDefinition(
                        id=def_data["id"],
                        name=def_data["name"],
                        description=def_data["description"],
                        agent_type=def_data["agent_type"],
                        is_active=def_data["is_active"],
                        created_at=def_data["created_at"],
                        updated_at=def_data["updated_at"]
                    )
                    definitions.append(definition)
                return definitions
            
            # 过滤用户有权限的智能体定义
            result_definitions = []
            for def_data in filtered_definitions:
                has_permission = await self.permission_service.check_permission(
                    "agent_definition", def_data["id"], user_id, "read"
                )
                
                if has_permission:
                    definition = AgentDefinition(
                        id=def_data["id"],
                        name=def_data["name"],
                        description=def_data["description"],
                        agent_type=def_data["agent_type"],
                        is_active=def_data["is_active"],
                        created_at=def_data["created_at"],
                        updated_at=def_data["updated_at"]
                    )
                    result_definitions.append(definition)
            
            return result_definitions
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取指定类型智能体定义列表失败: {str(e)}"
            )
    
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
        try:
            # 检查智能体定义是否存在
            get_result = await self.agent_manager.get_agent_definition(definition_id)
            if not get_result["success"]:
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
            
            # 使用核心业务逻辑层更新智能体定义
            result = await self.agent_manager.update_agent_definition(
                definition_id=definition_id,
                name=update_data.get("name"),
                description=update_data.get("description"),
                agent_type=update_data.get("agent_type"),
                config=update_data.get("config"),
                capabilities=update_data.get("capabilities"),
                is_active=update_data.get("is_active")
            )
            
            if not result["success"]:
                if result.get("error_code") == "NAME_EXISTS":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="智能体名称已存在"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result["error"]
                    )
            
            # 转换为旧的数据模型格式（兼容性）
            def_data = result["data"]
            definition = AgentDefinition(
                id=def_data["id"],
                name=def_data["name"],
                description=def_data["description"],
                agent_type=def_data["agent_type"],
                config=def_data["config"],
                capabilities=def_data["capabilities"],
                is_active=def_data["is_active"],
                created_at=def_data["created_at"],
                updated_at=def_data["updated_at"]
            )
            
            return definition
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新智能体定义失败: {str(e)}"
            )
    
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
        try:
            # 检查智能体定义是否存在
            get_result = await self.agent_manager.get_agent_definition(definition_id)
            if not get_result["success"]:
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
            
            # 使用核心业务逻辑层删除智能体定义
            result = await self.agent_manager.delete_agent_definition(definition_id)
            
            if not result["success"]:
                if result.get("error_code") == "HAS_RUNS":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="智能体定义有关联的运行记录，无法删除"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result["error"]
                    )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除智能体定义失败: {str(e)}"
            )
    
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
        try:
            # 使用核心业务逻辑层创建智能体模板
            result = await self.agent_manager.create_agent_template(
                name=template_data.get("name"),
                description=template_data.get("description", ""),
                template_data=template_data.get("template_data", {}),
                is_public=template_data.get("is_public", False),
                user_id=user_id
            )
            
            if not result["success"]:
                if result.get("error_code") == "NAME_EXISTS":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"模板名称 '{template_data.get('name')}' 已存在"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result["error"]
                    )
            
            # 转换为旧的数据模型格式（兼容性）
            temp_data = result["data"]
            template = AgentTemplate(
                id=temp_data["id"],
                name=temp_data["name"],
                description=temp_data["description"],
                template_data=temp_data["template_data"],
                is_public=temp_data["is_public"],
                created_at=temp_data["created_at"],
                updated_at=temp_data["updated_at"]
            )
            
            # 为创建者分配所有者权限
            await self.permission_service.ensure_owner_permission(
                "agent_template", template.id, user_id
            )
            
            return template
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建智能体模板失败: {str(e)}"
            )
    
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
        try:
            # 使用核心业务逻辑层获取智能体模板
            result = await self.agent_manager.get_agent_template(template_id)
            
            if not result["success"]:
                return None
            
            # 检查权限（公共模板所有人都可以读取）
            temp_data = result["data"]
            if not temp_data.get("is_public", False):
                has_permission = await self.permission_service.check_permission(
                    "agent_template", template_id, user_id, "read"
                ) or await self._check_admin_permission(user_id)
                
                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="没有权限访问此智能体模板"
                    )
            
            # 转换为旧的数据模型格式（兼容性）
            template = AgentTemplate(
                id=temp_data["id"],
                name=temp_data["name"],
                description=temp_data["description"],
                template_data=temp_data["template_data"],
                is_public=temp_data["is_public"],
                created_at=temp_data["created_at"],
                updated_at=temp_data["updated_at"]
            )
            
            return template
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取智能体模板失败: {str(e)}"
            )
    
    # ==================== 智能体运行管理 ====================
    
    async def create_agent_run(self, run_data: Dict[str, Any], user_id: str) -> AgentRun:
        """创建智能体运行记录
        
        Args:
            run_data: 智能体运行数据
            user_id: 用户ID
            
        Returns:
            AgentRun: 创建的智能体运行实例
            
        Raises:
            HTTPException: 如果智能体定义不存在或没有权限
        """
        try:
            definition_id = run_data.get("definition_id")
            
            # 检查智能体定义是否存在
            def_result = await self.agent_manager.get_agent_definition(definition_id)
            if not def_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="智能体定义不存在"
                )
            
            # 检查权限
            has_permission = await self.permission_service.check_permission(
                "agent_definition", definition_id, user_id, "execute"
            ) or await self._check_admin_permission(user_id)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有权限执行此智能体"
                )
            
            # 使用核心业务逻辑层创建智能体运行记录
            result = await self.agent_manager.create_agent_run(
                definition_id=definition_id,
                input_data=run_data.get("input_data", {}),
                config=run_data.get("config", {}),
                user_id=user_id
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            # 转换为旧的数据模型格式（兼容性）
            run_result_data = result["data"]
            agent_run = AgentRun(
                id=run_result_data["id"],
                definition_id=run_result_data["definition_id"],
                status=run_result_data["status"],
                created_at=run_result_data["created_at"],
                updated_at=run_result_data["updated_at"]
            )
            
            return agent_run
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建智能体运行记录失败: {str(e)}"
            )
    
    # ==================== 辅助方法 ====================
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        try:
            # 这里应该调用权限服务来检查管理员权限
            # 简化实现，实际应该根据具体的权限系统
            return await self.permission_service.is_admin(user_id)
        except:
            return False
