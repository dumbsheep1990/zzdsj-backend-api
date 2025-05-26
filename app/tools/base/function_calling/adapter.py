"""
Function Calling 适配工具
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
from app.tools.base.utils.tool_utils import get_all_tools
from app.tools.base.search import get_search_tool

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
        
        # 构建包含工具描述的系统消息
        if system_message:
            system_content = system_message.content
            if not system_content.endswith("\n"):
                system_content += "\n\n"
            else:
                system_content += "\n"
        else:
            system_content = ""
            
        system_content += "你可以使用以下工具：\n"
        for tool_desc in tool_descriptions:
            system_content += f"- {tool_desc['name']}: {tool_desc['description']}\n"
        
        system_content += "\n当需要使用工具时，请使用以下JSON格式：\n"
        system_content += "```json\n{\n  \"tool\": \"工具名称\",\n  \"parameters\": {\n    \"参数名1\": \"参数值1\",\n    \"参数名2\": \"参数值2\"\n  }\n}\n```\n"
        
        new_system_message = ChatMessage(
            role=MessageRole.SYSTEM,
            content=system_content
        )
        
        # 重建消息列表
        new_messages = [new_system_message] + other_messages + user_messages
        
        # 发送到模型并获取响应
        response = await self.llm.achat(new_messages)
        response_content = response.message.content
        
        # 尝试从响应中提取工具调用JSON
        tool_calls = self._extract_tool_calls(response_content)
        
        if not tool_calls:
            # 没有工具调用，直接返回响应
            return response_content, None
            
        # 执行工具调用并获取结果
        tool_results = {}
        for tool_call in tool_calls[:self.config.max_function_calls]:
            tool_name = tool_call.get("tool")
            parameters = tool_call.get("parameters", {})
            
            if tool_name not in self.tool_map:
                tool_results[tool_name] = f"错误: 工具 '{tool_name}' 不存在"
                continue
                
            tool = self.tool_map[tool_name]
            try:
                # 执行工具调用
                result = await tool.acall(**parameters)
                tool_results[tool_name] = result
            except Exception as e:
                tool_results[tool_name] = f"错误: {str(e)}"
                
        # 构建包含工具结果的新用户消息
        tool_results_message = "工具调用结果：\n\n"
        for tool_name, result in tool_results.items():
            tool_results_message += f"工具: {tool_name}\n结果: {result}\n\n"
            
        new_user_message = ChatMessage(
            role=MessageRole.USER,
            content=tool_results_message
        )
        
        # 发送工具结果到模型获取最终响应
        final_messages = new_messages + [new_user_message]
        final_response = await self.llm.achat(final_messages)
        
        return final_response.message.content, tool_results
        
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        从模型响应中提取工具调用JSON
        
        参数:
            content: 模型响应文本
            
        返回:
            List[Dict[str, Any]]: 工具调用列表
        """
        tool_calls = []
        
        # 查找JSON代码块
        import re
        json_pattern = r"```(?:json)?\s*({[\s\S]*?})```"
        matches = re.findall(json_pattern, content)
        
        for json_str in matches:
            try:
                data = json.loads(json_str)
                if "tool" in data and "parameters" in data:
                    tool_calls.append(data)
            except:
                pass
                
        # 如果没有找到JSON代码块，尝试直接解析整个响应
        if not tool_calls:
            try:
                data = json.loads(content)
                if "tool" in data and "parameters" in data:
                    tool_calls.append(data)
            except:
                pass
                
        return tool_calls
        
    def _get_tool_parameters(self, tool: BaseTool) -> Dict[str, Any]:
        """
        获取工具的参数描述
        
        参数:
            tool: 工具实例
            
        返回:
            Dict[str, Any]: 参数描述
        """
        parameters = {}
        
        if hasattr(tool, "__call__"):
            # 获取__call__方法的签名
            sig = inspect.signature(tool.__call__)
            for name, param in sig.parameters.items():
                if name not in ["self", "kwargs"]:
                    parameters[name] = {
                        "type": "string",
                        "description": f"{name} parameter"
                    }
        
        # 如果是FunctionTool，获取原始函数的签名
        if isinstance(tool, FunctionTool) and hasattr(tool, "fn"):
            sig = inspect.signature(tool.fn)
            for name, param in sig.parameters.items():
                if name not in ["self", "kwargs"]:
                    parameters[name] = {
                        "type": "string",
                        "description": f"{name} parameter"
                    }
                    
                    # 尝试从函数文档中获取参数描述
                    if tool.fn.__doc__:
                        param_pattern = rf":param {name}:\s*([^\n]+)"
                        match = re.search(param_pattern, tool.fn.__doc__)
                        if match:
                            parameters[name]["description"] = match.group(1).strip()
        
        return parameters


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
    config_obj = None
    if config is not None:
        config_obj = FunctionCallingConfig(**config)
        
    return FunctionCallingAdapter(
        llm=llm,
        tools=tools,
        config=config_obj,
        callback_manager=callback_manager
    )
