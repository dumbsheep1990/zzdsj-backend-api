from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
import re

# 基础知识库模式
class KnowledgeBaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="知识库描述")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="知识库设置")
    type: Optional[str] = Field("default", description="知识库类型")
    embedding_model: Optional[str] = Field("text-embedding-ada-002", description="嵌入模型")

    @validator('name')
    def validate_name(cls, v):
        """验证知识库名称"""
        if not v or not v.strip():
            raise ValueError('知识库名称不能为空')
        
        # 名称不能包含特殊字符
        if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$', v):
            raise ValueError('知识库名称只能包含字母、数字、中文、空格、下划线和连字符')
        
        return v.strip()

    @validator('type')
    def validate_type(cls, v):
        """验证知识库类型"""
        valid_types = ['default', 'document', 'qa', 'structured', 'multimodal']
        if v and v not in valid_types:
            raise ValueError(f'无效的知识库类型: {v}。有效类型: {valid_types}')
        return v

    @validator('embedding_model')
    def validate_embedding_model(cls, v):
        """验证嵌入模型"""
        if v and not v.strip():
            raise ValueError('嵌入模型不能为空')
        return v.strip() if v else None

# 创建知识库模式
class KnowledgeBaseCreate(KnowledgeBaseBase):
    
    @root_validator
    def validate_knowledge_base_config(cls, values):
        """验证知识库配置的完整性"""
        kb_type = values.get('type', 'default')
        settings = values.get('settings', {})
        
        # 根据知识库类型设置默认配置
        if kb_type == 'document':
            default_settings = {
                'chunk_size': 1000,
                'chunk_overlap': 200,
                'enable_ocr': False,
                'supported_formats': ['pdf', 'docx', 'txt', 'md']
            }
            # 合并用户设置和默认设置
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            values['settings'] = settings
        elif kb_type == 'qa':
            default_settings = {
                'similarity_threshold': 0.7,
                'max_results': 10,
                'enable_fuzzy_match': True
            }
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            values['settings'] = settings
        elif kb_type == 'multimodal':
            default_settings = {
                'image_processing': True,
                'audio_processing': False,
                'video_processing': False,
                'max_file_size_mb': 100
            }
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            values['settings'] = settings
        
        return values

