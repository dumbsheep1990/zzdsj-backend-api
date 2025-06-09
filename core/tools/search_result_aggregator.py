"""
搜索结果聚合器
专门处理多关键词检索的结果汇总、去重和重排
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math
import re
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """标准化搜索结果"""
    title: str
    url: str
    content: str
    source: str
    published_date: Optional[str] = None
    relevance_score: float = 0.0
    quality_score: float = 0.0
    keywords_matched: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RankingWeights:
    """排序权重配置"""
    relevance_weight: float = 0.4      # 相关性权重
    quality_weight: float = 0.2        # 质量权重
    freshness_weight: float = 0.2      # 新鲜度权重
    source_weight: float = 0.1         # 来源权重
    diversity_weight: float = 0.1      # 多样性权重


class SearchResultAggregator:
    """搜索结果聚合器"""
    
    def __init__(self, ranking_weights: Optional[RankingWeights] = None):
        """初始化聚合器"""
        self.ranking_weights = ranking_weights or RankingWeights()
        self.source_authority_scores = {
            "政府门户": 1.0,
            "省级门户": 0.9,
            "市级门户": 0.8,
            "搜索引擎": 0.6,
            "其他": 0.5
        }
    
    def aggregate_multi_keyword_results(
        self,
        keyword_results: Dict[str, List[SearchResult]],
        max_results: int = 50,
        enable_deduplication: bool = True,
        enable_diversity: bool = True
    ) -> List[SearchResult]:
        """
        聚合多关键词搜索结果
        
        Args:
            keyword_results: 按关键词组织的搜索结果
            max_results: 最大返回结果数
            enable_deduplication: 是否启用去重
            enable_diversity: 是否启用多样性优化
            
        Returns:
            聚合并重排后的结果列表
        """
        try:
            logger.info(f"开始聚合 {len(keyword_results)} 个关键词的搜索结果")
            
            # Step 1: 合并所有结果
            all_results = self._merge_results(keyword_results)
            logger.info(f"合并后总结果数: {len(all_results)}")
            
            # Step 2: 去重
            if enable_deduplication:
                all_results = self._deduplicate_results(all_results)
                logger.info(f"去重后结果数: {len(all_results)}")
            
            # Step 3: 计算综合评分
            all_results = self._calculate_comprehensive_scores(all_results, keyword_results)
            
            # Step 4: 重排序
            all_results = self._rank_results(all_results)
            
            # Step 5: 多样性优化
            if enable_diversity:
                all_results = self._optimize_diversity(all_results, max_results)
            
            # Step 6: 限制结果数量
            final_results = all_results[:max_results]
            
            logger.info(f"最终返回结果数: {len(final_results)}")
            return final_results
            
        except Exception as e:
            logger.error(f"搜索结果聚合失败: {str(e)}")
            # 返回第一个关键词的结果作为兜底
            if keyword_results:
                first_keyword_results = list(keyword_results.values())[0]
                return first_keyword_results[:max_results]
            return []
    
    def _merge_results(self, keyword_results: Dict[str, List[SearchResult]]) -> List[SearchResult]:
        """合并所有关键词的搜索结果"""
        all_results = []
        
        for keyword, results in keyword_results.items():
            for result in results:
                # 为每个结果记录匹配的关键词
                result_copy = SearchResult(
                    title=result.title,
                    url=result.url,
                    content=result.content,
                    source=result.source,
                    published_date=result.published_date,
                    relevance_score=result.relevance_score,
                    quality_score=result.quality_score,
                    keywords_matched=[keyword],
                    metadata=result.metadata.copy()
                )
                all_results.append(result_copy)
        
        return all_results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重搜索结果"""
        url_to_result = {}
        title_fingerprints = {}
        
        for result in results:
            # 基于URL去重
            if result.url in url_to_result:
                # 合并关键词信息
                existing = url_to_result[result.url]
                existing.keywords_matched.extend(result.keywords_matched)
                existing.keywords_matched = list(set(existing.keywords_matched))
                
                # 取更高的相关性评分
                if result.relevance_score > existing.relevance_score:
                    existing.relevance_score = result.relevance_score
                continue
            
            # 基于标题指纹去重
            title_fingerprint = self._generate_title_fingerprint(result.title)
            if title_fingerprint in title_fingerprints:
                # 相似标题，合并信息
                existing = title_fingerprints[title_fingerprint]
                existing.keywords_matched.extend(result.keywords_matched)
                existing.keywords_matched = list(set(existing.keywords_matched))
                continue
            
            url_to_result[result.url] = result
            title_fingerprints[title_fingerprint] = result
        
        return list(url_to_result.values())
    
    def _generate_title_fingerprint(self, title: str) -> str:
        """生成标题指纹用于去重"""
        # 移除标点符号和空格，转为小写
        cleaned = re.sub(r'[^\w]', '', title.lower())
        # 如果标题过长，取前30个字符
        return cleaned[:30]
    
    def _calculate_comprehensive_scores(
        self, 
        results: List[SearchResult], 
        keyword_results: Dict[str, List[SearchResult]]
    ) -> List[SearchResult]:
        """计算综合评分"""
        total_keywords = len(keyword_results)
        
        for result in results:
            # 1. 关键词匹配度评分
            keyword_coverage = len(result.keywords_matched) / total_keywords
            
            # 2. 多关键词相关性提升
            multi_keyword_bonus = min(len(result.keywords_matched) * 0.1, 0.3)
            enhanced_relevance = min(result.relevance_score + multi_keyword_bonus, 1.0)
            
            # 3. 新鲜度评分
            freshness_score = self._calculate_freshness_score(result.published_date)
            
            # 4. 来源权威性评分
            source_score = self._get_source_authority_score(result.source)
            
            # 5. 内容质量评分
            quality_score = result.quality_score or self._estimate_quality_score(result)
            
            # 6. 计算综合评分
            comprehensive_score = (
                enhanced_relevance * self.ranking_weights.relevance_weight +
                quality_score * self.ranking_weights.quality_weight +
                freshness_score * self.ranking_weights.freshness_weight +
                source_score * self.ranking_weights.source_weight +
                keyword_coverage * self.ranking_weights.diversity_weight
            )
            
            # 更新结果的评分信息
            result.relevance_score = enhanced_relevance
            result.quality_score = quality_score
            result.metadata.update({
                "comprehensive_score": comprehensive_score,
                "keyword_coverage": keyword_coverage,
                "freshness_score": freshness_score,
                "source_score": source_score
            })
        
        return results
    
    def _calculate_freshness_score(self, published_date: Optional[str]) -> float:
        """计算新鲜度评分"""
        if not published_date:
            return 0.5  # 默认中等新鲜度
        
        try:
            # 尝试解析日期
            pub_date = self._parse_date(published_date)
            if not pub_date:
                return 0.5
            
            # 计算距今天数
            days_ago = (datetime.now() - pub_date).days
            
            # 新鲜度评分曲线：越新越高分
            if days_ago <= 7:
                return 1.0
            elif days_ago <= 30:
                return 0.8
            elif days_ago <= 90:
                return 0.6
            elif days_ago <= 365:
                return 0.4
            else:
                return 0.2
                
        except Exception:
            return 0.5
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d", 
            "%Y年%m月%d日",
            "%m/%d/%Y",
            "%d/%m/%Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _get_source_authority_score(self, source: str) -> float:
        """获取来源权威性评分"""
        source_lower = source.lower()
        
        # 检查是否为政府门户
        if any(keyword in source_lower for keyword in ["政府", "gov.cn", "人民政府"]):
            if "市" in source_lower:
                return self.source_authority_scores["市级门户"]
            elif "省" in source_lower:
                return self.source_authority_scores["省级门户"]
            else:
                return self.source_authority_scores["政府门户"]
        
        # 检查是否为搜索引擎结果
        if any(keyword in source_lower for keyword in ["搜索", "search", "引擎"]):
            return self.source_authority_scores["搜索引擎"]
        
        return self.source_authority_scores["其他"]
    
    def _estimate_quality_score(self, result: SearchResult) -> float:
        """估算内容质量评分"""
        score = 0.5  # 基础分
        
        # 标题质量
        if len(result.title) > 10 and len(result.title) < 100:
            score += 0.1
        
        # 内容长度
        if len(result.content) > 50:
            score += 0.1
        if len(result.content) > 200:
            score += 0.1
        
        # 是否包含关键信息
        content_lower = result.content.lower()
        if any(keyword in content_lower for keyword in ["政策", "办法", "通知", "规定"]):
            score += 0.1
        
        # 是否有具体信息
        if any(keyword in content_lower for keyword in ["联系", "电话", "地址", "时间"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def _rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """对结果进行重排序"""
        return sorted(
            results, 
            key=lambda x: x.metadata.get("comprehensive_score", 0), 
            reverse=True
        )
    
    def _optimize_diversity(self, results: List[SearchResult], target_count: int) -> List[SearchResult]:
        """优化结果多样性"""
        if len(results) <= target_count:
            return results
        
        diverse_results = []
        used_sources = set()
        used_title_prefixes = set()
        
        # 第一轮：选择高分且多样的结果
        for result in results:
            if len(diverse_results) >= target_count:
                break
            
            # 检查来源多样性
            if result.source not in used_sources or len(used_sources) < 3:
                # 检查标题多样性
                title_prefix = result.title[:10]
                if title_prefix not in used_title_prefixes or len(used_title_prefixes) < target_count // 2:
                    diverse_results.append(result)
                    used_sources.add(result.source)
                    used_title_prefixes.add(title_prefix)
        
        # 第二轮：补充剩余位置
        for result in results:
            if len(diverse_results) >= target_count:
                break
            if result not in diverse_results:
                diverse_results.append(result)
        
        return diverse_results[:target_count]
    
    def create_keyword_specific_aggregator(self, keywords: List[str]) -> Callable:
        """创建针对特定关键词的聚合函数"""
        def keyword_aggregator(results: List[List[SearchResult]]) -> List[SearchResult]:
            # 将结果转换为按关键词组织的字典
            keyword_results = {}
            for i, keyword in enumerate(keywords):
                if i < len(results):
                    keyword_results[keyword] = results[i]
            
            return self.aggregate_multi_keyword_results(keyword_results)
        
        return keyword_aggregator


def create_policy_search_aggregator() -> SearchResultAggregator:
    """创建专用于政策检索的聚合器"""
    # 政策检索专用权重配置
    policy_weights = RankingWeights(
        relevance_weight=0.35,    # 相关性重要但不是唯一因素
        quality_weight=0.25,     # 政策文档质量很重要
        freshness_weight=0.25,   # 政策时效性重要
        source_weight=0.1,       # 来源权威性
        diversity_weight=0.05    # 多样性相对较低
    )
    
    aggregator = SearchResultAggregator(policy_weights)
    
    # 更新政策检索的来源权威性评分
    aggregator.source_authority_scores.update({
        "六盘水市人民政府": 1.0,
        "贵州省人民政府": 0.95,
        "政府门户": 0.9,
        "省级门户": 0.85,
        "市级门户": 0.8,
        "搜索引擎": 0.6
    })
    
    return aggregator 