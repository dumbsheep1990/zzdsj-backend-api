"""
资源权限模型模块: 提供用户与各类资源的访问权限控制
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.core.database import Base
import enum
import uuid

class ResourceType(enum.Enum):
    """资源类型枚举"""
    KNOWLEDGE_BASE = "knowledge_base"  # 知识库
    ASSISTANT = "assistant"            # 助手
    KNOWLEDGE_GRAPH = "knowledge_graph"  # 知识图谱
    MODEL_CONFIG = "model_config"      # 模型配置
    MCP_CONFIG = "mcp_config"          # MCP配置
    CHAT = "chat"                      # 对话

class AccessLevel(enum.Enum):
    """访问权限级别枚举"""
    READ = "read"        # 只读权限
    WRITE = "write"      # 读写权限
    ADMIN = "admin"      # 管理权限
    OWNER = "owner"      # 所有者权限

class ResourcePermission(Base):
    """资源权限模型 - 控制用户对各类资源的访问权限"""
    __tablename__ = "resource_permissions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    resource_type = Column(Enum(ResourceType), nullable=False, index=True, comment="资源类型")
    resource_id = Column(String(36), nullable=False, index=True, comment="资源ID")
    access_level = Column(Enum(AccessLevel), nullable=False, comment="访问权限级别")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（多对一）- 使用字符串引用避免循环导入
    user = relationship("User", back_populates="resource_permissions")
    
    # 联合唯一约束：同一用户对同一资源只能有一条权限记录
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

class KnowledgeBaseAccess(Base):
    """知识库访问权限模型 - 提供知识库级别的细粒度访问控制"""
    __tablename__ = "knowledge_base_access"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True, comment="知识库ID")
    can_read = Column(Boolean, default=True, comment="是否可读取")
    can_write = Column(Boolean, default=False, comment="是否可修改")
    can_delete = Column(Boolean, default=False, comment="是否可删除")
    can_share = Column(Boolean, default=False, comment="是否可分享")
    can_manage = Column(Boolean, default=False, comment="是否可管理")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（多对一）
    user = relationship("User", back_populates="knowledge_base_access")
    
    # 关联知识库（多对一）- 根据实际情况添加反向关系
    # knowledge_base = relationship("KnowledgeBase", back_populates="user_access")
    
    # 联合唯一约束
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

class AssistantAccess(Base):
    """助手访问权限模型 - 提供助手级别的细粒度访问控制"""
    __tablename__ = "assistant_access"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    assistant_id = Column(String(36), ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False, index=True, comment="助手ID")
    can_use = Column(Boolean, default=True, comment="是否可使用")
    can_edit = Column(Boolean, default=False, comment="是否可编辑")
    can_delete = Column(Boolean, default=False, comment="是否可删除")
    can_share = Column(Boolean, default=False, comment="是否可分享")
    can_manage = Column(Boolean, default=False, comment="是否可管理")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（多对一）
    user = relationship("User", back_populates="assistant_access")
    
    # 关联助手（多对一）
    # assistant = relationship("Assistant", back_populates="user_access")
    
    # 联合唯一约束
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

class ModelConfigAccess(Base):
    """模型配置访问权限模型 - 控制用户对模型配置的访问"""
    __tablename__ = "model_config_access"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    model_provider_id = Column(String(36), ForeignKey("model_providers.id", ondelete="CASCADE"), nullable=False, index=True, comment="模型提供商ID")
    can_use = Column(Boolean, default=True, comment="是否可使用")
    can_edit = Column(Boolean, default=False, comment="是否可编辑")
    can_delete = Column(Boolean, default=False, comment="是否可删除")
    quota_limit = Column(Integer, default=-1, comment="使用配额限制 (-1表示无限制)")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（多对一）
    user = relationship("User", back_populates="model_config_access")
    
    # 关联模型提供商（多对一）
    # model_provider = relationship("ModelProvider", back_populates="user_access")
    
    # 联合唯一约束
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

class MCPConfigAccess(Base):
    """MCP配置访问权限模型 - 控制用户对MCP工具的访问"""
    __tablename__ = "mcp_config_access"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    mcp_service_id = Column(String(36), ForeignKey("mcp_services.id", ondelete="CASCADE"), nullable=False, index=True, comment="MCP服务ID")
    can_use = Column(Boolean, default=True, comment="是否可使用")
    can_edit = Column(Boolean, default=False, comment="是否可编辑")
    can_delete = Column(Boolean, default=False, comment="是否可删除")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（多对一）
    user = relationship("User", back_populates="mcp_config_access")
    
    # 关联MCP服务（多对一）
    # mcp_service = relationship("MCPService", back_populates="user_access")
    
    # 联合唯一约束
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

class UserResourceQuota(Base):
    """用户资源配额模型 - 控制用户可使用的资源总量"""
    __tablename__ = "user_resource_quotas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False, comment="用户ID")
    
    # 知识库配额
    max_knowledge_bases = Column(Integer, default=5, comment="最大知识库数量")
    max_knowledge_base_size_mb = Column(Integer, default=1024, comment="单个知识库最大容量(MB)")
    
    # 助手配额
    max_assistants = Column(Integer, default=3, comment="最大助手数量")
    
    # 模型使用配额
    daily_model_tokens = Column(Integer, default=10000, comment="每日模型令牌使用量")
    monthly_model_tokens = Column(Integer, default=300000, comment="每月模型令牌使用量")
    
    # MCP配额
    max_mcp_calls_per_day = Column(Integer, default=100, comment="每日最大MCP调用次数")
    
    # 存储配额
    max_storage_mb = Column(Integer, default=2048, comment="最大存储空间(MB)")
    
    # 通用限制
    rate_limit_per_minute = Column(Integer, default=60, comment="每分钟请求限制")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关联用户（一对一）
    user = relationship("User", back_populates="resource_quota")
