"""
Agent链调度模式定义
提供Agent链配置和执行的数据模型
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class ExecutionMode(str, Enum):
    """执行模式枚举"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"      # 并行执行
    CONDITIONAL = "conditional"  # 条件执行


class AgentReference(BaseModel):
    """Agent引用"""
    id: int = Field(..., description="Agent ID")
    name: Optional[str] = Field(None, description="Agent名称")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent配置覆盖")


class AgentChainConfig(BaseModel):
    """Agent调用链配置"""
    id: Optional[str] = Field(None, description="调用链ID")
    name: str = Field(..., description="调用链名称")
    description: Optional[str] = Field(None, description="调用链描述")
    execution_mode: ExecutionMode = Field(ExecutionMode.SEQUENTIAL, description="执行模式")
    agents: List[AgentReference] = Field(..., description="Agent列表")
    conditions: Optional[Dict[str, Any]] = Field(None, description="条件执行配置，仅conditional模式使用")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    
    @validator('agents')
    def validate_agents(cls, agents):
        """验证Agent列表"""
        if not agents or len(agents) < 1:
            raise ValueError("至少需要一个Agent")
        return agents


class AgentChainRequest(BaseModel):
    """Agent调用链执行请求"""
    chain_id: Optional[str] = Field(None, description="预定义调用链ID")
    chain_config: Optional[AgentChainConfig] = Field(None, description="调用链配置，与chain_id二选一")
    input: str = Field(..., description="用户输入")
    user_id: Optional[str] = Field(None, description="用户ID")
    stream: bool = Field(False, description="是否流式响应")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    
    @validator('chain_id', 'chain_config')
    def validate_chain_reference(cls, value, values):
        """验证调用链引用"""
        if 'chain_id' in values and values['chain_id'] is None and 'chain_config' in values and values['chain_config'] is None:
            raise ValueError("必须提供chain_id或chain_config之一")
        return value


class AgentStepStatus(BaseModel):
    """Agent执行步骤状态"""
    agent_id: int = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent名称")
    status: str = Field(..., description="执行状态")
    start_time: str = Field(..., description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    error: Optional[str] = Field(None, description="错误信息")


class AgentChainStatus(BaseModel):
    """Agent调用链执行状态"""
    execution_id: str = Field(..., description="执行ID")
    chain_id: str = Field(..., description="调用链ID")
    status: str = Field(..., description="执行状态")
    progress: int = Field(..., description="进度百分比")
    start_time: str = Field(..., description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    steps: List[AgentStepStatus] = Field(..., description="执行步骤")
    error: Optional[str] = Field(None, description="错误信息")


class AgentChainResponse(BaseModel):
    """Agent调用链执行响应"""
    execution_id: str = Field(..., description="执行ID")
    chain_id: str = Field(..., description="调用链ID")
    content: str = Field(..., description="响应内容")
    messages: List[Dict[str, Any]] = Field(..., description="消息列表")
    created_at: str = Field(..., description="创建时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
