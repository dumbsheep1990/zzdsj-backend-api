# Token计算与统计功能实现文档

**日期**: 2025-05-06

## 1. 概述

本文档记录了Token计算与统计功能的实现过程及结果。该功能作为后置工具，用于计算和统计LLM调用中消耗的token数量，并将相关数据存储到InfluxDB时序数据库中。该功能支持关联用户、模型、时间、执行时间、对话ID等多维度数据，可以通过前端系统设置进行配置控制。

## 2. 实现内容

### 2.1 新增文件

1. **Token计算与统计工具**
   - `app/utils/token_metrics.py`: Token计算与统计核心工具类
   - `app/middleware/token_metrics_middleware.py`: Token统计后置处理中间件

2. **系统设置功能**
   - `app/schemas/settings.py`: 系统设置相关Pydantic模型
   - `app/services/settings_service.py`: 系统设置管理服务
   - `app/api/settings.py`: 系统设置API接口

3. **异步Redis客户端**
   - `app/utils/async_redis_client.py`: 支持异步操作的Redis客户端

### 2.2 修改文件

1. **配置文件**
   - `config.yaml`: 添加InfluxDB时序数据库配置
   - `app/config.py`: 添加InfluxDB相关配置支持

2. **主应用程序**
   - `main.py`: 注册系统设置API路由

3. **对话服务**
   - `app/core/chat/chat_service.py`: 集成Token统计中间件

4. **依赖管理**
   - `requirements.txt`: 添加InfluxDB客户端和tiktoken库

## 3. 核心功能

### 3.0 中间件目录详细说明

`app/middleware`目录包含了Token统计后置处理中间件的实现。中间件是用于在请求处理流程中进行额外处理的函数或类，它们可以在请求处理前后执行特定的操作。在本项目中，中间件用于实现Token统计功能。

#### 3.0.1 token_metrics_middleware.py

这个文件实现了Token统计的后置处理中间件，它的主要功能包括：

1. **异步Token统计装饰器**：
   ```python
   @async_token_metrics(user_id_key="user_id", model_name_key="model_name")
   async def my_chat_function(user_id, model, messages, ...):
       # 对话函数实现...
       return response
   ```
   该装饰器会在被装饰的函数执行完毕后，异步地计算并记录Token使用情况，不影响主流程的执行速度。

2. **手动调用接口**：
   ```python
   await TokenMetricsMiddleware.record_usage(
       user_id=user_id,
       model_name=model_name,
       messages=messages,
       response_text=response,
       conversation_id=conversation_id
   )
   ```
   提供了静态方法可以在任何地方手动调用，适用于不便使用装饰器的场景。

3. **异常安全处理**：所有异常都会被捕获并记录日志，确保不会影响主对话流程。

4. **灵活的参数提取**：能够自动从被装饰函数的参数、关键字参数和返回值中提取所需信息。

5. **支持开关控制**：根据系统设置决定是否执行Token统计，即使统计功能关闭，也会记录基本会话信息。

此中间件是本次实现的Token统计功能的核心组件，它通过后置处理方式，确保了Token统计功能不会影响系统的主要功能流程。

### 3.1 Token计算功能

Token计算功能通过`TokenCounter`类实现，支持多种模型的token计算：

```python
class TokenCounter:
    """Token计数器，支持多种模型的Token计算"""
    
    # 模型到编码器的映射
    MODEL_TO_ENCODING = {
        # OpenAI模型
        "gpt-3.5-turbo": "cl100k_base",
        "gpt-4": "cl100k_base",
        # 其他模型...
    }

    @classmethod
    def count_tokens(cls, text: str, model_name: str = "gpt-3.5-turbo") -> int:
        """计算文本的token数量"""
        # 实现细节...

    @classmethod
    def count_messages_tokens(cls, messages: List[Dict[str, str]], model_name: str = "gpt-3.5-turbo") -> int:
        """计算消息列表的token数量"""
        # 实现细节...
```

### 3.2 InfluxDB集成

通过`InfluxDBMetricsClient`类实现与InfluxDB的集成：

```python
class InfluxDBMetricsClient:
    """InfluxDB指标客户端，用于存储Token计算结果"""
    
    async def write_metrics(self, 
                           user_id: str,
                           model_name: str, 
                           input_tokens: int,
                           output_tokens: int,
                           conversation_id: Optional[str] = None,
                           execution_time: Optional[float] = None,
                           additional_tags: Optional[Dict[str, str]] = None,
                           additional_fields: Optional[Dict[str, Any]] = None):
        """异步写入指标数据"""
        # 实现细节...
```

