"""
智能体相关数据模型
"""
from typing import List, Optional, Dict, Any
from pydantic import Field
from app.schemas.assistants.base import BaseRequest, BaseResponse


class TaskRequest(BaseRequest):
    """任务请求"""
    task: str = Field(..., min_length=1, description="任务描述")
    framework: Optional[str] = Field(None, description="使用的框架")
    tool_ids: Optional[List[str]] = Field(None, description="工具ID列表")
    parameters: Optional[Dict[str, Any]] = Field(None, description="额外参数")


class TaskResponse(BaseResponse):
    """任务响应"""
    result: str = Field(..., description="任务结果")
    metadata: Dict[str, Any] = Field(..., description="元数据")


class ToolConfig(BaseRequest):
    """工具配置"""
    tool_id: Optional[str] = Field(None, description="工具ID")
    tool_type: str = Field(..., description="工具类型: mcp, query_engine, function")
    tool_name: str = Field(..., description="工具名称")
    enabled: bool = Field(True, description="是否启用")
    settings: Optional[Dict[str, Any]] = Field(None, description="工具设置")


class AgentToolResponse(BaseResponse):
    """智能体工具响应"""
    tool_name: str
    tool_type: str
    enabled: bool
    settings: Optional[Dict[str, Any]]


class FrameworkInfo(BaseResponse):
    """框架信息"""
    name: str
    display_name: str
    description: str
    version: str


class ToolInfo(BaseResponse):
    """工具信息"""
    id: str
    name: str
    type: str
    description: str


class FrameworkListResponse(BaseResponse):
    """框架列表响应"""
    frameworks: List[FrameworkInfo]
    total: int


class ToolListResponse(BaseResponse):
    """工具列表响应"""
    tools: List[ToolInfo]
    total: int