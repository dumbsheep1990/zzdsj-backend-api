"""
数据库连接管理模块
提供数据库连接和会话管理的核心功能
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# 创建Base类
Base = declarative_base()


class DatabaseConnection:
    """数据库连接管理器"""
    
    def __init__(self, database_url: str = None, **kwargs):
        """
        初始化数据库连接
        
        Args:
            database_url: 数据库连接URL
            **kwargs: 其他连接参数
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.pool_size = kwargs.get('pool_size', 10)
        self.max_overflow = kwargs.get('max_overflow', 20)
        self.pool_recycle = kwargs.get('pool_recycle', 3600)
        
        # 创建引擎
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=self.pool_recycle,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow
        )
        
        # 创建SessionLocal类
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        
        logger.info(f"数据库连接已初始化: {self.database_url}")
    
    def get_engine(self):
        """获取数据库引擎"""
        return self.engine
    
    def get_session_factory(self):
        """获取会话工厂"""
        return self.SessionLocal
    
    def create_session(self) -> Session:
        """创建新的数据库会话"""
        return self.SessionLocal()
    
    def check_connection(self) -> bool:
        """检查数据库连接是否正常"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute("SELECT 1")
                if result.scalar() == 1:
                    logger.info("数据库连接正常")
                    return True
            logger.error("数据库连接失败")
            return False
        except Exception as e:
            logger.error(f"数据库连接出错: {str(e)}")
            return False
    
    def get_connection_pool_stats(self) -> dict:
        """获取连接池统计信息"""
        return {
            "pool_size": self.engine.pool.size(),
            "checked_out": self.engine.pool.checkedout(),
            "overflow": self.engine.pool.overflow(),
            "checkedin": self.engine.pool.checkedin(),
        }


# 全局数据库连接实例
_db_connection = None


def get_db_connection() -> DatabaseConnection:
    """获取全局数据库连接实例"""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection


def get_db():
    """用于FastAPI依赖注入的数据库会话生成器"""
    db_conn = get_db_connection()
    db = db_conn.create_session()
    try:
        yield db
    finally:
        db.close() 