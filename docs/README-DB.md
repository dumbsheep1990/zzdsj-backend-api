# 智政知识库问答系统数据库设计文档

本文档详细说明了智政知识库问答系统的数据库层设计，包括数据库选型、表结构设计、关系设计以及索引策略。

## 数据库选型

系统采用 PostgreSQL 作为主要的关系型数据库，具有以下优势：

- **强大的SQL标准支持**：符合ANSI-SQL:2008标准，支持复杂查询
- **高性能**：优秀的查询优化器和并发控制
- **JSON数据类型支持**：存储和查询非结构化或半结构化数据
- **可靠性**：强大的事务处理和ACID合规性
- **可扩展性**：支持水平扩展和分区表
- **全文搜索功能**：内置的全文检索能力

## 系统最小数据库支持

系统正常运行所需的最小数据库组件：

1. **PostgreSQL**：主数据库，存储结构化数据（助手、知识库、对话等）
2. **Milvus**：向量数据库，存储文档嵌入向量，用于相似度搜索
3. **Redis**：缓存服务，用于存储临时数据、会话状态和提高性能

## 核心表结构设计

### 助手管理模块

#### 1. assistants（助手表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| name | String(100) | 助手名称 |
| description | Text | 助手描述 |
| model | String(100) | 使用的模型 |
| capabilities | JSON | 助手能力列表 |
| configuration | JSON | 助手特定配置 |
| system_prompt | Text | 系统提示词 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| access_url | String(255) | 访问URL |

### 知识库管理模块

#### 2. knowledge_bases（知识库表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| name | String(255) | 知识库名称 |
| description | Text | 知识库描述 |
| is_active | Boolean | 是否活跃 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| settings | JSON | 知识库设置 |
| type | String(50) | 知识库类型 |
| agno_kb_id | String(255) | Agno知识库ID |
| total_documents | Integer | 文档总数 |
| total_tokens | Integer | Token总数 |
| embedding_model | String(100) | 嵌入模型 |

#### 3. documents（文档表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| knowledge_base_id | Integer | 知识库ID（外键） |
| title | String(255) | 文档标题 |
| content | Text | 文档内容 |
| mime_type | String(100) | MIME类型 |
| metadata | JSON | 元数据 |
| file_path | String(255) | 文件路径 |
| file_size | Integer | 文件大小 |
| status | String(50) | 状态 |
| error_message | Text | 错误信息 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 4. document_chunks（文档分块表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| document_id | Integer | 文档ID（外键） |
| content | Text | 分块内容 |
| metadata | JSON | 元数据 |
| embedding_id | String(255) | 向量ID |
| token_count | Integer | token数量 |
| created_at | DateTime | 创建时间 |

### 对话管理模块

#### 5. conversations（对话表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| assistant_id | Integer | 助手ID（外键） |
| title | String(255) | 对话标题 |
| metadata | JSON | 元数据 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 6. messages（消息表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| conversation_id | Integer | 对话ID（外键） |
| role | String(50) | 角色（user, assistant, system） |
| content | Text | 消息内容 |
| metadata | JSON | 元数据 |
| created_at | DateTime | 创建时间 |

### 模型管理模块

#### 7. model_providers（模型提供商表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| name | String(100) | 提供商名称 |
| provider_type | String(50) | 提供商类型 |
| api_key | String(255) | API密钥 |
| api_base | String(255) | API基础URL |
| api_version | String(50) | API版本 |
| is_default | Boolean | 是否默认 |
| is_active | Boolean | 是否活跃 |
| config | JSON | 额外配置 |

#### 8. model_info（模型信息表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| provider_id | Integer | 提供商ID（外键） |
| model_id | String(100) | 模型ID/名称 |
| display_name | String(100) | 显示名称 |
| capabilities | JSON | 模型能力 |
| is_default | Boolean | 是否默认 |
| config | JSON | 模型特定配置 |

### 问答助手模块

#### 9. questions（问题表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| assistant_id | Integer | 助手ID（外键） |
| question_text | Text | 问题文本 |
| answer_text | Text | 回答文本 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| views_count | Integer | 查看次数 |
| enabled | Boolean | 是否启用 |
| answer_mode | String(20) | 回答模式 |
| use_cache | Boolean | 是否使用缓存 |

#### 10. question_document_segments（问题-文档分段关联表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| question_id | Integer | 问题ID（外键） |
| document_id | Integer | 文档ID（外键） |
| segment_id | Integer | 分段ID（外键） |
| relevance_score | Float | 相关度分数 |
| is_enabled | Boolean | 是否启用 |

