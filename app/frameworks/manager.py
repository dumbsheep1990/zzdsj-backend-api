"""
Framework Manager: Orchestrates and provides access to different AI framework integrations
This allows the core business logic to be framework-agnostic
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from app.config import settings


class FrameworkType(Enum):
    """Enum for supported AI frameworks"""
    LANGCHAIN = "langchain"
    HAYSTACK = "haystack" 
    LLAMAINDEX = "llamaindex"
    AGNO = "agno"


class FrameworkCapability(Enum):
    """Enum for supported capabilities of AI frameworks"""
    EMBEDDINGS = "embeddings"
    RETRIEVAL = "retrieval"
    QUESTION_ANSWERING = "question_answering"
    DOCUMENT_PROCESSING = "document_processing"
    AGENT = "agent"
    CHAT = "chat"


class FrameworkManager:
    """
    Manager for AI frameworks that provides a unified interface to access
    different framework capabilities based on configuration and use case
    """
    
    def __init__(self):
        self._framework_registry = {}
        self._capability_registry = {}
        self._default_frameworks = {}
        
        # Initialize the framework registry
        self._init_registry()
    
    def _init_registry(self):
        """Initialize the framework registry with available frameworks"""
        # Register default framework for each capability
        if settings.get_config("frameworks", "langchain", "enabled", default=True):
            self._register_langchain()
        
        if settings.get_config("frameworks", "haystack", "enabled", default=True):
            self._register_haystack()
        
        if settings.get_config("frameworks", "llamaindex", "enabled", default=True):
            self._register_llamaindex()
        
        if settings.get_config("frameworks", "agno", "enabled", default=False):
            self._register_agno()
    
    def _register_langchain(self):
        """Register LangChain framework and capabilities"""
        from app.frameworks.langchain import embeddings, chat, retrieval
        
        # Register the framework
        self._framework_registry[FrameworkType.LANGCHAIN] = {
            FrameworkCapability.EMBEDDINGS: embeddings,
            FrameworkCapability.CHAT: chat,
            FrameworkCapability.RETRIEVAL: retrieval
        }
        
        # Register capabilities with LangChain as provider
        self._register_capability(FrameworkCapability.EMBEDDINGS, FrameworkType.LANGCHAIN)
        self._register_capability(FrameworkCapability.CHAT, FrameworkType.LANGCHAIN)
    
    def _register_haystack(self):
        """Register Haystack framework and capabilities"""
        from app.frameworks.haystack import document_store, retrieval, reader
        
        # Register the framework
        self._framework_registry[FrameworkType.HAYSTACK] = {
            FrameworkCapability.RETRIEVAL: retrieval,
            FrameworkCapability.QUESTION_ANSWERING: reader,
            FrameworkCapability.DOCUMENT_PROCESSING: document_store
        }
        
        # Register capabilities with Haystack as provider
        self._register_capability(FrameworkCapability.QUESTION_ANSWERING, FrameworkType.HAYSTACK)
    
    def _register_llamaindex(self):
        """Register LlamaIndex framework and capabilities"""
        from app.frameworks.llamaindex import indexing, retrieval, agent
        
        # Register the framework
        self._framework_registry[FrameworkType.LLAMAINDEX] = {
            FrameworkCapability.DOCUMENT_PROCESSING: indexing,
            FrameworkCapability.RETRIEVAL: retrieval,
            FrameworkCapability.AGENT: agent
        }
        
        # Register capabilities with LlamaIndex as provider
        self._register_capability(FrameworkCapability.DOCUMENT_PROCESSING, FrameworkType.LLAMAINDEX)
    
    def _register_agno(self):
        """Register Agno framework and capabilities"""
        from app.frameworks.agents import agent
        
        # Register the framework
        self._framework_registry[FrameworkType.AGNO] = {
            FrameworkCapability.AGENT: agent
        }
        
        # Register capabilities with Agno as provider
        self._register_capability(FrameworkCapability.AGENT, FrameworkType.AGNO)
    
    def _register_capability(self, capability: FrameworkCapability, framework: FrameworkType):
        """Register a capability with its providing framework"""
        if capability not in self._capability_registry:
            self._capability_registry[capability] = []
        
        # Add framework to capability providers if not already registered
        if framework not in self._capability_registry[capability]:
            self._capability_registry[capability].append(framework)
        
        # Set as default if no default exists or if configured as default
        if capability not in self._default_frameworks:
            self._default_frameworks[capability] = framework
    
    def get_framework(self, framework_type: FrameworkType) -> Dict[FrameworkCapability, Any]:
        """Get all capabilities for a specific framework"""
        if framework_type not in self._framework_registry:
            raise ValueError(f"Framework {framework_type.value} is not registered")
        
        return self._framework_registry[framework_type]
    
    def get_capability(self, 
                      capability: FrameworkCapability, 
                      framework_type: Optional[FrameworkType] = None) -> Any:
        """
        Get a specific capability implementation
        If framework_type is specified, that framework's implementation is returned
        Otherwise, the default framework for that capability is used
        """
        # If framework is specified, use that implementation
        if framework_type is not None:
            if framework_type not in self._framework_registry:
                raise ValueError(f"Framework {framework_type.value} is not registered")
            
            framework_capabilities = self._framework_registry[framework_type]
            if capability not in framework_capabilities:
                raise ValueError(f"Capability {capability.value} not supported by {framework_type.value}")
            
            return framework_capabilities[capability]
        
        # Otherwise use the default framework for this capability
        if capability not in self._default_frameworks:
            raise ValueError(f"No default framework registered for capability {capability.value}")
        
        default_framework = self._default_frameworks[capability]
        return self._framework_registry[default_framework][capability]
    
    def list_frameworks(self) -> List[FrameworkType]:
        """List all registered frameworks"""
        return list(self._framework_registry.keys())
    
    def list_capabilities(self) -> List[FrameworkCapability]:
        """List all registered capabilities"""
        return list(self._capability_registry.keys())
    
    def get_capability_providers(self, capability: FrameworkCapability) -> List[FrameworkType]:
        """Get all frameworks that provide a specific capability"""
        if capability not in self._capability_registry:
            return []
        
        return self._capability_registry[capability]


# Singleton instance of the framework manager
_framework_manager = None

def get_framework_manager() -> FrameworkManager:
    """Get or initialize the framework manager singleton"""
    global _framework_manager
    
    if _framework_manager is None:
        _framework_manager = FrameworkManager()
    
    return _framework_manager
