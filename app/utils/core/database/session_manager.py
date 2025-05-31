"""
数据库会话管理模块
提供高级会话管理功能，包括异步上下文管理器和事务处理
"""

from contextlib import asynccontextmanager
import logging
from typing import Any, Callable
from .connection import get_db_connection

logger = logging.getLogger(__name__)


class DBSessionManager:
    """数据库会话管理器，提供异步上下文管理"""
    
    def __init__(self):
        self.db_connection = get_db_connection()
    
    @asynccontextmanager
    async def session(self):
        """异步上下文管理器获取会话"""
        db = self.db_connection.create_session()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            db.close()
    
    def execute_with_session(self, operation: Callable, *args, **kwargs) -> Any:
        """
        执行需要数据库会话的操作
        
        Args:
            operation: 需要执行的操作函数
            *args: 操作函数的位置参数
            **kwargs: 操作函数的关键字参数
            
        Returns:
            操作函数的返回值
        """
        db = self.db_connection.create_session()
        try:
            result = operation(db, *args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            db.close()
    
    def execute_transaction(self, operations: list) -> list:
        """
        执行事务操作
        
        Args:
            operations: 操作列表，每个元素为 (operation_func, args, kwargs)
            
        Returns:
            所有操作的返回值列表
        """
        db = self.db_connection.create_session()
        results = []
        try:
            for operation, args, kwargs in operations:
                result = operation(db, *args, **kwargs)
                results.append(result)
            db.commit()
            return results
        except Exception as e:
            db.rollback()
            logger.error(f"事务执行失败: {str(e)}")
            raise
        finally:
            db.close()
    
    def get_connection_pool_stats(self) -> dict:
        """获取连接池统计信息"""
        return self.db_connection.get_connection_pool_stats()
    
    def adjust_pool_size(self, pool_size: int = None, max_overflow: int = None):
        """
        调整连接池大小
        
        Args:
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
        """
        engine = self.db_connection.get_engine()
        if pool_size is not None:
            engine.pool._pool.maxsize = pool_size
            logger.info(f"已调整连接池大小为: {pool_size}")
        
        if max_overflow is not None:
            engine.pool._pool.overflow = max_overflow
            logger.info(f"已调整最大溢出为: {max_overflow}")


# 全局会话管理器实例
_session_manager = None


def get_session_manager() -> DBSessionManager:
    """获取全局会话管理器实例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = DBSessionManager()
    return _session_manager


# 异步获取会话的便捷函数
async def get_db_session():
    """异步获取数据库会话"""
    session_manager = get_session_manager()
    return session_manager.session() 