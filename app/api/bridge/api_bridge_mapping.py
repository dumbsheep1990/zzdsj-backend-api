"""
API桥接映射配置
定义原始API文件到新路径的映射关系
"""

# 映射格式: 
# "原始文件名（不含.py后缀）": {
#     "path": "新模块路径", 
#     "description": "API功能描述"
# }

API_BRIDGE_MAPPING = {
    "agent": {
        "path": "assistants.agent",
        "description": "智能体服务API: 提供智能体任务处理和工具调用的接口"
    },
    "api_key": {
        "path": "user.api_key",
        "description": "API密钥管理路由模块: 提供API密钥的创建、查询和管理功能"
    },
    "assistant_qa": {
        "path": "assistants.qa",
        "description": "问答助手管理API: 提供问答助手的CRUD操作和交互功能"
    },
    "assistant": {
        "path": "assistants.standard",
        "description": "助手API模块: 提供与AI助手交互的端点，支持各种模式（文本、图像、语音）和不同的接口格式"
    },
    "assistants": {
        "path": "assistants.classic",
        "description": "助手管理API模块: 提供助手资源的CRUD操作"
    },
    "auth": {
        "path": "user.auth",
        "description": "认证API模块: 提供用户认证、登录和令牌管理功能"
    },
    "base_tools_history": {
        "path": "tools.history",
        "description": "工具使用历史API: 提供工具使用历史记录的查询功能"
    },
    "base_tools": {
        "path": "tools.base",
        "description": "基础工具API: 提供系统基础工具的注册和调用功能"
    },
    "chat": {
        "path": "chat.conversations",
        "description": "聊天API模块: 提供聊天对话的创建和消息交互功能"
    },
    "knowledge": {
        "path": "knowledge.base",
        "description": "知识库管理API模块: 提供知识库及其文档的CRUD操作"
    },
    "lightrag": {
        "path": "knowledge.lightrag",
        "description": "LightRAG API模块: 提供LightRAG知识图谱增强检索服务的接口"
    },
    "mcp_service": {
        "path": "mcp.service",
        "description": "MCP服务管理API模块: 提供MCP服务的生命周期管理"
    },
    "mcp": {
        "path": "mcp.client",
        "description": "MCP服务和工具API模块: 提供自定义MCP服务和第三方MCP工具的REST API接口"
    },
    "model_provider": {
        "path": "ai.models.provider",
        "description": "模型提供商和模型信息API: 提供模型提供商和模型配置的管理功能"
    },
    "owl_tool": {
        "path": "tools.owl",
        "description": "OWL工具API: 提供OWL框架工具的管理和调用功能"
    },
    "rerank_models": {
        "path": "search.rerank",
        "description": "重排序模型API: 提供搜索结果重排序模型的管理和应用"
    },
    "resource_permission": {
        "path": "security.permissions",
        "description": "资源权限管理路由模块: 提供用户与各类资源之间权限关系的管理功能"
    },
    "search": {
        "path": "search.main",
        "description": "搜索API: 提供统一的搜索接口，支持知识库搜索和混合检索"
    },
    "sensitive_word": {
        "path": "system.sensitive_word",
        "description": "敏感词管理API模块: 提供敏感词的查询、添加、删除等功能"
    },
    "system_config": {
        "path": "system.config",
        "description": "系统配置API: 提供配置管理和系统自检API"
    },
    "tool": {
        "path": "tools.manager",
        "description": "工具管理API: 提供系统工具的注册、管理和调用功能"
    },
    "unified_tool_api": {
        "path": "tools.unified",
        "description": "统一工具API: 提供统一的工具调用接口"
    },
    "user": {
        "path": "user.manage",
        "description": "用户管理API: 提供用户账户的创建、查询和管理功能"
    },
    "voice": {
        "path": "voice.processing",
        "description": "语音API: 提供语音转文本和文本转语音的功能"
    },
    "advanced_retrieval": {
        "path": "search.advanced",
        "description": "高级检索API: 提供高级检索和混合检索功能"
    },
    "llamaindex_integration": {
        "path": "integrations.llamaindex",
        "description": "LlamaIndex集成API模块: 提供LlamaIndex框架集成的索引管理和查询操作"
    }
}
