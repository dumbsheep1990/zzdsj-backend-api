# 数据库初始化指南

## 概述

ZZ-Backend-Lite 提供两种数据库初始化方式，适用于不同的使用场景。

## 📊 数据库概况

- **总表数量**: 53个表
- **核心业务表**: 42个 
- **OWL Agent系统**: 8个表
- **上下文压缩系统**: 3个表
- **支持向量数据库**: Milvus/PgVector

## 🚀 方式一：全量初始化（推荐新项目）

### 特点
- 直接执行完整SQL脚本
- 适用于开发环境和新项目部署
- 快速创建完整数据库结构

### 使用方法

```bash
# 进入迁移目录
cd migrations

# 全量初始化（创建新数据库）
python database_initializer.py

# 强制重新创建（会删除现有数据）
python database_initializer.py --force-recreate

# 跳过向量数据库初始化
python database_initializer.py --skip-vector-db

# 指定向量数据库类型
python database_initializer.py --vector-store-type pgvector

# 检查初始化状态
python database_initializer.py --check-status
```

### 环境变量配置

```bash
# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=zzdsj

# 或使用完整URL
DATABASE_URL=postgresql://user:pass@host:port/dbname

# 向量数据库配置（可选）
MILVUS_HOST=localhost
MILVUS_PORT=19530
PGVECTOR_ENABLED=true
```

## 🔄 方式二：迁移管理（推荐生产环境）

### 特点
- 版本化数据库变更
- 支持增量更新和回滚
- 适用于生产环境和团队协作

### 使用方法

```bash
# 进入迁移目录
cd migrations

# 查看迁移状态
python migrate.py status

# 执行所有迁移
python migrate.py migrate

# 初始化迁移系统
python migrate.py init

# 创建新迁移文件
python migrate.py create-migration "migration_name"

# 重置数据库（危险操作）
python migrate.py reset --confirm
```

### 向量数据库迁移

```bash
# 创建向量数据库集合
python vector_db_migrator.py create-collection collection_name

# 查看集合状态
python vector_db_migrator.py list-collections

# 删除集合
python vector_db_migrator.py drop-collection collection_name
```

## 📋 快速启动指南

### 开发环境快速启动

```bash
# 1. 配置环境变量
export POSTGRES_HOST=localhost
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=zzdsj

# 2. 进入迁移目录
cd migrations

# 3. 全量初始化
python database_initializer.py --force-recreate

# 4. 检查状态
python database_initializer.py --check-status
```

### 生产环境部署

```bash
# 1. 配置环境变量
export DATABASE_URL=postgresql://user:pass@host:port/dbname

# 2. 进入迁移目录
cd migrations

# 3. 初始化迁移系统（首次部署）
python migrate.py init

# 4. 执行迁移
python migrate.py migrate

# 5. 检查状态
python migrate.py status
```

## 🛠 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查 PostgreSQL 服务是否运行
   - 验证连接参数和权限

2. **迁移执行失败**
   ```bash
   # 检查迁移状态
   python migrate.py status
   
   # 重置并重新迁移（慎用）
   python migrate.py reset --confirm
   python migrate.py migrate
   ```

3. **向量数据库连接问题**
   ```bash
   # 跳过向量数据库初始化
   python database_initializer.py --skip-vector-db
   ```

### 日志查看

```bash
# 设置详细日志
export LOG_LEVEL=DEBUG

# 查看详细执行过程
python database_initializer.py --force-recreate
```

## 📁 相关文件

- `database_complete.sql` - 完整数据库结构
- `migrations/database_initializer.py` - 全量初始化器
- `migrations/migrate.py` - 迁移管理工具
- `migrations/vector_db_migrator.py` - 向量数据库迁移工具
- `migrations/versions/` - 迁移版本文件目录

## ⚠️ 注意事项

1. **生产环境慎用 `--force-recreate`**，会删除所有数据
2. **备份重要数据**，特别是在执行迁移前
3. **测试环境优先验证**，确认迁移无误后再应用到生产
4. **向量数据库**需要单独配置和初始化

---

更多详细信息请参考项目文档或联系开发团队。 