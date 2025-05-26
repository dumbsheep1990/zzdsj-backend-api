"""
上下文压缩相关的Pydantic模型
定义上下文压缩工具的配置和输出格式
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


class CompressionMethod(str, Enum):
    """压缩方法枚举"""
    TREE_SUMMARIZE = "tree_summarize"
    COMPACT_AND_REFINE = "compact_and_refine"


class CompressionPhase(str, Enum):
    """压缩阶段枚举"""
    RETRIEVAL = "retrieval"  # 检索结果处理阶段
    FINAL = "final"          # 最终上下文处理阶段


class CompressionStatus(str, Enum):
    """压缩状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class CompressionConfig(BaseModel):
    """压缩配置模型"""
    enabled: bool = Field(True, description="是否启用压缩")
    method: CompressionMethod = Field(CompressionMethod.TREE_SUMMARIZE, description="压缩方法")
    top_n: int = Field(5, description="保留的最相关文档数量")
    num_children: int = Field(2, description="树状压缩中每个节点的子节点数量")
    streaming: bool = Field(False, description="是否启用流式处理")
    rerank_model: Optional[str] = Field(None, description="重排序模型名称")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    temperature: float = Field(0.1, description="LLM生成温度")
    store_original: bool = Field(False, description="是否存储原始文本")
    use_message_format: bool = Field(True, description="是否使用消息格式输出")
    phase: CompressionPhase = Field(CompressionPhase.FINAL, description="压缩阶段")
    
    class Config:
        use_enum_values = True
        extra = "allow"


class CompressedContextResult(BaseModel):
    """压缩上下文结果模型"""
    original_context: Optional[str] = Field(None, description="原始上下文")
    compressed_context: str = Field(..., description="压缩后的上下文")
    method: str = Field(..., description="使用的压缩方法")
    compression_ratio: float = Field(..., description="压缩比例")
    source_count: int = Field(0, description="处理的源文档数量")
    execution_time_ms: int = Field(0, description="执行时间（毫秒）")
    status: CompressionStatus = Field(CompressionStatus.SUCCESS, description="执行状态")
    
    class Config:
        use_enum_values = True


class CompressionToolCreate(BaseModel):
    """上下文压缩工具创建模型"""
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    compression_method: CompressionMethod = Field(CompressionMethod.TREE_SUMMARIZE, description="压缩方法")
    is_enabled: bool = Field(True, description="是否启用")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置参数")
    
    class Config:
        use_enum_values = True


class CompressionToolResponse(BaseModel):
    """上下文压缩工具响应模型"""
    id: int = Field(..., description="工具ID")
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    compression_method: str = Field(..., description="压缩方法")
    is_enabled: bool = Field(..., description="是否启用")
    config: Dict[str, Any] = Field(..., description="配置参数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        orm_mode = True


class AgentCompressionConfigCreate(BaseModel):
    """智能体压缩配置创建模型"""
    agent_id: int = Field(..., description="智能体ID")
    enabled: bool = Field(True, description="是否启用")
    method: CompressionMethod = Field(CompressionMethod.TREE_SUMMARIZE, description="压缩方法")
    top_n: int = Field(5, description="保留的最相关文档数量")
    num_children: int = Field(2, description="树状压缩中每个节点的子节点数量")
    streaming: bool = Field(False, description="是否启用流式处理")
    rerank_model: Optional[str] = Field(None, description="重排序模型名称")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    temperature: float = Field(0.1, description="LLM生成温度")
    store_original: bool = Field(False, description="是否存储原始文本")
    use_message_format: bool = Field(True, description="是否使用消息格式输出")
    phase: CompressionPhase = Field(CompressionPhase.FINAL, description="压缩阶段")
    
    class Config:
        use_enum_values = True


class AgentCompressionConfigResponse(BaseModel):
    """智能体压缩配置响应模型"""
    id: int = Field(..., description="配置ID")
    agent_id: int = Field(..., description="智能体ID")
    enabled: bool = Field(..., description="是否启用")
    method: str = Field(..., description="压缩方法")
    top_n: int = Field(..., description="保留的最相关文档数量")
    num_children: int = Field(..., description="树状压缩中每个节点的子节点数量")
    streaming: bool = Field(..., description="是否启用流式处理")
    rerank_model: Optional[str] = Field(None, description="重排序模型名称")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    temperature: float = Field(..., description="LLM生成温度")
    store_original: bool = Field(..., description="是否存储原始文本")
    use_message_format: bool = Field(..., description="是否使用消息格式输出")
    phase: str = Field(..., description="压缩阶段")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        orm_mode = True


class CompressionExecutionResponse(BaseModel):
    """压缩执行记录响应模型"""
    id: int = Field(..., description="执行记录ID")
    execution_id: str = Field(..., description="执行ID")
    agent_id: Optional[int] = Field(None, description="智能体ID")
    compression_config_id: Optional[int] = Field(None, description="压缩配置ID")
    query: Optional[str] = Field(None, description="查询内容")
    original_content_length: int = Field(..., description="原始内容长度")
    compressed_content_length: int = Field(..., description="压缩后内容长度")
    compression_ratio: float = Field(..., description="压缩比例")
    source_count: int = Field(..., description="处理的源文档数量")
    execution_time_ms: int = Field(..., description="执行时间（毫秒）")
    status: str = Field(..., description="执行状态")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(..., description="元数据")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        orm_mode = True
