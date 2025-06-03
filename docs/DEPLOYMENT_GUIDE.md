# 智政知识库系统部署指南

## 📋 概述

智政知识库系统采用**双存储引擎架构**，无论在任何部署模式下，都要求以下两个组件作为基础必需服务：

- **🔍 Elasticsearch**: 文档分片存储和混合检索引擎
- **📁 MinIO**: 用户文件上传存储引擎

## 🎯 部署模式

### 最小化模式 (minimal)
**适用场景**: 开发环境、功能测试、资源受限环境

**必需服务**:
```
✅ PostgreSQL     - 基础关系数据库
✅ Elasticsearch  - 文档分片和混合检索引擎 (基础必需)
✅ MinIO          - 用户文件上传存储引擎 (基础必需)  
✅ Redis          - 缓存和会话存储
✅ RabbitMQ       - 异步任务消息队列
✅ Celery Worker  - 异步任务处理器
```

**资源需求**:
- 内存: 最少 4GB RAM
- 磁盘: 最少 20GB 可用空间
- CPU: 2核心以上

### 标准模式 (standard)
**适用场景**: 生产环境、完整功能需求

**服务组成**:
```
✅ 最小化模式的所有服务
✅ Milvus         - 高性能向量搜索引擎 (可选增强)
✅ Nacos          - 服务发现和配置中心
✅ MySQL          - Nacos专用数据库
✅ Flower         - Celery监控界面
```

**资源需求**:
- 内存: 最少 8GB RAM
- 磁盘: 最少 50GB 可用空间  
- CPU: 4核心以上

### 生产模式 (production)
**适用场景**: 生产环境、高可用需求

**服务组成**:
```
✅ 标准模式的所有服务
✅ InfluxDB       - 时序数据库 (性能监控)
✅ 完整监控系统    - 日志聚合、告警通知
✅ 安全增强       - 数据加密、审计日志
```

**资源需求**:
- 内存: 最少 16GB RAM
- 磁盘: 最少 100GB 可用空间
- CPU: 8核心以上

## 🚀 快速部署

### 1. 环境准备

**必需软件**:
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.8+

**检查环境**:
```bash
docker --version
docker-compose --version
python3 --version
```

### 2. 配置文件

复制环境变量模板：
```bash
cp env.example .env
```

**最小化配置 (.env)**:
```bash
# 部署模式
DEPLOYMENT_MODE=minimal

# 基础必需组件配置
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_HYBRID_SEARCH=true
ELASTICSEARCH_HYBRID_WEIGHT=0.7

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=knowledge-docs

# 其他配置...
```

### 3. 启动服务

**选择部署模式**:

```bash
# 最小化模式
docker-compose -f docker-compose.minimal.yml up -d

# 标准模式 (默认)
docker-compose up -d

# 生产模式
docker-compose -f docker-compose.yml up -d --scale celery-worker=3
```

### 4. 初始化核心存储

```bash
# 运行核心存储初始化
python3 scripts/init_core_storage.py

# 或使用一体化启动脚本
./scripts/start_with_hybrid_search.sh
```

### 5. 验证部署

```bash
# 验证存储系统
python3 scripts/validate_storage_system.py

# 检查服务状态
docker-compose ps
```

## 📊 核心存储架构

### 🔍 Elasticsearch (基础必需)

**作用**: 文档分片存储和混合检索引擎

**配置**:
```yaml
# 环境变量
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_HYBRID_SEARCH=true    # 强制启用
ELASTICSEARCH_HYBRID_WEIGHT=0.7     # 70%语义 + 30%关键词
ELASTICSEARCH_INDEX=document_index

# Docker配置
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - "ES_JAVA_OPTS=-Xms512m -Xmx512m"  # 最小化模式
    # - "ES_JAVA_OPTS=-Xms1g -Xmx1g"    # 标准模式
```

**功能特性**:
- ✅ 文档分片存储
- ✅ 全文索引检索  
- ✅ 语义向量搜索
- ✅ 混合检索算法
- ✅ 实时索引更新

### 📁 MinIO (基础必需)

**作用**: 用户文件上传存储引擎

**配置**:
```yaml
# 环境变量
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=knowledge-docs
MINIO_SECURE=false

# Docker配置
minio:
  image: minio/minio:RELEASE.2023-09-30T07-02-29Z
  command: server /data --console-address ":9001"
```

