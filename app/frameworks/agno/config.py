"""
Agno配置模块：为Agno框架集成提供配置管理
"""

from typing import Dict, Any, Optional
from app.utils.config_manager import get_config


class AgnoConfig:
    """Agno框架集成的配置管理器"""
    
    def __init__(self):
        """从全局配置初始化Agno配置"""
        # 从配置加载设置
        self.enabled = get_config("frameworks", "agno", "enabled", default=True)
        self.log_level = get_config("frameworks", "agno", "log_level", default="INFO")
        
        # API配置
        self.api_base = get_config("frameworks", "agno", "api_base", default=None)
        self.api_key = get_config("frameworks", "agno", "api_key", default=None)
        self.api_version = get_config("frameworks", "agno", "api_version", default="v1")
        
        # 默认模型
        self.default_llm_model = get_config("frameworks", "agno", "default_llm_model", default="gpt-4")
        self.default_embedding_model = get_config("frameworks", "agno", "default_embedding_model", 
                                                default="text-embedding-ada-002")
        
        # 知识库设置
        self.kb_settings = {
            "chunk_size": get_config("frameworks", "agno", "kb_chunk_size", default=1000),
            "chunk_overlap": get_config("frameworks", "agno", "kb_chunk_overlap", default=200),
            "similarity_threshold": get_config("frameworks", "agno", "kb_similarity_threshold", default=0.7),
            "max_tokens_per_doc": get_config("frameworks", "agno", "kb_max_tokens_per_doc", default=100000)
        }
        
        # 代理设置
        self.agent_settings = {
            "temperature": get_config("frameworks", "agno", "agent_temperature", default=0.7),
            "max_tokens": get_config("frameworks", "agno", "agent_max_tokens", default=1500),
            "memory_enabled": get_config("frameworks", "agno", "agent_memory_enabled", default=True),
            "max_history_messages": get_config("frameworks", "agno", "agent_max_history", default=10)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
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
        """获取知识库设置"""
        return self.kb_settings
    
    def get_agent_settings(self) -> Dict[str, Any]:
        """获取代理设置"""
        return self.agent_settings


# 单例实例
_agno_config = None

def get_agno_config() -> AgnoConfig:
    """获取Agno配置单例"""
    global _agno_config
    if _agno_config is None:
        _agno_config = AgnoConfig()
    return _agno_config
