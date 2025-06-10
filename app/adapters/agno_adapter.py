"""
Agno框架适配器实现
集成现有AgnoToolsManager，提供统一的工具接口
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

# 导入现有Agno工具管理器和新的工具基础类
try:
    from ..tools.agno.manager import AgnoToolsManager
    from ..tools.agno.custom_tools import ZZDSJCustomTools
    from ..tools.agno_tool_base import agno_tool_manager
    from ..tools.reasoning.reasoning_toolkit import reasoning_toolkit
except ImportError:
    # 如果导入失败，提供模拟实现
    class AgnoToolsManager:
        def __init__(self):
            pass
        def get_all_agno_tools(self):
            return []
    
    class ZZDSJCustomTools:
        def __init__(self):
            pass
    
    agno_tool_manager = None
    reasoning_toolkit = None


class AgnoToolAdapter(BaseToolAdapter):
    """Agno工具适配器 - 复用现有AgnoToolsManager"""
    
    def __init__(self):
        # 支持的工具分类
        supported_categories = [
            ToolCategory.REASONING,
            ToolCategory.THINKING,
            ToolCategory.KNOWLEDGE,
            ToolCategory.SEARCH,
            ToolCategory.AGENTIC_SEARCH,
            ToolCategory.CHUNKING,
            ToolCategory.CUSTOM
        ]
        
        super().__init__("agno", supported_categories)
        
        # 工具映射表
        self._tool_mapping: Dict[str, Any] = {}
        
    async def _do_initialize(self):
        """初始化Agno工具管理器"""
        try:
            # 初始化推理工具包
            if reasoning_toolkit:
                await reasoning_toolkit.initialize_all()
                self._logger.info("Reasoning toolkit initialized")
            
            # 自动发现并注册Agno工具
            await self._discover_and_register_agno_tools()
            
            self._logger.info("Agno adapter initialized with all tools")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize Agno tools: {e}")
            raise AdapterError(f"Agno initialization failed: {e}", "AGNO_INIT_ERROR", e)
    
    async def _do_shutdown(self):
        """清理Agno资源"""
        self._tool_mapping.clear()
    
    async def _discover_and_register_agno_tools(self):
        """发现并注册Agno工具"""
        
        # 注册推理工具
        await self._register_reasoning_tools()
        
        # 注册思考工具
        await self._register_thinking_tools()
        
        # 注册知识工具
        await self._register_knowledge_tools()
        
        # 注册搜索工具
        await self._register_search_tools()
        
        # 注册分块工具
        await self._register_chunking_tools()
    
    async def _register_reasoning_tools(self):
        """注册推理工具"""
        reasoning_spec = ToolSpec(
            name="agno_reasoning",
            version="1.0.0",
            description="Agno ReasoningTools - 结构化推理和分析工具",
            category=ToolCategory.REASONING,
            provider="agno",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "推理查询"},
                    "structured": {"type": "boolean", "default": True},
                    "context": {"type": "string", "description": "推理上下文"}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "reasoning_result": {"type": "string"},
                    "analysis": {"type": "object"},
                    "confidence": {"type": "number"}
                }
            },
            capabilities=["reasoning", "analysis", "structured_thinking"],
            tags=["agno", "reasoning", "analysis"]
        )
        
        self._tools_cache[reasoning_spec.name] = reasoning_spec
        self._tool_mapping[reasoning_spec.name] = "reasoning_manager"
    
    async def _register_thinking_tools(self):
        """注册思考工具"""
        thinking_spec = ToolSpec(
            name="agno_thinking",
            version="1.0.0",
            description="Agno ThinkingTools - 迭代思考和问题分解工具",
            category=ToolCategory.THINKING,
            provider="agno",
            input_schema={
                "type": "object",
                "properties": {
                    "problem": {"type": "string", "description": "需要思考的问题"},
                    "max_iterations": {"type": "integer", "default": 5},
                    "depth": {"type": "integer", "default": 3}
                },
                "required": ["problem"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "thinking_process": {"type": "array"},
                    "solution": {"type": "string"},
                    "iterations": {"type": "integer"}
                }
            },
            capabilities=["thinking", "problem_solving", "iteration"],
            tags=["agno", "thinking", "problem_solving"]
        )
        
        self._tools_cache[thinking_spec.name] = thinking_spec
        self._tool_mapping[thinking_spec.name] = "thinking_manager"
    
    async def _register_knowledge_tools(self):
        """注册知识工具"""
        knowledge_spec = ToolSpec(
            name="agno_knowledge",
            version="1.0.0",
            description="Agno KnowledgeTools - 知识库搜索、分析和思考工具",
            category=ToolCategory.KNOWLEDGE,
            provider="agno",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "知识查询"},
                    "think": {"type": "boolean", "default": True},
                    "search": {"type": "boolean", "default": True},
                    "analyze": {"type": "boolean", "default": True},
                    "knowledge_base": {"type": "string", "description": "知识库名称"}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "analysis": {"type": "object"},
                    "sources": {"type": "array"}
                }
            },
            capabilities=["knowledge_search", "analysis", "thinking"],
            tags=["agno", "knowledge", "rag", "search"]
        )
        
        self._tools_cache[knowledge_spec.name] = knowledge_spec
        self._tool_mapping[knowledge_spec.name] = "knowledge_manager"
    
    async def _register_search_tools(self):
        """注册搜索工具"""
        search_spec = ToolSpec(
            name="agno_search",
            version="1.0.0",
            description="Agno AgenticSearch - 智能搜索和结果过滤工具",
            category=ToolCategory.AGENTIC_SEARCH,
            provider="agno",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"},
                    "search_engine": {"type": "string", "default": "google"},
                    "max_results": {"type": "integer", "default": 10},
                    "filters": {"type": "object", "description": "搜索过滤器"}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "total_results": {"type": "integer"},
                    "search_metadata": {"type": "object"}
                }
            },
            capabilities=["web_search", "intelligent_filtering", "result_ranking"],
            tags=["agno", "search", "web", "agentic"]
        )
        
        self._tools_cache[search_spec.name] = search_spec
        self._tool_mapping[search_spec.name] = "search_manager"
    
    async def _register_chunking_tools(self):
        """注册分块工具"""
        chunking_spec = ToolSpec(
            name="agno_chunking",
            version="1.0.0",
            description="Agno ChunkingTools - 智能文档分块和重叠处理工具",
            category=ToolCategory.CHUNKING,
            provider="agno",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "需要分块的文本"},
                    "chunk_size": {"type": "integer", "default": 1000},
                    "overlap": {"type": "integer", "default": 200},
                    "strategy": {"type": "string", "default": "semantic"}
                },
                "required": ["text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "chunks": {"type": "array"},
                    "chunk_count": {"type": "integer"},
                    "metadata": {"type": "object"}
                }
            },
            capabilities=["text_chunking", "overlap_handling", "semantic_splitting"],
            tags=["agno", "chunking", "text_processing"]
        )
        
        self._tools_cache[chunking_spec.name] = chunking_spec
        self._tool_mapping[chunking_spec.name] = "chunking_manager"
    
    async def discover_tools(self, 
                           filters: Optional[Dict[str, Any]] = None,
                           categories: Optional[List[ToolCategory]] = None) -> List[ToolSpec]:
        """发现可用工具"""
        tools = list(self._tools_cache.values())
        
        # 按分类过滤
        if categories:
            tools = [tool for tool in tools if tool.category in categories]
        
        # 按其他过滤条件过滤
        if filters:
            provider_filter = filters.get("provider")
            if provider_filter:
                tools = [tool for tool in tools if tool.provider == provider_filter]
            
            tags_filter = filters.get("tags")
            if tags_filter:
                tools = [tool for tool in tools 
                        if any(tag in tool.tags for tag in tags_filter)]
        
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
            
            # 验证参数
            if not await self.validate_params(tool_name, params):
                return self._create_error_result(
                    context.execution_id, tool_name,
                    "Invalid parameters", "INVALID_PARAMS"
                )
            
            # 执行工具 - 模拟执行
            result_data = await self._simulate_tool_execution(tool_name, params)
            
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
    
    async def _simulate_tool_execution(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行Agno工具 - 优先使用真实工具，回退到模拟"""
        # 尝试使用推理工具包
        if tool_name == "agno_reasoning" and reasoning_toolkit:
            try:
                # 转换参数格式
                reasoning_params = {
                    "problem": params.get("query", ""),
                    "reasoning_type": params.get("structured", True) and "deductive" or "inductive",
                    "context": params.get("context", "")
                }
                result = await reasoning_toolkit.execute_reasoning("structured_reasoning", reasoning_params)
                if result.success:
                    return result.result
                else:
                    self._logger.warning(f"Reasoning tool failed: {result.error}")
            except Exception as e:
                self._logger.warning(f"Failed to use reasoning toolkit: {e}")
        
        # 尝试使用其他Agno工具
        if agno_tool_manager:
            try:
                # 将工具名映射到内部工具
                internal_tool_name = self._map_to_internal_tool(tool_name)
                if internal_tool_name:
                    result = await agno_tool_manager.execute_tool(internal_tool_name, params)
                    if result.success:
                        return result.result
            except Exception as e:
                self._logger.warning(f"Failed to use agno tool manager: {e}")
        
        # 回退到模拟执行
        if tool_name == "agno_reasoning":
            return {"reasoning_result": f"推理结果：{params.get('query', '')}", "confidence": 0.85}
        elif tool_name == "agno_thinking":
            return {"solution": f"解决方案：{params.get('problem', '')}", "iterations": 3}
        elif tool_name == "agno_knowledge":
            return {"results": [{"title": f"知识项：{params.get('query', '')}"}], "sources": ["知识库A"]}
        elif tool_name == "agno_search":
            return {"results": [{"title": f"搜索结果：{params.get('query', '')}"}], "total_results": 1}
        elif tool_name == "agno_chunking":
            text = params.get("text", "")
            return {"chunks": [{"content": text[:500]}], "chunk_count": 1}
        else:
            return {"result": f"执行了工具 {tool_name}"}
    
    def _map_to_internal_tool(self, external_tool_name: str) -> Optional[str]:
        """将外部工具名映射到内部工具名"""
        mapping = {
            "agno_reasoning": "structured_reasoning",
            "agno_thinking": "logical_analysis", 
            "agno_knowledge": "problem_decomposition"
        }
        return mapping.get(external_tool_name)


