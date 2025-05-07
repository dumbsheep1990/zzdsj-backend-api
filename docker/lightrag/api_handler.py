"""
LightRAG API处理程序 - 提供前端动态工作目录管理功能
"""
import os
import sys
import json
import requests
from typing import Dict, List, Optional, Union, Any

class LightRAGApiHandler:
    """LightRAG API处理程序，用于管理工作目录和转发API请求"""
    
    def __init__(self, api_base_url: str = "http://localhost:9621"):
        """
        初始化LightRAG API处理程序
        
        Args:
            api_base_url: LightRAG API的基础URL
        """
        self.api_base_url = api_base_url.rstrip('/')
        
    def create_workdir(self, workdir_name: str) -> Dict[str, Any]:
        """
        创建新的工作目录
        
        Args:
            workdir_name: 工作目录名称
            
        Returns:
            包含操作结果的字典
        """
        endpoint = f"{self.api_base_url}/graphs"
        data = {
            "graph_id": workdir_name,
            "description": f"工作目录: {workdir_name}"
        }
        
        try:
            response = requests.post(endpoint, json=data)
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "success": True,
                    "message": f"成功创建工作目录: {workdir_name}",
                    "data": response.json() if response.text else {"graph_id": workdir_name}
                }
            else:
                return {
                    "success": False,
                    "message": f"创建工作目录失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"创建工作目录时发生错误: {str(e)}"
            }
    
    def list_workdirs(self) -> Dict[str, Any]:
        """
        列出所有可用的工作目录
        
        Returns:
            包含工作目录列表的字典
        """
        endpoint = f"{self.api_base_url}/graphs"
        
        try:
            response = requests.get(endpoint)
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "message": f"获取工作目录列表失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取工作目录列表时发生错误: {str(e)}"
            }
    
    def delete_workdir(self, workdir_name: str) -> Dict[str, Any]:
        """
        删除工作目录
        
        Args:
            workdir_name: 工作目录名称
            
        Returns:
            包含操作结果的字典
        """
        endpoint = f"{self.api_base_url}/graphs/{workdir_name}"
        
        try:
            response = requests.delete(endpoint)
            if response.status_code == 200 or response.status_code == 204:
                return {
                    "success": True,
                    "message": f"成功删除工作目录: {workdir_name}"
                }
            else:
                return {
                    "success": False,
                    "message": f"删除工作目录失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"删除工作目录时发生错误: {str(e)}"
            }
    
    def get_workdir_stats(self, workdir_name: str) -> Dict[str, Any]:
        """
        获取工作目录统计信息
        
        Args:
            workdir_name: 工作目录名称
            
        Returns:
            包含工作目录统计信息的字典
        """
        endpoint = f"{self.api_base_url}/graphs/{workdir_name}/stats"
        
        try:
            response = requests.get(endpoint)
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "message": f"获取工作目录统计信息失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取工作目录统计信息时发生错误: {str(e)}"
            }
    
    def query_with_workdir(self, query: str, workdir: str, mode: str = "hybrid") -> Dict[str, Any]:
        """
        在指定工作目录中执行查询
        
        Args:
            query: 查询文本
            workdir: 工作目录名称
            mode: 查询模式，可选值: hybrid, vector, graph
            
        Returns:
            包含查询结果的字典
        """
        endpoint = f"{self.api_base_url}/query"
        data = {
            "query": query,
            "mode": mode,
            "graph_id": workdir
        }
        
        try:
            response = requests.post(endpoint, json=data)
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "message": f"查询失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"执行查询时发生错误: {str(e)}"
            }
    
    def upload_text_to_workdir(self, text: str, workdir: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        向指定工作目录上传文本
        
        Args:
            text: 文本内容
            workdir: 工作目录名称
            description: 文档描述（可选）
            
        Returns:
            包含操作结果的字典
        """
        endpoint = f"{self.api_base_url}/documents/text"
        data = {
            "text": text,
            "graph_id": workdir
        }
        
        if description:
            data["description"] = description
        
        try:
            response = requests.post(endpoint, json=data)
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "success": True,
                    "message": "成功上传文本到工作目录",
                    "data": response.json() if response.text else {}
                }
            else:
                return {
                    "success": False,
                    "message": f"上传文本失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"上传文本时发生错误: {str(e)}"
            }
    
    def upload_file_to_workdir(self, file_path: str, workdir: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        向指定工作目录上传文件
        
        Args:
            file_path: 文件路径
            workdir: 工作目录名称
            description: 文档描述（可选）
            
        Returns:
            包含操作结果的字典
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        endpoint = f"{self.api_base_url}/documents/file"
        
        try:
            files = {'file': open(file_path, 'rb')}
            data = {'graph_id': workdir}
            
            if description:
                data['description'] = description
            
            response = requests.post(endpoint, files=files, data=data)
            files['file'].close()
            
            if response.status_code == 200 or response.status_code == 201:
                return {
                    "success": True,
                    "message": f"成功上传文件到工作目录: {os.path.basename(file_path)}",
                    "data": response.json() if response.text else {}
                }
            else:
                return {
                    "success": False,
                    "message": f"上传文件失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"上传文件时发生错误: {str(e)}"
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        检查LightRAG API服务健康状态
        
        Returns:
            包含健康状态的字典
        """
        endpoint = f"{self.api_base_url}/health"
        
        try:
            response = requests.get(endpoint)
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "LightRAG API服务运行正常",
                    "data": response.json() if response.text else {}
                }
            else:
                return {
                    "success": False,
                    "message": f"服务健康检查失败: {response.text}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"执行健康检查时发生错误: {str(e)}"
            }

# 测试用例
if __name__ == "__main__":
    api_handler = LightRAGApiHandler()
    
    # 健康检查
    health_result = api_handler.health_check()
    print(f"健康检查结果: {json.dumps(health_result, ensure_ascii=False, indent=2)}")
    
    if health_result["success"]:
        # 创建工作目录
        create_result = api_handler.create_workdir("test_workdir")
        print(f"创建工作目录结果: {json.dumps(create_result, ensure_ascii=False, indent=2)}")
        
        # 列出所有工作目录
        list_result = api_handler.list_workdirs()
        print(f"工作目录列表: {json.dumps(list_result, ensure_ascii=False, indent=2)}")
        
        # 上传测试文本
        text_result = api_handler.upload_text_to_workdir(
            "这是一个测试文档，用于验证LightRAG API的功能。",
            "test_workdir",
            "测试文档"
        )
        print(f"上传文本结果: {json.dumps(text_result, ensure_ascii=False, indent=2)}")
        
        # 执行查询
        query_result = api_handler.query_with_workdir(
            "什么是LightRAG?",
            "test_workdir"
        )
        print(f"查询结果: {json.dumps(query_result, ensure_ascii=False, indent=2)}")
