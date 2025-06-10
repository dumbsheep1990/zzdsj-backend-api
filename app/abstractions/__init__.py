"""
ZZDSJ抽象接口层
提供框架无关的统一工具接口和抽象定义
"""

from .tool_interface import (
    ToolSpec,
    ToolResult,
    ToolStatus,
    ToolCategory,
    UniversalToolInterface,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolDiscoveryRequest,
    ToolExecutionResponse,
)
from .framework_interface import (
    FrameworkInterface,
    FrameworkCapability,
    FrameworkStatus,
    FrameworkInfo,
    FrameworkConfig,
)

__all__ = [
    # 工具接口
    "ToolSpec",
    "ToolResult", 
    "ToolStatus",
    "ToolCategory",
    "UniversalToolInterface",
    "ToolExecutionContext",
    "ToolExecutionRequest",
    "ToolDiscoveryRequest", 
    "ToolExecutionResponse",
    
    # 框架接口
    "FrameworkInterface",
    "FrameworkCapability", 
    "FrameworkStatus",
    "FrameworkInfo",
    "FrameworkConfig",
]

__version__ = "1.0.0" 