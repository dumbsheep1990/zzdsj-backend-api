"""
统一依赖注入管理模块: 提供全局依赖项，用于简化服务注入和资源管理
"""

from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Callable, Type, TypeVar, Dict, Any, Generator

from app.utils.database import get_db, get_db_session
from app.services.knowledge import KnowledgeService
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
def knowledge_service_dependency(db: Session = Depends(db_dependency)) -> KnowledgeService:
    """获取知识库服务依赖"""
    return KnowledgeService(db)

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
register_service(KnowledgeService, knowledge_service_dependency)
register_service(AssistantService, assistant_service_dependency)
register_service(ConversationService, conversation_service_dependency)
register_service(ModelProviderService, model_provider_service_dependency)

# 服务依赖注入装饰器
def inject_service(service_class: Type[T]) -> Callable[..., T]:
    """依赖注入装饰器，用于获取指定类型的服务"""
    factory = get_service(service_class)
    return Depends(factory)
