"""
依赖注入管理器
"""
from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.compression_service import CompressionService


class ServiceContainer:
    """服务容器"""

    def __init__(self, db: Session):
        self.db = db
        self._services = {}

    def get_conversation_service(self) -> ConversationService:
        """获取对话服务"""
        if 'conversation' not in self._services:
            self._services['conversation'] = ConversationService(self.db)
        return self._services['conversation']

    def get_memory_service(self) -> MemoryService:
        """获取记忆服务"""
        if 'memory' not in self._services:
            self._services['memory'] = MemoryService(self.db)
        return self._services['memory']

    def get_compression_service(self) -> CompressionService:
        """获取压缩服务"""
        if 'compression' not in self._services:
            self._services['compression'] = CompressionService(self.db)
        return self._services['compression']


def get_service_container(db: Session = Depends(get_db)) -> ServiceContainer:
    """获取服务容器"""
    return ServiceContainer(db)
