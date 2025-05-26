"""
压缩上下文消息模块
提供处理和格式化压缩上下文消息的功能
"""

from typing import Dict, Any, List, Optional, Union
import json
from app.messaging.core.models import Message, MessageType, MessageRole


class CompressedContextMessage(Message):
    """压缩上下文消息"""
    type: MessageType = MessageType.COMPRESSED_CONTEXT
    content: Dict[str, Any]
    
    @property
    def original_context(self) -> str:
        """获取原始上下文（如果存储了的话）"""
        return self.content.get("original_context", "")
    
    @property
    def compressed_context(self) -> str:
        """获取压缩后的上下文"""
        return self.content.get("compressed_context", "")
    
    @property
    def compression_method(self) -> str:
        """获取压缩方法"""
        return self.content.get("method", "unknown")
    
    @property
    def compression_ratio(self) -> float:
        """获取压缩比例"""
        return self.content.get("compression_ratio", 1.0)
    
    @property
    def source_count(self) -> int:
        """获取源文档数量"""
        return self.content.get("source_count", 0)
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        # 只返回压缩后的内容，以便模型处理
        return {
            "role": self.role.value,
            "content": self.compressed_context
        }


def convert_compressed_context_to_internal(
    compressed_text: str,
    original_text: Optional[str] = None,
    method: str = "tree_summarize",
    compression_ratio: float = 0.0,
    source_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """
    将压缩上下文转换为内部消息格式
    
    参数:
        compressed_text: 压缩后的文本
        original_text: 原始文本
        method: 压缩方法
        compression_ratio: 压缩比例
        source_count: 源文档数量
        metadata: 额外元数据
        
    返回:
        压缩上下文消息对象
    """
    from app.messaging.core.models import MessageRole
    
    if metadata is None:
        metadata = {}
    
    # 计算压缩比例（如果未提供）
    if compression_ratio == 0.0 and original_text:
        original_len = len(original_text)
        compressed_len = len(compressed_text)
        if original_len > 0:
            compression_ratio = compressed_len / original_len
    
    content = {
        "compressed_context": compressed_text,
        "method": method,
        "compression_ratio": compression_ratio,
        "source_count": source_count
    }
    
    # 如果提供了原始文本，也存储它（但要注意内存消耗）
    if original_text:
        content["original_context"] = original_text
    
    return CompressedContextMessage(
        role=MessageRole.SYSTEM,
        content=content,
        metadata={**metadata, "compression": True}
    )
