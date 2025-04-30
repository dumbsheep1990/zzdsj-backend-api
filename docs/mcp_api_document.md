# MCP 自定义功能接口格式文档

以下文档详细说明了前端与后端MCP服务交互所需的接口参数。

## 一、自定义MCP服务接口

### 1. 服务器状态 (GET /api/mcp/server/status)

**请求参数**：无需参数

**响应格式**：
```json
{
  "name": "本地MCP服务器",
  "tools_count": 5,
  "resources_count": 3,
  "prompts_count": 2,
  "tools": ["tool1", "tool2", "tool3", "tool4", "tool5"],
  "resources": ["resource1", "resource2", "resource3"],
  "prompts": ["prompt1", "prompt2"],
  "is_running": true
}
```

### 2. 服务器重启 (POST /api/mcp/server/restart)

**请求参数**：无需参数

**响应格式**：
```json
{
  "status": "success",
  "message": "MCP服务器已成功重启"
}
```

### 3. 工具管理

#### 3.1 列出工具 (GET /api/mcp/tools)

**请求参数**：
- `category` (可选)：字符串，按类别筛选工具
- `tag` (可选)：字符串，按标签筛选工具

**响应格式**：
```json
[
  {
    "name": "weather_tool",
    "description": "获取天气信息",
    "category": "weather",
    "tags": ["气象", "天气预报"],
    "schema": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "城市名称"
        }
      },
      "required": ["city"]
    }
  }
]
```

#### 3.2 获取特定工具详情 (GET /api/mcp/tools/{name})

**请求参数**：
- `name` (必须)：字符串，工具名称

**响应格式**：与列出工具接口相同

#### 3.3 创建新工具 (POST /api/mcp/tools)

**请求参数**：
```json
{
  "name": "weather_tool",
  "description": "获取天气信息的工具",
  "category": "weather",
  "tags": ["气象", "天气预报"],
  "schema": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "城市名称"
      }
    },
    "required": ["city"]
  },
  "code": "async def weather_tool(city: str):\n    \"\"\"获取天气信息\"\"\"\n    # 实现获取天气的逻辑\n    return {\"temperature\": \"25°C\", \"condition\": \"晴\"}"
}
```

**必要参数**：
- `name`：工具名称
- `code`：工具的Python代码实现

**可选参数**：
- `description`：工具描述
- `category`：工具类别（默认为"general"）
- `schema`：工具的JSON Schema（如未提供，将从代码中推断）
- `tags`：工具标签列表

**响应格式**：与列出工具接口相同

### 4. 资源管理

#### 4.1 列出资源 (GET /api/mcp/resources)

**请求参数**：
- `category` (可选)：字符串，按类别筛选资源
- `tag` (可选)：字符串，按标签筛选资源

**响应格式**：
```json
[
  {
    "uri": "resource://weather/cities",
    "description": "全球主要城市列表",
    "category": "weather",
    "tags": ["城市", "地理"]
  }
]
```

#### 4.2 获取特定资源详情 (GET /api/mcp/resources/{uri})

**请求参数**：
- `uri` (必须)：字符串，资源URI

**响应格式**：与列出资源接口相同

#### 4.3 创建新资源 (POST /api/mcp/resources)

**请求参数**：
```json
{
  "uri": "resource://weather/cities",
  "description": "全球主要城市列表",
  "category": "weather",
  "tags": ["城市", "地理"],
  "code": "def get_cities():\n    \"\"\"返回城市列表\"\"\"\n    return [\"北京\", \"上海\", \"广州\", \"深圳\", \"杭州\"]"
}
```

**必要参数**：
- `uri`：资源URI
- `code`：资源的Python代码实现

**可选参数**：
- `description`：资源描述
- `category`：资源类别（默认为"general"）
- `tags`：资源标签列表

**响应格式**：与列出资源接口相同

### 5. 提示管理

#### 5.1 列出提示 (GET /api/mcp/prompts)

**请求参数**：
- `category` (可选)：字符串，按类别筛选提示
- `tag` (可选)：字符串，按标签筛选提示

**响应格式**：
```json
[
  {
    "name": "weather_prompt",
    "description": "天气查询提示",
    "category": "weather",
    "tags": ["天气", "提示"]
  }
]
```

#### 5.2 获取特定提示详情 (GET /api/mcp/prompts/{name})

**请求参数**：
- `name` (必须)：字符串，提示名称

**响应格式**：与列出提示接口相同

#### 5.3 创建新提示 (POST /api/mcp/prompts)

**请求参数**：
```json
{
  "name": "weather_prompt",
  "description": "天气查询提示",
  "category": "weather",
  "tags": ["天气", "提示"],
  "code": "def weather_prompt(city):\n    \"\"\"天气查询提示\"\"\"\n    return f\"请提供{city}的天气信息，包括温度和天气状况。\""
}
```

**必要参数**：
- `name`：提示名称
- `code`：提示的Python代码实现

**可选参数**：
- `description`：提示描述
- `category`：提示类别（默认为"general"）
- `tags`：提示标签列表

**响应格式**：与列出提示接口相同

### 6. 部署MCP服务 (POST /api/mcp/deploy)

**请求参数**：
```json
{
  "name": "天气服务",
  "description": "提供天气查询功能的MCP服务",
  "tools": ["weather_tool"],
  "resources": ["resource://weather/cities"],
  "prompts": ["weather_prompt"],
  "dependencies": ["fastmcp", "requests"],
  "enabled": true
}
```

**必要参数**：
- `name`：服务名称
- `tools`：要包含的工具名称列表
- `resources`：要包含的资源URI列表
- `prompts`：要包含的提示名称列表

**可选参数**：
- `description`：服务描述
- `dependencies`：依赖项列表（默认包含"fastmcp"）
- `enabled`：是否启用（默认为true）

