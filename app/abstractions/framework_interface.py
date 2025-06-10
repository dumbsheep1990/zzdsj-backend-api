"""
框架接口抽象定义
提供AI框架的统一接口和能力描述
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .tool_interface import ToolCategory, ToolSpec, UniversalToolInterface


class FrameworkStatus(str, Enum):
    """框架状态"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class FrameworkCapability(str, Enum):
    """框架能力"""
    # 核心能力
    AGENT_CREATION = "agent_creation"           # 代理创建
    CONVERSATION = "conversation"               # 对话能力
    REASONING = "reasoning"                     # 推理能力
    PLANNING = "planning"                       # 规划能力
    
    # 工具能力
    TOOL_CALLING = "tool_calling"               # 工具调用
    TOOL_REGISTRATION = "tool_registration"     # 工具注册
    CUSTOM_TOOLS = "custom_tools"               # 自定义工具
    BATCH_TOOLS = "batch_tools"                 # 批量工具执行
    
    # 知识能力
    KNOWLEDGE_BASE = "knowledge_base"           # 知识库
    RAG_RETRIEVAL = "rag_retrieval"            # RAG检索
    SEMANTIC_SEARCH = "semantic_search"         # 语义搜索
    DOCUMENT_PROCESSING = "document_processing" # 文档处理
    
    # 多模态能力
    TEXT_PROCESSING = "text_processing"         # 文本处理
    IMAGE_PROCESSING = "image_processing"       # 图像处理
    AUDIO_PROCESSING = "audio_processing"       # 音频处理
    VIDEO_PROCESSING = "video_processing"       # 视频处理
    
    # 协作能力
    MULTI_AGENT = "multi_agent"                # 多代理
    TEAM_COORDINATION = "team_coordination"     # 团队协调
    WORKFLOW = "workflow"                       # 工作流
    ORCHESTRATION = "orchestration"             # 编排
    
    # 集成能力
    API_INTEGRATION = "api_integration"         # API集成
    DATABASE_INTEGRATION = "database_integration" # 数据库集成
    EXTERNAL_SERVICES = "external_services"     # 外部服务
    MCP_PROTOCOL = "mcp_protocol"              # MCP协议


@dataclass
class FrameworkInfo:
    """框架信息"""
    name: str
    version: str
    description: str
    vendor: str
    license: str
    
    # 能力描述
    capabilities: Set[FrameworkCapability] = field(default_factory=set)
    supported_categories: Set[ToolCategory] = field(default_factory=set)
    
    # 技术信息
    python_version: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # 生命周期
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "vendor": self.vendor,
            "license": self.license,
            "capabilities": [cap.value for cap in self.capabilities],
            "supported_categories": [cat.value for cat in self.supported_categories],
            "python_version": self.python_version,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class FrameworkConfig:
    """框架配置"""
    # 基本配置
    enabled: bool = True
    auto_initialize: bool = True
    lazy_loading: bool = False
    
    # 性能配置
    max_concurrent_tools: int = 10
    default_timeout: int = 30
    retry_attempts: int = 3
    
    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 3600  # 秒
    
    # 日志配置
    log_level: str = "INFO"
    enable_tracing: bool = True
    
    # 自定义配置
    custom_config: Dict[str, Any] = field(default_factory=dict)


class FrameworkInterface(ABC):
    """AI框架统一接口抽象"""
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        self.config = config or FrameworkConfig()
        self._status = FrameworkStatus.UNINITIALIZED
        self._tool_interface: Optional[UniversalToolInterface] = None
    
    @property
    @abstractmethod
    def framework_info(self) -> FrameworkInfo:
        """获取框架信息"""
        pass
    
    @property
    def status(self) -> FrameworkStatus:
        """获取框架状态"""
        return self._status
    
    @property
    def tool_interface(self) -> Optional[UniversalToolInterface]:
        """获取工具接口"""
        return self._tool_interface
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化框架"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """关闭框架"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
    
    @abstractmethod
    def has_capability(self, capability: FrameworkCapability) -> bool:
        """检查是否具有指定能力"""
        pass
    
    @abstractmethod
    def supports_category(self, category: ToolCategory) -> bool:
        """检查是否支持指定工具分类"""
        pass
    
    async def get_available_tools(self, category: Optional[ToolCategory] = None) -> List[ToolSpec]:
        """获取可用工具"""
        if not self._tool_interface:
            return []
        
        categories = [category] if category else None
        return await self._tool_interface.discover_tools(categories=categories)
    
    async def create_tool_interface(self) -> UniversalToolInterface:
        """创建工具接口实例"""
        # 子类应该实现此方法
        raise NotImplementedError("Subclass must implement create_tool_interface")
    
    async def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 基本验证逻辑
        if self.config.max_concurrent_tools <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("max_concurrent_tools must be positive")
        
        if self.config.default_timeout <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("default_timeout must be positive")
        
        return validation_result
    
    def update_status(self, status: FrameworkStatus):
        """更新框架状态"""
        self._status = status
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取框架指标"""
        return {
            "status": self._status.value,
            "config": {
                "enabled": self.config.enabled,
                "max_concurrent_tools": self.config.max_concurrent_tools,
                "default_timeout": self.config.default_timeout
            },
            "capabilities": [cap.value for cap in self.framework_info.capabilities],
            "tool_interface_available": self._tool_interface is not None
        }


class FrameworkRegistry:
    """框架注册表"""
    
    def __init__(self):
        self._frameworks: Dict[str, FrameworkInterface] = {}
        self._configs: Dict[str, FrameworkConfig] = {}
    
    def register(self, name: str, framework: FrameworkInterface, config: Optional[FrameworkConfig] = None):
        """注册框架"""
        self._frameworks[name] = framework
        if config:
            self._configs[name] = config
    
    def unregister(self, name: str) -> bool:
        """注销框架"""
        if name in self._frameworks:
            del self._frameworks[name]
            if name in self._configs:
                del self._configs[name]
            return True
        return False
    
    def get_framework(self, name: str) -> Optional[FrameworkInterface]:
        """获取框架实例"""
        return self._frameworks.get(name)
    
    def get_config(self, name: str) -> Optional[FrameworkConfig]:
        """获取框架配置"""
        return self._configs.get(name)
    
    def list_frameworks(self) -> List[str]:
        """列出所有注册的框架"""
        return list(self._frameworks.keys())
    
    def get_frameworks_by_capability(self, capability: FrameworkCapability) -> List[str]:
        """根据能力获取框架列表"""
        result = []
        for name, framework in self._frameworks.items():
            if framework.has_capability(capability):
                result.append(name)
        return result
    
    def get_frameworks_by_category(self, category: ToolCategory) -> List[str]:
        """根据工具分类获取框架列表"""
        result = []
        for name, framework in self._frameworks.items():
            if framework.supports_category(category):
                result.append(name)
        return result
    
    async def initialize_all(self) -> Dict[str, bool]:
        """初始化所有已启用的框架"""
        results = {}
        for name, framework in self._frameworks.items():
            config = self._configs.get(name, FrameworkConfig())
            if config.enabled:
                try:
                    result = await framework.initialize()
                    results[name] = result
                except Exception as e:
                    results[name] = False
                    print(f"Failed to initialize framework {name}: {e}")
        return results
    
    async def shutdown_all(self) -> Dict[str, bool]:
        """关闭所有框架"""
        results = {}
        for name, framework in self._frameworks.items():
            try:
                result = await framework.shutdown()
                results[name] = result
            except Exception as e:
                results[name] = False
                print(f"Failed to shutdown framework {name}: {e}")
        return results 