"""
智能体管理器 - 核心业务逻辑
提供智能体定义、模板和运行的核心管理功能
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# 导入数据访问层
from app.repositories.agent_definition_repository import AgentDefinitionRepository
from app.repositories.agent_template_repository import AgentTemplateRepository
from app.repositories.agent_run_repository import AgentRunRepository

logger = logging.getLogger(__name__)


class AgentManager:
    """智能体管理器 - 核心业务逻辑类"""
    
    def __init__(self, db: Session):
        """初始化智能体管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.definition_repository = AgentDefinitionRepository()
        self.template_repository = AgentTemplateRepository()
        self.run_repository = AgentRunRepository()
        
    # ============ 智能体定义管理方法 ============
    
    async def create_agent_definition(
        self, 
        name: str,
        description: str = "",
        agent_type: str = "assistant",
        config: Dict[str, Any] = None,
        capabilities: List[Dict[str, Any]] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """创建智能体定义
        
        Args:
            name: 智能体名称
            description: 智能体描述
            agent_type: 智能体类型
            config: 智能体配置
            capabilities: 智能体能力列表
            user_id: 创建者ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证输入
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "智能体名称不能为空",
                    "error_code": "INVALID_NAME"
                }
            
            # 检查名称是否已存在
            existing_definition = await self.definition_repository.get_by_name(name.strip(), self.db)
            if existing_definition:
                return {
                    "success": False,
                    "error": "智能体名称已存在",
                    "error_code": "NAME_EXISTS"
                }
            
            # 准备智能体定义数据
            definition_data = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "description": description.strip() if description else "",
                "agent_type": agent_type,
                "config": config or {},
                "capabilities": capabilities or [],
                "is_active": True,
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 创建智能体定义
            definition = await self.definition_repository.create(definition_data, self.db)
            
            logger.info(f"智能体定义创建成功: {definition.id} - {definition.name}")
            
            return {
                "success": True,
                "data": {
                    "id": definition.id,
                    "name": definition.name,
                    "description": definition.description,
                    "agent_type": definition.agent_type,
                    "config": definition.config,
                    "capabilities": definition.capabilities,
                    "is_active": definition.is_active,
                    "created_at": definition.created_at,
                    "updated_at": definition.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建智能体定义失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建智能体定义失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_agent_definition(self, definition_id: str) -> Dict[str, Any]:
        """获取智能体定义详情
        
        Args:
            definition_id: 智能体定义ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            definition = await self.definition_repository.get_by_id(definition_id, self.db)
            if not definition:
                return {
                    "success": False,
                    "error": "智能体定义不存在",
                    "error_code": "DEFINITION_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": definition.id,
                    "name": definition.name,
                    "description": definition.description,
                    "agent_type": definition.agent_type,
                    "config": definition.config,
                    "capabilities": definition.capabilities,
                    "is_active": definition.is_active,
                    "created_at": definition.created_at,
                    "updated_at": definition.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取智能体定义失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取智能体定义失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def list_agent_definitions(
        self,
        agent_type: str = None,
        is_active: bool = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取智能体定义列表
        
        Args:
            agent_type: 智能体类型过滤
            is_active: 活跃状态过滤
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取智能体定义列表
            if agent_type:
                definitions = await self.definition_repository.list_by_type(agent_type, self.db)
            else:
                definitions = await self.definition_repository.list_all(skip, limit, self.db)
            
            # 应用活跃状态过滤
            if is_active is not None:
                definitions = [d for d in definitions if d.is_active == is_active]
            
            # 转换为标准格式
            definition_list = []
            for definition in definitions:
                definition_data = {
                    "id": definition.id,
                    "name": definition.name,
                    "description": definition.description,
                    "agent_type": definition.agent_type,
                    "is_active": definition.is_active,
                    "created_at": definition.created_at,
                    "updated_at": definition.updated_at
                }
                definition_list.append(definition_data)
            
            return {
                "success": True,
                "data": {
                    "definitions": definition_list,
                    "total": len(definition_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取智能体定义列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取智能体定义列表失败: {str(e)}",
                "error_code": "LIST_FAILED"
            }
    
    async def update_agent_definition(
        self,
        definition_id: str,
        name: str = None,
        description: str = None,
        agent_type: str = None,
        config: Dict[str, Any] = None,
        capabilities: List[Dict[str, Any]] = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """更新智能体定义
        
        Args:
            definition_id: 智能体定义ID
            name: 新名称
            description: 新描述
            agent_type: 新类型
            config: 新配置
            capabilities: 新能力列表
            is_active: 新状态
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查智能体定义是否存在
            definition = await self.definition_repository.get_by_id(definition_id, self.db)
            if not definition:
                return {
                    "success": False,
                    "error": "智能体定义不存在",
                    "error_code": "DEFINITION_NOT_FOUND"
                }
            
            # 准备更新数据
            update_data = {"updated_at": datetime.utcnow()}
            
            if name is not None:
                name = name.strip()
                if not name:
                    return {
                        "success": False,
                        "error": "智能体名称不能为空",
                        "error_code": "INVALID_NAME"
                    }
                
                # 检查名称冲突（排除当前定义）
                existing_definition = await self.definition_repository.get_by_name(name, self.db)
                if existing_definition and existing_definition.id != definition_id:
                    return {
                        "success": False,
                        "error": "智能体名称已存在",
                        "error_code": "NAME_EXISTS"
                    }
                
                update_data["name"] = name
            
            if description is not None:
                update_data["description"] = description.strip()
            
            if agent_type is not None:
                update_data["agent_type"] = agent_type
            
            if config is not None:
                update_data["config"] = config
            
            if capabilities is not None:
                update_data["capabilities"] = capabilities
            
            if is_active is not None:
                update_data["is_active"] = is_active
            
            # 更新智能体定义
            updated_definition = await self.definition_repository.update(definition_id, update_data, self.db)
            
            logger.info(f"智能体定义更新成功: {definition_id}")
            
            return {
                "success": True,
                "data": {
                    "id": updated_definition.id,
                    "name": updated_definition.name,
                    "description": updated_definition.description,
                    "agent_type": updated_definition.agent_type,
                    "config": updated_definition.config,
                    "capabilities": updated_definition.capabilities,
                    "is_active": updated_definition.is_active,
                    "created_at": updated_definition.created_at,
                    "updated_at": updated_definition.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新智能体定义失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新智能体定义失败: {str(e)}",
                "error_code": "UPDATE_FAILED"
            }
    
    async def delete_agent_definition(self, definition_id: str) -> Dict[str, Any]:
        """删除智能体定义
        
        Args:
            definition_id: 智能体定义ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查智能体定义是否存在
            definition = await self.definition_repository.get_by_id(definition_id, self.db)
            if not definition:
                return {
                    "success": False,
                    "error": "智能体定义不存在",
                    "error_code": "DEFINITION_NOT_FOUND"
                }
            
            # 检查是否有关联的运行记录
            runs = await self.run_repository.list_by_definition(definition_id, 0, 1, self.db)
            if runs:
                return {
                    "success": False,
                    "error": "智能体定义有关联的运行记录，无法删除",
                    "error_code": "HAS_RUNS"
                }
            
            # 删除智能体定义
            success = await self.definition_repository.delete(definition_id, self.db)
            
            if success:
                logger.info(f"智能体定义删除成功: {definition_id}")
                return {
                    "success": True,
                    "data": {"deleted_definition_id": definition_id}
                }
            else:
                return {
                    "success": False,
                    "error": "删除智能体定义失败",
                    "error_code": "DELETE_FAILED"
                }
            
        except Exception as e:
            logger.error(f"删除智能体定义失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除智能体定义失败: {str(e)}",
                "error_code": "DELETE_FAILED"
            }
    
    # ============ 智能体模板管理方法 ============
    
    async def create_agent_template(
        self,
        name: str,
        description: str = "",
        template_data: Dict[str, Any] = None,
        is_public: bool = False,
        user_id: str = None
    ) -> Dict[str, Any]:
        """创建智能体模板
        
        Args:
            name: 模板名称
            description: 模板描述
            template_data: 模板数据
            is_public: 是否公共模板
            user_id: 创建者ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证输入
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "模板名称不能为空",
                    "error_code": "INVALID_NAME"
                }
            
            # 检查名称是否已存在
            existing_template = await self.template_repository.get_by_name(name.strip(), self.db)
            if existing_template:
                return {
                    "success": False,
                    "error": "模板名称已存在",
                    "error_code": "NAME_EXISTS"
                }
            
            # 准备模板数据
            template_create_data = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "description": description.strip() if description else "",
                "template_data": template_data or {},
                "is_public": is_public,
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 创建智能体模板
            template = await self.template_repository.create(template_create_data, self.db)
            
            logger.info(f"智能体模板创建成功: {template.id} - {template.name}")
            
            return {
                "success": True,
                "data": {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "template_data": template.template_data,
                    "is_public": template.is_public,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建智能体模板失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建智能体模板失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_agent_template(self, template_id: str) -> Dict[str, Any]:
        """获取智能体模板详情
        
        Args:
            template_id: 模板ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            template = await self.template_repository.get_by_id(template_id, self.db)
            if not template:
                return {
                    "success": False,
                    "error": "智能体模板不存在",
                    "error_code": "TEMPLATE_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "template_data": template.template_data,
                    "is_public": template.is_public,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取智能体模板失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取智能体模板失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    # ============ 智能体运行管理方法 ============
    
    async def create_agent_run(
        self,
        definition_id: str,
        input_data: Dict[str, Any] = None,
        config: Dict[str, Any] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """创建智能体运行记录
        
        Args:
            definition_id: 智能体定义ID
            input_data: 输入数据
            config: 运行配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查智能体定义是否存在
            definition = await self.definition_repository.get_by_id(definition_id, self.db)
            if not definition:
                return {
                    "success": False,
                    "error": "智能体定义不存在",
                    "error_code": "DEFINITION_NOT_FOUND"
                }
            
            # 准备运行数据
            run_data = {
                "id": str(uuid.uuid4()),
                "definition_id": definition_id,
                "input_data": input_data or {},
                "config": config or {},
                "status": "pending",
                "result": {},
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 创建智能体运行记录
            run = await self.run_repository.create(run_data, self.db)
            
            logger.info(f"智能体运行记录创建成功: {run.id}")
            
            return {
                "success": True,
                "data": {
                    "id": run.id,
                    "definition_id": run.definition_id,
                    "status": run.status,
                    "created_at": run.created_at,
                    "updated_at": run.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建智能体运行记录失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建智能体运行记录失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def update_agent_run_status(
        self,
        run_id: str,
        status: str,
        result: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """更新智能体运行状态
        
        Args:
            run_id: 运行ID
            status: 新状态
            result: 运行结果
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查运行记录是否存在
            run = await self.run_repository.get_by_id(run_id, self.db)
            if not run:
                return {
                    "success": False,
                    "error": "智能体运行记录不存在",
                    "error_code": "RUN_NOT_FOUND"
                }
            
            # 准备更新数据
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if result is not None:
                update_data["result"] = result
            
            # 更新运行记录
            updated_run = await self.run_repository.update(run_id, update_data, self.db)
            
            logger.info(f"智能体运行状态更新成功: {run_id} -> {status}")
            
            return {
                "success": True,
                "data": {
                    "id": updated_run.id,
                    "status": updated_run.status,
                    "result": updated_run.result,
                    "updated_at": updated_run.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新智能体运行状态失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新智能体运行状态失败: {str(e)}",
                "error_code": "UPDATE_FAILED"
            } 