"""关系推理器
基于AI知识图谱框架的关系推理功能，自动推断实体间的潜在关系
"""

from typing import List, Dict, Any, Optional, Set
import logging
import networkx as nx
from collections import defaultdict, Counter
import itertools
from difflib import SequenceMatcher

from app.frameworks.ai_knowledge_graph.adapters.llm_adapter import get_llm_adapter

logger = logging.getLogger(__name__)

# 关系推理提示词
RELATIONSHIP_INFERENCE_SYSTEM_PROMPT = """
你是一个知识图谱关系推理专家。
你的任务是基于给定的实体和上下文，推断可能存在的合理关系。
"""

def get_within_community_prompt(entities):
    """生成社区内关系推理提示词"""
    return f"""
基于以下实体，识别它们之间可能存在的逻辑关系。
考虑这些实体在领域知识中的常见关联模式。

实体列表：
{entities}

为每个可能的关系，创建一个三元组（主语-谓语-宾语）。
只包括在该领域中逻辑上合理且可能真实的关系。
避免过于具体或投机性的关系。

将响应格式化为JSON数组：
[
  {{"subject": "实体1", "predicate": "关系", "object": "实体2"}},
  {{"subject": "实体3", "predicate": "关系", "object": "实体4"}}
]
"""

def get_cross_community_prompt(community1_entities, community2_entities):
    """生成跨社区关系推理提示词"""
    return f"""
分析两组相关实体之间可能存在的关系。
第一组可能代表一个主题领域，第二组代表另一个主题领域。

第一组实体：
{community1_entities}

第二组实体：
{community2_entities}

识别这两组之间可能存在的高级关系。
专注于概念性或结构性连接，而不是具体细节。

将响应格式化为JSON数组：
[
  {{"subject": "第一组实体", "predicate": "关系", "object": "第二组实体"}},
  {{"subject": "第二组实体", "predicate": "关系", "object": "第一组实体"}}
]
"""


