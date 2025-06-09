"""
基础仓储类
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, func
import logging

T = TypeVar('T')


class AsyncBaseRepository(ABC, Generic[T]):
    """异步基础仓储抽象类"""

    def __init__(self, db: AsyncSession, model_class: type):
        self.db = db
        self.model_class = model_class
        self.logger = logging.getLogger(self.__class__.__name__)

    async def create(self, **kwargs) -> T:
        """创建实体"""
        try:
            instance = self.model_class(**kwargs)
            self.db.add(instance)
            await self.db.commit()
            await self.db.refresh(instance)
            self.logger.info(f"Created {self.model_class.__name__} with id: {instance.id}")
            return instance
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Failed to create {self.model_class.__name__}: {str(e)}")
            raise

    async def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取实体"""
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
            

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """获取所有实体"""
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update(self, id: int, **kwargs) -> Optional[T]:
        """更新实体"""
        instance = await self.get_by_id(id)
        if not instance:
            return None

        try:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            await self.db.commit()
            await self.db.refresh(instance)
            return instance
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Failed to update {self.model_class.__name__}: {str(e)}")
            raise

    async def delete(self, id: int) -> bool:
        """删除实体"""
        instance = await self.get_by_id(id)
        if not instance:
            return False

        try:
            self.db.delete(instance)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()  
            self.logger.error(f"Failed to delete {self.model_class.__name__}: {str(e)}")
            raise

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计数量"""
        stmt = select(func.count(self.model_class.id))
        if filters:
            stmt = self._apply_filters(stmt, filters)
        result = await self.db.execute(stmt)
        return result.scalar()

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """应用过滤条件"""
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        return query