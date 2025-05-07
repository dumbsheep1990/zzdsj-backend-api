"""LightRAG客户端模块
提供对外的统一接口，包装内部实现详情
支持本地模式和Docker服务模式的双重运行方式
"""

from typing import List, Dict, Any, Optional, Union, Tuple, Callable
import logging
from pathlib import Path
import json
import os

# 检查是否有LightRAG本地库
try:
    import lightrag
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False

# 内部组件
from app.config import settings
from app.frameworks.lightrag.config import lightrag_config

# 本地模式组件
from app.frameworks.lightrag.graph import get_graph_manager
from app.frameworks.lightrag.document_processor import get_document_processor
from app.frameworks.lightrag.query_engine import create_lightrag_query_engine

# Docker服务模式组件
try:
    from app.frameworks.lightrag.docker_integration import get_lightrag_docker_service
    DOCKER_INTEGRATION_AVAILABLE = True
except ImportError:
    DOCKER_INTEGRATION_AVAILABLE = False

logger = logging.getLogger(__name__)


class LightRAGClient:
    """统一的LightRAG客户端接口
    支持本地模式和Docker服务模式
    """
    
    def __init__(self):
        """初始LightRAG客户端"""
        # 首先检查是否启用
        self.enabled = getattr(settings, "LIGHTRAG_ENABLED", False)
        if not self.enabled:
            logger.info("LightRAG功能已禁用")
            self.available = False
            return
            
        # 检查运行模式
        self.mode = getattr(settings, "LIGHTRAG_MODE", "auto")
        
        # 自动选择运行模式
        if self.mode == "auto":
            if DOCKER_INTEGRATION_AVAILABLE:
                # 先尝试Docker模式
                docker_service = get_lightrag_docker_service()
                if docker_service.is_service_available():
                    self.mode = "docker"
                    logger.info("LightRAG自动选择Docker模式")
                elif LIGHTRAG_AVAILABLE:
                    self.mode = "local"
                    logger.info("LightRAG Docker服务不可用，自动切换为本地模式")
                else:
                    logger.warning("LightRAG不可用: Docker服务不可用且本地模式依赖未安装")
                    self.available = False
                    return
            elif LIGHTRAG_AVAILABLE:
                self.mode = "local"
                logger.info("LightRAG使用本地模式")
            else:
                logger.warning("LightRAG不可用: 没有可用的实现方式")
                self.available = False
                return
        
        # 根据配置前置检查运行模式
        if self.mode == "docker":
            # Docker模式
            if not DOCKER_INTEGRATION_AVAILABLE:
                logger.error("LightRAG Docker集成模块不可用")
                self.available = False
                return
                
            # 初始Docker服务
            self.docker_service = get_lightrag_docker_service()
            if not self.docker_service.is_service_available():
                logger.error("LightRAG Docker服务不可用")
                self.available = False
                return
                
            self.available = True
            logger.info("LightRAG Docker模式初始化完成")
            
        elif self.mode == "local":
            # 本地模式
            if not LIGHTRAG_AVAILABLE:
                logger.error("LightRAG依赖未安装，本地模式不可用")
                self.available = False
                return
                
            # 初始化本地组件
            self.graph_manager = get_graph_manager()
            self.document_processor = get_document_processor()
            self.available = True
            logger.info("LightRAG本地模式初始化完成")
            
        else:
            # 无效模式
            logger.error(f"LightRAG无效的运行模式: {self.mode}")
            self.available = False
    
    def is_available(self) -> bool:
        """检查LightRAG是否可用
        
        返回:
            LightRAG是否可用
        """
        return self.available
    
    def list_graphs(self) -> List[str]:
        """列出所有知识图谱
        
        返回:
            图谱ID列表
        """
        if not self.available:
            return []
            
        if self.mode == "docker":
            result = self.docker_service.list_available_workdirs()
            return [item.get("graph_id", "") for item in result if "graph_id" in item]
        else:
            return self.graph_manager.list_graphs()
    
    def create_graph(self, graph_id: str, description: Optional[str] = None) -> bool:
        """创建新的知识图谱
        
        参数:
            graph_id: 图谱ID
            description: 图谱描述(仅Docker模式有效)
            
        返回:
            是否创建成功
        """
        if not self.available:
            return False
            
        if self.mode == "docker":
            result = self.docker_service.get_or_create_workdir(graph_id)
            return result.get("success", False)
        else:
            return self.graph_manager.create_graph(graph_id) is not None
    
    def delete_graph(self, graph_id: str) -> bool:
        """删除知识图谱
        
        参数:
            graph_id: 图谱ID
            
        返回:
            是否删除成功
        """
        if not self.available:
            return False
            
        if self.mode == "docker":
            result = self.docker_service.api_client.delete_workdir(graph_id)
            return result.get("success", False)
        else:
            return self.graph_manager.delete_graph(graph_id)
    
    def get_graph_stats(self, graph_id: str) -> Dict[str, Any]:
        """获取图谱统计信息
        
        参数:
            graph_id: 图谱ID
            
        返回:
            统计信息字典
        """
        if not self.available:
            return {}
            
        if self.mode == "docker":
            result = self.docker_service.api_client.get_workdir_stats(graph_id)
            if result.get("success", False):
                return result.get("data", {})
            return {}
        else:
            return self.graph_manager.get_knowledge_graph_stats(graph_id)
    
    def process_documents(
        self,
        documents: List[Dict[str, Any]],
        graph_id: str,
        use_semantic_chunking: Optional[bool] = None,
        use_knowledge_graph: Optional[bool] = None,
        callback: Optional[Callable] = None,
        task_id: Optional[str] = None
    ) -> str:
        """处理文档并构建知识图谱
        
        参数:
            documents: 要处理的文档列表
            graph_id: 知识图谱ID/工作目录
            use_semantic_chunking: 是否使用语义切分
            use_knowledge_graph: 是否构建知识图谱
            callback: 进度回调
            task_id: 任务ID，如不提供则自动生成
            
        返回:
            任务ID或状态标识
        """
        if not self.available:
            return ""
        
        # Docker模式下的文档处理
        if self.mode == "docker":
            # 确保工作目录存在
            self.docker_service.ensure_workdir_exists(graph_id)
            task_results = []
            
            # 逐个处理文档
            for doc in documents:
                # 根据文档类型处理
                if "text" in doc:
                    # 文本内容
                    result = self.docker_service.process_document(
                        content=doc["text"],
                        is_file=False,
                        workdir_id=graph_id,
                        description=doc.get("metadata", {}).get("description", None)
                    )
                elif "file_path" in doc:
                    # 文件路径
                    result = self.docker_service.process_document(
                        content="",
                        is_file=True,
                        file_path=doc["file_path"],
                        workdir_id=graph_id,
                        description=doc.get("metadata", {}).get("description", None)
                    )
                else:
                    logger.warning(f"LightRAG文档格式不支持: {doc}")
                    continue
                    
                task_results.append(result)
                
                # 回调处理
                if callback and callable(callback):
                    callback({
                        "status": "processing",
                        "current": len(task_results),
                        "total": len(documents),
                        "document": doc
                    })
            
            # 处理完成后回调
            if callback and callable(callback):
                callback({
                    "status": "completed",
                    "current": len(task_results),
                    "total": len(documents),
                    "success_count": sum(1 for r in task_results if r.get("success", False))
                })
                
            # 返回任务标识
            return task_id or f"docker_task_{graph_id}_{len(task_results)}"
        else:
            # 本地模式处理
            # 使用默认设置或提供的设置
            use_semantic_chunking = use_semantic_chunking if use_semantic_chunking is not None else lightrag_config.use_semantic_chunking
            use_knowledge_graph = use_knowledge_graph if use_knowledge_graph is not None else lightrag_config.use_knowledge_graph
            
            # 处理文档
            return self.document_processor.process_documents(
                documents=documents,
                graph_id=graph_id,
                use_semantic_chunking=use_semantic_chunking,
                use_knowledge_graph=use_knowledge_graph,
                callback=callback,
                task_id=task_id
            )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取处理任务状态
        
        参数:
            task_id: 任务ID
            
        返回:
            任务状态或None
        """
        if not self.available:
            return None
            
        # Docker模式没有异步任务状态查询
        if self.mode == "docker":
            if task_id and task_id.startswith("docker_task_"):
                # Docker模式下任务已完成
                return {
                    "status": "completed",
                    "message": "文档已处理完成",
                    "progress": 100
                }
            return None
        else:
            return self.document_processor.get_task_status(task_id)
    
    def query(self, query_text: str, graph_id: str, top_k: int = 5, use_graph_relations: bool = True) -> Dict[str, Any]:
        """查询知识图谱
        
        参数:
            query_text: 查询文本
            graph_id: 图谱ID/工作目录
            top_k: 返回结果数量(本地模式有效)
            use_graph_relations: 是否使用图谱关系(本地模式有效)
            
        返回:
            查询结果
        """
        if not self.available:
            return {"answer": "很抱歉，LightRAG功能当前不可用。", "sources": []}
        
        # Docker模式下的查询
        if self.mode == "docker":
            # 确保工作目录存在
            if not self.docker_service.ensure_workdir_exists(graph_id):
                return {
                    "answer": f"工作目录 {graph_id} 不存在或创建失败",
                    "sources": [],
                    "error": "工作目录错误"
                }
                
            try:
                # 执行查询
                mode = "hybrid" if use_graph_relations else "vector"
                result = self.docker_service.process_query(query_text, graph_id, mode)
                
                if not result.get("success", False):
                    return {
                        "answer": f"查询失败: {result.get('message', '')}",
                        "sources": [],
                        "error": result.get("message", "")
                    }
                    
                # 将API响应转换为标准格式
                data = result.get("data", {})
                response = {
                    "answer": data.get("answer", ""),
                    "metadata": {},
                    "sources": []
                }
                
                # 处理来源节点
                if "sources" in data and isinstance(data["sources"], list):
                    for source in data["sources"]:
                        response["sources"].append({
                            "content": source.get("content", ""),
                            "metadata": source.get("metadata", {}),
                            "score": source.get("score", 0.0)
                        })
                        
                return response
            except Exception as e:
                logger.error(f"LightRAG Docker模式查询错误: {str(e)}")
                return {
                    "answer": f"查询过程中发生错误: {str(e)}",
                    "sources": [],
                    "error": str(e)
                }
        else:
            # 本地模式查询
            try:
                # 创建查询引擎
                query_engine = create_lightrag_query_engine(
                    graph_id=graph_id,
                    top_k=top_k,
                    use_graph_relations=use_graph_relations
                )
                
                # 执行查询
                response = query_engine.query(query_text)
                
                # 封装结果
                result = {
                    "answer": response.response,
                    "metadata": response.metadata or {},
                    "sources": []
                }
                
                # 添加源节点
                if hasattr(response, "source_nodes") and response.source_nodes:
                    for node in response.source_nodes:
                        result["sources"].append({
                            "content": node.node.text,
                            "metadata": node.node.metadata,
                            "score": node.score
                        })
                        
                return result
            except Exception as e:
                logger.error(f"LightRAG本地模式查询错误: {str(e)}")
                return {
                    "answer": f"查询过程中发生错误: {str(e)}",
                    "sources": [],
                    "error": str(e)
                }
    
    def query_stream(self, query_text: str, graph_id: str, top_k: int = 5, use_graph_relations: bool = True) -> Union[Dict[str, Any], Any]:
        """流式查询知识图谱
        
        参数:
            query_text: 查询文本
            graph_id: 图谱ID/工作目录
            top_k: 返回结果数量(本地模式有效)
            use_graph_relations: 是否使用图谱关系(本地模式有效)
            
        返回:
            流式查询结果或错误字典
        """
        if not self.available:
            return {"answer": "很抱歉，LightRAG功能当前不可用。", "sources": []}
            
        # Docker模式下的流式查询
        if self.mode == "docker":
            # 确保工作目录存在
            if not self.docker_service.ensure_workdir_exists(graph_id):
                return {
                    "answer": f"工作目录 {graph_id} 不存在或创建失败",
                    "sources": [],
                    "error": "工作目录错误"
                }
                
            try:
                # 流式查询返回原始流式响应
                mode = "hybrid" if use_graph_relations else "vector"
                return self.docker_service.api_client.query_stream(query_text, graph_id, mode)
                
            except Exception as e:
                logger.error(f"LightRAG Docker模式流式查询错误: {str(e)}")
                return {
                    "answer": f"流式查询过程中发生错误: {str(e)}",
                    "sources": [],
                    "error": str(e)
                }
        else:
            # 本地模式暂不支持流式查询
            logger.warning("本地模式暂不支持流式查询，将返回非流式查询结果")
            return self.query(query_text, graph_id, top_k, use_graph_relations)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置
        
        返回:
            配置字典
        """
        if not self.available:
            return {"available": False, "enabled": False}
        
        if self.mode == "docker":
            # Docker模式配置
            config = {
                "available": True, 
                "enabled": True,
                "mode": "docker",
                "api_url": getattr(settings, "LIGHTRAG_API_URL", "http://localhost:9621")
            }
            
            # 获取服务配置
            health_check = self.docker_service.api_client.health_check()
            if health_check.get("success", False) and "data" in health_check:
                config.update({
                    "docker_service": health_check["data"],
                    "service_status": "healthy"
                })
            else:
                config.update({
                    "service_status": "available_with_issues",
                    "issues": health_check.get("error", "")
                })
            
            return config
        else:
            # 本地模式配置
            config = lightrag_config.get_config_dict()
            config.update({
                "available": True,
                "mode": "local"
            })
            return config


# 全局客户端实例
_client_instance = None


def get_lightrag_client() -> LightRAGClient:
    """获取LightRAG客户端实例"""
    global _client_instance
    
    if _client_instance is None:
        _client_instance = LightRAGClient()
        
    return _client_instance