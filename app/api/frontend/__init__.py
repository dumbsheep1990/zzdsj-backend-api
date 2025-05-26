"""
Frontend API - 前端API入口
专门为官方前端应用（Web端、移动端）提供的API接口
"""

from .router import router as frontend_router

__all__ = ["frontend_router"]

# API版本信息
API_VERSION = "frontend"
API_TITLE = "智政知识库问答系统 Frontend API"
API_DESCRIPTION = """
# 智政知识库问答系统 Frontend API

面向官方前端应用的API接口。

## 特点
- 🔐 **会话认证** - 基于Session/JWT的用户认证
- 🚀 **功能全面** - 支持前端所有功能需求
- ⚡ **实时交互** - WebSocket、SSE等实时通信
- 📁 **文件处理** - 完整的文件上传、处理流程
- 🔄 **状态管理** - 支持前端状态同步和管理
- 📊 **详细响应** - 返回前端需要的完整数据

## 核心功能模块

### 用户模块 (user/)
- **认证系统** - 登录、注册、找回密码
- **用户资料** - 头像、个人信息管理
- **用户设置** - 系统设置、通知偏好
- **个性化** - 主题、界面定制

### 工作空间模块 (workspace/)
- **项目管理** - 创建、管理多个项目
- **团队协作** - 邀请成员、权限管理
- **分享功能** - 内容分享、协作编辑
- **历史记录** - 操作历史、版本管理

### 知识库模块 (knowledge/)
- **知识库管理** - 创建、编辑、删除知识库
- **文档处理** - 上传、解析、索引文档
- **内容组织** - 文件夹、标签、分类管理
- **搜索查询** - 全文搜索、智能检索

### 助手模块 (assistants/)
- **助手创建** - 自定义AI助手
- **助手定制** - 个性化配置、能力设置
- **模板市场** - 预制助手模板
- **助手管理** - 编辑、分享、导入导出

### 聊天模块 (chat/)
- **对话管理** - 创建、管理聊天会话
- **消息处理** - 发送、接收、格式化消息
- **流式对话** - 实时流式响应
- **对话导出** - 保存、分享对话记录

### 多媒体模块 (media/)
- **文件上传** - 支持多种文件格式
- **语音功能** - 语音识别、语音合成
- **图像处理** - 图像理解、生成
- **文档处理** - PDF、Word等文档解析

## 认证方式

### JWT Token认证
```javascript
// 在请求头中包含JWT Token
headers: {
  'Authorization': 'Bearer YOUR_JWT_TOKEN'
}
```

### Session认证
```javascript
// 通过Cookie自动发送Session
// 无需特殊处理，浏览器自动携带
```

## 实时通信

### WebSocket连接
```javascript
// 连接WebSocket进行实时通信
const ws = new WebSocket('ws://api.example.com/frontend/ws');
```

### Server-Sent Events
```javascript
// 订阅实时事件
const eventSource = new EventSource('/frontend/events/stream');
```

## 错误处理
- **统一错误格式** - 标准化的错误响应
- **错误分类** - 区分业务错误、系统错误
- **国际化** - 支持多语言错误消息
- **友好提示** - 用户友好的错误提示

## 性能优化
- **数据缓存** - 智能缓存策略
- **分页加载** - 大数据集分页处理
- **懒加载** - 按需加载资源
- **压缩传输** - 响应数据压缩

## 开发支持
- 📧 前端技术支持：frontend-support@example.com
- 📚 前端开发文档：https://docs.example.com/frontend
- 💬 开发者群组：https://chat.example.com/frontend-dev
""" 