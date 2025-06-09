"""
工具配置数据模型
提供工具参数配置的数据存储和管理
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel

class ToolConfigurationSchema(BaseModel):
    """工具配置模式定义表"""
    __tablename__ = "tool_configuration_schemas"
    
    id = Column(String(36), primary_key=True, index=True)
    tool_id = Column(String(36), ForeignKey("tools.id"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False, index=True)  # 工具名称，便于查询
    
    # 配置模式定义
    schema_version = Column(String(20), nullable=False, default="1.0")  # 模式版本
    config_schema = Column(JSON, nullable=False)  # JSON Schema定义配置结构
    default_config = Column(JSON, nullable=True)  # 默认配置值
    
    # 验证规则
    validation_rules = Column(JSON, nullable=True)  # 自定义验证规则
    required_fields = Column(JSON, nullable=False, default=[])  # 必填字段列表
    
    # 展示配置
    ui_schema = Column(JSON, nullable=True)  # 前端UI渲染配置
    display_name = Column(String(200), nullable=False)  # 显示名称
    description = Column(Text, nullable=True)  # 配置说明
    
    # 状态信息
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    tool = relationship("Tool", back_populates="configuration_schemas")
    configurations = relationship("ToolConfiguration", back_populates="schema")

class ToolConfiguration(BaseModel):
    """用户工具配置表"""
    __tablename__ = "tool_configurations"
    
    id = Column(String(36), primary_key=True, index=True)
    schema_id = Column(String(36), ForeignKey("tool_configuration_schemas.id"), nullable=False)
    user_id = Column(String(36), nullable=False, index=True)  # 配置所属用户
    
    # 配置信息
    configuration_name = Column(String(200), nullable=True)  # 配置名称（用户自定义）
    config_values = Column(JSON, nullable=False)  # 具体配置值
    
    # 状态管理
    is_valid = Column(Boolean, default=False, nullable=False)  # 配置是否有效
    validation_errors = Column(JSON, nullable=True)  # 验证错误信息
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # 使用情况
    is_default = Column(Boolean, default=False, nullable=False)  # 是否为默认配置
    usage_count = Column(Integer, default=0, nullable=False)  # 使用次数
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    schema = relationship("ToolConfigurationSchema", back_populates="configurations")

class ToolConfigurationTemplate(BaseModel):
    """工具配置模板表"""
    __tablename__ = "tool_configuration_templates"
    
    id = Column(String(36), primary_key=True, index=True)
    schema_id = Column(String(36), ForeignKey("tool_configuration_schemas.id"), nullable=False)
    
    # 模板信息
    template_name = Column(String(200), nullable=False)
    template_description = Column(Text, nullable=True)
    template_config = Column(JSON, nullable=False)  # 模板配置值
    
    # 分类和标签
    category = Column(String(100), nullable=True)  # 模板分类
    tags = Column(JSON, nullable=True)  # 标签列表
    
    # 权限控制
    is_public = Column(Boolean, default=True, nullable=False)  # 是否公开
    created_by = Column(String(36), nullable=False)  # 创建者
    
    # 使用统计
    usage_count = Column(Integer, default=0, nullable=False)
    rating = Column(Integer, default=0, nullable=False)  # 评分
    
    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    schema = relationship("ToolConfigurationSchema") 