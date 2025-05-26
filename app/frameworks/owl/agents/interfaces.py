"""
OWL框架Agent接口定义
提供Agent的统一接口和数据模型
"""

from typing import Any, Dict, List, Optional, Protocol, Union
from pydantic import BaseModel, Field
from datetime import datetime


class AgentCapability(BaseModel):
    """Agent能力定义"""
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    parameters: Optional[Dict[str, Any]] = Field(None, description="能力参数定义")
    required: bool = Field(False, description="是否为必需能力")
    category: str = Field("general", description="能力分类")


class AgentConfig(BaseModel):
    """Agent统一配置模型"""
    id: Optional[int] = Field(None, description="Agent ID")
    name: str = Field(..., description="Agent名称")
    description: Optional[str] = Field(None, description="Agent描述")
    model_name: str = Field(..., description="模型名称")
    model_provider: Optional[str] = Field(None, description="模型提供商")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    temperature: float = Field(0.7, description="采样温度")
    max_tokens: int = Field(1500, description="最大生成Token数")
    top_p: Optional[float] = Field(None, description="Top-p采样参数")
    top_k: Optional[int] = Field(None, description="Top-k采样参数")
    capabilities: List[AgentCapability] = Field([], description="Agent能力列表")
    tools: List[str] = Field([], description="可用工具列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.dict(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """从字典创建配置"""
        return cls(**data)


class AgentDefinition(BaseModel):
    """Agent完整定义"""
    config: AgentConfig = Field(..., description="Agent配置")
    prompt_templates: Dict[str, str] = Field({}, description="提示词模板")
    behaviors: Dict[str, Any] = Field({}, description="行为定义")
    knowledge: List[Dict[str, Any]] = Field([], description="知识项")
    chain_position: Optional[Dict[str, Any]] = Field(None, description="在链中的位置和角色")
    version: str = Field("1.0", description="定义版本")


class AgentInputSchema(BaseModel):
    """Agent输入数据格式定义"""
    query: str = Field(..., description="用户查询或指令")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    parameters: Optional[Dict[str, Any]] = Field(None, description="参数")
    history: Optional[List[Dict[str, Any]]] = Field(None, description="对话历史")
    source_agent_id: Optional[int] = Field(None, description="源Agent ID")
    trace_id: Optional[str] = Field(None, description="追踪ID")


class AgentOutputSchema(BaseModel):
    """Agent输出数据格式定义"""
    content: str = Field(..., description="输出内容")
    metadata: Dict[str, Any] = Field({}, description="元数据")
    tool_calls: List[Dict[str, Any]] = Field([], description="工具调用记录")
    source_documents: List[Dict[str, Any]] = Field([], description="源文档")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")
    error: Optional[str] = Field(None, description="错误信息")
    raw_output: Optional[Any] = Field(None, description="原始输出")


class AgentChainStep(BaseModel):
    """Agent链步骤定义"""
    agent_id: int = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent名称") 
    position: int = Field(..., description="在链中的位置")
    role: str = Field("processor", description="在链中的角色")
    input_mapping: Dict[str, str] = Field({}, description="输入映射")
    output_mapping: Dict[str, str] = Field({}, description="输出映射")
    condition: Optional[str] = Field(None, description="执行条件")
    fallback: Optional[Dict[str, Any]] = Field(None, description="失败时的后备操作")


class AgentChainDefinition(BaseModel):
    """Agent链定义"""
    id: Optional[str] = Field(None, description="链ID")
    name: str = Field(..., description="链名称")
    description: Optional[str] = Field(None, description="链描述")
    steps: List[AgentChainStep] = Field(..., description="链步骤")
    mode: str = Field("sequential", description="执行模式: sequential, parallel, conditional")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")


class IAgent(Protocol):
    """Agent接口协议"""
    
    async def initialize(self, config: AgentConfig) -> None:
        """初始化Agent
        
        Args:
            config: Agent配置
        """
        ...
    
    async def process(self, input_data: AgentInputSchema) -> AgentOutputSchema:
        """处理输入并生成输出
        
        Args:
            input_data: 输入数据
            
        Returns:
            AgentOutputSchema: 输出数据
        """
        ...
    
    async def add_tools(self, tools: List[Any]) -> None:
        """添加工具
        
        Args:
            tools: 工具列表
        """
        ...
    
    def get_config(self) -> AgentConfig:
        """获取Agent配置
        
        Returns:
            AgentConfig: Agent配置
        """
        ...
    
    def get_capabilities(self) -> List[AgentCapability]:
        """获取Agent能力列表
        
        Returns:
            List[AgentCapability]: Agent能力列表
        """
        ...


class BaseAgentInterface:
    """基础Agent接口实现"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """初始化Agent接口
        
        Args:
            config: Agent配置
        """
        self.config = config or AgentConfig(name="默认Agent", model_name="gpt-3.5-turbo")
        self.tools = []
        self.capabilities = []
        self.initialized = False
    
    async def initialize(self, config: Optional[AgentConfig] = None) -> None:
        """初始化Agent
        
        Args:
            config: Agent配置
        """
        if config:
            self.config = config
        self.initialized = True
    
    async def process(self, input_data: AgentInputSchema) -> AgentOutputSchema:
        """处理输入并生成输出
        
        Args:
            input_data: 输入数据
            
        Returns:
            AgentOutputSchema: 输出数据
        """
        # 基类中的默认实现，返回未实现错误
        return AgentOutputSchema(
            content="",
            error="Agent处理方法未实现",
            metadata={"error_type": "not_implemented"}
        )
    
    async def add_tools(self, tools: List[Any]) -> None:
        """添加工具
        
        Args:
            tools: 工具列表
        """
        self.tools.extend(tools)
    
    def get_config(self) -> AgentConfig:
        """获取Agent配置
        
        Returns:
            AgentConfig: Agent配置
        """
        return self.config
    
    def get_capabilities(self) -> List[AgentCapability]:
        """获取Agent能力列表
        
        Returns:
            List[AgentCapability]: Agent能力列表
        """
        return self.capabilities
