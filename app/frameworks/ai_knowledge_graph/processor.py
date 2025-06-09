"""AI知识图谱核心处理器
提供文档处理、三元组提取、实体标准化和关系推断的完整流程
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
import logging
import json
import time
from pathlib import Path

from app.frameworks.ai_knowledge_graph.config import get_config
from app.frameworks.ai_knowledge_graph.core.extractor import TripleExtractor
from app.frameworks.ai_knowledge_graph.core.standardizer import EntityStandardizer
from app.frameworks.ai_knowledge_graph.core.inference import RelationshipInference
from app.frameworks.ai_knowledge_graph.core.visualizer import KnowledgeGraphVisualizer
from app.frameworks.ai_knowledge_graph.adapters.llm_adapter import get_llm_adapter

logger = logging.getLogger(__name__)

# 进度回调类型
ProgressCallback = Callable[[str, str, float, Optional[Dict[str, Any]]], None]

def null_callback(task_id: str, status: str, progress: float, info: Optional[Dict[str, Any]] = None) -> None:
    """默认的空回调函数"""
    logger.debug(f"AI-KG Task {task_id}: {status} - {progress:.1%} {info or ''}")


class KnowledgeGraphProcessor:
    """知识图谱处理器，负责完整的处理流程"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化处理器
        
        Args:
            config: 可选的配置覆盖
        """
        self.config = get_config()
        if config:
            self.config.update_config(config)
        
        # 初始化组件
        self.extractor = TripleExtractor(self.config)
        self.standardizer = EntityStandardizer(self.config)
        self.inference = RelationshipInference(self.config)
        self.visualizer = KnowledgeGraphVisualizer(self.config)
        
        logger.info("AI知识图谱处理器初始化完成")
    
    def process_text(
        self,
        text: str,
        graph_id: Optional[str] = None,
        callback: ProgressCallback = null_callback,
        task_id: Optional[str] = None,
        save_visualization: bool = True,
        return_visualization: bool = False
    ) -> Dict[str, Any]:
        """处理文本并生成知识图谱
        
        Args:
            text: 输入文本
            graph_id: 图谱ID，可选
            callback: 进度回调函数
            task_id: 任务ID
            save_visualization: 是否保存可视化文件
            return_visualization: 是否返回可视化HTML
            
        Returns:
            包含三元组、统计信息和可视化的字典
        """
        if not text or not text.strip():
            logger.warning("输入文本为空")
            return {"triples": [], "stats": {}, "visualization": None}
        
        # 生成任务ID
        if not task_id:
            task_id = f"ai_kg_process_{int(time.time())}"
        
        # 生成图谱ID
        if not graph_id:
            graph_id = f"graph_{int(time.time())}"
        
        logger.info(f"开始处理知识图谱: {graph_id}, 任务ID: {task_id}")
        callback(task_id, "开始处理", 0.0, {"graph_id": graph_id})
        
        try:
            # 第一阶段：三元组提取
            callback(task_id, "提取三元组", 0.1, None)
            triples = self.extractor.extract_triples(text, callback, task_id)
            logger.info(f"提取到 {len(triples)} 个三元组")
            
            if not triples:
                logger.warning("未提取到任何三元组")
                return {"triples": [], "stats": {}, "visualization": None}
            
            # 第二阶段：实体标准化
            if self.config.standardization_enabled:
                callback(task_id, "标准化实体", 0.4, None)
                triples = self.standardizer.standardize_entities(triples)
                logger.info(f"标准化后剩余 {len(triples)} 个三元组")
            
            # 第三阶段：关系推断
            if self.config.inference_enabled:
                callback(task_id, "推断关系", 0.6, None)
                triples = self.inference.infer_relationships(triples)
                logger.info(f"推断后共有 {len(triples)} 个三元组")
            
            # 第四阶段：生成统计信息
            callback(task_id, "生成统计", 0.8, None)
            stats = self._generate_stats(triples)
            
            # 第五阶段：可视化
            visualization_html = None
            if save_visualization or return_visualization:
                callback(task_id, "生成可视化", 0.9, None)
                
                if save_visualization:
                    output_file = Path(self.config.base_dir) / f"{graph_id}.html"
                    vis_stats = self.visualizer.visualize_knowledge_graph(
                        triples, str(output_file)
                    )
                    stats.update(vis_stats)
                
                if return_visualization:
                    vis_result = self.visualizer.visualize_knowledge_graph(
                        triples=triples,
                        output_path=None,
                        visualization_type="enhanced"
                    )
                    visualization_html = vis_result.get("html_content", "")
            
            callback(task_id, "完成", 1.0, {"stats": stats})
            logger.info(f"知识图谱处理完成: {stats}")
            
            result = {
                "triples": triples,
                "stats": stats,
                "graph_id": graph_id,
                "task_id": task_id
            }
            
            # 如果生成了HTML可视化，添加到结果中
            if visualization_html:
                result["visualization_html"] = visualization_html
                result["visualization"] = visualization_html  # 兼容性
            
            return result
            
        except Exception as e:
            logger.error(f"知识图谱处理失败: {str(e)}")
            callback(task_id, "错误", 0.0, {"error": str(e)})
            raise
    
    def process_documents(
        self,
        documents: List[Dict[str, Any]],
        graph_id: str,
        callback: ProgressCallback = null_callback,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理多个文档并构建知识图谱
        
        Args:
            documents: 文档列表，每个文档包含text字段
            graph_id: 图谱ID
            callback: 进度回调
            task_id: 任务ID
            
        Returns:
            处理结果
        """
        if not documents:
            logger.warning("没有提供文档")
            return {"triples": [], "stats": {}, "visualization": None}
        
        # 合并所有文档的文本
        full_text = "\n\n".join([
            doc.get("text", "") if isinstance(doc, dict) else str(doc)
            for doc in documents
        ])
        
        return self.process_text(
            full_text, 
            graph_id=graph_id, 
            callback=callback, 
            task_id=task_id
        )
    
    def extract_triples_only(self, text: str) -> List[Dict[str, Any]]:
        """仅提取三元组，不进行后续处理
        
        Args:
            text: 输入文本
            
        Returns:
            三元组列表
        """
        return self.extractor.extract_triples(text)
    
    def standardize_triples(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """仅对三元组进行标准化
        
        Args:
            triples: 三元组列表
            
        Returns:
            标准化后的三元组列表
        """
        return self.standardizer.standardize_entities(triples)
    
    def infer_relationships_only(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """仅进行关系推断
        
        Args:
            triples: 三元组列表
            
        Returns:
            推断后的三元组列表
        """
        return self.inference.infer_relationships(triples)
    
    def generate_visualization(
        self, 
        triples: List[Dict[str, Any]], 
        output_file: Optional[str] = None
    ) -> str:
        """生成可视化
        
        Args:
            triples: 三元组列表
            output_file: 输出文件路径，可选
            
        Returns:
            可视化HTML或文件路径
        """
        if output_file:
            result = self.visualizer.visualize_knowledge_graph(triples, output_file)
            return result.get("output_path", output_file)
        else:
            result = self.visualizer.visualize_knowledge_graph(triples)
            return result.get("html_content", "")
    
    def _generate_stats(self, triples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成统计信息
        
        Args:
            triples: 三元组列表
            
        Returns:
            统计信息字典
        """
        if not triples:
            return {"total_triples": 0, "unique_entities": 0, "unique_relations": 0}
        
        # 统计实体
        entities = set()
        relations = set()
        inferred_count = 0
        
        for triple in triples:
            if isinstance(triple, dict):
                entities.add(triple.get("subject", ""))
                entities.add(triple.get("object", ""))
                relations.add(triple.get("predicate", ""))
                
                if triple.get("inferred", False):
                    inferred_count += 1
        
        # 移除空字符串
        entities.discard("")
        relations.discard("")
        
        return {
            "total_triples": len(triples),
            "unique_entities": len(entities),
            "unique_relations": len(relations),
            "inferred_triples": inferred_count,
            "original_triples": len(triples) - inferred_count
        }
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取当前配置
        
        Returns:
            配置字典
        """
        return self.config.get_config_dict()
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """更新配置
        
        Args:
            config_updates: 配置更新
        """
        self.config.update_config(config_updates)
        
        # 重新初始化组件
        self.extractor = TripleExtractor(self.config)
        self.standardizer = EntityStandardizer(self.config)
        self.inference = RelationshipInference(self.config)
        self.visualizer = KnowledgeGraphVisualizer(self.config) 