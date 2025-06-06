# 智政知识库问答系统后端

智政知识库问答系统的后端服务，提供对知识库问答能力的细粒度控制。

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

- **LlamaIndex**：作为统一入口点和路由框架，提供知识库索引、聊天功能和嵌入处理
- **HayStack**：问答系统框架，负责高级文档检索
- **Agno**：用于自主操作的代理框架，支持复杂推理
- **MCP**：Model Context Protocol，提供模型与外部工具和数据源的标准化连接

### 模型提供商支持

- **OpenAI**: GPT-3.5, GPT-4, GPT-4o系列模型
- **智谱AI**: GLM系列模型
- **DeepSeek**: DeepSeek系列模型
- **通义千问**: 阿里达摩院千问系列模型
- **百度文心一言**: 百度ERNIE系列模型
- **月之暗面**: Moonshot系列模型
- **Anthropic**: Claude系列模型
- **本地推理**: Ollama和VLLM本地部署支持
- **其他国内模型**: 百川、MiniMax等中文模型支持

## 目录结构

```
zz-backend-lite/
├── app/
│   ├── api/                # FastAPI路由
│   │   ├── assistants.py   # 助手管理端点
│   │   ├── knowledge.py    # 知识库管理端点
│   │   ├── chat.py         # 聊天接口端点
│   │   ├── model_provider.py # 模型提供商管理
│   │   └── assistant_qa.py # 问答助手管理
│   ├── core/               # 核心业务逻辑
│   │   ├── assistants/     # 助手管理逻辑
│   │   ├── knowledge/      # 知识库管理
│   │   ├── chat/           # 聊天交互逻辑
│   │   ├── chat_manager.py # 统一聊天管理
│   │   ├── model_manager.py # 模型连接管理
│   │   └── assistant_qa_manager.py # 问答助手管理
│   ├── frameworks/         # AI框架集成
│   │   ├── haystack/       # Haystack集成
│   │   ├── llamaindex/     # LlamaIndex集成
│   │   ├── agno/           # Agno代理框架
│   │   ├── mcp/            # MCP服务集成
│   │   └── integration/    # 框架集成层
│   ├── models/             # 数据库模型
│   │   ├── assistants.py   # 助手模型
│   │   ├── knowledge.py    # 知识库模型
│   │   ├── chat.py         # 聊天模型
│   │   ├── model_provider.py # 模型提供商模型
│   │   ├── mcp.py          # MCP模型
│   │   └── assistant_qa.py # 问答助手模型
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

- Python 3.10+
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
# 配置和编辑.env文件，也可在前端系统页面进行配置
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

## 数据库管理

本项目使用Alembic进行数据库迁移管理，确保数据库结构与代码同步：

```bash
# 创建新的迁移版本
alembic revision --autogenerate -m "描述变更"

# 升级到最新版本
alembic upgrade head

# 查看迁移历史
alembic history

