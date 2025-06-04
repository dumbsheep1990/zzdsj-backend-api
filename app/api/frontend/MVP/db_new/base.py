from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings

Base = declarative_base()

# 异步引擎和会话工厂
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """依赖：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session