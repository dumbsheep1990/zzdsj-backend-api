# LightRAG知识图谱集成文档

## 1. 概述

本文档描述了如何将LightRAG知识图谱功能集成到现有系统中，包括部署要求、配置方法和使用示例。LightRAG提供了高效的检索增强生成(RAG)能力，通过知识图谱来增强大语言模型的响应质量。

## 2. 部署方式

LightRAG可以通过两种方式部署：

### 2.1 作为Python包集成

LightRAG可以作为Python包直接集成到现有系统中，这是最简单的方式，适合快速开发和测试：

```bash
pip install lightrag-hku
```

如果需要API服务和Web界面：

```bash
pip install "lightrag-hku[api]"
```

### 2.2 Docker部署模式（推荐）

**Docker部署是推荐的生产环境部署方式**，它提供了更好的隔离性和资源管理，特别是当使用PostgreSQL或Redis作为后端存储时。

LightRAG的Docker部署支持以下配置：

- 独立文件存储模式：最简单的部署方式，适合小规模应用
- PostgreSQL存储模式：适合大规模生产环境，提供更好的并发性能
- Redis存储模式：适合需要高速缓存和检索的场景

## 3. 环境要求

### 3.1 基础要求

- Python 3.8+
- 足够的磁盘空间用于存储知识图谱数据
- 至少8GB RAM（推荐16GB以上）

### 3.2 Docker环境要求

- Docker 20.10+
- Docker Compose V2
- 对于集群部署：Docker Swarm或Kubernetes

## 4. Docker部署配置

### 4.1 docker-compose.yml配置

将以下配置添加到现有的`docker-compose.yml`文件中：

```yaml
version: '3'

services:
  # 主应用服务
  app:
    # 现有配置...
    environment:
      # 现有环境变量...
      # LightRAG配置
      - LIGHTRAG_ENABLED=true
      - LIGHTRAG_BASE_DIR=/app/data/lightrag
      - LIGHTRAG_GRAPH_DB_TYPE=${LIGHTRAG_GRAPH_DB_TYPE:-file}
      - LIGHTRAG_PG_HOST=${LIGHTRAG_PG_HOST:-lightrag-postgres}
      - LIGHTRAG_PG_PORT=${LIGHTRAG_PG_PORT:-5432}
      - LIGHTRAG_PG_USER=${LIGHTRAG_PG_USER:-postgres}
      - LIGHTRAG_PG_PASSWORD=${LIGHTRAG_PG_PASSWORD:-password}
      - LIGHTRAG_PG_DB=${LIGHTRAG_PG_DB:-lightrag}
      - LIGHTRAG_REDIS_HOST=${LIGHTRAG_REDIS_HOST:-redis}
      - LIGHTRAG_REDIS_PORT=${LIGHTRAG_REDIS_PORT:-6379}
      - LIGHTRAG_REDIS_DB=${LIGHTRAG_REDIS_DB:-1}
      - LIGHTRAG_REDIS_PASSWORD=${LIGHTRAG_REDIS_PASSWORD:-}
    volumes:
      # 现有卷...
      - lightrag-data:/app/data/lightrag
    depends_on:
      # 现有依赖...
      - lightrag-postgres  # 如果使用PostgreSQL存储

  # LightRAG PostgreSQL数据库（可选，仅当使用PostgreSQL存储时需要）
  lightrag-postgres:
    image: postgres:14
    restart: always
    environment:
      POSTGRES_USER: ${LIGHTRAG_PG_USER:-postgres}
      POSTGRES_PASSWORD: ${LIGHTRAG_PG_PASSWORD:-password}
      POSTGRES_DB: ${LIGHTRAG_PG_DB:-lightrag}
    volumes:
      - lightrag-postgres-data:/var/lib/postgresql/data
    ports:
      - "5433:5432"  # 避免与主PostgreSQL冲突
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  # 现有卷...
  lightrag-data:
  lightrag-postgres-data:
```

### 4.2 .env文件配置

在项目根目录的`.env`文件中添加以下配置：

```
# LightRAG配置
LIGHTRAG_ENABLED=true
LIGHTRAG_BASE_DIR=./data/lightrag
LIGHTRAG_EMBEDDING_DIM=1536
LIGHTRAG_MAX_TOKEN_SIZE=8192

# LightRAG存储配置
# 可选: file (文件存储), postgres (PostgreSQL存储), redis (Redis存储)
LIGHTRAG_GRAPH_DB_TYPE=file  

# PostgreSQL配置（当LIGHTRAG_GRAPH_DB_TYPE=postgres时使用）
LIGHTRAG_PG_HOST=lightrag-postgres
LIGHTRAG_PG_PORT=5432
LIGHTRAG_PG_USER=postgres
LIGHTRAG_PG_PASSWORD=password
LIGHTRAG_PG_DB=lightrag

# Redis配置（当LIGHTRAG_GRAPH_DB_TYPE=redis时使用）
LIGHTRAG_REDIS_HOST=redis
LIGHTRAG_REDIS_PORT=6379
LIGHTRAG_REDIS_DB=1
LIGHTRAG_REDIS_PASSWORD=
```

## 5. 系统集成步骤

### 5.1 安装依赖

更新`requirements.txt`，添加LightRAG依赖：

```
lightrag-hku==0.1.0
```

### 5.2 配置文件修改

在`app/config.py`中添加LightRAG配置：

