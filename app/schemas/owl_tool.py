"""
OWL框架工具模式定义
定义OWL框架工具和工具包的请求和响应模式
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class ToolApiKeyConfig(BaseModel):
    """工具API密钥配置"""
    key_name: str = Field(..., description="API密钥名称")
    key_type: str = Field(..., description="API密钥类型，例如'environment'或'database'")
    key_value: Optional[str] = Field(None, description="API密钥值（仅当类型为'database'时使用）")


class ToolBase(BaseModel):
    """工具基础模式"""
    name: str = Field(..., description="工具名称")
    toolkit_name: str = Field(..., description="所属工具包名称")
    description: Optional[str] = Field(None, description="工具描述")
    function_name: str = Field(..., description="函数名称")
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式")
    is_enabled: Optional[bool] = Field(True, description="是否启用")
    requires_api_key: Optional[bool] = Field(False, description="是否需要API密钥")
    api_key_config: Optional[Dict[str, Any]] = Field(None, description="API密钥配置")


class ToolCreate(ToolBase):
    """创建工具请求模式"""
    pass


class ToolUpdate(BaseModel):
    """更新工具请求模式"""
    description: Optional[str] = Field(None, description="工具描述")
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    requires_api_key: Optional[bool] = Field(None, description="是否需要API密钥")
    api_key_config: Optional[Dict[str, Any]] = Field(None, description="API密钥配置")


class ToolResponse(ToolBase):
    """工具响应模式"""
    id: str = Field(..., description="工具ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolkitBase(BaseModel):
    """工具包基础模式"""
    name: str = Field(..., description="工具包名称")
    description: Optional[str] = Field(None, description="工具包描述")
    is_enabled: Optional[bool] = Field(True, description="是否启用")
    config: Optional[Dict[str, Any]] = Field(None, description="配置信息")


class ToolkitCreate(ToolkitBase):
    """创建工具包请求模式"""
    pass


class ToolkitUpdate(BaseModel):
    """更新工具包请求模式"""
    description: Optional[str] = Field(None, description="工具包描述")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    config: Optional[Dict[str, Any]] = Field(None, description="配置信息")


class ToolkitResponse(ToolkitBase):
    """工具包响应模式"""
    id: str = Field(..., description="工具包ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolExecutionRequest(BaseModel):
    """工具执行请求模式"""
    parameters: Dict[str, Any] = Field(..., description="执行参数")


class ToolExecutionResponse(BaseModel):
    """工具执行响应模式"""
    execution_id: str = Field(..., description="执行ID")
    tool_id: str = Field(..., description="工具ID")
    tool_name: str = Field(..., description="工具名称")
    status: str = Field(..., description="执行状态")
    result: Optional[Any] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
