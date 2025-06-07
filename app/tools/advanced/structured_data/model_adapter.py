"""
模型适配器 - 为系统内置工具提供统一的模型获取接口
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from core.system_config import SystemConfigManager
from app.models.model_provider import ModelProvider, ModelInfo

logger = logging.getLogger(__name__)


class ModelAdapter:
    """模型适配器"""
    
    def __init__(self, db: Session = None):
        self.db = db or next(get_db())
        self.config_manager = SystemConfigManager(self.db)
        
    async def get_default_model_config(self) -> Dict[str, Any]:
        """获取默认模型配置"""
        try:
            # 先尝试系统配置
            default_model = await self.config_manager.get_config_value("llm.default_model", "")
            default_provider = await self.config_manager.get_config_value("llm.default_provider", "")
            
            if default_model and default_provider:
                config = await self._get_provider_credentials(default_provider)
                config.update({
                    "model_name": default_model,
                    "provider": default_provider,
                    "source": "system_config"
                })
                return config
            
            # 回退到AI模块配置
            ai_config = await self._get_ai_module_config()
            if ai_config:
                return ai_config
            
            # 最终回退
            return self._get_fallback_config()
            
        except Exception as e:
            logger.error(f"获取模型配置失败: {str(e)}")
            return self._get_fallback_config()
    
    async def _get_provider_credentials(self, provider: str) -> Dict[str, Any]:
        """获取提供商认证信息"""
        credentials = {}
        try:
            if provider == "openai":
                credentials.update({
                    "api_key": await self.config_manager.get_config_value("llm.openai.api_key", ""),
                    "api_base": await self.config_manager.get_config_value("llm.openai.api_base", "https://api.openai.com/v1")
                })
            elif provider == "zhipu":
                credentials.update({
                    "api_key": await self.config_manager.get_config_value("llm.zhipu.api_key", "")
                })
            elif provider == "anthropic":
                credentials.update({
                    "api_key": await self.config_manager.get_config_value("llm.anthropic.api_key", "")
                })
        except Exception as e:
            logger.error(f"获取{provider}认证信息失败: {str(e)}")
        
        return credentials
    
    async def _get_ai_module_config(self) -> Optional[Dict[str, Any]]:
        """从AI模块获取配置"""
        try:
            # 查找默认提供商
            provider = self.db.query(ModelProvider).filter(
                ModelProvider.is_default == True,
                ModelProvider.is_active == True
            ).first()
            
            if not provider:
                provider = self.db.query(ModelProvider).filter(
                    ModelProvider.is_active == True
                ).first()
            
            if not provider:
                return None
            
            # 查找默认模型
            model = self.db.query(ModelInfo).filter(
                ModelInfo.provider_id == provider.id,
                ModelInfo.is_default == True
            ).first()
            
            if not model:
                model = self.db.query(ModelInfo).filter(
                    ModelInfo.provider_id == provider.id
                ).first()
            
            if not model:
                return None
            
            return {
                "model_name": model.model_id,
                "provider": provider.provider_type,
                "api_key": provider.api_key,
                "api_base": provider.api_base,
                "source": "ai_module"
            }
            
        except Exception as e:
            logger.error(f"获取AI模块配置失败: {str(e)}")
            return None
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """回退配置"""
        return {
            "model_name": "gpt-3.5-turbo",
            "provider": "openai",
            "api_key": "",
            "api_base": "https://api.openai.com/v1",
            "source": "fallback"
        }
    
    async def create_llm_client(self, model_config: Dict[str, Any] = None):
        """创建LLM客户端"""
        if not model_config:
            model_config = await self.get_default_model_config()
        
        provider = model_config.get("provider")
        model_name = model_config.get("model_name")
        api_key = model_config.get("api_key")
        api_base = model_config.get("api_base")
        
        if not api_key and provider != "ollama":
            logger.warning(f"{provider}提供商的API密钥未配置")
            return None
        
        try:
            if provider == "openai":
                from llama_index.llms.openai import OpenAI
                return OpenAI(model=model_name, api_key=api_key, api_base=api_base)
            elif provider == "zhipu":
                from llama_index.llms.zhipuai import ZhipuAI
                return ZhipuAI(model=model_name, api_key=api_key)
            elif provider == "anthropic":
                from llama_index.llms.anthropic import Anthropic
                return Anthropic(model=model_name, api_key=api_key)
            else:
                logger.error(f"不支持的提供商: {provider}")
                return None
                
        except ImportError as e:
            logger.error(f"导入{provider}客户端失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"创建{provider}客户端失败: {str(e)}")
            return None


def get_model_adapter(db: Session = None) -> ModelAdapter:
    """获取模型适配器实例"""
    return ModelAdapter(db) 