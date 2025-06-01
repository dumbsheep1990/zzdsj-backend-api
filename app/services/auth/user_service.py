"""
用户服务模块
处理用户管理、认证和授权相关的业务逻辑
重构版本：调用core层业务逻辑，符合分层架构原则
"""

from app.utils.service_decorators import register_service

import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.utils.core.database import get_db
# 导入core层业务逻辑
from core.auth import AuthService

# 导入模型类型（仅用于类型提示和API兼容性）
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse

logger = logging.getLogger(__name__)


@register_service(service_type="user", priority="critical", description="用户管理和认证服务")
class UserService:
    """用户服务类 - Services层，调用Core层业务逻辑"""
    
    def __init__(self, db: Session = Depends(get_db)):
        """初始化用户服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        # 使用core层的AuthService
        self.auth_service = AuthService(db)
    
    # ============ 认证相关方法 ============
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Optional[Dict[str, Any]]: 验证成功的用户信息或None
        """
        try:
            # 使用core层进行用户认证
            result = await self.auth_service.login(username, password)
            if result["success"]:
                return result["data"]["user"]
            else:
                logger.warning(f"用户认证失败: {username}, 错误: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"用户认证过程中出错: {str(e)}")
            return None
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌
        
        Args:
            data: 要编码的数据
            expires_delta: 过期时间增量（此参数为兼容性保留，实际由core层管理）
            
        Returns:
            str: JWT访问令牌
        """
        # 注意：这个方法主要为了API兼容性保留
        # 实际的令牌创建逻辑在core层的auth_service.login()中完成
        logger.warning("create_access_token方法仅为兼容性保留，建议使用auth_service.login()获取完整认证信息")
        return ""
    
    # ============ 用户管理方法 ============
    
    async def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """创建新用户
        
        Args:
            user_data: 用户创建数据
            
        Returns:
            Dict[str, Any]: 创建的用户信息
        
        Raises:
            HTTPException: 如果创建失败
        """
        try:
            result = await self.auth_service.register_user(
                username=user_data.username,
                email=getattr(user_data, 'email', f"{user_data.username}@localhost"),
                password=user_data.password,
                full_name=getattr(user_data, 'full_name', None),
                role=getattr(user_data, 'role', 'user')
            )
            
            if result["success"]:
                return result["data"]
            else:
                error_code = result.get("error_code", "UNKNOWN_ERROR")
                if error_code == "USERNAME_EXISTS":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="用户名已存在"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=result.get("error", "创建用户失败")
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建用户过程中发生错误"
            )
    
    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 查找到的用户信息或None
        """
        try:
            result = await self.auth_service.user_manager.get_user_profile(user_id)
            if result["success"]:
                return result["data"]
            else:
                logger.warning(f"获取用户失败: {user_id}, 错误: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"获取用户过程中出错: {str(e)}")
            return None
    
    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[Dict[str, Any]]: 查找到的用户信息或None
        """
        # Core层的UserManager目前没有直接按用户名查询的方法
        # 这里可以通过认证来获取用户信息（虽然需要密码）
        # 更好的做法是扩展core层添加按用户名查询的方法
        logger.warning("通过用户名获取用户功能需要扩展core层UserManager")
        return None
    
    async def list_users(self, skip: int = 0, limit: int = 100, 
                        role: str = None, is_active: bool = None) -> List[Dict[str, Any]]:
        """获取用户列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            role: 角色过滤
            is_active: 活跃状态过滤
            
        Returns:
            List[Dict[str, Any]]: 用户列表
        """
        try:
            result = await self.auth_service.user_manager.list_users(
                skip=skip,
                limit=limit,
                role=role,
                is_active=is_active
            )
            
            if result["success"]:
                return result["data"]["users"]
            else:
                logger.error(f"获取用户列表失败: {result.get('error')}")
                return []
        except Exception as e:
            logger.error(f"获取用户列表过程中出错: {str(e)}")
            return []
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[Dict[str, Any]]:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            user_data: 用户更新数据
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的用户信息或None
        """
        try:
            # 准备更新数据
            update_data = user_data.dict(exclude_unset=True)
            
            # 如果包含密码，需要单独处理
            if "password" in update_data:
                password = update_data.pop("password")
                # 密码更新需要验证旧密码，这里暂时无法处理
                logger.warning("密码更新需要通过change_password方法处理")
            
            if update_data:
                result = await self.auth_service.update_profile(user_id, **update_data)
                if result["success"]:
                    return result["data"]
                else:
                    logger.error(f"更新用户失败: {result.get('error')}")
                    return None
            else:
                # 没有需要更新的数据，返回当前用户信息
                return await self.get_by_id(user_id)
                
        except Exception as e:
            logger.error(f"更新用户过程中出错: {str(e)}")
            return None
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改用户密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            bool: 是否成功修改
        """
        try:
            result = await self.auth_service.change_password(user_id, old_password, new_password)
            if result["success"]:
                return True
            else:
                logger.warning(f"修改密码失败: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"修改密码过程中出错: {str(e)}")
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
        """
        # Core层暂未实现用户删除功能
        logger.warning("用户删除功能尚未在core层实现")
        return False
    
    # ============ 角色和权限管理 ============
    
    async def assign_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        """分配角色给用户
        
        Args:
            user_id: 用户ID
            role: 角色名称
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的用户信息或None
        """
        # 这里需要使用权限管理器分配角色
        # 目前core层的PermissionManager使用角色ID而不是角色名称
        logger.warning("角色分配功能需要扩展core层以支持角色名称")
        return None
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否具有特定权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称
            
        Returns:
            bool: 是否具有权限
        """
        try:
            return await self.auth_service.check_permission(user_id, permission)
        except Exception as e:
            logger.error(f"检查权限过程中出错: {str(e)}")
            return False
    
    async def check_resource_permission(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户是否具有特定资源的操作权限
        
        Args:
            user_id: 用户ID
            resource: 资源名称
            action: 操作名称
            
        Returns:
            bool: 是否具有权限
        """
        try:
            return await self.auth_service.check_resource_permission(user_id, resource, action)
        except Exception as e:
            logger.error(f"检查资源权限过程中出错: {str(e)}")
            return False
    
    # ============ 兼容性方法 ============
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码（兼容性方法）
        
        Args:
            plain_password: 明文密码
            hashed_password: 哈希密码
            
        Returns:
            bool: 密码是否匹配
        """
        # 保留此方法用于向后兼容，但实际密码验证应通过core层处理
        logger.warning("verify_password方法仅为兼容性保留，建议使用authenticate_user")
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希（兼容性方法）
        
        Args:
            password: 明文密码
            
        Returns:
            str: 哈希密码
        """
        # 保留此方法用于向后兼容，但实际密码处理应通过core层处理
        logger.warning("get_password_hash方法仅为兼容性保留，密码哈希应由core层处理")
        try:
            import bcrypt
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        except Exception as e:
            logger.error(f"密码哈希失败: {str(e)}")
            return ""
