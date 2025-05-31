"""
Core模块
系统核心功能模块的统一入口
"""

# 智能体相关模块
from .agent_builder import AgentBuilder
from .agent_manager import AgentManager
from .agent_chain.chain_executor import ChainExecutor
from .agent_chain.message_router import MessageRouter

# 新增：智能体核心业务逻辑模块
from .agents import (
    AgentManager as CoreAgentManager,
    ConversationManager as AgentConversationManager,
    MemoryManager,
    ToolManager as AgentToolManager,
    WorkflowManager,
    ChainManager,
    OwlAgentManager
)

# 助手和聊天模块
from .assistant_qa import AssistantQAManager
from .chat_manager import ChatManager

# 新增：聊天核心业务逻辑模块
from .chat.conversation_manager import ConversationManager

# 服务管理模块
from .mcp_service import McpServiceManager
from .model_manager import ModelManager

# 新增：集成管理模块
from .integrations import (
    MCPIntegrationManager,
    LlamaIndexIntegrationManager,
    LightRAGIntegrationManager,
    OwlIntegrationManager,
    FrameworkIntegrationManager
)

# 配置和控制模块
from .nl_config import NLConfigParser
from .owl_controller import OwlController, OwlControllerExtensions
from .system_config import SystemConfigManager, ConfigValidator, ConfigEncryption

# 认证授权模块
from .auth import UserManager, PermissionManager, AuthService

# 工具和搜索模块
from .searxng import SearxngManager
from .tool_orchestrator import ToolOrchestrator

# 新增：工具核心业务逻辑模块
from .tools import (
    ToolManager,
    ExecutionManager,
    RegistryManager
)

# 语音模块（如果存在__init__.py文件）
try:
    from .voice.voice_manager import VoiceManager
    from .voice.text_to_speech import TextToSpeech
    from .voice.speech_to_text import SpeechToText
except ImportError:
    pass

__all__ = [
    # 智能体相关
    "AgentBuilder",
    "AgentManager", 
    "ChainExecutor",
    "MessageRouter",
    
    # 智能体核心业务逻辑
    "CoreAgentManager",
    "AgentConversationManager",
    "MemoryManager",
    "AgentToolManager",
    "WorkflowManager",
    "ChainManager",
    "OwlAgentManager",
    
    # 助手和聊天
    "AssistantQAManager",
    "ChatManager",
    "ConversationManager",
    
    # 集成管理
    "MCPIntegrationManager",
    "LlamaIndexIntegrationManager", 
    "LightRAGIntegrationManager",
    "OwlIntegrationManager",
    "FrameworkIntegrationManager",
    
    # 服务管理
    "McpServiceManager",
    "ModelManager",
    
    # 配置和控制
    "NLConfigParser",
    "OwlController",
    "OwlControllerExtensions",
    "SystemConfigManager",
    "ConfigValidator", 
    "ConfigEncryption",
    
    # 认证授权
    "UserManager",
    "PermissionManager",
    "AuthService",
    
    # 工具和搜索
    "SearxngManager", 
    "ToolOrchestrator",
    "ToolManager",
    "ExecutionManager",
    "RegistryManager",
    
    # 语音（可选）
    "VoiceManager",
    "TextToSpeech", 
    "SpeechToText",
] 