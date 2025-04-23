"""
数据访问MCP客户端模块
定义数据访问类型MCP服务的接口（如数据库、存储、版本控制等）
"""

from abc import abstractmethod
from typing import Dict, Any, Optional, List, Union, BinaryIO
from .base import BaseMCPClient, ClientCapability

class DataMCPClient(BaseMCPClient):
    """数据访问类型MCP客户端"""
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        return [ClientCapability.DATABASE, ClientCapability.STORAGE, ClientCapability.FILE_OPERATIONS, ClientCapability.TOOLS]
    
    @abstractmethod
    async def query(
        self,
        query_string: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        执行查询
        
        参数:
            query_string: 查询语句
            parameters: 查询参数
            **kwargs: 其他参数
            
        返回:
            查询结果
        """
        pass
    
    @abstractmethod
    async def get_file(
        self,
        path: str,
        **kwargs
    ) -> Union[bytes, Dict[str, Any]]:
        """
        获取文件内容
        
        参数:
            path: 文件路径
            **kwargs: 其他参数
            
        返回:
            文件内容
        """
        pass
    
    @abstractmethod
    async def list_files(
        self,
        path: str,
        recursive: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        列出文件
        
        参数:
            path: 目录路径
            recursive: 是否递归列出子目录
            **kwargs: 其他参数
            
        返回:
            文件列表
        """
        pass
    
    @abstractmethod
    async def put_file(
        self,
        path: str,
        content: Union[str, bytes, BinaryIO],
        **kwargs
    ) -> Dict[str, Any]:
        """
        上传文件
        
        参数:
            path: 文件路径
            content: 文件内容
            **kwargs: 其他参数
            
        返回:
            上传结果
        """
        pass
    
    @abstractmethod
    async def delete_file(
        self,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        删除文件
        
        参数:
            path: 文件路径
            **kwargs: 其他参数
            
        返回:
            删除结果
        """
        pass
