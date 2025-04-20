# 知识库问答系统后端

智政智脑后端服务，提供对知识库问答能力的细粒度控制。

## 架构概述

该后端采用模块化架构设计，集成了多个框架和服务：

### 核心组件

- **FastAPI**：高性能REST API框架
- **PostgreSQL**：用于结构化数据的关系型数据库
- **Milvus**：用于嵌入和相似度搜索的向量数据库
- **Redis**：缓存和发布/订阅消息
- **MinIO**：文档文件的对象存储
- **RabbitMQ**：用于异步处理的消息队列
- **Nacos**：服务发现和配置管理
- **Celery**：用于后台处理的分布式任务队列

### AI/ML集成

- **LangChain**：LLM应用开发框架
- **HayStack**：问答系统框架
- **LlamaIndex**：LLM应用的数据框架
- **Agno**：用于自主操作的代理框架

## 目录结构

```
zz-backend-lite/
├── app/
│   ├── api/                # FastAPI路由
│   │   ├── assistants.py   # 助手管理端点
│   │   ├── knowledge.py    # 知识库管理端点
│   │   └── chat.py         # 聊天接口端点
│   ├── core/               # 核心业务逻辑
│   │   ├── assistants/     # 助手管理逻辑
│   │   ├── knowledge/      # 知识库管理
│   │   └── chat/           # 聊天交互逻辑
│   ├── frameworks/         # AI框架集成
│   │   ├── haystack/       # Haystack集成
│   │   ├── langchain/      # LangChain集成
│   │   ├── llamaindex/     # LlamaIndex集成
│   │   └── agents/         # 代理框架(Agno)
│   ├── models/             # 数据库模型
│   │   ├── assistants.py   # 助手模型
│   │   ├── knowledge.py    # 知识库模型
│   │   └── chat.py         # 聊天模型
│   ├── schemas/            # Pydantic模式
│   ├── utils/              # 实用函数
│   │   ├── database.py     # 数据库工具
│   │   ├── vector_store.py # Milvus集成
│   │   ├── redis_client.py # Redis集成
│   │   ├── object_storage.py # MinIO集成
│   │   ├── message_queue.py # RabbitMQ集成
│   │   └── service_discovery.py # Nacos集成
│   └── worker.py           # Celery工作任务
│   └── config.py           # 应用程序配置
├── main.py                 # 应用程序入口点
├── .env.example            # 环境变量模板
├── docker-compose.yml      # 基础设施设置
└── requirements.txt        # 依赖项
```

## 入门指南

### 前提条件

- Python 3.9+
- Docker和Docker Compose（用于基础设施）

### 设置基础设施

1. 启动所需的基础设施服务：

```bash
docker-compose up -d
```

这将启动PostgreSQL、Milvus、Redis、MinIO、RabbitMQ和Nacos。

2. 配置环境变量：

```bash
cp .env.example .env
# 使用您的特定设置编辑.env文件，特别是API密钥
```

3. 安装依赖项：

```bash
pip install -r requirements.txt
```

4. 初始化数据库模式（首次运行）：

```bash
alembic upgrade head
```

5. 启动后端服务：

```bash
python main.py
```

6. 启动用于后台任务的Celery工作器：

```bash
celery -A app.worker worker --loglevel=info
```

## API端点

该服务提供了几个RESTful API端点：

### 助手管理

- `GET /api/assistants/` - 列出所有助手
- `POST /api/assistants/` - 创建新助手
- `GET /api/assistants/{assistant_id}` - 获取助手详情
- `PUT /api/assistants/{assistant_id}` - 更新助手
- `DELETE /api/assistants/{assistant_id}` - 删除/停用助手

### 知识库管理

- `GET /api/knowledge/` - 列出所有知识库
- `POST /api/knowledge/` - 创建新知识库
- `GET /api/knowledge/{knowledge_base_id}` - 获取知识库详情
- `PUT /api/knowledge/{knowledge_base_id}` - 更新知识库
- `DELETE /api/knowledge/{knowledge_base_id}` - 删除知识库
- `GET /api/knowledge/{knowledge_base_id}/documents` - 列出文档
- `POST /api/knowledge/{knowledge_base_id}/documents` - 添加文档

### 聊天接口

- `GET /api/chat/conversations` - 列出对话
- `POST /api/chat/conversations` - 创建新对话
- `GET /api/chat/conversations/{conversation_id}` - 获取带有消息的对话
- `POST /api/chat/` - 发送消息并获取AI响应

## 助手能力

每个助手可以配置不同的能力：

- **客户支持**：处理客户服务查询
- **问答**：回答通用知识问题
- **服务介绍**：提供有关服务的信息

## 知识库集成

助手可以链接到多个知识库，使其能够基于特定文档集合回答问题。文档自动处理流程：

1. 根据文件类型上传和解析文档
2. 将内容分块成可管理的片段
3. 为每个块生成嵌入向量
4. 将块存储在Milvus中进行向量相似度搜索
5. 当提出问题时，检索相关块以为AI响应提供信息

## 高级功能

### 分布式处理

使用Celery和RabbitMQ异步处理长时间运行的任务（如文档处理），防止API超时。

### 服务发现

服务向Nacos注册自身，使其他服务能够动态发现并与之通信。

### 可扩展性

该架构支持水平扩展：
- 无状态API服务器可以部署在负载均衡器后面
- 多个Celery工作器可以并行处理任务
- Milvus和PostgreSQL等基础设施组件支持集群

## 定制化

系统可以通过多种方式扩展：

- 在`app/core/knowledge/document_processor.py`中添加新的文档解析器
- 在`app/frameworks/`目录中实现其他AI框架
- 通过扩展数据模型和核心服务逻辑创建新的助手能力

## 安全考虑

- API密钥和敏感数据应在`.env`文件中妥善保护
- MinIO桶权限应仔细配置
- 考虑为生产环境实施适当的身份验证和授权
