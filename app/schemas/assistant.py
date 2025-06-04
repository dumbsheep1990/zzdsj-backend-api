"""
助手模式模块: 助手API请求和响应的Pydantic模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from enum import Enum
import re


class AssistantCapability(str, Enum):
    """助手能力的枚举类型"""
    TEXT = "text"
    MULTIMODAL = "multimodal"
    VOICE = "voice"
    CODE = "code"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    TOOLS = "tools"


class AssistantBase(BaseModel):
    """具有共同属性的基础助手模式"""
    name: str = Field(..., description="助手名称", max_length=100, min_length=1)
    description: Optional[str] = Field(None, description="助手目的的描述", max_length=500)
    model: str = Field(..., description="助手使用的模型", max_length=100, min_length=1)
    capabilities: List[str] = Field(
        default=["text"],
        description="助手能力列表（文本、多模态、语音等）"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="助手特定配置"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="引导助手行为的系统提示",
        max_length=4000
    )

    @validator('name')
    def validate_name(cls, v):
        """验证助手名称"""
        if not v or not v.strip():
            raise ValueError('助手名称不能为空')
        
        # 助手名称不能包含特殊字符
        if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$', v):
            raise ValueError('助手名称只能包含字母、数字、中文、空格、下划线和连字符')
        
        return v.strip()

    @validator('model')
    def validate_model(cls, v):
        """验证模型名称"""
        if not v or not v.strip():
            raise ValueError('模型名称不能为空')
        
        # 模型名称应该是有效的标识符
        if not re.match(r'^[a-zA-Z0-9\._-]+$', v):
            raise ValueError('模型名称格式不正确')
        
        return v.strip()

    @validator('capabilities')
    def validate_capabilities(cls, v):
        """验证助手能力"""
        if not v:
            return ["text"]  # 默认能力
        
        valid_capabilities = [cap.value for cap in AssistantCapability]
        for capability in v:
            if capability not in valid_capabilities:
                raise ValueError(f'无效的助手能力: {capability}。有效能力: {valid_capabilities}')
        
        # 去重并保持顺序
        seen = set()
        unique_capabilities = []
        for cap in v:
            if cap not in seen:
                seen.add(cap)
                unique_capabilities.append(cap)
        
        return unique_capabilities

    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        """验证系统提示"""
        if v is not None:
            v = v.strip()
            if v and len(v) < 10:
                raise ValueError('系统提示长度至少为10个字符')
        return v


class AssistantCreate(AssistantBase):
    """创建新助手的模式"""
    knowledge_base_ids: Optional[List[int]] = Field(
        default_factory=list,
        description="要与助手关联的知识库ID列表"
    )

    @validator('knowledge_base_ids')
    def validate_knowledge_base_ids(cls, v):
        """验证知识库ID列表"""
        if v is not None:
            # 去重
            unique_ids = list(set(v))
            # 验证ID都是正整数
            for kb_id in unique_ids:
                if not isinstance(kb_id, int) or kb_id <= 0:
                    raise ValueError('知识库ID必须是正整数')
            return unique_ids
        return []

    @root_validator
    def validate_assistant_config(cls, values):
        """验证助手配置的一致性"""
        capabilities = values.get('capabilities', [])
        configuration = values.get('configuration', {})
        knowledge_base_ids = values.get('knowledge_base_ids', [])
        
        # 如果助手具有检索能力，建议关联知识库
        if AssistantCapability.RETRIEVAL in capabilities and not knowledge_base_ids:
            # 这里只是警告，不抛出错误
            pass
        
        # 根据能力设置默认配置
        if AssistantCapability.VOICE in capabilities:
            if 'voice_settings' not in configuration:
                configuration['voice_settings'] = {
                    'speed': 1.0,
                    'pitch': 0.0,
                    'voice_id': 'default'
                }
        
        if AssistantCapability.CODE in capabilities:
            if 'code_settings' not in configuration:
                configuration['code_settings'] = {
                    'execution_timeout': 30,
                    'max_output_length': 10000,
                    'allowed_languages': ['python', 'javascript', 'bash']
                }
        
        values['configuration'] = configuration
        return values


class AssistantUpdate(BaseModel):
    """更新助手的模式"""
    name: Optional[str] = Field(None, description="助手名称", max_length=100, min_length=1)
    description: Optional[str] = Field(None, description="助手目的的描述", max_length=500)
    model: Optional[str] = Field(None, description="助手使用的模型", max_length=100, min_length=1)
    capabilities: Optional[List[str]] = Field(
        None,
        description="助手能力列表（文本、多模态、语音等）"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="助手特定配置"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="引导助手行为的系统提示",
        max_length=4000
    )
    knowledge_base_ids: Optional[List[int]] = Field(
        None,
        description="要与助手关联的知识库ID列表"
    )

    @validator('name')
    def validate_name(cls, v):
        """验证助手名称"""
        if v is not None:
            if not v.strip():
                raise ValueError('助手名称不能为空')
            
            if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$', v):
                raise ValueError('助手名称只能包含字母、数字、中文、空格、下划线和连字符')
            
            return v.strip()
        return v

    @validator('model')
    def validate_model(cls, v):
        """验证模型名称"""
        if v is not None:
            if not v.strip():
                raise ValueError('模型名称不能为空')
            
            if not re.match(r'^[a-zA-Z0-9\._-]+$', v):
                raise ValueError('模型名称格式不正确')
            
            return v.strip()
        return v

    @validator('capabilities')
    def validate_capabilities(cls, v):
        """验证助手能力"""
        if v is not None:
            valid_capabilities = [cap.value for cap in AssistantCapability]
            for capability in v:
                if capability not in valid_capabilities:
                    raise ValueError(f'无效的助手能力: {capability}。有效能力: {valid_capabilities}')
            
            # 去重并保持顺序
            seen = set()
            unique_capabilities = []
            for cap in v:
                if cap not in seen:
                    seen.add(cap)
                    unique_capabilities.append(cap)
            
            return unique_capabilities
        return v

    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        """验证系统提示"""
        if v is not None:
            v = v.strip()
            if v and len(v) < 10:
                raise ValueError('系统提示长度至少为10个字符')
        return v


class AssistantResponse(AssistantBase):
    """助手响应的模式"""
    id: int
    access_url: Optional[str] = Field(None, description="访问助手Web界面的URL")
    created_at: datetime
    updated_at: Optional[datetime] = None
    knowledge_base_ids: List[int] = Field([], description="关联知识库ID列表")
    
    class Config:
        orm_mode = True


class AssistantList(BaseModel):
    """助手列表的模式"""
    assistants: List[AssistantResponse]
    total: int = Field(..., ge=0, description="总数量")


class ConversationBase(BaseModel):
    """会话基础模式"""
    title: Optional[str] = Field(None, description="会话标题", max_length=200)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任意元数据")

    @validator('title')
    def validate_title(cls, v):
        """验证会话标题"""
        if v is not None:
            v = v.strip()
            if v:
                # 标题不能包含特殊字符
                if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_\-\.\(\)]+$', v):
                    raise ValueError('会话标题只能包含字母、数字、中文、空格和常用标点符号')
                
                if len(v) < 2:
                    raise ValueError('会话标题长度至少为2个字符')
                
                return v
        return v


class ConversationCreate(ConversationBase):
    """创建新会话的模式"""
    assistant_id: int = Field(..., gt=0, description="助手ID")
    
    @validator('assistant_id')
    def validate_assistant_id(cls, v):
        """验证助手ID"""
        if v <= 0:
            raise ValueError('助手ID必须是正整数')
        return v

    @root_validator
    def validate_conversation_config(cls, values):
        """验证会话配置"""
        title = values.get('title')
        
        # 如果没有提供标题，自动生成一个
        if not title:
            from datetime import datetime
            values['title'] = f"新会话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return values


class ConversationResponse(ConversationBase):
    """会话响应的模式"""
    id: int
    assistant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = Field(0, ge=0, description="消息数量")
    
    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    """消息基础模式"""
    content: str = Field(..., description="消息内容", min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="消息元数据")

    @validator('content')
    def validate_content(cls, v):
        """验证消息内容"""
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        
        # 检查内容长度
        if len(v.strip()) < 1:
            raise ValueError('消息内容不能为空')
        
        return v.strip()


class MessageCreate(MessageBase):
    """创建新消息的模式"""
    conversation_id: int = Field(..., gt=0, description="会话ID")
    role: str = Field(..., description="消息角色")
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        """验证会话ID"""
        if v <= 0:
            raise ValueError('会话ID必须是正整数')
        return v

    @validator('role')
    def validate_role(cls, v):
        """验证消息角色"""
        valid_roles = ['user', 'assistant', 'system', 'tool']
        if v not in valid_roles:
            raise ValueError(f'无效的消息角色: {v}。有效角色: {valid_roles}')
        return v

    @root_validator
    def validate_message_config(cls, values):
        """验证消息配置"""
        role = values.get('role')
        content = values.get('content')
        metadata = values.get('metadata', {})
        
        # 系统消息通常较短，用户消息和助手消息可以较长
        if role == 'system' and len(content) > 1000:
            raise ValueError('系统消息长度不应超过1000个字符')
        
        # 为不同角色设置默认元数据
        if role == 'user' and 'timestamp' not in metadata:
            from datetime import datetime
            metadata['timestamp'] = datetime.now().isoformat()
            values['metadata'] = metadata
        
        return values


class MessageResponse(MessageBase):
    """消息响应的模式"""
    id: int
    conversation_id: int
    role: str
    created_at: datetime
    
    class Config:
        orm_mode = True


class AssistantSummary(BaseModel):
    """助手摘要模式"""
    id: int
    name: str
    description: Optional[str] = None
    capabilities: List[str]
    model: str
    access_url: Optional[str] = None
    conversation_count: int = Field(0, ge=0, description="会话数量")
    
    class Config:
        orm_mode = True


class ApiKeyCreate(BaseModel):
    """创建API密钥的模式"""
    name: str = Field(..., description="API密钥名称", min_length=1, max_length=100)
    assistant_id: Optional[int] = Field(None, description="可选地限制密钥到特定助手")
    expires_at: Optional[datetime] = Field(None, description="可选地设置过期日期")

    @validator('name')
    def validate_name(cls, v):
        """验证API密钥名称"""
        if not v or not v.strip():
            raise ValueError('API密钥名称不能为空')
        
        # 名称不能包含特殊字符
        if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$', v):
            raise ValueError('API密钥名称只能包含字母、数字、中文、空格、下划线和连字符')
        
        return v.strip()

    @validator('assistant_id')
    def validate_assistant_id(cls, v):
        """验证助手ID"""
        if v is not None and v <= 0:
            raise ValueError('助手ID必须是正整数')
        return v

    @validator('expires_at')
    def validate_expires_at(cls, v):
        """验证过期时间"""
        if v is not None:
            from datetime import datetime
            if v <= datetime.now():
                raise ValueError('过期时间必须是未来时间')
        return v


class ApiKeyResponse(BaseModel):
    """API密钥响应的模式"""
    id: int
    name: str
    key: str
    assistant_id: Optional[int] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = Field(True, description="是否激活")
    
    class Config:
        orm_mode = True


class AssistantStats(BaseModel):
    """助手统计信息"""
    assistant_id: int
    conversation_count: int = Field(0, ge=0)
    message_count: int = Field(0, ge=0)
    avg_response_time_ms: Optional[float] = Field(None, ge=0.0)
    user_count: int = Field(0, ge=0)
    last_used_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class ConversationExport(BaseModel):
    """会话导出模式"""
    format: str = Field(..., description="导出格式")
    include_metadata: bool = Field(False, description="是否包含元数据")
    
    @validator('format')
    def validate_format(cls, v):
        """验证导出格式"""
        valid_formats = ['json', 'txt', 'csv', 'markdown']
        if v not in valid_formats:
            raise ValueError(f'不支持的导出格式: {v}。支持的格式: {valid_formats}')
        return v
