"""
Agno工具模块：实现可被Agno代理使用的工具，
用于执行操作和与外部系统集成

基于Agno官方文档语法实现的工具系统
"""

from typing import Dict, List, Any, Optional, Callable, Union
import json
import os
from datetime import datetime
from pydantic import BaseModel, Field


class ZZDSJKnowledgeTools:
    """ZZDSJ知识库工具包 - 基于Agno工具模式"""
    
    def __init__(self, kb_id: Optional[str] = None):
        """
        初始化ZZDSJ知识库工具包
        
        参数:
            kb_id: 默认知识库ID
        """
        self.kb_id = kb_id
        
    def search_documents(self, query: str, kb_id: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
        """
        在知识库中搜索文档
        
        参数:
            query: 搜索查询
            kb_id: 知识库ID（可选，使用默认值）
            top_k: 返回结果数量
            
        返回:
            搜索结果
        """
        try:
            from app.frameworks.agno.knowledge_base import KnowledgeBaseProcessor
            
            # 使用提供的kb_id或默认值
            target_kb_id = kb_id or self.kb_id
            if not target_kb_id:
                return {"error": "未提供知识库ID", "results": [], "count": 0}
            
            # 创建KB处理器实例
            kb_processor = KnowledgeBaseProcessor(kb_id=target_kb_id)
            
            # 执行搜索
            results = kb_processor.search(query=query, top_k=top_k)
            
            return {
                "results": results,
                "count": len(results),
                "kb_id": target_kb_id,
                "query": query
            }
            
        except Exception as e:
            return {"error": f"搜索失败: {str(e)}", "results": [], "count": 0}

    def summarize_document(self, document_id: str, max_length: int = 200) -> Dict[str, Any]:
        """
        生成文档摘要
        
        参数:
            document_id: 文档ID
            max_length: 摘要最大长度
            
        返回:
            文档摘要
        """
        try:
            from app.frameworks.agno.document_processor import DocumentProcessor
            
            # 创建文档处理器
            doc_processor = DocumentProcessor()
            
            # 生成摘要
            summary_result = doc_processor.summarize_document(
                document_id=document_id,
                max_length=max_length
            )
            
            return {
                "summary": summary_result.get("summary", ""),
                "document_id": document_id,
                "length": len(summary_result.get("summary", "")),
                "metadata": summary_result.get("metadata", {})
            }
            
        except Exception as e:
            return {"error": f"摘要生成失败: {str(e)}", "summary": "", "document_id": document_id}

    def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        提取文件元数据
        
        参数:
            file_path: 文件路径
            
        返回:
            文件元数据
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            # 获取基本文件信息
            file_stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # 构建元数据
            metadata = {
                "file_name": file_name,
                "file_path": file_path,
                "file_extension": file_ext,
                "file_size": file_stat.st_size,
                "file_size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "accessed_at": datetime.fromtimestamp(file_stat.st_atime).isoformat(),
            }
            
            # 基于文件类型的内容类型映射
            content_type_mapping = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.json': 'application/json',
                '.csv': 'text/csv'
            }
            
            metadata["content_type"] = content_type_mapping.get(file_ext, 'application/octet-stream')
            
            # 判断是否为文本文件
            text_extensions = ['.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.css']
            metadata["is_text_file"] = file_ext in text_extensions
            
            return metadata
            
        except Exception as e:
            return {"error": f"元数据提取失败: {str(e)}"}


