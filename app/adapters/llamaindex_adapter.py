"""
LlamaIndex框架适配器实现
适配现有LlamaIndex工具，提供统一的工具接口
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..abstractions import (
    ToolSpec, ToolResult, ToolStatus, ToolCategory, ToolExecutionContext,
    FrameworkInfo, FrameworkCapability, FrameworkConfig
)
from .base_adapter import BaseToolAdapter, BaseFrameworkAdapter, AdapterError


class LlamaIndexToolAdapter(BaseToolAdapter):
    """LlamaIndex工具适配器"""
    
    def __init__(self):
        # 支持的工具分类
        supported_categories = [
            ToolCategory.KNOWLEDGE,
            ToolCategory.SEARCH,
            ToolCategory.FILE_MANAGEMENT,
            ToolCategory.INTEGRATION
        ]
        
        super().__init__("llamaindex", supported_categories)
        
        # 工具映射表
        self._tool_mapping: Dict[str, Any] = {}
        
    async def _do_initialize(self):
        """初始化LlamaIndex工具"""
        try:
            # 自动发现并注册LlamaIndex工具
            await self._discover_and_register_llamaindex_tools()
            
            self._logger.info("LlamaIndex adapter initialized with tools")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize LlamaIndex tools: {e}")
            raise AdapterError(f"LlamaIndex initialization failed: {e}", "LLAMAINDEX_INIT_ERROR", e)
    
    async def _do_shutdown(self):
        """清理LlamaIndex资源"""
        self._tool_mapping.clear()
    
    async def _discover_and_register_llamaindex_tools(self):
        """发现并注册LlamaIndex工具"""
        
        # 注册查询引擎工具
        query_engine_spec = ToolSpec(
            name="llamaindex_query_engine",
            version="1.0.0",
            description="LlamaIndex查询引擎 - 基于索引的智能查询",
            category=ToolCategory.KNOWLEDGE,
            provider="llamaindex",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询内容"},
                    "index_name": {"type": "string", "description": "索引名称"},
                    "similarity_top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "source_nodes": {"type": "array"}
                }
            },
            capabilities=["query", "retrieval"],
            tags=["llamaindex", "query", "retrieval"]
        )
        
        self._tools_cache[query_engine_spec.name] = query_engine_spec
        self._tool_mapping[query_engine_spec.name] = "query_engine"
    
    async def discover_tools(self, 
                           filters: Optional[Dict[str, Any]] = None,
                           categories: Optional[List[ToolCategory]] = None) -> List[ToolSpec]:
        """发现可用工具"""
        tools = list(self._tools_cache.values())
        
        # 按分类过滤
        if categories:
            tools = [tool for tool in tools if tool.category in categories]
        
        return tools
    
    async def execute_tool(self, 
                          tool_name: str, 
                          params: Dict[str, Any],
                          context: Optional[ToolExecutionContext] = None) -> ToolResult:
        """执行工具"""
        if not self._initialized:
            raise AdapterError("Adapter not initialized", "NOT_INITIALIZED")
        
        # 获取执行上下文
        if not context:
            context = ToolExecutionContext()
        
        start_time = datetime.now()
        
        try:
            # 验证工具存在
            if tool_name not in self._tool_mapping:
                return self._create_error_result(
                    context.execution_id, tool_name, 
                    f"Tool {tool_name} not found", "TOOL_NOT_FOUND"
                )
            
            # 执行工具 - 模拟执行
            result_data = {"result": f"执行了LlamaIndex工具 {tool_name}"}
            
            # 计算执行时间
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return self._create_success_result(
                context.execution_id, tool_name, result_data, duration_ms
            )
            
        except Exception as e:
            self._logger.error(f"Tool execution failed for {tool_name}: {e}")
            return self._create_error_result(
                context.execution_id, tool_name, str(e), "EXECUTION_ERROR"
            )


class LlamaIndexFrameworkAdapter(BaseFrameworkAdapter):
    """LlamaIndex框架适配器"""
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        tool_adapter = LlamaIndexToolAdapter()
        super().__init__(tool_adapter, config)
    
    def _create_framework_info(self) -> FrameworkInfo:
        """创建LlamaIndex框架信息"""
        return FrameworkInfo(
            name="llamaindex",
            version="0.10.0",
            description="LlamaIndex - 数据框架用于LLM应用程序",
            vendor="LlamaIndex Team",
            license="MIT",
            capabilities={
                FrameworkCapability.KNOWLEDGE_BASE,
                FrameworkCapability.RAG_RETRIEVAL,
                FrameworkCapability.SEMANTIC_SEARCH,
                FrameworkCapability.DOCUMENT_PROCESSING
            },
            supported_categories={
                ToolCategory.KNOWLEDGE,
                ToolCategory.SEARCH,
                ToolCategory.FILE_MANAGEMENT,
                ToolCategory.INTEGRATION
            },
            python_version="3.8+",
            dependencies=["llama-index>=0.10.0"],
            tags=["llm", "rag", "retrieval", "knowledge"]
        ) 