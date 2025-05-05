"""
用户相关的Pydantic模式：用于请求和响应的数据验证
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
import re

# 基础模型
class BaseUserModel(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")

    class Config:
        from_attributes = True

# 创建用户
class UserCreate(BaseUserModel):
    """用户创建模型"""
    password: str = Field(..., min_length=8, max_length=64, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    
    @validator('password')
    def password_strength(cls, v):
        """验证密码强度"""
        min_length = 8
        if len(v) < min_length:
            raise ValueError(f'密码长度不得少于{min_length}个字符')
        
        # 检查密码复杂度
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含至少一个数字')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('密码必须包含至少一个特殊字符')
        
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """验证两次输入的密码是否一致"""
        if 'password' in values and v != values['password']:
            raise ValueError('两次密码输入不一致')
        return v

# 用户更新
class UserUpdate(BaseModel):
    """用户更新模型"""
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    disabled: Optional[bool] = Field(None, description="是否禁用")
    avatar_url: Optional[str] = Field(None, description="头像URL")

# 用户设置更新
class UserSettingsUpdate(BaseModel):
    """用户设置更新模型"""
    theme: Optional[str] = Field(None, max_length=20, description="UI主题")
    language: Optional[str] = Field(None, max_length=10, description="界面语言")
    notification_enabled: Optional[bool] = Field(None, description="是否启用通知")

# 密码更新
class PasswordUpdate(BaseModel):
    """密码更新模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=64, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator('new_password')
    def password_strength(cls, v):
        """验证密码强度"""
        min_length = 8
        if len(v) < min_length:
            raise ValueError(f'密码长度不得少于{min_length}个字符')
        
        # 检查密码复杂度
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含至少一个数字')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('密码必须包含至少一个特殊字符')
        
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """验证两次输入的密码是否一致"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次密码输入不一致')
        return v

# 用户角色
class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")

class RoleCreate(RoleBase):
    """角色创建模型"""
    is_default: Optional[bool] = Field(False, description="是否为默认角色")

class RoleUpdate(BaseModel):
    """角色更新模型"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    is_default: Optional[bool] = Field(None, description="是否为默认角色")

class Role(RoleBase):
    """角色响应模型"""
    id: str = Field(..., description="角色ID")
    is_default: bool = Field(..., description="是否为默认角色")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

# 权限
class PermissionBase(BaseModel):
    """权限基础模型"""
    name: str = Field(..., min_length=2, max_length=50, description="权限名称")
    code: str = Field(..., min_length=2, max_length=50, description="权限代码")
    description: Optional[str] = Field(None, description="权限描述")
    resource: Optional[str] = Field(None, description="资源类型")

class PermissionCreate(PermissionBase):
    """权限创建模型"""
    pass

class PermissionUpdate(BaseModel):
    """权限更新模型"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    resource: Optional[str] = Field(None, description="资源类型")

class Permission(PermissionBase):
    """权限响应模型"""
    id: str = Field(..., description="权限ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

# 用户响应
class UserSettings(BaseModel):
    """用户设置响应模型"""
    theme: str = Field(..., description="UI主题")
    language: str = Field(..., description="界面语言")
    notification_enabled: bool = Field(..., description="是否启用通知")

class User(BaseUserModel):
    """用户响应模型"""
    id: str = Field(..., description="用户ID")
    is_superuser: bool = Field(..., description="是否为超级管理员")
    disabled: bool = Field(..., description="是否禁用")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    settings: Optional[UserSettings] = Field(None, description="用户设置")
    roles: List[Role] = Field([], description="用户角色")

# 登录与认证
class Token(BaseModel):
    """Token响应模型"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(..., description="令牌类型")
    expires_in: int = Field(..., description="过期时间(秒)")

class TokenPayload(BaseModel):
    """Token载荷模型"""
    sub: Optional[str] = Field(None, description="用户ID")
    exp: Optional[int] = Field(None, description="过期时间")
    type: Optional[str] = Field(None, description="令牌类型")

class Login(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

class RefreshToken(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")

# API密钥
class ApiKeyCreate(BaseModel):
    """API密钥创建模型"""
    name: str = Field(..., min_length=1, max_length=100, description="密钥名称")
    description: Optional[str] = Field(None, description="密钥描述")
    expires_days: Optional[int] = Field(None, ge=1, description="有效期(天)")

class ApiKeyUpdate(BaseModel):
    """API密钥更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="密钥名称")
    description: Optional[str] = Field(None, description="密钥描述")
    is_active: Optional[bool] = Field(None, description="是否激活")

class ApiKey(BaseModel):
    """API密钥响应模型"""
    id: str = Field(..., description="密钥ID")
    name: str = Field(..., description="密钥名称")
    description: Optional[str] = Field(None, description="密钥描述")
    is_active: bool = Field(..., description="是否激活")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    created_at: datetime = Field(..., description="创建时间")

class ApiKeyWithValue(ApiKey):
    """包含密钥值的API密钥响应模型"""
    key: str = Field(..., description="API密钥值")
