"""
思维链(Chain of Thought)管理器模块
提供统一的CoT调用和管理接口，支持不同模型的CoT能力适配
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import json

from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.callbacks import CallbackManager
from llama_index.core.llms.base import CompletionResponse, ChatResponse, LLM

from app.middleware.cot_parser import InducedCoTParser, MultiStepCoTParser

logger = logging.getLogger(__name__)

# 默认标签设置
DEFAULT_COT_START_TAG = "<THINK>"
DEFAULT_COT_END_TAG = "</THINK>"
DEFAULT_ANS_START_TAG = "<ANSWER>"
DEFAULT_ANS_END_TAG = "</ANSWER>"

class CoTManager:
    """
    思维链管理器
    提供统一的接口来处理不同模型的CoT能力，支持手动诱导CoT或使用原生CoT
    """
    
    def __init__(
        self,
        llm: Optional[LLM] = None,
        cot_tags: Optional[Dict[str, str]] = None,
        enable_structured_output: bool = True,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        初始化CoT管理器
        
        参数:
            llm: 语言模型实例，如果为None则使用全局设置的LLM
            cot_tags: 自定义CoT标签，如果为None则使用默认标签
            enable_structured_output: 是否启用结构化输出解析
            callback_manager: 回调管理器，用于事件通知
        """
        self.llm = llm or Settings.llm
        self.callback_manager = callback_manager
        self.enable_structured_output = enable_structured_output
        
        # 设置CoT标签
        self.cot_tags = cot_tags or {
            "cot_start_tag": DEFAULT_COT_START_TAG,
            "cot_end_tag": DEFAULT_COT_END_TAG,
            "answer_start_tag": DEFAULT_ANS_START_TAG,
            "answer_end_tag": DEFAULT_ANS_END_TAG
        }
        
        # 初始化解析器
        self.cot_parser = InducedCoTParser(
            cot_start_tag=self.cot_tags["cot_start_tag"],
            cot_end_tag=self.cot_tags["cot_end_tag"],
            answer_start_tag=self.cot_tags["answer_start_tag"],
            answer_end_tag=self.cot_tags["answer_end_tag"]
        )
        
        self.multi_step_parser = MultiStepCoTParser()
        
        # 检查模型是否原生支持CoT
        self.supports_native_cot = self._check_native_cot_support()
    
    def _check_native_cot_support(self) -> bool:
        """
        检查当前模型是否原生支持CoT
        
        返回:
            是否支持CoT的布尔值
        """
        # 根据模型名称或元数据判断是否支持原生CoT
        # 例如 GPT-4、Claude 2等模型支持原生CoT
        model_name = getattr(self.llm, "model", "")
        model_name = model_name.lower() if model_name else ""
        
        # 已知支持CoT的模型列表
        cot_supported_models = [
            "gpt-4", "gpt-4-turbo", "gpt-4-32k", 
            "claude-2", "claude-3", 
            "gemini-pro", "gemini-ultra",
            "qwen-", "glm-4", "yi-34b", "llama-3"
        ]
        
        return any(supported_model in model_name for supported_model in cot_supported_models)
    
    def get_cot_instruction(self) -> str:
        """
        获取CoT指令提示
        
        返回:
            CoT指令字符串
        """
        return self.cot_parser.format()
    
    def get_multi_step_instruction(self) -> str:
        """
        获取多步骤CoT指令提示
        
        返回:
            多步骤CoT指令字符串
        """
        return self.multi_step_parser.format()
    
    async def acall_with_cot(
        self,
        prompt_content: str,
        system_prompt: Optional[str] = None,
        enable_cot: bool = True,
        use_multi_step: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        additional_kwargs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步调用LLM并获取带CoT的响应
        
        参数:
            prompt_content: 主要提示内容
            system_prompt: 系统提示，如果为None则使用默认提示
            enable_cot: 是否启用CoT功能
            use_multi_step: 是否使用多步骤CoT格式
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            additional_kwargs: 传递给LLM的其他参数
        
        返回:
            包含cot_steps和final_answer的字典
        """
        # 准备参数
        kwargs = additional_kwargs or {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        
        # 准备系统提示
        base_system_prompt = system_prompt or "你是一个有用的AI助手。"
        current_system_prompt = base_system_prompt
        
        # 如果启用CoT且模型不支持原生CoT，则添加CoT指令
        if enable_cot and not self.supports_native_cot:
            cot_instruction = self.multi_step_parser.format() if use_multi_step else self.cot_parser.format()
            current_system_prompt = f"{base_system_prompt}\n\n{cot_instruction}"
        
        # 准备消息
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=current_system_prompt),
            ChatMessage(role=MessageRole.USER, content=prompt_content),
        ]
        
        try:
            # 调用LLM
            chat_response = await self.llm.achat(messages, **kwargs)
            raw_llm_output = chat_response.message.content
            
            # 解析输出
            if use_multi_step:
                parsed_output = self.multi_step_parser.parse(raw_llm_output)
            else:
                parsed_output = self.cot_parser.parse(raw_llm_output)
            
            # 添加原始输出
            parsed_output["raw_output"] = raw_llm_output
            
            return parsed_output
            
        except Exception as e:
            logger.error(f"调用LLM或解析CoT时出错: {str(e)}")
            # 出错时返回空结果
            if use_multi_step:
                return {
                    "steps": [],
                    "final_answer": f"处理请求时出错: {str(e)}",
                    "raw_output": ""
                }
            else:
                return {
                    "cot_steps": "",
                    "final_answer": f"处理请求时出错: {str(e)}",
                    "raw_output": ""
                }
    
    def call_with_cot(
        self,
        prompt_content: str,
        system_prompt: Optional[str] = None,
        enable_cot: bool = True,
        use_multi_step: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        additional_kwargs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        同步调用LLM并获取带CoT的响应
        
        参数:
            prompt_content: 主要提示内容
            system_prompt: 系统提示，如果为None则使用默认提示
            enable_cot: 是否启用CoT功能
            use_multi_step: 是否使用多步骤CoT格式
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            additional_kwargs: 传递给LLM的其他参数
        
        返回:
            包含cot_steps和final_answer的字典
        """
        # 准备参数
        kwargs = additional_kwargs or {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        
        # 准备系统提示
        base_system_prompt = system_prompt or "你是一个有用的AI助手。"
        current_system_prompt = base_system_prompt
        
        # 如果启用CoT且模型不支持原生CoT，则添加CoT指令
        if enable_cot and not self.supports_native_cot:
            cot_instruction = self.multi_step_parser.format() if use_multi_step else self.cot_parser.format()
            current_system_prompt = f"{base_system_prompt}\n\n{cot_instruction}"
        
        # 准备消息
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=current_system_prompt),
            ChatMessage(role=MessageRole.USER, content=prompt_content),
        ]
        
        try:
            # 调用LLM
            chat_response = self.llm.chat(messages, **kwargs)
            raw_llm_output = chat_response.message.content
            
            # 解析输出
            if use_multi_step:
                parsed_output = self.multi_step_parser.parse(raw_llm_output)
            else:
                parsed_output = self.cot_parser.parse(raw_llm_output)
            
            # 添加原始输出
            parsed_output["raw_output"] = raw_llm_output
            
            return parsed_output
            
        except Exception as e:
            logger.error(f"调用LLM或解析CoT时出错: {str(e)}")
            # 出错时返回空结果
            if use_multi_step:
                return {
                    "steps": [],
                    "final_answer": f"处理请求时出错: {str(e)}",
                    "raw_output": ""
                }
            else:
                return {
                    "cot_steps": "",
                    "final_answer": f"处理请求时出错: {str(e)}",
                    "raw_output": ""
                }
    
    def format_response_for_api(
        self, 
        response_data: Dict[str, Any],
        show_cot: bool = True
    ) -> Dict[str, Any]:
        """
        将内部响应格式化为API响应格式
        
        参数:
            response_data: 内部响应数据
            show_cot: 是否在响应中包含CoT数据
        
        返回:
            格式化的API响应
        """
        # 格式化多步骤CoT响应
        if "steps" in response_data:
            formatted_response = {
                "final_answer": response_data.get("final_answer", ""),
                "show_cot": show_cot
            }
            
            if show_cot:
                formatted_response["cot_data"] = {
                    "type": "multi_step",
                    "steps": response_data.get("steps", [])
                }
            
            return formatted_response
        
        # 格式化标准CoT响应
        else:
            formatted_response = {
                "final_answer": response_data.get("final_answer", ""),
                "show_cot": show_cot
            }
            
            if show_cot and response_data.get("cot_steps"):
                formatted_response["cot_data"] = {
                    "type": "standard",
                    "cot_steps": response_data.get("cot_steps", "")
                }
            
            return formatted_response
