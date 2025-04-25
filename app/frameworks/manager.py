"""
框架管理器: 协调并提供对不同AI框架集成的访问
这使得核心业务逻辑可以与具体框架无关
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from app.config import settings


class FrameworkType(Enum):
    """支持的AI框架枚举"""
    HAYSTACK = "haystack" 
    LLAMAINDEX = "llamaindex"
    AGNO = "agno"
    FASTMCP = "fastmcp"


class FrameworkCapability(Enum):
    """AI框架支持的能力枚举"""
    EMBEDDINGS = "embeddings"
    RETRIEVAL = "retrieval"
    QUESTION_ANSWERING = "question_answering"
    DOCUMENT_PROCESSING = "document_processing"
    AGENT = "agent"
    CHAT = "chat"
    MCP_TOOLS = "mcp_tools"


class FrameworkManager:
    """
    AI框架管理器，提供统一接口访问
    不同框架的能力，基于配置和用例
    """
    
    def __init__(self):
        self._framework_registry = {}
        self._capability_registry = {}
        self._default_frameworks = {}
        
        # 初始化框架注册表
        self._init_registry()
    
    def _init_registry(self):
        """使用可用框架初始化框架注册表"""
        # 为每个能力注册默认框架
        if settings.get_config("frameworks", "haystack", "enabled", default=True):
            self._register_haystack()
        
        if settings.get_config("frameworks", "llamaindex", "enabled", default=True):
            self._register_llamaindex()
        
        if settings.get_config("frameworks", "agno", "enabled", default=False):
            self._register_agno()
            
        if settings.get_config("frameworks", "fastmcp", "enabled", default=False):
            self._register_fastmcp()
    
    def _register_haystack(self):
        """注册Haystack框架及其能力"""
        from app.frameworks.haystack import document_store, retrieval, reader
        
        # 注册框架
        self._framework_registry[FrameworkType.HAYSTACK] = {
            FrameworkCapability.RETRIEVAL: retrieval,
            FrameworkCapability.QUESTION_ANSWERING: reader,
            FrameworkCapability.DOCUMENT_PROCESSING: document_store
        }
        
        # 注册以Haystack为提供者的能力
        self._register_capability(FrameworkCapability.QUESTION_ANSWERING, FrameworkType.HAYSTACK)
    
    def _register_llamaindex(self):
        """注册LlamaIndex框架及其能力"""
        from app.frameworks.llamaindex import indexing, retrieval, agent
        
        # 注册框架
        self._framework_registry[FrameworkType.LLAMAINDEX] = {
            FrameworkCapability.DOCUMENT_PROCESSING: indexing,
            FrameworkCapability.RETRIEVAL: retrieval,
            FrameworkCapability.AGENT: agent
        }
        
        # 注册以LlamaIndex为提供者的能力
        self._register_capability(FrameworkCapability.DOCUMENT_PROCESSING, FrameworkType.LLAMAINDEX)
    
    def _register_agno(self):
        """注册Agno框架及其能力"""
        from app.frameworks.agents import agent
        
        # 注册框架
        self._framework_registry[FrameworkType.AGNO] = {
            FrameworkCapability.AGENT: agent
        }
        
        # 注册以Agno为提供者的能力
        self._register_capability(FrameworkCapability.AGENT, FrameworkType.AGNO)
        
    def _register_fastmcp(self):
        """注册FastMCP框架及其能力"""
        from app.frameworks.fastmcp import tools, resources, server
        
        # 注册框架
        self._framework_registry[FrameworkType.FASTMCP] = {
            FrameworkCapability.MCP_TOOLS: tools,
            FrameworkCapability.AGENT: resources
        }
        
        # 注册以FastMCP为提供者的能力
        self._register_capability(FrameworkCapability.MCP_TOOLS, FrameworkType.FASTMCP)
    
    def _register_capability(self, capability: FrameworkCapability, framework: FrameworkType):
        """注册能力及其提供框架"""
        if capability not in self._capability_registry:
            self._capability_registry[capability] = []
        
        # 如果尚未注册，将框架添加到能力提供者
        if framework not in self._capability_registry[capability]:
            self._capability_registry[capability].append(framework)
        
        # 如果没有默认框架或配置为默认，则设置为默认
        if capability not in self._default_frameworks:
            self._default_frameworks[capability] = framework
    
    def get_framework(self, framework_type: FrameworkType) -> Dict[FrameworkCapability, Any]:
        """获取特定框架的所有能力"""
        if framework_type not in self._framework_registry:
            raise ValueError(f"框架 {framework_type.value} 未注册")
        
        return self._framework_registry[framework_type]
    
    def get_capability(self, 
                      capability: FrameworkCapability, 
                      framework_type: Optional[FrameworkType] = None) -> Any:
        """
        获取特定能力的实现
        如果指定了framework_type，则返回该框架的实现
        否则，使用该能力的默认框架
        """
        # 如果指定了框架，使用该实现
        if framework_type is not None:
            if framework_type not in self._framework_registry:
                raise ValueError(f"框架 {framework_type.value} 未注册")
            
            framework_capabilities = self._framework_registry[framework_type]
            if capability not in framework_capabilities:
                raise ValueError(f"能力 {capability.value} 不被 {framework_type.value} 支持")
            
            return framework_capabilities[capability]
        
        # 否则使用此能力的默认框架
        if capability not in self._default_frameworks:
            raise ValueError(f"没有为能力 {capability.value} 注册默认框架")
        
        default_framework = self._default_frameworks[capability]
        return self._framework_registry[default_framework][capability]
    
    def list_frameworks(self) -> List[FrameworkType]:
        """列出所有注册的框架"""
        return list(self._framework_registry.keys())
    
    def list_capabilities(self) -> List[FrameworkCapability]:
        """列出所有注册的能力"""
        return list(self._capability_registry.keys())
    
    def get_capability_providers(self, capability: FrameworkCapability) -> List[FrameworkType]:
        """获取提供特定能力的所有框架"""
        if capability not in self._capability_registry:
            return []
        
        return self._capability_registry[capability]


# 框架管理器的单例实例
_framework_manager = None

def get_framework_manager() -> FrameworkManager:
    """获取或初始化框架管理器单例"""
    global _framework_manager
    
    if _framework_manager is None:
        _framework_manager = FrameworkManager()
    
    return _framework_manager
