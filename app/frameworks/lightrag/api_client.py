"""
LightRAG API 客户端 - 用于连接部署在Docker中的LightRAG服务
该模块提供了与LightRAG API服务交互的接口，支持工作目录的动态创建和管理
"""
import os
import json
import requests
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urljoin

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("lightrag_api_client")

class LightRAGApiClient:
    """
    LightRAG API 客户端
    提供与LightRAG服务的交互接口，封装了工作目录管理和查询功能
    """
    
    def __init__(self):
        """初始化LightRAG API客户端"""
        self.base_url = getattr(settings, "LIGHTRAG_API_URL", "http://localhost:9621")
        self.base_url = self.base_url.rstrip("/")
        self._check_service_available()
    
    def _check_service_available(self) -> bool:
        """
        检查LightRAG服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=3)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LightRAG服务不可用: {str(e)}")
            return False
    
    def _make_request(self, method: str, endpoint: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None,
                     files: Optional[Dict] = None,
                     timeout: int = 30) -> Dict[str, Any]:
        """
        发送请求到LightRAG API
        
        Args:
            method: 请求方法 (GET, POST, DELETE等)
            endpoint: API端点
            params: URL参数
            data: 请求体数据
            files: 文件数据
            timeout: 请求超时时间(秒)
            
        Returns:
            包含响应数据的字典
        """
        url = urljoin(self.base_url, endpoint.lstrip("/"))
        
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=data,
                files=files,
                timeout=timeout
            )
            
            if response.status_code < 400:
                # 请求成功
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": response.json() if response.text and response.text.strip() else {}
                }
            else:
                # 请求失败
                error_detail = response.text
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict):
                        error_detail = error_json.get("detail", error_json.get("message", response.text))
                except:
                    pass
                
                logger.error(f"LightRAG API请求失败: {url}, 状态码: {response.status_code}, 错误: {error_detail}")
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": error_detail
                }
                
        except requests.RequestException as e:
            logger.error(f"请求LightRAG API时发生错误: {endpoint}, {str(e)}")
            return {
                "success": False,
                "error": f"请求错误: {str(e)}",
                "status_code": 500
            }
    
    def create_workdir(self, workdir_id: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新的工作目录
        
        Args:
            workdir_id: 工作目录ID
            description: 工作目录描述
            
        Returns:
            包含操作结果的字典
        """
        data = {
            "graph_id": workdir_id,
        }
        
        if description:
            data["description"] = description
        
        return self._make_request("POST", "/graphs", data=data)
    
    def list_workdirs(self) -> Dict[str, Any]:
        """
        获取所有工作目录列表
        
        Returns:
            包含工作目录列表的字典
        """
        return self._make_request("GET", "/graphs")
    
    def get_workdir_info(self, workdir_id: str) -> Dict[str, Any]:
        """
        获取工作目录信息
        
        Args:
            workdir_id: 工作目录ID
            
        Returns:
            包含工作目录信息的字典
        """
        return self._make_request("GET", f"/graphs/{workdir_id}")
    
    def delete_workdir(self, workdir_id: str) -> Dict[str, Any]:
        """
        删除工作目录
        
        Args:
            workdir_id: 工作目录ID
            
        Returns:
            包含操作结果的字典
        """
        return self._make_request("DELETE", f"/graphs/{workdir_id}")
    
    def get_workdir_stats(self, workdir_id: str) -> Dict[str, Any]:
        """
        获取工作目录统计信息
        
        Args:
            workdir_id: 工作目录ID
            
        Returns:
            包含统计信息的字典
        """
        return self._make_request("GET", f"/graphs/{workdir_id}/stats")
    
    def upload_text(self, text: str, workdir_id: Optional[str] = None, 
                  description: Optional[str] = None) -> Dict[str, Any]:
        """
        上传文本到指定工作目录
        
        Args:
            text: 文本内容
            workdir_id: 工作目录ID（可选）
            description: 文档描述（可选）
            
        Returns:
            包含操作结果的字典
        """
        data = {"text": text}
        
        if workdir_id:
            data["graph_id"] = workdir_id
        
        if description:
            data["description"] = description
        
        return self._make_request("POST", "/documents/text", data=data)
    
    def upload_file(self, file_path: str, workdir_id: Optional[str] = None,
                  description: Optional[str] = None) -> Dict[str, Any]:
        """
        上传文件到指定工作目录
        
        Args:
            file_path: 文件路径
            workdir_id: 工作目录ID（可选）
            description: 文档描述（可选）
            
        Returns:
            包含操作结果的字典
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}",
                "status_code": 400
            }
        
        try:
            files = {"file": open(file_path, "rb")}
            data = {}
            
            if workdir_id:
                data["graph_id"] = workdir_id
            
            if description:
                data["description"] = description
            
            result = self._make_request(
                "POST", 
                "/documents/file", 
                data=data,
                files=files
            )
            
            files["file"].close()
            return result
            
        except Exception as e:
            logger.error(f"上传文件时发生错误: {str(e)}")
            return {
                "success": False,
                "error": f"上传文件错误: {str(e)}",
                "status_code": 500
            }
    
    def query(self, query_text: str, workdir_id: Optional[str] = None, 
             mode: str = "hybrid") -> Dict[str, Any]:
        """
        查询知识图谱
        
        Args:
            query_text: 查询文本
            workdir_id: 工作目录ID（可选）
            mode: 查询模式 (hybrid, vector, graph)
            
        Returns:
            包含查询结果的字典
        """
        data = {
            "query": query_text,
            "mode": mode
        }
        
        if workdir_id:
            data["graph_id"] = workdir_id
        
        return self._make_request("POST", "/query", data=data)
    
    def query_stream(self, query_text: str, workdir_id: Optional[str] = None,
                   mode: str = "hybrid") -> requests.Response:
        """
        流式查询知识图谱（返回流式响应）
        
        Args:
            query_text: 查询文本
            workdir_id: 工作目录ID（可选）
            mode: 查询模式 (hybrid, vector, graph)
            
        Returns:
            流式响应对象
        """
        url = urljoin(self.base_url, "/query/stream")
        data = {
            "query": query_text,
            "mode": mode
        }
        
        if workdir_id:
            data["graph_id"] = workdir_id
        
        try:
            return requests.post(url, json=data, stream=True)
        except requests.RequestException as e:
            logger.error(f"流式查询请求失败: {str(e)}")
            raise

# 单例模式，确保全局只有一个客户端实例
_lightrag_api_client = None

def get_lightrag_api_client() -> LightRAGApiClient:
    """
    获取LightRAG API客户端单例
    
    Returns:
        LightRAGApiClient实例
    """
    global _lightrag_api_client
    if _lightrag_api_client is None:
        _lightrag_api_client = LightRAGApiClient()
    return _lightrag_api_client
