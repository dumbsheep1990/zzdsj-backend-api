"""
核心业务逻辑层 - LlamaIndex集成管理
处理LlamaIndex集成的核心业务逻辑，包括配置管理、索引管理、检索优化等
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from app.repositories.llamaindex_integration_repository import LlamaIndexIntegrationRepository


class LlamaIndexIntegrationManager:
    """LlamaIndex集成管理器 - 核心业务逻辑层"""
    
    def __init__(self, db: Session):
        """初始化LlamaIndex集成管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = LlamaIndexIntegrationRepository()
    
    async def create_integration(
        self,
        name: str,
        service_type: str,
        config: Dict[str, Any],
        description: Optional[str] = None,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建LlamaIndex集成配置
        
        Args:
            name: 集成名称
            service_type: 服务类型（如index, embedding, llm等）
            config: 配置信息
            description: 描述
            is_active: 是否活跃
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查名称是否已存在
            existing = await self.repository.get_by_name(name, self.db)
            if existing:
                return {
                    "success": False,
                    "error": f"集成名称 '{name}' 已存在",
                    "error_code": "INTEGRATION_NAME_EXISTS"
                }
            
            # 验证配置
            validation_result = await self._validate_config(service_type, config)
            if not validation_result["success"]:
                return validation_result
            
            # 创建集成配置数据
            integration_data = {
                "name": name,
                "service_type": service_type,
                "config": config,
                "description": description,
                "is_active": is_active,
                "metadata": metadata or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 保存到数据库
            integration = await self.repository.create(integration_data, self.db)
            
            return {
                "success": True,
                "data": {
                    "id": integration.id,
                    "name": integration.name,
                    "service_type": integration.service_type,
                    "config": self._hide_sensitive_config(integration.config),
                    "description": integration.description,
                    "is_active": integration.is_active,
                    "metadata": integration.metadata,
                    "created_at": integration.created_at.isoformat() if integration.created_at else None,
                    "updated_at": integration.updated_at.isoformat() if integration.updated_at else None
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"创建LlamaIndex集成配置失败: {str(e)}"
            }
    
    async def get_integration(self, integration_id: str) -> Dict[str, Any]:
        """获取集成配置
        
        Args:
            integration_id: 集成配置ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            integration = await self.repository.get_by_id(integration_id, self.db)
            if not integration:
                return {
                    "success": False,
                    "error": "集成配置不存在"
                }
            
            return {
                "success": True,
                "data": {
                    "id": integration.id,
                    "name": integration.name,
                    "service_type": integration.service_type,
                    "config": self._hide_sensitive_config(integration.config),
                    "description": integration.description,
                    "is_active": integration.is_active,
                    "metadata": integration.metadata,
                    "created_at": integration.created_at.isoformat() if integration.created_at else None,
                    "updated_at": integration.updated_at.isoformat() if integration.updated_at else None
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取LlamaIndex集成配置失败: {str(e)}"
            }
    
    async def get_integration_by_name(self, name: str) -> Dict[str, Any]:
        """通过名称获取集成配置
        
        Args:
            name: 集成名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            integration = await self.repository.get_by_name(name, self.db)
            if not integration:
                return {
                    "success": False,
                    "error": "集成配置不存在"
                }
            
            return {
                "success": True,
                "data": {
                    "id": integration.id,
                    "name": integration.name,
                    "service_type": integration.service_type,
                    "config": self._hide_sensitive_config(integration.config),
                    "description": integration.description,
                    "is_active": integration.is_active,
                    "metadata": integration.metadata,
                    "created_at": integration.created_at.isoformat() if integration.created_at else None,
                    "updated_at": integration.updated_at.isoformat() if integration.updated_at else None
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取LlamaIndex集成配置失败: {str(e)}"
            }
    
    async def list_integrations(
        self,
        skip: int = 0,
        limit: int = 100,
        service_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """获取集成配置列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            service_type: 服务类型过滤
            is_active: 活跃状态过滤
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            integrations = await self.repository.list_all(skip, limit, self.db)
            
            # 应用过滤条件
            filtered_integrations = []
            for integration in integrations:
                if service_type and integration.service_type != service_type:
                    continue
                if is_active is not None and integration.is_active != is_active:
                    continue
                
                integration_data = {
                    "id": integration.id,
                    "name": integration.name,
                    "service_type": integration.service_type,
                    "config": self._hide_sensitive_config(integration.config),
                    "description": integration.description,
                    "is_active": integration.is_active,
                    "metadata": integration.metadata,
                    "created_at": integration.created_at.isoformat() if integration.created_at else None,
                    "updated_at": integration.updated_at.isoformat() if integration.updated_at else None
                }
                filtered_integrations.append(integration_data)
            
            return {
                "success": True,
                "data": {
                    "integrations": filtered_integrations,
                    "total": len(filtered_integrations),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取LlamaIndex集成配置列表失败: {str(e)}"
            }
    
    async def update_integration(
        self,
        integration_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新集成配置
        
        Args:
            integration_id: 集成配置ID
            update_data: 更新数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查集成配置是否存在
            existing = await self.repository.get_by_id(integration_id, self.db)
            if not existing:
                return {
                    "success": False,
                    "error": "集成配置不存在"
                }
            
            # 如果更新名称，检查是否冲突
            if "name" in update_data and update_data["name"] != existing.name:
                name_conflict = await self.repository.get_by_name(update_data["name"], self.db)
                if name_conflict:
                    return {
                        "success": False,
                        "error": f"集成名称 '{update_data['name']}' 已存在",
                        "error_code": "INTEGRATION_NAME_EXISTS"
                    }
            
            # 验证配置（如果有更新）
            if "config" in update_data:
                service_type = update_data.get("service_type", existing.service_type)
                validation_result = await self._validate_config(service_type, update_data["config"])
                if not validation_result["success"]:
                    return validation_result
            
            # 添加更新时间
            update_data["updated_at"] = datetime.utcnow()
            
            # 更新集成配置
            integration = await self.repository.update(integration_id, update_data, self.db)
            
            return {
                "success": True,
                "data": {
                    "id": integration.id,
                    "name": integration.name,
                    "service_type": integration.service_type,
                    "config": self._hide_sensitive_config(integration.config),
                    "description": integration.description,
                    "is_active": integration.is_active,
                    "metadata": integration.metadata,
                    "created_at": integration.created_at.isoformat() if integration.created_at else None,
                    "updated_at": integration.updated_at.isoformat() if integration.updated_at else None
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"更新LlamaIndex集成配置失败: {str(e)}"
            }
    
    async def delete_integration(self, integration_id: str) -> Dict[str, Any]:
        """删除集成配置
        
        Args:
            integration_id: 集成配置ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查集成配置是否存在
            existing = await self.repository.get_by_id(integration_id, self.db)
            if not existing:
                return {
                    "success": False,
                    "error": "集成配置不存在"
                }
            
            # 删除集成配置
            await self.repository.delete(integration_id, self.db)
            
            return {
                "success": True,
                "data": {"deleted_id": integration_id}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"删除LlamaIndex集成配置失败: {str(e)}"
            }
    
    # ============ 私有辅助方法 ============
    
    def _hide_sensitive_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """隐藏敏感配置信息
        
        Args:
            config: 配置信息
            
        Returns:
            Dict[str, Any]: 隐藏敏感信息后的配置
        """
        if not config:
            return {}
        
        hidden_config = config.copy()
        sensitive_fields = ["api_key", "token", "password", "secret", "credentials"]
        
        for field in sensitive_fields:
            if field in hidden_config:
                hidden_config[field] = "***"
        
        return hidden_config
    
    async def _validate_config(
        self,
        service_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证配置信息
        
        Args:
            service_type: 服务类型
            config: 配置信息
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 根据不同服务类型验证配置
            required_fields = {
                "index": ["index_type"],
                "embedding": ["model_name"],
                "llm": ["model_name"],
                "retriever": ["retriever_type"],
                "storage": ["storage_type"]
            }
            
            if service_type not in required_fields:
                return {
                    "success": False,
                    "error": f"不支持的服务类型: {service_type}"
                }
            
            # 检查必需字段
            for field in required_fields[service_type]:
                if field not in config:
                    return {
                        "success": False,
                        "error": f"缺少必需的配置字段: {field}"
                    }
            
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"验证配置失败: {str(e)}"
            } 