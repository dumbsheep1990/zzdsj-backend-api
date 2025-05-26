"""
API共享数据验证系统
提供三层API架构的统一数据验证和清洗机制
"""

from typing import Any, Dict, List, Optional, Union, Callable, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, validator, ValidationError
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """
    基础验证器抽象类
    定义验证器的基本接口
    """
    
    @abstractmethod
    def validate(self, data: Any) -> Dict[str, Any]:
        """验证数据并返回清洗后的结果"""
        pass
    
    @abstractmethod
    def get_validation_errors(self, data: Any) -> List[Dict[str, Any]]:
        """获取验证错误列表"""
        pass


class CommonValidationRules:
    """
    通用验证规则集合
    包含各种常用的验证方法
    """
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """验证手机号格式（中国）"""
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def is_strong_password(password: str) -> bool:
        """验证强密码（至少8位，包含大小写字母、数字和特殊字符）"""
        if len(password) < 8:
            return False
        
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        return has_upper and has_lower and has_digit and has_special
    
    @staticmethod
    def is_valid_username(username: str) -> bool:
        """验证用户名格式（3-20位，字母数字下划线）"""
        pattern = r'^[a-zA-Z0-9_]{3,20}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def is_valid_slug(slug: str) -> bool:
        """验证URL slug格式"""
        pattern = r'^[a-z0-9-]+$'
        return bool(re.match(pattern, slug))
    
    @staticmethod
    def is_valid_api_key(api_key: str) -> bool:
        """验证API密钥格式"""
        # API密钥通常是32-64位的字母数字组合
        pattern = r'^[a-zA-Z0-9]{32,64}$'
        return bool(re.match(pattern, api_key))
    
    @staticmethod
    def is_valid_uuid(uuid_str: str) -> bool:
        """验证UUID格式"""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_str.lower()))
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """清理文本内容"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 限制长度
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @staticmethod
    def sanitize_html(html: str) -> str:
        """清理HTML内容（简单实现）"""
        if not html:
            return ""
        
        # 移除脚本标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除样式标签
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除危险属性
        html = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
        
        return html


# ================================
# 通用数据模型
# ================================

class PaginationModel(BaseModel):
    """分页参数模型"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    
    @validator('page_size')
    def validate_page_size(cls, v):
        if v > 100:
            raise ValueError('每页数量不能超过100')
        return v


class SortModel(BaseModel):
    """排序参数模型"""
    field: str = Field(..., description="排序字段")
    order: str = Field(default="asc", regex="^(asc|desc)$", description="排序方向")


class FilterModel(BaseModel):
    """筛选参数模型"""
    field: str = Field(..., description="筛选字段")
    operator: str = Field(..., regex="^(eq|ne|gt|lt|gte|lte|like|in|nin)$", description="操作符")
    value: Any = Field(..., description="筛选值")


# ================================
# V1 API专用验证器
# ================================

class V1ApiKeyModel(BaseModel):
    """V1 API密钥验证模型"""
    api_key: str = Field(..., min_length=32, max_length=64, description="API密钥")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not CommonValidationRules.is_valid_api_key(v):
            raise ValueError('API密钥格式无效')
        return v