### 3.3 中间件实现

通过装饰器和中间件类实现Token统计的后置处理：

```python
def async_token_metrics(user_id_key: str = "user_id", 
                      model_name_key: str = "model_name",
                      conversation_id_key: str = "conversation_id"):
    """异步Token统计装饰器"""
    # 实现细节...

class TokenMetricsMiddleware:
    """Token计算与统计中间件"""
    
    @staticmethod
    async def record_usage(user_id: str,
                          model_name: str,
                          messages: List[Dict[str, str]],
                          response_text: str,
                          conversation_id: Optional[str] = None,
                          execution_time: Optional[float] = None,
                          **kwargs):
        """记录Token使用情况"""
        # 实现细节...
```

### 3.4 系统设置管理

通过`SystemSettingsService`实现系统设置的管理：

```python
class SystemSettingsService(SettingsService[SystemSettings]):
    """系统设置服务，专门用于管理系统级别设置"""
    
    def __init__(self):
        """初始化系统设置服务"""
        # 从系统配置获取默认值
        default_settings = {
            "metrics": {
                "enabled": settings.metrics.enabled,
                "token_statistics": settings.metrics.token_statistics
            }
        }
        # 实现细节...
```

### 3.5 API接口

创建系统设置API接口，支持前端控制Token统计功能：

```python
@router.get("/metrics", response_model=MetricsSettings)
async def get_metrics_settings():
    """获取指标统计设置"""
    # 实现细节...

@router.patch("/metrics", response_model=MetricsSettings)
async def update_metrics_settings(settings_update: MetricsSettings):
    """更新指标统计设置"""
    # 实现细节...
```

## 4. 配置选项

### 4.1 InfluxDB配置

在`config.yaml`中添加了InfluxDB相关配置：

```yaml
metrics:
  enabled: true
  provider: influxdb
  token_statistics: true  # 是否开启token统计功能
  influxdb:
    url: http://localhost:8086
    token: ""  # 填入InfluxDB API token
    org: knowledge_qa_org
    bucket: llm_metrics
    batch_size: 50
    flush_interval: 10  # 数据写入间隔(秒)
```

### 4.2 系统设置模型

通过Pydantic模型定义系统设置结构：

```python
class MetricsSettings(BaseModel):
    """指标统计设置"""
    enabled: bool = Field(default=True, description="是否启用指标统计")
    token_statistics: bool = Field(default=True, description="是否启用token统计")

class SystemSettings(BaseModel):
    """系统设置"""
    metrics: Optional[MetricsSettings] = None
```

## 5. 集成方式

### 5.1 对话服务集成

在对话服务中集成Token统计中间件：

```python
# 异步记录Token使用统计
await TokenMetricsMiddleware.record_usage(
    user_id=str(assistant.user_id),
    model_name=model_name,
    messages=complete_messages,
    response_text=response,
    conversation_id=str(conversation_history[0].conversation_id if conversation_history else "unknown"),
    assistant_id=str(assistant.id),
    assistant_name=assistant.name,
    references_count=len(references_formatted)
)
```

### 5.2 装饰器方式

可以使用装饰器方式集成到任何对话函数：

```python
@async_token_metrics(user_id_key="user_id", model_name_key="model_name")
async def chat_function(user_id: str, model_name: str, messages: List[Dict], **kwargs):
    # 函数实现...
    return {"response": "模型回复内容"}
```

## 6. 依赖库

实现该功能需要添加以下依赖库：

```text
influxdb-client==1.37.0
tiktoken==0.5.1
```

## 7. 总结

本次实现的Token计算与统计功能作为所有对话类型的后置异步统计工具，具有以下特点：

1. **非侵入性**：作为后置处理，不影响核心对话流程
2. **异步处理**：使用异步方式处理，不阻塞主流程
3. **容错设计**：即使统计功能失败，不影响主要功能
4. **可配置性**：支持通过前端系统设置控制功能开关
5. **多维统计**：支持关联用户、模型、对话ID等多维度数据

该功能将帮助系统管理员更好地了解和优化模型使用情况，为资源规划和成本控制提供数据支持。
