"""AI知识图谱配置模块
管理AI知识图谱的相关配置参数和设置
"""

from typing import Dict, Any, Optional
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AIKnowledgeGraphConfig:
    """管理AI知识图谱配置的类"""
    
    def __init__(self):
        """初始化配置类"""
        # 基本配置
        self.enabled = os.getenv('AI_KG_ENABLED', 'true').lower() == 'true'
        self.base_dir = os.getenv('AI_KG_BASE_DIR', './data/ai_knowledge_graph')
        
        # 处理配置
        self.chunk_size = int(os.getenv('AI_KG_CHUNK_SIZE', '500'))
        self.chunk_overlap = int(os.getenv('AI_KG_CHUNK_OVERLAP', '50'))
        self.max_tokens = int(os.getenv('AI_KG_MAX_TOKENS', '8192'))
        self.temperature = float(os.getenv('AI_KG_TEMPERATURE', '0.8'))
        
        # 实体标准化配置
        self.standardization_enabled = os.getenv('AI_KG_STANDARDIZATION_ENABLED', 'true').lower() == 'true'
        self.use_llm_for_entities = os.getenv('AI_KG_USE_LLM_FOR_ENTITIES', 'true').lower() == 'true'
        
        # 关系推断配置
        self.inference_enabled = os.getenv('AI_KG_INFERENCE_ENABLED', 'true').lower() == 'true'
        self.use_llm_for_inference = os.getenv('AI_KG_USE_LLM_FOR_INFERENCE', 'true').lower() == 'true'
        self.apply_transitive = os.getenv('AI_KG_APPLY_TRANSITIVE', 'true').lower() == 'true'
        
        # 可视化配置
        self.edge_smooth = os.getenv('AI_KG_EDGE_SMOOTH', 'false').lower() == 'true'
        self.output_format = os.getenv('AI_KG_OUTPUT_FORMAT', 'html')
        self.visualization = {
            "width": os.getenv('AI_KG_VIS_WIDTH', "100%"),
            "height": os.getenv('AI_KG_VIS_HEIGHT', "800px"),
            "bgcolor": os.getenv('AI_KG_VIS_BGCOLOR', "#ffffff"),
            "font_color": os.getenv('AI_KG_VIS_FONT_COLOR', "#000000")
        }
        
        # 存储配置
        self.storage_type = os.getenv('AI_KG_STORAGE_TYPE', 'database')  # database, file
        self.storage_path = os.getenv('AI_KG_STORAGE_PATH', os.path.join(self.base_dir, 'storage'))
        
        # 社区检测配置
        self.min_community_size = int(os.getenv('AI_KG_MIN_COMMUNITY_SIZE', '2'))
        
        # 导出配置
        self.export_formats = os.getenv('AI_KG_EXPORT_FORMATS', 'json,csv,rdf,cypher').split(',')
        
        # 创建基础目录
        if self.enabled:
            os.makedirs(self.base_dir, exist_ok=True)
    
    def get_processing_config(self) -> Dict[str, Any]:
        """获取处理配置
        
        Returns:
            处理配置字典
        """
        return {
            "chunking": {
                "chunk_size": self.chunk_size,
                "overlap": self.chunk_overlap
            },
            "llm": {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            },
            "standardization": {
                "enabled": self.standardization_enabled,
                "use_llm_for_entities": self.use_llm_for_entities
            },
            "inference": {
                "enabled": self.inference_enabled,
                "use_llm_for_inference": self.use_llm_for_inference,
                "apply_transitive": self.apply_transitive
            },
            "visualization": {
                "edge_smooth": self.edge_smooth
            }
        }
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置
        
        Returns:
            存储配置字典
        """
        return {
            "type": self.storage_type,
            "base_dir": self.base_dir
        }
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取完整配置字典
        
        Returns:
            配置字典
        """
        return {
            "enabled": self.enabled,
            "base_dir": self.base_dir,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "standardization_enabled": self.standardization_enabled,
            "use_llm_for_entities": self.use_llm_for_entities,
            "inference_enabled": self.inference_enabled,
            "use_llm_for_inference": self.use_llm_for_inference,
            "apply_transitive": self.apply_transitive,
            "edge_smooth": self.edge_smooth,
            "output_format": self.output_format,
            "storage_type": self.storage_type
        }
    
    def get_graph_id_for_knowledge_base(self, knowledge_base_id: int) -> str:
        """为知识库生成图谱ID
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            图谱ID
        """
        return f"kb_{knowledge_base_id}"
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """更新配置
        
        Args:
            config_updates: 配置更新字典
        """
        for key, value in config_updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"更新配置: {key} = {value}")


# 全局配置实例
kg_config = AIKnowledgeGraphConfig()


def get_config() -> AIKnowledgeGraphConfig:
    """获取配置实例
    
    Returns:
        配置实例
    """
    return kg_config


def reload_config() -> AIKnowledgeGraphConfig:
    """重新加载配置
    
    Returns:
        新的配置实例
    """
    global kg_config
    kg_config = AIKnowledgeGraphConfig()
    return kg_config 