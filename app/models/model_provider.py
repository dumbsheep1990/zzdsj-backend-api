"""
模型提供商数据模型
定义与模型提供商和模型配置相关的数据库模型
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.models.database import Base

class ProviderType(str, enum.Enum):
    """模型提供商类型"""
    OPENAI = "openai"
    ZHIPU = "zhipu"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    VLLM = "vllm"
    DASHSCOPE = "dashscope"  # 通义千问
    ANTHROPIC = "anthropic"
    TOGETHER = "together"  # TogetherAI
    QWEN = "qwen"      # 阿里千问API
    BAIDU = "baidu"    # 百度文心一言
    MOONSHOT = "moonshot"  # 月之暗面
    GLM = "glm"        # 智谱GLM
    MINIMAX = "minimax"    # MiniMax
    BAICHUAN = "baichuan"  # 百川
    CUSTOM = "custom"


class ModelProvider(Base):
    """模型提供商"""
    __tablename__ = "model_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)
    api_key = Column(String(255))
    api_base = Column(String(255))
    api_version = Column(String(50))
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    config = Column(JSON)  # 存储额外配置如代理、超时等
    
    # 与此提供商关联的模型
    models = relationship("ModelInfo", back_populates="provider", cascade="all, delete-orphan")


class ModelInfo(Base):
    """模型信息"""
    __tablename__ = "model_info"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("model_providers.id"))
    model_id = Column(String(100), nullable=False)  # 模型ID/名称
    display_name = Column(String(100))
    capabilities = Column(JSON)  # ['completion', 'chat', 'embedding', 'vision'] 等
    is_default = Column(Boolean, default=False)  # 是否是该提供商的默认模型
    config = Column(JSON)  # 存储模型特定配置
    
    # 关系
    provider = relationship("ModelProvider", back_populates="models")