**响应格式**：
```json
{
  "status": "success",
  "message": "MCP服务 天气服务 已成功部署",
  "deployment_id": "12345678-1234-5678-1234-567812345678",
  "deployment_url": "http://localhost:8000/mcp/12345678-1234-5678-1234-567812345678"
}
```

## 二、第三方MCP工具接口

### 1. 提供商管理

#### 1.1 列出提供商 (GET /api/mcp/providers)

**请求参数**：
- `capability` (可选)：字符串，按能力筛选提供商

**响应格式**：
```json
[
  {
    "id": "amap-api",
    "name": "高德地图",
    "description": "高德地图API服务",
    "provider": "amap",
    "capabilities": ["map", "navigation", "geocoding", "poi"],
    "requires_auth": true,
    "metadata": {
      "version": "1.0",
      "services": ["路线规划", "地址搜索", "周边兴趣点", "行政区划查询"]
    }
  }
]
```

#### 1.2 获取特定提供商详情 (GET /api/mcp/providers/{provider_id})

**请求参数**：
- `provider_id` (必须)：字符串，提供商ID

**响应格式**：与列出提供商接口相同

#### 1.3 注册新提供商 (POST /api/mcp/providers)

**请求参数**：
```json
{
  "id": "custom-ai",
  "name": "自定义AI服务",
  "provider": "custom",
  "api_url": "https://api.custom-ai.com/v1",
  "description": "自定义AI服务的MCP实现",
  "api_key": "your-api-key-here",
  "auth_type": "api_key",
  "capabilities": ["chat", "embedding"],
  "metadata": {
    "version": "1.0",
    "models": ["custom-model-1", "custom-model-2"]
  }
}
```

**必要参数**：
- `id`：提供商ID
- `name`：提供商名称
- `provider`：提供商类型
- `api_url`：API URL

**可选参数**：
- `description`：提供商描述
- `api_key`：API密钥
- `auth_type`：认证类型（默认为"api_key"）
- `capabilities`：能力列表
- `metadata`：元数据

**响应格式**：与列出提供商接口相同

#### 1.4 删除提供商 (DELETE /api/mcp/providers/{provider_id})

**请求参数**：
- `provider_id` (必须)：字符串，提供商ID

**响应格式**：
```json
{
  "status": "success",
  "message": "已删除MCP提供商: custom-ai"
}
```

### 2. 工具操作

#### 2.1 列出提供商工具 (GET /api/mcp/providers/{provider_id}/tools)

**请求参数**：
- `provider_id` (必须)：字符串，提供商ID
- `api_key` (可选)：字符串，API密钥

**响应格式**：
```json
[
  {
    "name": "weather",
    "description": "查询天气信息",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
          "description": "位置信息"
        }
      },
      "required": ["location"]
    }
  }
]
```

#### 2.2 测试提供商工具 (POST /api/mcp/providers/{provider_id}/tools/{tool_name}/test)

**请求参数**：
```json
{
  "tool_name": "weather",
  "parameters": {
    "location": "北京"
  },
  "timeout": 30,
  "context": {
    "user_id": "123",
    "session_id": "abc"
  }
}
```

**必要参数**：
- `tool_name`：工具名称
- `parameters`：工具参数

**可选参数**：
- `timeout`：超时时间（秒）
- `context`：上下文信息

**响应格式**：
```json
{
  "status": "success",
  "data": {
    "temperature": "25°C",
    "condition": "晴"
  },
  "metadata": {
    "latency": 0.5,
    "model": "gpt-3.5-turbo"
  }
}
```

### 3. 聊天功能 (POST /api/mcp/providers/{provider_id}/chat)

**请求参数**：
```json
{
  "messages": [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好，请介绍一下自己"}
  ],
  "model": "gpt-3.5-turbo",
  "temperature": 0.7,
  "max_tokens": 1000,
  "tools": [
    {
      "name": "weather",
      "description": "查询天气信息",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "位置信息"
          }
        },
        "required": ["location"]
      }
    }
  ],
  "stream": false
}
```

**必要参数**：
- `messages`：消息列表，每个消息包含`role`和`content`

**可选参数**：
- `model`：模型名称
- `temperature`：温度参数
- `max_tokens`：最大生成令牌数
- `tools`：可用工具列表
- `stream`：是否使用流式响应（默认为false）

**响应格式**（非流式）：
```json
{
  "id": "chat_12345",
  "created": 1714726568,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "你好！我是一个AI助手，我可以帮助回答问题、提供信息以及协助各种任务。有什么我可以帮你的吗？"
      },
      "finish_reason": "stop",
      "index": 0
    }
  ],
  "usage": {
    "prompt_tokens": 23,
    "completion_tokens": 45,
    "total_tokens": 68
  }
}
```

**响应格式**（流式，Server-Sent Events）：
```
data: {"id":"chat_12345","created":1714726568,"model":"gpt-3.5-turbo","choices":[{"delta":{"role":"assistant"},"index":0}]}

data: {"id":"chat_12345","created":1714726568,"model":"gpt-3.5-turbo","choices":[{"delta":{"content":"你好"},"index":0}]}

data: {"id":"chat_12345","created":1714726568,"model":"gpt-3.5-turbo","choices":[{"delta":{"content":"！"},"index":0}]}

data: {"id":"chat_12345","created":1714726568,"model":"gpt-3.5-turbo","choices":[{"delta":{"content":"我是"},"index":0}]}

...

data: [DONE]
```

## 三、状态码说明

- **200 OK**：请求成功
- **201 Created**：创建资源成功
- **400 Bad Request**：请求参数错误
- **401 Unauthorized**：未授权或API密钥无效
- **404 Not Found**：资源不存在
- **500 Internal Server Error**：服务器内部错误

