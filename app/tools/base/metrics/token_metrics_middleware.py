"""
Token计算与统计中间件

提供对话后置处理功能，计算并记录Token使用情况。
此中间件不影响主要流程，即使出现异常也不会阻断对话流程。
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from functools import wraps

from app.config import settings
from app.utils.token_metrics import record_llm_usage

logger = logging.getLogger(__name__)


def async_token_metrics(user_id_key: str = "user_id", 
                      model_name_key: str = "model_name",
                      conversation_id_key: str = "conversation_id"):
    """
    异步Token统计装饰器，用于在LLM对话函数完成后异步记录Token使用情况
    
    参数:
        user_id_key: 用户ID在函数参数中的键名
        model_name_key: 模型名称在函数参数中的键名
        conversation_id_key: 对话ID在函数参数中的键名
    
    使用示例:
    ```python
    @async_token_metrics(user_id_key="user_id", model_name_key="model_name")
    async def my_chat_function(user_id: str, model_name: str, messages: List[Dict], **kwargs):
        # 函数实现...
        return {"response": "模型回复内容"}
    ```
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 如果指标统计未启用，直接调用原函数
            if not settings.metrics.enabled:
                return await func(*args, **kwargs)

            # 记录开始时间
            start_time = time.time()
            
            # 调用原函数
            result = await func(*args, **kwargs)
            
            # 计算执行时间(毫秒)
            execution_time = (time.time() - start_time) * 1000
            
            # 异步记录指标
            asyncio.create_task(_record_metrics(
                func.__name__,
                kwargs,
                result,
                execution_time,
                user_id_key,
                model_name_key,
                conversation_id_key
            ))
            
            return result
        return wrapper
    return decorator


async def _record_metrics(func_name: str, 
                        kwargs: Dict[str, Any],
                        result: Any,
                        execution_time: float,
                        user_id_key: str,
                        model_name_key: str,
                        conversation_id_key: str):
    """
    内部函数，用于异步记录指标
    
    参数:
        func_name: 被装饰的函数名
        kwargs: 函数的关键字参数
        result: 函数的返回结果
        execution_time: 执行时间(毫秒)
        user_id_key: 用户ID键名
        model_name_key: 模型名称键名
        conversation_id_key: 对话ID键名
    """
    try:
        # 从kwargs提取参数
        user_id = kwargs.get(user_id_key, "unknown")
        model_name = kwargs.get(model_name_key, "unknown")
        conversation_id = kwargs.get(conversation_id_key)
        
        # 始终记录基本信息，即使token统计功能关闭
        messages = kwargs.get("messages", [])
        
        # 从结果中提取响应
        response_text = ""
        if isinstance(result, dict):
            # 尝试从不同的常见返回格式中提取文本
            for key in ["response", "text", "content", "answer", "message"]:
                if key in result and isinstance(result[key], str):
                    response_text = result[key]
                    break
            
            # 检查嵌套字典
            if not response_text and "message" in result and isinstance(result["message"], dict):
                response_text = result["message"].get("content", "")
                
            # 检查choices格式(OpenAI风格)
            if not response_text and "choices" in result and isinstance(result["choices"], list) and result["choices"]:
                choice = result["choices"][0]
                if isinstance(choice, dict):
                    if "message" in choice and isinstance(choice["message"], dict):
                        response_text = choice["message"].get("content", "")
                    elif "text" in choice:
                        response_text = choice["text"]
        
        # 如果无法提取文本，使用字符串表示
        if not response_text and result is not None:
            response_text = str(result)
        
        # 记录指标
        await record_llm_usage(
            user_id=user_id,
            model_name=model_name,
            messages=messages,
            response_text=response_text,
            conversation_id=conversation_id,
            execution_time=execution_time,
            function=func_name
        )
    except Exception as e:
        # 捕获所有异常，确保不影响主流程
        logger.error(f"Token指标记录失败: {e}")


class TokenMetricsMiddleware:
    """
    Token计算与统计中间件
    
    提供手动方式记录Token使用情况，适用于非装饰器场景
    """
    
    @staticmethod
    async def record_usage(user_id: str,
                          model_name: str,
                          messages: List[Dict[str, str]],
                          response_text: str,
                          conversation_id: Optional[str] = None,
                          execution_time: Optional[float] = None,
                          **kwargs):
        """
        记录Token使用情况
        
        参数:
            user_id: 用户ID
            model_name: 模型名称
            messages: 输入消息列表
            response_text: 响应文本
            conversation_id: 对话ID
            execution_time: 执行时间(ms)
            **kwargs: 额外参数
        """
        if not settings.metrics.enabled:
            return
            
        try:
            # 使用工具函数记录
            return await record_llm_usage(
                user_id=user_id,
                model_name=model_name,
                messages=messages,
                response_text=response_text,
                conversation_id=conversation_id,
                execution_time=execution_time,
                **kwargs
            )
        except Exception as e:
            # 捕获所有异常，确保不影响主流程
            logger.error(f"Token指标记录失败: {e}")
            return None
