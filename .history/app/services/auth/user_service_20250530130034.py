"""
用户服务模块
处理用户管理、认证和授权相关的业务逻辑
"""

from app.utils.service_decorators import register_service

import uuid
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from app.utils.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@register_service(service_type="user", priority="critical", description="用户管理和认证服务")
class UserService:
    """用户服务类"""
    
    def __init__(self, db: Session = Depends(get_db)):
        """初始化用户服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = UserRepository()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码
        
        Args:
            plain_password: 明文密码
            hashed_password: 哈希密码
            
        Returns:
            bool: 密码是否匹配
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希
        
        Args:
            password: 明文密码
            
        Returns:
            str: 哈希密码
        """
        return pwd_context.hash(password)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Optional[User]: 验证成功的用户或None
        """
        user = await self.repository.get_by_username(username, self.db)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌
        
        Args:
            data: 要编码的数据
            expires_delta: 过期时间增量
            
        Returns:
            str: JWT访问令牌
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    async def create_user(self, user_data: UserCreate) -> User:
        """创建新用户
        
        Args:
            user_data: 用户创建数据
            
        Returns:
            User: 创建的用户实例
        
        Raises:
            HTTPException: 如果用户名已存在
        """
        # 检查用户名是否已存在
        existing_user = await self.repository.get_by_username(user_data.username, self.db)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 创建新用户
        hashed_password = self.get_password_hash(user_data.password)
        user_dict = user_data.dict()
        user_dict.pop("password")
        user_dict["hashed_password"] = hashed_password
        user_dict["id"] = str(uuid.uuid4())
        
        return await self.repository.create(user_dict, self.db)
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[User]: 查找到的用户或None
        """
        return await self.repository.get_by_id(user_id, self.db)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 查找到的用户或None
        """
        return await self.repository.get_by_username(username, self.db)
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """获取用户列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[User]: 用户列表
        """
        return await self.repository.list_all(skip, limit, self.db)
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            user_data: 用户更新数据
            
        Returns:
            Optional[User]: 更新后的用户或None
        """
        # 获取现有用户
        existing_user = await self.repository.get_by_id(user_id, self.db)
        if not existing_user:
            return None
        
        # 准备更新数据
        update_data = user_data.dict(exclude_unset=True)
        
        # 如果提供了新密码，则哈希
        if "password" in update_data:
            hashed_password = self.get_password_hash(update_data.pop("password"))
            update_data["hashed_password"] = hashed_password
        
        return await self.repository.update(user_id, update_data, self.db)
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
        """
        return await self.repository.delete(user_id, self.db)
    
    async def assign_role(self, user_id: str, role: str) -> Optional[User]:
        """分配角色给用户
        
        Args:
            user_id: 用户ID
            role: 角色名称
            
        Returns:
            Optional[User]: 更新后的用户或None
        """
        # 获取现有用户
        existing_user = await self.repository.get_by_id(user_id, self.db)
        if not existing_user:
            return None
        
        # 更新角色
        existing_user.role = role
        self.db.commit()
        self.db.refresh(existing_user)
        
        return existing_user
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否具有特定权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称
            
        Returns:
            bool: 是否具有权限
        """
        user = await self.repository.get_by_id(user_id, self.db)
        if not user:
            return False
        
        # 管理员拥有所有权限
        if user.role == "admin":
            return True
        
        # 根据角色检查权限
        # 这里需要实现具体的权限检查逻辑，例如基于角色的权限映射
        # 这是一个简化示例
        role_permissions = {
            "user": ["read_own", "create_own"],
            "editor": ["read_own", "create_own", "update_own"],
            "admin": ["read_all", "create_all", "update_all", "delete_all"]
        }
        
        if user.role in role_permissions and permission in role_permissions[user.role]:
            return True
        
        return False
