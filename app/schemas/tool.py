from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ToolBase(BaseModel):
    """工具基类"""
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    tool_type: str = Field(..., description="工具类型")
    module_path: str = Field(..., description="模块路径")
    class_name: str = Field(..., description="类名")
    parameter_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式定义")
    input_format: Optional[Dict[str, Any]] = Field(None, description="输入格式定义")
    output_format: Optional[Dict[str, Any]] = Field(None, description="输出格式定义")
    tags: Optional[List[str]] = Field(None, description="工具标签")
    category: Optional[str] = Field(None, description="工具分类")

class ToolCreate(ToolBase):
    """创建工具"""
    is_system: bool = Field(False, description="是否为系统工具")

class ToolUpdate(BaseModel):
    """更新工具"""
    name: Optional[str] = Field(None, description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    tool_type: Optional[str] = Field(None, description="工具类型")
    module_path: Optional[str] = Field(None, description="模块路径")
    class_name: Optional[str] = Field(None, description="类名")
    parameter_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式定义")
    input_format: Optional[Dict[str, Any]] = Field(None, description="输入格式定义")
    output_format: Optional[Dict[str, Any]] = Field(None, description="输出格式定义")
    tags: Optional[List[str]] = Field(None, description="工具标签")
    category: Optional[str] = Field(None, description="工具分类")

class ToolResponse(ToolBase):
    """工具响应"""
    id: int
    creator_id: Optional[int] = None
    is_system: bool = False
    created_at: str
    updated_at: str
    
    class Config:
        orm_mode = True
