"""
统一依赖注入管理模块: 提供全局依赖项，用于简化服务注入和资源管理
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Callable, Type, TypeVar, Dict, Any, Generator

from app.utils.core.database import get_db, get_db_session
# 导入统一知识库服务
from app.services.unified_knowledge_service import UnifiedKnowledgeService, get_unified_knowledge_service
from app.services.assistant import AssistantService
from app.services.conversation import ConversationService
from app.services.model_provider import ModelProviderService

# 创建泛型服务类型
T = TypeVar('T')

# 服务注册表
_service_registry: Dict[Type[Any], Callable[..., Any]] = {}

def register_service(service_class: Type[T], factory: Callable[..., T]) -> None:
    """注册服务工厂函数"""
    _service_registry[service_class] = factory

def get_service(service_class: Type[T]) -> Callable[..., T]:
    """获取指定类型的服务"""
    if service_class not in _service_registry:
        raise ValueError(f"服务未注册: {service_class.__name__}")
    return _service_registry[service_class]

# 数据库会话依赖
def db_dependency() -> Generator[Session, None, None]:
    """获取数据库会话依赖"""
    return get_db()

# 异步数据库会话依赖
async def async_db_dependency() -> Generator[Session, None, None]:
    """获取异步数据库会话依赖"""
    async for db in get_db_session():
        yield db

# 服务依赖函数
def knowledge_service_dependency(db: Session = Depends(db_dependency)) -> UnifiedKnowledgeService:
    """获取统一知识库服务依赖"""
    return get_unified_knowledge_service(db)

def assistant_service_dependency(db: Session = Depends(db_dependency)) -> AssistantService:
    """获取助手服务依赖"""
    return AssistantService(db)

def conversation_service_dependency(db: Session = Depends(db_dependency)) -> ConversationService:
    """获取对话服务依赖"""
    return ConversationService(db)

def model_provider_service_dependency(db: Session = Depends(db_dependency)) -> ModelProviderService:
    """获取模型提供商服务依赖"""
    return ModelProviderService(db)

# 注册服务工厂
register_service(UnifiedKnowledgeService, knowledge_service_dependency)
register_service(AssistantService, assistant_service_dependency)
register_service(ConversationService, conversation_service_dependency)
register_service(ModelProviderService, model_provider_service_dependency)

# LightRAG依赖注入
from app.frameworks.lightrag.workdir_manager import get_workdir_manager
from app.frameworks.lightrag.api_client import get_lightrag_api_client

async def get_lightrag_manager_dependency():
    """获取LightRAG工作目录管理器实例"""
    return get_workdir_manager()

async def get_lightrag_api_client_dependency():
    """获取LightRAG API客户端实例"""
    return get_lightrag_api_client()

# 服务依赖注入装饰器
def inject_service(service_class: Type[T]) -> Callable[..., T]:
    """依赖注入装饰器，用于获取指定类型的服务"""
    factory = get_service(service_class)
    return Depends(factory)
