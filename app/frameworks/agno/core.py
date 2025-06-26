"""
Agno核心模块 - 动态配置版本
提供与ZZDSJ系统配置集成的Agno核心接口，去除硬编码依赖
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.frameworks.agno.model_config_adapter import (
    ZZDSJAgnoModelAdapter, 
    ModelType, 
    ModelConfiguration,
    get_model_adapter
)

# 动态导入Agno组件
try:
    from agno.agent import Agent as AgnoAgent
    from agno.models.base import Model as AgnoModel
    from agno.memory import Memory as AgnoMemory
    from agno.storage import Storage as AgnoStorage
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    AgnoAgent = object
    AgnoModel = object

logger = logging.getLogger(__name__)

@dataclass
class AgnoServiceContext:
    """Agno服务上下文 - 动态配置版本"""
    
    # 动态模型配置
    chat_model: Optional[AgnoModel] = None
    embedding_model: Optional[AgnoModel] = None
    rerank_model: Optional[AgnoModel] = None
    
    # 系统配置
    model_adapter: Optional[ZZDSJAgnoModelAdapter] = None
    
    # 运行时配置
    chunk_size: int = 1024
    chunk_overlap: int = 200
    similarity_top_k: int = 5
    response_mode: str = "compact"
    
    def __post_init__(self):
        """初始化后处理"""
        if self.model_adapter is None:
            self.model_adapter = get_model_adapter()

class AgnoLLMInterface(ABC):
    """Agno LLM统一接口 - 支持动态模型配置"""
    
    def __init__(self, model_config: Optional[ModelConfiguration] = None):
        self.model_config = model_config
        self._agno_model = None
        self._model_adapter = get_model_adapter()
    
    @property
    async def agno_model(self) -> Optional[AgnoModel]:
        """获取Agno模型实例"""
        if self._agno_model is None:
            self._agno_model = await self._create_agno_model()
        return self._agno_model
    
    async def _create_agno_model(self) -> Optional[AgnoModel]:
        """创建Agno模型实例"""
        try:
            if self.model_config:
                # 使用指定配置
                return await self._model_adapter.create_agno_model_by_type(
                    ModelType.CHAT, self.model_config.model_id
                )
            else:
                # 使用默认配置
                return await self._model_adapter.create_agno_model_by_type(ModelType.CHAT)
        except Exception as e:
            logger.error(f"创建Agno模型失败: {str(e)}")
            return None
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成响应"""
        pass
    
    @abstractmethod
    async def agenerate(self, prompt: str, **kwargs) -> str:
        """异步生成响应"""
        pass