# 回滚到特定版本
alembic downgrade <版本号>
```

## API端点

该服务提供了几个RESTful API端点：

### 用户认证与授权

- `POST /api/v1/auth/register` - 注册新用户
- `POST /api/v1/auth/login` - 用户登录获取令牌
- `POST /api/v1/auth/refresh` - 刷新访问令牌
- `GET /api/v1/auth/me` - 获取当前用户信息

### 用户管理

- `GET /api/v1/users/` - 获取用户列表（需要管理权限）
- `GET /api/v1/users/{user_id}` - 获取指定用户信息
- `PUT /api/v1/users/me` - 更新当前用户信息
- `PUT /api/v1/users/{user_id}` - 更新指定用户信息（需要管理权限）
- `DELETE /api/v1/users/{user_id}` - 删除/禁用用户（需要管理权限）
- `PUT /api/v1/users/me/password` - 更新当前用户密码
- `PUT /api/v1/users/me/settings` - 更新当前用户设置

### 角色与权限管理

- `GET /api/v1/users/roles` - 获取所有角色
- `POST /api/v1/users/roles` - 创建新角色
- `PUT /api/v1/users/roles/{role_id}` - 更新角色
- `DELETE /api/v1/users/roles/{role_id}` - 删除角色
- `GET /api/v1/users/permissions` - 获取所有权限
- `PUT /api/v1/users/roles/{role_id}/permissions` - 分配权限给角色
- `PUT /api/v1/users/{user_id}/roles` - 分配角色给用户

### API密钥管理

- `GET /api/v1/api-keys/` - 获取当前用户的API密钥
- `POST /api/v1/api-keys/` - 创建新API密钥
- `PUT /api/v1/api-keys/{api_key_id}` - 更新API密钥
- `DELETE /api/v1/api-keys/{api_key_id}` - 删除API密钥

### 助手管理

- `GET /api/v1/assistants/` - 列出所有助手
- `POST /api/v1/assistants/` - 创建新助手
- `GET /api/v1/assistants/{assistant_id}` - 获取助手详情
- `PUT /api/v1/assistants/{assistant_id}` - 更新助手
- `DELETE /api/v1/assistants/{assistant_id}` - 删除/停用助手

### 知识库管理

- `GET /api/v1/knowledge/` - 列出所有知识库
- `POST /api/v1/knowledge/` - 创建新知识库
- `GET /api/v1/knowledge/{knowledge_base_id}` - 获取知识库详情
- `PUT /api/v1/knowledge/{knowledge_base_id}` - 更新知识库
- `DELETE /api/v1/knowledge/{knowledge_base_id}` - 删除知识库
- `GET /api/v1/knowledge/{knowledge_base_id}/documents` - 列出文档
- `POST /api/v1/knowledge/{knowledge_base_id}/documents` - 添加文档

### 聊天接口

- `GET /api/v1/chat/conversations` - 列出对话
- `POST /api/v1/chat/conversations` - 创建新对话
- `GET /api/v1/chat/conversations/{conversation_id}` - 获取带有消息的对话
- `POST /api/v1/chat/` - 发送消息并获取AI响应

### 模型管理接口

- `GET /api/v1/models/providers` - 获取所有模型提供商
- `POST /api/v1/models/providers` - 添加新模型提供商
- `GET /api/v1/models/providers/{provider_id}` - 获取提供商详情
- `PUT /api/v1/models/providers/{provider_id}` - 更新模型提供商
- `DELETE /api/v1/models/providers/{provider_id}` - 删除模型提供商
- `GET /api/v1/models/providers/{provider_id}/models` - 获取提供商的模型
- `POST /api/v1/models/providers/{provider_id}/models` - 添加新模型
- `POST /api/v1/models/test-connection` - 测试模型连接

### 问答助手接口

- `GET /api/v1/assistant-qa/assistants` - 获取问答助手列表
- `POST /api/v1/assistant-qa/assistants` - 创建问答助手
- `GET /api/v1/assistant-qa/assistants/{assistant_id}` - 获取问答助手详情
- `GET /api/v1/assistant-qa/assistants/{assistant_id}/questions` - 获取问题列表
- `POST /api/v1/assistant-qa/questions` - 创建新问题
- `GET /api/v1/assistant-qa/questions/{question_id}` - 获取问题详情
- `PUT /api/v1/assistant-qa/questions/{question_id}/answer-settings` - 更新回答设置
- `PUT /api/v1/assistant-qa/questions/{question_id}/document-settings` - 更新文档设置

### MCP服务接口

#### 自定义MCP服务

- `GET /api/v1/mcp/server/status` - 获取MCP服务器状态，包括已注册工具、资源和提示的数量
- `POST /api/v1/mcp/server/restart` - 重启MCP服务器

- `GET /api/v1/mcp/tools` - 列出所有MCP工具，支持按类别和标签筛选
- `GET /api/v1/mcp/tools/{name}` - 获取特定工具的详细信息
- `POST /api/v1/mcp/tools` - 创建新MCP工具，支持动态代码加载和注册

- `GET /api/v1/mcp/resources` - 列出所有MCP资源
- `GET /api/v1/mcp/resources/{uri}` - 获取特定资源详情
- `POST /api/v1/mcp/resources` - 创建新MCP资源

- `GET /api/v1/mcp/prompts` - 列出所有MCP提示
- `GET /api/v1/mcp/prompts/{name}` - 获取特定提示详情
- `POST /api/v1/mcp/prompts` - 创建新MCP提示

- `POST /api/v1/mcp/deploy` - 将选定的工具、资源和提示打包并部署为MCP服务

#### 第三方MCP工具

- `GET /api/v1/mcp/providers` - 列出所有第三方MCP提供商，支持按能力筛选
- `GET /api/v1/mcp/providers/{provider_id}` - 获取特定提供商详情
- `POST /api/v1/mcp/providers` - 注册新的第三方MCP提供商
- `DELETE /api/v1/mcp/providers/{provider_id}` - 删除第三方MCP提供商

- `GET /api/v1/mcp/providers/{provider_id}/tools` - 列出提供商提供的工具
- `POST /api/v1/mcp/providers/{provider_id}/tools/{tool_name}/test` - 测试特定工具

- `POST /api/v1/mcp/providers/{provider_id}/chat` - 与支持聊天能力的提供商进行聊天，支持流式响应

## 知识库集成

助手可以链接到多个知识库，使其能够基于特定文档集合回答问题。文档自动处理流程：

1. 根据文件类型上传和解析文档
2. 将内容分块成可管理的片段
3. 为每个块生成嵌入向量
4. 将块存储在Milvus中进行向量相似度搜索
5. 当提出问题时，检索相关块以为AI响应提供信息

## 模型管理系统

模型管理系统提供了对各种大语言模型(LLM)的统一管理：

1. **模型提供商管理**：支持添加、编辑和删除模型提供商，包括配置API密钥和基础URL
2. **模型配置**：允许配置模型参数，如温度、最大输出长度等
3. **连接测试**：在使用前测试模型连接和API密钥有效性
4. **多提供商支持**：支持常见国内外模型提供商，如OpenAI、智谱、百度、阿里等
5. **本地部署支持**：集成Ollama和VLLM等本地部署方案

## 问答助手系统

问答助手系统提供产品级问答管理界面：

1. **助手类型**：支持产品文档助手、技术支持助手等不同类型助手
2. **问题管理**：为每个助手创建和管理预设问题卡片
3. **文档关联**：自动关联相关文档，并显示文档相关度
4. **回答模式控制**：提供多种回答模式
   - 默认模式：结合模型和文档知识
   - 仅文档模式：只使用文档内容回答
   - 仅模型模式：不参考文档只用模型回答
   - 混合模式：使用Agno代理进行高级协调
5. **文档设置**：允许选择特定文档分段用于回答问题
6. **缓存控制**：支持启用或禁用回答缓存

## 框架集成架构

系统通过集成多个框架来发挥各自优势：

1. **统一入口 - LlamaIndex**：负责接收用户查询，管理会话上下文，协调整个工作流，提供文档索引和检索功能
2. **QA助手 - Agno代理**：处理用户查询，支持记忆和工具使用，调用Haystack进行文档检索
3. **QA管理 - LlamaIndex与Agno协作**：LlamaIndex负责对话历史管理和文档知识集成，Agno维护会话状态
4. **知识库管理 - LlamaIndex与Haystack**：LlamaIndex负责文档索引和检索，Haystack用于高级搜索

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

### 多模型管理

支持在运行时切换不同模型提供商：
- 可根据成本、性能和能力选择适当的模型
- 支持特定任务使用专用模型（如文档总结vs.问答）
- 提供模型回退机制，确保服务可靠性

## 核心功能架构

### 知识库处理流程

1. **文档上传**：通过API上传文档到MinIO对象存储
2. **文档处理**：使用LlamaIndex进行文档解析、分块和嵌入 
3. **向量存储**：嵌入向量存储到Milvus向量数据库
4. **元数据索引**：文档元数据存储在PostgreSQL中

### 聊天系统架构

1. **聊天管理**：基于LlamaIndex构建的聊天管理器，处理消息路由和模型选择
2. **QA助手 - Agno代理**：处理用户查询，支持记忆和工具使用，调用Haystack进行文档检索
3. **QA管理 - LlamaIndex与Agno协作**：LlamaIndex负责对话历史管理和文档知识集成，Agno维护会话状态
4. **知识库管理 - LlamaIndex与Haystack**：LlamaIndex负责文档索引和检索，Haystack用于高级搜索

### MCP服务集成

1. **标准化工具连接**：使用Model Context Protocol标准连接AI模型与外部工具
2. **工具注册管理**：支持动态创建和注册MCP工具
3. **资源管理**：统一管理外部资源连接
4. **提示模板**：管理标准化的提示模板
