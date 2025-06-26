"""
Agno编排系统类型定义和接口
定义了完全解耦合架构中各组件的抽象接口和数据类型
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio

# ==================== 枚举类型定义 ====================

class ToolFramework(Enum):
    """工具框架类型"""
    AGNO = "agno"
    LLAMAINDEX = "llamaindex" 
    OWL = "owl"
    FASTMCP = "fastmcp"
    HAYSTACK = "haystack"
    ZZDSJ = "zzdsj"
    CUSTOM = "custom"

class ToolCategory(Enum):
    """工具类别"""
    REASONING = "reasoning"
    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    CHUNKING = "chunking"
    FILE_MANAGEMENT = "file_management"
    SYSTEM = "system"
    INTEGRATION = "integration"
    CUSTOM = "custom"

class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class AgentRole(Enum):
    """Agent角色类型"""
    ASSISTANT = "assistant"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    CUSTOM = "custom"

class ResponseFormat(Enum):
    """响应格式"""
    JSON = "json"
    TEXT = "text"
    STREAM = "stream"
    STRUCTURED = "structured"
    RAW = "raw"

# ==================== 数据类定义 ====================

@dataclass
class ToolMetadata:
    """工具元数据"""
    id: str
    name: str
    description: str
    category: ToolCategory
    framework: ToolFramework
    version: str = "1.0.0"
    author: str = "ZZDSJ"
    capabilities: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    is_async: bool = True
    is_enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ToolInstance:
    """工具实例"""
    metadata: ToolMetadata
    instance: Any
    config: Dict[str, Any] = field(default_factory=dict)
    is_initialized: bool = False
    last_used: Optional[datetime] = None
    usage_count: int = 0

@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    role: AgentRole
    description: str = ""
    instructions: List[str] = field(default_factory=list)
    model_config: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)  # 工具ID列表
    knowledge_bases: List[str] = field(default_factory=list)
    memory_config: Dict[str, Any] = field(default_factory=dict)
    max_loops: int = 10
    timeout: int = 300  # 超时时间（秒）
    show_tool_calls: bool = True
    markdown: bool = True
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrchestrationRequest:
    """编排请求"""
    user_id: str
    session_id: Optional[str] = None
    task_description: str = ""
    agent_config: Optional[AgentConfig] = None
    frontend_config: Dict[str, Any] = field(default_factory=dict)  # 前端原始配置
    context: Dict[str, Any] = field(default_factory=dict)
    response_format: ResponseFormat = ResponseFormat.JSON
    streaming: bool = False
    priority: int = 0  # 优先级（0最高）
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolCallResult:
    """工具调用结果"""
    tool_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionContext:
    """执行上下文"""
    request_id: str
    user_id: str
    session_id: Optional[str]
    agent_instance: Any = None
    tool_instances: Dict[str, ToolInstance] = field(default_factory=dict)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    status: ExecutionStatus = ExecutionStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrchestrationResult:
    """编排结果"""
    request_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_calls: List[ToolCallResult] = field(default_factory=list)
    agent_config: Optional[AgentConfig] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

# ==================== 抽象接口定义 ====================

class IToolRegistry(ABC):
    """工具注册中心接口"""
    
    @abstractmethod
    async def register_tool(self, tool_metadata: ToolMetadata, tool_class: type) -> bool:
        """注册工具"""
        pass
    
    @abstractmethod
    async def unregister_tool(self, tool_id: str) -> bool:
        """注销工具"""
        pass
    
    @abstractmethod
    async def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        pass
    
    @abstractmethod
    async def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolMetadata]:
        """列出工具"""
        pass
    
    @abstractmethod
    async def create_tool_instance(self, tool_id: str, config: Dict[str, Any]) -> Optional[ToolInstance]:
        """创建工具实例"""
        pass

class IConfigParser(ABC):
    """配置解析器接口"""
    
    @abstractmethod
    async def parse_frontend_config(self, config: Dict[str, Any]) -> AgentConfig:
        """解析前端配置"""
        pass
    
    @abstractmethod
    async def validate_config(self, config: AgentConfig) -> List[str]:
        """验证配置"""
        pass
    
    @abstractmethod
    async def merge_configs(self, base_config: AgentConfig, override_config: Dict[str, Any]) -> AgentConfig:
        """合并配置"""
        pass

class IMatchingEngine(ABC):
    """匹配引擎接口"""
    
    @abstractmethod
    async def match_tools(self, requirements: List[str], available_tools: List[ToolMetadata]) -> List[str]:
        """匹配工具"""
        pass
    
    @abstractmethod
    async def recommend_tools(self, task_description: str, context: Dict[str, Any]) -> List[str]:
        """推荐工具"""
        pass
    
    @abstractmethod
    async def optimize_tool_chain(self, tool_ids: List[str]) -> List[str]:
        """优化工具链"""
        pass

class IAgentAssembler(ABC):
    """Agent组装器接口"""
    
    @abstractmethod
    async def assemble_agent(self, config: AgentConfig, context: ExecutionContext) -> Any:
        """组装Agent"""
        pass
    
    @abstractmethod
    async def validate_assembly(self, agent_instance: Any) -> bool:
        """验证组装结果"""
        pass
    
    @abstractmethod
    async def optimize_agent(self, agent_instance: Any, performance_data: Dict[str, Any]) -> Any:
        """优化Agent"""
        pass

class IExecutionEngine(ABC):
    """执行引擎接口"""
    
    @abstractmethod
    async def execute(self, context: ExecutionContext, query: str) -> OrchestrationResult:
        """执行任务"""
        pass
    
    @abstractmethod
    async def execute_stream(self, context: ExecutionContext, query: str) -> AsyncGenerator[Any, None]:
        """流式执行"""
        pass
    
    @abstractmethod
    async def cancel_execution(self, request_id: str) -> bool:
        """取消执行"""
        pass
    
    @abstractmethod
    async def get_execution_status(self, request_id: str) -> ExecutionStatus:
        """获取执行状态"""
        pass

class IToolCallManager(ABC):
    """工具调用管理器接口"""
    
    @abstractmethod
    async def call_tool(self, tool_instance: ToolInstance, method: str, *args, **kwargs) -> ToolCallResult:
        """调用工具"""
        pass
    
    @abstractmethod
    async def batch_call_tools(self, calls: List[Dict[str, Any]]) -> List[ToolCallResult]:
        """批量调用工具"""
        pass
    
    @abstractmethod
    async def monitor_tool_calls(self, context: ExecutionContext) -> AsyncGenerator[ToolCallResult, None]:
        """监控工具调用"""
        pass

class IResponseProcessor(ABC):
    """响应处理器接口"""
    
    @abstractmethod
    async def process_response(self, raw_response: Any, format: ResponseFormat) -> Any:
        """处理响应"""
        pass
    
    @abstractmethod
    async def format_error(self, error: Exception, context: Optional[ExecutionContext] = None) -> Dict[str, Any]:
        """格式化错误"""
        pass
    
    @abstractmethod
    async def aggregate_results(self, results: List[Any]) -> Any:
        """聚合结果"""
        pass

class IOrchestrationManager(ABC):
    """编排管理器接口"""
    
    @abstractmethod
    async def orchestrate(self, request: OrchestrationRequest) -> OrchestrationResult:
        """执行编排"""
        pass
    
    @abstractmethod
    async def orchestrate_stream(self, request: OrchestrationRequest) -> AsyncGenerator[Any, None]:
        """流式编排"""
        pass
    
    @abstractmethod
    async def get_orchestration_status(self, request_id: str) -> Dict[str, Any]:
        """获取编排状态"""
        pass
    
    @abstractmethod
    async def cancel_orchestration(self, request_id: str) -> bool:
        """取消编排"""
        pass

# ==================== 事件和回调类型 ====================

class OrchestrationEvent(Enum):
    """编排事件类型"""
    STARTED = "started"
    TOOL_CALLED = "tool_called"
    AGENT_RESPONSE = "agent_response"
    ERROR_OCCURRED = "error_occurred"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class EventData:
    """事件数据"""
    event_type: OrchestrationEvent
    request_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

# 事件回调类型
EventCallback = Callable[[EventData], None]
AsyncEventCallback = Callable[[EventData], asyncio.coroutine]

# ==================== 配置和常量 ====================

# 默认配置
DEFAULT_TOOL_TIMEOUT = 30
DEFAULT_AGENT_MAX_LOOPS = 10
DEFAULT_EXECUTION_TIMEOUT = 300
DEFAULT_CACHE_TTL = 3600

# 系统限制
MAX_CONCURRENT_EXECUTIONS = 100
MAX_TOOL_CALLS_PER_REQUEST = 50
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

# 错误代码
class ErrorCode(Enum):
    """错误代码"""
    INVALID_CONFIG = "INVALID_CONFIG"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    INTERNAL_ERROR = "INTERNAL_ERROR" 