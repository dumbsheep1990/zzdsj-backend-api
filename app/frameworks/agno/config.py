"""
Agno Configuration Module: Provides configuration management for Agno framework integration
"""

from typing import Dict, Any, Optional
from app.utils.config_manager import get_config


class AgnoConfig:
    """Configuration manager for Agno framework integration"""
    
    def __init__(self):
        """Initialize Agno configuration from global config"""
        # Load settings from config
        self.enabled = get_config("frameworks", "agno", "enabled", default=True)
        self.log_level = get_config("frameworks", "agno", "log_level", default="INFO")
        
        # API configuration
        self.api_base = get_config("frameworks", "agno", "api_base", default=None)
        self.api_key = get_config("frameworks", "agno", "api_key", default=None)
        self.api_version = get_config("frameworks", "agno", "api_version", default="v1")
        
        # Default models
        self.default_llm_model = get_config("frameworks", "agno", "default_llm_model", default="gpt-4")
        self.default_embedding_model = get_config("frameworks", "agno", "default_embedding_model", 
                                                default="text-embedding-ada-002")
        
        # Knowledge base settings
        self.kb_settings = {
            "chunk_size": get_config("frameworks", "agno", "kb_chunk_size", default=1000),
            "chunk_overlap": get_config("frameworks", "agno", "kb_chunk_overlap", default=200),
            "similarity_threshold": get_config("frameworks", "agno", "kb_similarity_threshold", default=0.7),
            "max_tokens_per_doc": get_config("frameworks", "agno", "kb_max_tokens_per_doc", default=100000)
        }
        
        # Agent settings
        self.agent_settings = {
            "temperature": get_config("frameworks", "agno", "agent_temperature", default=0.7),
            "max_tokens": get_config("frameworks", "agno", "agent_max_tokens", default=1500),
            "memory_enabled": get_config("frameworks", "agno", "agent_memory_enabled", default=True),
            "max_history_messages": get_config("frameworks", "agno", "agent_max_history", default=10)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "enabled": self.enabled,
            "log_level": self.log_level,
            "api": {
                "base": self.api_base,
                "version": self.api_version
            },
            "models": {
                "llm": self.default_llm_model,
                "embeddings": self.default_embedding_model
            },
            "knowledge_base": self.kb_settings,
            "agent": self.agent_settings
        }
    
    def get_kb_settings(self) -> Dict[str, Any]:
        """Get knowledge base settings"""
        return self.kb_settings
    
    def get_agent_settings(self) -> Dict[str, Any]:
        """Get agent settings"""
        return self.agent_settings


# Singleton instance
_agno_config = None

def get_agno_config() -> AgnoConfig:
    """Get Agno configuration singleton"""
    global _agno_config
    if _agno_config is None:
        _agno_config = AgnoConfig()
    return _agno_config
