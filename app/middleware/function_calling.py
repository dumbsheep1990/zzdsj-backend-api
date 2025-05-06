"""
Function Calling 适配中间件
为任意模型提供统一的工具调用能力，支持原生 function calling 和链式调用两种方式
"""

import json
import inspect
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Callable, Type, Tuple

from pydantic import BaseModel, Field, create_model
from llama_index.core.llms import LLM, ChatMessage, MessageRole
from llama_index.core.agent import FunctionCallingAgentWorker
from llama_index.core.tools import BaseTool, FunctionTool, ToolMetadata
from llama_index.core.callbacks import CallbackManager
from llama_index.core.bridge.pydantic import BaseModel as LlamaIndexBaseModel

from app.config import settings
from app.middleware.tool_utils import get_all_tools
from app.middleware.search_tool import get_search_tool

logger = logging.getLogger(__name__)

class FunctionCallingStrategy(str, Enum):
    """Function Calling 策略枚举"""
    NATIVE = "native"  # 原生支持 function calling
    CHAIN = "chain"    # 链式调用（模型生成JSON -> 解析 -> 调用）
    AUTO = "auto"      # 自动选择最佳策略

class FunctionCallingConfig(BaseModel):
    """Function Calling 配置"""
    strategy: FunctionCallingStrategy = Field(
        default=FunctionCallingStrategy.AUTO,
        description="Function Calling 策略"
    )
    max_function_calls: int = Field(
        default=5,
        description="最大函数调用次数，防止无限循环"
    )
    max_iterations: int = Field(
        default=10,
        description="最大迭代次数，防止无限循环"
    )
    verbose: bool = Field(
        default=False,
        description="是否输出详细日志"
    )

