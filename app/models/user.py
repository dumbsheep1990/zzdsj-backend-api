"""
用户模型模块: 包含用户、角色和权限相关的数据模型
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import relationship
import uuid
from app.utils.core.database import Base
from sqlalchemy.dialects.postgresql import ARRAY
from .resource_permission import ResourcePermission, KnowledgeBaseAccess, AssistantAccess, ModelConfigAccess, MCPConfigAccess, UserResourceQuota

# 用户角色关联表（多对多）
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
)

# 角色权限关联表（多对多）
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 添加自增ID字段
    auto_id = Column(Integer, autoincrement=True, unique=True, index=True, comment="自增ID")
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, index=True, nullable=False, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="哈希密码")
    full_name = Column(String(100), comment="全名")
    disabled = Column(Boolean, default=False, comment="是否禁用")
    is_superuser = Column(Boolean, default=False, comment="是否超级管理员")
    last_login = Column(DateTime, comment="最后登录时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 用户头像
    avatar_url = Column(String(255), comment="头像URL")
    
    # 关联角色（多对多）
    roles = relationship("Role", secondary=user_role, back_populates="users")
    
    # 关联用户设置（一对一）
    settings = relationship("UserSettings", uselist=False, back_populates="user", cascade="all, delete-orphan")
    
    # 关联API密钥（一对多）
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    
    # 关联资源权限（一对多）
    resource_permissions = relationship("ResourcePermission", back_populates="user", cascade="all, delete-orphan")
    
    # 关联知识库访问权限（一对多）
    knowledge_base_access = relationship("KnowledgeBaseAccess", back_populates="user", cascade="all, delete-orphan")
    
    # 关联助手访问权限（一对多）
    assistant_access = relationship("AssistantAccess", back_populates="user", cascade="all, delete-orphan")
    
    # 关联模型配置访问权限（一对多）
    model_config_access = relationship("ModelConfigAccess", back_populates="user", cascade="all, delete-orphan")
    
    # 关联MCP配置访问权限（一对多）
    mcp_config_access = relationship("MCPConfigAccess", back_populates="user", cascade="all, delete-orphan")
    
    # 关联资源配额（一对一）
    resource_quota = relationship("UserResourceQuota", uselist=False, back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    """角色模型"""
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False, comment="角色名称")
    description = Column(String(255), comment="角色描述")
    is_default = Column(Boolean, default=False, comment="是否默认角色")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（多对多）
    users = relationship("User", secondary=user_role, back_populates="roles")
    
    # 关联权限（多对多）
    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")

class Permission(Base):
    """权限模型"""
    __tablename__ = "permissions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False, comment="权限名称")
    code = Column(String(50), unique=True, nullable=False, comment="权限代码")
    description = Column(String(255), comment="权限描述")
    resource = Column(String(50), comment="资源类型")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联角色（多对多）
    roles = relationship("Role", secondary=role_permission, back_populates="permissions")

class UserSettings(Base):
    """用户设置模型"""
    __tablename__ = "user_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False, comment="用户ID")
    theme = Column(String(20), default="light", comment="UI主题")
    language = Column(String(10), default="zh-CN", comment="界面语言")
    notification_enabled = Column(Boolean, default=True, comment="是否启用通知")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（一对一）
    user = relationship("User", back_populates="settings")

class ApiKey(Base):
    """API密钥模型"""
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, comment="用户ID")
    key = Column(String(64), unique=True, nullable=False, comment="API密钥")
    name = Column(String(100), comment="密钥名称")
    description = Column(String(255), comment="密钥描述")
    is_active = Column(Boolean, default=True, comment="是否激活")
    expires_at = Column(DateTime, comment="过期时间")
    last_used_at = Column(DateTime, comment="最后使用时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（多对一）
    user = relationship("User", back_populates="api_keys")
