"""
Agno框架动态配置模块
从ZZDSJ系统配置动态获取Agno相关配置，支持用户级别和系统级别配置
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class AgnoConfigSection(str, Enum):
    """Agno配置分类"""
    MODELS = "agno.models"
    TOOLS = "agno.tools"
    MEMORY = "agno.memory"
    STORAGE = "agno.storage"
    PERFORMANCE = "agno.performance"
    FEATURES = "agno.features"

@dataclass
class AgnoModelConfig:
    """Agno模型配置"""
    default_chat_model: Optional[str] = None
    default_embedding_model: Optional[str] = None
    default_rerank_model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3

@dataclass
class AgnoToolConfig:
    """Agno工具配置"""
    enabled_tools: List[str] = field(default_factory=list)
    tool_timeout: int = 30
    max_tool_calls: int = 10
    allow_dangerous_tools: bool = False
    tool_call_logging: bool = True

@dataclass
class AgnoMemoryConfig:
    """Agno内存配置"""
    memory_type: str = "simple"  # simple, persistent, redis
    max_memory_size: int = 1000
    memory_ttl: int = 3600  # 秒
    persist_to_db: bool = False
    redis_url: Optional[str] = None

@dataclass
class AgnoStorageConfig:
    """Agno存储配置"""
    storage_type: str = "sqlite"  # sqlite, postgresql, memory
    storage_path: Optional[str] = None
    connection_string: Optional[str] = None
    table_prefix: str = "agno_"
    auto_create_tables: bool = True

@dataclass
class AgnoPerformanceConfig:
    """Agno性能配置"""
    chunk_size: int = 1024
    chunk_overlap: int = 200
    similarity_top_k: int = 5
    response_mode: str = "compact"
    enable_streaming: bool = True
    concurrent_requests: int = 10

@dataclass
class AgnoFeatureConfig:
    """Agno功能配置"""
    show_tool_calls: bool = True
    markdown: bool = True
    reasoning_enabled: bool = True
    debug_mode: bool = False
    logging_level: str = "INFO"

@dataclass
class DynamicAgnoConfig:
    """动态Agno配置主类"""
    models: AgnoModelConfig = field(default_factory=AgnoModelConfig)
    tools: AgnoToolConfig = field(default_factory=AgnoToolConfig)
    memory: AgnoMemoryConfig = field(default_factory=AgnoMemoryConfig)
    storage: AgnoStorageConfig = field(default_factory=AgnoStorageConfig)
    performance: AgnoPerformanceConfig = field(default_factory=AgnoPerformanceConfig)
    features: AgnoFeatureConfig = field(default_factory=AgnoFeatureConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "models": self.models.__dict__,
            "tools": self.tools.__dict__,
            "memory": self.memory.__dict__,
            "storage": self.storage.__dict__,
            "performance": self.performance.__dict__,
            "features": self.features.__dict__
        }

class DynamicAgnoConfigManager:
    """动态Agno配置管理器"""
    
    def __init__(self, db_session=None):
        """初始化配置管理器"""
        from app.utils.core.database import get_db
        self.db = db_session or next(get_db())
        self._config_cache: Dict[str, DynamicAgnoConfig] = {}
        self._system_config_cache: Optional[DynamicAgnoConfig] = None
        self._cache_ttl = 300  # 5分钟缓存
        self._last_cache_update = 0
    
    async def get_system_config(self) -> DynamicAgnoConfig:
        """获取系统级Agno配置"""
        try:
            from core.system_config.config_manager import SystemConfigManager
            
            config_manager = SystemConfigManager(self.db)
            
            # 获取模型配置
            models_config = AgnoModelConfig(
                default_chat_model=await config_manager.get_config_value(
                    "agno.models.default_chat_model", None
                ),
                default_embedding_model=await config_manager.get_config_value(
                    "agno.models.default_embedding_model", None
                ),
                default_rerank_model=await config_manager.get_config_value(
                    "agno.models.default_rerank_model", None
                ),
                temperature=await config_manager.get_config_value(
                    "agno.models.temperature", 0.7
                ),
                max_tokens=await config_manager.get_config_value(
                    "agno.models.max_tokens", 4096
                ),
                timeout=await config_manager.get_config_value(
                    "agno.models.timeout", 60
                ),
                max_retries=await config_manager.get_config_value(
                    "agno.models.max_retries", 3
                )
            )
            
            # 获取工具配置
            enabled_tools_str = await config_manager.get_config_value(
                "agno.tools.enabled_tools", "[]"
            )
            try:
                import json
                enabled_tools = json.loads(enabled_tools_str) if enabled_tools_str else []
            except:
                enabled_tools = []
                
            tools_config = AgnoToolConfig(
                enabled_tools=enabled_tools,
                tool_timeout=await config_manager.get_config_value(
                    "agno.tools.tool_timeout", 30
                ),
                max_tool_calls=await config_manager.get_config_value(
                    "agno.tools.max_tool_calls", 10
                ),
                allow_dangerous_tools=await config_manager.get_config_value(
                    "agno.tools.allow_dangerous_tools", False
                ),
                tool_call_logging=await config_manager.get_config_value(
                    "agno.tools.tool_call_logging", True
                )
            )
            
            # 获取内存配置
            memory_config = AgnoMemoryConfig(
                memory_type=await config_manager.get_config_value(
                    "agno.memory.memory_type", "simple"
                ),
                max_memory_size=await config_manager.get_config_value(
                    "agno.memory.max_memory_size", 1000
                ),
                memory_ttl=await config_manager.get_config_value(
                    "agno.memory.memory_ttl", 3600
                ),
                persist_to_db=await config_manager.get_config_value(
                    "agno.memory.persist_to_db", False
                ),
                redis_url=await config_manager.get_config_value(
                    "agno.memory.redis_url", None
                )
            )
            
            # 获取存储配置
            storage_config = AgnoStorageConfig(
                storage_type=await config_manager.get_config_value(
                    "agno.storage.storage_type", "sqlite"
                ),
                storage_path=await config_manager.get_config_value(
                    "agno.storage.storage_path", None
                ),
                connection_string=await config_manager.get_config_value(
                    "agno.storage.connection_string", None
                ),
                table_prefix=await config_manager.get_config_value(
                    "agno.storage.table_prefix", "agno_"
                ),
                auto_create_tables=await config_manager.get_config_value(
                    "agno.storage.auto_create_tables", True
                )
            )
            
            # 获取性能配置
            performance_config = AgnoPerformanceConfig(
                chunk_size=await config_manager.get_config_value(
                    "agno.performance.chunk_size", 1024
                ),
                chunk_overlap=await config_manager.get_config_value(
                    "agno.performance.chunk_overlap", 200
                ),
                similarity_top_k=await config_manager.get_config_value(
                    "agno.performance.similarity_top_k", 5
                ),
                response_mode=await config_manager.get_config_value(
                    "agno.performance.response_mode", "compact"
                ),
                enable_streaming=await config_manager.get_config_value(
                    "agno.performance.enable_streaming", True
                ),
                concurrent_requests=await config_manager.get_config_value(
                    "agno.performance.concurrent_requests", 10
                )
            )
            
            # 获取功能配置
            features_config = AgnoFeatureConfig(
                show_tool_calls=await config_manager.get_config_value(
                    "agno.features.show_tool_calls", True
                ),
                markdown=await config_manager.get_config_value(
                    "agno.features.markdown", True
                ),
                reasoning_enabled=await config_manager.get_config_value(
                    "agno.features.reasoning_enabled", True
                ),
                debug_mode=await config_manager.get_config_value(
                    "agno.features.debug_mode", False
                ),
                logging_level=await config_manager.get_config_value(
                    "agno.features.logging_level", "INFO"
                )
            )
            
            # 创建完整配置
            config = DynamicAgnoConfig(
                models=models_config,
                tools=tools_config,
                memory=memory_config,
                storage=storage_config,
                performance=performance_config,
                features=features_config
            )
            
            # 缓存系统配置
            self._system_config_cache = config
            
            logger.info("成功加载系统级Agno配置")
            return config
            
        except Exception as e:
            logger.error(f"获取系统级Agno配置失败: {str(e)}")
            # 返回默认配置
            return DynamicAgnoConfig()
    
    async def get_user_config(self, user_id: str) -> DynamicAgnoConfig:
        """获取用户级Agno配置"""
        try:
            # 检查缓存
            if user_id in self._config_cache:
                return self._config_cache[user_id]
            
            # 获取系统配置作为基础
            system_config = await self.get_system_config()
            
            # 获取用户特定配置
            from core.system_config.config_manager import SystemConfigManager
            config_manager = SystemConfigManager(self.db)
            
            user_overrides = await config_manager.get_user_config(user_id, "agno")
            
            # 合并配置
            user_config = self._merge_configs(system_config, user_overrides)
            
            # 缓存用户配置
            self._config_cache[user_id] = user_config
            
            logger.info(f"成功加载用户 {user_id} 的Agno配置")
            return user_config
            
        except Exception as e:
            logger.error(f"获取用户 {user_id} 的Agno配置失败: {str(e)}")
            # 返回系统配置
            return await self.get_system_config()
    
    def _merge_configs(self, base_config: DynamicAgnoConfig, overrides: Dict[str, Any]) -> DynamicAgnoConfig:
        """合并配置"""
        try:
            # 深拷贝基础配置
            import copy
            merged_config = copy.deepcopy(base_config)
            
            # 应用覆盖配置
            for key, value in overrides.items():
                self._apply_config_override(merged_config, key, value)
            
            return merged_config
            
        except Exception as e:
            logger.error(f"合并配置失败: {str(e)}")
            return base_config
    
    def _apply_config_override(self, config: DynamicAgnoConfig, key: str, value: Any):
        """应用配置覆盖"""
        try:
            # 解析嵌套键 (例如: "models.temperature")
            parts = key.split('.')
            
            if len(parts) == 2:
                section, field = parts
                if hasattr(config, section):
                    section_obj = getattr(config, section)
                    if hasattr(section_obj, field):
                        setattr(section_obj, field, value)
                        
        except Exception as e:
            logger.warning(f"应用配置覆盖失败 {key}={value}: {str(e)}")
    
    async def update_user_config(self, user_id: str, config_updates: Dict[str, Any]) -> bool:
        """更新用户配置"""
        try:
            from core.system_config.config_manager import SystemConfigManager
            config_manager = SystemConfigManager(self.db)
            
            # 更新配置
            for key, value in config_updates.items():
                await config_manager.set_user_config(user_id, f"agno.{key}", value)
            
            # 清除缓存
            if user_id in self._config_cache:
                del self._config_cache[user_id]
            
            logger.info(f"成功更新用户 {user_id} 的Agno配置")
            return True
            
        except Exception as e:
            logger.error(f"更新用户 {user_id} 的Agno配置失败: {str(e)}")
            return False
    
    async def reset_user_config(self, user_id: str) -> bool:
        """重置用户配置为系统默认"""
        try:
            from core.system_config.config_manager import SystemConfigManager
            config_manager = SystemConfigManager(self.db)
            
            # 删除用户的Agno配置
            await config_manager.delete_user_config(user_id, "agno")
            
            # 清除缓存
            if user_id in self._config_cache:
                del self._config_cache[user_id]
            
            logger.info(f"成功重置用户 {user_id} 的Agno配置")
            return True
            
        except Exception as e:
            logger.error(f"重置用户 {user_id} 的Agno配置失败: {str(e)}")
            return False
    
    def clear_cache(self):
        """清除配置缓存"""
        self._config_cache.clear()
        self._system_config_cache = None
        logger.info("Agno配置缓存已清除")

# 全局配置管理器实例
_global_config_manager: Optional[DynamicAgnoConfigManager] = None

def get_config_manager() -> DynamicAgnoConfigManager:
    """获取全局配置管理器"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = DynamicAgnoConfigManager()
    return _global_config_manager

async def get_system_agno_config() -> DynamicAgnoConfig:
    """获取系统级Agno配置"""
    manager = get_config_manager()
    return await manager.get_system_config()

async def get_user_agno_config(user_id: str) -> DynamicAgnoConfig:
    """获取用户级Agno配置"""
    manager = get_config_manager()
    return await manager.get_user_config(user_id)

# 导出主要组件
__all__ = [
    "DynamicAgnoConfig",
    "AgnoModelConfig",
    "AgnoToolConfig", 
    "AgnoMemoryConfig",
    "AgnoStorageConfig",
    "AgnoPerformanceConfig",
    "AgnoFeatureConfig",
    "DynamicAgnoConfigManager",
    "get_config_manager",
    "get_system_agno_config",
    "get_user_agno_config"
]
