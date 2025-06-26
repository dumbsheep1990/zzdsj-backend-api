"""
Agno嵌入模块：动态配置版本
基于系统配置和用户配置动态创建和管理Agno嵌入模型，
支持多种嵌入提供商和向量数据库集成
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Type
from abc import ABC, abstractmethod

from app.frameworks.agno.model_config_adapter import (
    get_model_adapter, 
    ModelType, 
    ModelConfiguration,
    SupportedProvider
)
from app.config import settings

# 动态导入Agno嵌入组件
try:
    from agno.embedder.openai import OpenAIEmbedder
    from agno.embedder.cohere import CohereEmbedder
    from agno.embedder.google import GeminiEmbedder
    from agno.embedder.azure_openai import AzureOpenAIEmbedder
    from agno.embedder.huggingface import HuggingfaceCustomEmbedder
    from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
    from agno.embedder.fastembed import FastEmbedEmbedder
    from agno.embedder.mistral import MistralEmbedder
    from agno.embedder.voyageai import VoyageAIEmbedder
    from agno.embedder.ollama import OllamaEmbedder
    AGNO_EMBEDDERS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Agno embedders not available: {e}")
    AGNO_EMBEDDERS_AVAILABLE = False
    # 创建占位符类
    OpenAIEmbedder = None
    CohereEmbedder = None
    GeminiEmbedder = None

logger = logging.getLogger(__name__)

class AgnoEmbedderInterface(ABC):
    """Agno嵌入器统一接口"""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """嵌入单个文本"""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文本"""
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """获取嵌入维度"""
        pass

class DynamicAgnoEmbedder(AgnoEmbedderInterface):
    """动态Agno嵌入器 - 基于配置创建对应的嵌入器"""
    
    def __init__(self, model_config: Optional[ModelConfiguration] = None):
        """
        初始化动态嵌入器
        
        Args:
            model_config: 模型配置，如果为None则使用系统默认配置
        """
        self.model_config = model_config
        self._embedder_instance = None
        self._model_adapter = get_model_adapter()
        
    async def _get_embedder_instance(self):
        """获取嵌入器实例"""
        if self._embedder_instance is None:
            await self._create_embedder_instance()
        return self._embedder_instance
    
    async def _create_embedder_instance(self):
        """创建嵌入器实例"""
        try:
            # 获取模型配置
            if self.model_config is None:
                self.model_config = await self._model_adapter.get_default_model_by_type(ModelType.EMBEDDING)
            
            if not self.model_config:
                raise RuntimeError("无法获取嵌入模型配置")
            
            # 根据提供商创建对应的嵌入器
            self._embedder_instance = await self._create_embedder_by_provider(self.model_config)
            
            if not self._embedder_instance:
                raise RuntimeError(f"无法创建 {self.model_config.provider.value} 嵌入器")
                
            logger.info(f"成功创建 {self.model_config.provider.value} 嵌入器: {self.model_config.model_name}")
            
        except Exception as e:
            logger.error(f"创建嵌入器失败: {str(e)}")
            # 创建回退嵌入器
            await self._create_fallback_embedder()
    
    async def _create_embedder_by_provider(self, config: ModelConfiguration):
        """根据提供商创建嵌入器"""
        if not AGNO_EMBEDDERS_AVAILABLE:
            logger.warning("Agno嵌入器不可用，使用回退实现")
            return None
        
        provider = config.provider
        model_id = config.model_id
        
        try:
            if provider == SupportedProvider.OPENAI:
                return OpenAIEmbedder(
                    id=model_id,
                    api_key=config.api_key or settings.OPENAI_API_KEY,
                    api_base=config.api_base,
                    dimensions=config.config.get('dimensions')
                )
            
            elif provider == SupportedProvider.COHERE:
                return CohereEmbedder(
                    id=model_id,
                    api_key=config.api_key
                )
            
            elif provider == SupportedProvider.ANTHROPIC:
                # Anthropic主要用于聊天，这里可能需要其他嵌入提供商
                logger.warning("Anthropic不直接提供嵌入服务，尝试使用OpenAI作为嵌入器")
                return OpenAIEmbedder(
                    id="text-embedding-3-small",
                    api_key=settings.OPENAI_API_KEY
                )
            
            elif provider in [SupportedProvider.ZHIPU, SupportedProvider.GLM]:
                return GeminiEmbedder(
                    id=model_id,
                    api_key=config.api_key
                )
            
            elif provider == SupportedProvider.OLLAMA:
                return OllamaEmbedder(
                    id=model_id,
                    dimensions=config.config.get('dimensions', 1024)
                )
            
            elif provider == SupportedProvider.TOGETHER:
                # Together AI通常使用Sentence Transformers
                return SentenceTransformerEmbedder(
                    id=model_id or "all-MiniLM-L6-v2"
                )
            
            else:
                # 默认使用FastEmbed作为通用嵌入器
                logger.info(f"使用FastEmbed作为 {provider.value} 的默认嵌入器")
                return FastEmbedEmbedder(
                    id=model_id or "BAAI/bge-small-en-v1.5"
                )
                
        except Exception as e:
            logger.error(f"创建 {provider.value} 嵌入器失败: {str(e)}")
            return None
    
    async def _create_fallback_embedder(self):
        """创建回退嵌入器"""
        try:
            # 尝试使用SentenceTransformer作为回退
            if SentenceTransformerEmbedder:
                self._embedder_instance = SentenceTransformerEmbedder(id="all-MiniLM-L6-v2")
                logger.warning("使用SentenceTransformer作为回退嵌入器")
            else:
                # 最后的回退：使用简单的本地嵌入器
                self._embedder_instance = LocalFallbackEmbedder()
                logger.warning("使用本地回退嵌入器")
        except Exception as e:
            logger.error(f"创建回退嵌入器失败: {str(e)}")
            self._embedder_instance = LocalFallbackEmbedder()
    
    async def embed_text(self, text: str) -> List[float]:
        """嵌入单个文本"""
        embedder = await self._get_embedder_instance()
        try:
            if hasattr(embedder, 'aget_embedding'):
                # 异步方法
                return await embedder.aget_embedding(text)
            elif hasattr(embedder, 'get_embedding'):
                # 同步方法，在线程池中执行
                return await asyncio.to_thread(embedder.get_embedding, text)
            else:
                # 回退方法
                return await embedder.embed_text(text)
        except Exception as e:
            logger.error(f"文本嵌入失败: {str(e)}")
            # 返回零向量作为回退
            return [0.0] * self.get_embedding_dimension()
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文本"""
        embedder = await self._get_embedder_instance()
        try:
            if hasattr(embedder, 'aget_embeddings'):
                # 批量异步方法
                return await embedder.aget_embeddings(texts)
            elif hasattr(embedder, 'get_embeddings'):
                # 批量同步方法
                return await asyncio.to_thread(embedder.get_embeddings, texts)
            else:
                # 逐个处理
                embeddings = []
                for text in texts:
                    embedding = await self.embed_text(text)
                    embeddings.append(embedding)
                return embeddings
        except Exception as e:
            logger.error(f"批量文本嵌入失败: {str(e)}")
            # 返回零向量列表作为回退
            dimension = self.get_embedding_dimension()
            return [[0.0] * dimension for _ in texts]
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入维度"""
        if self.model_config:
            # 从配置获取维度
            return self.model_config.config.get('dimensions', 1536)
        
        # 根据模型类型返回标准维度
        if self.model_config and self.model_config.model_id:
            model_id = self.model_config.model_id.lower()
            if "ada" in model_id:
                return 1536
            elif "bge" in model_id:
                return 768
            elif "sentence" in model_id:
                return 384
        
        return 1536  # 默认维度