## 关系设计

系统中的主要数据关系如下：

1. **助手与知识库**：多对多关系
   - 通过 `assistant_knowledge_base` 关联表实现
   - 一个助手可以关联多个知识库，一个知识库可以被多个助手使用

2. **助手与对话**：一对多关系
   - 一个助手可以有多个对话，一个对话仅属于一个助手
   - 通过 `assistant_id` 外键关联

3. **对话与消息**：一对多关系
   - 一个对话包含多条消息，一条消息仅属于一个对话
   - 通过 `conversation_id` 外键关联

4. **知识库与文档**：一对多关系
   - 一个知识库包含多个文档，一个文档仅属于一个知识库
   - 通过 `knowledge_base_id` 外键关联

5. **文档与分块**：一对多关系
   - 一个文档被分为多个分块，一个分块仅属于一个文档
   - 通过 `document_id` 外键关联

6. **模型提供商与模型信息**：一对多关系
   - 一个提供商可以提供多个模型，一个模型归属于一个提供商
   - 通过 `provider_id` 外键关联

7. **助手与问题**：一对多关系
   - 一个问答助手包含多个问题，一个问题属于一个助手
   - 通过 `assistant_id` 外键关联

8. **问题与文档分段**：多对多关系
   - 通过 `question_document_segments` 关联表实现
   - 一个问题可以关联多个文档分段，一个分段可以被多个问题引用

## 索引策略

为提高查询性能，系统采用以下索引策略：

1. **助手表**：
   - 主键索引：`id`
   - 索引：`name`（快速按名称搜索）

2. **知识库表**：
   - 主键索引：`id`
   - 索引：`name`（快速按名称搜索）
   - 索引：`type`（按类型筛选）

3. **文档表**：
   - 主键索引：`id`
   - 外键索引：`knowledge_base_id`（知识库筛选）
   - 索引：`status`（按处理状态筛选）

4. **对话表**：
   - 主键索引：`id`
   - 外键索引：`assistant_id`（助手筛选）
   - 索引：`created_at`（按时间排序）

5. **消息表**：
   - 主键索引：`id`
   - 外键索引：`conversation_id`（对话筛选）
   - 索引：`role, created_at`（按角色和时间排序）

6. **模型提供商表**：
   - 主键索引：`id`
   - 索引：`provider_type`（按类型筛选）
   - 索引：`is_default, is_active`（默认和活跃状态筛选）

7. **问题表**：
   - 主键索引：`id`
   - 外键索引：`assistant_id`（助手筛选）
   - 索引：`enabled`（按启用状态筛选）
   - 索引：`views_count`（按查看次数排序）

## 数据迁移与演化

系统使用 Alembic 进行数据库迁移和版本控制，支持以下功能：

1. **版本控制**：记录所有数据库结构更改
2. **向前/向后迁移**：支持升级和降级操作
3. **分支迁移**：允许从任何迁移点创建新分支
4. **自动生成**：基于模型变更自动生成迁移脚本

## 高级数据管理

### 1. 大型BLOB数据处理

对于大型文件内容：
- 文本内容存储在PostgreSQL的Text字段中
- 原始文件存储在MinIO对象存储中
- 通过`file_path`字段关联文件的MinIO存储路径

### 2. 向量数据管理

文档分块嵌入向量：
- 向量数据存储在Milvus向量数据库中
- PostgreSQL中通过`embedding_id`引用Milvus中的向量ID
- 支持高维向量的高效相似度搜索

### 3. 缓存策略

使用Redis实现多级缓存：
- 频繁访问的问答结果缓存
- 会话状态和上下文缓存
- 文档检索结果的临时缓存

## 数据安全

数据库安全措施：

1. **敏感数据加密**：API密钥等敏感信息在存储前加密
2. **细粒度访问控制**：基于角色的数据库访问控制
3. **定期备份**：自动定期备份以防数据丢失
4. **审计日志**：记录关键数据操作以便追踪

## 数据库扩展方案

随着系统增长，数据库扩展策略：

1. **读写分离**：主库写入，从库读取
2. **表分区**：大表（如消息表）按时间或ID范围分区
3. **数据归档**：历史对话数据定期归档至冷存储
4. **连接池优化**：动态调整连接池大小

## 标准化服务配置下的基础依赖信息

为确保系统在各环境中稳定运行，标准化部署要求以下基础依赖配置：

### 数据库服务依赖

#### 1. PostgreSQL

