"""
Agno框架模型配置适配器
将ZZDSJ系统现有的模型配置系统集成到Agno框架中，支持多厂商和动态配置
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum

try:
    from agno import Agent, Team, OpenAIChat, AnthropicChat, Model
    from agno.models.base import ModelConfig
    AGNO_AVAILABLE = True
except ImportError:
    # 降级处理，避免在没有Agno的环境中崩溃
    AGNO_AVAILABLE = False
    Agent = object
    Team = object
    OpenAIChat = object
    AnthropicChat = object
    Model = object
    ModelConfig = object

from sqlalchemy.orm import Session
from app.models.model_provider import ModelProvider
from app.models.model_info import ModelInfo
from app.services.models.provider_service import ModelProviderService
from core.model_manager.manager import get_model_client
from app.utils.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)


class SupportedProvider(str, Enum):
    """支持的模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    BAIDU = "baidu"
    QWEN = "qwen"
    OLLAMA = "ollama"
    VLLM = "vllm"
    MINIMAX = "minimax"
    BAICHUAN = "baichuan"
    GLM = "glm"
    TOGETHER = "together"
    DASHSCOPE = "dashscope"
    COHERE = "cohere"
    LOCAL_RERANK = "local_rerank"


class ModelType(str, Enum):
    """模型类型枚举"""
    CHAT = "chat"
    EMBEDDING = "embedding"
    RERANK = "rerank"
    VISION = "vision"
    COMPLETION = "completion"


@dataclass
class ModelConfiguration:
    """模型配置数据类"""
    model_id: str
    model_name: str
    provider: SupportedProvider
    model_type: ModelType  # 新增模型类型
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    context_window: int = 8192
    is_default: bool = False
    is_enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "provider": self.provider.value,
            "model_type": self.model_type.value,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "api_version": self.api_version,
            "context_window": self.context_window,
            "is_default": self.is_default,
            "is_enabled": self.is_enabled,
            "config": self.config,
            "description": self.description
        }


