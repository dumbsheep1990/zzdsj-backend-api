"""
Core模块
系统核心功能模块的统一入口
"""

# 智能体相关模块
from .agent_builder import AgentBuilder
from .agent_manager import AgentManager
from .agent_chain.chain_executor import ChainExecutor
from .agent_chain.message_router import MessageRouter

# 助手和聊天模块
from .assistant_qa import AssistantQAManager
from .chat_manager import ChatManager

# 服务管理模块
from .mcp_service import McpServiceManager
from .model_manager import ModelManager

# 配置和控制模块
from .nl_config import NLConfigParser
from .owl_controller import OwlController, OwlControllerExtensions
from .system_config import SystemConfigManager, ConfigValidator, ConfigEncryption

# 工具和搜索模块
from .searxng import SearxngManager
from .tool_orchestrator import ToolOrchestrator

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
    
    # 助手和聊天
    "AssistantQAManager",
    "ChatManager",
    
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
    
    # 工具和搜索
    "SearxngManager", 
    "ToolOrchestrator",
    
    # 语音（可选）
    "VoiceManager",
    "TextToSpeech", 
    "SpeechToText",
] 