**存储结构**:
```
knowledge-docs/
├── documents/          # 原始文档文件
├── images/             # 图片文件
├── videos/             # 视频文件  
├── audios/             # 音频文件
├── temp/               # 临时文件 (30天自动清理)
├── processed/          # 处理后的文件
└── backups/            # 备份文件 (90天自动清理)
```

## 🔧 高级配置

### 环境变量配置

```bash
# ===== 部署模式 =====
DEPLOYMENT_MODE=standard              # minimal/standard/production

# ===== 核心存储引擎 (基础必需) =====
# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_HYBRID_SEARCH=true     # 强制启用混合检索
ELASTICSEARCH_HYBRID_WEIGHT=0.7      # 混合检索权重
ELASTICSEARCH_INDEX=document_index

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=knowledge-docs
MINIO_SECURE=false

# ===== 可选增强组件 =====
# Milvus (仅在 standard/production 模式启用)
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=document_vectors
MILVUS_ENABLED=true

# Nacos (仅在 standard/production 模式启用)
NACOS_SERVER_ADDRESSES=127.0.0.1:8848
NACOS_NAMESPACE=public
NACOS_GROUP=DEFAULT_GROUP
NACOS_ENABLED=true

# ===== AI模型配置 =====
OPENAI_API_KEY=your-openai-api-key
EMBEDDING_MODEL=text-embedding-ada-002
CHAT_MODEL=gpt-3.5-turbo
```

### 性能调优

**Elasticsearch 性能优化**:
```yaml
elasticsearch:
  environment:
    # 内存设置 (标准模式)
    - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    
    # 内存设置 (生产模式)  
    - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    
    # 禁用安全功能 (开发环境)
    - xpack.security.enabled=false
  
  # 资源限制
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '1.0'
```

**MinIO 性能优化**:
```yaml
minio:
  environment:
    # 访问日志
    - MINIO_BROWSER_REDIRECT_URL=http://localhost:9001
    
    # 并发设置
    - MINIO_API_REQUESTS_MAX=1000
    
  # 资源限制
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '0.5'
```

## 🛠️ 运维管理

### 服务监控

**健康检查**:
```bash
# Elasticsearch健康状态
curl http://localhost:9200/_cluster/health

# MinIO健康状态  
curl http://localhost:9000/minio/health/live

# 系统整体状态
python3 scripts/validate_storage_system.py
```

**性能监控**:
```bash
# Flower监控界面
http://localhost:5555

# MinIO控制台
http://localhost:9001

# Elasticsearch监控
curl http://localhost:9200/_cat/indices?v
```

### 数据备份

**MinIO备份**:
```bash
# 导出MinIO数据
docker run --rm -v minio_data:/data -v /backup:/backup \
  alpine tar czf /backup/minio_backup_$(date +%Y%m%d).tar.gz /data
```

**Elasticsearch备份**:
```bash
# 创建快照
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_$(date +%Y%m%d)" \
  -H 'Content-Type: application/json'
```

### 故障排除

**常见问题**:

1. **Elasticsearch启动失败**
   ```bash
   # 检查内存限制
   docker stats elasticsearch
   
   # 查看日志
   docker-compose logs elasticsearch
   
   # 重置数据 (谨慎使用)
   docker volume rm zzdsj_elasticsearch_data
   ```

2. **MinIO连接失败**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep 9000
   
   # 查看日志
   docker-compose logs minio
   
   # 重启服务
   docker-compose restart minio
   ```

3. **混合检索不工作**
   ```bash
   # 验证配置
   python3 scripts/validate_hybrid_search.py
   
   # 重新初始化
   python3 scripts/init_elasticsearch.py
   ```

## 📚 相关文档

- [存储架构指南](STORAGE_ARCHITECTURE_GUIDE.md)
- [混合检索配置](HYBRID_SEARCH_GUIDE.md)
- [API文档](../api-docs/)
- [Docker Compose参考](../docker-compose.yml)

## ⚠️ 重要提醒

1. **基础必需组件**: Elasticsearch和MinIO是系统核心，缺少任一组件将导致系统无法正常工作
2. **混合检索强制启用**: 系统默认强制启用混合检索功能，这是核心特性不建议禁用
3. **数据持久化**: 确保Docker volume正确配置，避免数据丢失
4. **安全设置**: 生产环境请修改默认密码和密钥
5. **资源监控**: 定期监控存储空间和性能指标

---

**🎉 部署成功标志**:
- ✅ Elasticsearch集群状态为green或yellow
- ✅ MinIO服务正常响应且存储桶已创建
- ✅ 混合检索功能正常工作
- ✅ 文件上传功能正常工作
- ✅ 系统整体验证通过 