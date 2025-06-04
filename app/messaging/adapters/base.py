"""
基础适配器
定义适配器的基本接口和共享功能
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from abc import ABC, abstractmethod
from datetime import datetime

from fastapi.responses import StreamingResponse

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, StatusMessage, 
    ErrorMessage, DoneMessage
)
from app.messaging.services.message_service import MessageService, get_message_service
from app.messaging.services.stream_service import StreamService, get_stream_service

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """基础适配器抽象类，定义所有适配器的共同接口"""
    
    def __init__(
        self,
        message_service: Optional[MessageService] = None,
        stream_service: Optional[StreamService] = None,
        adapter_name: str = "BaseAdapter"
    ):
        """
        初始化基础适配器
        
        参数:
            message_service: 消息服务实例，如不提供则获取全局实例
            stream_service: 流服务实例，如不提供则获取全局实例
            adapter_name: 适配器名称，用于日志记录
        """
        self.message_service = message_service or get_message_service()
        self.stream_service = stream_service or get_stream_service()
        self.adapter_name = adapter_name
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # 性能统计
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_messages_processed": 0,
            "average_response_time": 0.0
        }
        
        self.logger.info(f"适配器初始化完成: {self.adapter_name}")
    
    async def process_messages(
        self, 
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """
        处理消息的通用实现
        
        参数:
            input_data: 输入数据字典
            context: 可选的上下文信息
            
        返回:
            消息列表
        """
        start_time = datetime.now()
        self._stats["total_requests"] += 1
        
        try:
            self.logger.info(f"开始处理消息: {self.adapter_name}")
            
            # 验证输入数据
            validated_data = await self._validate_input(input_data)
            if not validated_data:
                raise ValueError("输入数据验证失败")
            
            # 预处理
            processed_data = await self._preprocess_data(validated_data, context)
            
            # 具体的消息处理逻辑（由子类实现）
            messages = await self._do_process_messages(processed_data, context)
            
            # 后处理
            final_messages = await self._postprocess_messages(messages, context)
            
            # 更新统计信息
            self._stats["successful_requests"] += 1
            self._stats["total_messages_processed"] += len(final_messages)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_average_response_time(processing_time)
            
            self.logger.info(f"消息处理完成: {self.adapter_name}, 处理了 {len(final_messages)} 条消息")
            
            return final_messages
            
        except Exception as e:
            self._stats["failed_requests"] += 1
            self.logger.error(f"消息处理失败: {self.adapter_name}, 错误: {str(e)}")
            
            # 返回错误消息
            error_message = ErrorMessage(
                content={"error_message": str(e), "error_code": "PROCESSING_ERROR"},
                metadata={"adapter": self.adapter_name, "timestamp": datetime.now().isoformat()}
            )
            return [error_message]
    
    async def stream_messages(
        self, 
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        流式处理消息的通用实现
        
        参数:
            input_data: 输入数据字典
            context: 可选的上下文信息
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        start_time = datetime.now()
        self._stats["total_requests"] += 1
        
        try:
            self.logger.info(f"开始流式处理消息: {self.adapter_name}")
            
            # 发送开始状态消息
            start_message = StatusMessage(
                content={
                    "status": "processing_started",
                    "adapter": self.adapter_name,
                    "stream_id": stream_id
                }
            )
            yield start_message
            
            # 验证输入数据
            validated_data = await self._validate_input(input_data)
            if not validated_data:
                raise ValueError("输入数据验证失败")
            
            # 预处理
            processed_data = await self._preprocess_data(validated_data, context)
            
            # 具体的流式消息处理逻辑（由子类实现）
            message_count = 0
            async for message in self._do_stream_messages(processed_data, context, stream_id):
                # 后处理单个消息
                processed_message = await self._postprocess_single_message(message, context)
                message_count += 1
                yield processed_message
            
            # 发送完成消息
            done_message = DoneMessage(
                metadata={
                    "adapter": self.adapter_name,
                    "stream_id": stream_id,
                    "messages_processed": message_count,
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            )
            yield done_message
            
            # 更新统计信息
            self._stats["successful_requests"] += 1
            self._stats["total_messages_processed"] += message_count
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_average_response_time(processing_time)
            
            self.logger.info(f"流式消息处理完成: {self.adapter_name}, 处理了 {message_count} 条消息")
            
        except Exception as e:
            self._stats["failed_requests"] += 1
            self.logger.error(f"流式消息处理失败: {self.adapter_name}, 错误: {str(e)}")
            
            # 发送错误消息
            error_message = ErrorMessage(
                content={"error_message": str(e), "error_code": "STREAMING_ERROR"},
                metadata={"adapter": self.adapter_name, "stream_id": stream_id, "timestamp": datetime.now().isoformat()}
            )
            yield error_message
    
    async def to_sse_response(
        self, 
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        转换为SSE响应的通用实现
        
        参数:
            input_data: 输入数据字典
            context: 可选的上下文信息
            stream_id: 流ID
            
        返回:
            SSE响应对象
        """
        self.logger.info(f"创建SSE响应: {self.adapter_name}")
        
        async def sse_generator():
            """SSE事件生成器"""
            try:
                # 发送连接确认
                connection_event = {
                    "event": "connection",
                    "data": {
                        "status": "connected",
                        "adapter": self.adapter_name,
                        "stream_id": stream_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                yield f"event: connection\ndata: {self._to_json_string(connection_event['data'])}\n\n"
                
                # 流式处理消息并转换为SSE格式
                async for message in self.stream_messages(input_data, context, stream_id):
                    event_name = message.type.value
                    event_data = message.to_dict()
                    
                    # 格式化SSE事件
                    sse_event = f"event: {event_name}\ndata: {self._to_json_string(event_data)}\n\n"
                    yield sse_event
                
                # 发送关闭事件
                close_event = {
                    "status": "completed",
                    "adapter": self.adapter_name,
                    "stream_id": stream_id,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"event: close\ndata: {self._to_json_string(close_event)}\n\n"
                
            except Exception as e:
                self.logger.error(f"SSE流生成失败: {self.adapter_name}, 错误: {str(e)}")
                
                # 发送错误事件
                error_event = {
                    "error_message": str(e),
                    "error_code": "SSE_STREAM_ERROR",
                    "adapter": self.adapter_name,
                    "stream_id": stream_id,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"event: error\ndata: {self._to_json_string(error_event)}\n\n"
        
        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    
    def to_json_response(
        self, 
        messages: List[Message],
        context: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        转换为JSON响应的通用实现
        
        参数:
            messages: 消息列表
            context: 可选的上下文信息
            include_metadata: 是否包含元数据
            
        返回:
            JSON响应字典
        """
        self.logger.info(f"创建JSON响应: {self.adapter_name}, {len(messages)} 条消息")
        
        try:
            # 构建基础响应结构
            response = {
                "success": True,
                "adapter": self.adapter_name,
                "timestamp": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": []
            }
            
            # 处理消息列表
            for message in messages:
                message_dict = message.to_dict()
                
                # 根据配置决定是否包含详细元数据
                if not include_metadata:
                    message_dict.pop("metadata", None)
                
                response["messages"].append(message_dict)
            
            # 添加统计信息（可选）
            if include_metadata:
                response["statistics"] = self._get_current_stats()
                
                # 添加上下文信息（如果有）
                if context:
                    response["context"] = context
            
            # 分析消息类型分布
            message_types = {}
            for message in messages:
                msg_type = message.type.value
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            response["message_types"] = message_types
            
            return response
            
        except Exception as e:
            self.logger.error(f"JSON响应创建失败: {self.adapter_name}, 错误: {str(e)}")
            
            # 返回错误响应
            return {
                "success": False,
                "adapter": self.adapter_name,
                "timestamp": datetime.now().isoformat(),
                "error": {
                    "message": str(e),
                    "code": "JSON_RESPONSE_ERROR"
                },
                "messages": []
            }
    
    # ========== 抽象方法，子类必须实现 ==========
    
    @abstractmethod
    async def _validate_input(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """验证输入数据，子类实现具体的验证逻辑"""
        pass
    
    @abstractmethod
    async def _do_process_messages(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """执行具体的消息处理逻辑，子类实现"""
        pass
    
    @abstractmethod
    async def _do_stream_messages(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """执行具体的流式消息处理逻辑，子类实现"""
        pass
    
    # ========== 可重写的辅助方法 ==========
    
    async def _preprocess_data(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        预处理数据，子类可重写进行自定义预处理
        
        参数:
            input_data: 验证后的输入数据
            context: 上下文信息
            
        返回:
            预处理后的数据
        """
        # 默认实现：直接返回输入数据
        return input_data
    
    async def _postprocess_messages(
        self, 
        messages: List[Message], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """
        后处理消息列表，子类可重写进行自定义后处理
        
        参数:
            messages: 处理后的消息列表
            context: 上下文信息
            
        返回:
            后处理后的消息列表
        """
        # 默认实现：直接返回消息列表
        return messages
    
    async def _postprocess_single_message(
        self, 
        message: Message, 
        context: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        后处理单个消息，子类可重写进行自定义后处理
        
        参数:
            message: 消息对象
            context: 上下文信息
            
        返回:
            后处理后的消息
        """
        # 默认实现：直接返回消息
        return message
    
    # ========== 工具方法 ==========
    
    def _to_json_string(self, data: Any) -> str:
        """安全地将数据转换为JSON字符串"""
        try:
            import json
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"JSON序列化失败: {str(e)}")
            return f'{{"error": "JSON序列化失败: {str(e)}"}}'
    
    def _update_average_response_time(self, processing_time: float):
        """更新平均响应时间"""
        current_avg = self._stats["average_response_time"]
        total_requests = self._stats["successful_requests"]
        
        if total_requests == 1:
            self._stats["average_response_time"] = processing_time
        else:
            # 计算移动平均值
            self._stats["average_response_time"] = (
                (current_avg * (total_requests - 1) + processing_time) / total_requests
            )
    
    def _get_current_stats(self) -> Dict[str, Any]:
        """获取当前统计信息"""
        return {
            "total_requests": self._stats["total_requests"],
            "successful_requests": self._stats["successful_requests"],
            "failed_requests": self._stats["failed_requests"],
            "total_messages_processed": self._stats["total_messages_processed"],
            "average_response_time": round(self._stats["average_response_time"], 3),
            "success_rate": round(
                (self._stats["successful_requests"] / max(1, self._stats["total_requests"])) * 100, 2
            )
        }
    
    def get_adapter_info(self) -> Dict[str, Any]:
        """获取适配器信息"""
        return {
            "adapter_name": self.adapter_name,
            "adapter_type": self.__class__.__name__,
            "created_at": datetime.now().isoformat(),
            "statistics": self._get_current_stats()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_messages_processed": 0,
            "average_response_time": 0.0
        }
        self.logger.info(f"适配器统计信息已重置: {self.adapter_name}")


class DefaultAdapter(BaseAdapter):
    """默认适配器实现，提供基本的消息处理功能"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, adapter_name="DefaultAdapter", **kwargs)
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """验证输入数据"""
        if not isinstance(input_data, dict):
            self.logger.error("输入数据必须是字典类型")
            return None
        
        # 基本验证：确保有必要的字段
        if "content" not in input_data:
            self.logger.error("输入数据缺少'content'字段")
            return None
        
        return input_data
    
    async def _do_process_messages(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """执行基本的消息处理"""
        content = input_data.get("content", "")
        message_type = input_data.get("type", MessageType.TEXT.value)
        role = input_data.get("role", MessageRole.ASSISTANT.value)
        
        # 创建消息
        if message_type == MessageType.TEXT.value:
            message = TextMessage(
                content=content,
                role=MessageRole(role),
                metadata={"adapter": self.adapter_name}
            )
        else:
            # 默认处理为文本消息
            message = TextMessage(
                content=str(content),
                role=MessageRole(role),
                metadata={"adapter": self.adapter_name, "original_type": message_type}
            )
        
        return [message]
    
    async def _do_stream_messages(
        self, 
        input_data: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """执行基本的流式消息处理"""
        # 处理消息并逐个发送
        messages = await self._do_process_messages(input_data, context)
        
        for message in messages:
            # 模拟流式处理的延迟
            await asyncio.sleep(0.1)
            yield message
