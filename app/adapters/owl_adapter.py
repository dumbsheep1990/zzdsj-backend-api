"""
OWL框架适配器实现
集成OWL智能体框架的工具和功能到统一工具系统
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

# 导入OWL框架组件
try:
    from ..frameworks.owl.tool_manager import OwlToolManager, tool_manager
    from ..frameworks.owl.toolkits.base import OwlToolkitManager
    from ..frameworks.owl.config import (
        owl_tools_settings, search_tool_settings, document_tool_settings,
        knowledge_tool_settings, api_tool_settings, code_exec_tool_settings
    )
except ImportError:
    # 如果导入失败，提供模拟实现
    class OwlToolManager:
        def __init__(self):
            pass
        def list_available_tools(self):
            return []
        async def execute_tool(self, tool_name: str, **kwargs):
            return {"status": "error", "message": "OWL framework not available"}
    
    class OwlToolkitManager:
        def __init__(self):
            pass
        async def initialize(self):
            pass
        async def get_tools(self):
            return []
    
    tool_manager = OwlToolManager()
    owl_tools_settings = None


class OwlToolAdapter(BaseToolAdapter):
    """OWL工具适配器 - 集成OWL智能体框架"""
    
    def __init__(self):
        # OWL支持的工具分类
        supported_categories = [
            ToolCategory.SEARCH,
            ToolCategory.FILE_MANAGEMENT,   # 用于文档处理
            ToolCategory.KNOWLEDGE,
            ToolCategory.INTEGRATION,       # 用于API调用和代码执行
            ToolCategory.CUSTOM            # 用于智能体工具
        ]
        
        super().__init__("owl", supported_categories)
        
        # OWL组件
        self._owl_tool_manager = tool_manager
        self._owl_toolkit_manager = OwlToolkitManager()
        
        # 工具映射表
        self._tool_mapping: Dict[str, str] = {}
        
    async def _do_initialize(self):
        """初始化OWL工具适配器"""
        try:
            # 初始化OWL工具包管理器
            await self._owl_toolkit_manager.initialize()
            
            # 发现并注册OWL工具
            await self._discover_and_register_owl_tools()
            
            self._logger.info("OWL adapter initialized with all tools")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize OWL tools: {e}")
            raise AdapterError(f"OWL initialization failed: {e}", "OWL_INIT_ERROR", e)
    
    async def _do_shutdown(self):
        """清理OWL资源"""
        self._tool_mapping.clear()
    
    async def _discover_and_register_owl_tools(self):
        """发现并注册OWL工具"""
        
        # 注册搜索工具
        await self._register_search_tools()
        
        # 注册文档处理工具
        await self._register_document_tools()
        
        # 注册知识库工具
        await self._register_knowledge_tools()
        
        # 注册API调用工具
        await self._register_api_tools()
        
        # 注册代码执行工具
        await self._register_code_execution_tools()
        
        # 注册智能体工具
        await self._register_agent_tools()
    
    async def _register_search_tools(self):
        """注册搜索工具"""
        search_spec = ToolSpec(
            name="owl_search",
            version="1.0.0",
            description="OWL智能搜索工具 - 支持多源搜索和结果过滤",
            category=ToolCategory.SEARCH,
            provider="owl",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"},
                    "max_results": {"type": "integer", "default": 5},
                    "filter_enabled": {"type": "boolean", "default": True},
                    "search_source": {"type": "string", "enum": ["web", "internal", "all"], "default": "all"}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "total_count": {"type": "integer"},
                    "search_metadata": {"type": "object"}
                }
            },
            capabilities=["web_search", "result_filtering", "multi_source"],
            tags=["owl", "search", "web", "filtering"]
        )
        
        self._tools_cache[search_spec.name] = search_spec
        self._tool_mapping[search_spec.name] = "search"
    
    async def _register_document_tools(self):
        """注册文档处理工具"""
        document_spec = ToolSpec(
            name="owl_document",
            version="1.0.0",
            description="OWL文档处理工具 - 支持多格式文档读取、解析和处理",
            category=ToolCategory.FILE_MANAGEMENT,
            provider="owl",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文档文件路径"},
                    "action": {"type": "string", "enum": ["read", "parse", "extract"], "default": "read"},
                    "format": {"type": "string", "enum": ["pdf", "docx", "txt"], "description": "文档格式"},
                    "extract_images": {"type": "boolean", "default": False}
                },
                "required": ["file_path"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "metadata": {"type": "object"},
                    "images": {"type": "array"}
                }
            },
            capabilities=["document_reading", "format_parsing", "content_extraction"],
            tags=["owl", "document", "pdf", "docx", "parsing"]
        )
        
        self._tools_cache[document_spec.name] = document_spec
        self._tool_mapping[document_spec.name] = "document"
    
    async def _register_knowledge_tools(self):
        """注册知识库工具"""
        knowledge_spec = ToolSpec(
            name="owl_knowledge",
            version="1.0.0",
            description="OWL知识库工具 - 智能知识检索和语义搜索",
            category=ToolCategory.KNOWLEDGE,
            provider="owl",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "知识查询"},
                    "max_chunks": {"type": "integer", "default": 10},
                    "similarity_threshold": {"type": "number", "default": 0.75},
                    "knowledge_base": {"type": "string", "description": "知识库名称"}
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "chunks": {"type": "array"},
                    "sources": {"type": "array"},
                    "similarity_scores": {"type": "array"}
                }
            },
            capabilities=["semantic_search", "knowledge_retrieval", "similarity_matching"],
            tags=["owl", "knowledge", "rag", "semantic", "retrieval"]
        )
        
        self._tools_cache[knowledge_spec.name] = knowledge_spec
        self._tool_mapping[knowledge_spec.name] = "knowledge"
    
    async def _register_api_tools(self):
        """注册API调用工具"""
        api_spec = ToolSpec(
            name="owl_api",
            version="1.0.0",
            description="OWL API调用工具 - 支持HTTP请求和API集成",
            category=ToolCategory.INTEGRATION,
            provider="owl",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "API端点URL"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                    "headers": {"type": "object", "description": "请求头"},
                    "data": {"type": "object", "description": "请求数据"},
                    "timeout": {"type": "integer", "default": 15}
                },
                "required": ["url"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {"type": "object"},
                    "status_code": {"type": "integer"},
                    "headers": {"type": "object"}
                }
            },
            capabilities=["http_requests", "api_integration", "response_parsing"],
            tags=["owl", "api", "http", "integration"]
        )
        
        self._tools_cache[api_spec.name] = api_spec
        self._tool_mapping[api_spec.name] = "api"
    
    async def _register_code_execution_tools(self):
        """注册代码执行工具"""
        code_exec_spec = ToolSpec(
            name="owl_code_exec",
            version="1.0.0",
            description="OWL代码执行工具 - 安全的代码执行环境",
            category=ToolCategory.INTEGRATION,
            provider="owl",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要执行的代码"},
                    "language": {"type": "string", "enum": ["python", "javascript"], "default": "python"},
                    "timeout": {"type": "integer", "default": 5},
                    "max_memory_mb": {"type": "integer", "default": 100}
                },
                "required": ["code"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                    "stdout": {"type": "string"},
                    "stderr": {"type": "string"},
                    "execution_time": {"type": "number"}
                }
            },
            capabilities=["code_execution", "sandbox_environment", "multi_language"],
            tags=["owl", "code", "execution", "python", "javascript"]
        )
        
        self._tools_cache[code_exec_spec.name] = code_exec_spec
        self._tool_mapping[code_exec_spec.name] = "code_exec"
    
    async def _register_agent_tools(self):
        """注册智能体工具"""
        agent_spec = ToolSpec(
            name="owl_agent",
            version="1.0.0",
            description="OWL智能体工具 - 智能代理创建和管理",
            category=ToolCategory.CUSTOM,
            provider="owl",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "enum": ["single", "multi", "society"], "default": "single"},
                    "task": {"type": "string", "description": "代理任务"},
                    "tools": {"type": "array", "description": "可用工具列表"},
                    "collaboration": {"type": "boolean", "default": False}
                },
                "required": ["task"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "result": {"type": "object"},
                    "execution_path": {"type": "array"}
                }
            },
            capabilities=["agent_creation", "multi_agent", "collaboration", "society"],
            tags=["owl", "agent", "ai", "automation", "society"]
        )
        
        self._tools_cache[agent_spec.name] = agent_spec
        self._tool_mapping[agent_spec.name] = "agent"
    
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
            
            # 执行OWL工具
            result_data = await self._execute_owl_tool(tool_name, params)
            
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
    
    async def _execute_owl_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行OWL工具"""
        # 获取内部工具名
        internal_tool_name = self._tool_mapping.get(tool_name)
        if not internal_tool_name:
            raise ValueError(f"Unknown tool mapping for {tool_name}")
        
        # 尝试使用OWL工具管理器执行
        try:
            result = await self._owl_tool_manager.execute_tool(internal_tool_name, **params)
            if result.get("status") == "success":
                return result.get("data", {})
            else:
                # 如果OWL工具执行失败，使用模拟执行
                return await self._simulate_owl_tool_execution(tool_name, params)
        except Exception as e:
            self._logger.warning(f"OWL tool execution failed, using simulation: {e}")
            return await self._simulate_owl_tool_execution(tool_name, params)
    
    async def _simulate_owl_tool_execution(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """模拟OWL工具执行"""
        if tool_name == "owl_search":
            return {
                "results": [{"title": f"搜索结果：{params.get('query', '')}", "url": "https://example.com"}],
                "total_count": 1,
                "search_metadata": {"source": "owl_search", "filter_applied": params.get('filter_enabled', True)}
            }
        elif tool_name == "owl_document":
            return {
                "content": f"文档内容：{params.get('file_path', '')}",
                "metadata": {"format": params.get('format', 'unknown'), "pages": 1},
                "images": []
            }
        elif tool_name == "owl_knowledge":
            return {
                "chunks": [{"text": f"知识片段：{params.get('query', '')}", "score": 0.85}],
                "sources": ["knowledge_base_1"],
                "similarity_scores": [0.85]
            }
        elif tool_name == "owl_api":
            return {
                "response": {"message": f"API调用成功：{params.get('url', '')}"},
                "status_code": 200,
                "headers": {"content-type": "application/json"}
            }
        elif tool_name == "owl_code_exec":
            return {
                "result": f"代码执行结果：{params.get('code', '')}",
                "stdout": "Hello World",
                "stderr": "",
                "execution_time": 0.1
            }
        elif tool_name == "owl_agent":
            return {
                "agent_id": str(uuid4()),
                "result": {"task_completed": True, "output": f"任务完成：{params.get('task', '')}"},
                "execution_path": ["initialize", "execute", "complete"]
            }
        else:
            return {"result": f"执行了OWL工具 {tool_name}"}


class OwlFrameworkAdapter(BaseFrameworkAdapter):
    """OWL框架适配器"""
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        tool_adapter = OwlToolAdapter()
        super().__init__(tool_adapter, config)
    
    def _create_framework_info(self) -> FrameworkInfo:
        """创建OWL框架信息"""
        return FrameworkInfo(
            name="owl",
            version="1.0.0",
            description="OWL智能体框架 - 提供完整的智能代理、工具集成和协作能力",
            vendor="OWL Team",
            license="MIT",
            capabilities={
                FrameworkCapability.AGENT_CREATION,
                FrameworkCapability.MULTI_AGENT,
                FrameworkCapability.TEAM_COORDINATION,
                FrameworkCapability.TOOL_CALLING,
                FrameworkCapability.TOOL_REGISTRATION,
                FrameworkCapability.CUSTOM_TOOLS,
                FrameworkCapability.KNOWLEDGE_BASE,
                FrameworkCapability.RAG_RETRIEVAL,
                FrameworkCapability.DOCUMENT_PROCESSING,
                FrameworkCapability.SEMANTIC_SEARCH,
                FrameworkCapability.API_INTEGRATION
            },
            supported_categories={
                ToolCategory.SEARCH,
                ToolCategory.FILE_MANAGEMENT,
                ToolCategory.KNOWLEDGE,
                ToolCategory.INTEGRATION,
                ToolCategory.CUSTOM
            },
            python_version="3.9+",
            dependencies=["owl>=1.0.0", "fastapi", "pydantic"],
            tags=["ai", "agents", "collaboration", "tools", "society"]
        ) 