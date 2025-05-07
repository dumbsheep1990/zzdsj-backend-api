# MCP服务管理API文档

本文档详细描述了MCP（Model Context Protocol）服务的REST API接口设计与使用方法。

## 1. 基本信息

- 基础路径: `/api/mcp-services`
- 内容类型: `application/json`
- 认证方式: 基于Token的认证（在HTTP头中使用`Authorization: Bearer <token>`）

## 2. 通用响应结构

所有API响应均遵循以下格式：

```json
{
  "status": "string",  // "success" 或 "error"
  "data": {},          // 请求成功时返回的数据对象
  "error": {           // 请求失败时返回的错误信息
    "code": "string",  // 错误代码
    "message": "string" // 错误描述
  }
}
```

## 3. MCP服务管理

### 3.1 获取MCP服务列表

获取所有已配置的MCP服务列表。

- **URL**: `/api/mcp-services`
- **方法**: `GET`
- **查询参数**:
  - `status` (可选): 按服务状态筛选（"running", "stopped", "error"）
  - `category` (可选): 按服务类别筛选
  - `page` (可选): 分页页码，默认1
  - `limit` (可选): 每页数量，默认20
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "services": [
        {
          "deployment_id": "string",
          "name": "string",
          "description": "string",
          "version": "string",
          "status": "string",
          "created_at": "string",
          "updated_at": "string",
          "url": "string",
          "tool_count": 0
        }
      ],
      "total": 0,
      "page": 1,
      "limit": 20
    }
    ```

### 3.2 获取MCP服务详情

获取指定MCP服务的详细信息。

- **URL**: `/api/mcp-services/{deployment_id}`
- **方法**: `GET`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "deployment_id": "string",
      "name": "string",
      "description": "string",
      "version": "string",
      "status": "string",
      "created_at": "string",
      "updated_at": "string",
      "url": "string",
      "docker_config": {
        "container_name": "string",
        "image": "string",
        "port": 0,
        "host_port": 0,
        "env": {},
        "volumes": [],
        "restart_policy": "string",
        "resource_limits": {
          "cpu": "string",
          "memory": "string"
        }
      },
      "tools": [
        {
          "name": "string",
          "description": "string",
          "category": "string"
        }
      ]
    }
    ```

### 3.3 创建MCP服务

创建新的MCP服务配置。

- **URL**: `/api/mcp-services`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "name": "string",
    "description": "string",
    "version": "string",
    "image": "string",
    "port": 0,
    "host_port": 0,
    "env": {},
    "volumes": [],
    "restart_policy": "string",
    "resource_limits": {
      "cpu": "string",
      "memory": "string"
    }
  }
  ```
- **成功响应**:
  - 状态码: `201 Created`
  - 响应体:
    ```json
    {
      "deployment_id": "string",
      "name": "string",
      "status": "created"
    }
    ```

### 3.4 更新MCP服务

更新已有的MCP服务配置。

- **URL**: `/api/mcp-services/{deployment_id}`
- **方法**: `PUT`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **请求体**:
  ```json
  {
    "name": "string",
    "description": "string",
    "version": "string",
    "image": "string",
    "port": 0,
    "host_port": 0,
    "env": {},
    "volumes": [],
    "restart_policy": "string",
    "resource_limits": {
      "cpu": "string",
      "memory": "string"
    }
  }
  ```
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "deployment_id": "string",
      "name": "string",
      "status": "updated"
    }
    ```

### 3.5 删除MCP服务

删除指定的MCP服务。

- **URL**: `/api/mcp-services/{deployment_id}`
- **方法**: `DELETE`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "status": "success",
      "message": "MCP服务已成功删除"
    }
    ```

### 3.6 启动MCP服务

启动指定的MCP服务。

- **URL**: `/api/mcp-services/{deployment_id}/start`
- **方法**: `POST`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "status": "success",
      "deployment_id": "string",
      "message": "MCP服务启动成功"
    }
    ```

### 3.7 停止MCP服务

停止指定的MCP服务。

- **URL**: `/api/mcp-services/{deployment_id}/stop`
- **方法**: `POST`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "status": "success",
      "deployment_id": "string",
      "message": "MCP服务停止成功"
    }
    ```

### 3.8 重启MCP服务

重启指定的MCP服务。

- **URL**: `/api/mcp-services/{deployment_id}/restart`
- **方法**: `POST`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "status": "success",
      "deployment_id": "string",
      "message": "MCP服务重启成功"
    }
    ```

### 3.9 获取MCP服务日志

获取指定MCP服务的日志。

- **URL**: `/api/mcp-services/{deployment_id}/logs`
- **方法**: `GET`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **查询参数**:
  - `tail` (可选): 返回最近的日志行数，默认100
  - `since` (可选): 返回自指定时间以来的日志，格式为ISO8601
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "deployment_id": "string",
      "logs": "string",
      "timestamp": "string"
    }
    ```

### 3.10 获取MCP服务健康状态

检查指定MCP服务的健康状态。

- **URL**: `/api/mcp-services/{deployment_id}/health`
- **方法**: `GET`
- **路径参数**:
  - `deployment_id`: MCP服务的部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "deployment_id": "string",
      "status": "string",
      "uptime": 0,
      "details": {}
    }
    ```

## 4. MCP工具管理

### 4.1 获取工具列表

获取所有MCP工具列表。

