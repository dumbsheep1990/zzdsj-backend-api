"""
用户相关的Pydantic模式：用于请求和响应的数据验证
"""

from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
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
class UserCreate(BaseModel):
    """用户创建模型"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, max_length=64, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    phone: Optional[str] = Field(None, description="手机号码")
    
    @validator('username')
    def validate_username(cls, v):
        """验证用户名"""
        if not v or not v.strip():
            raise ValueError('用户名不能为空')
        
        # 用户名只能包含字母、数字和下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        
        # 用户名不能以数字开头
        if v[0].isdigit():
            raise ValueError('用户名不能以数字开头')
        
        return v.lower()  # 转换为小写

    @validator('email')
    def validate_email(cls, v):
        """验证邮箱地址"""
        if not v or not v.strip():
            raise ValueError('邮箱地址不能为空')
        
        # 简单的邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.strip()):
            raise ValueError('邮箱格式不正确')
        
        return v.lower().strip()

    @validator('password')
    def password_strength(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError('密码长度至少为8个字符')
        
        # 检查密码复杂度
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in v)
        
        complexity_count = sum([has_upper, has_lower, has_digit, has_special])
        
        if complexity_count < 3:
            raise ValueError('密码必须包含以下至少3种类型：大写字母、小写字母、数字、特殊字符')
        
        # 检查常见弱密码
        weak_passwords = ['12345678', 'password', 'qwerty123', '11111111']
        if v.lower() in weak_passwords:
            raise ValueError('密码过于简单，请使用更复杂的密码')
        
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """验证密码确认"""
        if 'password' in values and v != values['password']:
            raise ValueError('密码确认不匹配')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        """验证手机号码"""
        if v is not None:
            v = v.strip()
            if v:
                # 支持中国大陆手机号格式
                phone_pattern = r'^1[3-9]\d{9}$'
                if not re.match(phone_pattern, v):
                    raise ValueError('手机号码格式不正确')
        return v

    @validator('nickname')
    def validate_nickname(cls, v):
        """验证昵称"""
        if v is not None:
            v = v.strip()
            if v:
                # 昵称不能包含特殊字符（除了空格、中文、字母、数字）
                if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s]+$', v):
                    raise ValueError('昵称只能包含字母、数字、中文和空格')
                
                # 昵称长度检查
                if len(v) < 2:
                    raise ValueError('昵称长度至少为2个字符')
                
                return v
        return v

# 用户更新
class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[str] = Field(None, description="邮箱地址")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    phone: Optional[str] = Field(None, description="手机号码")
    avatar: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, max_length=200, description="个人简介")
    
    @validator('email')
    def validate_email(cls, v):
        """验证邮箱地址"""
        if v is not None:
            v = v.strip()
            if v:
                # 简单的邮箱格式验证
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, v):
                    raise ValueError('邮箱格式不正确')
                return v.lower()
        return v

    @validator('phone')
    def validate_phone(cls, v):
        """验证手机号码"""
        if v is not None:
            v = v.strip()
            if v:
                # 支持中国大陆手机号格式
                phone_pattern = r'^1[3-9]\d{9}$'
                if not re.match(phone_pattern, v):
                    raise ValueError('手机号码格式不正确')
        return v

    @validator('nickname')
    def validate_nickname(cls, v):
        """验证昵称"""
        if v is not None:
            v = v.strip()
            if v:
                # 昵称不能包含特殊字符
                if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s]+$', v):
                    raise ValueError('昵称只能包含字母、数字、中文和空格')
                
                if len(v) < 2:
                    raise ValueError('昵称长度至少为2个字符')
                
                return v
        return v

    @validator('avatar')
    def validate_avatar(cls, v):
        """验证头像URL"""
        if v is not None:
            v = v.strip()
            if v:
                # 简单的URL格式验证
                url_pattern = r'^https?://.+\.(jpg|jpeg|png|gif|webp)$'
                if not re.match(url_pattern, v, re.IGNORECASE):
                    raise ValueError('头像URL格式不正确，必须是有效的图片URL')
        return v

    @validator('bio')
    def validate_bio(cls, v):
        """验证个人简介"""
        if v is not None:
            v = v.strip()
            if v and len(v) < 10:
                raise ValueError('个人简介长度至少为10个字符')
        return v

# 用户设置更新
class UserSettingsUpdate(BaseModel):
    """用户设置更新模型"""
    theme: Optional[str] = Field(None, max_length=20, description="UI主题")
    language: Optional[str] = Field(None, max_length=10, description="界面语言")
    notification_enabled: Optional[bool] = Field(None, description="是否启用通知")
    timezone: Optional[str] = Field(None, max_length=50, description="时区")
    
    @validator('theme')
    def validate_theme(cls, v):
        """验证主题"""
        if v is not None:
            valid_themes = ['light', 'dark', 'auto', 'system']
            if v not in valid_themes:
                raise ValueError(f'无效的主题选择: {v}。有效主题: {valid_themes}')
        return v

    @validator('language')
    def validate_language(cls, v):
        """验证语言"""
        if v is not None:
            valid_languages = ['zh-CN', 'zh-TW', 'en-US', 'ja-JP', 'ko-KR']
            if v not in valid_languages:
                raise ValueError(f'不支持的语言: {v}。支持的语言: {valid_languages}')
        return v

    @validator('timezone')
    def validate_timezone(cls, v):
        """验证时区"""
        if v is not None:
            # 简单的时区格式验证
            timezone_pattern = r'^[A-Za-z]+/[A-Za-z_]+$|^UTC[+-]\d{1,2}$|^UTC$'
            if not re.match(timezone_pattern, v):
                raise ValueError('时区格式不正确，例如: Asia/Shanghai, UTC+8, UTC')
        return v

# 密码更新
class PasswordUpdate(BaseModel):
    """密码更新模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=64, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")

    @validator('new_password')
    def password_strength(cls, v):
        """验证新密码强度"""
        if len(v) < 8:
            raise ValueError('新密码长度至少为8个字符')
        
        # 检查密码复杂度
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in v)
        
        complexity_count = sum([has_upper, has_lower, has_digit, has_special])
        
        if complexity_count < 3:
            raise ValueError('新密码必须包含以下至少3种类型：大写字母、小写字母、数字、特殊字符')
        
        # 检查常见弱密码
        weak_passwords = ['12345678', 'password', 'qwerty123', '11111111']
        if v.lower() in weak_passwords:
            raise ValueError('新密码过于简单，请使用更复杂的密码')
        
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """验证新密码确认"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('新密码确认不匹配')
        return v

    @root_validator
    def validate_password_change(cls, values):
        """验证密码变更"""
        current_password = values.get('current_password')
        new_password = values.get('new_password')
        
        # 检查新密码不能与当前密码相同
        if current_password and new_password and current_password == new_password:
            raise ValueError('新密码不能与当前密码相同')
        
        return values

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

# 用户激活请求
class UserActivation(BaseModel):
    """用户激活模型"""
    activation_token: str = Field(..., min_length=32, description="激活令牌")
    
    @validator('activation_token')
    def validate_activation_token(cls, v):
        """验证激活令牌"""
        if not v or not v.strip():
            raise ValueError('激活令牌不能为空')
        
        # 令牌应该是32位以上的字符串
        if len(v.strip()) < 32:
            raise ValueError('激活令牌格式不正确')
        
        return v.strip()

# 用户权限模型
class UserPermissions(BaseModel):
    """用户权限模型"""
    can_create_knowledge_base: bool = Field(False, description="可以创建知识库")
    can_manage_assistants: bool = Field(False, description="可以管理助手")
    can_use_advanced_features: bool = Field(False, description="可以使用高级功能")
    max_knowledge_bases: int = Field(5, ge=0, le=100, description="最大知识库数量")
    max_documents_per_kb: int = Field(1000, ge=0, le=10000, description="每个知识库最大文档数")
    max_api_calls_per_day: int = Field(1000, ge=0, description="每日最大API调用次数")
    
    @validator('max_knowledge_bases')
    def validate_max_knowledge_bases(cls, v):
        """验证最大知识库数量"""
        if v < 0 or v > 100:
            raise ValueError('最大知识库数量必须在0-100之间')
        return v

    @validator('max_documents_per_kb')
    def validate_max_documents_per_kb(cls, v):
        """验证每个知识库最大文档数"""
        if v < 0 or v > 10000:
            raise ValueError('每个知识库最大文档数必须在0-10000之间')
        return v

# 用户配额使用情况
class UserQuotaUsage(BaseModel):
    """用户配额使用情况"""
    knowledge_bases_used: int = Field(0, ge=0, description="已使用知识库数")
    documents_used: int = Field(0, ge=0, description="已使用文档数")
    api_calls_today: int = Field(0, ge=0, description="今日API调用次数")
    storage_used_mb: float = Field(0.0, ge=0.0, description="已使用存储空间(MB)")
    
    def calculate_usage_percentage(self, permissions: UserPermissions) -> Dict[str, float]:
        """计算使用率百分比"""
        return {
            "knowledge_bases": (self.knowledge_bases_used / max(permissions.max_knowledge_bases, 1)) * 100,
            "documents": (self.documents_used / max(permissions.max_documents_per_kb * permissions.max_knowledge_bases, 1)) * 100,
            "api_calls": (self.api_calls_today / max(permissions.max_api_calls_per_day, 1)) * 100
        }
