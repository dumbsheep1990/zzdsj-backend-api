"""
知识库服务 - 兼容性入口
此文件提供向前兼容，将调用转发到统一服务
"""

from app.services.unified_knowledge_service import LegacyKnowledgeServiceAdapter as KnowledgeService
from app.services.unified_knowledge_service import get_legacy_adapter

def get_knowledge_service(db):
    """获取兼容的知识库服务"""
    return get_legacy_adapter(db)

# 保持原有的导入路径可用
__all__ = ['KnowledgeService', 'get_knowledge_service'] 