class DynamicAgnoLLM(AgnoLLMInterface):
    """动态Agno LLM实现"""
    
    def __init__(self, model_id: Optional[str] = None, model_type: ModelType = ModelType.CHAT):
        """初始化动态LLM
        
        Args:
            model_id: 模型ID，如果为None则使用默认模型
            model_type: 模型类型
        """
        self.model_id = model_id
        self.model_type = model_type
        self._model_adapter = get_model_adapter()
        self._agno_model = None
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成响应"""
        model = await self.agno_model
        if not model:
            raise RuntimeError("无法获取模型实例")
        
        try:
            # 使用Agno模型生成响应
            response = await model.agenerate(prompt, **kwargs)
            return str(response)
        except Exception as e:
            logger.error(f"模型生成失败: {str(e)}")
            raise
    
    async def agenerate(self, prompt: str, **kwargs) -> str:
        """异步生成响应"""
        return await self.generate(prompt, **kwargs)
    
    @property
    async def agno_model(self) -> Optional[AgnoModel]:
        """获取Agno模型实例"""
        if self._agno_model is None:
            self._agno_model = await self._create_model_instance()
        return self._agno_model
    
    async def _create_model_instance(self) -> Optional[AgnoModel]:
        """创建模型实例"""
        try:
            if self.model_id:
                return await self._model_adapter.create_agno_model_by_type(
                    self.model_type, self.model_id
                )
            else:
                return await self._model_adapter.create_agno_model_by_type(self.model_type)
        except Exception as e:
            logger.error(f"创建模型实例失败: {str(e)}")
            return None

class AgnoServiceContextBuilder:
    """Agno服务上下文构建器 - 动态配置版本"""
    
    def __init__(self):
        self.model_adapter = get_model_adapter()
        self._context_config = {}
    
    async def build_from_system_config(self, user_id: Optional[str] = None) -> AgnoServiceContext:
        """从系统配置构建服务上下文
        
        Args:
            user_id: 用户ID，用于个性化配置
            
        Returns:
            AgnoServiceContext: 构建的服务上下文
        """
        try:
            # 获取默认模型配置
            chat_model = await self.model_adapter.create_agno_model_by_type(ModelType.CHAT)
            embedding_model = await self.model_adapter.create_agno_model_by_type(ModelType.EMBEDDING)
            rerank_model = await self.model_adapter.create_agno_model_by_type(ModelType.RERANK)
            
            # 从系统配置获取其他参数
            system_config = await self._get_system_config(user_id)
            
            return AgnoServiceContext(
                chat_model=chat_model,
                embedding_model=embedding_model,
                rerank_model=rerank_model,
                model_adapter=self.model_adapter,
                chunk_size=system_config.get('chunk_size', 1024),
                chunk_overlap=system_config.get('chunk_overlap', 200),
                similarity_top_k=system_config.get('similarity_top_k', 5),
                response_mode=system_config.get('response_mode', 'compact')
            )
            
        except Exception as e:
            logger.error(f"构建服务上下文失败: {str(e)}")
            # 返回默认配置的上下文
            return AgnoServiceContext(model_adapter=self.model_adapter)
    
    async def build_from_config(self, config: Dict[str, Any]) -> AgnoServiceContext:
        """从配置字典构建服务上下文
        
        Args:
            config: 配置字典
            
        Returns:
            AgnoServiceContext: 构建的服务上下文
        """
        try:
            # 创建指定的模型
            chat_model = None
            if config.get('chat_model_id'):
                chat_model = await self.model_adapter.create_agno_model_by_type(
                    ModelType.CHAT, config['chat_model_id']
                )
            
            embedding_model = None
            if config.get('embedding_model_id'):
                embedding_model = await self.model_adapter.create_agno_model_by_type(
                    ModelType.EMBEDDING, config['embedding_model_id']
                )
            
            rerank_model = None
            if config.get('rerank_model_id'):
                rerank_model = await self.model_adapter.create_agno_model_by_type(
                    ModelType.RERANK, config['rerank_model_id']
                )
            
            return AgnoServiceContext(
                chat_model=chat_model,
                embedding_model=embedding_model,
                rerank_model=rerank_model,
                model_adapter=self.model_adapter,
                chunk_size=config.get('chunk_size', 1024),
                chunk_overlap=config.get('chunk_overlap', 200),
                similarity_top_k=config.get('similarity_top_k', 5),
                response_mode=config.get('response_mode', 'compact')
            )
            
        except Exception as e:
            logger.error(f"从配置构建服务上下文失败: {str(e)}")
            return AgnoServiceContext(model_adapter=self.model_adapter)
    
    async def _get_system_config(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取系统配置"""
        try:
            from core.system_config.config_manager import SystemConfigManager
            from app.utils.core.database import get_db
            
            db = next(get_db())
            config_manager = SystemConfigManager(db)
            
            # 获取系统级配置
            config = {}
            config['chunk_size'] = await config_manager.get_config_value('agno.chunk_size', 1024)
            config['chunk_overlap'] = await config_manager.get_config_value('agno.chunk_overlap', 200)
            config['similarity_top_k'] = await config_manager.get_config_value('agno.similarity_top_k', 5)
            config['response_mode'] = await config_manager.get_config_value('agno.response_mode', 'compact')
            
            # 如果有用户ID，获取用户级配置
            if user_id:
                user_config = await config_manager.get_user_config(user_id, 'agno')
                config.update(user_config)
            
            return config
            
        except Exception as e:
            logger.error(f"获取系统配置失败: {str(e)}")
            return {}

# 全局服务上下文构建器
_global_context_builder: Optional[AgnoServiceContextBuilder] = None

def get_context_builder() -> AgnoServiceContextBuilder:
    """获取全局服务上下文构建器"""
    global _global_context_builder
    if _global_context_builder is None:
        _global_context_builder = AgnoServiceContextBuilder()
    return _global_context_builder

async def get_default_service_context(user_id: Optional[str] = None) -> AgnoServiceContext:
    """获取默认服务上下文
    
    Args:
        user_id: 用户ID
        
    Returns:
        AgnoServiceContext: 默认服务上下文
    """
    builder = get_context_builder()
    return await builder.build_from_system_config(user_id)

async def create_llm(model_id: Optional[str] = None, model_type: ModelType = ModelType.CHAT) -> DynamicAgnoLLM:
    """创建动态LLM实例
    
    Args:
        model_id: 模型ID
        model_type: 模型类型
        
    Returns:
        DynamicAgnoLLM: LLM实例
    """
    return DynamicAgnoLLM(model_id=model_id, model_type=model_type)

# 导出主要组件
__all__ = [
    "AgnoServiceContext",
    "AgnoLLMInterface", 
    "DynamicAgnoLLM",
    "AgnoServiceContextBuilder",
    "get_context_builder",
    "get_default_service_context",
    "create_llm"
] 