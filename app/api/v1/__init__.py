"""
V1 API - 第三方对外API入口
专门为第三方开发者和外部系统集成者提供的API接口
"""

from fastapi import APIRouter

from app.api.v1.routes import (
    assistants,
    chat, 
    knowledge,
    model_provider,
    voice,
    mcp,
    assistant_qa,
    settings,
    lightrag
)

from .router import router as v1_router

__all__ = ["v1_router"]

# API版本信息
API_VERSION = "v1"
API_TITLE = "智政知识库问答系统 V1 API"
API_DESCRIPTION = """
# 智政知识库问答系统 V1 API

面向第三方开发者和外部系统集成者的API接口。

## 特点
- 🔑 **API密钥认证** - 基于API Key的安全认证
- 🚀 **简化接口** - 标准化的REST API，易于集成
- 📊 **限流保护** - 智能限流，保护系统稳定性
- 📖 **完整文档** - 详细的接口文档和示例代码
- 🔒 **数据安全** - 敏感信息脱敏，保护数据安全

## 核心功能
- **智能助手** - 调用各种AI助手进行对话和任务处理
- **知识查询** - 从知识库中查询和检索相关信息
- **AI能力** - 文本生成、向量化、分析等AI能力接口
- **工具调用** - 调用系统内置的各种工具和插件

## 认证方式
在请求头中包含API密钥：
```
Authorization: Bearer YOUR_API_KEY
```

## 限流说明
- 默认限制：1000次/小时
- 超出限制将返回429状态码
- 建议实现指数退避重试机制

## 支持
- 📧 技术支持：api-support@example.com
- 📚 开发者文档：https://docs.example.com/api/v1
- 💬 开发者社区：https://community.example.com
"""

# 创建主路由
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(assistants.router, prefix="/assistants", tags=["助手管理"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(model_provider.router, prefix="/models", tags=["模型管理"])
api_router.include_router(voice.router, prefix="/voice", tags=["语音服务"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["MCP工具链"])
api_router.include_router(assistant_qa.router, prefix="/assistant-qa", tags=["问答助手"])
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
api_router.include_router(lightrag.router, prefix="/lightrag", tags=["知识图谱"])