- **URL**: `/api/mcp-services/tools`
- **方法**: `GET`
- **查询参数**:
  - `deployment_id` (可选): 按部署ID筛选
  - `category` (可选): 按工具类别筛选
  - `page` (可选): 分页页码，默认1
  - `limit` (可选): 每页数量，默认20
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "tools": [
        {
          "name": "string",
          "description": "string",
          "category": "string",
          "deployment_id": "string",
          "service_name": "string"
        }
      ],
      "total": 0,
      "page": 1,
      "limit": 20
    }
    ```

### 4.2 获取工具Schema

获取指定工具的参数Schema。

- **URL**: `/api/mcp-services/tools/{tool_name}/schema`
- **方法**: `GET`
- **路径参数**:
  - `tool_name`: 工具名称
- **查询参数**:
  - `deployment_id` (必选): 部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "type": "object",
      "properties": {
        "param1": {
          "type": "string",
          "description": "参数1的描述"
        },
        "param2": {
          "type": "integer",
          "description": "参数2的描述"
        }
      },
      "required": ["param1"]
    }
    ```

### 4.3 获取工具使用示例

获取指定工具的使用示例。

- **URL**: `/api/mcp-services/tools/{tool_name}/examples`
- **方法**: `GET`
- **路径参数**:
  - `tool_name`: 工具名称
- **查询参数**:
  - `deployment_id` (必选): 部署ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    [
      {
        "param1": "示例值1",
        "param2": 123
      },
      {
        "param1": "示例值2",
        "param2": 456
      }
    ]
    ```

### 4.4 调用MCP工具

直接调用指定的MCP工具。

- **URL**: `/api/mcp-services/tools/{tool_name}/invoke`
- **方法**: `POST`
- **路径参数**:
  - `tool_name`: 工具名称
- **查询参数**:
  - `deployment_id` (必选): 部署ID
- **请求体**:
  ```json
  {
    "params": {
      "param1": "value1",
      "param2": 123
    },
    "metadata": {
      "caller_id": "string",
      "session_id": "string"
    }
  }
  ```
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体: 工具执行结果，结构视工具而定

## 5. LlamaIndex集成

### 5.1 获取支持LlamaIndex的工具列表

获取所有已适配到LlamaIndex的MCP工具列表。

- **URL**: `/api/mcp-services/llamaindex/tools`
- **方法**: `GET`
- **查询参数**:
  - `category` (可选): 按工具类别筛选
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "tools": [
        {
          "name": "string",
          "description": "string",
          "category": "string",
          "deployment_id": "string",
          "service_name": "string",
          "parameters": {}
        }
      ]
    }
    ```

### 5.2 为助手配置工具

为指定助手配置可用的MCP工具。

- **URL**: `/api/assistant-qa/{assistant_id}/tools`
- **方法**: `POST`
- **路径参数**:
  - `assistant_id`: 助手ID
- **请求体**:
  ```json
  {
    "tools": [
      {
        "tool_name": "string",
        "deployment_id": "string",
        "enabled": true
      }
    ]
  }
  ```
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "assistant_id": "string",
      "tools": [
        {
          "tool_name": "string",
          "deployment_id": "string",
          "enabled": true
        }
      ]
    }
    ```

### 5.3 获取助手已配置工具

获取指定助手已配置的MCP工具列表。

- **URL**: `/api/assistant-qa/{assistant_id}/tools`
- **方法**: `GET`
- **路径参数**:
  - `assistant_id`: 助手ID
- **成功响应**:
  - 状态码: `200 OK`
  - 响应体:
    ```json
    {
      "assistant_id": "string",
      "tools": [
        {
          "tool_name": "string",
          "deployment_id": "string",
          "enabled": true,
          "description": "string",
          "category": "string"
        }
      ]
    }
    ```

## 6. 错误码说明

| 错误码 | 描述 | HTTP状态码 |
|--------|------|------------|
| MCP001 | MCP服务不存在 | 404 |
| MCP002 | 容器启动失败 | 500 |
| MCP003 | 容器操作超时 | 504 |
| MCP004 | 工具不存在 | 404 |
| MCP005 | 工具调用失败 | 500 |
| MCP006 | 参数验证失败 | 400 |
| MCP007 | MCP服务健康检查失败 | 503 |
| MCP008 | 服务状态错误 | 409 |

## 7. 最佳实践

### 7.1 工具调用示例

使用Python调用MCP工具的示例代码：

```python
import httpx
import json

async def call_mcp_tool(tool_name, deployment_id, params):
    url = f"http://your-api-host/api/mcp-services/tools/{tool_name}/invoke?deployment_id={deployment_id}"
    
    payload = {
        "params": params,
        "metadata": {
            "caller_id": "your-app",
            "session_id": "user-session-123"
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, 
            json=payload,
            headers={
                "Authorization": "Bearer your-token",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API调用失败: {response.text}")

# 使用示例
result = await call_mcp_tool(
    tool_name="calculator",
    deployment_id="mcp-math-1",
    params={
        "operation": "add",
        "a": 5,
        "b": 3
    }
)
print(result)  # 输出: {"result": 8}
```

### 7.2 服务生命周期管理

MCP服务的生命周期管理最佳实践：

1. 创建服务前，确保Docker镜像已存在并可访问
2. 服务启动后立即进行健康检查
3. 定期检查服务状态，保持服务可用性
4. 在服务更新前先停止现有服务
5. 删除服务前务必先停止服务
6. 记录服务日志，便于问题诊断

### 7.3 性能优化

1. 使用适当的资源限制（CPU、内存）避免资源过度使用
2. 合理设置超时时间，避免长时间运行的工具阻塞系统
3. 对高频调用的工具考虑添加缓存机制
4. 对大型响应数据考虑分页或流式返回

## 8. 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| v1.0 | 2023-07-01 | 初始版本 |
| v1.1 | 2023-08-15 | 添加工具调用历史记录功能 |
| v1.2 | 2023-09-30 | 添加LlamaIndex集成支持 |
