"""
高级工具注册脚本 - 在应用启动时自动注册所有高级工具
"""

import logging
from fastapi import FastAPI
from typing import Dict, Any, List, Optional

from app.tools.advanced.adapters import register_advanced_tools
from app.config import settings

logger = logging.getLogger(__name__)

class ToolRegistry:
    """工具注册表，用于管理已注册的高级工具"""
    
    def __init__(self):
        """初始化注册表"""
        self.tools = {}
        self.is_initialized = False
    
    def initialize(self):
        """初始化注册所有工具"""
        if self.is_initialized:
            return
        
        try:
            # 注册所有高级工具
            self.tools = register_advanced_tools()
            self.is_initialized = True
            logger.info("高级工具注册成功")
        except Exception as e:
            logger.error(f"高级工具注册失败: {str(e)}")
    
    def get_owl_tools(self) -> Dict[str, Any]:
        """获取所有OWL工具"""
        if not self.is_initialized:
            self.initialize()
        return self.tools.get("owl", {})
    
    def get_agno_tools(self) -> Dict[str, Any]:
        """获取所有AGNO工具"""
        if not self.is_initialized:
            self.initialize()
        return self.tools.get("agno", {})
    
    def get_mcp_tools(self) -> Dict[str, Any]:
        """获取所有MCP工具"""
        if not self.is_initialized:
            self.initialize()
        return self.tools.get("mcp", {})
    
    def get_tool(self, framework: str, tool_name: str) -> Optional[Any]:
        """获取特定框架的特定工具"""
        if not self.is_initialized:
            self.initialize()
        return self.tools.get(framework, {}).get(tool_name)

# 创建单例实例
_tool_registry = None

def get_tool_registry() -> ToolRegistry:
    """获取工具注册表实例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry

def register_advanced_tools_on_startup(app: FastAPI):
    """在FastAPI应用启动时注册高级工具"""
    
    @app.on_event("startup")
    async def startup_register_tools():
        # 检查是否启用高级工具
        if getattr(settings, "ADVANCED_TOOLS_ENABLED", True):
            logger.info("正在注册高级工具...")
            registry = get_tool_registry()
            registry.initialize()
            logger.info(f"高级工具注册完成，共注册{len(registry.get_owl_tools())}个OWL工具，{len(registry.get_agno_tools())}个AGNO工具，{len(registry.get_mcp_tools())}个MCP工具")
        else:
            logger.info("高级工具已禁用，跳过注册")
    
    return startup_register_tools
