"""
应用配置管理
"""
from pydantic import BaseSettings, Field
from typing import List, Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    APP_NAME: str = "AI Assistant Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(False, env="DEBUG")

    # 数据库配置
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(5, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(10, env="DATABASE_MAX_OVERFLOW")

    # API配置
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = Field(["*"], env="CORS_ORIGINS")

    # 认证配置
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # AI模型配置
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    DEFAULT_AI_MODEL: str = Field("gpt-3.5-turbo", env="DEFAULT_AI_MODEL")

    # 助手配置
    MAX_ASSISTANTS_PER_USER: int = Field(50, env="MAX_ASSISTANTS_PER_USER")
    MAX_CONVERSATIONS_PER_USER: int = Field(1000, env="MAX_CONVERSATIONS_PER_USER")
    MAX_MESSAGE_LENGTH: int = Field(10000, env="MAX_MESSAGE_LENGTH")

    # 知识库配置
    VECTOR_DB_URL: Optional[str] = Field(None, env="VECTOR_DB_URL")
    EMBEDDING_MODEL: str = Field("text-embedding-ada-002", env="EMBEDDING_MODEL")
    CHUNK_SIZE: int = Field(1000, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(200, env="CHUNK_OVERLAP")

    # Redis配置（用于缓存和队列）
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    CACHE_TTL: int = Field(3600, env="CACHE_TTL")

    # 日志配置
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = Field(None, env="LOG_FILE")

    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(1000, env="RATE_LIMIT_PER_HOUR")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()