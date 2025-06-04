"""
服务层基础类
"""
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
from sqlalchemy.orm import Session
import logging

T = TypeVar('T')


class BaseService(ABC, Generic[T]):
    """服务层基础类"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def create(self, data: dict) -> T:
        """创建资源"""
        pass

    @abstractmethod
    async def get(self, id: int) -> Optional[T]:
        """获取资源"""
        pass

    @abstractmethod
    async def update(self, id: int, data: dict) -> Optional[T]:
        """更新资源"""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """删除资源"""
        pass