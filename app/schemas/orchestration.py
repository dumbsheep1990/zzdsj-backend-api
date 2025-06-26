from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ModuleConfigSchema(BaseModel):
    """模块配置Schema"""
    tools: List[str] = Field(default_factory=list, description="工具列表")
    knowledgeBases: List[str] = Field(default_factory=list, description="知识库列表")
    executionStrategy: str = Field(default="sequential", description="执行策略")
    order: int = Field(default=1, description="执行顺序")
    enabled: bool = Field(default=True, description="是否启用")
    parallelGroups: Optional[List[List[str]]] = Field(None, description="并行执行组")
    conditionConfig: Optional[Dict[str, Any]] = Field(None, description="条件执行配置")
    config: Optional[Dict[str, Any]] = Field(None, description="模块特定配置")


class OrchestrationDataSchema(BaseModel):
    """编排数据Schema"""
    executionMode: str = Field(..., description="执行模式: sequential|parallel|conditional")
    modules: Dict[str, ModuleConfigSchema] = Field(..., description="模块配置字典")


class OrchestrationCreate(BaseModel):
    """创建编排请求Schema"""
    assistant_id: int = Field(..., description="助手ID")
    name: str = Field(..., min_length=1, max_length=255, description="编排名称")
    description: Optional[str] = Field(None, max_length=1000, description="编排描述")
    orchestration_config: OrchestrationDataSchema = Field(..., description="编排配置")


class OrchestrationUpdate(BaseModel):
    """更新编排请求Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="编排名称")
    description: Optional[str] = Field(None, max_length=1000, description="编排描述")
    orchestration_config: Optional[OrchestrationDataSchema] = Field(None, description="编排配置")
    is_active: Optional[bool] = Field(None, description="是否激活")


class OrchestrationResponse(BaseModel):
    """编排响应Schema"""
    id: int
    assistant_id: int
    name: str
    description: Optional[str]
    orchestration_config: Dict[str, Any]
    execution_plan: Optional[Dict[str, Any]]
    is_active: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


class OrchestrationExecutionRequest(BaseModel):
    """编排执行请求Schema"""
    orchestration_id: int = Field(..., description="编排ID")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    session_id: Optional[str] = Field(None, description="会话ID，可选")


class StepExecutionDetail(BaseModel):
    """步骤执行详情Schema"""
    step_id: str
    module_name: str
    status: str  # success, failed, skipped, running
    duration_ms: int
    timestamp: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class OrchestrationExecutionResponse(BaseModel):
    """编排执行响应Schema"""
    session_id: str
    status: str  # running, completed, failed, cancelled
    output_data: Optional[Dict[str, Any]] = None
    execution_trace: Optional[List[StepExecutionDetail]] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OrchestrationExecutionStatus(BaseModel):
    """编排执行状态Schema"""
    session_id: str
    orchestration_id: int
    status: str
    progress: Optional[Dict[str, Any]] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    elapsed_ms: Optional[int] = None
    estimated_remaining_ms: Optional[int] = None
    execution_trace: List[StepExecutionDetail]
    partial_output: Optional[Dict[str, Any]] = None


class OrchestrationValidationResult(BaseModel):
    """编排配置验证结果Schema"""
    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class OrchestrationStats(BaseModel):
    """编排统计信息Schema"""
    total_orchestrations: int
    active_orchestrations: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration_ms: float


class OrchestrationMetrics(BaseModel):
    """编排系统指标Schema"""
    current_load: Dict[str, Any]
    resource_usage: Dict[str, Any]
    performance: Dict[str, Any]
    error_rates: Dict[str, Any]


class OrchestrationHealthCheck(BaseModel):
    """编排系统健康检查Schema"""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    components: Dict[str, Dict[str, Any]]
    dependencies: Dict[str, str] 