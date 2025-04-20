"""
基础仓库模块: 提供通用的数据库操作基类
"""

from typing import TypeVar, Generic, Type, List, Optional, Any, Dict, Union
from sqlalchemy.orm import Session
import logging

from app.models.database import Base

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    """基础仓库类，实现通用的CRUD操作"""
    
    def __init__(self, model: Type[T], db: Session):
        """
        初始化仓库
        
        参数:
            model: 仓库操作的模型类
            db: 数据库会话
        """
        self.model = model
        self.db = db
    
    def get_by_id(self, id: str) -> Optional[T]:
        """通过ID获取实体"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """获取所有实体，支持分页"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def filter_by(self, **kwargs) -> List[T]:
        """根据条件过滤实体"""
        return self.db.query(self.model).filter_by(**kwargs).all()
    
    def create(self, obj_in: Dict[str, Any]) -> T:
        """创建新实体"""
        try:
            obj = self.model(**obj_in)
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建实体时出错: {str(e)}")
            raise
    
    def update(self, id: str, obj_in: Dict[str, Any]) -> Optional[T]:
        """更新实体"""
        try:
            obj = self.get_by_id(id)
            if obj:
                for key, value in obj_in.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                self.db.commit()
                self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新实体时出错: {str(e)}")
            raise
    
    def delete(self, id: str) -> bool:
        """删除实体"""
        try:
            obj = self.get_by_id(id)
            if obj:
                self.db.delete(obj)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除实体时出错: {str(e)}")
            raise
    
    def count(self, **kwargs) -> int:
        """计算满足条件的实体数量"""
        return self.db.query(self.model).filter_by(**kwargs).count()
