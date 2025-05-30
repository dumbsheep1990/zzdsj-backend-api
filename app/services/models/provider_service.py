"""
模型提供商服务模块
处理模型连接和配置管理相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.model_provider import ModelProvider
from app.repositories.model_provider_repository import ModelProviderRepository
from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="model-provider", priority="high", description="模型提供商管理服务")
class ModelProviderService:
    """模型提供商服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化模型提供商服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = ModelProviderRepository()
        self.permission_service = permission_service
    
    async def create_model_provider(self, provider_data: Dict[str, Any], user_id: str) -> ModelProvider:
        """创建模型提供商
        
        Args:
            provider_data: 模型提供商数据
            user_id: 用户ID
            
        Returns:
            ModelProvider: 创建的模型提供商实例
            
        Raises:
            HTTPException: 如果提供商名称已存在或没有权限
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以创建模型提供商"
            )
        
        # 检查提供商名称是否已存在
        existing_provider = await self.repository.get_by_name(
            provider_data.get("provider_name"), self.db
        )
        if existing_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"提供商名称 '{provider_data.get('provider_name')}' 已存在"
            )
        
        # 创建模型提供商
        return await self.repository.create(provider_data, self.db)
    
    async def get_model_provider(self, provider_id: str, user_id: str) -> Optional[ModelProvider]:
        """获取模型提供商
        
        Args:
            provider_id: 模型提供商ID
            user_id: 用户ID
            
        Returns:
            Optional[ModelProvider]: 获取的模型提供商实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取模型提供商
        provider = await self.repository.get_by_id(provider_id, self.db)
        if not provider:
            return None
        
        # 处理敏感字段
        return self._sanitize_provider(provider, user_id)
    
    async def get_model_provider_by_name(self, provider_name: str, user_id: str) -> Optional[ModelProvider]:
        """通过名称获取模型提供商
        
        Args:
            provider_name: 模型提供商名称
            user_id: 用户ID
            
        Returns:
            Optional[ModelProvider]: 获取的模型提供商实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取模型提供商
        provider = await self.repository.get_by_name(provider_name, self.db)
        if not provider:
            return None
        
        # 处理敏感字段
        return self._sanitize_provider(provider, user_id)
    
    async def list_model_providers(self, user_id: str, skip: int = 0, limit: int = 100) -> List[ModelProvider]:
        """获取模型提供商列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[ModelProvider]: 模型提供商列表
        """
        # 获取所有模型提供商
        providers = await self.repository.list_all(skip, limit, self.db)
        
        # 处理敏感字段
        return [self._sanitize_provider(provider, user_id) for provider in providers]
    
    async def list_active_model_providers(self, user_id: str) -> List[ModelProvider]:
        """获取所有激活的模型提供商列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[ModelProvider]: 激活的模型提供商列表
        """
        # 获取激活的模型提供商
        providers = await self.repository.list_active(self.db)
        
        # 处理敏感字段
        return [self._sanitize_provider(provider, user_id) for provider in providers]
    
    async def update_model_provider(self, provider_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[ModelProvider]:
        """更新模型提供商
        
        Args:
            provider_id: 模型提供商ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[ModelProvider]: 更新后的模型提供商实例或None
            
        Raises:
            HTTPException: 如果没有权限或模型提供商不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以更新模型提供商"
            )
        
        # 获取模型提供商
        provider = await self.repository.get_by_id(provider_id, self.db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型提供商不存在"
            )
        
        # 更新模型提供商
        updated = await self.repository.update(provider_id, update_data, self.db)
        return self._sanitize_provider(updated, user_id) if updated else None
    
    async def set_api_key(self, provider_id: str, api_key: str, user_id: str) -> Optional[ModelProvider]:
        """设置API密钥
        
        Args:
            provider_id: 模型提供商ID
            api_key: API密钥
            user_id: 用户ID
            
        Returns:
            Optional[ModelProvider]: 更新后的模型提供商实例或None
            
        Raises:
            HTTPException: 如果没有权限或模型提供商不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以设置API密钥"
            )
        
        # 获取模型提供商
        provider = await self.repository.get_by_id(provider_id, self.db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型提供商不存在"
            )
        
        # 更新API密钥
        update_data = {"api_key": api_key}
        updated = await self.repository.update(provider_id, update_data, self.db)
        return self._sanitize_provider(updated, user_id) if updated else None
    
    async def activate_model_provider(self, provider_id: str, user_id: str) -> Optional[ModelProvider]:
        """激活模型提供商
        
        Args:
            provider_id: 模型提供商ID
            user_id: 用户ID
            
        Returns:
            Optional[ModelProvider]: 更新后的模型提供商实例或None
            
        Raises:
            HTTPException: 如果没有权限或模型提供商不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以激活模型提供商"
            )
        
        # 获取模型提供商
        provider = await self.repository.get_by_id(provider_id, self.db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型提供商不存在"
            )
        
        # 更新状态
        update_data = {"is_active": True}
        updated = await self.repository.update(provider_id, update_data, self.db)
        return self._sanitize_provider(updated, user_id) if updated else None
    
    async def deactivate_model_provider(self, provider_id: str, user_id: str) -> Optional[ModelProvider]:
        """停用模型提供商
        
        Args:
            provider_id: 模型提供商ID
            user_id: 用户ID
            
        Returns:
            Optional[ModelProvider]: 更新后的模型提供商实例或None
            
        Raises:
            HTTPException: 如果没有权限或模型提供商不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以停用模型提供商"
            )
        
        # 获取模型提供商
        provider = await self.repository.get_by_id(provider_id, self.db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型提供商不存在"
            )
        
        # 更新状态
        update_data = {"is_active": False}
        updated = await self.repository.update(provider_id, update_data, self.db)
        return self._sanitize_provider(updated, user_id) if updated else None
    
    async def delete_model_provider(self, provider_id: str, user_id: str) -> bool:
        """删除模型提供商
        
        Args:
            provider_id: 模型提供商ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或模型提供商不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以删除模型提供商"
            )
        
        # 获取模型提供商
        provider = await self.repository.get_by_id(provider_id, self.db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型提供商不存在"
            )
        
        # 删除模型提供商
        return await self.repository.delete(provider_id, self.db)
    
    async def validate_connection(self, provider_id: str, user_id: str) -> Dict[str, Any]:
        """验证与模型提供商的连接
        
        Args:
            provider_id: 模型提供商ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 连接验证结果
            
        Raises:
            HTTPException: 如果没有权限或模型提供商不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以验证模型提供商连接"
            )
        
        # 获取模型提供商（包含敏感信息）
        provider = await self.repository.get_by_id(provider_id, self.db)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型提供商不存在"
            )
        
        # 实现验证逻辑
        # 这里需要根据不同的模型提供商类型实现不同的验证逻辑
        try:
            provider_type = provider.provider_type
            api_key = provider.api_key
            
            # 验证连接
            # 简化示例，实际实现需要根据不同提供商调用不同API
            if provider_type == "openai":
                # 验证OpenAI连接
                return await self._validate_openai_connection(api_key)
            elif provider_type == "anthropic":
                # 验证Anthropic连接
                return await self._validate_anthropic_connection(api_key)
            elif provider_type == "local":
                # 验证本地模型连接
                return await self._validate_local_connection(provider.endpoint_url)
            else:
                raise ValueError(f"不支持的提供商类型: {provider_type}")
                
        except Exception as e:
            # 返回验证失败结果
            return {
                "success": False,
                "message": f"连接验证失败: {str(e)}",
                "provider_id": provider_id,
                "provider_name": provider.provider_name
            }
    
    async def _validate_openai_connection(self, api_key: str) -> Dict[str, Any]:
        """验证OpenAI连接
        
        Args:
            api_key: API密钥
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        # 实现OpenAI连接验证逻辑
        # 简化示例
        return {
            "success": True,
            "message": "OpenAI连接验证成功",
            "provider_type": "openai",
            "models_available": ["gpt-4", "gpt-3.5-turbo"]
        }
    
    async def _validate_anthropic_connection(self, api_key: str) -> Dict[str, Any]:
        """验证Anthropic连接
        
        Args:
            api_key: API密钥
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        # 实现Anthropic连接验证逻辑
        # 简化示例
        return {
            "success": True,
            "message": "Anthropic连接验证成功",
            "provider_type": "anthropic",
            "models_available": ["claude-3-opus", "claude-3-sonnet"]
        }
    
    async def _validate_local_connection(self, endpoint_url: str) -> Dict[str, Any]:
        """验证本地模型连接
        
        Args:
            endpoint_url: 端点URL
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        # 实现本地模型连接验证逻辑
        # 简化示例
        return {
            "success": True,
            "message": "本地模型连接验证成功",
            "provider_type": "local",
            "endpoint": endpoint_url
        }
    
    async def _sanitize_provider(self, provider: ModelProvider, user_id: str) -> ModelProvider:
        """处理模型提供商的敏感字段
        
        Args:
            provider: 模型提供商实例
            user_id: 用户ID
            
        Returns:
            ModelProvider: 处理后的模型提供商实例
        """
        if not provider:
            return None
            
        # 创建一个副本，避免修改原始对象
        # 隐藏API密钥，除非用户是管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin and hasattr(provider, 'api_key'):
            # 隐藏API密钥
            provider.api_key = "********" if provider.api_key else None
        
        return provider
    
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
