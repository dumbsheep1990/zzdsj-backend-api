"""
Docker集成模块 - LightRAG框架Docker容器管理
"""
import os
import docker
import logging
import time
from typing import Dict, List, Optional, Any, Union

from app.config import settings
from app.utils.common.logger import setup_logger
from app.frameworks.lightrag.api_client import get_lightrag_api_client

logger = setup_logger("lightrag_docker")

class LightRAGDockerService:
    """
    LightRAG Docker服务集成
    管理与Docker中运行的LightRAG服务的交互
    """
    
    def __init__(self):
        """初始化LightRAG Docker服务集成"""
        self.api_client = get_lightrag_api_client()
        self.initialize_settings()
    
    def initialize_settings(self):
        """初始化服务设置"""
        # 在config.py中设置默认值，如果不存在
        if not hasattr(settings, "LIGHTRAG_API_URL"):
            setattr(settings, "LIGHTRAG_API_URL", "http://localhost:9621")
        
        if not hasattr(settings, "LIGHTRAG_ENABLED"):
            setattr(settings, "LIGHTRAG_ENABLED", True)
        
        if not hasattr(settings, "LIGHTRAG_DEFAULT_WORKDIR"):
            setattr(settings, "LIGHTRAG_DEFAULT_WORKDIR", "default")
    
    def is_service_available(self) -> bool:
        """
        检查LightRAG服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            return self.api_client._check_service_available()
        except Exception as e:
            logger.error(f"检查LightRAG服务可用性时出错: {str(e)}")
            return False
    
    def get_or_create_workdir(self, workdir_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取或创建工作目录
        
        Args:
            workdir_id: 工作目录ID，如果为None，则使用默认工作目录
            
        Returns:
            Dict: 包含工作目录信息的字典
        """
        if not workdir_id:
            workdir_id = getattr(settings, "LIGHTRAG_DEFAULT_WORKDIR", "default")
        
        # 先尝试获取工作目录信息
        result = self.api_client.get_workdir_info(workdir_id)
        
        # 如果工作目录不存在，则创建
        if not result.get("success", False) and result.get("status_code") in (404, 400):
            logger.info(f"工作目录 {workdir_id} 不存在，正在创建...")
            create_result = self.api_client.create_workdir(
                workdir_id=workdir_id,
                description=f"自动创建的工作目录: {workdir_id}"
            )
            
            if create_result.get("success", False):
                logger.info(f"工作目录 {workdir_id} 创建成功")
                return create_result
            else:
                logger.error(f"创建工作目录 {workdir_id} 失败: {create_result.get('error', '未知错误')}")
                return create_result
        
        return result
    
    def ensure_workdir_exists(self, workdir_id: str) -> bool:
        """
        确保工作目录存在
        
        Args:
            workdir_id: 工作目录ID
            
        Returns:
            bool: 工作目录是否存在或创建成功
        """
        result = self.get_or_create_workdir(workdir_id)
        return result.get("success", False)
    
    def process_query(self, query: str, workdir_id: Optional[str] = None, 
                     mode: str = "hybrid") -> Dict[str, Any]:
        """
        处理查询并返回结果
        
        Args:
            query: 查询文本
            workdir_id: 工作目录ID（可选）
            mode: 查询模式
            
        Returns:
            Dict: 查询结果
        """
        # 确保工作目录存在
        if workdir_id:
            self.ensure_workdir_exists(workdir_id)
        
        # 执行查询
        return self.api_client.query(query, workdir_id, mode)
    
    def process_document(self, content: Union[str, bytes], 
                        is_file: bool = False,
                        file_path: Optional[str] = None,
                        workdir_id: Optional[str] = None,
                        description: Optional[str] = None) -> Dict[str, Any]:
        """
        处理文档并将其添加到知识库
        
        Args:
            content: 文档内容或文件路径
            is_file: 是否为文件
            file_path: 文件路径（如果is_file为True）
            workdir_id: 工作目录ID（可选）
            description: 文档描述（可选）
            
        Returns:
            Dict: 处理结果
        """
        # 确保工作目录存在
        if workdir_id:
            self.ensure_workdir_exists(workdir_id)
        
        # 处理文档
        if is_file:
            if not file_path:
                return {
                    "success": False,
                    "error": "处理文件时必须提供文件路径",
                    "status_code": 400
                }
            return self.api_client.upload_file(file_path, workdir_id, description)
        else:
            if not isinstance(content, str):
                try:
                    content = content.decode("utf-8")
                except:
                    return {
                        "success": False,
                        "error": "无法解码文本内容",
                        "status_code": 400
                    }
            return self.api_client.upload_text(content, workdir_id, description)
    
    def list_available_workdirs(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的工作目录
        
        Returns:
            List: 工作目录列表
        """
        result = self.api_client.list_workdirs()
        if result.get("success", False):
            return result.get("data", [])
        return []

# 单例模式，确保全局只有一个服务实例
_lightrag_docker_service = None

def get_lightrag_docker_service() -> LightRAGDockerService:
    """
    获取LightRAG Docker服务单例
    
    Returns:
        LightRAGDockerService实例
    """
    global _lightrag_docker_service
    if _lightrag_docker_service is None:
        _lightrag_docker_service = LightRAGDockerService()
    return _lightrag_docker_service
