# 数据库层功能增强实现文档

**日期**: 2025年4月29日


## 1. 概述

本文档详细记录了对"智政知识库问答系统"数据库层的增强实现，基于`database_integration.md`中的需求分析。主要实现了以下功能：

1. **数据库迁移系统**: 集成Alembic迁移框架
2. **统一依赖注入框架**: 实现全局依赖注入管理
3. **数据库初始化与填充**: 增强数据库自动初始化功能
4. **LlamaIndex存储适配器**: 为LlamaIndex框架提供自定义存储后端
5. **连接池管理**: 添加连接池监控和动态调整
6. **数据库测试**: 创建数据库操作的自动化测试

## 2. 数据库迁移系统 (Alembic)

### 2.1 实现内容

- 初始化Alembic配置文件`alembic.ini`
- 创建迁移脚本目录`migrations/`
- 配置`env.py`自动关联SQLAlchemy模型
- 设置从环境变量读取数据库信息

### 2.2 关键代码

```python
# migrations/env.py 关键部分
from app.config import settings
from app.utils.database import Base
from app.models import assistants, knowledge, chat, model_provider, assistant_qa
```

### 2.3 使用方法
# 从应用配置中获取数据库URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 设置模型元数据
target_metadata = Base.metadata

# 生成迁移脚本
python -m alembic revision --autogenerate -m "初始数据库架构"

# 升级到最新版本
python -m alembic upgrade head

# 回滚到上一版本
python -m alembic downgrade -1

### 3. 统一依赖注入框架
3.1 实现内容
创建全局依赖注入管理模块app/dependencies.py
实现服务注册和检索机制
提供同步和异步数据库会话依赖
实现服务依赖注入装饰器
3.2 关键代码
# app/dependencies.py 服务注册机制
_service_registry: Dict[Type[Any], Callable[..., Any]] = {}

def register_service(service_class: Type[T], factory: Callable[..., T]) -> None:
    """注册服务工厂函数"""
    _service_registry[service_class] = factory

def get_service(service_class: Type[T]) -> Callable[..., T]:
    """获取指定类型的服务"""
    if service_class not in _service_registry:
        raise ValueError(f"服务未注册: {service_class.__name__}")
    return _service_registry[service_class]

# 依赖注入装饰器
def inject_service(service_class: Type[T]) -> Callable[..., T]:
    """依赖注入装饰器，用于获取指定类型的服务"""
    factory = get_service(service_class)
    return Depends(factory)



3.3 使用方法

# API示例
from app.dependencies import inject_service
from app.services.assistant import AssistantService

@router.get("/assistants/{assistant_id}")
async def get_assistant(
    assistant_id: str,
    assistant_service: AssistantService = inject_service(AssistantService)
):
    """获取助手详情"""
    return await assistant_service.get_assistant(assistant_id)


