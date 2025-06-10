"""
智能工具推荐服务
基于使用统计、用户行为和AI分析提供智能工具推荐
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json

from .recommendation_types import (
    ToolRecommendation, 
    ToolChainRecommendation, 
    RecommendationContext,
    RecommendationResult,
    RecommendationType,
    RecommendationReason,
    ToolChainStep,
    RecommendationMetrics
)

# 引入现有的统计系统
from app.utils.version.tool_usage_stats import ToolUsageStatsManager
from app.utils.version.tool_performance_monitor import ToolPerformanceMonitor
from app.services.tools.tool_service import ToolService

logger = logging.getLogger(__name__)

class IntelligentToolRecommender:
    """智能工具推荐器
    
    结合使用统计、性能监控和用户行为分析提供智能推荐
    """
    
    def __init__(
        self,
        usage_stats_manager: ToolUsageStatsManager,
        performance_monitor: ToolPerformanceMonitor,
        tool_service: ToolService
    ):
        self.usage_stats = usage_stats_manager
        self.performance_monitor = performance_monitor
        self.tool_service = tool_service
        
        # 推荐算法权重配置
        self.weights = {
            'success_rate': 0.3,
            'usage_frequency': 0.2,
            'performance': 0.2,
            'user_preference': 0.15,
            'collaborative': 0.1,
            'recency': 0.05
        }
        
        # 缓存
        self._recommendation_cache = {}
        self._cache_ttl = 300  # 5分钟缓存
        
    async def recommend_for_task(
        self, 
        task_description: str, 
        user_id: str,
        max_recommendations: int = 10
    ) -> List[ToolRecommendation]:
        """基于任务描述推荐最适合的工具
        
        Args:
            task_description: 任务描述
            user_id: 用户ID
            max_recommendations: 最大推荐数量
            
        Returns:
            List[ToolRecommendation]: 推荐的工具列表
        """
        start_time = datetime.now()
        logger.info(f"开始为用户 {user_id} 生成任务推荐: {task_description}")
        
        try:
            # 创建推荐上下文
            context = RecommendationContext(
                user_id=user_id,
                task_description=task_description
            )
            
            # 分析任务关键词
            task_keywords = self._extract_task_keywords(task_description)
            
            # 获取所有可用工具
            available_tools = await self.tool_service.get_all_tools()
            
            # 计算推荐分数
            recommendations = []
            for tool in available_tools:
                score_data = await self._calculate_tool_score(tool, context, task_keywords)
                if score_data['total_score'] > 0.1:  # 过滤低分工具
                    recommendation = ToolRecommendation(
                        tool_id=tool.id,
                        tool_name=tool.name,
                        tool_description=tool.description,
                        confidence_score=score_data['total_score'],
                        recommendation_type=RecommendationType.TASK_BASED,
                        reasons=score_data['reasons'],
                        explanation=score_data['explanation'],
                        expected_performance=score_data['performance_data'],
                        usage_statistics=score_data['usage_data']
                    )
                    recommendations.append(recommendation)
            
            # 按置信度排序并限制数量
            recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
            recommendations = recommendations[:max_recommendations]
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"任务推荐完成，耗时 {processing_time:.2f}ms，推荐 {len(recommendations)} 个工具")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"任务推荐失败: {str(e)}", exc_info=True)
            return []
    
    async def recommend_tool_chain(
        self, 
        objective: str, 
        context: RecommendationContext,
        max_chains: int = 5
    ) -> List[ToolChainRecommendation]:
        """推荐完整的工具链以完成特定目标
        
        Args:
            objective: 目标描述
            context: 推荐上下文
            max_chains: 最大工具链数量
            
        Returns:
            List[ToolChainRecommendation]: 推荐的工具链列表
        """
        start_time = datetime.now()
        logger.info(f"开始生成工具链推荐: {objective}")
        
        try:
            # 分析目标并分解为子任务
            subtasks = self._decompose_objective(objective)
            
            # 为每个子任务推荐工具
            chain_recommendations = []
            
            # 基于历史成功模式生成工具链
            successful_patterns = await self._get_successful_tool_patterns(context.user_id)
            
            for pattern_name, pattern_data in successful_patterns.items():
                if self._pattern_matches_objective(pattern_data, objective):
                    chain = await self._build_tool_chain_from_pattern(
                        pattern_name, pattern_data, objective, context
                    )
                    if chain:
                        chain_recommendations.append(chain)
            
            # 如果没有匹配的模式，生成新的工具链
            if not chain_recommendations:
                generated_chains = await self._generate_tool_chains(subtasks, context)
                chain_recommendations.extend(generated_chains)
            
            # 按置信度排序并限制数量
            chain_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
            chain_recommendations = chain_recommendations[:max_chains]
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"工具链推荐完成，耗时 {processing_time:.2f}ms，推荐 {len(chain_recommendations)} 个工具链")
            
            return chain_recommendations
            
        except Exception as e:
            logger.error(f"工具链推荐失败: {str(e)}", exc_info=True)
            return []
    
    async def recommend_similar_tools(
        self, 
        tool_id: str,
        user_id: str,
        max_recommendations: int = 8
    ) -> List[ToolRecommendation]:
        """推荐功能相似的工具
        
        Args:
            tool_id: 基准工具ID
            user_id: 用户ID
            max_recommendations: 最大推荐数量
            
        Returns:
            List[ToolRecommendation]: 相似工具推荐列表
        """
        try:
            # 获取基准工具信息
            base_tool = await self.tool_service.get_tool_by_id(tool_id)
            if not base_tool:
                return []
            
            # 获取所有工具
            all_tools = await self.tool_service.get_all_tools()
            
            # 计算相似度
            similar_tools = []
            for tool in all_tools:
                if tool.id == tool_id:
                    continue
                    
                similarity_score = await self._calculate_tool_similarity(base_tool, tool)
                if similarity_score > 0.3:  # 相似度阈值
                    # 获取该工具的使用统计
                    usage_data = await self.usage_stats.get_tool_statistics(tool.id)
                    
                    recommendation = ToolRecommendation(
                        tool_id=tool.id,
                        tool_name=tool.name,
                        tool_description=tool.description,
                        confidence_score=similarity_score,
                        recommendation_type=RecommendationType.SIMILAR_TOOLS,
                        reasons=[RecommendationReason.COMPLEMENTARY_TOOLS],
                        explanation=f"与 {base_tool.name} 功能相似的工具",
                        usage_statistics=usage_data
                    )
                    similar_tools.append(recommendation)
            
            # 按相似度排序
            similar_tools.sort(key=lambda x: x.confidence_score, reverse=True)
            return similar_tools[:max_recommendations]
            
        except Exception as e:
            logger.error(f"相似工具推荐失败: {str(e)}", exc_info=True)
            return []
    
    async def get_personalized_recommendations(
        self,
        user_id: str,
        max_recommendations: int = 15
    ) -> RecommendationResult:
        """获取个性化推荐
        
        Args:
            user_id: 用户ID
            max_recommendations: 最大推荐数量
            
        Returns:
            RecommendationResult: 完整推荐结果
        """
        start_time = datetime.now()
        
        try:
            # 创建上下文
            context = RecommendationContext(user_id=user_id)
            
            # 获取用户历史行为
            user_history = await self.usage_stats.get_user_usage_history(user_id)
            
            # 基于用户偏好的工具推荐
            preference_recommendations = await self._recommend_by_user_preference(user_id)
            
            # 协同过滤推荐
            collaborative_recommendations = await self._recommend_by_collaborative_filtering(user_id)
            
            # 趋势推荐（最近流行的工具）
            trending_recommendations = await self._recommend_trending_tools(user_id)
            
            # 合并和去重
            all_tool_recommendations = []
            seen_tool_ids = set()
            
            for rec_list in [preference_recommendations, collaborative_recommendations, trending_recommendations]:
                for rec in rec_list:
                    if rec.tool_id not in seen_tool_ids:
                        all_tool_recommendations.append(rec)
                        seen_tool_ids.add(rec.tool_id)
            
            # 按置信度排序
            all_tool_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
            final_tool_recommendations = all_tool_recommendations[:max_recommendations]
            
            # 生成工具链推荐
            chain_recommendations = await self._recommend_popular_tool_chains(user_id, 5)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return RecommendationResult(
                tool_recommendations=final_tool_recommendations,
                chain_recommendations=chain_recommendations,
                context=context,
                timestamp=datetime.now(),
                total_recommendations=len(final_tool_recommendations) + len(chain_recommendations),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"个性化推荐失败: {str(e)}", exc_info=True)
            return RecommendationResult(
                tool_recommendations=[],
                chain_recommendations=[],
                context=RecommendationContext(user_id=user_id),
                timestamp=datetime.now(),
                total_recommendations=0,
                processing_time_ms=0
            )
    
    # 私有方法
    
    def _extract_task_keywords(self, task_description: str) -> List[str]:
        """从任务描述中提取关键词"""
        # 简单的关键词提取（生产环境可以使用更高级的NLP技术）
        keywords = []
        
        # 预定义的关键词映射
        keyword_mapping = {
            '搜索': ['search', 'find', 'query', '查找', '检索'],
            '分析': ['analyze', 'analysis', '分析', '解析'],
            '处理': ['process', 'handle', '处理', '执行'],
            '生成': ['generate', 'create', '生成', '创建'],
            '转换': ['convert', 'transform', '转换', '变换'],
            '文档': ['document', 'file', '文档', '文件'],
            '数据': ['data', '数据'],
            '图像': ['image', 'picture', '图像', '图片'],
            '文本': ['text', 'content', '文本', '内容']
        }
        
        task_lower = task_description.lower()
        for category, terms in keyword_mapping.items():
            if any(term in task_lower for term in terms):
                keywords.append(category)
        
        return keywords
    
    async def _calculate_tool_score(
        self, 
        tool: Any, 
        context: RecommendationContext, 
        task_keywords: List[str]
    ) -> Dict[str, Any]:
        """计算工具推荐分数"""
        try:
            # 获取工具统计数据
            tool_stats = await self.usage_stats.get_tool_statistics(tool.id)
            performance_data = await self.performance_monitor.get_tool_metrics(tool.id)
            
            # 计算各项分数
            scores = {}
            reasons = []
            
            # 1. 成功率分数
            success_rate = tool_stats.get('success_rate', 0.5)
            scores['success_rate'] = success_rate * self.weights['success_rate']
            if success_rate > 0.8:
                reasons.append(RecommendationReason.HIGH_SUCCESS_RATE)
            
            # 2. 使用频率分数
            usage_count = tool_stats.get('total_usage', 0)
            frequency_score = min(usage_count / 100, 1.0)  # 归一化到0-1
            scores['frequency'] = frequency_score * self.weights['usage_frequency']
            if usage_count > 50:
                reasons.append(RecommendationReason.FREQUENTLY_USED)
            
            # 3. 性能分数
            avg_response_time = performance_data.get('avg_response_time', 5000)
            performance_score = max(0, 1 - (avg_response_time / 10000))  # 10秒为基准
            scores['performance'] = performance_score * self.weights['performance']
            if performance_score > 0.8:
                reasons.append(RecommendationReason.PERFORMANCE_OPTIMIZED)
            
            # 4. 任务匹配分数
            task_match_score = self._calculate_task_match_score(tool, task_keywords)
            scores['task_match'] = task_match_score * 0.25  # 临时权重
            if task_match_score > 0.7:
                reasons.append(RecommendationReason.TASK_PATTERN)
            
            # 5. 用户偏好分数（基于历史使用）
            user_preference_score = await self._calculate_user_preference_score(tool.id, context.user_id)
            scores['user_preference'] = user_preference_score * self.weights['user_preference']
            
            # 总分计算
            total_score = sum(scores.values())
            
            # 生成解释
            explanation = self._generate_recommendation_explanation(tool, scores, reasons)
            
            return {
                'total_score': total_score,
                'scores': scores,
                'reasons': reasons,
                'explanation': explanation,
                'performance_data': performance_data,
                'usage_data': tool_stats
            }
            
        except Exception as e:
            logger.error(f"计算工具分数失败 {tool.id}: {str(e)}")
            return {
                'total_score': 0.0,
                'scores': {},
                'reasons': [],
                'explanation': '分数计算失败',
                'performance_data': {},
                'usage_data': {}
            }
    
    def _calculate_task_match_score(self, tool: Any, task_keywords: List[str]) -> float:
        """计算工具与任务的匹配度"""
        if not task_keywords:
            return 0.5  # 默认分数
        
        # 简单的关键词匹配
        tool_text = f"{tool.name} {tool.description} {getattr(tool, 'category', '')}".lower()
        
        matches = 0
        for keyword in task_keywords:
            if keyword.lower() in tool_text:
                matches += 1
        
        return matches / len(task_keywords) if task_keywords else 0
    
    async def _calculate_user_preference_score(self, tool_id: str, user_id: str) -> float:
        """计算用户对工具的偏好分数"""
        try:
            # 获取用户使用历史
            user_history = await self.usage_stats.get_user_usage_history(user_id)
            
            # 计算该用户对此工具的使用频率
            tool_usage = user_history.get(tool_id, {})
            usage_count = tool_usage.get('count', 0)
            
            # 归一化分数
            if usage_count == 0:
                return 0.0
            elif usage_count <= 5:
                return 0.3
            elif usage_count <= 15:
                return 0.6
            else:
                return 0.9
                
        except Exception as e:
            logger.error(f"计算用户偏好分数失败: {str(e)}")
            return 0.0
    
    def _generate_recommendation_explanation(self, tool: Any, scores: Dict, reasons: List) -> str:
        """生成推荐解释"""
        explanations = []
        
        if RecommendationReason.HIGH_SUCCESS_RATE in reasons:
            explanations.append("具有较高的成功率")
        if RecommendationReason.FREQUENTLY_USED in reasons:
            explanations.append("被频繁使用")
        if RecommendationReason.PERFORMANCE_OPTIMIZED in reasons:
            explanations.append("性能表现优秀")
        if RecommendationReason.TASK_PATTERN in reasons:
            explanations.append("与您的任务高度匹配")
        
        if not explanations:
            explanations.append("综合评分较高")
        
        return f"推荐 {tool.name}，因为它" + "、".join(explanations)
    
    async def _recommend_by_user_preference(self, user_id: str) -> List[ToolRecommendation]:
        """基于用户偏好推荐"""
        # 实现基于用户历史偏好的推荐算法
        # 这里是简化实现
        return []
    
    async def _recommend_by_collaborative_filtering(self, user_id: str) -> List[ToolRecommendation]:
        """协同过滤推荐"""
        # 实现协同过滤算法
        # 这里是简化实现
        return []
    
    async def _recommend_trending_tools(self, user_id: str) -> List[ToolRecommendation]:
        """推荐趋势工具"""
        # 实现趋势分析推荐
        # 这里是简化实现
        return []
    
    # 工具链相关方法
    
    def _decompose_objective(self, objective: str) -> List[str]:
        """分解目标为子任务"""
        # 简化实现，实际可以使用NLP技术
        return [objective]  # 暂时返回原目标
    
    async def _get_successful_tool_patterns(self, user_id: str) -> Dict[str, Any]:
        """获取成功的工具使用模式"""
        # 实现模式挖掘
        return {}
    
    def _pattern_matches_objective(self, pattern_data: Dict, objective: str) -> bool:
        """判断模式是否匹配目标"""
        return False  # 简化实现
    
    async def _build_tool_chain_from_pattern(
        self, pattern_name: str, pattern_data: Dict, objective: str, context: RecommendationContext
    ) -> Optional[ToolChainRecommendation]:
        """从模式构建工具链"""
        return None  # 简化实现
    
    async def _generate_tool_chains(
        self, subtasks: List[str], context: RecommendationContext
    ) -> List[ToolChainRecommendation]:
        """生成新的工具链"""
        return []  # 简化实现
    
    async def _recommend_popular_tool_chains(self, user_id: str, max_chains: int) -> List[ToolChainRecommendation]:
        """推荐流行的工具链"""
        return []  # 简化实现
    
    async def _calculate_tool_similarity(self, tool1: Any, tool2: Any) -> float:
        """计算工具相似度"""
        # 简单的文本相似度计算
        text1 = f"{tool1.name} {tool1.description}".lower()
        text2 = f"{tool2.name} {tool2.description}".lower()
        
        # 简单的共同词汇计算
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0 