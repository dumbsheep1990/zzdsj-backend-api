"""
Haystack框架适配器实现
集成Haystack文档阅读和提取式问答功能到统一工具系统
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

# 导入Haystack框架组件
try:
    from ..frameworks.haystack.reader import extract_answers, answer_with_references
    HAYSTACK_AVAILABLE = True
except ImportError:
    # 如果导入失败，提供模拟实现
    HAYSTACK_AVAILABLE = False
    def extract_answers(question, contexts, model_name=None, top_k=3):
        return []
    def answer_with_references(question, contexts, model_name=None, top_k=3):
        return "", []


class HaystackToolAdapter(BaseToolAdapter):
    """Haystack工具适配器 - 集成Haystack文档阅读功能"""
    
    def __init__(self):
        # Haystack支持的工具分类
        supported_categories = [
            ToolCategory.REASONING,    # 推理工具
            ToolCategory.KNOWLEDGE     # 知识处理工具
        ]
        
        super().__init__("haystack", supported_categories)
        
        # 工具映射表
        self._tool_mapping: Dict[str, str] = {}
        
    async def _do_initialize(self):
        """初始化Haystack工具适配器"""
        try:
            # 发现并注册Haystack工具
            await self._discover_and_register_haystack_tools()
            
            self._logger.info("Haystack adapter initialized with document reading tools")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize Haystack tools: {e}")
            raise AdapterError(f"Haystack initialization failed: {e}", "HAYSTACK_INIT_ERROR", e)
    
    async def _do_shutdown(self):
        """清理Haystack资源"""
        self._tool_mapping.clear()
    
    async def _discover_and_register_haystack_tools(self):
        """发现并注册Haystack工具"""
        
        # 注册提取式问答工具
        extract_qa_spec = ToolSpec(
            name="haystack_extract_answers",
            version="1.0.0",
            description="Haystack提取式问答 - 从文档上下文中提取精确答案",
            category=ToolCategory.REASONING,
            provider="haystack",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string", 
                        "description": "要回答的问题"
                    },
                    "contexts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "上下文内容"},
                                "metadata": {"type": "object", "description": "元数据"}
                            },
                            "required": ["content"]
                        },
                        "description": "文档上下文列表"
                    },
                    "model_name": {
                        "type": "string", 
                        "description": "可选的模型名称"
                    },
                    "top_k": {
                        "type": "integer", 
                        "default": 3,
                        "description": "返回的答案数量"
                    }
                },
                "required": ["question", "contexts"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "answer": {"type": "string"},
                                "score": {"type": "number"},
                                "context": {"type": "string"},
                                "document_id": {"type": "string"},
                                "start_idx": {"type": "integer"},
                                "end_idx": {"type": "integer"}
                            }
                        }
                    }
                }
            },
            capabilities=["extractive_qa", "document_reading", "answer_extraction"],
            tags=["haystack", "qa", "extraction", "reading", "nlp"]
        )
        
        self._tools_cache[extract_qa_spec.name] = extract_qa_spec
        self._tool_mapping[extract_qa_spec.name] = "extract_answers"
        
        # 注册带参考的问答工具
        ref_qa_spec = ToolSpec(
            name="haystack_answer_with_references",
            version="1.0.0", 
            description="Haystack带参考问答 - 提供答案和支持参考文档",
            category=ToolCategory.KNOWLEDGE,
            provider="haystack",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "要回答的问题"
                    },
                    "contexts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "上下文内容"},
                                "metadata": {"type": "object", "description": "元数据"}
                            },
                            "required": ["content"]
                        },
                        "description": "文档上下文列表"
                    },
                    "model_name": {
                        "type": "string",
                        "description": "可选的模型名称"
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 3,
                        "description": "要考虑的答案数量"
                    }
                },
                "required": ["question", "contexts"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "最佳答案"},
                    "references": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "relevance": {"type": "number"},
                                "document_id": {"type": "string"},
                                "highlight_start": {"type": "integer"},
                                "highlight_end": {"type": "integer"}
                            }
                        },
                        "description": "支持参考列表"
                    }
                }
            },
            capabilities=["qa_with_references", "document_reading", "citation_generation"],
            tags=["haystack", "qa", "references", "citations", "nlp"]
        )
        
        self._tools_cache[ref_qa_spec.name] = ref_qa_spec
        self._tool_mapping[ref_qa_spec.name] = "answer_with_references"
    
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
            
            # 执行Haystack工具
            result_data = await self._execute_haystack_tool(tool_name, params)
            
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
    
    async def _execute_haystack_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行Haystack工具"""
        # 获取内部工具名
        internal_tool_name = self._tool_mapping.get(tool_name)
        if not internal_tool_name:
            raise ValueError(f"Unknown tool mapping for {tool_name}")
        
        # 尝试真实执行Haystack工具
        try:
            if HAYSTACK_AVAILABLE:
                if internal_tool_name == "extract_answers":
                    return await self._execute_extract_answers(params)
                elif internal_tool_name == "answer_with_references":
                    return await self._execute_answer_with_references(params)
                else:
                    raise ValueError(f"Unknown Haystack tool: {internal_tool_name}")
            else:
                return await self._simulate_haystack_tool_execution(tool_name, params)
        except Exception as e:
            self._logger.warning(f"Haystack tool execution failed, using simulation: {e}")
            return await self._simulate_haystack_tool_execution(tool_name, params)
    
    async def _execute_extract_answers(self, params: Dict[str, Any]) -> Any:
        """执行提取式问答"""
        question = params.get('question', '')
        contexts = params.get('contexts', [])
        model_name = params.get('model_name')
        top_k = params.get('top_k', 3)
        
        # 在线程池中执行同步函数
        loop = asyncio.get_event_loop()
        answers = await loop.run_in_executor(
            None, extract_answers, question, contexts, model_name, top_k
        )
        
        return {"answers": answers}
    
    async def _execute_answer_with_references(self, params: Dict[str, Any]) -> Any:
        """执行带参考的问答"""
        question = params.get('question', '')
        contexts = params.get('contexts', [])
        model_name = params.get('model_name')
        top_k = params.get('top_k', 3)
        
        # 在线程池中执行同步函数
        loop = asyncio.get_event_loop()
        answer, references = await loop.run_in_executor(
            None, answer_with_references, question, contexts, model_name, top_k
        )
        
        return {
            "answer": answer,
            "references": references
        }
    
    async def _simulate_haystack_tool_execution(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """模拟Haystack工具执行"""
        question = params.get('question', '')
        contexts = params.get('contexts', [])
        
        if "extract_answers" in tool_name:
            # 模拟提取式问答
            simulated_answers = []
            for i, ctx in enumerate(contexts[:3]):  # 最多返回3个答案
                answer_text = f"模拟答案{i+1}：基于{question}的回答"
                simulated_answers.append({
                    "answer": answer_text,
                    "score": 0.9 - i * 0.1,
                    "context": ctx.get('content', '')[:200] + "...",
                    "document_id": f"doc_{i}",
                    "start_idx": 0,
                    "end_idx": len(answer_text)
                })
            
            return {"answers": simulated_answers}
        
        elif "answer_with_references" in tool_name:
            # 模拟带参考的问答
            best_answer = f"模拟答案：{question}的回答基于提供的上下文"
            
            references = []
            for i, ctx in enumerate(contexts[:3]):
                references.append({
                    "content": ctx.get('content', '')[:300] + "...",
                    "relevance": 0.9 - i * 0.1,
                    "document_id": f"ref_doc_{i}",
                    "highlight_start": 0,
                    "highlight_end": 50
                })
            
            return {
                "answer": best_answer,
                "references": references
            }
        
        else:
            return {"result": f"执行了Haystack工具 {tool_name}"}


class HaystackFrameworkAdapter(BaseFrameworkAdapter):
    """Haystack框架适配器"""
    
    def __init__(self, config: Optional[FrameworkConfig] = None):
        tool_adapter = HaystackToolAdapter()
        super().__init__(tool_adapter, config)
    
    def _create_framework_info(self) -> FrameworkInfo:
        """创建Haystack框架信息"""
        return FrameworkInfo(
            name="haystack",
            version="1.21.0",
            description="Haystack框架 - 文档阅读和提取式问答专家",
            vendor="deepset",
            license="Apache 2.0",
            capabilities={
                FrameworkCapability.TOOL_CALLING,
                FrameworkCapability.DOCUMENT_PROCESSING,
                FrameworkCapability.QUESTION_ANSWERING,
                FrameworkCapability.TEXT_PROCESSING,
                FrameworkCapability.KNOWLEDGE_EXTRACTION
            },
            supported_categories={
                ToolCategory.REASONING,
                ToolCategory.KNOWLEDGE
            },
            python_version="3.8+",
            dependencies=["haystack-ai>=1.21.0", "transformers", "torch"],
            tags=["nlp", "qa", "document", "reading", "extraction"]
        ) 