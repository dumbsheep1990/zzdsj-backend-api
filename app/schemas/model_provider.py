"""
模型提供商和模型信息的Pydantic模式
用于API请求和响应的数据验证
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class ProviderTypeEnum(str, Enum):
    """模型提供商类型枚举"""
    OPENAI = "openai"
    ZHIPU = "zhipu"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    VLLM = "vllm"
    DASHSCOPE = "dashscope"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"
    CUSTOM = "custom"


class ModelCapabilityEnum(str, Enum):
    """模型能力枚举"""
    COMPLETION = "completion"
    CHAT = "chat"
    EMBEDDING = "embedding"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"


class ModelProviderBase(BaseModel):
    """模型提供商基础模式"""
    name: str
    provider_type: ProviderTypeEnum
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None


class ModelProviderCreate(ModelProviderBase):
    """创建模型提供商请求模式"""
    pass


class ModelProviderUpdate(BaseModel):
    """更新模型提供商请求模式"""
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ModelInfoBase(BaseModel):
    """模型信息基础模式"""
    model_id: str
    display_name: Optional[str] = None
    capabilities: List[str] = []
    is_default: bool = False
    config: Optional[Dict[str, Any]] = None


class ModelInfoCreate(ModelInfoBase):
    """创建模型信息请求模式"""
    pass


class ModelInfoUpdate(BaseModel):
    """更新模型信息请求模式"""
    display_name: Optional[str] = None
    capabilities: Optional[List[str]] = None
    is_default: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ModelInfo(ModelInfoBase):
    """模型信息响应模式"""
    id: int
    provider_id: int

    class Config:
        orm_mode = True


class ModelProvider(ModelProviderBase):
    """模型提供商响应模式"""
    id: int
    models: List[ModelInfo] = []

    class Config:
        orm_mode = True


class ModelProviderList(BaseModel):
    """模型提供商列表响应"""
    providers: List[ModelProvider]


class ModelTestRequest(BaseModel):
    """测试模型连接请求"""
    provider_id: int
    model_id: Optional[str] = None
    prompt: str = "Hello, can you tell me what time it is?"


class ModelTestResponse(BaseModel):
    """测试模型连接响应"""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None
