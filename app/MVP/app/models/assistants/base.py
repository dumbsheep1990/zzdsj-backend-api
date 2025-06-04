"""
基础模型定义
"""
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from app.config.database import Base


class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())


class BaseModel(Base, TimestampMixin):
    """基础模型类"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)