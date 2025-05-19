"""
统一工具系统的Pydantic模型
包含所有工具类型的通用Schema定义
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from uuid import UUID

class ToolBase(BaseModel):
    """工具基础模型"""
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    is_enabled: Optional[bool] = Field(True, description="是否启用")

class ToolCreate(ToolBase):
    """创建工具请求模型"""
    toolkit_name: str = Field(..., description="工具包名称")
    function_name: str = Field(..., description="函数名称")
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式")
    requires_api_key: Optional[bool] = Field(False, description="是否需要API密钥")
    implementation_type: Optional[str] = Field("python_function", description="实现类型")
    implementation_details: Optional[Dict[str, Any]] = Field(None, description="实现详情")
    is_system: Optional[bool] = Field(False, description="是否系统工具")

class ToolUpdate(BaseModel):
    """更新工具请求模型"""
    name: Optional[str] = Field(None, description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式")
    implementation_details: Optional[Dict[str, Any]] = Field(None, description="实现详情")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    requires_api_key: Optional[bool] = Field(None, description="是否需要API密钥")

class ToolResponse(ToolBase):
    """工具响应模型"""
    id: str = Field(..., description="工具ID")
    toolkit_name: str = Field(..., description="工具包名称")
    function_name: str = Field(..., description="函数名称")
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式")
    requires_api_key: bool = Field(False, description="是否需要API密钥")
    source: str = Field("database", description="工具来源，如database或camel")
    
    class Config:
        orm_mode = True

class ToolExecuteRequest(BaseModel):
    """工具执行请求模型"""
    parameters: Dict[str, Any] = Field({}, description="执行参数")
    agent_run_id: Optional[str] = Field(None, description="智能体运行ID")

class ToolExecuteResponse(BaseModel):
    """工具执行响应模型"""
    status: str = Field(..., description="执行状态")
    data: Dict[str, Any] = Field(..., description="执行结果")
    message: Optional[str] = Field(None, description="执行消息")

class ToolkitBase(BaseModel):
    """工具包基础模型"""
    name: str = Field(..., description="工具包名称")
    description: Optional[str] = Field(None, description="工具包描述")
    is_enabled: Optional[bool] = Field(True, description="是否启用")

class ToolkitCreate(ToolkitBase):
    """创建工具包请求模型"""
    config: Optional[Dict[str, Any]] = Field(None, description="工具包配置")

class ToolkitUpdate(BaseModel):
    """更新工具包请求模型"""
    name: Optional[str] = Field(None, description="工具包名称")
    description: Optional[str] = Field(None, description="工具包描述")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    config: Optional[Dict[str, Any]] = Field(None, description="工具包配置")

class ToolkitResponse(ToolkitBase):
    """工具包响应模型"""
    id: str = Field(..., description="工具包ID")
    config: Optional[Dict[str, Any]] = Field(None, description="工具包配置")
    tool_count: Optional[int] = Field(0, description="工具数量")
    source: str = Field("database", description="工具包来源，如database或camel")
    
    class Config:
        orm_mode = True

class ToolkitWithToolsResponse(ToolkitResponse):
    """包含工具的工具包响应模型"""
    tools: List[ToolResponse] = Field([], description="工具列表")

class TaskRequest(BaseModel):
    """任务执行请求模型"""
    task: str = Field(..., description="任务描述")
    tools: Optional[List[str]] = Field(None, description="可用工具列表")
    model: Optional[str] = Field(None, description="模型名称")

class TaskResponse(BaseModel):
    """任务执行响应模型"""
    status: str = Field(..., description="执行状态")
    data: Dict[str, Any] = Field(..., description="执行结果")
    message: Optional[str] = Field(None, description="执行消息")
