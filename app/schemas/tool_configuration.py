"""
工具配置相关的数据模式定义
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class ToolConfigurationSchemaCreate(BaseModel):
    """创建工具配置模式的请求模式"""
    tool_id: str = Field(..., description="工具ID")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="配置说明")
    config_schema: Dict[str, Any] = Field(..., description="JSON Schema配置定义")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置值")
    ui_schema: Optional[Dict[str, Any]] = Field(None, description="UI渲染配置")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="自定义验证规则")

class ToolConfigurationSchemaResponse(BaseModel):
    """工具配置模式响应模式"""
    schema_id: str = Field(..., description="配置模式ID")
    tool_id: str = Field(..., description="工具ID")
    tool_name: str = Field(..., description="工具名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="配置说明")
    config_schema: Dict[str, Any] = Field(..., description="JSON Schema配置定义")
    default_config: Dict[str, Any] = Field(..., description="默认配置值")
    ui_schema: Dict[str, Any] = Field(..., description="UI渲染配置")
    required_fields: List[str] = Field(..., description="必填字段列表")
    validation_rules: Dict[str, Any] = Field(..., description="自定义验证规则")

class ToolConfigurationCreate(BaseModel):
    """创建用户工具配置的请求模式"""
    schema_id: str = Field(..., description="配置模式ID")
    config_values: Dict[str, Any] = Field(..., description="配置值")
    configuration_name: Optional[str] = Field(None, description="配置名称")

class ToolConfigurationResponse(BaseModel):
    """用户工具配置响应模式"""
    configuration_id: str = Field(..., description="配置ID")
    tool_id: str = Field(..., description="工具ID")
    tool_name: str = Field(..., description="工具名称")
    config_values: Dict[str, Any] = Field(..., description="配置值")
    is_valid: bool = Field(..., description="配置是否有效")
    validation_errors: Optional[List[Dict[str, Any]]] = Field(None, description="验证错误")
    configuration_name: Optional[str] = Field(None, description="配置名称")
    is_default: bool = Field(..., description="是否为默认配置")

class ToolConfigurationValidationResponse(BaseModel):
    """工具配置验证响应模式"""
    is_valid: bool = Field(..., description="配置是否有效")
    errors: List[Dict[str, Any]] = Field(default=[], description="验证错误列表")
    tool_name: str = Field(..., description="工具名称")
    message: str = Field(..., description="验证消息")

class ToolConfigurationValidationError(BaseModel):
    """配置验证错误详情"""
    field: str = Field(..., description="错误字段")
    message: str = Field(..., description="错误消息")
    type: str = Field(..., description="错误类型")

class ToolConfigurationWizardResponse(BaseModel):
    """工具配置向导响应模式"""
    tool_name: str = Field(..., description="工具名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="配置说明")
    config_schema: Dict[str, Any] = Field(..., description="配置模式")
    ui_schema: Dict[str, Any] = Field(..., description="UI模式")
    default_config: Dict[str, Any] = Field(..., description="默认配置")
    existing_config: Optional[Dict[str, Any]] = Field(None, description="现有配置")
    required_fields: List[str] = Field(..., description="必填字段")

class ToolReadinessResponse(BaseModel):
    """工具准备状态响应模式"""
    ready: bool = Field(..., description="是否准备就绪")
    message: str = Field(..., description="状态消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    action_required: Optional[str] = Field(None, description="需要的操作")
    validation_errors: Optional[List[Dict[str, Any]]] = Field(None, description="验证错误") 