class RelationshipInference:
    """关系推理器类"""
    
    def __init__(self, config):
        """初始化关系推理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.llm_adapter = get_llm_adapter()
        
        logger.info("关系推理器初始化完成")
    
    def infer_relationships(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """推断关系
        
        Args:
            triples: 现有三元组列表
            
        Returns:
            包含推断关系的三元组列表
        """
        if not triples:
            return triples
        
        logger.info("开始推断关系...")
        
        # 1. 构建图谱
        graph = self._build_graph(triples)
        
        # 2. 识别社区
        communities = self._identify_communities(graph)
        logger.info(f"识别到 {len(communities)} 个社区")
        
        # 3. 应用传递推理
        inferred_triples = self._apply_transitive_inference(triples)
        
        # 4. 应用词汇相似性推理
        inferred_triples.extend(self._infer_relationships_by_lexical_similarity(triples))
        
        # 5. 可选的LLM辅助推理
        if self.config.use_llm_for_inference:
            # 社区内推理
            within_community_triples = self._infer_within_community_relationships(
                communities, graph
            )
            inferred_triples.extend(within_community_triples)
            
            # 跨社区推理
            cross_community_triples = self._infer_relationships_with_llm(
                communities, graph
            )
            inferred_triples.extend(cross_community_triples)
        
        # 6. 合并所有三元组并去重
        all_triples = triples + inferred_triples
        deduplicated_triples = self._deduplicate_triples(all_triples)
        
        logger.info(f"推断了 {len(inferred_triples)} 个新关系，总计 {len(deduplicated_triples)} 个关系")
        return deduplicated_triples
    
    def _build_graph(self, triples: List[Dict[str, Any]]) -> nx.Graph:
        """构建networkx图
        
        Args:
            triples: 三元组列表
            
        Returns:
            构建的图
        """
        graph = nx.Graph()
        
        for triple in triples:
            subject = triple["subject"]
            obj = triple["object"]
            predicate = triple["predicate"]
            
            # 添加边，保留关系信息
            if graph.has_edge(subject, obj):
                # 如果边已存在，添加关系到现有边
                graph[subject][obj]["relationships"].add(predicate)
            else:
                graph.add_edge(subject, obj, relationships={predicate})
        
        return graph
    
    def _identify_communities(self, graph: nx.Graph) -> List[Set[str]]:
        """识别图中的社区
        
        Args:
            graph: networkx图
            
        Returns:
            社区列表
        """
        if len(graph.nodes) < 2:
            return [set(graph.nodes)]
        
        try:
            # 使用Louvain算法进行社区检测
            communities = nx.community.louvain_communities(graph)
            
            # 过滤小社区
            min_community_size = max(2, self.config.min_community_size)
            filtered_communities = [
                community for community in communities 
                if len(community) >= min_community_size
            ]
            
            if not filtered_communities:
                # 如果没有足够大的社区，返回整个图作为一个社区
                return [set(graph.nodes)]
            
            return filtered_communities
            
        except Exception as e:
            logger.warning(f"社区检测失败: {str(e)}")
            # 降级到连接组件
            return [set(component) for component in nx.connected_components(graph)]
    
    def _apply_transitive_inference(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用传递推理
        
        Args:
            triples: 现有三元组列表
            
        Returns:
            推断的三元组列表
        """
        inferred_triples = []
        
        # 按谓词分组
        predicate_groups = defaultdict(list)
        for triple in triples:
            predicate_groups[triple["predicate"]].append(triple)
        
        # 对于每个谓词，应用传递性
        for predicate, pred_triples in predicate_groups.items():
            if self._is_transitive_relation(predicate):
                # 构建有向图
                directed_graph = nx.DiGraph()
                for triple in pred_triples:
                    directed_graph.add_edge(triple["subject"], triple["object"])
                
                # 找到传递闭包
                try:
                    transitive_closure = nx.transitive_closure(directed_graph)
                    
                    for source, target in transitive_closure.edges():
                        # 检查这是否是新的关系
                        if not directed_graph.has_edge(source, target):
                            inferred_triples.append({
                                "subject": source,
                                "predicate": predicate,
                                "object": target,
                                "inferred": True,
                                "inference_type": "transitive"
                            })
                except Exception as e:
                    logger.warning(f"传递推理失败 for {predicate}: {str(e)}")
        
        return inferred_triples
    
    def _is_transitive_relation(self, predicate: str) -> bool:
        """判断关系是否具有传递性
        
        Args:
            predicate: 谓词
            
        Returns:
            是否具有传递性
        """
        transitive_keywords = [
            "part of", "member of", "subset of", "instance of", "type of",
            "contains", "includes", "belongs to", "category of", "class of",
            "is a", "种类", "类型", "包含", "属于", "成员", "部分",
            "子类", "实例", "组成", "归属"
        ]
        
        predicate_lower = predicate.lower()
        return any(keyword in predicate_lower for keyword in transitive_keywords)
    
    def _infer_relationships_by_lexical_similarity(
        self, 
        triples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """基于词汇相似性推断关系
        
        Args:
            triples: 现有三元组列表
            
        Returns:
            推断的三元组列表
        """
        inferred_triples = []
        
        # 提取所有实体
        entities = set()
        for triple in triples:
            entities.add(triple["subject"])
            entities.add(triple["object"])
        
        entity_list = list(entities)
        
        # 对实体进行两两比较
        for i, entity1 in enumerate(entity_list):
            for entity2 in entity_list[i+1:]:
                similarity = self._calculate_string_similarity(entity1, entity2)
                
                if similarity > 0.7:  # 高相似度阈值
                    # 推断"相似"关系
                    inferred_triples.append({
                        "subject": entity1,
                        "predicate": "similar to",
                        "object": entity2,
                        "inferred": True,
                        "inference_type": "lexical_similarity",
                        "similarity_score": similarity
                    })
                elif similarity > 0.5:  # 中等相似度阈值
                    # 推断"相关"关系
                    inferred_triples.append({
                        "subject": entity1,
                        "predicate": "related to",
                        "object": entity2,
                        "inferred": True,
                        "inference_type": "lexical_similarity",
                        "similarity_score": similarity
                    })
        
        return inferred_triples
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度
        
        Args:
            str1: 字符串1
            str2: 字符串2
            
        Returns:
            相似度分数 (0-1)
        """
        # 使用SequenceMatcher计算相似度
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _infer_within_community_relationships(
        self, 
        communities: List[Set[str]], 
        graph: nx.Graph
    ) -> List[Dict[str, Any]]:
        """推断社区内的关系
        
        Args:
            communities: 社区列表
            graph: 图
            
        Returns:
            推断的三元组列表
        """
        inferred_triples = []
        
        for community in communities:
            if len(community) < 3:  # 太小的社区跳过
                continue
            
            # 选择代表性实体
            representative_entities = self._select_representative_entities(
                community, graph, max_entities=8
            )
            
            if len(representative_entities) < 2:
                continue
            
            try:
                # 调用LLM推断社区内关系
                system_prompt = RELATIONSHIP_INFERENCE_SYSTEM_PROMPT
                user_prompt = get_within_community_prompt(list(representative_entities))
                
                response = self.llm_adapter.call_llm(
                    user_prompt=user_prompt,
                    system_prompt=system_prompt,
                    max_tokens=self.config.max_tokens,
                    temperature=0.3
                )
                
                # 解析响应
                llm_triples = self._parse_llm_triples_response(response)
                
                for triple in llm_triples:
                    triple.update({
                        "inferred": True,
                        "inference_type": "within_community_llm"
                    })
                
                inferred_triples.extend(llm_triples)
                
            except Exception as e:
                logger.warning(f"社区内关系推理失败: {str(e)}")
        
        return inferred_triples
    
    def _infer_relationships_with_llm(
        self, 
        communities: List[Set[str]], 
        graph: nx.Graph
    ) -> List[Dict[str, Any]]:
        """使用LLM推断跨社区关系
        
        Args:
            communities: 社区列表
            graph: 图
            
        Returns:
            推断的三元组列表
        """
        inferred_triples = []
        
        if len(communities) < 2:
            return inferred_triples
        
        # 对社区进行两两比较
        for i, community1 in enumerate(communities):
            for community2 in communities[i+1:]:
                # 选择每个社区的代表性实体
                rep_entities1 = self._select_representative_entities(
                    community1, graph, max_entities=5
                )
                rep_entities2 = self._select_representative_entities(
                    community2, graph, max_entities=5
                )
                
                if len(rep_entities1) < 1 or len(rep_entities2) < 1:
                    continue
                
                try:
                    # 调用LLM推断跨社区关系
                    system_prompt = RELATIONSHIP_INFERENCE_SYSTEM_PROMPT
                    user_prompt = get_cross_community_prompt(
                        list(rep_entities1), list(rep_entities2)
                    )
                    
                    response = self.llm_adapter.call_llm(
                        user_prompt=user_prompt,
                        system_prompt=system_prompt,
                        max_tokens=self.config.max_tokens,
                        temperature=0.3
                    )
                    
                    # 解析响应
                    llm_triples = self._parse_llm_triples_response(response)
                    
                    for triple in llm_triples:
                        triple.update({
                            "inferred": True,
                            "inference_type": "cross_community_llm"
                        })
                    
                    inferred_triples.extend(llm_triples)
                    
                except Exception as e:
                    logger.warning(f"跨社区关系推理失败: {str(e)}")
        
        return inferred_triples
    
    def _select_representative_entities(
        self, 
        community: Set[str], 
        graph: nx.Graph, 
        max_entities: int = 5
    ) -> List[str]:
        """选择社区的代表性实体
        
        Args:
            community: 社区实体集合
            graph: 图
            max_entities: 最大实体数
            
        Returns:
            代表性实体列表
        """
        if len(community) <= max_entities:
            return list(community)
        
        # 计算每个实体在社区内的重要性
        entity_scores = {}
        
        for entity in community:
            if entity in graph:
                # 基于度中心性
                degree = graph.degree(entity)
                # 基于邻居数量
                neighbors_in_community = len([
                    neighbor for neighbor in graph.neighbors(entity)
                    if neighbor in community
                ])
                
                entity_scores[entity] = degree + neighbors_in_community
            else:
                entity_scores[entity] = 0
        
        # 选择得分最高的实体
        sorted_entities = sorted(
            entity_scores.items(), 
            key=lambda x: (-x[1], x[0])  # 按得分降序，名称升序
        )
        
        return [entity for entity, _ in sorted_entities[:max_entities]]
    
    def _parse_llm_triples_response(self, response: str) -> List[Dict[str, Any]]:
        """解析LLM的三元组响应
        
        Args:
            response: LLM响应
            
        Returns:
            解析的三元组列表
        """
        triples = []
        
        try:
            import json
            
            # 尝试提取JSON数组
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                if isinstance(parsed_data, list):
                    for item in parsed_data:
                        if (isinstance(item, dict) and 
                            "subject" in item and 
                            "predicate" in item and 
                            "object" in item):
                            triples.append({
                                "subject": str(item["subject"]).strip(),
                                "predicate": str(item["predicate"]).strip(),
                                "object": str(item["object"]).strip()
                            })
            
        except Exception as e:
            logger.warning(f"解析LLM三元组响应失败: {str(e)}")
        
        return triples
    
    def _deduplicate_triples(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重三元组
        
        Args:
            triples: 三元组列表
            
        Returns:
            去重后的三元组列表
        """
        seen = set()
        deduplicated = []
        
        for triple in triples:
            # 创建标准化的键
            key = (
                triple["subject"].lower().strip(),
                triple["predicate"].lower().strip(),
                triple["object"].lower().strip()
            )
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(triple)
        
        if len(deduplicated) < len(triples):
            logger.info(f"去重移除了 {len(triples) - len(deduplicated)} 个重复三元组")
        
        return deduplicated 