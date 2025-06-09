"""存储适配器
与现有系统的存储层集成，支持数据库和文件存储
"""

from typing import List, Dict, Any, Optional
import logging
import json
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageAdapter:
    """存储适配器类，负责知识图谱数据的持久化"""
    
    def __init__(self, config):
        """初始化存储适配器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.base_storage_path = getattr(config, 'storage_path', '/tmp/ai_knowledge_graphs')
        
        # 确保存储目录存在
        Path(self.base_storage_path).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"存储适配器初始化完成，存储路径: {self.base_storage_path}")
    
    def save_knowledge_graph(
        self, 
        graph_id: str, 
        triples: List[Dict[str, Any]], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """保存知识图谱数据
        
        Args:
            graph_id: 图谱ID
            triples: 三元组列表
            metadata: 元数据
            
        Returns:
            保存结果
        """
        try:
            graph_data = {
                "graph_id": graph_id,
                "created_at": datetime.utcnow().isoformat(),
                "triples": triples,
                "metadata": metadata or {}
            }
            
            # 保存到JSON文件
            file_path = self._get_graph_file_path(graph_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"知识图谱已保存: {graph_id} -> {file_path}")
            
            return {
                "success": True,
                "graph_id": graph_id,
                "file_path": str(file_path),
                "triples_count": len(triples)
            }
            
        except Exception as e:
            logger.error(f"保存知识图谱失败 {graph_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_knowledge_graph(self, graph_id: str) -> Dict[str, Any]:
        """加载知识图谱数据
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            图谱数据或错误信息
        """
        try:
            file_path = self._get_graph_file_path(graph_id)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"知识图谱不存在: {graph_id}"
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            logger.info(f"知识图谱已加载: {graph_id}")
            
            return {
                "success": True,
                "graph_data": graph_data
            }
            
        except Exception as e:
            logger.error(f"加载知识图谱失败 {graph_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_knowledge_graphs(self) -> List[Dict[str, Any]]:
        """列出所有知识图谱
        
        Returns:
            图谱列表
        """
        try:
            graphs = []
            storage_path = Path(self.base_storage_path)
            
            for file_path in storage_path.glob("*.json"):
                if file_path.name.startswith("graph_"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            graph_data = json.load(f)
                        
                        graphs.append({
                            "graph_id": graph_data.get("graph_id"),
                            "created_at": graph_data.get("created_at"),
                            "triples_count": len(graph_data.get("triples", [])),
                            "file_path": str(file_path),
                            "metadata": graph_data.get("metadata", {})
                        })
                    except Exception as e:
                        logger.warning(f"无法读取图谱文件 {file_path}: {str(e)}")
            
            # 按创建时间排序
            graphs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return graphs
            
        except Exception as e:
            logger.error(f"列出知识图谱失败: {str(e)}")
            return []
    
    def delete_knowledge_graph(self, graph_id: str) -> Dict[str, Any]:
        """删除知识图谱
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            删除结果
        """
        try:
            file_path = self._get_graph_file_path(graph_id)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"知识图谱不存在: {graph_id}"
                }
            
            # 删除JSON文件
            file_path.unlink()
            
            # 删除相关的可视化文件
            html_path = file_path.with_suffix('.html')
            if html_path.exists():
                html_path.unlink()
            
            logger.info(f"知识图谱已删除: {graph_id}")
            
            return {
                "success": True,
                "graph_id": graph_id
            }
            
        except Exception as e:
            logger.error(f"删除知识图谱失败 {graph_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def save_visualization(
        self, 
        graph_id: str, 
        html_content: str
    ) -> Dict[str, Any]:
        """保存可视化文件
        
        Args:
            graph_id: 图谱ID
            html_content: HTML内容
            
        Returns:
            保存结果
        """
        try:
            html_path = self._get_visualization_file_path(graph_id)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"可视化文件已保存: {graph_id} -> {html_path}")
            
            return {
                "success": True,
                "graph_id": graph_id,
                "html_path": str(html_path)
            }
            
        except Exception as e:
            logger.error(f"保存可视化文件失败 {graph_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_visualization_path(self, graph_id: str) -> Optional[str]:
        """获取可视化文件路径
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            文件路径或None
        """
        html_path = self._get_visualization_file_path(graph_id)
        if html_path.exists():
            return str(html_path)
        return None
    
    def export_to_format(
        self, 
        graph_id: str, 
        format_type: str = "json"
    ) -> Dict[str, Any]:
        """导出知识图谱到指定格式
        
        Args:
            graph_id: 图谱ID
            format_type: 导出格式 (json, csv, rdf)
            
        Returns:
            导出结果
        """
        try:
            # 加载图谱数据
            load_result = self.load_knowledge_graph(graph_id)
            if not load_result.get("success"):
                return load_result
            
            graph_data = load_result["graph_data"]
            triples = graph_data.get("triples", [])
            
            if format_type.lower() == "json":
                return self._export_to_json(graph_id, graph_data)
            elif format_type.lower() == "csv":
                return self._export_to_csv(graph_id, triples)
            elif format_type.lower() == "rdf":
                return self._export_to_rdf(graph_id, triples)
            else:
                return {
                    "success": False,
                    "error": f"不支持的导出格式: {format_type}"
                }
                
        except Exception as e:
            logger.error(f"导出知识图谱失败 {graph_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_graph_file_path(self, graph_id: str) -> Path:
        """获取图谱文件路径"""
        return Path(self.base_storage_path) / f"graph_{graph_id}.json"
    
    def _get_visualization_file_path(self, graph_id: str) -> Path:
        """获取可视化文件路径"""
        return Path(self.base_storage_path) / f"graph_{graph_id}.html"
    
    def _export_to_json(self, graph_id: str, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """导出为JSON格式"""
        export_path = Path(self.base_storage_path) / f"export_{graph_id}.json"
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "export_path": str(export_path),
            "format": "json"
        }
    
    def _export_to_csv(self, graph_id: str, triples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """导出为CSV格式"""
        import csv
        
        export_path = Path(self.base_storage_path) / f"export_{graph_id}.csv"
        
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Subject', 'Predicate', 'Object', 'Inferred', 'Inference_Type'])
            
            for triple in triples:
                writer.writerow([
                    triple.get('subject', ''),
                    triple.get('predicate', ''),
                    triple.get('object', ''),
                    triple.get('inferred', False),
                    triple.get('inference_type', '')
                ])
        
        return {
            "success": True,
            "export_path": str(export_path),
            "format": "csv"
        }
    
    def _export_to_rdf(self, graph_id: str, triples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """导出为RDF格式"""
        export_path = Path(self.base_storage_path) / f"export_{graph_id}.ttl"
        
        rdf_content = "@prefix : <http://example.org/kg/> .\n"
        rdf_content += "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
        rdf_content += "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n\n"
        
        for triple in triples:
            subject = self._uri_encode(triple.get('subject', ''))
            predicate = self._uri_encode(triple.get('predicate', ''))
            obj = self._uri_encode(triple.get('object', ''))
            
            rdf_content += f":{subject} :{predicate} :{obj} .\n"
        
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(rdf_content)
        
        return {
            "success": True,
            "export_path": str(export_path),
            "format": "rdf"
        }
    
    def _uri_encode(self, text: str) -> str:
        """编码URI"""
        # 简单的URI编码，将空格和特殊字符替换为下划线
        return ''.join(c if c.isalnum() else '_' for c in text) 