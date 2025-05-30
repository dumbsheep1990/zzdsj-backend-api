"""
用户管理器
提供用户管理的核心业务逻辑
"""

import hashlib
import secrets
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserManager:
    """用户管理器 - Core层业务逻辑"""
    
    def __init__(self, db: Session):
        """初始化用户管理器"""
        self.db = db
        self.repository = UserRepository(db)
    
    # ============ 用户创建和管理 ============
    
    async def create_user(self, username: str, email: str, password: str,
                         full_name: str = None, role: str = "user",
                         is_active: bool = True) -> Dict[str, Any]:
        """创建用户 - 业务逻辑层"""
        try:
            # 业务规则验证
            if await self.repository.get_user_by_username(username):
                return {
                    "success": False,
                    "error": f"用户名 '{username}' 已存在",
                    "error_code": "USERNAME_EXISTS"
                }
            
            if await self.repository.get_user_by_email(email):
                return {
                    "success": False,
                    "error": f"邮箱 '{email}' 已存在",
                    "error_code": "EMAIL_EXISTS"
                }
            
            # 用户名和邮箱格式验证
            if not self._validate_username(username):
                return {
                    "success": False,
                    "error": "用户名格式无效",
                    "error_code": "INVALID_USERNAME"
                }
            
            if not self._validate_email(email):
                return {
                    "success": False,
                    "error": "邮箱格式无效",
                    "error_code": "INVALID_EMAIL"
                }
            
            # 密码强度验证
            password_validation = self._validate_password_strength(password)
            if not password_validation["valid"]:
                return {
                    "success": False,
                    "error": f"密码强度不符合要求: {password_validation['error']}",
                    "error_code": "WEAK_PASSWORD"
                }
            
            # 角色验证
            if not self._validate_role(role):
                return {
                    "success": False,
                    "error": f"无效的用户角色: {role}",
                    "error_code": "INVALID_ROLE"
                }
            
            # 生成密码哈希
            password_hash = self._hash_password(password)
            
            # 创建用户
            user = await self.repository.create_user(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                is_active=is_active
            )
            
            return {
                "success": True,
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建用户失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """用户认证 - 业务逻辑层"""
        try:
            # 获取用户信息
            user = await self.repository.get_user_by_username(username)
            if not user:
                # 为了安全，不要透露用户是否存在
                return {
                    "success": False,
                    "error": "用户名或密码错误",
                    "error_code": "INVALID_CREDENTIALS"
                }
            
            # 检查用户是否激活
            if not user.is_active:
                return {
                    "success": False,
                    "error": "用户账户已被禁用",
                    "error_code": "USER_DISABLED"
                }
            
            # 验证密码
            if not self._verify_password(password, user.password_hash):
                # 记录失败的登录尝试
                await self._record_login_attempt(user.id, success=False)
                
                return {
                    "success": False,
                    "error": "用户名或密码错误",
                    "error_code": "INVALID_CREDENTIALS"
                }
            
            # 检查账户是否被锁定
            if await self._is_account_locked(user.id):
                return {
                    "success": False,
                    "error": "账户已被锁定，请稍后再试",
                    "error_code": "ACCOUNT_LOCKED"
                }
            
            # 更新最后登录时间
            await self.repository.update_last_login(user.id)
            
            # 记录成功的登录尝试
            await self._record_login_attempt(user.id, success=True)
            
            return {
                "success": True,
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
            }
            
        except Exception as e:
            logger.error(f"用户认证失败: {str(e)}")
            return {
                "success": False,
                "error": f"认证过程中发生错误: {str(e)}",
                "error_code": "AUTH_ERROR"
            }
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料 - 业务逻辑层"""
        try:
            user = await self.repository.get_user_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "profile_updated_at": user.updated_at.isoformat() if user.updated_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户资料失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取用户资料失败: {str(e)}",
                "error_code": "GET_PROFILE_FAILED"
            }
    
    async def update_user_profile(self, user_id: str, **updates) -> Dict[str, Any]:
        """更新用户资料 - 业务逻辑层"""
        try:
            user = await self.repository.get_user_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }
            
            # 业务规则验证
            allowed_fields = {"full_name", "email"}
            invalid_fields = set(updates.keys()) - allowed_fields
            if invalid_fields:
                return {
                    "success": False,
                    "error": f"不允许更新的字段: {', '.join(invalid_fields)}",
                    "error_code": "INVALID_FIELDS"
                }
            
            # 邮箱唯一性检查
            if "email" in updates:
                existing_user = await self.repository.get_user_by_email(updates["email"])
                if existing_user and existing_user.id != user_id:
                    return {
                        "success": False,
                        "error": f"邮箱 '{updates['email']}' 已被其他用户使用",
                        "error_code": "EMAIL_EXISTS"
                    }
                
                if not self._validate_email(updates["email"]):
                    return {
                        "success": False,
                        "error": "邮箱格式无效",
                        "error_code": "INVALID_EMAIL"
                    }
            
            # 执行更新
            updated_user = await self.repository.update_user(user_id, **updates)
            
            return {
                "success": True,
                "data": {
                    "id": updated_user.id,
                    "username": updated_user.username,
                    "email": updated_user.email,
                    "full_name": updated_user.full_name,
                    "updated_at": updated_user.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"更新用户资料失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新用户资料失败: {str(e)}",
                "error_code": "UPDATE_FAILED"
            }
    
    async def change_password(self, user_id: str, old_password: str, 
                            new_password: str) -> Dict[str, Any]:
        """修改密码 - 业务逻辑层"""
        try:
            user = await self.repository.get_user_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }
            
            # 验证原密码
            if not self._verify_password(old_password, user.password_hash):
                return {
                    "success": False,
                    "error": "原密码错误",
                    "error_code": "INVALID_OLD_PASSWORD"
                }
            
            # 新密码强度验证
            password_validation = self._validate_password_strength(new_password)
            if not password_validation["valid"]:
                return {
                    "success": False,
                    "error": f"新密码强度不符合要求: {password_validation['error']}",
                    "error_code": "WEAK_PASSWORD"
                }
            
            # 检查新密码是否与旧密码相同
            if self._verify_password(new_password, user.password_hash):
                return {
                    "success": False,
                    "error": "新密码不能与原密码相同",
                    "error_code": "SAME_PASSWORD"
                }
            
            # 生成新密码哈希
            new_password_hash = self._hash_password(new_password)
            
            # 更新密码
            await self.repository.update_password(user_id, new_password_hash)
            
            return {
                "success": True,
                "data": {
                    "message": "密码修改成功",
                    "changed_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"修改密码失败: {str(e)}")
            return {
                "success": False,
                "error": f"修改密码失败: {str(e)}",
                "error_code": "CHANGE_PASSWORD_FAILED"
            }
    
    # ============ 用户管理功能 ============
    
    async def list_users(self, skip: int = 0, limit: int = 100,
                        role: str = None, is_active: bool = None) -> Dict[str, Any]:
        """获取用户列表 - 业务逻辑层"""
        try:
            users = await self.repository.list_users(
                skip=skip, 
                limit=limit, 
                role=role, 
                is_active=is_active
            )
            
            total_count = await self.repository.count_users(role=role, is_active=is_active)
            
            return {
                "success": True,
                "data": {
                    "users": [
                        {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "full_name": user.full_name,
                            "role": user.role,
                            "is_active": user.is_active,
                            "created_at": user.created_at.isoformat(),
                            "last_login": user.last_login.isoformat() if user.last_login else None
                        }
                        for user in users
                    ],
                    "total_count": total_count,
                    "page_info": {
                        "skip": skip,
                        "limit": limit,
                        "has_more": skip + limit < total_count
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取用户列表失败: {str(e)}",
                "error_code": "LIST_FAILED"
            }
    
    async def activate_user(self, user_id: str) -> Dict[str, Any]:
        """激活用户 - 业务逻辑层"""
        try:
            result = await self.repository.set_user_active_status(user_id, True)
            if not result:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "message": "用户已激活",
                    "user_id": user_id
                }
            }
            
        except Exception as e:
            logger.error(f"激活用户失败: {str(e)}")
            return {
                "success": False,
                "error": f"激活用户失败: {str(e)}",
                "error_code": "ACTIVATE_FAILED"
            }
    
    async def deactivate_user(self, user_id: str) -> Dict[str, Any]:
        """停用用户 - 业务逻辑层"""
        try:
            result = await self.repository.set_user_active_status(user_id, False)
            if not result:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "message": "用户已停用",
                    "user_id": user_id
                }
            }
            
        except Exception as e:
            logger.error(f"停用用户失败: {str(e)}")
            return {
                "success": False,
                "error": f"停用用户失败: {str(e)}",
                "error_code": "DEACTIVATE_FAILED"
            }
    
    # ============ 私有辅助方法 ============
    
    def _validate_username(self, username: str) -> bool:
        """验证用户名格式"""
        import re
        # 用户名只能包含字母、数字、下划线，长度3-30
        pattern = r'^[a-zA-Z0-9_]{3,30}$'
        return bool(re.match(pattern, username))
    
    def _validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_password_strength(self, password: str) -> Dict[str, Any]:
        """验证密码强度"""
        if len(password) < 8:
            return {"valid": False, "error": "密码长度至少8个字符"}
        
        if len(password) > 128:
            return {"valid": False, "error": "密码长度不能超过128个字符"}
        
        # 检查是否包含字母
        if not any(c.isalpha() for c in password):
            return {"valid": False, "error": "密码必须包含字母"}
        
        # 检查是否包含数字
        if not any(c.isdigit() for c in password):
            return {"valid": False, "error": "密码必须包含数字"}
        
        return {"valid": True, "error": None}
    
    def _validate_role(self, role: str) -> bool:
        """验证用户角色"""
        valid_roles = {"admin", "user", "moderator", "viewer"}
        return role in valid_roles
    
    def _hash_password(self, password: str) -> str:
        """生成密码哈希"""
        # 使用bcrypt或类似的安全哈希算法
        import bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    async def _record_login_attempt(self, user_id: str, success: bool) -> None:
        """记录登录尝试"""
        try:
            await self.repository.record_login_attempt(user_id, success)
        except Exception as e:
            logger.error(f"记录登录尝试失败: {str(e)}")
    
    async def _is_account_locked(self, user_id: str) -> bool:
        """检查账户是否被锁定"""
        try:
            # 检查最近15分钟内是否有5次失败的登录尝试
            failed_attempts = await self.repository.get_failed_login_attempts(
                user_id, 
                minutes=15, 
                limit=5
            )
            return len(failed_attempts) >= 5
        except Exception as e:
            logger.error(f"检查账户锁定状态失败: {str(e)}")
            return False 