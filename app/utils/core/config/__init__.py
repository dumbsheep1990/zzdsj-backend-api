"""
配置管理核心模块
提供配置加载、验证、引导和状态管理的统一接口
"""

# 核心组件导入
from .manager import (
    ConfigManager,
    get_config_manager,
    get_config,
    set_config,
    reload_config
)

from .validator import (
    ConfigValidator,
    get_validator,
    validate_config
)

from .bootstrap import (
    ConfigBootstrap,
    inject_config_to_env,
    get_config_group,
    get_base_dependencies
)

from .state import ConfigState
from .directory_manager import ConfigDirectoryManager

# 导出所有公共接口
__all__ = [
    # 配置管理
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "set_config", 
    "reload_config",
    
    # 配置验证
    "ConfigValidator",
    "get_validator",
    "validate_config",
    
    # 配置引导
    "ConfigBootstrap", 
    "inject_config_to_env",
    "get_config_group",
    "get_base_dependencies",
    
    # 配置状态
    "ConfigState",
    
    # 目录管理
    "ConfigDirectoryManager"
]

# 便捷函数
def init_config(config_path: str = None, validate: bool = True) -> dict:
    """
    初始化配置系统的便捷函数
    
    Args:
        config_path: 配置文件路径
        validate: 是否验证配置
        
    Returns:
        初始化结果
    """
    try:
        # 创建配置管理器
        if config_path:
            manager = ConfigManager(config_path)
        else:
            manager = get_config_manager()
        
        # 验证配置
        if validate:
            validator = get_validator()
            config_data = manager.get_all()
            report = validate_config(config_data)
            
            if not report["valid"]:
                return {
                    "success": False,
                    "error": "配置验证失败",
                    "validation_report": report
                }
        
        # 注入环境变量
        inject_config_to_env()
        
        return {
            "success": True,
            "config_path": manager._config_path,
            "validation_report": report if validate else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"配置初始化失败: {str(e)}"
        }


def get_service_config(service_name: str) -> dict:
    """
    获取服务配置的便捷函数
    
    Args:
        service_name: 服务名称
        
    Returns:
        服务配置字典
    """
    manager = get_config_manager()
    return manager.get_section(service_name)


def validate_service_config(service_name: str, config: dict = None) -> dict:
    """
    验证服务配置的便捷函数
    
    Args:
        service_name: 服务名称
        config: 配置字典，如果未提供则从管理器获取
        
    Returns:
        验证报告
    """
    if config is None:
        config = get_service_config(service_name)
    
    validator = get_validator()
    
    # 根据服务类型选择验证方法
    if service_name == "database":
        validator.validate_database_config(config)
    elif service_name == "redis":
        validator.validate_redis_config(config)
    elif service_name.startswith("minio"):
        validator.validate_minio_config(config)
    elif service_name.startswith("milvus"):
        validator.validate_milvus_config(config)
    elif service_name.startswith("elasticsearch"):
        validator.validate_elasticsearch_config(config)
    elif service_name == "llm":
        validator.validate_llm_config(config)
    elif service_name == "auth":
        validator.validate_jwt_config(config)
    else:
        # 通用验证
        validator.validate_required_fields(config, [])
    
    return validator.get_validation_report()