class ZZDSJFileManagementTools:
    """ZZDSJ文件管理工具包"""
    
    def __init__(self, upload_base_path: str = "uploads/"):
        """
        初始化文件管理工具包
        
        参数:
            upload_base_path: 上传文件基础路径
        """
        self.upload_base_path = upload_base_path
    
    def list_files(self, directory: str = "", file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        列出目录中的文件
        
        参数:
            directory: 目录路径（相对于base_path）
            file_type: 文件类型过滤（如 '.pdf', '.docx'）
            
        返回:
            文件列表
        """
        try:
            full_path = os.path.join(self.upload_base_path, directory)
            
            if not os.path.exists(full_path):
                return {"error": f"目录不存在: {full_path}", "files": []}
            
            files = []
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                
                if os.path.isfile(item_path):
                    file_ext = os.path.splitext(item)[1].lower()
                    
                    # 文件类型过滤
                    if file_type and file_ext != file_type.lower():
                        continue
                    
                    file_stat = os.stat(item_path)
                    files.append({
                        "name": item,
                        "path": os.path.join(directory, item),
                        "extension": file_ext,
                        "size": file_stat.st_size,
                        "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    })
            
            return {
                "files": sorted(files, key=lambda x: x["modified_at"], reverse=True),
                "count": len(files),
                "directory": directory
            }
            
        except Exception as e:
            return {"error": f"文件列表获取失败: {str(e)}", "files": []}

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取特定文件的详细信息
        
        参数:
            file_path: 文件路径
            
        返回:
            文件详细信息
        """
        try:
            full_path = os.path.join(self.upload_base_path, file_path)
            
            if not os.path.exists(full_path):
                return {"error": f"文件不存在: {file_path}"}
            
            file_stat = os.stat(full_path)
            file_name = os.path.basename(full_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            file_info = {
                "name": file_name,
                "path": file_path,
                "full_path": full_path,
                "extension": file_ext,
                "size": file_stat.st_size,
                "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "is_readable": os.access(full_path, os.R_OK),
                "is_writable": os.access(full_path, os.W_OK)
            }
            
            return file_info
            
        except Exception as e:
            return {"error": f"文件信息获取失败: {str(e)}"}


class ZZDSJSystemTools:
    """ZZDSJ系统工具包"""
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态信息
        
        返回:
            系统状态
        """
        try:
            import psutil
            
            # 获取系统资源使用情况
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = {
                "cpu_usage": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return status
            
        except ImportError:
            return {"error": "psutil未安装，无法获取系统状态"}
        except Exception as e:
            return {"error": f"系统状态获取失败: {str(e)}"}

    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """
        检查特定服务的健康状态
        
        参数:
            service_name: 服务名称
            
        返回:
            服务健康状态
        """
        try:
            # 这里可以扩展为实际的服务健康检查逻辑
            # 例如检查数据库连接、Redis连接等
            
            health_checks = {
                "database": self._check_database_health,
                "redis": self._check_redis_health,
                "vector_db": self._check_vector_db_health,
                "knowledge_base": self._check_knowledge_base_health
            }
            
            if service_name in health_checks:
                return health_checks[service_name]()
            else:
                return {"error": f"未知服务: {service_name}"}
                
        except Exception as e:
            return {"error": f"服务健康检查失败: {str(e)}"}
    
    def _check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        # 占位符实现
        return {"status": "healthy", "service": "database", "response_time_ms": 50}
    
    def _check_redis_health(self) -> Dict[str, Any]:
        """检查Redis健康状态"""
        # 占位符实现
        return {"status": "healthy", "service": "redis", "response_time_ms": 10}
    
    def _check_vector_db_health(self) -> Dict[str, Any]:
        """检查向量数据库健康状态"""
        # 占位符实现
        return {"status": "healthy", "service": "vector_db", "response_time_ms": 80}
    
    def _check_knowledge_base_health(self) -> Dict[str, Any]:
        """检查知识库健康状态"""
        # 占位符实现
        return {"status": "healthy", "service": "knowledge_base", "response_time_ms": 120}


# 工具注册函数 - 符合Agno代理使用模式
def get_zzdsj_knowledge_tools(kb_id: Optional[str] = None) -> ZZDSJKnowledgeTools:
    """
    获取ZZDSJ知识库工具包
    
    参数:
        kb_id: 默认知识库ID
        
    返回:
        知识库工具包实例
    """
    return ZZDSJKnowledgeTools(kb_id=kb_id)


def get_zzdsj_file_tools(upload_base_path: str = "uploads/") -> ZZDSJFileManagementTools:
    """
    获取ZZDSJ文件管理工具包
    
    参数:
        upload_base_path: 上传文件基础路径
        
    返回:
        文件管理工具包实例
    """
    return ZZDSJFileManagementTools(upload_base_path=upload_base_path)


def get_zzdsj_system_tools() -> ZZDSJSystemTools:
    """
    获取ZZDSJ系统工具包
    
    返回:
        系统工具包实例
    """
    return ZZDSJSystemTools()


# 示例：创建自定义工具函数以便于Agno代理使用
def create_zzdsj_agent_tools(kb_id: Optional[str] = None) -> Dict[str, Any]:
    """
    为Agno代理创建ZZDSJ工具集合
    
    参数:
        kb_id: 默认知识库ID
        
    返回:
        工具字典，可直接用于Agno Agent的tools参数
    """
    knowledge_tools = get_zzdsj_knowledge_tools(kb_id)
    file_tools = get_zzdsj_file_tools()
    system_tools = get_zzdsj_system_tools()
    
    return {
        "knowledge": knowledge_tools,
        "files": file_tools,
        "system": system_tools
    }
