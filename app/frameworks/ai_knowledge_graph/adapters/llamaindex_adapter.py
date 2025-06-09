"""LlamaIndex适配器
与LlamaIndex生态系统集成，支持知识图谱构建的数据节点和查询引擎
"""

from typing import List, Dict, Any, Optional, Union
import logging
from datetime import datetime

try:
    from llama_index.core import Document, VectorStoreIndex, ServiceContext
    from llama_index.core.node_parser import SimpleNodeParser
    from llama_index.core.schema import BaseNode, TextNode
    from llama_index.core.indices.knowledge_graph import KnowledgeGraphIndex
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    logger.warning("LlamaIndex未安装，LlamaIndex适配器功能受限")

from app.frameworks.ai_knowledge_graph.processor import KnowledgeGraphProcessor

logger = logging.getLogger(__name__)


class LlamaIndexAdapter:
    """LlamaIndex适配器类，将AI知识图谱集成到LlamaIndex生态"""
    
    def __init__(self, config, service_context=None):
        """初始化LlamaIndex适配器
        
        Args:
            config: 配置对象
            service_context: LlamaIndex服务上下文
        """
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("LlamaIndex未安装，无法使用LlamaIndex适配器")
        
        self.config = config
        self.service_context = service_context
        self.kg_processor = KnowledgeGraphProcessor(config)
        
        logger.info("LlamaIndex适配器初始化完成")
    
    def create_knowledge_graph_from_documents(
        self, 
        documents: List[Document],
        graph_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """从LlamaIndex文档创建知识图谱
        
        Args:
            documents: LlamaIndex文档列表
            graph_id: 图谱ID，可选
            
        Returns:
            知识图谱创建结果
        """
        try:
            # 提取文档文本
            document_texts = []
            for doc in documents:
                text_content = doc.text if hasattr(doc, 'text') else str(doc)
                document_texts.append({
                    "text": text_content,
                    "metadata": getattr(doc, 'metadata', {})
                })
            
            # 生成图谱ID
            if not graph_id:
                graph_id = f"llamaindex_kg_{int(datetime.now().timestamp())}"
            
            # 使用知识图谱处理器处理文档
            result = self.kg_processor.process_documents(
                document_texts, 
                graph_id=graph_id
            )
            
            # 添加LlamaIndex相关元数据
            result["source"] = "llamaindex_documents"
            result["document_count"] = len(documents)
            
            logger.info(f"从 {len(documents)} 个LlamaIndex文档创建知识图谱: {graph_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"从LlamaIndex文档创建知识图谱失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_knowledge_graph_nodes(
        self, 
        triples: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> List[BaseNode]:
        """将知识图谱三元组转换为LlamaIndex节点
        
        Args:
            triples: 三元组列表
            include_metadata: 是否包含元数据
            
        Returns:
            LlamaIndex节点列表
        """
        if not LLAMAINDEX_AVAILABLE:
            logger.error("LlamaIndex未安装，无法创建节点")
            return []
        
        try:
            nodes = []
            
            for i, triple in enumerate(triples):
                # 创建节点文本
                node_text = f"{triple['subject']} {triple['predicate']} {triple['object']}"
                
                # 创建元数据
                metadata = {
                    "node_type": "knowledge_graph_triple",
                    "triple_id": i,
                    "subject": triple['subject'],
                    "predicate": triple['predicate'],
                    "object": triple['object']
                }
                
                if include_metadata:
                    # 添加推理信息
                    if triple.get('inferred', False):
                        metadata["inferred"] = True
                        metadata["inference_type"] = triple.get('inference_type', 'unknown')
                    
                    # 添加其他元数据
                    for key, value in triple.items():
                        if key not in ["subject", "predicate", "object"]:
                            metadata[f"triple_{key}"] = value
                
                # 创建TextNode
                node = TextNode(
                    text=node_text,
                    metadata=metadata,
                    id_=f"kg_triple_{i}"
                )
                
                nodes.append(node)
            
            logger.info(f"创建了 {len(nodes)} 个知识图谱节点")
            return nodes
            
        except Exception as e:
            logger.error(f"创建知识图谱节点失败: {str(e)}")
            return []
    
    def create_hybrid_index(
        self, 
        documents: List[Document],
        graph_id: Optional[str] = None,
        include_vector_index: bool = True
    ) -> Dict[str, Any]:
        """创建混合索引，包含向量索引和知识图谱
        
        Args:
            documents: 文档列表
            graph_id: 图谱ID
            include_vector_index: 是否包含向量索引
            
        Returns:
            混合索引结果
        """
        try:
            # 1. 创建知识图谱
            kg_result = self.create_knowledge_graph_from_documents(documents, graph_id)
            
            if not kg_result.get("triples"):
                logger.warning("未提取到三元组，无法创建混合索引")
                return kg_result
            
            # 2. 创建知识图谱节点
            kg_nodes = self.create_knowledge_graph_nodes(kg_result["triples"])
            
            # 3. 可选创建向量索引
            vector_index = None
            if include_vector_index and self.service_context:
                try:
                    # 解析原始文档为节点
                    node_parser = SimpleNodeParser.from_defaults()
                    doc_nodes = node_parser.get_nodes_from_documents(documents)
                    
                    # 合并文档节点和知识图谱节点
                    all_nodes = doc_nodes + kg_nodes
                    
                    # 创建向量索引
                    vector_index = VectorStoreIndex(
                        nodes=all_nodes,
                        service_context=self.service_context
                    )
                    
                except Exception as e:
                    logger.warning(f"创建向量索引失败: {str(e)}")
            
            result = {
                "success": True,
                "graph_id": kg_result.get("graph_id"),
                "knowledge_graph": kg_result,
                "kg_nodes": kg_nodes,
                "vector_index": vector_index,
                "hybrid_node_count": len(kg_nodes) + (len(documents) if include_vector_index else 0)
            }
            
            logger.info(f"创建混合索引成功，包含 {len(kg_nodes)} 个知识图谱节点")
            
            return result
            
        except Exception as e:
            logger.error(f"创建混合索引失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def query_knowledge_graph(
        self, 
        query: str, 
        triples: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """查询知识图谱
        
        Args:
            query: 查询文本
            triples: 三元组列表
            top_k: 返回结果数量
            
        Returns:
            查询结果
        """
        try:
            # 简单的关键词匹配查询
            query_lower = query.lower()
            results = []
            
            for triple in triples:
                score = 0
                
                # 计算相关性分数
                if query_lower in triple['subject'].lower():
                    score += 2
                if query_lower in triple['predicate'].lower():
                    score += 1
                if query_lower in triple['object'].lower():
                    score += 2
                
                # 检查关键词重叠
                query_words = set(query_lower.split())
                triple_words = set(
                    (triple['subject'] + ' ' + triple['predicate'] + ' ' + triple['object']).lower().split()
                )
                overlap = len(query_words.intersection(triple_words))
                score += overlap
                
                if score > 0:
                    results.append({
                        "triple": triple,
                        "score": score,
                        "explanation": f"匹配分数: {score}"
                    })
            
            # 按分数排序并返回top_k结果
            results.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"知识图谱查询 '{query}' 返回 {len(results[:top_k])} 个结果")
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"知识图谱查询失败: {str(e)}")
            return []
    
    def extract_entities_from_nodes(
        self, 
        nodes: List[BaseNode]
    ) -> List[str]:
        """从LlamaIndex节点提取实体
        
        Args:
            nodes: 节点列表
            
        Returns:
            实体列表
        """
        try:
            entities = set()
            
            for node in nodes:
                # 从节点文本提取三元组
                node_text = node.text if hasattr(node, 'text') else str(node)
                triples = self.kg_processor.extract_triples_only(node_text)
                
                # 收集实体
                for triple in triples:
                    entities.add(triple['subject'])
                    entities.add(triple['object'])
            
            entity_list = list(entities)
            logger.info(f"从 {len(nodes)} 个节点提取了 {len(entity_list)} 个实体")
            
            return entity_list
            
        except Exception as e:
            logger.error(f"从节点提取实体失败: {str(e)}")
            return []
    
    def create_graph_query_engine(
        self, 
        triples: List[Dict[str, Any]]
    ):
        """创建知识图谱查询引擎
        
        Args:
            triples: 三元组列表
            
        Returns:
            查询引擎或None
        """
        try:
            if not self.service_context:
                logger.warning("未提供ServiceContext，无法创建查询引擎")
                return None
            
            # 创建知识图谱节点
            kg_nodes = self.create_knowledge_graph_nodes(triples)
            
            if not kg_nodes:
                logger.warning("未创建知识图谱节点，无法创建查询引擎")
                return None
            
            # 创建知识图谱索引
            kg_index = KnowledgeGraphIndex(
                nodes=kg_nodes,
                service_context=self.service_context
            )
            
            # 创建查询引擎
            query_engine = kg_index.as_query_engine()
            
            logger.info(f"创建知识图谱查询引擎成功，包含 {len(kg_nodes)} 个节点")
            
            return query_engine
            
        except Exception as e:
            logger.error(f"创建知识图谱查询引擎失败: {str(e)}")
            return None
    
    def get_related_triples(
        self, 
        entity: str, 
        triples: List[Dict[str, Any]],
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """获取与实体相关的三元组
        
        Args:
            entity: 目标实体
            triples: 三元组列表
            max_hops: 最大跳数
            
        Returns:
            相关三元组列表
        """
        try:
            related = []
            visited = set()
            current_entities = {entity.lower()}
            
            for hop in range(max_hops):
                new_entities = set()
                
                for triple in triples:
                    triple_id = (triple['subject'], triple['predicate'], triple['object'])
                    if triple_id in visited:
                        continue
                    
                    subject_lower = triple['subject'].lower()
                    object_lower = triple['object'].lower()
                    
                    if subject_lower in current_entities or object_lower in current_entities:
                        related.append(triple)
                        visited.add(triple_id)
                        new_entities.add(subject_lower)
                        new_entities.add(object_lower)
                
                if not new_entities:
                    break
                
                current_entities = new_entities
            
            logger.info(f"找到实体 '{entity}' 的 {len(related)} 个相关三元组 (最大跳数: {max_hops})")
            
            return related
            
        except Exception as e:
            logger.error(f"获取相关三元组失败: {str(e)}")
            return []
    
    def export_to_llamaindex_format(
        self, 
        triples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """导出为LlamaIndex兼容格式
        
        Args:
            triples: 三元组列表
            
        Returns:
            LlamaIndex格式的数据
        """
        try:
            # 创建文档
            documents = []
            nodes = self.create_knowledge_graph_nodes(triples)
            
            for i, node in enumerate(nodes):
                doc = Document(
                    text=node.text,
                    metadata=node.metadata,
                    id_=f"kg_doc_{i}"
                )
                documents.append(doc)
            
            export_data = {
                "documents": documents,
                "nodes": nodes,
                "triples": triples,
                "export_format": "llamaindex",
                "export_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"导出了 {len(documents)} 个文档和 {len(nodes)} 个节点到LlamaIndex格式")
            
            return export_data
            
        except Exception as e:
            logger.error(f"导出到LlamaIndex格式失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 