# 更新知识库模式
class KnowledgeBaseUpdate(BaseModel):
    """更新知识库模式"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    type: Optional[str] = None
    embedding_model: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        """验证知识库名称"""
        if v is not None:
            if not v.strip():
                raise ValueError('知识库名称不能为空')
            
            if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\s_-]+$', v):
                raise ValueError('知识库名称只能包含字母、数字、中文、空格、下划线和连字符')
            
            return v.strip()
        return v

    @validator('type')
    def validate_type(cls, v):
        """验证知识库类型"""
        if v is not None:
            valid_types = ['default', 'document', 'qa', 'structured', 'multimodal']
            if v not in valid_types:
                raise ValueError(f'无效的知识库类型: {v}。有效类型: {valid_types}')
        return v

# 知识库模式（用于响应）
class KnowledgeBase(KnowledgeBaseBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_documents: int
    total_tokens: int
    agno_kb_id: Optional[str] = None
    
    class Config:
        orm_mode = True

# 带统计数据的知识库
class KnowledgeBaseWithStats(KnowledgeBase):
    document_count: int
    total_tokens: int
    file_types: Dict[str, int] = Field(default_factory=dict)
    processing_stats: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        orm_mode = True

# 文档基础模式
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="文档标题")
    content: Optional[str] = Field(None, description="文档内容")
    mime_type: Optional[str] = Field("text/plain", description="MIME类型")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="文档元数据")
    file_path: Optional[str] = Field(None, description="文件路径")

    @validator('title')
    def validate_title(cls, v):
        """验证文档标题"""
        if not v or not v.strip():
            raise ValueError('文档标题不能为空')
        return v.strip()

    @validator('mime_type')
    def validate_mime_type(cls, v):
        """验证MIME类型"""
        if v:
            valid_mime_types = [
                'text/plain', 'text/markdown', 'text/html',
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'image/jpeg', 'image/png', 'image/gif'
            ]
            if v not in valid_mime_types:
                # 允许通用的MIME类型格式
                if not re.match(r'^[a-zA-Z]+/[a-zA-Z0-9\.\-\+]+$', v):
                    raise ValueError(f'无效的MIME类型格式: {v}')
        return v

# 创建文档模式
class DocumentCreate(DocumentBase):
    knowledge_base_id: int = Field(..., gt=0, description="知识库ID")

    @root_validator
    def validate_document_content(cls, values):
        """验证文档内容的完整性"""
        content = values.get('content')
        file_path = values.get('file_path')
        mime_type = values.get('mime_type', 'text/plain')
        
        # 如果没有内容也没有文件路径，抛出错误
        if not content and not file_path:
            raise ValueError('文档必须提供内容或文件路径')
        
        # 根据MIME类型验证内容
        if content and mime_type.startswith('text/'):
            if len(content.strip()) < 10:
                raise ValueError('文本内容长度至少为10个字符')
        
        return values

# 更新文档模式
class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

    @validator('title')
    def validate_title(cls, v):
        """验证文档标题"""
        if v is not None:
            if not v.strip():
                raise ValueError('文档标题不能为空')
            return v.strip()
        return v

    @validator('status')
    def validate_status(cls, v):
        """验证文档状态"""
        if v is not None:
            valid_statuses = ['pending', 'processing', 'completed', 'failed']
            if v not in valid_statuses:
                raise ValueError(f'无效的文档状态: {v}。有效状态: {valid_statuses}')
        return v

# 文档模式（用于响应）
class Document(DocumentBase):
    id: int
    knowledge_base_id: int
    created_at: datetime
    updated_at: datetime
    file_size: int
    status: str
    error_message: Optional[str] = None
    
    class Config:
        orm_mode = True

# 文档块模式
class DocumentChunk(BaseModel):
    id: int
    document_id: int
    content: str = Field(..., min_length=1, description="文档块内容")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_id: str
    token_count: int = Field(..., ge=0, description="令牌数量")
    created_at: datetime
    
    class Config:
        orm_mode = True

# 知识库统计数据模式
class KnowledgeBaseStats(BaseModel):
    document_count: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    processed_count: int = Field(..., ge=0)
    pending_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    file_types: Dict[str, int] = Field(default_factory=dict)
    
    @validator('*', pre=True)
    def validate_non_negative(cls, v):
        """验证统计数据不能为负数"""
        if isinstance(v, int) and v < 0:
            raise ValueError('统计数据不能为负数')
        return v

# 文档列表响应
class DocumentListResponse(BaseModel):
    items: List[Document]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)

    @validator('page_size')
    def validate_page_size(cls, v):
        """验证分页大小"""
        if v > 100:
            raise ValueError('分页大小不能超过100')
        return v

# 文档搜索请求
class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="搜索查询")
    knowledge_base_id: Optional[int] = Field(None, gt=0, description="知识库ID")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="相似度阈值")
    
    @validator('query')
    def validate_query(cls, v):
        """验证搜索查询"""
        if not v or not v.strip():
            raise ValueError('搜索查询不能为空')
        return v.strip()

# 文档搜索结果
class DocumentSearchResult(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    content: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

# 批量文档操作请求
class BulkDocumentRequest(BaseModel):
    document_ids: List[int] = Field(..., min_items=1, max_items=100, description="文档ID列表")
    action: str = Field(..., description="操作类型")
    
    @validator('action')
    def validate_action(cls, v):
        """验证操作类型"""
        valid_actions = ['delete', 'reprocess', 'activate', 'deactivate']
        if v not in valid_actions:
            raise ValueError(f'无效的操作类型: {v}。有效操作: {valid_actions}')
        return v

# 批量操作响应
class BulkOperationResponse(BaseModel):
    success_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    errors: List[str] = Field(default_factory=list)
    processed_ids: List[int] = Field(default_factory=list)
