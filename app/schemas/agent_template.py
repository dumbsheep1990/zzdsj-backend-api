from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AgentTemplateBase(BaseModel):
    """智能体模板基类"""
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    category: Optional[str] = Field(None, description="模板分类")
    base_agent_type: str = Field(..., description="基础智能体类型")
    configuration: Optional[Dict[str, Any]] = Field(None, description="模板配置")
    system_prompt_template: Optional[str] = Field(None, description="系统提示词模板")
    recommended_tools: Optional[List[Dict[str, Any]]] = Field(None, description="推荐工具")
    example_workflow: Optional[Dict[str, Any]] = Field(None, description="示例工作流")
    usage_guide: Optional[str] = Field(None, description="使用指南")

class AgentTemplateCreate(AgentTemplateBase):
    """创建智能体模板"""
    is_system: bool = Field(False, description="是否为系统模板")

class AgentTemplateUpdate(BaseModel):
    """更新智能体模板"""
    name: Optional[str] = Field(None, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    category: Optional[str] = Field(None, description="模板分类")
    base_agent_type: Optional[str] = Field(None, description="基础智能体类型")
    configuration: Optional[Dict[str, Any]] = Field(None, description="模板配置")
    system_prompt_template: Optional[str] = Field(None, description="系统提示词模板")
    recommended_tools: Optional[List[Dict[str, Any]]] = Field(None, description="推荐工具")
    example_workflow: Optional[Dict[str, Any]] = Field(None, description="示例工作流")
    usage_guide: Optional[str] = Field(None, description="使用指南")

class AgentTemplateResponse(AgentTemplateBase):
    """智能体模板响应"""
    id: int
    creator_id: Optional[int] = None
    is_system: bool = False
    created_at: str
    updated_at: str
    
    class Config:
        orm_mode = True

class TemplateInstantiationRequest(BaseModel):
    """模板实例化请求"""
    template_id: int = Field(..., description="模板ID")
    name: str = Field(..., description="新智能体名称")
    description: Optional[str] = Field(None, description="新智能体描述")
    is_public: bool = Field(False, description="是否公开")
    parameters: Optional[Dict[str, Any]] = Field(None, description="模板参数")
    
class TemplateInstantiationResponse(BaseModel):
    """模板实例化响应"""
    definition_id: int = Field(..., description="创建的智能体定义ID")
    name: str = Field(..., description="创建的智能体名称")
