"""
Utils核心模块
提供数据库、配置管理、缓存系统的统一接口
"""

# 数据库模块
from .database import (
    DatabaseConnection,
    get_db_connection,
    get_db,
    DBSessionManager,
    get_session_manager,
    DatabaseMigrator,
    get_migrator,
    DatabaseHealthChecker,
    get_health_checker,
    init_database,
    check_database_health
)

# 配置管理模块
from .config import (
    ConfigManager,
    get_config_manager,
    get_config,
    set_config,
    reload_config,
    ConfigValidator,
    get_validator,
    validate_config,
    init_config,
    get_service_config,
    validate_service_config
)

# 缓存系统模块
from .cache import (
    RedisClient,
    get_redis_client,
    MemoryCache,
    get_memory_cache,
    CacheManager,
    get_cache_manager,
    get_cache_client
)

# 导出所有公共接口
__all__ = [
    # 数据库相关
    "DatabaseConnection",
    "get_db_connection",
    "get_db",
    "DBSessionManager", 
    "get_session_manager",
    "DatabaseMigrator",
    "get_migrator",
    "DatabaseHealthChecker",
    "get_health_checker",
    "init_database",
    "check_database_health",
    
    # 配置管理相关
    "ConfigManager",
    "get_config_manager",
    "get_config",
    "set_config",
    "reload_config",
    "ConfigValidator",
    "get_validator", 
    "validate_config",
    "init_config",
    "get_service_config",
    "validate_service_config",
    
    # 缓存相关
    "RedisClient",
    "get_redis_client",
    "MemoryCache",
    "get_memory_cache",
    "CacheManager",
    "get_cache_manager",
    "get_cache_client"
]

# 便捷函数
def init_core_systems(config_path: str = None) -> dict:
    """
    初始化所有核心系统的便捷函数
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        初始化结果
    """
    results = {}
    
    # 初始化配置系统
    config_result = init_config(config_path, validate=True)
    results["config"] = config_result
    
    if not config_result["success"]:
        return results
    
    # 初始化数据库
    try:
        db_result = init_database(create_tables=False, seed_data=False)
        results["database"] = {"success": db_result}
    except Exception as e:
        results["database"] = {"success": False, "error": str(e)}
    
    # 初始化缓存
    try:
        cache_manager = get_cache_manager()
        cache_health = cache_manager.health_check()
        results["cache"] = {
            "success": cache_health["overall_healthy"],
            "health": cache_health
        }
    except Exception as e:
        results["cache"] = {"success": False, "error": str(e)}
    
    # 检查整体状态
    all_success = all(
        result.get("success", False) 
        for result in results.values()
    )
    
    results["overall"] = {
        "success": all_success,
        "message": "所有核心系统初始化成功" if all_success else "部分核心系统初始化失败"
    }
    
    return results


def health_check_all() -> dict:
    """
    检查所有核心系统健康状态
    
    Returns:
        健康检查报告
    """
    health_report = {}
    
    # 数据库健康检查
    try:
        db_health = check_database_health()
        health_report["database"] = db_health
    except Exception as e:
        health_report["database"] = {
            "overall_status": "error",
            "error": str(e)
        }
    
    # 缓存健康检查
    try:
        cache_manager = get_cache_manager()
        cache_health = cache_manager.health_check()
        health_report["cache"] = cache_health
    except Exception as e:
        health_report["cache"] = {
            "overall_healthy": False,
            "error": str(e)
        }
    
    # 配置系统检查
    try:
        config_manager = get_config_manager()
        config_data = config_manager.get_all()
        validation_report = validate_config(config_data)
        health_report["config"] = {
            "valid": validation_report["valid"],
            "error_count": validation_report["error_count"],
            "warning_count": validation_report["warning_count"]
        }
    except Exception as e:
        health_report["config"] = {
            "valid": False,
            "error": str(e)
        }
    
    # 整体健康状态
    overall_healthy = (
        health_report.get("database", {}).get("overall_status") in ["healthy", "warning"] and
        health_report.get("cache", {}).get("overall_healthy", False) and
        health_report.get("config", {}).get("valid", False)
    )
    
    health_report["overall"] = {
        "healthy": overall_healthy,
        "status": "healthy" if overall_healthy else "unhealthy"
    }
    
    return health_report