- **推荐版本**：PostgreSQL 12.0 或更高版本
- **必要配置**：
  - 连接池：最小 5 连接，最大 100 连接
  - 事务隔离级别：READ COMMITTED
  - 字符集：UTF-8
  - 时区：Asia/Shanghai
- **资源要求**：
  - 最小配置：2 CPU核心，4GB内存，50GB存储
  - 生产推荐：4+ CPU核心，8GB+内存，SSD存储
  - 连接限制：根据预期并发用户计算，一般为 `(核心数 * 2) + 有效磁盘数`

#### 2. Milvus 向量数据库

- **推荐版本**：Milvus 2.1.0 或更高版本
- **必要配置**：
  - 索引类型：HNSW（推荐）或IVF_FLAT
  - 向量维度：依据使用的嵌入模型（如OpenAI为1536维）
  - 距离计算度量：余弦相似度 (COSINE)
- **资源要求**：
  - 最小配置：4 CPU核心，8GB内存
  - 生产推荐：8+ CPU核心，16GB+内存，SSD存储
  - 集合配置：1个默认向量集合，自动分片

#### 3. Redis 缓存服务

- **推荐版本**：Redis 6.0 或更高版本
- **必要配置**：
  - 持久化策略：RDB (每小时一次) + AOF (每秒同步)
  - 内存策略：allkeys-lru (当内存不足时淘汰最近最少使用的键)
  - 连接池：最小 5 连接，最大 50 连接
- **资源要求**：
  - 最小配置：2 CPU核心，4GB内存
  - 生产推荐：根据缓存命中率和响应时间调整
  - 数据库规划：
    - DB 0：默认/通用
    - DB 1：会话缓存
    - DB 2：API响应缓存
    - DB 3：向量检索结果缓存

### 存储服务依赖

#### 4. MinIO 对象存储

- **推荐版本**：MinIO RELEASE.2023-03-20T20-16-18Z 或更高版本
- **必要配置**：
  - 存储桶：至少配置一个默认bucket用于文档存储
  - 访问策略：仅后端服务可访问
  - 数据冗余：生产环境建议至少3份副本
- **资源要求**：
  - 文件系统：XFS（推荐）或ext4
  - 存储空间：根据预期文档规模，建议至少100GB起步

### 消息队列依赖

#### 5. RabbitMQ 消息队列

- **推荐版本**：RabbitMQ 3.9 或更高版本
- **必要配置**：
  - 队列定义：
    - document_processing：文档处理队列
    - vector_indexing：向量索引队列
    - notification：通知队列
  - 持久化：所有队列配置为持久化
  - 消息确认：启用消费者确认
- **资源要求**：
  - 最小配置：2 CPU核心，4GB内存
  - 生产推荐：根据消息吞吐量调整资源

### 服务发现与配置管理

#### 6. Nacos 服务发现与配置中心

- **推荐版本**：Nacos 2.0.0 或更高版本
- **必要配置**：
  - 命名空间：至少区分开发、测试和生产环境
  - 配置组：按服务模块划分
  - 集群名称：基于部署区域划分
- **资源要求**：
  - 最小配置：2 CPU核心，4GB内存
  - 生产推荐：3节点集群，每节点4 CPU核心，8GB内存

### 数据库连接信息配置模板

```yaml
# PostgreSQL配置
database:
  url: postgresql://username:password@hostname:5432/db_name
  pool_size: 20
  max_overflow: 10
  pool_recycle: 3600
  connect_args:
    client_encoding: 'utf8'
    application_name: 'zz-knowledge-qa'

# Milvus配置
vector_store:
  milvus:
    host: milvus-host
    port: 19530
    collection: knowledge_embeddings
    index_type: HNSW
    metric_type: COSINE
    dimension: 1536
    
# Redis配置
redis:
  host: redis-host
  port: 6379
  db: 0
  password: your-redis-password
  socket_timeout: 5
  socket_connect_timeout: 5
  
# 存储配置
storage:
  minio:
    endpoint: minio-host:9000
    access_key: your-access-key
    secret_key: your-secret-key
    secure: false
    bucket: knowledge-docs
    
# 消息队列配置
message_queue:
  rabbitmq:
    host: rabbitmq-host
    port: 5672
    user: guest
    password: guest
    virtual_host: /
    
# 服务发现配置
service_discovery:
  nacos:
    server_addresses: nacos-host:8848
    namespace: public
    group: DEFAULT_GROUP
    service_name: knowledge-qa-backend
