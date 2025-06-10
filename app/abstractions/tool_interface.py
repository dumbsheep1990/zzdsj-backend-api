"""
统一工具接口定义
提供框架无关的工具规范和接口抽象
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import asyncio
from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """工具执行状态"""
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ToolCategory(str, Enum):
    """工具分类"""
    REASONING = "reasoning"              # 推理工具
    THINKING = "thinking"                # 思考工具
    KNOWLEDGE = "knowledge"              # 知识库工具
    SEARCH = "search"                    # 搜索工具
    AGENTIC_SEARCH = "agentic_search"    # 智能搜索
    CHUNKING = "chunking"                # 分块工具
    CALCULATOR = "calculator"            # 计算工具
    FILE_MANAGEMENT = "file_management"  # 文件管理
    MCP = "mcp"                         # MCP协议工具
    CUSTOM = "custom"                   # 自定义工具
    INTEGRATION = "integration"         # 集成工具


@dataclass
class ToolSpec:
    """工具规范定义"""
    # 基本信息
    name: str
    version: str
    description: str
    category: ToolCategory
    provider: str  # 提供方框架 (agno, llamaindex, custom)
    
    # Schema定义
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    
    # 配置
    timeout: Optional[int] = 30  # 超时时间(秒)
    async_supported: bool = True
    batch_supported: bool = False
    
    # 生命周期
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category.value,
            "provider": self.provider,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "metadata": self.metadata,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "timeout": self.timeout,
            "async_supported": self.async_supported,
            "batch_supported": self.batch_supported,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ToolExecutionContext:
    """工具执行上下文"""
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    
    # 执行配置
    timeout: Optional[int] = None
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ToolResult:
    """工具执行结果"""
    # 基本信息
    execution_id: str
    tool_name: str
    status: ToolStatus
    
    # 结果数据
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # 执行信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "trace_data": self.trace_data
        }
    
    def is_success(self) -> bool:
        """判断是否执行成功"""
        return self.status == ToolStatus.COMPLETED and self.error is None
    
    def is_failed(self) -> bool:
        """判断是否执行失败"""
        return self.status in [ToolStatus.FAILED, ToolStatus.TIMEOUT, ToolStatus.CANCELLED]


class UniversalToolInterface(ABC):
    """框架无关的统一工具接口"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """获取提供方名称"""
        pass
    
    @property
    @abstractmethod
    def supported_categories(self) -> List[ToolCategory]:
        """获取支持的工具分类"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化工具接口"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """关闭工具接口"""
        pass
    
    @abstractmethod
    async def register_tool(self, tool_spec: ToolSpec) -> Dict[str, Any]:
        """注册工具"""
        pass
    
    @abstractmethod
    async def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        pass
    
    @abstractmethod
    async def discover_tools(self, 
                           filters: Optional[Dict[str, Any]] = None,
                           categories: Optional[List[ToolCategory]] = None) -> List[ToolSpec]:
        """发现可用工具"""
        pass
    
    @abstractmethod
    async def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """获取工具规范"""
        pass
    
    @abstractmethod
    async def execute_tool(self, 
                          tool_name: str, 
                          params: Dict[str, Any],
                          context: Optional[ToolExecutionContext] = None) -> ToolResult:
        """执行工具"""
        pass
    
    @abstractmethod
    async def validate_params(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """验证工具参数"""
        pass
    
    async def batch_execute(self, 
                          requests: List[Dict[str, Any]],
                          context: Optional[ToolExecutionContext] = None) -> List[ToolResult]:
        """批量执行工具"""
        tasks = []
        for request in requests:
            tool_name = request.get("tool_name")
            params = request.get("params", {})
            task = self.execute_tool(tool_name, params, context)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_tool_status(self, execution_id: str) -> Optional[ToolStatus]:
        """获取工具执行状态"""
        # 默认实现，子类可以重写
        return None
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """取消工具执行"""
        # 默认实现，子类可以重写
        return False


# Pydantic模型用于API请求/响应
class ToolExecutionRequest(BaseModel):
    """工具执行请求模型"""
    tool_name: str = Field(..., description="工具名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    context: Optional[Dict[str, Any]] = Field(None, description="执行上下文")
    timeout: Optional[int] = Field(None, description="超时时间(秒)")


class ToolDiscoveryRequest(BaseModel):
    """工具发现请求模型"""
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    categories: Optional[List[str]] = Field(None, description="工具分类")
    provider: Optional[str] = Field(None, description="提供方框架")


class ToolExecutionResponse(BaseModel):
    """工具执行响应模型"""
    success: bool = Field(..., description="执行是否成功")
    execution_id: str = Field(..., description="执行ID")
    tool_name: str = Field(..., description="工具名称")
    status: str = Field(..., description="执行状态")
    data: Any = Field(None, description="结果数据")
    error: Optional[str] = Field(None, description="错误信息")
    duration_ms: Optional[int] = Field(None, description="执行时长(毫秒)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据") 