class FunctionCallingAdapter:
    """Function Calling 适配器，提供统一的工具调用能力"""

    def __init__(
        self,
        llm: LLM,
        tools: Optional[List[BaseTool]] = None,
        config: Optional[FunctionCallingConfig] = None,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        初始化 Function Calling 适配器
        
        参数:
            llm: 语言模型实例
            tools: 工具列表，如果为None则使用get_all_tools获取
            config: 配置，如果为None则使用默认配置
            callback_manager: 回调管理器
        """
        self.llm = llm
        self.tools = tools if tools is not None else get_all_tools()
        self.config = config if config is not None else FunctionCallingConfig()
        self.callback_manager = callback_manager
        
        # 确定策略
        if self.config.strategy == FunctionCallingStrategy.AUTO:
            self.effective_strategy = self._detect_model_capability()
        else:
            self.effective_strategy = self.config.strategy
            
        # 创建对应的处理器
        if self.effective_strategy == FunctionCallingStrategy.NATIVE:
            from llama_index.core.agent import FunctionCallingAgentWorker
            self.agent_worker = FunctionCallingAgentWorker.from_tools(
                tools=self.tools,
                llm=self.llm,
                verbose=self.config.verbose,
                callback_manager=self.callback_manager
            )
        else:
            self.tool_map = {tool.metadata.name: tool for tool in self.tools}
            
        logger.info(f"使用 Function Calling 策略: {self.effective_strategy}")
    
    def _detect_model_capability(self) -> FunctionCallingStrategy:
        """
        检测模型是否原生支持 function calling
        
        返回:
            FunctionCallingStrategy: 检测到的策略
        """
        model_type = getattr(self.llm, "model", "")
        model_type = model_type.lower() if isinstance(model_type, str) else ""
        
        # 已知支持 function calling 的模型
        native_function_calling_models = [
            "gpt-4", "gpt-3.5", "claude-3", "gemini", "qwen", "glm-4", "llama-3",
            "chatglm", "minimax", "azure-openai", "anthropic", "ernie", "qwen-vl",
            "spark", "moonshot", "baichuan", "yi", "mixtral"
        ]
        
        # 检测模型类型
        for model_prefix in native_function_calling_models:
            if model_prefix in model_type:
                return FunctionCallingStrategy.NATIVE
        
        # 检测模型方法
        if hasattr(self.llm, "function_calling") or hasattr(self.llm, "supports_function_calling"):
            if getattr(self.llm, "supports_function_calling", False):
                return FunctionCallingStrategy.NATIVE
                
        # 默认使用链式调用
        return FunctionCallingStrategy.CHAIN
    
    async def arun(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[BaseTool]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        异步执行 function calling
        
        参数:
            messages: 对话消息列表
            tools: 可选的工具列表，如果提供则覆盖初始化时的工具
            
        返回:
            Tuple[str, Optional[Dict[str, Any]]]: (响应文本, 工具调用结果)
        """
        active_tools = tools if tools is not None else self.tools
        
        if self.effective_strategy == FunctionCallingStrategy.NATIVE:
            # 使用原生 function calling
            if tools is not None:
                # 如果提供了新的工具列表，需要重新创建 agent worker
                agent = FunctionCallingAgentWorker.from_tools(
                    tools=active_tools,
                    llm=self.llm,
                    verbose=self.config.verbose,
                    callback_manager=self.callback_manager
                )
            else:
                agent = self.agent_worker
                
            try:
                response = await agent.achat(messages)
                return response.response, response.sources if hasattr(response, "sources") else None
            except Exception as e:
                logger.error(f"原生 function calling 执行失败: {str(e)}")
                # 失败时降级到链式调用
                return await self._achain_call(messages, active_tools)
        else:
            # 使用链式调用
            return await self._achain_call(messages, active_tools)
    
    async def _achain_call(
        self,
        messages: List[ChatMessage],
        tools: List[BaseTool]
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        执行链式调用（模型生成JSON -> 解析 -> 调用）
        
        参数:
            messages: 对话消息列表
            tools: 工具列表
            
        返回:
            Tuple[str, Optional[Dict[str, Any]]]: (响应文本, 工具调用结果)
        """
        # 构建工具描述
        tool_descriptions = []
        for tool in tools:
            tool_descriptions.append({
                "name": tool.metadata.name,
                "description": tool.metadata.description,
                "parameters": self._get_tool_parameters(tool)
            })
        
        # 添加工具描述到系统消息
        system_message = None
        user_messages = []
        other_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg
            elif msg.role == MessageRole.USER:
                user_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # 如果没有系统消息，创建一个
        if system_message is None:
            system_message = ChatMessage(
                role=MessageRole.SYSTEM,
                content="你是一个有用的AI助手。"
            )
        
        # 增强系统消息，添加工具描述和使用说明
        enhanced_system_content = (
            f"{system_message.content}\n\n"
            "你可以使用以下工具来辅助回答：\n\n"
            f"{json.dumps(tool_descriptions, ensure_ascii=False, indent=2)}\n\n"
            "当你需要使用工具时，请使用以下JSON格式响应：\n"
            "```json\n"
            "{\n"
            '  "tool": "工具名称",\n'
            '  "parameters": {\n'
            '    "参数1": "值1",\n'
            '    "参数2": "值2"\n'
            "  }\n"
            "}\n"
            "```\n"
            "如果你不需要使用工具，直接用普通文本回答即可。"
        )
        
        enhanced_system_message = ChatMessage(
            role=MessageRole.SYSTEM,
            content=enhanced_system_content
        )
        
        # 重新构建消息列表
        enhanced_messages = [enhanced_system_message] + other_messages + user_messages
        
        # 执行对话
        iterations = 0
        response_text = ""
        tool_results = {}
        
        while iterations < self.config.max_iterations:
            iterations += 1
            
            # 调用模型
            response = await self.llm.achat(enhanced_messages)
            response_text = response.message.content
            
            # 尝试解析JSON工具调用
            tool_call = self._extract_tool_call(response_text)
            
            if tool_call is None:
                # 没有工具调用，直接返回
                break
            
            tool_name = tool_call.get("tool")
            parameters = tool_call.get("parameters", {})
            
            if not tool_name or tool_name not in self.tool_map:
                # 无效的工具调用
                response_text = f"抱歉，我找不到名为 '{tool_name}' 的工具。请直接回答问题或使用可用的工具。"
                break
            
            # 执行工具调用
            tool = self.tool_map[tool_name]
            try:
                tool_result = await self._aexecute_tool(tool, parameters)
                tool_results[tool_name] = tool_result
                
                # 添加工具结果消息
                enhanced_messages.append(ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=json.dumps(tool_call, ensure_ascii=False)
                ))
                
                enhanced_messages.append(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=f"工具 '{tool_name}' 执行结果：\n{tool_result}"
                ))
                
                # 添加最后一个用户消息，让模型生成最终回答
                if iterations == self.config.max_iterations - 1:
                    enhanced_messages.append(ChatMessage(
                        role=MessageRole.SYSTEM,
                        content="请根据以上工具执行结果，给出完整的回答。不要再使用工具，直接用自然语言回复。"
                    ))
            except Exception as e:
                logger.error(f"工具 '{tool_name}' 执行失败: {str(e)}")
                enhanced_messages.append(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=f"工具 '{tool_name}' 执行失败: {str(e)}。请尝试使用其他方法回答问题。"
                ))
        
        return response_text, tool_results if tool_results else None
    
    def _extract_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从响应文本中提取工具调用JSON
        
        参数:
            text: 响应文本
            
        返回:
            Optional[Dict[str, Any]]: 解析后的工具调用，如果没有则为None
        """
        # 尝试提取 ```json ... ``` 格式
        json_blocks = []
        lines = text.split("\n")
        in_json_block = False
        current_block = []
        
        for line in lines:
            if line.strip().startswith("```json") or line.strip().startswith("```"):
                in_json_block = True
                current_block = []
            elif in_json_block and line.strip().startswith("```"):
                in_json_block = False
                json_blocks.append("\n".join(current_block))
            elif in_json_block:
                current_block.append(line)
        
        # 尝试解析提取到的JSON块
        for block in json_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and "tool" in data:
                    return data
            except json.JSONDecodeError:
                continue
        
        # 尝试解析整个文本作为JSON
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict) and "tool" in data:
                return data
        except json.JSONDecodeError:
            pass
            
        return None
    
    async def _aexecute_tool(self, tool: BaseTool, parameters: Dict[str, Any]) -> str:
        """
        异步执行工具调用
        
        参数:
            tool: 工具实例
            parameters: 调用参数
            
        返回:
            str: 工具执行结果
        """
        if hasattr(tool, '_arun'):
            # 异步调用
            try:
                return await tool._arun(**parameters)
            except Exception as e:
                logger.error(f"异步工具执行失败: {str(e)}")
                raise
        else:
            # 同步调用
            try:
                return tool._run(**parameters)
            except Exception as e:
                logger.error(f"同步工具执行失败: {str(e)}")
                raise
    
    def _get_tool_parameters(self, tool: BaseTool) -> Dict[str, Any]:
        """
        获取工具参数描述
        
        参数:
            tool: 工具实例
            
        返回:
            Dict[str, Any]: 参数描述
        """
        parameters = {}
        
        if isinstance(tool, FunctionTool):
            # 对于函数工具，使用函数签名
            sig = inspect.signature(tool.fn)
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                    
                param_type = param.annotation
                param_default = None if param.default is inspect.Parameter.empty else param.default
                
                param_desc = {
                    "type": "string",  # 默认类型
                    "description": f"参数 {name}"
                }
                
                # 尝试获取类型信息
                if param_type is not inspect.Parameter.empty:
                    if param_type is str:
                        param_desc["type"] = "string"
                    elif param_type is int:
                        param_desc["type"] = "integer"
                    elif param_type is float:
                        param_desc["type"] = "number"
                    elif param_type is bool:
                        param_desc["type"] = "boolean"
                    elif param_type is list or param_type is List:
                        param_desc["type"] = "array"
                    elif param_type is dict or param_type is Dict:
                        param_desc["type"] = "object"
                
                # 设置默认值
                if param_default is not None:
                    param_desc["default"] = param_default
                
                parameters[name] = param_desc
        else:
            # 对于其他工具，尝试从元数据获取参数信息
            if hasattr(tool, "metadata") and hasattr(tool.metadata, "fn_schema"):
                schema = tool.metadata.fn_schema
                if schema and "parameters" in schema:
                    return schema["parameters"]
        
        return parameters
    
    def run(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[BaseTool]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        同步执行 function calling（包装异步方法）
        
        参数:
            messages: 对话消息列表
            tools: 可选的工具列表，如果提供则覆盖初始化时的工具
            
        返回:
            Tuple[str, Optional[Dict[str, Any]]]: (响应文本, 工具调用结果)
        """
        import asyncio
        return asyncio.run(self.arun(messages, tools))


def create_function_calling_adapter(
    llm: LLM,
    tools: Optional[List[BaseTool]] = None,
    config: Optional[Dict[str, Any]] = None,
    callback_manager: Optional[CallbackManager] = None
) -> FunctionCallingAdapter:
    """
    创建 Function Calling 适配器
    
    参数:
        llm: 语言模型实例
        tools: 工具列表，如果为None则使用get_all_tools获取
        config: 配置，如果为None则使用默认配置
        callback_manager: 回调管理器
        
    返回:
        FunctionCallingAdapter: 适配器实例
    """
    function_calling_config = FunctionCallingConfig(**(config or {}))
    return FunctionCallingAdapter(
        llm=llm,
        tools=tools,
        config=function_calling_config,
        callback_manager=callback_manager
    )
