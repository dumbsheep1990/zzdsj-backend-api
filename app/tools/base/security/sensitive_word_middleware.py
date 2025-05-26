"""
敏感词过滤中间件
用于拦截包含敏感词的请求，适用于FastAPI框架
"""

import logging
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
import json

from app.utils.sensitive_word_filter import get_sensitive_word_filter, SensitiveWordFilter

logger = logging.getLogger(__name__)

class SensitiveWordMiddleware:
    """敏感词过滤中间件"""
    
    def __init__(self, enable_check_paths: Optional[list] = None):
        """
        初始化敏感词过滤中间件
        
        参数:
            enable_check_paths: 需要进行敏感词检测的路径列表，如["/api/chat/"]
                               如不指定，则默认检测所有聊天相关路径
        """
        self.filter = get_sensitive_word_filter()
        self.enable_check_paths = enable_check_paths or [
            "/api/chat/",          # 聊天API
            "/api/conversations/",  # 对话API
            "/api/assistant_qa/",   # 问答助手API
        ]
    
    async def __call__(self, request: Request, call_next: Callable):
        """
        FastAPI中间件入口方法
        
        参数:
            request: FastAPI请求对象
            call_next: 下一个中间件处理函数
            
        返回:
            处理后的响应
        """
        # 检查是否需要处理该请求
        if not self._should_check_request(request):
            return await call_next(request)
        
        # 确保敏感词过滤器已初始化
        await self.filter.initialize()
        
        # 处理POST请求中的文本
        if request.method == "POST":
            try:
                # 获取请求体内容
                body = await request.body()
                if not body:
                    return await call_next(request)
                
                # 解析JSON
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    # 非JSON请求，不处理
                    return await call_next(request)
                
                # 提取需要检查的文本
                text_to_check = self._extract_text_from_request(data)
                if not text_to_check:
                    return await call_next(request)
                
                # 检查敏感词
                is_sensitive, sensitive_words, response_message = await self.filter.check_sensitive(text_to_check)
                
                if is_sensitive:
                    # 记录敏感词检测结果
                    logger.warning(f"检测到敏感词: {', '.join(sensitive_words)}, 路径: {request.url.path}")
                    
                    # 返回敏感词错误响应
                    return JSONResponse(
                        status_code=403,
                        content={
                            "status": "error",
                            "message": response_message,
                            "code": "sensitive_content_detected",
                            "details": {
                                "sensitive_words": sensitive_words
                            }
                        }
                    )
                
                # 重写请求体，以便后续中间件处理
                async def get_body_override():
                    return body
                
                request._body = body
                request.body = get_body_override
            
            except Exception as e:
                logger.error(f"敏感词检测过程中出错: {str(e)}")
                # 出错时不阻止请求继续处理
                pass
        
        # 继续处理请求
        return await call_next(request)
    
    def _should_check_request(self, request: Request) -> bool:
        """
        检查是否应该对该请求进行敏感词检测
        
        参数:
            request: FastAPI请求对象
            
        返回:
            是否需要检测
        """
        if request.method != "POST":
            return False
        
        # 检查请求路径是否在需要检测的列表中
        for path in self.enable_check_paths:
            if request.url.path.startswith(path):
                return True
        
        return False
    
    def _extract_text_from_request(self, data: Dict[str, Any]) -> str:
        """
        从请求数据中提取需要检查的文本
        
        参数:
            data: 请求数据字典
            
        返回:
            需要检查的文本
        """
        # 提取常见聊天请求中的文本字段
        message = ""
        
        # 常见聊天API请求格式
        if "message" in data:
            message = data["message"]
        elif "content" in data:
            message = data["content"]
        elif "text" in data:
            message = data["text"]
        elif "question" in data:
            message = data["question"]
        elif "query" in data:
            message = data["query"]
        
        # 处理嵌套结构
        if not message and isinstance(data.get("messages"), list):
            for msg in data["messages"]:
                if isinstance(msg, dict) and msg.get("role") == "user":
                    message = msg.get("content", "")
                    break
        
        return message
