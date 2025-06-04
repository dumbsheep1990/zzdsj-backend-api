"""
基础服务类
"""
from abc import ABC
from typing import Optional
import logging
from sqlalchemy.orm import Session


class BaseService(ABC):
    """基础服务抽象类"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    def _check_permission(self, resource_owner_id: int, user_id: int, resource_name: str = "资源") -> None:
        """检查用户权限"""
        from app.core.assistants.exceptions import PermissionDeniedError

        if resource_owner_id != user_id:
            raise PermissionDeniedError(resource_name)

    def _validate_exists(self, resource: Optional[any], resource_name: str = "资源") -> None:
        """验证资源存在"""
        from app.core.assistants.exceptions import AssistantNotFoundError

        if not resource:
            raise AssistantNotFoundError(0)  # 实际使用时应传入具体ID