"""
上下文压缩装饰器 - 用于Agent流程中的上下文压缩
提供两种装饰器:
1. compress_retrieval_results - 压缩检索结果
2. compress_final_context - 压缩最终提交给LLM的上下文
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast
import logging

from llama_index.core.schema import NodeWithScore, Document, QueryBundle
from llama_index.core.llms import LLM

from app.tools.advanced.context_compression.context_compressor import (
    ContextCompressor, 
    CompressionConfig,
    get_context_compressor
)

logger = logging.getLogger(__name__)

# 类型变量定义
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

def compress_retrieval_results(
    config: Optional[CompressionConfig] = None,
    llm: Optional[LLM] = None
) -> Callable[[F], F]:
    """
    检索结果压缩装饰器 - 作用于检索方法，压缩检索返回的内容
    
    Args:
        config: 压缩配置
        llm: 语言模型实例
        
    Returns:
        装饰后的函数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 调用原始函数
            results = await func(*args, **kwargs)
            
            # 如果压缩未启用，直接返回原始结果
            if not config or not config.enabled:
                return results
                
            # 获取查询内容 - 通过检查函数参数
            query = None
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # 检查kwargs中是否有query参数
            for param_name in ['query', 'question', 'q', 'text', 'content']:
                if param_name in kwargs:
                    query = kwargs[param_name]
                    break
                    
            # 如果没有在kwargs中找到，检查args
            if query is None and len(args) > 1:  # 第一个通常是self
                for i, param_name in enumerate(param_names):
                    if param_name in ['query', 'question', 'q', 'text', 'content'] and i < len(args):
                        query = args[i]
                        break
            
            # 如果没有找到查询，使用空字符串
            if query is None:
                query = ""
                logger.warning("未找到查询参数，使用空字符串")
            
            # 获取压缩工具
            compressor = get_context_compressor(llm=llm, config=config)
            
            # 处理不同类型的检索结果
            if isinstance(results, dict) and "results" in results:
                # 检索工具格式的结果
                # 将结果转换为Document列表
                documents = []
                for item in results.get("results", []):
                    text = item.get("content", "")
                    metadata = item.get("metadata", {})
                    documents.append(Document(text=text, metadata=metadata))
                
                # 创建压缩上下文消息
                compressed_message = compressor.compress_to_message(query, documents, config)
                
                # 更新结果 - 添加压缩后的消息
                results["compressed_message"] = compressed_message
                results["compressed_context"] = compressed_message.content.get("compressed_context", "")
                
            elif isinstance(results, list) and len(results) > 0:
                # 文档或节点列表
                if hasattr(results[0], "node") and hasattr(results[0], "score"):
                    # NodeWithScore列表
                    compressed_message = compressor.compress_to_message(query, results, config)
                    # 返回压缩文本和原始结果
                    return {
                        "original_results": results,
                        "compressed_message": compressed_message,
                        "compressed_context": compressed_message.content.get("compressed_context", "")
                    }
                elif hasattr(results[0], "text") or isinstance(results[0], dict) and "text" in results[0]:
                    # Document列表或包含text的字典列表
                    documents = []
                    for item in results:
                        if hasattr(item, "text"):
                            documents.append(item)
                        elif isinstance(item, dict) and "text" in item:
                            text = item.get("text", "")
                            metadata = item.get("metadata", {})
                            documents.append(Document(text=text, metadata=metadata))
                    
                    compressed_message = compressor.compress_to_message(query, documents, config)
                    return {
                        "original_results": results,
                        "compressed_message": compressed_message,
                        "compressed_context": compressed_message.content.get("compressed_context", "")
                    }
            
            return results
            
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 同步版本实现类似的逻辑
            logger.warning("压缩装饰器应用于同步函数，可能无法正常工作")
            return func(*args, **kwargs)
            
        # 根据原函数是否为异步函数返回相应的包装器
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
            
    return decorator


def compress_final_context(
    config: Optional[CompressionConfig] = None,
    llm: Optional[LLM] = None
) -> Callable[[F], F]:
    """
    最终上下文压缩装饰器 - 作用于Agent的处理方法，压缩提交给模型的最终上下文
    
    Args:
        config: 压缩配置
        llm: 语言模型实例
        
    Returns:
        装饰后的函数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 如果压缩未启用，直接调用原始函数
            if not config or not config.enabled:
                return await func(*args, **kwargs)
            
            # 获取查询内容
            query = None
            for param_name in ['query', 'question', 'q', 'text', 'content']:
                if param_name in kwargs:
                    query = kwargs[param_name]
                    break
            
            # 如果没有找到查询，尝试从args中获取
            if query is None and len(args) > 1:
                # 尝试检查第二个参数（第一个通常是self）
                if isinstance(args[1], str):
                    query = args[1]
                elif hasattr(args[1], 'query'):
                    query = args[1].query
            
            # 如果没有找到查询，使用空字符串
            if query is None:
                query = ""
                logger.warning("未找到查询参数，使用空字符串")
            
            # 检查是否有上下文参数
            context = kwargs.get('context', None)
            
            # 如果没有上下文参数，直接调用原始函数
            if context is None:
                return await func(*args, **kwargs)
            
            # 获取压缩工具
            compressor = get_context_compressor(llm=llm, config=config)
            
            # 根据上下文类型进行压缩
            if isinstance(context, str):
                # 字符串上下文
                compressed_message = compressor.compress_to_message(query, context, config)
                # 更新kwargs - 可以选择传递完整消息或仅压缩内容
                if config and config.use_message_format:
                    kwargs['context'] = compressed_message
                else:
                    kwargs['context'] = compressed_message.content.get("compressed_context", "")
                    # 可以添加元数据
                    if 'metadata' in kwargs:
                        kwargs['metadata']['compressed_context'] = {
                            "method": compressed_message.content.get("method", "unknown"),
                            "ratio": compressed_message.content.get("compression_ratio", 1.0),
                            "source_count": compressed_message.content.get("source_count", 0)
                        }
            elif isinstance(context, list):
                # 列表上下文 - 可能是文档或节点列表
                if len(context) > 0:
                    if hasattr(context[0], 'node') and hasattr(context[0], 'score'):
                        # NodeWithScore列表
                        compressed_message = compressor.compress_to_message(query, context, config)
                        if config and config.use_message_format:
                            kwargs['context'] = compressed_message
                        else:
                            kwargs['context'] = compressed_message.content.get("compressed_context", "")
                    elif hasattr(context[0], 'text'):
                        # Document列表
                        compressed_message = compressor.compress_to_message(query, context, config)
                        if config and config.use_message_format:
                            kwargs['context'] = compressed_message
                        else:
                            kwargs['context'] = compressed_message.content.get("compressed_context", "")
            elif hasattr(context, 'content') and isinstance(context.content, dict) and "compressed_context" in context.content:
                # 已经是压缩上下文消息，直接使用
                if not config or not config.use_message_format:
                    kwargs['context'] = context.content.get("compressed_context", "")
            
            # 调用原始函数
            return await func(*args, **kwargs)
            
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 同步版本实现类似的逻辑
            logger.warning("压缩装饰器应用于同步函数，可能无法正常工作")
            return func(*args, **kwargs)
            
        # 根据原函数是否为异步函数返回相应的包装器
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
            
    return decorator
