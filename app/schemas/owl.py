"""
OWL框架相关的Pydantic模型
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class ToolExecuteRequest(BaseModel):
    """工具执行请求模型"""
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")

class ToolData(BaseModel):
    """工具数据模型"""
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    source: str = Field(..., description="工具来源，internal或camel")
    toolkit: Optional[str] = Field(None, description="工具包名称，仅对camel工具有效")

class ToolListResponse(BaseModel):
    """工具列表响应模型"""
    status: str = Field(..., description="响应状态")
    data: List[Dict[str, Any]] = Field(..., description="工具列表")
    total: int = Field(..., description="工具总数")

class ToolMetadataResponse(BaseModel):
    """工具元数据响应模型"""
    status: str = Field(..., description="响应状态")
    data: Dict[str, Any] = Field(..., description="工具元数据")

class ToolExecuteResult(BaseModel):
    """工具执行结果模型"""
    status: str = Field(..., description="执行状态，success或error")
    tool: str = Field(..., description="工具名称")
    source: str = Field(..., description="工具来源，internal或camel")
    result: Optional[Any] = Field(None, description="执行结果，仅在status为success时有效")
    error: Optional[str] = Field(None, description="错误信息，仅在status为error时有效")

class ToolExecuteResponse(BaseModel):
    """工具执行响应模型"""
    status: str = Field(..., description="响应状态")
    data: ToolExecuteResult = Field(..., description="执行结果")

class ToolkitModel(BaseModel):
    """工具包模型"""
    name: str = Field(..., description="工具包名称")
    description: Optional[str] = Field(None, description="工具包描述") 
    tool_count: int = Field(..., description="工具数量")
    loaded: bool = Field(..., description="是否已加载")

class ToolkitListResponse(BaseModel):
    """工具包列表响应模型"""
    status: str = Field(..., description="响应状态")
    data: List[ToolkitModel] = Field(..., description="工具包列表")
    total: int = Field(..., description="工具包总数")

class TaskRequest(BaseModel):
    """任务请求模型"""
    task: str = Field(..., description="任务描述")
    tools: Optional[List[str]] = Field(None, description="可用工具列表")
    model: Optional[str] = Field(None, description="模型名称")

class TaskResponse(BaseModel):
    """任务响应模型"""
    status: str = Field(..., description="响应状态")
    data: Dict[str, Any] = Field(..., description="任务结果")
