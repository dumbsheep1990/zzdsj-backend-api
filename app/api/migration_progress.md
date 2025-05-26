# API层重构与迁移进度报告

## 概述

本文档记录了API层重构与迁移的进度情况。重构的目标是将原有的API文件按功能划分为不同模块，放置在frontend、admin和v1三个API层中。

## 迁移进度统计

- **总文件数**: 33
- **已迁移文件数**: 24
- **完成百分比**: 73%

## 已完成迁移的模块

### 1. 助手模块 (100% 完成)

- ✅ app/api/assistants.py → app/api/frontend/assistants/classic.py
- ✅ app/api/assistant.py → app/api/frontend/assistants/standard.py
- ✅ app/api/assistant_qa.py → app/api/frontend/assistants/qa.py

### 2. 知识库模块 (100% 完成)

- ✅ app/api/knowledge.py → app/api/frontend/knowledge/base.py
- ✅ app/api/knowledge_documents.py → app/api/frontend/knowledge/documents.py
- ✅ app/api/knowledge_chunks.py → app/api/frontend/knowledge/chunks.py
- ✅ app/api/knowledge_search.py → app/api/frontend/knowledge/search.py

### 3. 对话模块 (100% 完成)

- ✅ app/api/chat.py → app/api/frontend/chat/conversation.py

### 4. 搜索模块 (100% 完成)

- ✅ app/api/advanced_retrieval.py → app/api/frontend/search/advanced.py
- ✅ app/api/rerank_models.py → app/api/frontend/search/rerank.py

### 5. 工具模块 (100% 完成)

- ✅ app/api/base_tools.py → app/api/frontend/tools/base.py
- ✅ app/api/base_tools_history.py → app/api/frontend/tools/history.py
- ✅ app/api/tool.py → app/api/frontend/tools/manager.py
- ✅ app/api/unified_tool_api.py → app/api/frontend/tools/unified.py
- ✅ app/api/owl_tool.py → app/api/frontend/tools/owl.py

### 6. 用户模块 (100% 完成)

- ✅ app/api/user.py → app/api/frontend/user/manage.py
- ✅ app/api/auth.py → app/api/frontend/user/auth.py
- ✅ app/api/api_key.py → app/api/frontend/user/api_key.py
- ✅ app/api/frontend/user/profile.py (新文件)
- ✅ app/api/frontend/user/settings.py (新文件)
- ✅ app/api/frontend/user/preferences.py (新文件)

### 7. AI模型模块 (100% 完成)

- ✅ app/api/model_provider.py → app/api/frontend/ai/models/provider.py, app/api/frontend/ai/models/model.py

## 待迁移的模块

### 8. 系统模块 (0% 完成)

- ❌ app/api/system_config.py → app/api/frontend/system/config.py
- ❌ app/api/sensitive_word.py → app/api/frontend/system/sensitive_word.py

### 9. MCP服务模块 (0% 完成)

- ❌ app/api/mcp.py → app/api/frontend/mcp/client.py
- ❌ app/api/mcp_service.py → app/api/frontend/mcp/service.py

### 10. LightRAG模块 (0% 完成)

- ❌ app/api/lightrag.py → app/api/frontend/lightrag/service.py

### 11. 资源权限模块 (0% 完成)

- ❌ app/api/resource_permission.py → app/api/frontend/security/permissions.py

## 下一步计划

1. 迁移系统模块
2. 迁移MCP服务模块
3. 迁移LightRAG模块
4. 迁移资源权限模块
5. 更新API路由配置
6. 测试所有API接口
7. 更新文档 