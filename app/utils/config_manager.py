import os
import yaml
from typing import Any, Dict, Optional
from functools import lru_cache

class ConfigManager:
    """YAML配置管理器，用于应用程序设置"""
    
    def __init__(self, config_path: Optional[str] = None):
        """使用可选的配置路径初始化"""
        # 默认使用项目根目录中的config.yaml
        if not config_path:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
            
        # 如果有特定环境的配置，则加载
        env = os.getenv("APP_ENV", "development")
        env_config_path = os.path.join(os.path.dirname(config_path), f'config.{env}.yaml')
        
        # 加载基础配置
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # 如果存在特定环境的配置，则覆盖基础配置
        if os.path.exists(env_config_path):
            with open(env_config_path, 'r') as f:
                env_config = yaml.safe_load(f)
                self._deep_update(self.config, env_config)
        
        # 允许环境变量覆盖配置
        self._override_from_env()
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """递归地用另一个字典更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _override_from_env(self) -> None:
        """从环境变量覆盖配置值"""
        # 环境变量到配置路径的映射
        env_mappings = {
            "DATABASE_URL": ["database", "url"],
            "OPENAI_API_KEY": ["llm", "openai_api_key"],
            "MILVUS_HOST": ["vector_store", "milvus", "host"],
            "REDIS_HOST": ["redis", "host"],
            "MINIO_ENDPOINT": ["storage", "minio", "endpoint"],
            "RABBITMQ_HOST": ["message_queue", "rabbitmq", "host"],
            "NACOS_SERVER_ADDRESSES": ["service_discovery", "nacos", "server_addresses"],
            # 根据需要添加更多映射
        }
        
        # 应用覆盖
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_nested_value(self.config, config_path, os.environ[env_var])
    
    def _set_nested_value(self, config_dict: Dict[str, Any], path: list, value: Any) -> None:
        """使用路径列表在嵌套字典中设置值"""
        current = config_dict
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 如果可能，将值类型转换为与现有值匹配
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
        """使用点表示法从配置中获取值"""
        current = self.config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current


@lru_cache()
def get_config_manager() -> ConfigManager:
    """获取配置管理器实例的单例函数"""
    return ConfigManager()


# 获取配置值的辅助函数
def get_config(*keys: str, default: Any = None) -> Any:
    """使用点表示法获取配置值"""
    return get_config_manager().get(*keys, default=default)
