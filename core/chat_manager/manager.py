"""
聊天管理器: 统一不同模型提供商的聊天接口
支持OpenAI、智谱、DeepSeek、Ollama和VLLM等多种模型
"""
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
import logging
import time
import json
import httpx
import os

from core.model_manager import get_model_client
from app.models.model_provider import ModelProvider, ModelInfo
from app.models.assistant import Assistant
from app.utils.core.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

class ChatManager:
    """统一的聊天管理器，支持多种模型提供商"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_default_provider(self) -> Optional[ModelProvider]:
        """获取默认模型提供商"""
        return self.db.query(ModelProvider).filter(ModelProvider.is_default == True).first()
    
    def get_provider_by_id(self, provider_id: int) -> Optional[ModelProvider]:
        """根据ID获取模型提供商"""
        return self.db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    
    def get_default_model(self, provider_id: int) -> Optional[ModelInfo]:
        """获取提供商的默认模型"""
        return self.db.query(ModelInfo).filter(
            ModelInfo.provider_id == provider_id,
            ModelInfo.is_default == True
        ).first()
    
    def get_model_by_id(self, model_id: int) -> Optional[ModelInfo]:
        """根据ID获取模型信息"""
        return self.db.query(ModelInfo).filter(ModelInfo.id == model_id).first()
    
    def get_model_by_name(self, provider_id: int, model_name: str) -> Optional[ModelInfo]:
        """根据名称获取模型信息"""
        return self.db.query(ModelInfo).filter(
            ModelInfo.provider_id == provider_id,
            ModelInfo.model_id == model_name
        ).first()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model_info: Optional[Union[ModelInfo, str]] = None,
        provider: Optional[ModelProvider] = None,
        assistant: Optional[Assistant] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> Union[str, Any]:
        """
        使用指定模型生成聊天回复
        
        参数:
            messages: 聊天消息列表
            model_info: 模型信息或模型名称
            provider: 模型提供商
            assistant: 助手实例
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式生成
            context: 上下文信息
            
        返回:
            生成的回复
        """
        # 1. 确定使用的提供商和模型
        if provider is None:
            provider = self.get_default_provider()
            if provider is None:
                raise ValueError("未找到默认模型提供商")
        
        if model_info is None:
            model_info = self.get_default_model(provider.id)
            if model_info is None:
                raise ValueError(f"未找到提供商 {provider.name} 的默认模型")
        
        # 如果model_info是字符串，查找对应的模型
        if isinstance(model_info, str):
            model = self.get_model_by_name(provider.id, model_info)
            if model is None:
                raise ValueError(f"未找到模型: {model_info}")
            model_info = model
        
        # 2. 准备系统提示
        system_prompt = ""
        if assistant:
            system_prompt = assistant.system_prompt or ""
        
        # 查找并添加系统消息
        has_system_message = False
        for msg in messages:
            if msg.get("role") == "system":
                has_system_message = True
                # 如果已有系统消息但assistant也有系统提示，则合并
                if system_prompt and msg.get("content") != system_prompt:
                    msg["content"] = f"{system_prompt}\n\n{msg['content']}"
                break
        
        # 如果没有系统消息但有系统提示，添加系统消息
        if not has_system_message and system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # 3. 添加上下文信息
        if context:
            context_msg = {"role": "system", "content": "以下是相关的上下文信息:\n\n"}
            for i, ctx in enumerate(context):
                content = ctx.get("content", "")
                if content:
                    context_msg["content"] += f"[文档 {i+1}]\n{content}\n\n"
            
            # 将上下文插入到系统消息之后，或者作为第一条消息
            if has_system_message or system_prompt:
                messages.insert(1, context_msg)
            else:
                messages.insert(0, context_msg)
        
        # 4. 调用相应提供商的聊天API
        start_time = time.time()
        
        try:
            if provider.provider_type.lower() == "openai":
                return await self._openai_chat_completion(
                    provider, model_info.model_id, messages, temperature, max_tokens, stream
                )
            elif provider.provider_type.lower() == "zhipu":
                return await self._zhipu_chat_completion(
                    provider, model_info.model_id, messages, temperature, max_tokens, stream
                )
            elif provider.provider_type.lower() == "ollama":
                return await self._ollama_chat_completion(
                    provider, model_info.model_id, messages, temperature, max_tokens, stream
                )
            elif provider.provider_type.lower() == "vllm":
                return await self._vllm_chat_completion(
                    provider, model_info.model_id, messages, temperature, max_tokens, stream
                )
            else:
                # 其他提供商可根据需要添加
                return await self._generic_chat_completion(
                    provider, model_info.model_id, messages, temperature, max_tokens, stream
                )
        
        except Exception as e:
            logger.error(f"聊天生成失败: {str(e)}")
            raise
        
        finally:
            logger.info(f"聊天生成耗时: {time.time() - start_time:.2f}秒")
    
    async def _openai_chat_completion(
        self,
        provider: ModelProvider,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Union[str, Any]:
        """OpenAI聊天生成"""
        from openai import AsyncOpenAI
        
        # 配置客户端
        client_args = {"api_key": provider.api_key}
        
        if provider.api_base:
            client_args["base_url"] = provider.api_base
        
        config = provider.config or {}
        timeout = config.get("timeout", 30)
        client_args["timeout"] = timeout
        
        # 代理设置
        if config.get("proxy"):
            client_args["http_client"] = httpx.AsyncClient(
                proxies=config["proxy"],
                timeout=timeout
            )
        
        client = AsyncOpenAI(**client_args)
        
        response = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        
        if stream:
            return response
        
        return response.choices[0].message.content
    
    async def _zhipu_chat_completion(
        self,
        provider: ModelProvider,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Union[str, Any]:
        """智谱AI聊天生成"""
        try:
            from zhipuai import ZhipuAI
            
            client = ZhipuAI(api_key=provider.api_key)
            
            response = await client.chat.completions.acreate(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            if stream:
                return response
            
            return response.choices[0].message.content
        
        except ImportError:
            # 如果没有智谱AI SDK，使用HTTP请求
            api_base = provider.api_base or "https://open.bigmodel.cn/api/paas/v3/model-api"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider.api_key}"
            }
            
            data = {
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            async with httpx.AsyncClient(timeout=provider.config.get("timeout", 30)) as client:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code != 200:
                    raise ValueError(f"智谱API错误: {response.text}")
                
                if stream:
                    return response
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
    
    async def _ollama_chat_completion(
        self,
        provider: ModelProvider,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Union[str, Any]:
        """Ollama聊天生成"""
        try:
            import ollama
            
            ollama.set_host(provider.api_base or "http://localhost:11434")
            
            # 检查是否存在系统消息
            system_prompt = None
            filtered_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    filtered_messages.append(msg)
            
            # 如果没有非系统消息，添加一个虚拟的用户消息
            if not filtered_messages:
                filtered_messages.append({"role": "user", "content": "Hello"})
            
            response = await ollama.chat(
                model=model_id,
                messages=filtered_messages,
                stream=stream,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "system": system_prompt
                }
            )
            
            if stream:
                return response
            
            return response["message"]["content"]
        
        except ImportError:
            # 如果没有Ollama SDK，使用HTTP请求
            api_base = provider.api_base or "http://localhost:11434"
            
            # 检查是否存在系统消息
            system_prompt = None
            filtered_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    filtered_messages.append(msg)
            
            # 如果没有非系统消息，添加一个虚拟的用户消息
            if not filtered_messages:
                filtered_messages.append({"role": "user", "content": "Hello"})
            
            data = {
                "model": model_id,
                "messages": filtered_messages,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            if system_prompt:
                data["options"]["system"] = system_prompt
            
            async with httpx.AsyncClient(timeout=provider.config.get("timeout", 60)) as client:
                response = await client.post(
                    f"{api_base}/api/chat",
                    json=data
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Ollama API错误: {response.text}")
                
                if stream:
                    return response
                
                result = response.json()
                return result["message"]["content"]
    
    async def _vllm_chat_completion(
        self,
        provider: ModelProvider,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Union[str, Any]:
        """vLLM聊天生成"""
        api_base = provider.api_base or "http://localhost:8000"
        config = provider.config or {}
        
        # 将消息转换为提示格式
        prompt = self._convert_messages_to_prompt(messages, config.get("chat_template"))
        
        data = {
            "model": model_id,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        # 添加其他vLLM特定参数
        if config.get("stop"):
            data["stop"] = config["stop"]
        if config.get("top_p") is not None:
            data["top_p"] = config["top_p"]
        if config.get("presence_penalty") is not None:
            data["presence_penalty"] = config["presence_penalty"]
        if config.get("frequency_penalty") is not None:
            data["frequency_penalty"] = config["frequency_penalty"]
        
        async with httpx.AsyncClient(timeout=config.get("timeout", 60)) as client:
            if stream:
                response = await client.post(
                    f"{api_base}/v1/completions",
                    json=data,
                    headers={"Accept": "text/event-stream"}
                )
                return response
            
            response = await client.post(
                f"{api_base}/v1/completions",
                json=data
            )
            
            if response.status_code != 200:
                raise ValueError(f"vLLM API错误: {response.text}")
            
            result = response.json()
            return result["choices"][0]["text"]
    
    async def _generic_chat_completion(
        self,
        provider: ModelProvider,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> str:
        """通用聊天生成"""
        # 获取模型客户端
        client = get_model_client(
            provider_type=provider.provider_type,
            model_id=model_id,
            api_key=provider.api_key,
            api_base=provider.api_base,
            api_version=provider.api_version,
            config=provider.config
        )
        
        try:
            # 根据不同提供商调用相应的接口
            if provider.provider_type.lower() == "deepseek":
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                )
            elif provider.provider_type.lower() == "dashscope":
                response = client.Generation.call(
                    model=model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    result_format='message' if not stream else 'stream'
                )
            elif provider.provider_type.lower() == "anthropic":
                response = client.messages.create(
                    model=model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                )
            else:
                # 默认情况，尝试通用的调用方式
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                )
            
            if stream:
                return response
            
            # 根据不同提供商解析响应
            if provider.provider_type.lower() == "deepseek":
                return response.choices[0].message.content
            elif provider.provider_type.lower() == "dashscope":
                return response['output']['choices'][0]['message']['content']
            elif provider.provider_type.lower() == "anthropic":
                return response.content[0].text
            else:
                return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"{provider.provider_type}聊天生成失败: {str(e)}")
            raise
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]], template: Optional[str] = None) -> str:
        """
        将消息列表转换为提示字符串
        支持不同的模板格式
        """
        if not template or template.lower() == "chatml":
            # ChatML格式 (role\ncontent\n)
            prompt = ""
            for message in messages:
                role = message["role"]
                content = message["content"]
                prompt += f"{role}\n{content}\n"
            
            # 添加助手角色开始标记
            prompt += "assistant\n"
            return prompt
        
        elif template.lower() == "llama":
            # Llama 2格式
            system_prompt = ""
            prompt = ""
            
            for message in messages:
                role = message["role"]
                content = message["content"]
                
                if role == "system":
                    system_prompt = content
                elif role == "user":
                    prompt += f"[INST] {content} [/INST]"
                elif role == "assistant":
                    prompt += f"{content}"
            
            if system_prompt:
                # 将系统提示放在第一个用户消息之前
                if prompt.startswith("[INST]"):
                    prompt = f"[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{prompt[6:]}"
                else:
                    prompt = f"[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n [/INST]"
            
            return prompt
        
        elif template.lower() == "zephyr":
            # Zephyr格式
            system_prompt = "You are a helpful assistant."
            prompt = ""
            
            for message in messages:
                role = message["role"]
                content = message["content"]
                
                if role == "system":
                    system_prompt = content
                elif role == "user":
                    prompt += f"{content}\n"
                elif role == "assistant":
                    prompt += f"{content}\n"
            
            if system_prompt:
                prompt = f"{system_prompt}\n\n{prompt}"
            
            return prompt
        
        else:
            raise ValueError(f"不支持的模板格式: {template}")
