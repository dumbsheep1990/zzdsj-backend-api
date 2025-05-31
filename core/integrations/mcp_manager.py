"""
核心业务逻辑层 - MCP集成管理
处理MCP服务集成的核心业务逻辑，包括配置管理、连接验证、服务发现等
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import json
import asyncio
from datetime import datetime

from app.repositories.mcp_integration_repository import MCPIntegrationRepository


class MCPIntegrationManager:
    """MCP集成管理器 - 核心业务逻辑层"""
    
    def __init__(self, db: Session):
        """初始化MCP集成管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = MCPIntegrationRepository()
    
    async def create_integration(
        self,
        server_name: str,
        server_type: str,
        connection_config: Dict[str, Any],
        auth_config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建MCP服务集成配置
        
        Args:
            server_name: 服务器名称
            server_type: 服务器类型
            connection_config: 连接配置
            auth_config: 认证配置
            description: 描述
            is_active: 是否活跃
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果，包含success字段和data/error信息
        """
        try:
            # 检查服务器名称是否已存在
            existing = await self.repository.get_by_server_name(server_name, self.db)
            if existing:
                return {
                    "success": False,
                    "error": f"服务器名称 '{server_name}' 已存在",
                    "error_code": "INTEGRATION_NAME_EXISTS"
                }
            
            # 验证连接配置
            validation_result = await self._validate_connection_config(server_type, connection_config)
            if not validation_result["success"]:
                return validation_result
            
            # 创建集成配置数据
            integration_data = {
                "server_name": server_name,
                "server_type": server_type,
                "connection_config": connection_config,
                "auth_config": auth_config or {},
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
                    "server_name": integration.server_name,
                    "server_type": integration.server_type,
                    "connection_config": integration.connection_config,
                    "auth_config": self._hide_sensitive_auth_info(integration.auth_config),
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
                "error": f"创建MCP集成配置失败: {str(e)}"
            }
    
    async def get_integration(self, integration_id: str) -> Dict[str, Any]:
        """获取MCP集成配置
        
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
                    "server_name": integration.server_name,
                    "server_type": integration.server_type,
                    "connection_config": integration.connection_config,
                    "auth_config": self._hide_sensitive_auth_info(integration.auth_config),
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
                "error": f"获取MCP集成配置失败: {str(e)}"
            }
    
    async def get_integration_with_credentials(self, integration_id: str) -> Dict[str, Any]:
        """获取包含完整认证信息的MCP集成配置
        
        Args:
            integration_id: 集成配置ID
            
        Returns:
            Dict[str, Any]: 操作结果（包含完整认证信息）
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
                    "server_name": integration.server_name,
                    "server_type": integration.server_type,
                    "connection_config": integration.connection_config,
                    "auth_config": integration.auth_config,  # 包含完整认证信息
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
                "error": f"获取MCP集成配置失败: {str(e)}"
            }
    
    async def get_integration_by_server_name(self, server_name: str) -> Dict[str, Any]:
        """通过服务器名称获取集成配置
        
        Args:
            server_name: 服务器名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            integration = await self.repository.get_by_server_name(server_name, self.db)
            if not integration:
                return {
                    "success": False,
                    "error": "集成配置不存在"
                }
            
            return {
                "success": True,
                "data": {
                    "id": integration.id,
                    "server_name": integration.server_name,
                    "server_type": integration.server_type,
                    "connection_config": integration.connection_config,
                    "auth_config": self._hide_sensitive_auth_info(integration.auth_config),
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
                "error": f"获取MCP集成配置失败: {str(e)}"
            }
    
    async def list_integrations(
        self,
        skip: int = 0,
        limit: int = 100,
        server_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """获取集成配置列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            server_type: 服务器类型过滤
            is_active: 活跃状态过滤
            
        Returns:
            Dict[str, Any]: 操作结果，包含集成配置列表和总数
        """
        try:
            integrations = await self.repository.list_all(skip, limit, self.db)
            
            # 应用过滤条件
            filtered_integrations = []
            for integration in integrations:
                if server_type and integration.server_type != server_type:
                    continue
                if is_active is not None and integration.is_active != is_active:
                    continue
                
                integration_data = {
                    "id": integration.id,
                    "server_name": integration.server_name,
                    "server_type": integration.server_type,
                    "connection_config": integration.connection_config,
                    "auth_config": self._hide_sensitive_auth_info(integration.auth_config),
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
                "error": f"获取MCP集成配置列表失败: {str(e)}"
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
            
            # 如果更新服务器名称，检查是否冲突
            if "server_name" in update_data and update_data["server_name"] != existing.server_name:
                name_conflict = await self.repository.get_by_server_name(
                    update_data["server_name"], self.db
                )
                if name_conflict:
                    return {
                        "success": False,
                        "error": f"服务器名称 '{update_data['server_name']}' 已存在",
                        "error_code": "INTEGRATION_NAME_EXISTS"
                    }
            
            # 验证连接配置（如果有更新）
            if "connection_config" in update_data:
                server_type = update_data.get("server_type", existing.server_type)
                validation_result = await self._validate_connection_config(
                    server_type, update_data["connection_config"]
                )
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
                    "server_name": integration.server_name,
                    "server_type": integration.server_type,
                    "connection_config": integration.connection_config,
                    "auth_config": self._hide_sensitive_auth_info(integration.auth_config),
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
                "error": f"更新MCP集成配置失败: {str(e)}"
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
                "error": f"删除MCP集成配置失败: {str(e)}"
            }
    
    async def test_connection(self, integration_id: str) -> Dict[str, Any]:
        """测试集成连接
        
        Args:
            integration_id: 集成配置ID
            
        Returns:
            Dict[str, Any]: 连接测试结果
        """
        try:
            # 获取完整认证信息
            result = await self.get_integration_with_credentials(integration_id)
            if not result["success"]:
                return result
            
            integration_data = result["data"]
            
            # 根据服务器类型测试连接
            connection_result = await self._test_mcp_connection(
                integration_data["server_type"],
                integration_data["connection_config"],
                integration_data["auth_config"]
            )
            
            return connection_result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"测试MCP连接失败: {str(e)}"
            }
    
    # ============ 私有辅助方法 ============
    
    def _hide_sensitive_auth_info(self, auth_config: Dict[str, Any]) -> Dict[str, Any]:
        """隐藏敏感认证信息
        
        Args:
            auth_config: 认证配置
            
        Returns:
            Dict[str, Any]: 隐藏敏感信息后的配置
        """
        if not auth_config:
            return {}
        
        hidden_config = auth_config.copy()
        sensitive_fields = ["password", "token", "secret", "key", "api_key"]
        
        for field in sensitive_fields:
            if field in hidden_config:
                hidden_config[field] = "***"
        
        return hidden_config
    
    async def _validate_connection_config(
        self,
        server_type: str,
        connection_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证连接配置
        
        Args:
            server_type: 服务器类型
            connection_config: 连接配置
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            required_fields = {
                "stdio": ["command"],
                "sse": ["url"],
                "websocket": ["url"]
            }
            
            if server_type not in required_fields:
                return {
                    "success": False,
                    "error": f"不支持的服务器类型: {server_type}"
                }
            
            # 检查必需字段
            for field in required_fields[server_type]:
                if field not in connection_config:
                    return {
                        "success": False,
                        "error": f"缺少必需的连接配置字段: {field}"
                    }
            
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"验证连接配置失败: {str(e)}"
            }
    
    async def _test_mcp_connection(
        self,
        server_type: str,
        connection_config: Dict[str, Any],
        auth_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """测试MCP连接
        
        Args:
            server_type: 服务器类型
            connection_config: 连接配置
            auth_config: 认证配置
            
        Returns:
            Dict[str, Any]: 连接测试结果
        """
        try:
            # 这里应该实现实际的MCP连接测试逻辑
            # 目前返回模拟结果
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            return {
                "success": True,
                "data": {
                    "connected": True,
                    "server_type": server_type,
                    "response_time_ms": 100,
                    "server_info": {
                        "version": "1.0.0",
                        "capabilities": ["tools", "resources", "prompts"]
                    }
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"MCP连接测试失败: {str(e)}"
            } 