```python
# LightRAG配置
LIGHTRAG_ENABLED = os.getenv("LIGHTRAG_ENABLED", "false").lower() == "true"
LIGHTRAG_BASE_DIR = os.getenv("LIGHTRAG_BASE_DIR", os.path.join(DATA_DIR, "lightrag"))
LIGHTRAG_DEFAULT_EMBEDDING_DIM = int(os.getenv("LIGHTRAG_EMBEDDING_DIM", "1536"))
LIGHTRAG_MAX_TOKEN_SIZE = int(os.getenv("LIGHTRAG_MAX_TOKEN_SIZE", "8192"))

# LightRAG存储配置
LIGHTRAG_GRAPH_DB_TYPE = os.getenv("LIGHTRAG_GRAPH_DB_TYPE", "file")  # 可选: file, postgres, redis
LIGHTRAG_PG_HOST = os.getenv("LIGHTRAG_PG_HOST", "postgres")
LIGHTRAG_PG_PORT = int(os.getenv("LIGHTRAG_PG_PORT", "5432"))
LIGHTRAG_PG_USER = os.getenv("LIGHTRAG_PG_USER", "postgres")
LIGHTRAG_PG_PASSWORD = os.getenv("LIGHTRAG_PG_PASSWORD", "password")
LIGHTRAG_PG_DB = os.getenv("LIGHTRAG_PG_DB", "lightrag")
```

### 5.3 数据库迁移

运行以下命令创建必要的数据库表：

```bash
# 创建迁移脚本
alembic revision --autogenerate -m "Add LightRAG knowledge graph tables"

# 应用迁移
alembic upgrade head
```

### 5.4 启动服务

完成配置后，使用Docker Compose启动服务：

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 6. 存储模式选择

LightRAG支持三种存储模式，每种模式适用于不同的场景：

### 6.1 文件存储模式

- **配置**: `LIGHTRAG_GRAPH_DB_TYPE=file`
- **优点**: 设置简单，无需额外服务
- **缺点**: 不适合高并发或大规模生产环境
- **适用场景**: 开发、测试、小规模部署

### 6.2 PostgreSQL存储模式

- **配置**: `LIGHTRAG_GRAPH_DB_TYPE=postgres`
- **优点**: 高可靠性、支持复杂查询、适合大规模部署
- **缺点**: 需要额外维护PostgreSQL服务
- **适用场景**: 生产环境、大规模知识图谱、高并发访问

### 6.3 Redis存储模式

- **配置**: `LIGHTRAG_GRAPH_DB_TYPE=redis`
- **优点**: 高性能、快速查询、支持缓存
- **缺点**: 内存消耗大、持久化配置复杂
- **适用场景**: 需要高速查询的场景、临时数据处理

## 7. 多图谱架构

LightRAG支持创建和管理多个独立的知识图谱，每个图谱有自己的工作目录和配置：

### 7.1 目录结构

```
/app/data/lightrag/
├── graph1/       # 图谱1的工作目录
│   ├── kv_storage/
│   ├── vector_storage/
│   └── graph_storage/
├── graph2/       # 图谱2的工作目录
│   ├── kv_storage/
│   ├── vector_storage/
│   └── graph_storage/
└── ...
```

### 7.2 资源管理

对于多图谱部署，请考虑以下资源管理建议：

- 每个图谱约需要100MB-1GB的磁盘空间（取决于文档数量）
- 图谱加载时会占用内存，建议为每个活跃图谱预留500MB-2GB内存
- 大规模部署时考虑使用PostgreSQL存储，提高资源使用效率

## 8. 扩展部署

### 8.1 单机多容器

适用于中小规模部署，将LightRAG与主应用部署在同一台主机上：

```yaml
version: '3'

services:
  app:
    # 应用配置...
  
  lightrag-postgres:
    # PostgreSQL配置...
  
  redis:
    # Redis配置...
```

### 8.2 集群部署

适用于大规模生产环境，使用Docker Swarm或Kubernetes：

```yaml
# docker-compose.yml for Swarm mode
version: '3.8'

services:
  app:
    # 应用配置...
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
  
  lightrag-postgres:
    # PostgreSQL配置...
    deploy:
      placement:
        constraints:
          - node.role == worker
          - node.labels.storage == true
```

## 9. 性能优化建议

### 9.1 系统级优化

- 使用SSD存储以提高I/O性能
- 为PostgreSQL配置适当的内存和连接池
- 设置合理的工作线程数，避免资源竞争

### 9.2 配置优化

```
# 性能优化配置
LIGHTRAG_EMBEDDING_DIM=1536     # 嵌入维度，影响精度和资源消耗
LIGHTRAG_MAX_TOKEN_SIZE=8192    # 最大token数量，影响处理速度
LIGHTRAG_PG_POOL_SIZE=10        # PostgreSQL连接池大小
LIGHTRAG_MAX_WORKERS=4          # 文档处理工作线程数
```

## 10. 故障排除

### 10.1 常见问题

1. **启动失败**: 检查环境变量配置和存储服务是否可用
2. **内存溢出**: 减小批处理大小或增加容器内存限制
3. **查询超时**: 检查网络连接和数据库负载

### 10.2 日志检查

```bash
# 查看应用日志
docker-compose logs app

# 查看PostgreSQL日志
docker-compose logs lightrag-postgres
```

### 10.3 健康检查

访问健康检查API端点：`http://localhost:8000/api/health/lightrag`

## 11. 结论

LightRAG知识图谱的Docker部署为系统提供了强大的检索增强生成能力，通过选择合适的存储后端和配置参数，可以适应从小型测试到大规模生产环境的各种需求。

虽然可以不使用Docker部署LightRAG，但Docker部署方式提供了更好的隔离性、可移植性和资源管理，尤其适合生产环境。对于简单的开发测试，可以考虑使用直接的Python包集成方式。

## 12. 参考资料

- [LightRAG官方文档](https://github.com/HKUDS/LightRAG)
- [PostgreSQL官方文档](https://www.postgresql.org/docs/)
- [Docker官方文档](https://docs.docker.com/)
- [LlamaIndex集成文档](https://docs.llamaindex.ai/)
