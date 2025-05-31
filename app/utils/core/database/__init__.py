"""
数据库核心模块
提供数据库连接、会话管理、迁移和健康检查的统一接口
"""

# 核心组件导入
from .connection import (
    DatabaseConnection,
    get_db_connection,
    get_db,
    Base
)

from .session_manager import (
    DBSessionManager,
    get_session_manager,
    get_db_session
)

from .migration import (
    DatabaseMigrator,
    get_migrator
)

from .health_check import (
    DatabaseHealthChecker,
    get_health_checker,
    quick_health_check
)

# 导出所有公共接口
__all__ = [
    # 连接管理
    "DatabaseConnection",
    "get_db_connection", 
    "get_db",
    "Base",
    
    # 会话管理
    "DBSessionManager",
    "get_session_manager",
    "get_db_session",
    
    # 数据库迁移
    "DatabaseMigrator", 
    "get_migrator",
    
    # 健康检查
    "DatabaseHealthChecker",
    "get_health_checker",
    "quick_health_check"
]

# 便捷函数
def init_database(create_tables: bool = True, seed_data: bool = True) -> bool:
    """
    初始化数据库的便捷函数
    
    Args:
        create_tables: 是否创建表
        seed_data: 是否填充初始数据
        
    Returns:
        初始化是否成功
    """
    migrator = get_migrator()
    return migrator.init_db(create_tables=create_tables, seed_data=seed_data)


def check_database_health() -> dict:
    """
    检查数据库健康状态的便捷函数
    
    Returns:
        健康检查报告
    """
    health_checker = get_health_checker()
    return health_checker.full_health_check()
