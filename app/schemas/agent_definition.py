from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ToolConfig(BaseModel):
    """工具配置"""
    id: int
    name: str 
    order: Optional[int] = None
    condition: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

class AgentDefinitionBase(BaseModel):
    """智能体定义基类"""
    name: str = Field(..., description="智能体名称")
    description: Optional[str] = Field(None, description="智能体描述")
    base_agent_type: str = Field(..., description="基础智能体类型")
    is_public: bool = Field(False, description="是否公开")
    configuration: Optional[Dict[str, Any]] = Field(None, description="智能体配置")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    workflow_definition: Optional[Dict[str, Any]] = Field(None, description="工作流定义")

class AgentDefinitionCreate(AgentDefinitionBase):
    """创建智能体定义"""
    tools: List[ToolConfig] = Field([], description="关联的工具配置")

class AgentDefinitionUpdate(BaseModel):
    """更新智能体定义"""
    name: Optional[str] = Field(None, description="智能体名称")
    description: Optional[str] = Field(None, description="智能体描述")
    base_agent_type: Optional[str] = Field(None, description="基础智能体类型")
    is_public: Optional[bool] = Field(None, description="是否公开")
    configuration: Optional[Dict[str, Any]] = Field(None, description="智能体配置")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    workflow_definition: Optional[Dict[str, Any]] = Field(None, description="工作流定义")
    tools: Optional[List[ToolConfig]] = Field(None, description="关联的工具配置")

class AgentDefinitionResponse(AgentDefinitionBase):
    """智能体定义响应"""
    id: int
    creator_id: Optional[int] = None
    is_system: bool = False
    tools: List[ToolConfig] = []
    created_at: str
    updated_at: str
    
    class Config:
        orm_mode = True
        
class AgentRunRequest(BaseModel):
    """智能体运行请求"""
    definition_id: int = Field(..., description="智能体定义ID")
    task: str = Field(..., description="任务内容")
    parameters: Optional[Dict[str, Any]] = Field(None, description="运行参数")

class AgentRunResponse(BaseModel):
    """智能体运行响应"""
    run_id: int = Field(..., description="运行ID")
    result: Optional[str] = Field(None, description="运行结果")
    status: str = Field(..., description="运行状态")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    class Config:
        orm_mode = True
