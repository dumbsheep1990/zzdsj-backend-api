"""
模型提供商和模型信息的Pydantic模式
用于API请求和响应的数据验证
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import re


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
    name: str = Field(..., min_length=1, max_length=100, description="提供商名称")
    provider_type: ProviderTypeEnum
    api_key: Optional[str] = Field(None, min_length=8, description="API密钥")
    api_base: Optional[str] = Field(None, description="API基础URL")
    api_version: Optional[str] = Field(None, description="API版本")
    is_default: bool = False
    is_active: bool = True
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="扩展配置")

    @validator('name')
    def validate_name(cls, v):
        """验证提供商名称"""
        if not v or not v.strip():
            raise ValueError('提供商名称不能为空')
        
        # 名称不能包含特殊字符
        if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$', v):
            raise ValueError('提供商名称只能包含字母、数字、中文、空格、下划线和连字符')
        
        return v.strip()

    @validator('api_base')
    def validate_api_base(cls, v):
        """验证API基础URL"""
        if v and not re.match(r'^https?://', v):
            raise ValueError('API基础URL必须以http://或https://开头')
        return v

    @validator('api_key')
    def validate_api_key(cls, v, values):
        """验证API密钥"""
        if v is not None:
            # 移除空白字符
            v = v.strip()
            if len(v) < 8:
                raise ValueError('API密钥长度至少为8个字符')
            
            # 根据提供商类型验证API密钥格式
            provider_type = values.get('provider_type')
            if provider_type == ProviderTypeEnum.OPENAI and not v.startswith('sk-'):
                raise ValueError('OpenAI API密钥必须以sk-开头')
            elif provider_type == ProviderTypeEnum.ANTHROPIC and not v.startswith('sk-ant-'):
                raise ValueError('Anthropic API密钥必须以sk-ant-开头')
        
        return v


class ModelProviderCreate(ModelProviderBase):
    """创建模型提供商请求模式"""
    
    @root_validator
    def validate_provider_config(cls, values):
        """验证提供商配置的完整性"""
        provider_type = values.get('provider_type')
        api_key = values.get('api_key')
        api_base = values.get('api_base')
        
        # 对于非本地部署的提供商，需要API密钥
        if provider_type in [ProviderTypeEnum.OPENAI, ProviderTypeEnum.ANTHROPIC, 
                           ProviderTypeEnum.ZHIPU, ProviderTypeEnum.DEEPSEEK]:
            if not api_key:
                raise ValueError(f'{provider_type.value}提供商需要提供API密钥')
        
        # 对于本地部署的提供商，需要API基础URL
        if provider_type in [ProviderTypeEnum.OLLAMA, ProviderTypeEnum.VLLM]:
            if not api_base:
                raise ValueError(f'{provider_type.value}提供商需要提供API基础URL')
        
        return values


class ModelProviderUpdate(BaseModel):
    """更新模型提供商请求模式"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = Field(None, min_length=8)
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None

    @validator('name')
    def validate_name(cls, v):
        """验证提供商名称"""
        if v is not None:
            if not v.strip():
                raise ValueError('提供商名称不能为空')
            
            if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$', v):
                raise ValueError('提供商名称只能包含字母、数字、中文、空格、下划线和连字符')
            
            return v.strip()
        return v

    @validator('api_base')
    def validate_api_base(cls, v):
        """验证API基础URL"""
        if v and not re.match(r'^https?://', v):
            raise ValueError('API基础URL必须以http://或https://开头')
        return v


class ModelInfoBase(BaseModel):
    """模型信息基础模式"""
    model_id: str = Field(..., min_length=1, max_length=200, description="模型ID")
    display_name: Optional[str] = Field(None, max_length=200, description="显示名称")
    capabilities: List[str] = Field(default_factory=list, description="模型能力列表")
    is_default: bool = False
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="模型配置")

    @validator('model_id')
    def validate_model_id(cls, v):
        """验证模型ID"""
        if not v or not v.strip():
            raise ValueError('模型ID不能为空')
        
        # 模型ID应该是有效的标识符
        if not re.match(r'^[a-zA-Z0-9\._-]+$', v):
            raise ValueError('模型ID只能包含字母、数字、点、下划线和连字符')
        
        return v.strip()

    @validator('capabilities')
    def validate_capabilities(cls, v):
        """验证模型能力"""
        if v:
            valid_capabilities = [cap.value for cap in ModelCapabilityEnum]
            for capability in v:
                if capability not in valid_capabilities:
                    raise ValueError(f'无效的模型能力: {capability}。有效能力: {valid_capabilities}')
        return v

    @validator('display_name')
    def validate_display_name(cls, v):
        """验证显示名称"""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class ModelInfoCreate(ModelInfoBase):
    """创建模型信息请求模式"""
    
    @root_validator
    def validate_model_config(cls, values):
        """验证模型配置的一致性"""
        capabilities = values.get('capabilities', [])
        config = values.get('config', {})
        
        # 如果模型支持视觉能力，检查相关配置
        if ModelCapabilityEnum.VISION in capabilities:
            if not config.get('max_image_size'):
                # 设置默认的图像处理配置
                config['max_image_size'] = 1024
                values['config'] = config
        
        # 如果模型支持函数调用，检查相关配置
        if ModelCapabilityEnum.FUNCTION_CALLING in capabilities:
            if 'max_functions' not in config:
                config['max_functions'] = 128
                values['config'] = config
        
        return values


class ModelInfoUpdate(BaseModel):
    """更新模型信息请求模式"""
    display_name: Optional[str] = Field(None, max_length=200)
    capabilities: Optional[List[str]] = None
    is_default: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None

    @validator('capabilities')
    def validate_capabilities(cls, v):
        """验证模型能力"""
        if v is not None:
            valid_capabilities = [cap.value for cap in ModelCapabilityEnum]
            for capability in v:
                if capability not in valid_capabilities:
                    raise ValueError(f'无效的模型能力: {capability}。有效能力: {valid_capabilities}')
        return v

    @validator('display_name')
    def validate_display_name(cls, v):
        """验证显示名称"""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


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
    prompt: str = Field("Hello, can you tell me what time it is?", min_length=1, max_length=1000)
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """验证测试提示词"""
        if not v or not v.strip():
            raise ValueError('测试提示词不能为空')
        return v.strip()


class ModelTestResponse(BaseModel):
    """测试模型连接响应"""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None
    
    @validator('latency_ms')
    def validate_latency(cls, v):
        """验证延迟时间"""
        if v is not None and v < 0:
            raise ValueError('延迟时间不能为负数')
        return v


class ModelProviderHealth(BaseModel):
    """模型提供商健康状态"""
    provider_id: int
    provider_name: str
    is_healthy: bool
    last_check: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None


class ModelProviderStats(BaseModel):
    """模型提供商统计信息"""
    provider_id: int
    provider_name: str
    total_models: int
    active_models: int
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: Optional[float] = None