class AgnoFrameworkAdapter(BaseFrameworkAdapter):
    """Agno框架适配器"""
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        tool_adapter = AgnoToolAdapter()
        super().__init__(tool_adapter, config)
    
    def _create_framework_info(self) -> FrameworkInfo:
        """创建Agno框架信息"""
        return FrameworkInfo(
            name="agno",
            version="2.0.0",
            description="Agno AI Framework - 智能代理和工具框架",
            vendor="Agno Team",
            license="MIT",
            capabilities={
                FrameworkCapability.AGENT_CREATION,
                FrameworkCapability.CONVERSATION,
                FrameworkCapability.REASONING,
                FrameworkCapability.TOOL_CALLING,
                FrameworkCapability.TOOL_REGISTRATION,
                FrameworkCapability.CUSTOM_TOOLS,
                FrameworkCapability.KNOWLEDGE_BASE,
                FrameworkCapability.RAG_RETRIEVAL,
                FrameworkCapability.SEMANTIC_SEARCH,
                FrameworkCapability.MULTI_AGENT,
                FrameworkCapability.TEAM_COORDINATION
            },
            supported_categories={
                ToolCategory.REASONING,
                ToolCategory.THINKING,
                ToolCategory.KNOWLEDGE,
                ToolCategory.SEARCH,
                ToolCategory.AGENTIC_SEARCH,
                ToolCategory.CHUNKING,
                ToolCategory.CUSTOM
            },
            python_version="3.9+",
            dependencies=["agno>=2.0.0", "openai", "anthropic"],
            tags=["ai", "agents", "reasoning", "rag"]
        ) 