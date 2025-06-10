"""
统一工具注册中心
集成多个框架适配器，提供统一的工具注册、发现和执行接口
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..abstractions import (
    ToolSpec, ToolResult, ToolStatus, ToolCategory, ToolExecutionContext
)
from ..adapters import BaseToolAdapter, AgnoToolAdapter, LlamaIndexToolAdapter, OwlToolAdapter, FastMCPToolAdapter, HaystackToolAdapter


class ToolRegistryError(Exception):
    """工具注册表错误"""
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.error_code = error_code


class UnifiedToolRegistry:
    """统一工具注册中心 - 管理多框架工具"""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # 框架适配器注册表
        self._adapters: Dict[str, BaseToolAdapter] = {}
        
        # 工具注册表 - 按框架组织
        self._tools_by_provider: Dict[str, Dict[str, ToolSpec]] = {}
        
        # 工具注册表 - 按分类组织
        self._tools_by_category: Dict[ToolCategory, Dict[str, ToolSpec]] = {}
        
        # 全局工具索引
        self._global_tools: Dict[str, ToolSpec] = {}
        
        # 执行状态跟踪
        self._execution_status: Dict[str, ToolStatus] = {}
        
        # 统计信息
        self._stats = {
            "total_tools": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "frameworks_count": 0
        }
        
        self._initialized = False
    
    async def initialize(self) -> bool:
        """初始化注册中心"""
        try:
            # 注册默认框架适配器
            await self._register_default_adapters()
            
            # 初始化所有适配器
            await self._initialize_adapters()
            
            # 发现并注册所有工具
            await self._discover_and_register_all_tools()
            
            self._initialized = True
            self._logger.info("Unified tool registry initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize unified tool registry: {e}")
            raise ToolRegistryError(f"Initialization failed: {e}", "INIT_ERROR")
    
    async def shutdown(self) -> bool:
        """关闭注册中心"""
        try:
            # 关闭所有适配器
            for adapter in self._adapters.values():
                await adapter.shutdown()
            
            # 清理状态
            self._adapters.clear()
            self._tools_by_provider.clear()
            self._tools_by_category.clear()
            self._global_tools.clear()
            self._execution_status.clear()
            
            self._initialized = False
            self._logger.info("Unified tool registry shutdown successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to shutdown unified tool registry: {e}")
            return False
    
    async def _register_default_adapters(self):
        """注册默认框架适配器"""
        # 注册Agno适配器
        agno_adapter = AgnoToolAdapter()
        await self.register_adapter("agno", agno_adapter)
        
        # 注册LlamaIndex适配器
        llamaindex_adapter = LlamaIndexToolAdapter()
        await self.register_adapter("llamaindex", llamaindex_adapter)
        
        # 注册OWL适配器
        owl_adapter = OwlToolAdapter()
        await self.register_adapter("owl", owl_adapter)
        
        # 注册FastMCP适配器
        fastmcp_adapter = FastMCPToolAdapter()
        await self.register_adapter("fastmcp", fastmcp_adapter)
        
        # 注册Haystack适配器
        haystack_adapter = HaystackToolAdapter()
        await self.register_adapter("haystack", haystack_adapter)
    
    async def register_adapter(self, provider_name: str, adapter: BaseToolAdapter) -> bool:
        """注册框架适配器"""
        if provider_name in self._adapters:
            raise ToolRegistryError(f"Adapter {provider_name} already registered", "DUPLICATE_ADAPTER")
        
        self._adapters[provider_name] = adapter
        self._tools_by_provider[provider_name] = {}
        self._stats["frameworks_count"] += 1
        
        self._logger.info(f"Registered adapter: {provider_name}")
        return True
    
    async def _initialize_adapters(self):
        """初始化所有适配器"""
        for provider_name, adapter in self._adapters.items():
            try:
                await adapter.initialize()
                self._logger.info(f"Initialized adapter: {provider_name}")
            except Exception as e:
                self._logger.error(f"Failed to initialize adapter {provider_name}: {e}")
                raise
    
    async def _discover_and_register_all_tools(self):
        """发现并注册所有工具"""
        for provider_name, adapter in self._adapters.items():
            try:
                # 发现工具
                tools = await adapter.discover_tools()
                
                # 注册工具
                for tool in tools:
                    await self._register_tool_internal(tool, provider_name)
                
                self._logger.info(f"Discovered and registered {len(tools)} tools from {provider_name}")
                
            except Exception as e:
                self._logger.error(f"Failed to discover tools from {provider_name}: {e}")
                # 继续处理其他适配器
                continue
    
    async def _register_tool_internal(self, tool_spec: ToolSpec, provider_name: str):
        """内部工具注册方法"""
        # 验证工具规范
        if not tool_spec.name:
            raise ToolRegistryError("Tool name is required", "INVALID_TOOL_SPEC")
        
        # 检查工具名称冲突
        if tool_spec.name in self._global_tools:
            existing_tool = self._global_tools[tool_spec.name]
            if existing_tool.provider != provider_name:
                # 重命名工具以避免冲突
                tool_spec.name = f"{provider_name}_{tool_spec.name}"
        
        # 注册到提供方索引
        self._tools_by_provider[provider_name][tool_spec.name] = tool_spec
        
        # 注册到分类索引
        if tool_spec.category not in self._tools_by_category:
            self._tools_by_category[tool_spec.category] = {}
        self._tools_by_category[tool_spec.category][tool_spec.name] = tool_spec
        
        # 注册到全局索引
        self._global_tools[tool_spec.name] = tool_spec
        
        self._stats["total_tools"] += 1
    
    async def discover_tools(self, 
                           filters: Optional[Dict[str, Any]] = None,
                           categories: Optional[List[ToolCategory]] = None,
                           providers: Optional[List[str]] = None) -> List[ToolSpec]:
        """发现可用工具"""
        if not self._initialized:
            raise ToolRegistryError("Registry not initialized", "NOT_INITIALIZED")
        
        tools = list(self._global_tools.values())
        
        # 按分类过滤
        if categories:
            tools = [tool for tool in tools if tool.category in categories]
        
        # 按提供方过滤
        if providers:
            tools = [tool for tool in tools if tool.provider in providers]
        
        return tools
    
    async def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """获取工具规范"""
        return self._global_tools.get(tool_name)
    
    async def execute_tool(self, 
                          tool_name: str, 
                          params: Dict[str, Any],
                          context: Optional[ToolExecutionContext] = None) -> ToolResult:
        """执行工具"""
        if not self._initialized:
            raise ToolRegistryError("Registry not initialized", "NOT_INITIALIZED")
        
        # 获取工具规范
        tool_spec = await self.get_tool_spec(tool_name)
        if not tool_spec:
            return self._create_error_result(
                context.execution_id if context else str(uuid4()),
                tool_name,
                f"Tool {tool_name} not found",
                "TOOL_NOT_FOUND"
            )
        
        # 获取适配器
        adapter = self._adapters.get(tool_spec.provider)
        if not adapter:
            return self._create_error_result(
                context.execution_id if context else str(uuid4()),
                tool_name,
                f"Adapter for provider {tool_spec.provider} not found",
                "ADAPTER_NOT_FOUND"
            )
        
        # 更新执行状态
        execution_id = context.execution_id if context else str(uuid4())
        self._execution_status[execution_id] = ToolStatus.RUNNING
        
        try:
            # 执行工具
            result = await adapter.execute_tool(tool_name, params, context)
            
            # 更新统计信息
            self._stats["total_executions"] += 1
            if result.is_success():
                self._stats["successful_executions"] += 1
            else:
                self._stats["failed_executions"] += 1
            
            # 更新执行状态
            self._execution_status[execution_id] = result.status
            
            return result
            
        except Exception as e:
            self._logger.error(f"Tool execution failed for {tool_name}: {e}")
            self._stats["total_executions"] += 1
            self._stats["failed_executions"] += 1
            self._execution_status[execution_id] = ToolStatus.FAILED
            
            return self._create_error_result(
                execution_id, tool_name, str(e), "EXECUTION_ERROR"
            )
    
    def get_execution_status(self, execution_id: str) -> Optional[ToolStatus]:
        """获取执行状态"""
        return self._execution_status.get(execution_id)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        return {
            **self._stats,
            "tools_by_provider": {
                provider: len(tools) for provider, tools in self._tools_by_provider.items()
            },
            "tools_by_category": {
                category.value: len(tools) for category, tools in self._tools_by_category.items()
            },
            "available_providers": list(self._adapters.keys()),
            "initialized": self._initialized,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_error_result(self, execution_id: str, tool_name: str, error: str, 
                           error_code: str = None) -> ToolResult:
        """创建错误结果"""
        return ToolResult(
            execution_id=execution_id,
            tool_name=tool_name,
            status=ToolStatus.FAILED,
            error=error,
            error_code=error_code,
            completed_at=datetime.now()
        ) 