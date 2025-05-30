"""
数据模型模块初始化文件
导入所有数据库模型类以便统一管理和使用
"""

# 基础模型
from .database import Base
from .user import User, Role, Permission, UserRole, RolePermission, UserSettings, ApiKey
from .resource_permission import ResourcePermission, KnowledgeBaseAccess, AssistantAccess, ModelConfigAccess, MCPConfigAccess, UserResourceQuota

# 知识库系统
from .knowledge import KnowledgeBase, Document, DocumentChunk, AssistantKnowledgeBase

# 助手系统
from .assistant import Assistant
from .assistants import Assistant as AssistantV2  # 别名处理
from .assistant_knowledge_graph import AssistantKnowledgeGraph
from .assistant_qa import Question, QuestionDocumentSegment, QuestionFeedback, QuestionTag, AnswerMode

# 聊天系统
from .chat import Conversation, Message, MessageReference

# 工具系统
from .tool import Tool
from .tool_execution import ToolExecution
from .base_tools import BaseTool
from .unified_tool import UnifiedTool, ToolUsageStat
from .tool_chain import ToolChain, ToolChainExecution

# Agent系统
from .agent_definition import AgentDefinition
from .agent_template import AgentTemplate
from .agent_run import AgentRun
from .agent_chain import AgentChain, AgentChainExecution, AgentChainExecutionStep

# MCP服务系统
from .mcp import MCPServiceConfig, MCPTool, MCPToolExecution, AgentConfig, AgentTool

# 模型提供商
from .model_provider import ModelProvider, ModelInfo

# 系统配置
from .system_config import ConfigCategory, SystemConfig, ConfigHistory, ServiceHealthRecord

# 框架集成
from .lightrag_integration import LightRAGIntegration, LightRAGGraph, LightRAGQuery
from .llamaindex_integration import LlamaIndexIntegration
from .framework_config import FrameworkConfig

# OWL智能体
from .owl_agent import OWLAgent, OWLToolkit, OWLTool as OWLToolModel, OWLAgentMemory
from .owl_integration import OWLIntegration
from .owl_tool import OWLTool

# 上下文压缩
from .context_compression import ContextCompressionExecution
from .compression_strategy import CompressionStrategy

# 搜索系统
from .search import SearchSession, SearchResultCache

# 语音功能
from .voice import VoiceModel

# 内存系统
from .memory import Memory

# MCP集成
from .mcp_integration import MCPIntegration

__all__ = [
    # 基础模型
    "Base", "User", "Role", "Permission", "UserRole", "RolePermission", "UserSettings", "ApiKey",
    
    # 权限系统
    "ResourcePermission", "KnowledgeBaseAccess", "AssistantAccess", "ModelConfigAccess", 
    "MCPConfigAccess", "UserResourceQuota",
    
    # 知识库系统
    "KnowledgeBase", "Document", "DocumentChunk", "AssistantKnowledgeBase",
    
    # 助手系统
    "Assistant", "AssistantV2", "AssistantKnowledgeGraph",
    "Question", "QuestionDocumentSegment", "QuestionFeedback", "QuestionTag", "AnswerMode",
    
    # 聊天系统
    "Conversation", "Message", "MessageReference",
    
    # 工具系统
    "Tool", "ToolExecution", "BaseTool", "UnifiedTool", "ToolUsageStat",
    "ToolChain", "ToolChainExecution",
    
    # Agent系统
    "AgentDefinition", "AgentTemplate", "AgentRun",
    "AgentChain", "AgentChainExecution", "AgentChainExecutionStep",
    
    # MCP服务系统
    "MCPServiceConfig", "MCPTool", "MCPToolExecution", "AgentConfig", "AgentTool",
    
    # 模型提供商
    "ModelProvider", "ModelInfo",
    
    # 系统配置
    "ConfigCategory", "SystemConfig", "ConfigHistory", "ServiceHealthRecord",
    
    # 框架集成
    "LightRAGIntegration", "LightRAGGraph", "LightRAGQuery",
    "LlamaIndexIntegration", "FrameworkConfig",
    
    # OWL智能体
    "OWLAgent", "OWLToolkit", "OWLToolModel", "OWLAgentMemory",
    "OWLIntegration", "OWLTool",
    
    # 上下文压缩
    "ContextCompressionExecution", "CompressionStrategy",
    
    # 搜索系统
    "SearchSession", "SearchResultCache",
    
    # 语音功能
    "VoiceModel",
    
    # 内存系统
    "Memory",
    
    # MCP集成
    "MCPIntegration",
] 