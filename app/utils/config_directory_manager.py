import os
import yaml
import logging
from typing import Dict, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

class ConfigDirectoryManager:
    """配置目录管理器，处理配置文件加载和环境变量替换"""
    
    def __init__(self, config_dir: str = None):
        """初始化配置管理器"""
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
        self.config_cache = {}
    
    def get_config(self, config_name: str, default: Any = None) -> Any:
        """获取指定名称的配置"""
        if config_name in self.config_cache:
            return self.config_cache[config_name]
        
        config_path = os.path.join(self.config_dir, f"{config_name}.yaml")
        
        if not os.path.exists(config_path):
            logger.warning(f"配置文件不存在: {config_path}")
            return default
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 处理环境变量替换
            config = self._process_env_vars(config)
            
            self.config_cache[config_name] = config
            return config
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {config_path}, 错误: {str(e)}")
            return default
    
    def _process_env_vars(self, config: Any) -> Any:
        """递归处理配置中的环境变量引用"""
        if isinstance(config, dict):
            return {k: self._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("{") and config.endswith("}"):
            # 环境变量引用格式: {ENV_VAR_NAME}
            env_var_name = config[1:-1]
            env_var_value = os.environ.get(env_var_name)
            
            if env_var_value is None:
                logger.warning(f"环境变量未设置: {env_var_name}")
                return config
            
            return env_var_value
        else:
            return config

# 创建单例实例
_config_directory_manager = None

def get_config_directory_manager() -> ConfigDirectoryManager:
    """获取配置目录管理器实例"""
    global _config_directory_manager
    if _config_directory_manager is None:
        _config_directory_manager = ConfigDirectoryManager()
    return _config_directory_manager
