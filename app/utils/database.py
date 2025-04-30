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
            
    def get_connection_pool_stats(self):
        """获取连接池统计信息"""
        return {
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checkedin": engine.pool.checkedin(),
        }
    
    def adjust_pool_size(self, pool_size=None, max_overflow=None):
        """调整连接池大小"""
        if pool_size is not None:
            engine.pool._pool.maxsize = pool_size
            logger.info(f"已调整连接池大小为: {pool_size}")
        
        if max_overflow is not None:
            engine.pool._pool.overflow = max_overflow
            logger.info(f"已调整最大溢出为: {max_overflow}")

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

# 数据库初始化和填充
def init_db(create_tables=True, seed_data=True):
    """
    初始化数据库
    
    Args:
        create_tables (bool): 是否创建表
        seed_data (bool): 是否填充初始数据
    """
    # 导入所有模型
    from app.models import assistants, knowledge, chat, model_provider, assistant_qa, mcp
    
    if create_tables:
        # 创建表
        logger.info("正在创建数据库表...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
    
    if seed_data:
        logger.info("正在填充初始数据...")
        seed_initial_data()
        logger.info("初始数据填充完成")

def seed_initial_data():
    """填充初始数据"""
    # 使用会话管理器执行
    db_manager.execute_with_session(_seed_model_providers)
    # 可以添加更多的种子数据填充函数
    
def _seed_model_providers(db):
    """填充模型提供商初始数据"""
    from app.models.model_provider import ModelProvider
    
    # 检查默认的模型提供商是否已存在
    existing_provider = db.query(ModelProvider).filter_by(name="OpenAI").first()
    if existing_provider is None:
        # 创建默认模型提供商
        logger.info("创建默认模型提供商: OpenAI")
        default_provider = ModelProvider(
            name="OpenAI",
            provider_type="openai",
            api_base="https://api.openai.com/v1",
            is_default=True,
            is_active=True,
            models=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        )
        db.add(default_provider)
        
        # 添加其他模型提供商
        logger.info("创建模型提供商: Azure OpenAI")
        azure_provider = ModelProvider(
            name="Azure OpenAI",
            provider_type="azure",
            api_base="https://your-resource-name.openai.azure.com",
            is_default=False,
            is_active=False,
            models=["gpt-35-turbo", "gpt-4"]
        )
        db.add(azure_provider)
