"""
OWL智能体工具配置模块
提供从环境变量加载工具配置的功能
"""
import os
from pydantic import BaseSettings, Field
from typing import List, Dict, Optional, Set


# 基础工具配置
class OwlToolsSettings(BaseSettings):
    """OWL工具系统基础配置"""
    enabled: bool = Field(True, env="OWL_TOOLS_ENABLED")
    timeout_seconds: int = Field(30, env="OWL_TOOLS_TIMEOUT_SECONDS")
    max_concurrent: int = Field(5, env="OWL_TOOLS_MAX_CONCURRENT")

    class Config:
        env_file = ".env"


# 搜索工具配置
class SearchToolSettings(BaseSettings):
    """搜索工具配置"""
    enabled: bool = Field(True, env="OWL_TOOL_SEARCH_ENABLED")
    max_results: int = Field(5, env="OWL_TOOL_SEARCH_MAX_RESULTS")
    api_timeout: int = Field(10, env="OWL_TOOL_SEARCH_API_TIMEOUT")
    enable_filter: bool = Field(True, env="OWL_TOOL_SEARCH_ENABLE_FILTER")

    class Config:
        env_file = ".env"


# 文档工具配置
class DocumentToolSettings(BaseSettings):
    """文档工具配置"""
    enabled: bool = Field(True, env="OWL_TOOL_DOCUMENT_ENABLED")
    max_file_size_mb: int = Field(50, env="OWL_TOOL_DOCUMENT_MAX_FILE_SIZE_MB")
    
    @property
    def supported_formats(self) -> List[str]:
        """支持的文件格式列表"""
        formats_str = os.getenv("OWL_TOOL_DOCUMENT_SUPPORTED_FORMATS", "pdf,docx,txt")
        return formats_str.split(",")

    class Config:
        env_file = ".env"


# 知识库工具配置
class KnowledgeToolSettings(BaseSettings):
    """知识库工具配置"""
    enabled: bool = Field(True, env="OWL_TOOL_KNOWLEDGE_ENABLED")
    max_chunks: int = Field(10, env="OWL_TOOL_KNOWLEDGE_MAX_CHUNKS")
    similarity_threshold: float = Field(0.75, env="OWL_TOOL_KNOWLEDGE_SIMILARITY_THRESHOLD")

    class Config:
        env_file = ".env"


# API调用工具配置
class ApiToolSettings(BaseSettings):
    """API调用工具配置"""
    enabled: bool = Field(True, env="OWL_TOOL_API_ENABLED")
    max_requests_per_min: int = Field(30, env="OWL_TOOL_API_MAX_REQUESTS_PER_MIN")
    default_timeout: int = Field(15, env="OWL_TOOL_API_DEFAULT_TIMEOUT")
    retry_attempts: int = Field(3, env="OWL_TOOL_API_RETRY_ATTEMPTS")

    class Config:
        env_file = ".env"


# 代码执行工具配置
class CodeExecToolSettings(BaseSettings):
    """代码执行工具配置"""
    enabled: bool = Field(False, env="OWL_TOOL_CODE_EXEC_ENABLED")
    timeout: int = Field(5, env="OWL_TOOL_CODE_EXEC_TIMEOUT")
    max_memory_mb: int = Field(100, env="OWL_TOOL_CODE_EXEC_MAX_MEMORY_MB")
    
    @property
    def allowed_languages(self) -> List[str]:
        """允许执行的语言列表"""
        langs_str = os.getenv("OWL_TOOL_CODE_EXEC_ALLOWED_LANGUAGES", "python,javascript")
        return langs_str.split(",")

    class Config:
        env_file = ".env"


# 初始化配置实例
owl_tools_settings = OwlToolsSettings()
search_tool_settings = SearchToolSettings()
document_tool_settings = DocumentToolSettings()
knowledge_tool_settings = KnowledgeToolSettings()
api_tool_settings = ApiToolSettings()
code_exec_tool_settings = CodeExecToolSettings()


# 配置访问函数
def get_tool_settings(tool_name: str) -> Optional[BaseSettings]:
    """根据工具名获取对应的配置实例
    
    Args:
        tool_name (str): 工具名称
        
    Returns:
        Optional[BaseSettings]: 工具配置实例，若不存在则返回None
    """
    settings_map = {
        "search": search_tool_settings,
        "document": document_tool_settings,
        "knowledge": knowledge_tool_settings,
        "api": api_tool_settings,
        "code_exec": code_exec_tool_settings,
    }
    return settings_map.get(tool_name)


def is_tool_enabled(tool_name: str) -> bool:
    """检查工具是否启用
    
    Args:
        tool_name (str): 工具名称
        
    Returns:
        bool: 工具是否启用
    """
    # 首先检查全局启用状态
    if not owl_tools_settings.enabled:
        return False
        
    # 然后检查特定工具启用状态
    settings = get_tool_settings(tool_name)
    if settings and hasattr(settings, "enabled"):
        return settings.enabled
        
    return False
