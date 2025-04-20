"""
数据库连接工具模块: 提供SQL连接和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging
from app.config import settings

# 配置日志
logger = logging.getLogger(__name__)

# 创建SQLAlchemy引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=settings.DB_POOL_SIZE if hasattr(settings, 'DB_POOL_SIZE') else 10,
    max_overflow=settings.DB_MAX_OVERFLOW if hasattr(settings, 'DB_MAX_OVERFLOW') else 20
)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类
Base = declarative_base()

# 获取数据库会话
def get_db():
    """用于FastAPI依赖注入的数据库会话生成器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化数据库表
def init_db():
    """初始化数据库表，导入所有模型以确保它们被注册"""
    # 导入所有模型
    from app.models import assistants, knowledge, chat
    
    # 创建表
    logger.info("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")

class DBSessionManager:
    """数据库会话管理器，提供异步上下文管理"""
    
    @asynccontextmanager
    async def session(self):
        """异步上下文管理器获取会话"""
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            db.close()
    
    def execute_with_session(self, operation, *args, **kwargs):
        """执行需要数据库会话的操作"""
        db = SessionLocal()
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

# 创建会话管理器单例
db_manager = DBSessionManager()

# 异步获取会话
async def get_db_session():
    """异步获取数据库会话"""
    return db_manager.session()

# 检查数据库连接
def check_connection():
    """检查数据库连接是否正常"""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            if result.scalar() == 1:
                logger.info("数据库连接正常")
                return True
        logger.error("数据库连接失败")
        return False
    except Exception as e:
        logger.error(f"数据库连接出错: {str(e)}")
        return False
