"""实体标准化器
基于AI知识图谱框架的实体标准化功能，确保实体命名一致性
"""

from typing import List, Dict, Any, Optional
import logging
import re
from collections import defaultdict

from app.frameworks.ai_knowledge_graph.adapters.llm_adapter import get_llm_adapter

logger = logging.getLogger(__name__)

# 实体解析提示词
ENTITY_RESOLUTION_SYSTEM_PROMPT = """
你是一个实体解析和知识表示专家。
你的任务是标准化知识图谱中的实体名称以确保一致性。
"""

def get_entity_resolution_user_prompt(entity_list):
    """生成实体解析的用户提示词"""
    return f"""
下面是从知识图谱中提取的实体名称列表。
有些可能指向相同的现实世界实体，但措辞不同。

请识别指向相同概念的实体组，并为每个组提供标准化名称。
返回答案为JSON对象，其中键是标准化名称，值是应映射到该标准名称的所有变体名称的数组。
仅包括具有多个变体或需要标准化的实体。

实体列表：
{entity_list}

将你的响应格式化为有效的JSON，如下所示：
{{
  "标准化名称1": ["变体1", "变体2"],
  "标准化名称2": ["变体3", "变体4", "变体5"]
}}
"""


class EntityStandardizer:
    """实体标准化器类"""
    
    def __init__(self, config):
        """初始化实体标准化器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.llm_adapter = get_llm_adapter()
        
        logger.info("实体标准化器初始化完成")
    
    def standardize_entities(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标准化实体名称
        
        Args:
            triples: 三元组列表
            
        Returns:
            标准化后的三元组列表
        """
        if not triples:
            return triples
        
        logger.info("开始标准化实体名称...")
        
        # 验证输入三元组
        valid_triples = []
        invalid_count = 0
        
        for triple in triples:
            if isinstance(triple, dict) and "subject" in triple and "predicate" in triple and "object" in triple:
                valid_triples.append(triple)
            else:
                invalid_count += 1
        
        if invalid_count > 0:
            logger.warning(f"过滤掉 {invalid_count} 个无效三元组")
        
        if not valid_triples:
            logger.error("没有有效的三元组进行实体标准化")
            return []
        
        # 1. 提取所有唯一实体
        all_entities = set()
        for triple in valid_triples:
            all_entities.add(triple["subject"].lower())
            all_entities.add(triple["object"].lower())
        
        # 2. 基于规则的标准化
        standardized_entities = self._rule_based_standardization(all_entities, valid_triples)
        
        # 3. 可选的LLM辅助标准化
        if self.config.use_llm_for_entities:
            standardized_entities = self._llm_assisted_standardization(
                standardized_entities, all_entities
            )
        
        # 4. 应用标准化到所有三元组
        standardized_triples = self._apply_standardization(valid_triples, standardized_entities)
        
        # 5. 过滤自引用三元组
        filtered_triples = [
            triple for triple in standardized_triples 
            if triple["subject"] != triple["object"]
        ]
        
        if len(filtered_triples) < len(standardized_triples):
            logger.info(f"移除了 {len(standardized_triples) - len(filtered_triples)} 个自引用三元组")
        
        logger.info(f"标准化了 {len(all_entities)} 个实体为 {len(set(standardized_entities.values()))} 个标准形式")
        return filtered_triples
    
    def _rule_based_standardization(
        self, 
        all_entities: set, 
        valid_triples: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """基于规则的标准化
        
        Args:
            all_entities: 所有实体集合
            valid_triples: 有效三元组列表
            
        Returns:
            实体标准化映射
        """
        standardized_entities = {}
        entity_groups = defaultdict(list)
        
        # 标准化文本的辅助函数
        def normalize_text(text):
            text = text.lower()
            # 移除常见停用词
            stopwords = {"the", "a", "an", "of", "and", "or", "in", "on", "at", "to", "for", "with", "by", "as"}
            words = [word for word in re.findall(r'\b\w+\b', text) if word not in stopwords]
            return " ".join(words)
        
        # 按复杂度排序实体（较长的实体优先）
        sorted_entities = sorted(all_entities, key=lambda x: (-len(x), x))
        
        # 第一遍：基础标准化
        for entity in sorted_entities:
            normalized = normalize_text(entity)
            if normalized:  # 跳过空字符串
                entity_groups[normalized].append(entity)
        
        # 为每个组选择最代表性的名称
        for group_key, variants in entity_groups.items():
            if len(variants) == 1:
                # 只有一个变体，直接使用
                standardized_entities[variants[0]] = variants[0]
            else:
                # 多个变体，选择最常见或最短的作为标准
                variant_counts = defaultdict(int)
                for triple in valid_triples:
                    for variant in variants:
                        if triple["subject"].lower() == variant:
                            variant_counts[variant] += 1
                        if triple["object"].lower() == variant:
                            variant_counts[variant] += 1
                
                # 选择最常见的变体作为标准形式
                standard_form = sorted(variants, key=lambda x: (-variant_counts[x], len(x)))[0]
                for variant in variants:
                    standardized_entities[variant] = standard_form
        
        # 第二遍：处理词根关系
        additional_standardizations = self._handle_word_relationships(standardized_entities)
        standardized_entities.update(additional_standardizations)
        
        return standardized_entities
    
    def _handle_word_relationships(self, standardized_entities: Dict[str, str]) -> Dict[str, str]:
        """处理词根关系
        
        Args:
            standardized_entities: 现有标准化映射
            
        Returns:
            额外的标准化映射
        """
        additional_standardizations = {}
        
        # 获取所有标准形式
        standard_forms = set(standardized_entities.values())
        sorted_standards = sorted(standard_forms, key=len)
        
        for i, entity1 in enumerate(sorted_standards):
            e1_words = set(entity1.split())
            
            for entity2 in sorted_standards[i+1:]:
                if entity1 == entity2:
                    continue
                
                e2_words = set(entity2.split())
                
                # 检查一个实体是否是另一个的子集
                if e1_words.issubset(e2_words) and len(e1_words) > 0:
                    # 较短的可能是更通用的概念
                    additional_standardizations[entity2] = entity1
                elif e2_words.issubset(e1_words) and len(e2_words) > 0:
                    additional_standardizations[entity1] = entity2
                else:
                    # 检查词干相似性
                    stems1 = {word[:4] for word in e1_words if len(word) > 4}
                    stems2 = {word[:4] for word in e2_words if len(word) > 4}
                    
                    shared_stems = stems1.intersection(stems2)
                    
                    if shared_stems and (len(shared_stems) / max(len(stems1), len(stems2))) > 0.5:
                        # 使用较短的实体作为标准
                        if len(entity1) <= len(entity2):
                            additional_standardizations[entity2] = entity1
                        else:
                            additional_standardizations[entity1] = entity2
        
        return additional_standardizations
    
    def _llm_assisted_standardization(
        self, 
        standardized_entities: Dict[str, str], 
        all_entities: set
    ) -> Dict[str, str]:
        """LLM辅助的实体标准化
        
        Args:
            standardized_entities: 现有标准化映射
            all_entities: 所有实体集合
            
        Returns:
            更新的标准化映射
        """
        try:
            entity_list = list(all_entities)
            if len(entity_list) > 100:  # 限制实体数量以避免token限制
                entity_list = entity_list[:100]
            
            # 构造提示词
            system_prompt = ENTITY_RESOLUTION_SYSTEM_PROMPT
            user_prompt = get_entity_resolution_user_prompt(entity_list)
            
            # 调用LLM
            response = self.llm_adapter.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=0.2  # 较低温度以获得一致性
            )
            
            # 解析响应
            llm_mappings = self._parse_llm_response(response)
            
            if llm_mappings:
                # 应用LLM建议的映射
                for standard, variants in llm_mappings.items():
                    for variant in variants:
                        if variant.lower() in all_entities:
                            standardized_entities[variant.lower()] = standard.lower()
                
                logger.info(f"LLM辅助标准化应用了 {len(llm_mappings)} 个额外映射")
            
        except Exception as e:
            logger.warning(f"LLM辅助实体标准化失败: {str(e)}")
        
        return standardized_entities
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, List[str]]]:
        """解析LLM响应
        
        Args:
            response: LLM响应
            
        Returns:
            解析的映射字典或None
        """
        try:
            import json
            
            # 尝试从响应中提取JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            
        except Exception as e:
            logger.warning(f"解析LLM响应失败: {str(e)}")
        
        return None
    
    def _apply_standardization(
        self, 
        valid_triples: List[Dict[str, Any]], 
        standardized_entities: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """应用标准化到三元组
        
        Args:
            valid_triples: 有效三元组列表
            standardized_entities: 标准化映射
            
        Returns:
            标准化后的三元组列表
        """
        standardized_triples = []
        
        for triple in valid_triples:
            subj_lower = triple["subject"].lower()
            obj_lower = triple["object"].lower()
            
            standardized_triple = {
                "subject": standardized_entities.get(subj_lower, triple["subject"]),
                "predicate": self._limit_predicate_length(triple["predicate"]),
                "object": standardized_entities.get(obj_lower, triple["object"]),
                "chunk": triple.get("chunk", 0)
            }
            
            # 保留其他元数据
            for key, value in triple.items():
                if key not in ["subject", "predicate", "object", "chunk"]:
                    standardized_triple[key] = value
            
            standardized_triples.append(standardized_triple)
        
        return standardized_triples
    
    def _limit_predicate_length(self, predicate: str, max_words: int = 3) -> str:
        """限制谓词长度
        
        Args:
            predicate: 原始谓词
            max_words: 最大词数
            
        Returns:
            限制长度后的谓词
        """
        words = predicate.split()
        if len(words) <= max_words:
            return predicate
        
        # 如果太长，只使用前max_words个词
        shortened = ' '.join(words[:max_words])
        
        # 如果最后一个词是停用词，则移除
        stop_words = {'a', 'an', 'the', 'of', 'with', 'by', 'to', 'from', 'in', 'on', 'for'}
        if len(words) > 1:
            last_word = shortened.split()[-1].lower()
            if last_word in stop_words:
                shortened = ' '.join(shortened.split()[:-1])
        
        return shortened 