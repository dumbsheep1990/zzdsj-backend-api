# LightRAG API 服务部署指南

本指南说明如何在环境中部署和注册 LightRAG API 服务，以便与主系统集成。该服务已与主项目的配置系统集成，修改了配置管理方式，提供了Linux服务器环境下的部署脚本。

## 文件说明

- `docker-compose.yml`: LightRAG API 服务的 Docker 配置文件，已与主项目配置集成
- `.env.example`: 最小化的环境变量示例文件，仅包含必要的服务特定变量
- `start.sh`: 启动 LightRAG 服务的Linux脚本
- `stop.sh`: 停止 LightRAG 服务的Linux脚本
- `register_service.py`: 将 LightRAG 服务注册到 Nacos 服务发现系统的脚本，可从主项目获取配置
- `register_service.sh`: 启动 LightRAG 服务并注册到服务发现系统的Linux脚本

## 使用方法

### 准备工作

1. 确保已安装 Docker 和 Docker Compose
2. 确保已创建 Docker 网络（默认为 `zz-backend-network`）
   ```bash
   docker network create zz-backend-network
   ```
3. 如需必要，复制 `.env.example` 为 `.env` 并仅设置服务特定变量
   注意：主要配置将从主项目环境中自动继承

### 启动服务

方法一：仅启动 LightRAG 服务
```bash
# 给脚本添加执行权限
chmod +x start.sh
# 启动服务
./start.sh
```

方法二：启动 LightRAG 服务并注册到服务发现系统
```bash
# 给脚本添加执行权限
chmod +x register_service.sh
# 启动并注册服务
./register_service.sh
```

### 停止服务
```bash
# 给脚本添加执行权限
chmod +x stop.sh
# 停止服务
./stop.sh
```

## 服务验证

服务启动后，可通过以下URL验证服务状态：

- 健康检查：http://localhost:9621/health
- 接口文档：http://localhost:9621/docs

## 与现有系统集成

LightRAG API 已通过服务注册集成到了系统中，可以通过服务发现系统获取服务地址。在应用程序中，可以使用 `app.frameworks.lightrag.client.py` 中的 `LightRAGClient` 类与服务进行交互。

## 配置说明

本服务的配置采用多层次的方式：

1. **主项目配置**：主要配置从项目的 `app.config.settings` 中获取
2. **环境变量**：如果在主项目配置中找不到，则从环境变量中获取
3. **默认值**：如果上述两种方式都找不到，则使用默认值

### 关键配置参数

| 变量名 | 说明 | 默认值 |
|-------|------|-------|
| LIGHTRAG_PORT | 服务端口 | 9621 |
| LIGHTRAG_GRAPH_DB_TYPE | 图数据库类型(file/postgres/redis) | file |
| LIGHTRAG_DEFAULT_WORKDIR | 默认工作目录名 | default |
| LIGHTRAG_DATA_PATH | 存储数据的本地路径 | ./data |
| NETWORK_NAME | Docker网络名称 | zz-backend-network |

### 数据库配置

服务会自动从主项目中获取以下数据库配置：

- PostgreSQL：`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- Redis：`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`

## 简化的配置管理

该服务已经优化配置管理，实现了以下目标：

1. **配置集中化**：主要配置集中在主项目中，实现单一数据来源
2. **环境兼容性**：提供 Linux 环境下的脚本，适合生产部署
3. **动态工作目录**：支持前端动态创建工作目录

## 注意事项

1. 系统会使用主项目的数据库连接参数，无需重复配置
2. 设置 `LIGHTRAG_DATA_PATH` 可以自定义数据存储路径
3. 实际部署时建议使用持久化存储卷，如：
   ```yaml
   volumes:
     - /data/lightrag:/app/data/lightrag
   ```
