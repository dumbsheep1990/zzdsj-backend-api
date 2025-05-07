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
    
    def _build_env_mappings(self) -> Dict[str, list]:
        """自动构建环境变量到配置路径的映射"""
        # 基础映射 - 强制性依赖和基础配置
        base_mappings = {
            # 数据库配置
            "DATABASE_URL": ["database", "url"],
            
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
            
            # Nacos配置
            "NACOS_SERVER_ADDRESSES": ["service_discovery", "nacos", "server_addresses"],
            "NACOS_NAMESPACE": ["service_discovery", "nacos", "namespace"],
            "NACOS_GROUP": ["service_discovery", "nacos", "group"],
            
            # RabbitMQ配置
            "RABBITMQ_HOST": ["message_queue", "rabbitmq", "host"],
            "RABBITMQ_PORT": ["message_queue", "rabbitmq", "port"],
            "RABBITMQ_USER": ["message_queue", "rabbitmq", "user"],
            "RABBITMQ_PASSWORD": ["message_queue", "rabbitmq", "password"],
            
            # LLM通用配置
            "OPENAI_API_KEY": ["llm", "openai_api_key"],
            "DEFAULT_MODEL": ["llm", "default_model"],
            
            # InfluxDB配置
            "INFLUXDB_URL": ["metrics", "influxdb", "url"],
            "INFLUXDB_TOKEN": ["metrics", "influxdb", "token"],
            "INFLUXDB_ORG": ["metrics", "influxdb", "org"],
            "INFLUXDB_BUCKET": ["metrics", "influxdb", "bucket"],
        }
        
        # 扩展服务配置 - SearxNG
        searxng_mappings = {
            "SEARXNG_ENABLED": ["searxng", "enabled"],
            "SEARXNG_AUTO_DEPLOY": ["searxng", "auto_deploy"],
            "SEARXNG_HOST": ["searxng", "host"],
            "SEARXNG_PORT": ["searxng", "port"],
            "SEARXNG_DOCKER_IMAGE": ["searxng", "docker", "image"],
            "SEARXNG_CONTAINER_NAME": ["searxng", "docker", "container_name"],
            "SEARXNG_BIND_PORT": ["searxng", "docker", "bind_port"],
            "SEARXNG_INSTANCE_NAME": ["searxng", "instance_name"],
            "SEARXNG_BASE_URL": ["searxng", "base_url"],
            "SEARXNG_NETWORK_NAME": ["searxng", "docker", "network_name"],
        }
        
        # 扩展服务配置 - LightRAG
        lightrag_mappings = {
            "LIGHTRAG_ENABLED": ["lightrag", "enabled"],
            "LIGHTRAG_BASE_DIR": ["lightrag", "base_dir"],
            "LIGHTRAG_EMBEDDING_DIM": ["lightrag", "embedding_dim"],
            "LIGHTRAG_MAX_TOKEN_SIZE": ["lightrag", "max_token_size"],
            "LIGHTRAG_GRAPH_DB_TYPE": ["lightrag", "graph_db_type"],
            "LIGHTRAG_PG_HOST": ["lightrag", "pg_host"],
            "LIGHTRAG_PG_PORT": ["lightrag", "pg_port"],
            "LIGHTRAG_PG_USER": ["lightrag", "pg_user"],
            "LIGHTRAG_PG_PASSWORD": ["lightrag", "pg_password"],
            "LIGHTRAG_PG_DB": ["lightrag", "pg_db"],
            "LIGHTRAG_DOCKER_IMAGE": ["lightrag", "docker", "image"],
            "LIGHTRAG_CONTAINER_NAME": ["lightrag", "docker", "container_name"],
            "LIGHTRAG_PORT": ["lightrag", "port"],
            "LIGHTRAG_DATA_PATH": ["lightrag", "data_path"],
            "LIGHTRAG_NETWORK_NAME": ["lightrag", "docker", "network_name"],
        }
        
        # 语音配置 - 可选，仅当启用时需要
        voice_mappings = {
            "VOICE_ENABLED": ["voice", "enabled"],
            "STT_MODEL_NAME": ["voice", "stt", "model_name"],
            "TTS_MODEL_NAME": ["voice", "tts", "model_name"],
            "XUNFEI_APP_ID": ["voice", "xunfei", "app_id"],
            "XUNFEI_API_KEY": ["voice", "xunfei", "api_key"],
            "XUNFEI_API_SECRET": ["voice", "xunfei", "api_secret"],
        }
        
        # 合并所有映射
        all_mappings = {}
        all_mappings.update(base_mappings)
        all_mappings.update(searxng_mappings)
        all_mappings.update(lightrag_mappings)
        all_mappings.update(voice_mappings)
        
        # 添加从配置中自动检测的映射
        self._add_auto_mappings(all_mappings)
        
        return all_mappings
    
    def _add_auto_mappings(self, mappings: Dict[str, list]) -> None:
        """通过遍历现有配置，添加自动检测的映射"""
        def traverse_dict(d, path=None):
            if path is None:
                path = []
            
            for k, v in d.items():
                current_path = path + [k]
                
                if isinstance(v, dict):
                    traverse_dict(v, current_path)
                else:
                    # 生成环境变量名
                    env_var = "_".join(current_path).upper()
                    if env_var not in mappings:
                        mappings[env_var] = current_path
        
        # 仅对不完整的配置部分进行自动映射
        # 这里可以根据需要添加逻辑来确定哪些部分需要自动映射
        # 例如，模型提供商配置
        model_providers = self.config.get("model_providers", {})
        if model_providers:
            traverse_dict(model_providers, ["model_providers"])
            
    def _override_from_env(self) -> None:
        """从环境变量覆盖配置值"""
        # 获取环境变量到配置路径的映射
        env_mappings = self._build_env_mappings()
        
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


# 配置注入函数
def inject_config_to_env() -> None:
    """将配置值注入到环境变量中"""
    config_manager = get_config_manager()
    env_mappings = config_manager._build_env_mappings()
    
    # 遍历配置映射，将配置值注入到环境变量
    for env_var, config_path in env_mappings.items():
        value = config_manager.get(*config_path)
        if value is not None:
            # 只注入非空的配置值
            os.environ[env_var] = str(value)

# 获取配置分组函数
def get_config_group(group: str) -> Dict[str, Any]:
    """获取特定配置组的所有配置项"""
    return get_config_manager().get(group) or {}

# 获取基础依赖配置
def get_base_dependencies() -> Dict[str, Dict[str, Any]]:
    """获取系统的基础依赖配置，这些是必须的依赖"""
    manager = get_config_manager()
    return {
        "database": manager.get("database", default={}),
        "redis": manager.get("redis", default={}),
        "minio": manager.get("storage", "minio", default={}),
        "milvus": manager.get("vector_store", "milvus", default={}),
        "elasticsearch": manager.get("vector_store", "elasticsearch", default={}),
        "nacos": manager.get("service_discovery", "nacos", default={}),
        "influxdb": manager.get("metrics", "influxdb", default={}),
        "neo4j": manager.get("graph_db", "neo4j", default={})
    }

# 获取配置值的辅助函数
def get_config(*keys: str, default: Any = None) -> Any:
    """使用点表示法获取配置值"""
    return get_config_manager().get(*keys, default=default)
