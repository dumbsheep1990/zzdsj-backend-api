"""
上下文压缩中间件
提供在请求处理过程中应用上下文压缩的中间件
"""

from typing import Dict, Any, Optional, List, Callable, Awaitable
from fastapi import Request, Response
import json
import time
from datetime import datetime

from app.messaging.core.models import Message, MessageType
from app.messaging.core.compressed_context import convert_compressed_context_to_internal
from app.schemas.context_compression import CompressionConfig, CompressedContextResult
from app.services.context_compression_service import ContextCompressionService


class ContextCompressionMiddleware:
    """上下文压缩中间件，用于在请求过程中自动应用上下文压缩"""
    
    def __init__(
        self,
        app,
        db_session_getter: Callable,
        enabled: bool = True,
        paths_to_compress: List[str] = None,
        compression_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化上下文压缩中间件
        
        参数:
            app: FastAPI应用实例
            db_session_getter: 获取数据库会话的函数
            enabled: 是否启用压缩
            paths_to_compress: 需要压缩的路径列表
            compression_config: 压缩配置
        """
        self.app = app
        self.get_db_session = db_session_getter
        self.enabled = enabled
        self.paths_to_compress = paths_to_compress or [
            "/api/v1/owl/agents/{agent_id}/completions",
            "/api/v1/owl/agents/{agent_id}/chat",
            "/api/v1/chat/completions"
        ]
        self.compression_config = compression_config or {}
        
    async def __call__(self, request: Request, call_next):
        """
        中间件主函数
        
        参数:
            request: HTTP请求对象
            call_next: 下一个中间件函数
            
        返回:
            HTTP响应对象
        """
        # 如果未启用或路径不匹配，则直接传递给下一个中间件
        if not self.enabled or not self._should_compress_path(request.url.path):
            return await call_next(request)
        
        # 创建响应拦截器
        response_interceptor = ResponseInterceptor()
        
        # 传递给下一个中间件，获取响应
        response = await call_next(request)
        
        # 如果响应类型不是JSON，则直接返回
        if not response.headers.get("content-type", "").startswith("application/json"):
            return response
        
        # 读取响应内容
        body = await response.body()
        if not body:
            return response
        
        try:
            # 解析响应内容
            response_data = json.loads(body)
            
            # 检查是否需要压缩上下文
            if self._should_compress_content(response_data):
                # 执行上下文压缩
                compressed_data = await self._compress_context(request, response_data)
                
                # 创建新的响应
                new_response = Response(
                    content=json.dumps(compressed_data),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                return new_response
        except Exception as e:
            # 发生错误时记录并返回原始响应
            print(f"上下文压缩中间件错误: {str(e)}")
        
        # 如果没有需要压缩的内容或发生错误，返回原始响应
        return response
    
    def _should_compress_path(self, path: str) -> bool:
        """
        检查路径是否需要压缩
        
        参数:
            path: 请求路径
            
        返回:
            是否需要压缩
        """
        for pattern in self.paths_to_compress:
            # 替换路径参数为通配符
            simplified_pattern = pattern.replace("{agent_id}", "[^/]+")
            if path.endswith(simplified_pattern) or path == simplified_pattern:
                return True
        return False
    
    def _should_compress_content(self, response_data: Dict[str, Any]) -> bool:
        """
        检查响应内容是否需要压缩
        
        参数:
            response_data: 响应数据
            
        返回:
            是否需要压缩
        """
        # 检查是否包含消息列表
        if "messages" in response_data and isinstance(response_data["messages"], list):
            return True
        
        # 检查是否为OpenAI格式的响应
        if "choices" in response_data and isinstance(response_data["choices"], list):
            return True
        
        return False
    
    async def _compress_context(self, request: Request, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        压缩响应中的上下文
        
        参数:
            request: HTTP请求对象
            response_data: 响应数据
            
        返回:
            压缩后的响应数据
        """
        # 提取请求中的查询和智能体ID
        query = ""
        agent_id = None
        
        try:
            # 尝试从路径中提取智能体ID
            path_parts = request.url.path.split("/")
            for i, part in enumerate(path_parts):
                if part == "agents" and i + 1 < len(path_parts):
                    try:
                        agent_id = int(path_parts[i + 1])
                    except ValueError:
                        pass
            
            # 尝试从请求体中提取查询
            body = await request.json()
            query = body.get("query", "") or body.get("messages", [{}])[-1].get("content", "")
        except Exception:
            pass
        
        # 创建压缩配置
        config = CompressionConfig(**self.compression_config)
        
        # 获取数据库会话
        db = self.get_db_session()
        
        # 创建压缩服务
        compression_service = ContextCompressionService(db)
        
        # 如果响应包含消息列表，则压缩每条消息
        if "messages" in response_data and isinstance(response_data["messages"], list):
            # 获取所有系统消息和助手消息的内容
            all_content = ""
            for msg in response_data["messages"]:
                if msg.get("role") == "system" or msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if content:
                        all_content += content + "\n\n"
            
            # 如果有内容需要压缩
            if all_content:
                # 执行压缩
                result = await compression_service.compress_context(
                    content=all_content,
                    query=query,
                    agent_id=agent_id,
                    config=config
                )
                
                # 如果压缩成功，替换原始消息
                if result.status == "success" and result.compression_ratio < 0.95:
                    # 添加压缩上下文消息
                    compressed_msg = convert_compressed_context_to_internal(
                        compressed_text=result.compressed_context,
                        original_text=result.original_context,
                        method=result.method,
                        compression_ratio=result.compression_ratio
                    )
                    
                    # 将压缩消息添加到响应中
                    response_data["compressed_context"] = {
                        "original_length": len(all_content),
                        "compressed_length": len(result.compressed_context),
                        "compression_ratio": result.compression_ratio,
                        "method": result.method
                    }
                    
                    # 添加压缩消息到消息列表中
                    response_data["messages"].append(compressed_msg.dict())
        
        # 如果是OpenAI格式的响应，处理choices中的消息
        elif "choices" in response_data and isinstance(response_data["choices"], list):
            for choice in response_data["choices"]:
                if "message" in choice and isinstance(choice["message"], dict):
                    content = choice["message"].get("content", "")
                    if content and len(content) > 1000:  # 只压缩较长的内容
                        # 执行压缩
                        result = await compression_service.compress_context(
                            content=content,
                            query=query,
                            agent_id=agent_id,
                            config=config
                        )
                        
                        # 如果压缩成功且压缩比小于95%，则替换内容
                        if result.status == "success" and result.compression_ratio < 0.95:
                            choice["message"]["original_content"] = content
                            choice["message"]["content"] = result.compressed_context
                            choice["message"]["compression_info"] = {
                                "ratio": result.compression_ratio,
                                "method": result.method
                            }
        
        return response_data


class ResponseInterceptor:
    """响应拦截器，用于在响应发送前修改响应内容"""
    
    async def __call__(self, response: Response):
        """处理响应"""
        return response
