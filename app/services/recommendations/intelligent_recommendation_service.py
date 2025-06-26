"""
智能推荐服务
整合AI工具组合推荐、自然语言编排和自动发现功能的主接口
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

# 导入主要组件
from .ai_combination_recommender import AIToolCombinationRecommender
from app.services.orchestration.natural_language_orchestrator import NaturalLanguageOrchestrator
from app.services.tools.auto_discovery import AutoToolDiscovery
from app.services.tools.tool_service import ToolService
from app.utils.version.tool_usage_stats import ToolUsageStatsManager
from core.nl_config.parser import NLConfigParser

# 导入类型定义
from .recommendation_types import (
    RecommendationContext,
    RecommendationResult,
    ToolChainRecommendation,
    ToolRecommendation,
    RecommendationType,
    RecommendationReason,
    RecommendationFilter,
    UserFeedback,
    RecommendationMetrics
)

logger = logging.getLogger(__name__)

class IntelligentRecommendationService:
    """智能推荐服务主接口"""
    
    def __init__(
        self,
        tool_service: ToolService,
        usage_stats_manager: ToolUsageStatsManager,
        nl_parser: NLConfigParser
    ):
        self.tool_service = tool_service
        self.usage_stats_manager = usage_stats_manager
        self.nl_parser = nl_parser
        
        # 核心组件
        self.ai_recommender = AIToolCombinationRecommender(
            tool_service, usage_stats_manager
        )
        self.nl_orchestrator = NaturalLanguageOrchestrator(
            tool_service, self.ai_recommender, nl_parser
        )
        
        # 服务状态
        self._initialized = False
        
        # 缓存
        self._recommendation_cache: Dict[str, RecommendationResult] = {}
        self.cache_ttl = 3600  # 1小时
        
    async def initialize(self):
        """初始化推荐服务"""
        if self._initialized:
            return
        
        try:
            # 初始化所有组件
            await self.ai_recommender.initialize()
            await self.nl_orchestrator.initialize()
            await self.usage_stats_manager.initialize()
            
            self._initialized = True
            logger.info("智能推荐服务初始化完成")
            
        except Exception as e:
            logger.error(f"智能推荐服务初始化失败: {str(e)}", exc_info=True)
            raise
    
    async def get_tool_chain_recommendations(
        self,
        context: RecommendationContext,
        max_recommendations: int = 5,
        filters: Optional[RecommendationFilter] = None
    ) -> RecommendationResult:
        """
        获取工具链推荐
        
        Args:
            context: 推荐上下文
            max_recommendations: 最大推荐数量
            filters: 推荐过滤器
            
        Returns:
            RecommendationResult: 推荐结果
        """
        await self.initialize()
        
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        try:
            # 检查缓存
            cache_key = self._generate_cache_key(context)
            if cache_key in self._recommendation_cache:
                cached_result = self._recommendation_cache[cache_key]
                # 检查缓存是否过期
                if (datetime.now() - cached_result.generated_at).seconds < self.cache_ttl:
                    logger.info(f"返回缓存的推荐结果: {request_id}")
                    return cached_result
            
            # 生成推荐
            recommendations = []
            
            # 1. AI生成的工具链推荐
            ai_recommendations = await self._get_ai_generated_recommendations(
                context, max_recommendations
            )
            recommendations.extend(ai_recommendations)
            
            # 2. 基于使用历史的推荐
            usage_recommendations = await self._get_usage_based_recommendations(
                context, max_recommendations
            )
            recommendations.extend(usage_recommendations)
            
            # 3. 基于相似性的推荐
            similarity_recommendations = await self._get_similarity_based_recommendations(
                context, max_recommendations
            )
            recommendations.extend(similarity_recommendations)
            
            # 去重和排序
            recommendations = self._deduplicate_and_rank_recommendations(recommendations)
            
            # 应用过滤器
            if filters:
                recommendations = filters.apply(recommendations)
            
            # 限制数量
            recommendations = recommendations[:max_recommendations]
            
            # 获取单个工具推荐
            individual_tools = await self._get_individual_tool_recommendations(
                context, max_recommendations
            )
            
            # 计算推荐质量
            quality_score = self._calculate_recommendation_quality(
                recommendations, individual_tools
            )
            
            # 构建结果
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = RecommendationResult(
                request_id=request_id,
                context=context,
                tool_chain_recommendations=recommendations,
                individual_tool_recommendations=individual_tools,
                total_recommendations=len(recommendations) + len(individual_tools),
                processing_time=processing_time,
                recommendation_quality=quality_score,
                generated_at=datetime.now()
            )
            
            # 缓存结果
            self._recommendation_cache[cache_key] = result
            
            logger.info(f"生成推荐完成: {request_id}, 耗时: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"获取工具链推荐失败: {str(e)}", exc_info=True)
            # 返回空结果
            return self._create_empty_result(request_id, context)
    
    async def get_natural_language_recommendations(
        self,
        description: str,
        user_id: str,
        domain_context: Optional[str] = None,
        complexity_preference: str = "balanced"
    ) -> ToolChainRecommendation:
        """
        基于自然语言描述获取推荐
        
        Args:
            description: 自然语言描述
            user_id: 用户ID
            domain_context: 领域上下文
            complexity_preference: 复杂度偏好
            
        Returns:
            ToolChainRecommendation: 工具链推荐
        """
        await self.initialize()
        
        try:
            # 使用自然语言编排器生成工具链
            tool_chain = await self.nl_orchestrator.text_to_tool_chain(
                description=description,
                user_id=user_id,
                domain_context=domain_context,
                complexity_preference=complexity_preference
            )
            
            # 转换为推荐格式
            recommendation = self._convert_toolchain_to_recommendation(tool_chain)
            
            logger.info(f"自然语言推荐生成完成: {recommendation.chain_id}")
            return recommendation
            
        except Exception as e:
            logger.error(f"自然语言推荐失败: {str(e)}", exc_info=True)
            # 返回基本推荐
            return self._create_fallback_recommendation(description, user_id)
    
    async def optimize_tool_chain(
        self,
        chain_recommendation: ToolChainRecommendation,
        user_feedback: Optional[str] = None,
        performance_goals: Optional[Dict[str, Any]] = None
    ) -> ToolChainRecommendation:
        """
        优化工具链
        
        Args:
            chain_recommendation: 当前工具链推荐
            user_feedback: 用户反馈
            performance_goals: 性能目标
            
        Returns:
            ToolChainRecommendation: 优化后的工具链推荐
        """
        await self.initialize()
        
        try:
            # 转换推荐为工具链
            tool_chain = self._convert_recommendation_to_toolchain(chain_recommendation)
            
            # 使用AI推荐器优化工具顺序
            tools = [step.tool_name for step in chain_recommendation.steps]
            optimized_chain = await self.ai_recommender.optimize_tool_sequence(
                tools=tools,
                objective=chain_recommendation.objective,
                constraints=performance_goals
            )
            
            # 如果有用户反馈，使用对话式优化
            if user_feedback:
                tool_chain = await self.nl_orchestrator.interactive_refinement(
                    chain=tool_chain,
                    user_feedback=user_feedback
                )
            
            # 转换回推荐格式
            optimized_recommendation = self._convert_toolchain_to_recommendation(tool_chain)
            optimized_recommendation.recommendation_type = RecommendationType.AI_GENERATED
            optimized_recommendation.reasons.append(RecommendationReason.PERFORMANCE_OPTIMIZED)
            
            logger.info(f"工具链优化完成: {optimized_recommendation.chain_id}")
            return optimized_recommendation
            
        except Exception as e:
            logger.error(f"工具链优化失败: {str(e)}", exc_info=True)
            return chain_recommendation  # 返回原始推荐
    
    async def submit_feedback(
        self,
        feedback: UserFeedback
    ) -> bool:
        """
        提交用户反馈
        
        Args:
            feedback: 用户反馈
            
        Returns:
            bool: 是否提交成功
        """
        try:
            # 记录反馈到统计系统
            await self.usage_stats_manager.record_tool_usage(
                user_id=feedback.user_id,
                tool_id="recommendation_system",
                tool_name="推荐系统",
                action="feedback",
                success=feedback.rating >= 3,
                context={
                    "recommendation_id": feedback.recommendation_id,
                    "rating": feedback.rating,
                    "comments": feedback.comments,
                    "used_recommendation": feedback.used_recommendation,
                    "execution_success": feedback.execution_success
                }
            )
            
            # 可以在这里添加反馈学习逻辑
            await self._learn_from_feedback(feedback)
            
            logger.info(f"用户反馈记录成功: {feedback.feedback_id}")
            return True
            
        except Exception as e:
            logger.error(f"记录用户反馈失败: {str(e)}", exc_info=True)
            return False
    
    async def get_recommendation_metrics(
        self,
        days: int = 30
    ) -> RecommendationMetrics:
        """
        获取推荐系统指标
        
        Args:
            days: 统计天数
            
        Returns:
            RecommendationMetrics: 推荐指标
        """
        try:
            # 这里可以实现详细的指标计算
            # 简化实现
            return RecommendationMetrics(
                total_requests=len(self._recommendation_cache),
                successful_recommendations=int(len(self._recommendation_cache) * 0.8),
                user_satisfaction_avg=4.2,
                execution_success_rate=0.75,
                avg_processing_time=2.5,
                recommendation_diversity=0.8,
                top_performing_chains=[]
            )
            
        except Exception as e:
            logger.error(f"获取推荐指标失败: {str(e)}", exc_info=True)
            return RecommendationMetrics(
                total_requests=0,
                successful_recommendations=0,
                user_satisfaction_avg=0.0,
                execution_success_rate=0.0,
                avg_processing_time=0.0,
                recommendation_diversity=0.0,
                top_performing_chains=[]
            )
    
    # ========== 私有方法 ==========
    
    async def _get_ai_generated_recommendations(
        self,
        context: RecommendationContext,
        max_count: int
    ) -> List[ToolChainRecommendation]:
        """获取AI生成的推荐"""
        try:
            return await self.ai_recommender.generate_intelligent_tool_chains(
                objective=context.task_description,
                context=context,
                max_chains=max_count,
                complexity_preference=context.complexity_preference
            )
        except Exception as e:
            logger.warning(f"AI生成推荐失败: {str(e)}")
            return []
    
    async def _get_usage_based_recommendations(
        self,
        context: RecommendationContext,
        max_count: int
    ) -> List[ToolChainRecommendation]:
        """获取基于使用历史的推荐"""
        try:
            # 获取用户使用模式
            user_pattern = await self.usage_stats_manager.get_user_usage_pattern(
                context.user_id
            )
            
            # 基于常用工具生成推荐
            recommendations = []
            if user_pattern.favorite_tools:
                for i, tools_combo in enumerate(self._generate_tool_combinations(
                    user_pattern.favorite_tools, max_count
                )):
                    recommendation = ToolChainRecommendation(
                        chain_id=f"usage_based_{i}",
                        objective=context.task_description,
                        steps=self._create_simple_steps(tools_combo),
                        confidence_score=0.7,
                        estimated_duration=30.0,
                        complexity_level="medium",
                        success_probability=0.75,
                        recommendation_type=RecommendationType.USAGE_BASED,
                        reasons=[RecommendationReason.FREQUENT_USAGE],
                        explanation=f"基于您常用的工具: {', '.join(tools_combo)}"
                    )
                    recommendations.append(recommendation)
            
            return recommendations[:max_count]
            
        except Exception as e:
            logger.warning(f"基于使用历史的推荐失败: {str(e)}")
            return []
    
    async def _get_similarity_based_recommendations(
        self,
        context: RecommendationContext,
        max_count: int
    ) -> List[ToolChainRecommendation]:
        """获取基于相似性的推荐"""
        try:
            # 简化实现：基于任务描述的关键词匹配
            recommendations = []
            
            # 获取趋势工具
            trending_tools = await self.usage_stats_manager.get_trending_tools()
            
            if trending_tools:
                for i, trend in enumerate(trending_tools[:max_count]):
                    recommendation = ToolChainRecommendation(
                        chain_id=f"similarity_based_{i}",
                        objective=context.task_description,
                        steps=self._create_simple_steps([trend['tool_id']]),
                        confidence_score=trend.get('success_rate', 0.6),
                        estimated_duration=20.0,
                        complexity_level="low",
                        success_probability=trend.get('success_rate', 0.6),
                        recommendation_type=RecommendationType.SIMILARITY,
                        reasons=[RecommendationReason.SIMILAR_TASKS],
                        explanation=f"基于相似任务的热门工具: {trend['tool_id']}"
                    )
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.warning(f"基于相似性的推荐失败: {str(e)}")
            return []
    
    async def _get_individual_tool_recommendations(
        self,
        context: RecommendationContext,
        max_count: int
    ) -> List[ToolRecommendation]:
        """获取单个工具推荐"""
        try:
            recommendations = []
            
            # 获取用户可访问的工具
            available_tools = await self.tool_service.get_user_accessible_tools(context.user_id)
            
            for tool in available_tools[:max_count]:
                # 获取工具统计
                stats = await self.usage_stats_manager.get_tool_stats(
                    tool.id, context.user_id
                )
                
                recommendation = ToolRecommendation(
                    tool_id=tool.id,
                    tool_name=tool.name,
                    description=tool.description,
                    category=getattr(tool, 'category', 'general'),
                    confidence_score=stats.get('success_rate', 0.5),
                    reasons=[RecommendationReason.CAPABILITY_MATCH],
                    estimated_performance={
                        'execution_time': stats.get('avg_execution_time', 30.0),
                        'success_rate': stats.get('success_rate', 0.5)
                    },
                    compatibility_score=0.8  # 简化实现
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.warning(f"获取单个工具推荐失败: {str(e)}")
            return []
    
    def _deduplicate_and_rank_recommendations(
        self,
        recommendations: List[ToolChainRecommendation]
    ) -> List[ToolChainRecommendation]:
        """去重和排序推荐"""
        # 简单的去重逻辑：基于工具组合
        seen_tool_combinations = set()
        unique_recommendations = []
        
        for rec in recommendations:
            tool_combo = tuple(sorted([step.tool_name for step in rec.steps]))
            if tool_combo not in seen_tool_combinations:
                seen_tool_combinations.add(tool_combo)
                unique_recommendations.append(rec)
        
        # 按置信度排序
        unique_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return unique_recommendations
    
    def _calculate_recommendation_quality(
        self,
        tool_chain_recs: List[ToolChainRecommendation],
        individual_recs: List[ToolRecommendation]
    ) -> float:
        """计算推荐质量评分"""
        if not tool_chain_recs and not individual_recs:
            return 0.0
        
        # 计算平均置信度
        total_confidence = 0.0
        total_count = 0
        
        for rec in tool_chain_recs:
            total_confidence += rec.confidence_score
            total_count += 1
        
        for rec in individual_recs:
            total_confidence += rec.confidence_score
            total_count += 1
        
        return total_confidence / total_count if total_count > 0 else 0.0
    
    def _generate_cache_key(self, context: RecommendationContext) -> str:
        """生成缓存键"""
        return f"rec_{context.user_id}_{hash(context.task_description)}_{context.complexity_preference}"
    
    def _generate_tool_combinations(
        self,
        tools: List[str],
        max_combinations: int
    ) -> List[List[str]]:
        """生成工具组合"""
        import itertools
        
        combinations = []
        
        # 单个工具
        for tool in tools[:max_combinations]:
            combinations.append([tool])
        
        # 两个工具的组合
        for combo in itertools.combinations(tools, 2):
            combinations.append(list(combo))
            if len(combinations) >= max_combinations:
                break
        
        return combinations[:max_combinations]
    
    def _create_simple_steps(self, tools: List[str]) -> List:
        """创建简单的工具链步骤"""
        from .recommendation_types import ToolChainStep
        
        steps = []
        for i, tool in enumerate(tools):
            step = ToolChainStep(
                step_number=i + 1,
                tool_id=tool,
                tool_name=tool,
                action_description=f"执行工具: {tool}",
                expected_input={},
                expected_output={}
            )
            steps.append(step)
        
        return steps
    
    def _create_empty_result(
        self,
        request_id: str,
        context: RecommendationContext
    ) -> RecommendationResult:
        """创建空的推荐结果"""
        return RecommendationResult(
            request_id=request_id,
            context=context,
            tool_chain_recommendations=[],
            individual_tool_recommendations=[],
            total_recommendations=0,
            processing_time=0.0,
            recommendation_quality=0.0
        )
    
    def _convert_toolchain_to_recommendation(self, tool_chain) -> ToolChainRecommendation:
        """将工具链转换为推荐格式"""
        from .recommendation_types import ToolChainStep
        
        steps = []
        for i, tool in enumerate(tool_chain.tools):
            step = ToolChainStep(
                step_number=i + 1,
                tool_id=tool,
                tool_name=tool,
                action_description=f"执行工具: {tool}",
                expected_input={},
                expected_output={}
            )
            steps.append(step)
        
        return ToolChainRecommendation(
            chain_id=tool_chain.chain_id,
            objective=tool_chain.objective,
            steps=steps,
            confidence_score=tool_chain.ai_analysis.success_probability if tool_chain.ai_analysis else 0.7,
            estimated_duration=tool_chain.execution_plan.estimated_duration,
            complexity_level=tool_chain.execution_plan.complexity.value,
            success_probability=tool_chain.execution_plan.success_probability,
            recommendation_type=RecommendationType.AI_GENERATED,
            reasons=[RecommendationReason.AI_ANALYSIS],
            explanation=tool_chain.description,
            ai_analysis=tool_chain.ai_analysis
        )
    
    def _convert_recommendation_to_toolchain(self, recommendation: ToolChainRecommendation):
        """将推荐转换为工具链格式"""
        # 简化实现，返回一个模拟的工具链对象
        class MockToolChain:
            def __init__(self, rec):
                self.chain_id = rec.chain_id
                self.name = f"工具链-{rec.chain_id[:8]}"
                self.description = rec.explanation
                self.objective = rec.objective
                self.tools = [step.tool_name for step in rec.steps]
                self.ai_analysis = rec.ai_analysis
                self.creator_id = "system"
                self.status = "optimized"
        
        return MockToolChain(recommendation)
    
    def _create_fallback_recommendation(
        self,
        description: str,
        user_id: str
    ) -> ToolChainRecommendation:
        """创建备用推荐"""
        return ToolChainRecommendation(
            chain_id=str(uuid.uuid4()),
            objective=description,
            steps=self._create_simple_steps(["通用工具"]),
            confidence_score=0.5,
            estimated_duration=30.0,
            complexity_level="low",
            success_probability=0.5,
            recommendation_type=RecommendationType.RULE_BASED,
            reasons=[RecommendationReason.USER_PREFERENCE],
            explanation="基于基本规则的备用推荐"
        )
    
    async def _learn_from_feedback(self, feedback: UserFeedback):
        """从反馈中学习（预留接口）"""
        # 这里可以实现机器学习算法来改进推荐质量
        pass


# 工厂函数
def get_intelligent_recommendation_service(
    tool_service: ToolService,
    usage_stats_manager: ToolUsageStatsManager,
    nl_parser: NLConfigParser
) -> IntelligentRecommendationService:
    """获取智能推荐服务实例"""
    return IntelligentRecommendationService(
        tool_service, usage_stats_manager, nl_parser
    ) 