"""
配置管理器模块
提供YAML配置的加载、解析和管理功能
"""

import os
import yaml
from typing import Any, Dict, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """YAML配置管理器，用于应用程序设置"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        使用可选的配置路径初始化
        
        Args:
            config_path: 配置文件路径，默认使用项目根目录中的config.yaml
        """
        self._config = {}
        self._config_path = self._determine_config_path(config_path)
        self._load_config()
    
    def _determine_config_path(self, config_path: Optional[str]) -> str:
        """确定配置文件路径"""
        if config_path:
            return config_path
        
        # 默认使用项目根目录中的config.yaml
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
            'config.yaml'
        )
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 加载基础配置
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"已加载配置文件: {self._config_path}")
            else:
                logger.warning(f"配置文件不存在: {self._config_path}")
                self._config = {}
            
            # 加载环境特定配置
            self._load_environment_config()
            
            # 允许环境变量覆盖配置
            self._override_from_env()
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            self._config = {}
    
    def _load_environment_config(self):
        """加载环境特定的配置"""
        env = os.getenv("APP_ENV", "development")
        env_config_path = os.path.join(
            os.path.dirname(self._config_path), 
            f'config.{env}.yaml'
        )
        
        if os.path.exists(env_config_path):
            try:
                with open(env_config_path, 'r', encoding='utf-8') as f:
                    env_config = yaml.safe_load(f) or {}
                    self._deep_update(self._config, env_config)
                logger.info(f"已加载环境配置: {env_config_path}")
            except Exception as e:
                logger.error(f"加载环境配置失败: {str(e)}")
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """递归地用另一个字典更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _build_env_mappings(self) -> Dict[str, list]:
        """构建环境变量到配置路径的映射"""
        # 基础映射 - 核心配置
        base_mappings = {
            # 数据库配置
            "DATABASE_URL": ["database", "url"],
            "DB_POOL_SIZE": ["database", "pool_size"],
            "DB_MAX_OVERFLOW": ["database", "max_overflow"],
            
            # Redis配置
            "REDIS_HOST": ["redis", "host"],
            "REDIS_PORT": ["redis", "port"],
            "REDIS_DB": ["redis", "db"],
            "REDIS_PASSWORD": ["redis", "password"],
            
            # MinIO配置
            "MINIO_ENDPOINT": ["storage", "minio", "endpoint"],
            "MINIO_ACCESS_KEY": ["storage", "minio", "access_key"],
            "MINIO_SECRET_KEY": ["storage", "minio", "secret_key"],
            "MINIO_SECURE": ["storage", "minio", "secure"],
            "MINIO_BUCKET": ["storage", "minio", "bucket"],
            
            # Milvus配置
            "MILVUS_HOST": ["vector_store", "milvus", "host"],
            "MILVUS_PORT": ["vector_store", "milvus", "port"],
            "MILVUS_COLLECTION": ["vector_store", "milvus", "collection"],
            
            # Elasticsearch配置
            "ELASTICSEARCH_URL": ["vector_store", "elasticsearch", "url"],
            "ELASTICSEARCH_USERNAME": ["vector_store", "elasticsearch", "username"],
            "ELASTICSEARCH_PASSWORD": ["vector_store", "elasticsearch", "password"],
            "ELASTICSEARCH_INDEX": ["vector_store", "elasticsearch", "index"],
            
            # LLM配置
            "OPENAI_API_KEY": ["llm", "openai_api_key"],
            "DEFAULT_MODEL": ["llm", "default_model"],
            
            # JWT配置
            "JWT_SECRET_KEY": ["auth", "jwt_secret_key"],
            "JWT_ALGORITHM": ["auth", "jwt_algorithm"],
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": ["auth", "access_token_expire_minutes"],
            
            # InfluxDB配置
            "INFLUXDB_URL": ["metrics", "influxdb", "url"],
            "INFLUXDB_TOKEN": ["metrics", "influxdb", "token"],
            "INFLUXDB_ORG": ["metrics", "influxdb", "org"],
            "INFLUXDB_BUCKET": ["metrics", "influxdb", "bucket"],
        }
        
        return base_mappings
    
    def _override_from_env(self) -> None:
        """从环境变量覆盖配置值"""
        env_mappings = self._build_env_mappings()
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_nested_value(self._config, config_path, os.environ[env_var])
                logger.debug(f"环境变量覆盖: {env_var} -> {'.'.join(config_path)}")
    
    def _set_nested_value(self, config_dict: Dict[str, Any], path: list, value: Any) -> None:
        """使用路径列表在嵌套字典中设置值"""
        current = config_dict
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 类型转换
        if path[-1] in current and not isinstance(current[path[-1]], dict):
            existing_type = type(current[path[-1]])
            if existing_type == bool:
                value = value.lower() in ('true', 'yes', '1')
            elif existing_type == int:
                value = int(value)
            elif existing_type == float:
                value = float(value)
        
        current[path[-1]] = value
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        使用点分隔的键获取配置值
        
        Args:
            *keys: 配置键路径
            default: 默认值
            
        Returns:
            配置值
        """
        current = self._config
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, *keys: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            *keys: 配置键路径
            value: 要设置的值
        """
        if not keys:
            return
        
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def reload(self) -> None:
        """重新加载配置"""
        logger.info("重新加载配置")
        self._load_config()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def has_key(self, *keys: str) -> bool:
        """检查配置键是否存在"""
        try:
            self.get(*keys)
            return True
        except:
            return False
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节"""
        return self.get(section, default={})
    
    def update_section(self, section: str, data: Dict[str, Any]) -> None:
        """更新配置节"""
        current_section = self.get_section(section)
        self._deep_update(current_section, data)
        self.set(section, current_section)


# 全局配置管理器实例
_config_manager = None


@lru_cache()
def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(*keys: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数
    
    Args:
        *keys: 配置键路径
        default: 默认值
        
    Returns:
        配置值
    """
    manager = get_config_manager()
    return manager.get(*keys, default=default)


def set_config(*keys: str, value: Any) -> None:
    """
    设置配置值的便捷函数
    
    Args:
        *keys: 配置键路径
        value: 要设置的值
    """
    manager = get_config_manager()
    manager.set(*keys, value=value)


def reload_config() -> None:
    """重新加载配置的便捷函数"""
    manager = get_config_manager()
    manager.reload() 