class LocalFallbackEmbedder(AgnoEmbedderInterface):
    """本地回退嵌入器 - 当所有其他嵌入器都失败时使用"""
    
    def __init__(self):
        self.dimension = 768
        logger.warning("使用本地回退嵌入器，这只应该在开发或测试环境中使用")
    
    async def embed_text(self, text: str) -> List[float]:
        """使用简单的哈希算法生成确定性嵌入"""
        import hashlib
        import numpy as np
        
        # 使用文本的哈希生成种子
        hash_obj = hashlib.sha256(text.encode())
        seed = int.from_bytes(hash_obj.digest()[:4], byteorder='big')
        
        # 使用种子生成确定性的随机向量
        np.random.seed(seed % (2**32))
        embedding = np.random.normal(0, 1, self.dimension)
        
        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.tolist()
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入"""
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """获取维度"""
        return self.dimension

# 工厂函数

async def create_embedder(
    model_id: Optional[str] = None,
    provider: Optional[SupportedProvider] = None,
    user_id: Optional[str] = None
) -> DynamicAgnoEmbedder:
    """
    创建嵌入器实例
    
    Args:
        model_id: 指定的模型ID
        provider: 指定的提供商
        user_id: 用户ID，用于获取用户特定配置
        
    Returns:
        DynamicAgnoEmbedder: 嵌入器实例
    """
    model_adapter = get_model_adapter()
    
    if model_id:
        # 使用指定的模型ID
        model_config = await model_adapter.get_model_configuration(model_id)
    elif provider:
        # 使用指定提供商的默认嵌入模型
        models = await model_adapter.get_models_by_type(ModelType.EMBEDDING, provider)
        model_config = models[0] if models else None
    else:
        # 使用系统默认嵌入模型
        model_config = await model_adapter.get_default_model_by_type(ModelType.EMBEDDING)
    
    return DynamicAgnoEmbedder(model_config)

async def get_default_embedder() -> DynamicAgnoEmbedder:
    """获取默认嵌入器"""
    return await create_embedder()

async def get_user_embedder(user_id: str) -> DynamicAgnoEmbedder:
    """获取用户特定的嵌入器"""
    # TODO: 实现用户特定的嵌入器配置
    return await create_embedder(user_id=user_id)

# 兼容性函数（保持原有接口）
async def get_embedding_model(
    model_name: Optional[str] = None, 
    api_key: Optional[str] = None
) -> DynamicAgnoEmbedder:
    """
    获取嵌入模型（兼容原接口）
    
    Args:
        model_name: 模型名称
        api_key: API密钥
        
    Returns:
        DynamicAgnoEmbedder: 嵌入器实例
    """
    return await create_embedder(model_id=model_name)

class EmbeddingModel(DynamicAgnoEmbedder):
    """兼容性类 - 保持原有接口"""
    
    def __init__(self, model_name: str = "text-embedding-ada-002", api_key: Optional[str] = None):
        """兼容原有初始化方式"""
        # 创建临时配置
        from app.frameworks.agno.model_config_adapter import ModelConfiguration, SupportedProvider, ModelType
        
        temp_config = ModelConfiguration(
            model_id=model_name,
            model_name=model_name,
            provider=SupportedProvider.OPENAI,  # 默认OpenAI
            model_type=ModelType.EMBEDDING,
            api_key=api_key
        )
        
        super().__init__(temp_config)
