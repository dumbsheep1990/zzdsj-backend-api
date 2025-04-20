import os
import yaml
from typing import Any, Dict, Optional
from functools import lru_cache

class ConfigManager:
    """YAML configuration manager for application settings"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with optional config path"""
        # Default to config.yaml in project root
        if not config_path:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
            
        # Load environment-specific config if available
        env = os.getenv("APP_ENV", "development")
        env_config_path = os.path.join(os.path.dirname(config_path), f'config.{env}.yaml')
        
        # Load base config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Override with environment-specific config if it exists
        if os.path.exists(env_config_path):
            with open(env_config_path, 'r') as f:
                env_config = yaml.safe_load(f)
                self._deep_update(self.config, env_config)
        
        # Allow environment variables to override config
        self._override_from_env()
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """Recursively update a dictionary with another dictionary"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _override_from_env(self) -> None:
        """Override config values from environment variables"""
        # Map of environment variables to config paths
        env_mappings = {
            "DATABASE_URL": ["database", "url"],
            "OPENAI_API_KEY": ["llm", "openai_api_key"],
            "MILVUS_HOST": ["vector_store", "milvus", "host"],
            "REDIS_HOST": ["redis", "host"],
            "MINIO_ENDPOINT": ["storage", "minio", "endpoint"],
            "RABBITMQ_HOST": ["message_queue", "rabbitmq", "host"],
            "NACOS_SERVER_ADDRESSES": ["service_discovery", "nacos", "server_addresses"],
            # Add more mappings as needed
        }
        
        # Apply overrides
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_nested_value(self.config, config_path, os.environ[env_var])
    
    def _set_nested_value(self, config_dict: Dict[str, Any], path: list, value: Any) -> None:
        """Set a value in a nested dictionary using a path list"""
        current = config_dict
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Convert value type to match the existing value if possible
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
        """Get a value from the config using dot notation"""
        current = self.config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current


@lru_cache()
def get_config_manager() -> ConfigManager:
    """Singleton function to get the config manager instance"""
    return ConfigManager()


# Helper function to get config values
def get_config(*keys: str, default: Any = None) -> Any:
    """Get a config value using dot notation"""
    return get_config_manager().get(*keys, default=default)