### 4. 数据库初始化与数据填充
4.1 实现内容
增强init_db函数，支持表创建和数据填充
实现seed_initial_data函数填充初始数据
在应用启动时自动初始化数据库
添加错误处理和日志记录
4.2 关键代码
# app/utils/database.py 数据库初始化
def init_db(create_tables=True, seed_data=True):
    """
    初始化数据库
    
    Args:
        create_tables (bool): 是否创建表
        seed_data (bool): 是否填充初始数据
    """
    # 导入所有模型
    from app.models import assistants, knowledge, chat, model_provider, assistant_qa
    
    if create_tables:
        # 创建表
        logger.info("正在创建数据库表...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
    
    if seed_data:
        logger.info("正在填充初始数据...")
        seed_initial_data()
        logger.info("初始数据填充完成")

### 4.3 应用启动时的自动初始化
# main.py 启动事件
@app.on_event("startup")
async def startup_event():
    """启动时初始化服务"""
    # 初始化数据库
    print("正在初始化数据库...")
    try:
        init_db(create_tables=True, seed_data=True)
        print("数据库初始化成功")
    except Exception as e:
        print(f"初始化数据库时出错: {e}")


5. LlamaIndex存储适配器
5.1 实现内容
创建app/frameworks/llamaindex/storage.py模块
实现PostgresDocumentStore类，提供PostgreSQL存储后端
实现LlamaIndexStorageAdapter集成类
支持文档的增删改查操作
5.2 关键代码
# app/frameworks/llamaindex/storage.py 适配器类
class PostgresDocumentStore(BaseDocumentStore):
    """PostgreSQL文档存储适配器"""
    
    def __init__(self, namespace: Optional[str] = None):
        """初始化PostgreSQL文档存储"""
        self.namespace = namespace or "default"
        self._simple_docstore = SimpleDocumentStore()  # 用作备份和缓存
        
    def add_documents(self, docs: List[Document], **kwargs: Any) -> None:
        """添加文档到存储"""
        # 实现文档存储逻辑...
        
    def get_document(self, doc_id: str, **kwargs: Any) -> Optional[Document]:
        """从存储中获取文档"""
        # 实现文档获取逻辑...        


5.3 使用方法
# 使用示例
from app.frameworks.llamaindex.storage import LlamaIndexStorageAdapter
from llama_index.core import VectorStoreIndex

# 创建存储适配器
storage_adapter = LlamaIndexStorageAdapter(namespace="my_assistant")
storage_context = storage_adapter.get_storage_context()

# 创建索引时使用自定义存储
index = VectorStoreIndex.from_documents(
    documents=docs,
    storage_context=storage_context
)        


6. 连接池管理
6.1 实现内容
添加连接池统计信息获取函数
实现连接池大小动态调整功能
优化连接池配置读取
添加错误处理和日志记录
6.2 关键代码
python
CopyInsert
# app/utils/database.py 连接池管理
def get_connection_pool_stats(self):
    """获取连接池统计信息"""
    return {
        "pool_size": engine.pool.size(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "checkedin": engine.pool.checkedin(),
    }

def adjust_pool_size(self, pool_size=None, max_overflow=None):
    """调整连接池大小"""
    if pool_size is not None:
        engine.pool._pool.maxsize = pool_size
        logger.info(f"已调整连接池大小为: {pool_size}")
    
    if max_overflow is not None:
        engine.pool._pool.overflow = max_overflow
        logger.info(f"已调整最大溢出为: {max_overflow}")
7. 数据库测试
7.1 实现内容
创建tests/test_database.py测试模块
实现数据库连接测试
实现数据库初始化测试
实现模型CRUD操作测试
7.2 关键代码
python
CopyInsert
# tests/test_database.py 测试类
class TestDatabaseConnection(unittest.TestCase):
    """测试数据库连接"""
    def test_connection(self):
        """测试数据库连接是否正常"""
        self.assertTrue(check_connection(), "数据库连接失败")

class TestModelCRUD(unittest.TestCase):
    """测试模型CRUD操作"""
    
    def setUp(self):
        """测试前准备"""
        db_gen = get_db()
        self.db = next(db_gen)
    
    def tearDown(self):
        """测试后清理"""
        # 回滚所有测试中的变更
        self.db.rollback()
        self.db.close()
        
    def test_model_provider_crud(self):
        """测试模型提供商的CRUD操作"""
        # 实现CRUD测试逻辑...
7.3 运行测试
bash
CopyInsert
# 运行所有测试
python -m unittest discover -s tests

# 运行特定测试
python -m unittest tests.test_database
8. 后续建议
8.1 迁移策略
建议定期创建迁移脚本，尤其是在模型变更后
在迁移前备份数据库
在测试环境验证迁移脚本
8.2 连接池优化
根据应用负载调整连接池大小
设置合理的连接超时时间
实现连接池监控仪表盘
8.3 性能优化
定期分析和优化数据库查询
考虑添加查询缓存机制
为频繁查询的字段添加索引
9. 总结
本次数据库层功能增强完成了以下目标：

实现了完整的数据库版本控制和迁移系统
提供了统一的依赖注入框架
增强了数据库初始化和数据填充功能
为LlamaIndex提供了自定义存储后端
优化了连接池管理
添加了数据库测试
这些改进使系统更加健壮，支持更好的版本控制、依赖管理和测试能力。

