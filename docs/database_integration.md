# 智政知识库问答系统 - 数据库层业务对接文档

## 1. 当前数据库架构概述

智政知识库问答系统采用多数据库架构：
- **PostgreSQL**: 主关系型数据库，存储结构化数据（助手、知识库、对话等）
- **Milvus**: 向量数据库，存储文档嵌入向量，用于相似度搜索
- **Redis**: 缓存服务，存储临时数据和会话状态

## 2. 现有DB组件实现

系统目前的数据库组件实现如下：

### 2.1 数据库连接管理
在 `app/utils/database.py` 已实现：
- SQLAlchemy 引擎创建与配置
- 会话工厂 (SessionLocal)
- 基础模型类 (Base)
- 简单的依赖注入函数 `get_db()`
- 数据库会话管理器 `DBSessionManager`
- 基本的连接检查功能

### 2.2 数据模型
`app/models/` 目录下定义了多个模型：
- assistants.py: 助手相关模型
- knowledge.py: 知识库相关模型
- chat.py: 聊天相关模型
- model_provider.py: 模型提供商相关模型
- assistant_qa.py: 问答助手相关模型

## 3. 缺失的数据库层功能

### 3.1 数据库初始化
当前仅有简单的 `init_db()` 函数，但缺少：
- 应用启动时的自动初始化机制
- 初始数据填充 (seeding) 机制
- 数据库连接池参数动态调整机制

### 3.2 依赖注入
目前的依赖注入机制比较简单：
- 仅有同步版本的 `get_db()`
- 缺少更完善的依赖注入框架集成
- 缺少依赖注入的统一管理

### 3.3 数据迁移
缺少完整的数据库迁移机制：
- README 中提到使用 Alembic，但未见具体实现
- 缺少版本控制的迁移脚本
- 缺少迁移回滚机制
- 无自动化的迁移测试流程

## 4. 建议的数据库层改进方案

### 4.1 数据库初始化改进

#### 4.1.1 自动初始化机制
```python
# 在 main.py 中添加
from app.utils.database import init_db

def startup_event():
    """应用启动时执行的事件"""
    # 初始化数据库
    init_db()
    # 其他初始化...

app.add_event_handler("startup", startup_event)
```

#### 4.1.2 初始数据填充
```python
# 在 app/utils/database.py 中添加
def seed_db(db: Session):
    """填充初始数据"""
    from app.models.model_provider import ModelProvider
    
    # 检查是否已存在
    if db.query(ModelProvider).filter_by(name="OpenAI").first() is None:
        # 创建默认模型提供商
        default_provider = ModelProvider(
            name="OpenAI",
            provider_type="openai",
            is_default=True,
            is_active=True
        )
        db.add(default_provider)
        db.commit()
```

### 4.2 依赖注入改进

#### 4.2.1 统一依赖注入管理
创建 `app/dependencies.py` 文件：
```python
"""依赖注入管理模块"""
from fastapi import Depends
from sqlalchemy.orm import Session
from app.utils.database import get_db, get_db_session
from app.services.assistant import AssistantService
from app.services.knowledge import KnowledgeBaseService
# 其他导入...

# 数据库依赖
def get_db_dependency():
    """获取数据库会话依赖"""
    return Depends(get_db)

# 服务层依赖
def get_assistant_service(db: Session = Depends(get_db)):
    """获取助手服务依赖"""
    return AssistantService(db)

def get_kb_service(db: Session = Depends(get_db)):
    """获取知识库服务依赖"""
    return KnowledgeBaseService(db)

# 更多服务依赖...
```

### 4.3 数据迁移实现

#### 4.3.1 Alembic 配置
1. 创建 `alembic.ini` 文件
2. 创建 `migrations` 目录
3. 配置 `env.py` 文件关联 SQLAlchemy 模型

#### 4.3.2 迁移脚本示例
```bash
# 生成迁移脚本
alembic revision --autogenerate -m "创建初始表结构"

# 升级到最新版本
alembic upgrade head

# 回滚到上一个版本
alembic downgrade -1
```

#### 4.3.3 CI/CD 集成
```yaml
# 在 CI/CD 流程中添加
steps:
  - name: 运行数据库迁移
    run: |
      alembic upgrade head
```

## 5. LlamaIndex 集成的数据库适配

根据系统架构，系统已重构为使用 LlamaIndex 作为统一入口和路由框架，需要考虑以下数据库适配：

### 5.1 LlamaIndex 文档存储适配
创建 `app/frameworks/llamaindex/storage.py` 文件：
```python
"""LlamaIndex 存储适配器"""
from llama_index.storage.docstore import BaseDocumentStore
from llama_index.schema import Document, BaseNode
from app.utils.database import db_manager
from app.models.knowledge import DocumentChunk
# 其他导入...

class PostgresDocumentStore(BaseDocumentStore):
    """PostgreSQL 文档存储适配器"""
    
    def __init__(self):
        """初始化"""
        super().__init__()
    
    def add_documents(self, docs, **kwargs):
        """添加文档"""
        # 实现文档添加逻辑
        pass
    
    def get_document(self, doc_id, **kwargs):
        """获取文档"""
        # 实现文档获取逻辑
        pass
    
    # 其他方法实现...
```

## 6. 业务对接指南

### 6.1 服务层中使用数据库
```python
from app.utils.database import db_manager
from app.models.assistants import Assistant

class AssistantService:
    """助手服务"""
    
    def __init__(self, db=None):
        """初始化，支持直接传入会话或使用会话管理器"""
        self.db = db
    
    async def create_assistant(self, data):
        """创建助手"""
        if self.db:
            # 如果已有会话，直接使用
            assistant = Assistant(**data)
            self.db.add(assistant)
            self.db.commit()
            self.db.refresh(assistant)
            return assistant
        else:
            # 使用会话管理器
            async with db_manager.session() as session:
                assistant = Assistant(**data)
                session.add(assistant)
                await session.commit()
                await session.refresh(assistant)
                return assistant
```

### 6.2 API层使用数据库依赖
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.services.assistant import AssistantService

router = APIRouter()

@router.post("/assistants/")
async def create_assistant(
    data: AssistantCreate,
    db: Session = Depends(get_db)
):
    """创建新助手"""
    service = AssistantService(db)
    return await service.create_assistant(data.dict())
```

## 7. 下一步建议

1. **实现数据库迁移**: 搭建 Alembic 迁移框架，创建初始迁移脚本
2. **完善依赖注入**: 实现统一的依赖注入管理
3. **添加数据库初始化**: 在应用启动时自动初始化并填充必要数据
4. **增强数据库连接管理**: 添加连接池监控和动态调整
5. **实现 LlamaIndex 适配器**: 为 LlamaIndex 框架提供自定义存储后端
6. **添加数据库测试**: 创建数据库操作的自动化测试

## 8. 最佳实践

1. **事务管理**: 使用 `db_manager.session()` 上下文管理器确保事务一致性
2. **依赖注入**: 在 API 端点中使用 `Depends(get_db)` 获取数据库会话
3. **连接池管理**: 通过配置适当调整连接池大小，避免连接泄漏
4. **异常处理**: 使用 try-except 块捕获并记录数据库异常
5. **迁移版本控制**: 定期创建数据库迁移脚本，记录架构变更
6. **服务层抽象**: 将数据库操作封装在服务层，而非直接在 API 中操作数据库