class ZZDSJAgnoModelAdapter:
    """ZZDSJ Agno模型配置适配器 - 支持完整的三类别模型管理"""
    
    def __init__(self, db: Optional[Session] = None):
        """初始化适配器"""
        self.db = db or next(get_db())
        self.provider_service = ModelProviderService(self.db)
        self._model_cache: Dict[str, Model] = {}
        self._config_cache: Dict[str, ModelConfiguration] = {}
        self._last_cache_update = 0
        self.cache_ttl = 300  # 5分钟缓存
        
        logger.info("ZZDSJ Agno模型配置适配器已初始化")

    async def get_models_by_type(self, model_type: ModelType, provider: Optional[SupportedProvider] = None) -> List[ModelConfiguration]:
        """按类型获取模型配置列表"""
        try:
            # 从数据库获取模型提供商
            providers = await self.provider_service.get_active_providers()
            
            models = []
            for provider_obj in providers:
                # 如果指定了提供商，过滤
                if provider and provider_obj.provider_type != provider.value:
                    continue
                    
                # 解析模型列表
                provider_models = self._parse_provider_models(provider_obj)
                
                # 按类型筛选
                for model_config in provider_models:
                    if model_config.model_type == model_type:
                        models.append(model_config)
            
            logger.info(f"获取 {model_type.value} 类型模型 {len(models)} 个")
            return models
            
        except Exception as e:
            logger.error(f"获取 {model_type.value} 类型模型失败: {str(e)}")
            return []

    async def get_default_model_by_type(self, model_type: ModelType) -> Optional[ModelConfiguration]:
        """获取指定类型的默认模型配置"""
        try:
            # 优先从系统配置获取
            from core.system_config.config_manager import SystemConfigManager
            config_manager = SystemConfigManager(self.db)
            
            default_model_key = f"llm.default_model.{model_type.value}"
            default_model_id = await config_manager.get_config_value(default_model_key, "")
            
            if default_model_id:
                # 查找指定的默认模型
                models = await self.get_models_by_type(model_type)
                for model in models:
                    if model.model_id == default_model_id and model.is_enabled:
                        logger.info(f"使用系统配置的默认 {model_type.value} 模型: {model.model_name}")
                        return model
            
            # 如果没有配置，查找第一个可用的默认模型
            models = await self.get_models_by_type(model_type)
            for model in models:
                if model.is_default and model.is_enabled:
                    logger.info(f"使用提供商默认的 {model_type.value} 模型: {model.model_name}")
                    return model
            
            # 最后兜底，返回第一个可用模型
            if models:
                first_available = models[0]
                logger.warning(f"未找到默认 {model_type.value} 模型，使用第一个可用模型: {first_available.model_name}")
                return first_available
            
            logger.error(f"未找到任何可用的 {model_type.value} 模型")
            return None
            
        except Exception as e:
            logger.error(f"获取默认 {model_type.value} 模型失败: {str(e)}")
            return None

    async def create_agno_model_by_type(self, model_type: ModelType, model_id: Optional[str] = None) -> Optional[Model]:
        """根据类型创建Agno模型实例"""
        if not AGNO_AVAILABLE:
            logger.warning("Agno框架不可用")
            return None
            
        try:
            # 如果指定模型ID，直接获取
            if model_id:
                model_config = await self.get_model_configuration(model_id)
            else:
                # 否则获取默认模型
                model_config = await self.get_default_model_by_type(model_type)
            
            if not model_config:
                logger.error(f"未找到 {model_type.value} 模型配置")
                return None
            
            # 检查缓存
            cache_key = f"{model_config.provider.value}:{model_config.model_id}:{model_type.value}"
            if cache_key in self._model_cache:
                return self._model_cache[cache_key]
            
            # 创建Agno模型实例
            model_instance = None
            
            if model_config.provider == SupportedProvider.OPENAI:
                model_instance = OpenAIChat(
                    id=model_config.model_id,
                    api_key=model_config.api_key or self._get_env_var("OPENAI_API_KEY"),
                    base_url=model_config.api_base,
                    max_tokens=model_config.config.get("max_tokens", 4096),
                    temperature=model_config.config.get("temperature", 0.7)
                )
            elif model_config.provider == SupportedProvider.ANTHROPIC:
                model_instance = AnthropicChat(
                    id=model_config.model_id,
                    api_key=model_config.api_key or self._get_env_var("ANTHROPIC_API_KEY"),
                    max_tokens=model_config.config.get("max_tokens", 4096),
                    temperature=model_config.config.get("temperature", 0.7)
                )
            # 其他提供商的实现...
            
            if model_instance:
                self._model_cache[cache_key] = model_instance
                logger.info(f"创建 {model_type.value} 模型实例: {model_config.model_name}")
                return model_instance
            
            logger.warning(f"暂不支持 {model_config.provider.value} 提供商的Agno集成")
            return None
            
        except Exception as e:
            logger.error(f"创建 {model_type.value} Agno模型失败: {str(e)}")
            return None

    def _parse_provider_models(self, provider_obj) -> List[ModelConfiguration]:
        """解析提供商的模型配置"""
        models = []
        
        try:
            import json
            if provider_obj.models:
                models_data = json.loads(provider_obj.models) if isinstance(provider_obj.models, str) else provider_obj.models
                
                for model_data in models_data:
                    try:
                        # 确定模型类型
                        model_type_str = model_data.get("type", "chat")
                        model_type = ModelType(model_type_str) if model_type_str in [t.value for t in ModelType] else ModelType.CHAT
                        
                        # 确定提供商
                        provider_type = SupportedProvider(provider_obj.provider_type) if provider_obj.provider_type in [p.value for p in SupportedProvider] else SupportedProvider.OPENAI
                        
                        model_config = ModelConfiguration(
                            model_id=model_data.get("id", ""),
                            model_name=model_data.get("name", ""),
                            provider=provider_type,
                            model_type=model_type,
                            api_key=provider_obj.api_key,
                            api_base=provider_obj.api_base,
                            api_version=provider_obj.api_version,
                            context_window=model_data.get("context_window", 8192),
                            is_default=model_data.get("is_default", False),
                            is_enabled=provider_obj.is_enabled,
                            config=model_data.get("config", {}),
                            description=model_data.get("description", "")
                        )
                        
                        models.append(model_config)
                        
                    except ValueError as e:
                        logger.warning(f"跳过不支持的模型配置: {model_data}, 错误: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"解析提供商 {provider_obj.name} 的模型配置失败: {str(e)}")
        
        return models

    async def get_model_configuration(self, model_id: str) -> Optional[ModelConfiguration]:
        """获取模型配置"""
        # 检查缓存
        if model_id in self._config_cache:
            return self._config_cache[model_id]
        
        try:
            db = self.db or next(get_db())
            
            # 查找模型
            model = db.query(ModelInfo).filter(
                ModelInfo.model_id == model_id
            ).first()
            
            if not model:
                logger.warning(f"未找到模型: {model_id}")
                return None
            
            # 查找对应的提供商
            provider = db.query(ModelProvider).filter(
                ModelProvider.id == model.provider_id
            ).first()
            
            if not provider:
                logger.warning(f"模型 {model_id} 对应的提供商不存在")
                return None
            
            config = ModelConfiguration(
                model_id=model.model_id,
                model_name=model.model_name,
                provider=SupportedProvider(provider.provider_type),
                model_type=ModelType.CHAT,  # 假设默认是聊天模型
                api_key=provider.api_key,
                api_base=provider.api_base,
                api_version=provider.api_version,
                context_window=model.context_window,
                is_default=model.is_default,
                is_enabled=provider.is_enabled,
                config=provider.config
            )
            
            # 缓存配置
            self._config_cache[model_id] = config
            return config
            
        except Exception as e:
            logger.error(f"获取模型 {model_id} 配置失败: {str(e)}")
            return None

    def _get_env_var(self, var_name: str) -> Optional[str]:
        """获取环境变量"""
        return getattr(settings, f"{var_name.upper()}_API_KEY", None)


# 全局模型适配器实例
_global_adapter: Optional[ZZDSJAgnoModelAdapter] = None


def get_model_adapter() -> ZZDSJAgnoModelAdapter:
    """获取全局模型适配器实例
    
    Returns:
        ZZDSJAgnoModelAdapter: 模型适配器实例
    """
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = ZZDSJAgnoModelAdapter()
    return _global_adapter


async def create_chat_model(model_id: Optional[str] = None) -> Optional[Model]:
    """创建对话模型"""
    adapter = get_model_adapter()
    return await adapter.create_agno_model_by_type(ModelType.CHAT, model_id)


async def create_embedding_model(model_id: Optional[str] = None) -> Optional[Model]:
    """创建嵌入模型（注意：Agno主要支持对话模型，嵌入模型可能需要其他处理）"""
    adapter = get_model_adapter()
    return await adapter.create_agno_model_by_type(ModelType.EMBEDDING, model_id)


async def create_rerank_model(model_id: Optional[str] = None) -> Optional[Model]:
    """创建重排序模型（注意：Agno主要支持对话模型，重排序模型可能需要其他处理）"""
    adapter = get_model_adapter()
    return await adapter.create_agno_model_by_type(ModelType.RERANK, model_id)


async def get_available_models_by_type(model_type: ModelType) -> List[ModelConfiguration]:
    """获取指定类型的可用模型列表"""
    adapter = get_model_adapter()
    return await adapter.get_models_by_type(model_type)