class V1ChatRequestModel(BaseModel):
    """V1 聊天请求验证模型"""
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")
    assistant_id: str = Field(..., description="助手ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    stream: bool = Field(default=False, description="是否流式响应")
    
    @validator('message')
    def validate_message(cls, v):
        return CommonValidationRules.sanitize_text(v, 4000)


class V1KnowledgeQueryModel(BaseModel):
    """V1 知识库查询验证模型"""
    query: str = Field(..., min_length=1, max_length=500, description="查询文本")
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制")
    
    @validator('query')
    def validate_query(cls, v):
        return CommonValidationRules.sanitize_text(v, 500)


# ================================
# Frontend API专用验证器
# ================================

class FrontendUserRegisterModel(BaseModel):
    """前端用户注册验证模型"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, description="密码")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    
    @validator('username')
    def validate_username(cls, v):
        if not CommonValidationRules.is_valid_username(v):
            raise ValueError('用户名只能包含字母、数字和下划线，长度3-20位')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if not CommonValidationRules.is_valid_email(v):
            raise ValueError('邮箱格式无效')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if not CommonValidationRules.is_strong_password(v):
            raise ValueError('密码必须至少8位，包含大小写字母、数字和特殊字符')
        return v
    
    @validator('nickname')
    def validate_nickname(cls, v):
        if v:
            return CommonValidationRules.sanitize_text(v, 50)
        return v


class FrontendAssistantCreateModel(BaseModel):
    """前端助手创建验证模型"""
    name: str = Field(..., min_length=1, max_length=100, description="助手名称")
    description: str = Field(..., min_length=10, max_length=500, description="助手描述")
    system_prompt: str = Field(..., min_length=10, max_length=2000, description="系统提示词")
    model: str = Field(..., description="使用的模型")
    is_public: bool = Field(default=False, description="是否公开")
    tags: List[str] = Field(default=[], description="标签")
    
    @validator('name')
    def validate_name(cls, v):
        return CommonValidationRules.sanitize_text(v, 100)
    
    @validator('description')
    def validate_description(cls, v):
        return CommonValidationRules.sanitize_text(v, 500)
    
    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        return CommonValidationRules.sanitize_text(v, 2000)
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('标签数量不能超过10个')
        
        cleaned_tags = []
        for tag in v:
            if len(tag) > 20:
                raise ValueError('单个标签长度不能超过20个字符')
            cleaned_tags.append(CommonValidationRules.sanitize_text(tag, 20))
        
        return cleaned_tags


class FrontendKnowledgeBaseCreateModel(BaseModel):
    """前端知识库创建验证模型"""
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: str = Field(..., min_length=10, max_length=500, description="知识库描述")
    is_public: bool = Field(default=False, description="是否公开")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    tags: List[str] = Field(default=[], description="标签")
    settings: Dict[str, Any] = Field(default={}, description="配置")
    
    @validator('name')
    def validate_name(cls, v):
        return CommonValidationRules.sanitize_text(v, 100)
    
    @validator('description')
    def validate_description(cls, v):
        return CommonValidationRules.sanitize_text(v, 500)
    
    @validator('category')
    def validate_category(cls, v):
        if v:
            return CommonValidationRules.sanitize_text(v, 50)
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('标签数量不能超过10个')
        return [CommonValidationRules.sanitize_text(tag, 20) for tag in v]


# ================================
# Admin API专用验证器
# ================================

class AdminUserManageModel(BaseModel):
    """管理员用户管理验证模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=20, description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_admin: Optional[bool] = Field(None, description="是否管理员")
    permissions: Optional[List[str]] = Field(None, description="权限列表")
    roles: Optional[List[str]] = Field(None, description="角色列表")
    
    @validator('username')
    def validate_username(cls, v):
        if v and not CommonValidationRules.is_valid_username(v):
            raise ValueError('用户名格式无效')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v and not CommonValidationRules.is_valid_email(v):
            raise ValueError('邮箱格式无效')
        return v.lower() if v else v


class AdminSystemConfigModel(BaseModel):
    """管理员系统配置验证模型"""
    config_key: str = Field(..., min_length=1, max_length=100, description="配置键")
    config_value: Any = Field(..., description="配置值")
    description: Optional[str] = Field(None, max_length=200, description="配置描述")
    is_sensitive: bool = Field(default=False, description="是否敏感配置")
    
    @validator('config_key')
    def validate_config_key(cls, v):
        # 配置键只允许字母、数字、点和下划线
        pattern = r'^[a-zA-Z0-9._]+$'
        if not re.match(pattern, v):
            raise ValueError('配置键只能包含字母、数字、点和下划线')
        return v


# ================================
# 业务领域验证器
# ================================

class FileUploadModel(BaseModel):
    """文件上传验证模型"""
    filename: str = Field(..., min_length=1, max_length=255, description="文件名")
    content_type: str = Field(..., description="文件类型")
    size: int = Field(..., ge=1, description="文件大小（字节）")
    
    @validator('filename')
    def validate_filename(cls, v):
        # 检查文件名中的危险字符
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f'文件名不能包含字符: {char}')
        
        return v
    
    @validator('size')
    def validate_size(cls, v):
        # 限制文件大小为100MB
        max_size = 100 * 1024 * 1024  # 100MB
        if v > max_size:
            raise ValueError('文件大小不能超过100MB')
        return v


