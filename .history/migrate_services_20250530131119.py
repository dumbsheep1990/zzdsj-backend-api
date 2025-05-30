#!/usr/bin/env python3
"""
批量迁移services文件的脚本
按照重构计划将服务文件移动到对应的模块目录
"""

import os
import shutil
from pathlib import Path

# 迁移映射表
MIGRATION_MAP = {
    # 聊天模块
    "chat": {
        "chat_service.py": "chat_service.py",
        "conversation.py": "conversation_service.py", 
        "voice_service.py": "voice_service.py"
    },
    
    # 知识库模块
    "knowledge": {
        "unified_knowledge_service.py": "unified_service.py",
        "knowledge_service_legacy.py": "legacy_service.py",
        "knowledge_service_adapter.py": "adapter_service.py",
        "hybrid_search_service.py": "hybrid_search_service.py",
        "advanced_retrieval_service.py": "retrieval_service.py",
        "context_compression_service.py": "compression_service.py",
        "knowledge.py": "base_service.py"
    },
    
    # 知识库遗留模块
    "knowledge/legacy": {
        "knowledge_legacy.py": "legacy_service.py"
    },
    
    # 工具模块
    "tools": {
        "tool_service.py": "tool_service.py",
        "tool_execution_service.py": "execution_service.py",
        "base_tool_service.py": "base_service.py",
        "base_tools_service.py": "base_tools_service.py",
        "owl_tool_service.py": "owl_service.py",
        "unified_tool_service.py": "unified_service.py"
    },
    
    # 集成模块
    "integrations": {
        "integration.py": "framework_service.py",
        "mcp_integration_service.py": "mcp_service.py",
        "owl_integration_service.py": "owl_service.py",
        "lightrag_integration_service.py": "lightrag_service.py",
        "llamaindex_integration_service.py": "llamaindex_service.py"
    },
    
    # 模型模块
    "models": {
        "model_provider_service.py": "provider_service.py"
    },
    
    # 系统模块
    "system": {
        "system_config_service.py": "config_service.py",
        "async_system_config_service.py": "async_config_service.py",
        "settings_service.py": "settings_service.py",
        "framework_config_service.py": "framework_config_service.py"
    },
    
    # 认证和权限模块
    "auth": {
        "user_service.py": "user_service.py",
        "resource_permission_service.py": "permission_service.py"
    },
    
    # 监控模块
    "monitoring": {
        "monitoring_service.py": "monitoring_service.py"
    }
}

# 各模块的__init__.py内容
INIT_CONTENTS = {
    "chat": '''"""
聊天服务模块
负责聊天会话、对话管理和语音功能
"""

from .chat_service import ChatService
from .conversation_service import ConversationService
from .voice_service import VoiceService

__all__ = [
    "ChatService",
    "ConversationService",
    "VoiceService"
]''',

    "knowledge": '''"""
知识库服务模块
负责知识库管理、搜索和检索功能
"""

from .unified_service import UnifiedKnowledgeService
from .legacy_service import KnowledgeServiceLegacy
from .adapter_service import KnowledgeServiceAdapter
from .hybrid_search_service import HybridSearchService
from .retrieval_service import AdvancedRetrievalService
from .compression_service import ContextCompressionService
from .base_service import KnowledgeBase

__all__ = [
    "UnifiedKnowledgeService",
    "KnowledgeServiceLegacy", 
    "KnowledgeServiceAdapter",
    "HybridSearchService",
    "AdvancedRetrievalService",
    "ContextCompressionService",
    "KnowledgeBase"
]''',

    "tools": '''"""
工具服务模块
负责工具管理、执行和编排功能
"""

from .tool_service import ToolService
from .execution_service import ToolExecutionService
from .base_service import BaseToolService
from .base_tools_service import BaseToolsService
from .owl_service import OwlToolService
from .unified_service import UnifiedToolService

__all__ = [
    "ToolService",
    "ToolExecutionService",
    "BaseToolService",
    "BaseToolsService", 
    "OwlToolService",
    "UnifiedToolService"
]''',

    "integrations": '''"""
集成服务模块
负责第三方框架和协议集成
"""

from .framework_service import IntegrationService
from .mcp_service import MCPIntegrationService
from .owl_service import OwlIntegrationService
from .lightrag_service import LightragIntegrationService
from .llamaindex_service import LlamaindexIntegrationService

__all__ = [
    "IntegrationService",
    "MCPIntegrationService",
    "OwlIntegrationService",
    "LightragIntegrationService",
    "LlamaindexIntegrationService"
]''',

    "models": '''"""
模型服务模块
负责模型提供商管理和配置
"""

from .provider_service import ModelProviderService

__all__ = [
    "ModelProviderService"
]''',

    "system": '''"""
系统服务模块
负责系统配置和设置管理
"""

from .config_service import SystemConfigService
from .async_config_service import AsyncSystemConfigService
from .settings_service import SettingsService
from .framework_config_service import FrameworkConfigService

__all__ = [
    "SystemConfigService",
    "AsyncSystemConfigService",
    "SettingsService",
    "FrameworkConfigService"
]''',

    "auth": '''"""
认证和权限服务模块
负责用户管理和权限控制
"""

from .user_service import UserService
from .permission_service import ResourcePermissionService

__all__ = [
    "UserService",
    "ResourcePermissionService"
]''',

    "monitoring": '''"""
监控服务模块
负责系统监控和性能指标收集
"""

from .monitoring_service import MonitoringService

__all__ = [
    "MonitoringService"
]'''
}

def migrate_files():
    """执行文件迁移"""
    base_path = Path("app/services")
    
    for module, files in MIGRATION_MAP.items():
        module_path = base_path / module
        
        print(f"📁 处理模块: {module}")
        
        # 创建模块的__init__.py文件
        if module in INIT_CONTENTS:
            init_file = module_path / "__init__.py"
            if not init_file.exists():
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(INIT_CONTENTS[module])
                print(f"  ✅ 创建: {init_file}")
        
        # 迁移文件
        for source_file, target_file in files.items():
            source_path = base_path / source_file
            target_path = module_path / target_file
            
            if source_path.exists():
                try:
                    shutil.copy2(source_path, target_path)
                    print(f"  ✅ 迁移: {source_file} → {module}/{target_file}")
                except Exception as e:
                    print(f"  ❌ 错误: {source_file} → {e}")
            else:
                print(f"  ⚠️  文件不存在: {source_file}")

def main():
    print("🚀 开始迁移services文件...")
    migrate_files()
    print("\n📊 迁移完成！")

if __name__ == "__main__":
    main() 