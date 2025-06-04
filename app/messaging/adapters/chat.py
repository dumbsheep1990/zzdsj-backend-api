"""
聊天适配器
提供与聊天系统的集成接口
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from datetime import datetime, timedelta

from fastapi.responses import StreamingResponse

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    FunctionCallMessage, FunctionReturnMessage, ThinkingMessage, 
    ImageMessage, HybridMessage, StatusMessage, ErrorMessage, DoneMessage
)
from app.messaging.services.message_service import MessageService, get_message_service
from app.messaging.services.stream_service import StreamService, get_stream_service
from app.messaging.adapters.base import BaseAdapter
from app.messaging.adapters.llama_index import LlamaIndexAdapter
from app.frameworks.llamaindex.chat import create_chat_engine

# 导入缓存管理器
from app.utils.core.cache import get_cache_manager

logger = logging.getLogger(__name__)


class ChatAdapter(BaseAdapter):
    """
    聊天适配器
    为聊天模块提供统一的消息处理接口
    支持完整的聊天记忆管理功能
    """
    
    def __init__(
        self,
        message_service: Optional[MessageService] = None,
        stream_service: Optional[StreamService] = None,
        llama_index_adapter: Optional[LlamaIndexAdapter] = None,
        adapter_name: str = "ChatAdapter"
    ):
        """
        初始化聊天适配器
        
        参数:
            message_service: 消息服务实例，如不提供则获取全局实例
            stream_service: 流服务实例，如不提供则获取全局实例
            llama_index_adapter: LlamaIndex适配器实例，如不提供则创建新实例
            adapter_name: 适配器名称
        """
        super().__init__(message_service, stream_service, adapter_name)
        self.llama_index_adapter = llama_index_adapter or LlamaIndexAdapter(
            message_service, stream_service
        )
        
        # 获取缓存管理器用于记忆存储
        self.cache_manager = get_cache_manager()
        
        # 记忆配置
        self.memory_config = {
            "max_history_messages": 50,  # 最大历史消息数量
            "memory_ttl": 24 * 3600,     # 记忆过期时间(24小时)
            "context_window": 20,        # 上下文窗口大小
            "compression_threshold": 30  # 超过此数量时压缩记忆
        }
        
        logger.info(f"聊天适配器初始化完成，支持记忆管理功能")
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """验证输入数据"""
        if not isinstance(input_data, dict):
            self.logger.error("输入数据必须是字典类型")
            return None
        
        # 检查消息列表
        if "messages" not in input_data:
            self.logger.error("输入数据缺少'messages'字段")
            return None
            
        messages = input_data["messages"]
        if not isinstance(messages, list):
            self.logger.error("'messages'字段必须是列表类型")
            return None
        
        return input_data
    
    async def _do_process_messages(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """执行具体的消息处理逻辑"""
        messages = input_data["messages"]
        model_name = input_data.get("model_name")
        temperature = input_data.get("temperature")
        system_prompt = input_data.get("system_prompt")
        memory_key = input_data.get("memory_key")
        
        # 处理历史记忆逻辑
        memory_messages = []
        if memory_key:
            memory_messages = await self._get_chat_memory(memory_key)
            self.logger.info(f"从记忆中获取 {len(memory_messages)} 条历史消息")
        
        # 合并历史记忆和当前消息
        all_messages = memory_messages + messages
        
        # 使用LlamaIndex适配器处理消息
        response_messages = await self.llama_index_adapter.process_messages(
            messages=all_messages,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt
        )
        
        # 处理保存记忆逻辑
        if memory_key and response_messages:
            conversation_messages = messages + response_messages
            await self._save_chat_memory(memory_key, conversation_messages)
            self.logger.info(f"保存 {len(conversation_messages)} 条消息到记忆")
        
        return response_messages
    
    async def _do_stream_messages(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """执行具体的流式消息处理逻辑"""
        messages = input_data["messages"]
        model_name = input_data.get("model_name")
        temperature = input_data.get("temperature")
        system_prompt = input_data.get("system_prompt")
        memory_key = input_data.get("memory_key")
        
        # 处理历史记忆逻辑
        memory_messages = []
        if memory_key:
            memory_messages = await self._get_chat_memory(memory_key)
            self.logger.info(f"流式处理：从记忆中获取 {len(memory_messages)} 条历史消息")
        
        # 合并历史记忆和当前消息
        all_messages = memory_messages + messages
        
        # 使用LlamaIndex适配器流式处理消息
        stream_generator = self.llama_index_adapter.stream_messages(
            messages=all_messages,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt,
            stream_id=stream_id
        )
        
        # 收集所有消息用于保存记忆
        if memory_key:
            collected_messages = []
            async for message in stream_generator:
                collected_messages.append(message)
                yield message
                
            # 在流结束后保存记忆
            conversation_messages = messages + collected_messages
            await self._save_chat_memory(memory_key, conversation_messages)
            self.logger.info(f"流式处理：保存 {len(conversation_messages)} 条消息到记忆")
        else:
            # 直接传递消息流
            async for message in stream_generator:
                yield message
    
    async def process_messages(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        memory_key: Optional[str] = None
    ) -> List[Message]:
        """
        处理聊天消息
        
        参数:
            messages: 聊天消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            memory_key: 记忆键，用于管理聊天历史
            
        返回:
            处理后的消息列表
        """
        input_data = {
            "messages": messages,
            "model_name": model_name,
            "temperature": temperature,
            "system_prompt": system_prompt,
            "memory_key": memory_key
        }
        
        return await super().process_messages(input_data)
    
    async def stream_messages(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None,
        memory_key: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        流式处理聊天消息
        
        参数:
            messages: 聊天消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            memory_key: 记忆键，用于管理聊天历史
            
        返回:
            消息流生成器
        """
        input_data = {
            "messages": messages,
            "model_name": model_name,
            "temperature": temperature,
            "system_prompt": system_prompt,
            "memory_key": memory_key
        }
        
        async for message in super().stream_messages(input_data, stream_id=stream_id):
            yield message
    
    async def to_sse_response(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None,
        memory_key: Optional[str] = None
    ) -> StreamingResponse:
        """
        转换为SSE响应
        
        参数:
            messages: 聊天消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            memory_key: 记忆键，用于管理聊天历史
            
        返回:
            SSE响应对象
        """
        input_data = {
            "messages": messages,
            "model_name": model_name,
            "temperature": temperature,
            "system_prompt": system_prompt,
            "memory_key": memory_key
        }
        
        return await super().to_sse_response(input_data, stream_id=stream_id)
    
    def to_json_response(
        self,
        messages: List[Message],
        include_metadata: bool = False,
        include_history: bool = False,
        memory_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        转换为JSON响应
        
        参数:
            messages: 聊天消息列表
            include_metadata: 是否包含元数据
            include_history: 是否包含历史记录
            memory_key: 记忆键，用于获取历史记录
            context: 上下文信息
            
        返回:
            JSON响应字典
        """
        # 获取基础响应
        response = super().to_json_response(messages, context, include_metadata)
        
        # 添加聊天特定信息
        response["chat_info"] = {
            "memory_key": memory_key,
            "has_memory": memory_key is not None,
            "include_history": include_history
        }
        
        # 添加历史记录
        if include_history and memory_key:
            try:
                history = self._get_chat_history(memory_key)
                response["history"] = history
                response["chat_info"]["history_count"] = len(history)
            except Exception as e:
                self.logger.error(f"获取历史记录失败: {str(e)}")
                response["chat_info"]["history_error"] = str(e)
        
        return response
    
    async def process_conversation(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_id: Optional[str] = None
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        处理完整的对话
        
        参数:
            user_message: 用户消息内容
            conversation_id: 对话ID，用于关联历史记录
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream: 是否流式处理
            stream_id: 流ID
            
        返回:
            处理后的响应对象
        """
        # 创建用户消息
        message = TextMessage(
            content=user_message,
            role=MessageRole.USER
        )
        
        # 处理消息
        if stream:
            return await self.to_sse_response(
                messages=[message],
                model_name=model_name,
                temperature=temperature,
                system_prompt=system_prompt,
                stream_id=stream_id,
                memory_key=conversation_id
            )
        else:
            response_messages = await self.process_messages(
                messages=[message],
                model_name=model_name,
                temperature=temperature,
                system_prompt=system_prompt,
                memory_key=conversation_id
            )
            
            return self.to_json_response(
                messages=response_messages,
                include_metadata=False,
                include_history=True,
                memory_key=conversation_id
            )
    
    # ========== 记忆管理核心方法 ==========
    
    async def _get_chat_memory(self, memory_key: str) -> List[Message]:
        """
        从缓存中获取聊天历史记忆
        
        参数:
            memory_key: 记忆键
            
        返回:
            历史消息列表
        """
        try:
            # 构建缓存键
            cache_key = f"chat_memory:{memory_key}"
            
            # 从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            
            if cached_data is None:
                self.logger.debug(f"未找到记忆缓存: {memory_key}")
                return []
            
            # 解析缓存的消息数据
            if isinstance(cached_data, str):
                messages_data = json.loads(cached_data)
            elif isinstance(cached_data, dict):
                messages_data = cached_data.get("messages", [])
            else:
                messages_data = cached_data
            
            # 转换为Message对象
            messages = []
            for msg_data in messages_data:
                try:
                    # 根据消息类型创建不同的Message对象
                    msg_type = msg_data.get("type", MessageType.TEXT.value)
                    
                    if msg_type == MessageType.TEXT.value:
                        message = TextMessage(
                            content=msg_data["content"],
                            role=MessageRole(msg_data["role"]),
                            metadata=msg_data.get("metadata", {})
                        )
                    else:
                        # 对于其他类型，创建基础Message对象
                        message = Message(
                            type=MessageType(msg_type),
                            role=MessageRole(msg_data["role"]),
                            content=msg_data["content"],
                            metadata=msg_data.get("metadata", {})
                        )
                    
                    messages.append(message)
                    
                except Exception as e:
                    self.logger.warning(f"跳过无效的消息数据: {str(e)}")
                    continue
            
            # 应用上下文窗口限制
            context_window = self.memory_config["context_window"]
            if len(messages) > context_window:
                messages = messages[-context_window:]
                self.logger.debug(f"应用上下文窗口限制，保留最近 {context_window} 条消息")
            
            self.logger.info(f"成功从缓存获取 {len(messages)} 条历史消息")
            return messages
            
        except Exception as e:
            self.logger.error(f"获取聊天记忆失败: {str(e)}")
            return []
    
    async def _save_chat_memory(self, memory_key: str, messages: List[Message]) -> None:
        """
        保存聊天历史记忆到缓存
        
        参数:
            memory_key: 记忆键
            messages: 要保存的消息列表
        """
        try:
            # 构建缓存键
            cache_key = f"chat_memory:{memory_key}"
            
            # 获取现有记忆
            existing_messages = await self._get_chat_memory(memory_key)
            
            # 合并新旧消息，避免重复
            all_messages = existing_messages + messages
            
            # 去重逻辑（基于消息内容和时间戳）
            unique_messages = []
            seen_signatures = set()
            
            for msg in all_messages:
                # 创建消息签名用于去重
                signature = self._create_message_signature(msg)
                if signature not in seen_signatures:
                    unique_messages.append(msg)
                    seen_signatures.add(signature)
            
            # 应用最大历史消息限制
            max_messages = self.memory_config["max_history_messages"]
            if len(unique_messages) > max_messages:
                unique_messages = unique_messages[-max_messages:]
                self.logger.debug(f"应用最大历史限制，保留最近 {max_messages} 条消息")
            
            # 检查是否需要压缩记忆
            compression_threshold = self.memory_config["compression_threshold"]
            if len(unique_messages) > compression_threshold:
                unique_messages = await self._compress_memory(unique_messages)
            
            # 转换为可序列化的格式
            messages_data = []
            for msg in unique_messages:
                msg_dict = {
                    "type": msg.type.value,
                    "role": msg.role.value,
                    "content": msg.content,
                    "metadata": msg.metadata or {},
                    "timestamp": getattr(msg, "timestamp", datetime.now().isoformat())
                }
                messages_data.append(msg_dict)
            
            # 构建缓存数据
            cache_data = {
                "messages": messages_data,
                "updated_at": datetime.now().isoformat(),
                "message_count": len(messages_data),
                "memory_key": memory_key
            }
            
            # 保存到缓存，设置TTL
            ttl = self.memory_config["memory_ttl"]
            success = self.cache_manager.set(cache_key, cache_data, ttl)
            
            if success:
                self.logger.info(f"成功保存 {len(messages_data)} 条消息到记忆缓存")
            else:
                self.logger.error(f"保存消息到记忆缓存失败")
                
        except Exception as e:
            self.logger.error(f"保存聊天记忆失败: {str(e)}")
    
    def _get_chat_history(self, memory_key: str) -> List[Dict[str, Any]]:
        """
        获取格式化的聊天历史记录
        
        参数:
            memory_key: 记忆键
            
        返回:
            格式化的历史记录列表
        """
        try:
            # 构建缓存键
            cache_key = f"chat_memory:{memory_key}"
            
            # 从缓存获取数据
            cached_data = self.cache_manager.get(cache_key)
            
            if cached_data is None:
                return []
            
            # 解析缓存的消息数据
            if isinstance(cached_data, str):
                cache_data = json.loads(cached_data)
            else:
                cache_data = cached_data
            
            messages_data = cache_data.get("messages", [])
            
            # 格式化历史记录
            history = []
            for msg_data in messages_data:
                history_item = {
                    "role": msg_data["role"],
                    "content": msg_data["content"],
                    "timestamp": msg_data.get("timestamp"),
                    "type": msg_data.get("type", "text")
                }
                history.append(history_item)
            
            return history
            
        except Exception as e:
            self.logger.error(f"获取聊天历史记录失败: {str(e)}")
            return []
    
    def _create_message_signature(self, message: Message) -> str:
        """
        创建消息签名用于去重
        
        参数:
            message: 消息对象
            
        返回:
            消息签名字符串
        """
        import hashlib
        
        # 构建签名内容
        signature_content = f"{message.role.value}:{message.type.value}:{str(message.content)}"
        
        # 如果有时间戳，也加入签名
        if hasattr(message, "timestamp") and message.timestamp:
            signature_content += f":{message.timestamp}"
        
        # 生成MD5哈希
        return hashlib.md5(signature_content.encode("utf-8")).hexdigest()
    
    async def _compress_memory(self, messages: List[Message]) -> List[Message]:
        """
        压缩记忆，保留重要消息
        
        参数:
            messages: 原始消息列表
            
        返回:
            压缩后的消息列表
        """
        try:
            # 简单的压缩策略：保留最近的消息和重要的系统消息
            important_messages = []
            recent_messages = []
            
            for msg in messages:
                # 保留系统消息和错误消息
                if msg.role == MessageRole.SYSTEM or msg.type == MessageType.ERROR:
                    important_messages.append(msg)
                else:
                    recent_messages.append(msg)
            
            # 保留最近的用户和助手消息
            max_recent = max(10, self.memory_config["context_window"] // 2)
            if len(recent_messages) > max_recent:
                recent_messages = recent_messages[-max_recent:]
            
            # 合并重要消息和最近消息
            compressed_messages = important_messages + recent_messages
            
            self.logger.info(f"记忆压缩：{len(messages)} -> {len(compressed_messages)} 条消息")
            return compressed_messages
            
        except Exception as e:
            self.logger.error(f"记忆压缩失败: {str(e)}")
            # 如果压缩失败，返回最近的消息
            return messages[-self.memory_config["context_window"]:]
    
    # ========== 记忆管理工具方法 ==========
    
    async def clear_memory(self, memory_key: str) -> bool:
        """
        清除指定的聊天记忆
        
        参数:
            memory_key: 记忆键
            
        返回:
            操作是否成功
        """
        try:
            cache_key = f"chat_memory:{memory_key}"
            success = self.cache_manager.delete(cache_key)
            
            if success:
                self.logger.info(f"成功清除聊天记忆: {memory_key}")
            else:
                self.logger.warning(f"清除聊天记忆失败: {memory_key}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"清除聊天记忆时发生错误: {str(e)}")
            return False
    
    async def get_memory_stats(self, memory_key: str) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        参数:
            memory_key: 记忆键
            
        返回:
            记忆统计信息
        """
        try:
            cache_key = f"chat_memory:{memory_key}"
            cached_data = self.cache_manager.get(cache_key)
            
            if cached_data is None:
                return {
                    "exists": False,
                    "message_count": 0,
                    "last_updated": None
                }
            
            if isinstance(cached_data, str):
                cache_data = json.loads(cached_data)
            else:
                cache_data = cached_data
            
            return {
                "exists": True,
                "message_count": cache_data.get("message_count", 0),
                "last_updated": cache_data.get("updated_at"),
                "memory_key": cache_data.get("memory_key"),
                "ttl_remaining": self.cache_manager.get_ttl(cache_key)
            }
            
        except Exception as e:
            self.logger.error(f"获取记忆统计信息失败: {str(e)}")
            return {
                "exists": False,
                "error": str(e)
            }
    
    def get_memory_config(self) -> Dict[str, Any]:
        """获取记忆配置"""
        return self.memory_config.copy()
    
    def update_memory_config(self, config: Dict[str, Any]) -> None:
        """
        更新记忆配置
        
        参数:
            config: 新的配置参数
        """
        self.memory_config.update(config)
        self.logger.info(f"记忆配置已更新: {config}")
