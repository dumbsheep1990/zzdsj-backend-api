# 数据库迁移系统

这是一个完整的数据库迁移和初始化系统，支持PostgreSQL关系型数据库和向量数据库（Milvus/PgVector）的统一管理。

## 系统架构

```
migrations/
├── database_initializer.py      # 数据库初始化器
├── vector_db_migrator.py       # 向量数据库迁移管理器
├── migrate.py                  # 统一迁移管理命令
├── versions/                   # Alembic迁移版本文件
├── vector_migrations/          # 向量数据库迁移文件
├── sql/                       # 数据初始化SQL文件
│   └── common/               # 通用数据文件
└── README.md                  # 本文档
```

## 功能特性

### 1. 统一管理
- **关系型数据库**: 使用Alembic进行版本控制
- **向量数据库**: 自定义迁移系统，支持Milvus和PgVector
- **统一接口**: 通过`migrate.py`统一管理所有数据库操作

### 2. 完整的生命周期管理
- **初始化**: 从零开始创建完整的数据库结构
- **迁移**: 版本控制和增量更新
- **状态检查**: 实时监控数据库状态
- **回滚**: 支持迁移回滚（部分功能）

### 3. 向量数据库标准化
- **模板系统**: 预定义的集合模板
- **标准化配置**: 统一的字段和索引配置
- **版本控制**: 向量数据库的版本管理

## 快速开始

### 安装依赖

```bash
# 安装基础依赖
pip install asyncpg sqlalchemy alembic

# 安装向量数据库依赖
pip install pymilvus  # for Milvus
# 或
pip install pgvector  # for PgVector
```

### 环境配置

确保设置了正确的数据库连接：

```bash
# 设置PostgreSQL连接
export DATABASE_URL="postgresql://user:password@localhost:5432/database"

# 设置Milvus连接（如果使用）
export MILVUS_HOST="localhost"
export MILVUS_PORT="19530"
```

### 首次初始化

```bash
# 完整初始化（PostgreSQL + Milvus）
python migrate.py init --vector-store-type milvus

# 仅初始化PostgreSQL
python migrate.py init --skip-vector-db

# 强制重新创建（注意：会删除所有数据）
python migrate.py init --force-recreate --vector-store-type milvus
```

## 使用指南

### 1. 初始化数据库

```bash
# 初始化所有数据库
python migrate.py init

# 指定向量数据库类型
python migrate.py init --vector-store-type pgvector

# 跳过向量数据库
python migrate.py init --skip-vector-db

# 强制重新创建
python migrate.py init --force-recreate
```

### 2. 查看状态

```bash
# 检查所有数据库状态
python migrate.py status

# 仅检查PostgreSQL
python migrate.py status --skip-vector-db
```

### 3. 执行迁移

```bash
# 迁移到最新版本
python migrate.py migrate

# 仅迁移PostgreSQL
python migrate.py migrate --skip-vector-db
```

### 4. 创建向量数据库迁移

```bash
# 创建基本迁移
python migrate.py create-migration --description "添加新功能"

# 创建包含集合的迁移
python migrate.py create-migration \
  --description "添加图像和文档集合" \
  --create-collections document image
```

### 5. 重置数据库

```bash
# 重置所有数据库（危险操作）
python migrate.py reset --confirm-reset

# 仅重置PostgreSQL
python migrate.py reset --confirm-reset --skip-vector-db
```

## 高级用法

### 1. 自定义向量数据库迁移

创建自定义迁移文件：

```python
from vector_db_migrator import VectorDBMigrator

migrator = VectorDBMigrator("milvus")

# 创建自定义迁移
migration = await migrator.create_migration(
    description="添加自定义集合",
    collections_to_create=[
        {
            "name": "custom_collection",
            "schema": {
                "fields": [
                    {"name": "id", "type": "int64", "is_primary": True},
                    {"name": "embedding", "type": "float_vector", "dimension": 768},
                    {"name": "text", "type": "varchar", "max_length": 1000}
                ]
            },
            "index_config": {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "nlist": 1024
            }
        }
    ]
)

# 应用迁移
result = await migrator.apply_migration(migration.version)
```

### 2. 批量操作

```python
from database_initializer import DatabaseInitializer

initializer = DatabaseInitializer()

# 批量初始化
result = await initializer.initialize_all(
    force_recreate=False,
    skip_vector_db=False,
    vector_store_type="milvus"
)

# 检查结果
for component, details in result.items():
    print(f"{component}: {details}")
```

### 3. 环境特定配置

不同环境可以使用不同的配置：

```bash
# 开发环境
python migrate.py init --vector-store-type milvus

# 测试环境
python migrate.py init --vector-store-type pgvector

# 生产环境
python migrate.py migrate --log-level WARNING
```

## 配置文件

### 1. Alembic配置 (alembic.ini)

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://user:password@localhost:5432/database

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic
```

### 2. 向量数据库模板配置

模板配置文件位于 `app/config/vector_store_templates.yaml`，定义了：

- **base_configs**: 基础配置模板
- **field_templates**: 字段模板
- **index_templates**: 索引模板
- **collection_templates**: 集合模板

## 故障排除

### 1. 常见问题

**数据库连接失败**
```bash
# 检查连接配置
echo $DATABASE_URL

# 测试连接
python -c "import asyncpg; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

**向量数据库连接失败**
```bash
# 检查Milvus服务
curl http://localhost:19530/health

# 检查PgVector扩展
psql -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**迁移冲突**
```bash
# 查看迁移状态
python migrate.py status

# 重置迁移状态（谨慎使用）
python migrate.py reset --confirm-reset
```

### 2. 日志调试

```bash
# 启用详细日志
python migrate.py init --log-level DEBUG

# 查看日志文件
tail -f migrations.log
```

### 3. 手动恢复

如果自动迁移失败，可以手动执行：

```sql
-- 检查迁移历史
SELECT * FROM alembic_version;
SELECT * FROM vector_db_migrations;

-- 手动标记迁移完成
INSERT INTO vector_db_migrations (version, description, vector_store_type, operations_hash)
VALUES ('20250108_001', 'Manual fix', 'milvus', 'manual');
```

## 开发指南

### 1. 添加新的关系型数据库迁移

```bash
# 使用Alembic创建迁移
alembic revision --autogenerate -m "添加新表"

# 编辑生成的迁移文件
vim migrations/versions/xxx_add_new_table.py

# 应用迁移
python migrate.py migrate
```

### 2. 添加新的向量数据库功能

1. 在 `vector_db_migrator.py` 中添加新的操作类型
2. 在 `_execute_operation` 方法中处理新类型
3. 创建相应的迁移文件

### 3. 扩展初始化器

在 `database_initializer.py` 中添加新的初始化步骤：

```python
async def _initialize_new_component(self):
    """初始化新组件"""
    # 实现初始化逻辑
    pass

# 在 initialize_all 方法中调用
async def initialize_all(self, ...):
    # ... 现有代码 ...
    await self._initialize_new_component()
```

## 最佳实践

1. **备份**: 在生产环境执行迁移前，一定要备份数据
2. **测试**: 在测试环境验证迁移脚本
3. **监控**: 监控迁移过程和数据库性能
4. **版本控制**: 将迁移文件纳入版本控制
5. **文档**: 记录重要的迁移变更

## 维护

- 定期清理过期的迁移文件
- 监控数据库性能和空间使用
- 更新配置模板以适应新需求
- 保持向量数据库和关系型数据库的一致性

## 支持

如有问题，请：

1. 查看日志文件 `migrations.log`
2. 检查数据库连接和权限
3. 参考故障排除部分
4. 联系开发团队 