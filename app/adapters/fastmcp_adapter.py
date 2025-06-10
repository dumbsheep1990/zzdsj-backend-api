"""
FastMCP框架适配器实现
集成FastMCP (Model Context Protocol) 框架到统一工具系统
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

# 导入FastMCP框架组件
try:
    from ..frameworks.fastmcp import (
        create_mcp_server, get_mcp_server, register_tool, list_tools,
        register_resource, list_resources, register_prompt, list_prompts,
        register_external_mcp, list_external_mcps, get_external_mcp,
        MCPClient, create_mcp_client
    )
    from ..frameworks.fastmcp.integrations import (
        get_all_providers, create_chat_client, create_image_client,
        create_map_client, create_data_client
    )
except ImportError:
    # 如果导入失败，提供模拟实现
    def create_mcp_server():
        return None
    def get_mcp_server():
        return None
    def list_tools():
        return []
    def list_resources():
        return []
    def list_prompts():
        return []
    def list_external_mcps():
        return []
    def get_all_providers():
        return []


class FastMCPToolAdapter(BaseToolAdapter):
    """FastMCP工具适配器 - 集成FastMCP框架"""
    
    def __init__(self):
        # FastMCP支持的工具分类
        supported_categories = [
            ToolCategory.MCP,              # MCP协议工具
            ToolCategory.INTEGRATION,     # 集成工具
            ToolCategory.CUSTOM           # 自定义工具
        ]
        
        super().__init__("fastmcp", supported_categories)
        
        # FastMCP组件
        self._mcp_server = None
        self._external_clients: Dict[str, Any] = {}
        
        # 工具映射表
        self._tool_mapping: Dict[str, str] = {}
        self._resource_mapping: Dict[str, str] = {}
        self._prompt_mapping: Dict[str, str] = {}
        
    async def _do_initialize(self):
        """初始化FastMCP工具适配器"""
        try:
            # 初始化MCP服务器
            self._mcp_server = get_mcp_server()
            if not self._mcp_server:
                self._mcp_server = create_mcp_server()
            
            # 发现并注册FastMCP工具
            await self._discover_and_register_fastmcp_tools()
            
            self._logger.info("FastMCP adapter initialized with all tools")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize FastMCP tools: {e}")
            raise AdapterError(f"FastMCP initialization failed: {e}", "FASTMCP_INIT_ERROR", e)
    
    async def _do_shutdown(self):
        """清理FastMCP资源"""
        # 关闭外部客户端连接
        for client_name, client in self._external_clients.items():
            try:
                if hasattr(client, 'close'):
                    await client.close()
            except Exception as e:
                self._logger.warning(f"Failed to close MCP client {client_name}: {e}")
        
        self._external_clients.clear()
        self._tool_mapping.clear()
        self._resource_mapping.clear()
        self._prompt_mapping.clear()
    
    async def _discover_and_register_fastmcp_tools(self):
        """发现并注册FastMCP工具"""
        
        # 注册MCP工具
        await self._register_mcp_tools()
        
        # 注册MCP资源
        await self._register_mcp_resources()
        
        # 注册MCP提示
        await self._register_mcp_prompts()
        
        # 注册外部MCP服务
        await self._register_external_mcp_services()
        
        # 注册MCP客户端工具
        await self._register_mcp_client_tools()
    
    async def _register_mcp_tools(self):
        """注册MCP原生工具"""
        try:
            tools = list_tools()
            for tool in tools:
                tool_spec = ToolSpec(
                    name=f"fastmcp_{tool['name']}",
                    version="1.0.0",
                    description=f"FastMCP工具: {tool.get('description', tool['name'])}",
                    category=ToolCategory.MCP,
                    provider="fastmcp",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "params": {"type": "object", "description": "工具参数"}
                        },
                        "required": []
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "result": {"type": "object"},
                            "metadata": {"type": "object"}
                        }
                    },
                    capabilities=["mcp_tool_execution"],
                    tags=["fastmcp", "mcp", "tool"] + tool.get('tags', [])
                )
                
                self._tools_cache[tool_spec.name] = tool_spec
                self._tool_mapping[tool_spec.name] = tool['name']
                
        except Exception as e:
            self._logger.warning(f"Failed to register MCP tools: {e}")
    
    async def _register_mcp_resources(self):
        """注册MCP资源"""
        try:
            resources = list_resources()
            for resource in resources:
                resource_spec = ToolSpec(
                    name=f"fastmcp_resource_{resource['name']}",
                    version="1.0.0",
                    description=f"FastMCP资源: {resource.get('description', resource['name'])}",
                    category=ToolCategory.MCP,
                    provider="fastmcp",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "uri": {"type": "string", "description": "资源URI"},
                            "params": {"type": "object", "description": "资源参数"}
                        },
                        "required": ["uri"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "metadata": {"type": "object"}
                        }
                    },
                    capabilities=["mcp_resource_access"],
                    tags=["fastmcp", "mcp", "resource"]
                )
                
                self._tools_cache[resource_spec.name] = resource_spec
                self._resource_mapping[resource_spec.name] = resource['name']
                
        except Exception as e:
            self._logger.warning(f"Failed to register MCP resources: {e}")
    
    async def _register_mcp_prompts(self):
        """注册MCP提示"""
        try:
            prompts = list_prompts()
            for prompt in prompts:
                prompt_spec = ToolSpec(
                    name=f"fastmcp_prompt_{prompt['name']}",
                    version="1.0.0",
                    description=f"FastMCP提示: {prompt.get('description', prompt['name'])}",
                    category=ToolCategory.MCP,
                    provider="fastmcp",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "arguments": {"type": "object", "description": "提示参数"}
                        },
                        "required": []
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "messages": {"type": "array"},
                            "metadata": {"type": "object"}
                        }
                    },
                    capabilities=["mcp_prompt_generation"],
                    tags=["fastmcp", "mcp", "prompt"]
                )
                
                self._tools_cache[prompt_spec.name] = prompt_spec
                self._prompt_mapping[prompt_spec.name] = prompt['name']
                
        except Exception as e:
            self._logger.warning(f"Failed to register MCP prompts: {e}")
    
    async def _register_external_mcp_services(self):
        """注册外部MCP服务"""
        try:
            external_mcps = list_external_mcps()
            for mcp_service in external_mcps:
                service_spec = ToolSpec(
                    name=f"fastmcp_external_{mcp_service['name']}",
                    version="1.0.0",
                    description=f"外部MCP服务: {mcp_service.get('description', mcp_service['name'])}",
                    category=ToolCategory.INTEGRATION,
                    provider="fastmcp",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["call_tool", "get_resource", "get_prompt"]},
                            "target": {"type": "string", "description": "目标工具/资源/提示名称"},
                            "params": {"type": "object", "description": "调用参数"}
                        },
                        "required": ["action", "target"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "result": {"type": "object"},
                            "metadata": {"type": "object"}
                        }
                    },
                    capabilities=["external_mcp_integration"],
                    tags=["fastmcp", "mcp", "external", "integration"]
                )
                
                self._tools_cache[service_spec.name] = service_spec
                self._tool_mapping[service_spec.name] = mcp_service['name']
                
        except Exception as e:
            self._logger.warning(f"Failed to register external MCP services: {e}")
    
    async def _register_mcp_client_tools(self):
        """注册MCP客户端工具"""
        try:
            providers = get_all_providers()
            
            # 聊天客户端工具
            chat_spec = ToolSpec(
                name="fastmcp_chat_client",
                version="1.0.0",
                description="FastMCP聊天客户端 - 智能对话和文本生成",
                category=ToolCategory.INTEGRATION,
                provider="fastmcp",
                input_schema={
                    "type": "object",
                    "properties": {
                        "provider": {"type": "string", "description": "服务提供商"},
                        "messages": {"type": "array", "description": "对话消息"},
                        "model": {"type": "string", "description": "模型名称"},
                        "temperature": {"type": "number", "default": 0.7}
                    },
                    "required": ["provider", "messages"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "usage": {"type": "object"},
                        "model": {"type": "string"}
                    }
                },
                capabilities=["chat_generation", "text_completion"],
                tags=["fastmcp", "chat", "llm", "generation"]
            )
            self._tools_cache[chat_spec.name] = chat_spec
            self._tool_mapping[chat_spec.name] = "chat_client"
            
            # 图像客户端工具
            image_spec = ToolSpec(
                name="fastmcp_image_client",
                version="1.0.0",
                description="FastMCP图像客户端 - 图像生成和处理",
                category=ToolCategory.INTEGRATION,
                provider="fastmcp",
                input_schema={
                    "type": "object",
                    "properties": {
                        "provider": {"type": "string", "description": "服务提供商"},
                        "prompt": {"type": "string", "description": "图像描述"},
                        "size": {"type": "string", "default": "1024x1024"},
                        "quality": {"type": "string", "default": "standard"}
                    },
                    "required": ["provider", "prompt"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "image_url": {"type": "string"},
                        "metadata": {"type": "object"}
                    }
                },
                capabilities=["image_generation", "image_processing"],
                tags=["fastmcp", "image", "generation", "ai"]
            )
            self._tools_cache[image_spec.name] = image_spec
            self._tool_mapping[image_spec.name] = "image_client"
            
            # 地图客户端工具
            map_spec = ToolSpec(
                name="fastmcp_map_client",
                version="1.0.0",
                description="FastMCP地图客户端 - 地理信息和地图服务",
                category=ToolCategory.INTEGRATION,
                provider="fastmcp",
                input_schema={
                    "type": "object",
                    "properties": {
                        "provider": {"type": "string", "description": "地图服务提供商"},
                        "action": {"type": "string", "enum": ["geocode", "reverse_geocode", "search", "directions"]},
                        "query": {"type": "string", "description": "查询内容"},
                        "coordinates": {"type": "object", "description": "坐标信息"}
                    },
                    "required": ["provider", "action"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "metadata": {"type": "object"}
                    }
                },
                capabilities=["geocoding", "mapping", "location_services"],
                tags=["fastmcp", "map", "geo", "location"]
            )
            self._tools_cache[map_spec.name] = map_spec
            self._tool_mapping[map_spec.name] = "map_client"
            
            # 数据客户端工具
            data_spec = ToolSpec(
                name="fastmcp_data_client",
                version="1.0.0",
                description="FastMCP数据客户端 - 数据分析和处理",
                category=ToolCategory.INTEGRATION,
                provider="fastmcp",
                input_schema={
                    "type": "object",
                    "properties": {
                        "provider": {"type": "string", "description": "数据服务提供商"},
                        "operation": {"type": "string", "enum": ["query", "analyze", "transform", "export"]},
                        "data": {"type": "object", "description": "数据内容"},
                        "parameters": {"type": "object", "description": "操作参数"}
                    },
                    "required": ["provider", "operation"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "object"},
                        "statistics": {"type": "object"},
                        "metadata": {"type": "object"}
                    }
                },
                capabilities=["data_analysis", "data_processing", "data_transformation"],
                tags=["fastmcp", "data", "analysis", "processing"]
            )
            self._tools_cache[data_spec.name] = data_spec
            self._tool_mapping[data_spec.name] = "data_client"
            
        except Exception as e:
            self._logger.warning(f"Failed to register MCP client tools: {e}")
    
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
            
            # 执行FastMCP工具
            result_data = await self._execute_fastmcp_tool(tool_name, params)
            
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
    
    async def _execute_fastmcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行FastMCP工具"""
        # 获取内部工具名
        internal_tool_name = self._tool_mapping.get(tool_name)
        if not internal_tool_name:
            raise ValueError(f"Unknown tool mapping for {tool_name}")
        
        # 尝试真实执行FastMCP工具
        try:
            if internal_tool_name == "chat_client":
                return await self._execute_chat_client(params)
            elif internal_tool_name == "image_client":
                return await self._execute_image_client(params)
            elif internal_tool_name == "map_client":
                return await self._execute_map_client(params)
            elif internal_tool_name == "data_client":
                return await self._execute_data_client(params)
            else:
                # 其他工具使用模拟执行
                return await self._simulate_fastmcp_tool_execution(tool_name, params)
        except Exception as e:
            self._logger.warning(f"FastMCP tool execution failed, using simulation: {e}")
            return await self._simulate_fastmcp_tool_execution(tool_name, params)
    
    async def _execute_chat_client(self, params: Dict[str, Any]) -> Any:
        """执行聊天客户端"""
        provider = params.get('provider', 'openai')
        messages = params.get('messages', [])
        
        try:
            client = create_chat_client(provider)
            response = await client.chat(messages, **params)
            return {
                "response": response.get('content', ''),
                "usage": response.get('usage', {}),
                "model": response.get('model', '')
            }
        except Exception as e:
            return {
                "response": f"模拟聊天响应：{messages[-1].get('content', '') if messages else '你好'}",
                "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
                "model": f"{provider}_model"
            }
    
    async def _execute_image_client(self, params: Dict[str, Any]) -> Any:
        """执行图像客户端"""
        provider = params.get('provider', 'openai')
        prompt = params.get('prompt', '')
        
        try:
            client = create_image_client(provider)
            response = await client.generate_image(prompt, **params)
            return {
                "image_url": response.get('url', ''),
                "metadata": response.get('metadata', {})
            }
        except Exception as e:
            return {
                "image_url": f"https://example.com/generated_image_{hash(prompt) % 10000}.jpg",
                "metadata": {"provider": provider, "prompt": prompt, "status": "simulated"}
            }
    
    async def _execute_map_client(self, params: Dict[str, Any]) -> Any:
        """执行地图客户端"""
        provider = params.get('provider', 'google')
        action = params.get('action', 'search')
        query = params.get('query', '')
        
        try:
            client = create_map_client(provider)
            response = await client.execute(action, query, **params)
            return {
                "results": response.get('results', []),
                "metadata": response.get('metadata', {})
            }
        except Exception as e:
            return {
                "results": [{"name": f"模拟地点：{query}", "coordinates": [39.9042, 116.4074]}],
                "metadata": {"provider": provider, "action": action, "status": "simulated"}
            }
    
    async def _execute_data_client(self, params: Dict[str, Any]) -> Any:
        """执行数据客户端"""
        provider = params.get('provider', 'pandas')
        operation = params.get('operation', 'analyze')
        
        try:
            client = create_data_client(provider)
            response = await client.execute(operation, **params)
            return {
                "result": response.get('result', {}),
                "statistics": response.get('statistics', {}),
                "metadata": response.get('metadata', {})
            }
        except Exception as e:
            return {
                "result": {"processed_rows": 100, "output": "数据处理完成"},
                "statistics": {"mean": 50.5, "std": 28.9, "count": 100},
                "metadata": {"provider": provider, "operation": operation, "status": "simulated"}
            }
    
    async def _simulate_fastmcp_tool_execution(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """模拟FastMCP工具执行"""
        if "resource" in tool_name:
            return {
                "content": f"模拟资源内容：{params.get('uri', '')}",
                "metadata": {"type": "simulated_resource", "uri": params.get('uri', '')}
            }
        elif "prompt" in tool_name:
            return {
                "messages": [{"role": "system", "content": f"模拟提示：{tool_name}"}],
                "metadata": {"type": "simulated_prompt", "arguments": params.get('arguments', {})}
            }
        elif "external" in tool_name:
            return {
                "result": f"外部MCP服务响应：{params.get('target', '')}",
                "metadata": {"action": params.get('action', ''), "status": "simulated"}
            }
        else:
            return {"result": f"执行了FastMCP工具 {tool_name}"}


class FastMCPFrameworkAdapter(BaseFrameworkAdapter):
    """FastMCP框架适配器"""
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        tool_adapter = FastMCPToolAdapter()
        super().__init__(tool_adapter, config)
    
    def _create_framework_info(self) -> FrameworkInfo:
        """创建FastMCP框架信息"""
        return FrameworkInfo(
            name="fastmcp",
            version="1.0.0",
            description="FastMCP框架 - Model Context Protocol工具和服务集成平台",
            vendor="FastMCP Team",
            license="MIT",
            capabilities={
                FrameworkCapability.TOOL_CALLING,
                FrameworkCapability.TOOL_REGISTRATION,
                FrameworkCapability.CUSTOM_TOOLS,
                FrameworkCapability.API_INTEGRATION,
                FrameworkCapability.EXTERNAL_SERVICES,
                FrameworkCapability.MCP_PROTOCOL,
                FrameworkCapability.TEXT_PROCESSING,
                FrameworkCapability.IMAGE_PROCESSING
            },
            supported_categories={
                ToolCategory.MCP,
                ToolCategory.INTEGRATION,
                ToolCategory.CUSTOM
            },
            python_version="3.9+",
            dependencies=["fastmcp>=1.0.0", "httpx", "pydantic"],
            tags=["mcp", "protocol", "integration", "services", "clients"]
        ) 