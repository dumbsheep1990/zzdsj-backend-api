"""
资源权限相关的Pydantic模式：用于请求和响应的数据验证
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

# 导入模型中的枚举类型
from app.models.resource_permission import ResourceType, AccessLevel

# 通用资源权限模式
class ResourcePermissionBase(BaseModel):
    """资源权限基础模型"""
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    access_level: AccessLevel = Field(..., description="访问权限级别")

class ResourcePermissionCreate(ResourcePermissionBase):
    """资源权限创建模型"""
    user_id: str = Field(..., description="用户ID")

class ResourcePermissionUpdate(BaseModel):
    """资源权限更新模型"""
    access_level: Optional[AccessLevel] = Field(None, description="访问权限级别")

class ResourcePermissionResponse(ResourcePermissionBase):
    """资源权限响应模型"""
    id: str = Field(..., description="权限记录ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

# 知识库访问权限模式
class KnowledgeBaseAccessBase(BaseModel):
    """知识库访问权限基础模型"""
    knowledge_base_id: str = Field(..., description="知识库ID")
    can_read: bool = Field(True, description="是否可读取")
    can_write: bool = Field(False, description="是否可修改")
    can_delete: bool = Field(False, description="是否可删除")
    can_share: bool = Field(False, description="是否可分享")
    can_manage: bool = Field(False, description="是否可管理")

class KnowledgeBaseAccessCreate(KnowledgeBaseAccessBase):
    """知识库访问权限创建模型"""
    user_id: str = Field(..., description="用户ID")

class KnowledgeBaseAccessUpdate(BaseModel):
    """知识库访问权限更新模型"""
    can_read: Optional[bool] = Field(None, description="是否可读取")
    can_write: Optional[bool] = Field(None, description="是否可修改")
    can_delete: Optional[bool] = Field(None, description="是否可删除")
    can_share: Optional[bool] = Field(None, description="是否可分享")
    can_manage: Optional[bool] = Field(None, description="是否可管理")

class KnowledgeBaseAccessResponse(KnowledgeBaseAccessBase):
    """知识库访问权限响应模型"""
    id: str = Field(..., description="访问权限记录ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

# 助手访问权限模式
class AssistantAccessBase(BaseModel):
    """助手访问权限基础模型"""
    assistant_id: str = Field(..., description="助手ID")
    can_use: bool = Field(True, description="是否可使用")
    can_edit: bool = Field(False, description="是否可编辑")
    can_delete: bool = Field(False, description="是否可删除")
    can_share: bool = Field(False, description="是否可分享")
    can_manage: bool = Field(False, description="是否可管理")

class AssistantAccessCreate(AssistantAccessBase):
    """助手访问权限创建模型"""
    user_id: str = Field(..., description="用户ID")

class AssistantAccessUpdate(BaseModel):
    """助手访问权限更新模型"""
    can_use: Optional[bool] = Field(None, description="是否可使用")
    can_edit: Optional[bool] = Field(None, description="是否可编辑")
    can_delete: Optional[bool] = Field(None, description="是否可删除")
    can_share: Optional[bool] = Field(None, description="是否可分享")
    can_manage: Optional[bool] = Field(None, description="是否可管理")

class AssistantAccessResponse(AssistantAccessBase):
    """助手访问权限响应模型"""
    id: str = Field(..., description="访问权限记录ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

# 模型配置访问权限模式
class ModelConfigAccessBase(BaseModel):
    """模型配置访问权限基础模型"""
    model_provider_id: str = Field(..., description="模型提供商ID")
    can_use: bool = Field(True, description="是否可使用")
    can_edit: bool = Field(False, description="是否可编辑")
    can_delete: bool = Field(False, description="是否可删除")
    quota_limit: int = Field(-1, description="使用配额限制 (-1表示无限制)")

class ModelConfigAccessCreate(ModelConfigAccessBase):
    """模型配置访问权限创建模型"""
    user_id: str = Field(..., description="用户ID")

class ModelConfigAccessUpdate(BaseModel):
    """模型配置访问权限更新模型"""
    can_use: Optional[bool] = Field(None, description="是否可使用")
    can_edit: Optional[bool] = Field(None, description="是否可编辑")
    can_delete: Optional[bool] = Field(None, description="是否可删除")
    quota_limit: Optional[int] = Field(None, description="使用配额限制")

class ModelConfigAccessResponse(ModelConfigAccessBase):
    """模型配置访问权限响应模型"""
    id: str = Field(..., description="访问权限记录ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

# MCP配置访问权限模式
class MCPConfigAccessBase(BaseModel):
    """MCP配置访问权限基础模型"""
    mcp_service_id: str = Field(..., description="MCP服务ID")
    can_use: bool = Field(True, description="是否可使用")
    can_edit: bool = Field(False, description="是否可编辑")
    can_delete: bool = Field(False, description="是否可删除")

class MCPConfigAccessCreate(MCPConfigAccessBase):
    """MCP配置访问权限创建模型"""
    user_id: str = Field(..., description="用户ID")

class MCPConfigAccessUpdate(BaseModel):
    """MCP配置访问权限更新模型"""
    can_use: Optional[bool] = Field(None, description="是否可使用")
    can_edit: Optional[bool] = Field(None, description="是否可编辑")
    can_delete: Optional[bool] = Field(None, description="是否可删除")

class MCPConfigAccessResponse(MCPConfigAccessBase):
    """MCP配置访问权限响应模型"""
    id: str = Field(..., description="访问权限记录ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

# 用户资源配额模式
class UserResourceQuotaBase(BaseModel):
    """用户资源配额基础模型"""
    max_knowledge_bases: int = Field(..., description="最大知识库数量")
    max_knowledge_base_size_mb: int = Field(..., description="单个知识库最大容量(MB)")
    max_assistants: int = Field(..., description="最大助手数量")
    daily_model_tokens: int = Field(..., description="每日模型令牌使用量")
    monthly_model_tokens: int = Field(..., description="每月模型令牌使用量")
    max_mcp_calls_per_day: int = Field(..., description="每日最大MCP调用次数")
    max_storage_mb: int = Field(..., description="最大存储空间(MB)")
    rate_limit_per_minute: int = Field(..., description="每分钟请求限制")

class UserResourceQuotaCreate(UserResourceQuotaBase):
    """用户资源配额创建模型"""
    user_id: str = Field(..., description="用户ID")

class UserResourceQuotaUpdate(BaseModel):
    """用户资源配额更新模型"""
    max_knowledge_bases: Optional[int] = Field(None, description="最大知识库数量")
    max_knowledge_base_size_mb: Optional[int] = Field(None, description="单个知识库最大容量(MB)")
    max_assistants: Optional[int] = Field(None, description="最大助手数量")
    daily_model_tokens: Optional[int] = Field(None, description="每日模型令牌使用量")
    monthly_model_tokens: Optional[int] = Field(None, description="每月模型令牌使用量")
    max_mcp_calls_per_day: Optional[int] = Field(None, description="每日最大MCP调用次数")
    max_storage_mb: Optional[int] = Field(None, description="最大存储空间(MB)")
    rate_limit_per_minute: Optional[int] = Field(None, description="每分钟请求限制")

class UserResourceQuotaResponse(UserResourceQuotaBase):
    """用户资源配额响应模型"""
    id: str = Field(..., description="配额记录ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True