class MessageModel(BaseModel):
    """消息验证模型"""
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    message_type: str = Field(..., regex="^(text|image|audio|video|file)$", description="消息类型")
    metadata: Dict[str, Any] = Field(default={}, description="消息元数据")
    
    @validator('content')
    def validate_content(cls, v):
        return CommonValidationRules.sanitize_text(v, 10000)


# ================================
# 验证器工厂
# ================================

class ValidatorFactory:
    """验证器工厂类"""
    
    _validators = {
        # V1 API验证器
        'v1_api_key': V1ApiKeyModel,
        'v1_chat_request': V1ChatRequestModel,
        'v1_knowledge_query': V1KnowledgeQueryModel,
        
        # Frontend API验证器
        'frontend_user_register': FrontendUserRegisterModel,
        'frontend_assistant_create': FrontendAssistantCreateModel,
        'frontend_knowledge_create': FrontendKnowledgeBaseCreateModel,
        
        # Admin API验证器
        'admin_user_manage': AdminUserManageModel,
        'admin_system_config': AdminSystemConfigModel,
        
        # 通用验证器
        'pagination': PaginationModel,
        'sort': SortModel,
        'filter': FilterModel,
        'file_upload': FileUploadModel,
        'message': MessageModel,
    }
    
    @classmethod
    def get_validator(cls, validator_name: str) -> Type[BaseModel]:
        """获取指定验证器"""
        validator = cls._validators.get(validator_name)
        if not validator:
            raise ValueError(f"未找到验证器: {validator_name}")
        return validator
    
    @classmethod
    def validate_data(cls, validator_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """使用指定验证器验证数据"""
        validator = cls.get_validator(validator_name)
        try:
            validated_data = validator(**data)
            return validated_data.dict()
        except ValidationError as e:
            logger.warning(f"数据验证失败 [{validator_name}]: {e}")
            raise e
    
    @classmethod
    def register_validator(cls, name: str, validator: Type[BaseModel]):
        """注册新的验证器"""
        cls._validators[name] = validator
    
    @classmethod
    def list_validators(cls) -> List[str]:
        """列出所有可用的验证器"""
        return list(cls._validators.keys())


# ================================
# 验证器装饰器
# ================================

def validate_request(validator_name: str):
    """请求数据验证装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 假设第一个参数是请求数据
            if args and isinstance(args[0], dict):
                try:
                    validated_data = ValidatorFactory.validate_data(validator_name, args[0])
                    args = (validated_data,) + args[1:]
                except ValidationError as e:
                    from app.api.shared.exceptions import ValidationError as APIValidationError
                    raise APIValidationError(
                        message="请求数据验证失败",
                        validation_errors=[
                            {
                                "field": ".".join(str(x) for x in error["loc"]),
                                "message": error["msg"],
                                "type": error["type"]
                            }
                            for error in e.errors()
                        ]
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ================================
# 数据清洗工具
# ================================

class DataSanitizer:
    """数据清洗工具类"""
    
    @staticmethod
    def sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗用户输入数据"""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # 清洗字符串类型的值
                sanitized[key] = CommonValidationRules.sanitize_text(value)
            elif isinstance(value, dict):
                # 递归清洗字典
                sanitized[key] = DataSanitizer.sanitize_user_input(value)
            elif isinstance(value, list):
                # 清洗列表
                sanitized[key] = [
                    CommonValidationRules.sanitize_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def remove_sensitive_fields(data: Dict[str, Any], sensitive_fields: List[str] = None) -> Dict[str, Any]:
        """移除敏感字段"""
        if sensitive_fields is None:
            sensitive_fields = ['password', 'token', 'secret', 'api_key', 'private_key']
        
        cleaned = {}
        for key, value in data.items():
            if key.lower() in [field.lower() for field in sensitive_fields]:
                cleaned[key] = "***REDACTED***"
            elif isinstance(value, dict):
                cleaned[key] = DataSanitizer.remove_sensitive_fields(value, sensitive_fields)
            else:
                cleaned[key] = value
        
        return cleaned 