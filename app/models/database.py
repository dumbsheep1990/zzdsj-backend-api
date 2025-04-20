from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# 创建SQLAlchemy引擎
engine = create_engine(settings.DATABASE_URL)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base基类
Base = declarative_base()

# 数据库依赖
def get_db():
    """
    数据库会话依赖项，用于API路由中获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
