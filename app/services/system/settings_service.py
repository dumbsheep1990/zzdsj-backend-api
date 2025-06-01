"""
系统设置服务

提供系统设置的存储、获取和更新功能，使用Redis作为存储后端。
支持用户自定义设置与系统默认设置的合并。
"""

import json
import logging
from typing import Dict, Any, Optional, TypeVar, Type, Generic, Union, cast
from pydantic import BaseModel

from app.config import settings
from app.utils.core.cache import get_redis_client

logger = logging.getLogger(__name__)

# 类型变量，用于泛型类型注解
T = TypeVar('T', bound=BaseModel)

class SettingsService(Generic[T]):
    """通用系统设置服务，支持任意Pydantic模型作为设置格式"""
    
    def __init__(self, model_cls: Type[T], settings_key: str, default_settings: Optional[Dict[str, Any]] = None):
        """
        初始化设置服务
        
        参数:
            model_cls: Pydantic模型类
            settings_key: Redis存储键
            default_settings: 默认设置值
        """
        self.model_cls = model_cls
        self.settings_key = settings_key
        self.default_settings = default_settings or {}
        self.redis_client = get_redis_client()
    
    async def get_settings(self) -> T:
        """获取当前设置，如果不存在则使用默认设置"""
        try:
            # 从Redis获取设置
            settings_data = await self.redis_client.get(self.settings_key)
            
            if settings_data:
                # 解析存储的设置
                current_settings = json.loads(settings_data)
                # 合并默认值与存储值
                merged_settings = self._merge_with_defaults(current_settings)
                return self.model_cls(**merged_settings)
            
            # 如果不存在，使用默认设置
            return self.model_cls(**self.default_settings)
        except Exception as e:
            logger.error(f"获取设置失败: {e}")
            # 出错时返回默认设置
            return self.model_cls(**self.default_settings)
    
    async def update_settings(self, new_settings: Union[Dict[str, Any], T]) -> T:
        """
        更新设置
        
        参数:
            new_settings: 新的设置值，可以是字典或Pydantic模型
            
        返回:
            更新后的设置
        """
        try:
            # 获取当前设置
            current = await self.get_settings()
            current_dict = current.dict()
            
            # 处理输入类型
            if isinstance(new_settings, BaseModel):
                new_settings_dict = new_settings.dict(exclude_unset=True)
            else:
                new_settings_dict = new_settings
            
            # 合并设置
            for key, value in new_settings_dict.items():
                if key in current_dict and isinstance(value, dict) and isinstance(current_dict[key], dict):
                    # 嵌套字典的深度合并
                    for k, v in value.items():
                        current_dict[key][k] = v
                else:
                    current_dict[key] = value
            
            # 验证并创建新模型
            updated_settings = self.model_cls(**current_dict)
            
            # 存储到Redis
            await self.redis_client.set(
                self.settings_key, 
                json.dumps(updated_settings.dict())
            )
            
            # 同步更新系统运行时配置
            self._sync_with_app_config(updated_settings)
            
            return updated_settings
        except Exception as e:
            logger.error(f"更新设置失败: {e}")
            # 出错时返回当前设置
            return await self.get_settings()
    
    def _merge_with_defaults(self, stored_settings: Dict[str, Any]) -> Dict[str, Any]:
        """合并存储的设置与默认设置"""
        result = self.default_settings.copy()
        
        # 递归合并
        def _deep_merge(target, source):
            for key, value in source.items():
                if key in target and isinstance(value, dict) and isinstance(target[key], dict):
                    _deep_merge(target[key], value)
                else:
                    target[key] = value
        
        _deep_merge(result, stored_settings)
        return result
    
    def _sync_with_app_config(self, updated_settings: T) -> None:
        """
        同步更新的设置到应用程序配置
        
        这个方法用于确保应用程序配置与用户设置保持同步，
        对于特定的设置，会更新对应的系统运行时配置。
        """
        # 这里根据模型类型和具体需求进行不同的同步逻辑
        pass


# 从schemas导入系统设置模型
from app.schemas.settings import SystemSettings, MetricsSettings

class SystemSettingsService(SettingsService[SystemSettings]):
    """系统设置服务，专门用于管理系统级别设置"""
    
    def __init__(self):
        """初始化系统设置服务"""
        # 从系统配置获取默认值
        default_settings = {
            "metrics": {
                "enabled": settings.metrics.enabled,
                "token_statistics": settings.metrics.token_statistics
            }
        }
        
        super().__init__(
            model_cls=SystemSettings,
            settings_key="system:settings",
            default_settings=default_settings
        )
    
    def _sync_with_app_config(self, updated_settings: SystemSettings) -> None:
        """同步系统设置到应用配置"""
        # 更新指标统计设置
        if updated_settings.metrics:
            # 运行时更新系统配置
            settings.metrics.enabled = updated_settings.metrics.enabled
            settings.metrics.token_statistics = updated_settings.metrics.token_statistics
            
            logger.info(f"系统指标统计设置已更新: enabled={settings.metrics.enabled}, "
                      f"token_statistics={settings.metrics.token_statistics}")


# 全局系统设置服务实例
_system_settings_service = None

def get_system_settings_service() -> SystemSettingsService:
    """获取系统设置服务实例"""
    global _system_settings_service
    if _system_settings_service is None:
        _system_settings_service = SystemSettingsService()
    return _system_settings_service
