"""
智能搜索策略选择器
自动评估引擎能力并选择最优搜索策略
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class SearchStrategy(str, Enum):
    """搜索策略类型"""
    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    FALLBACK = "fallback"


class EngineStatus(str, Enum):
    """引擎状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class EngineCapabilityAssessment:
    """引擎能力评估结果"""
    engine_name: str
    status: EngineStatus
    response_time_ms: float
    success_rate: float
    throughput_qps: float
    accuracy_score: float
    last_assessment: float
    
    # 详细指标
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    error_rate: float = 0.0
    connection_count: int = 0
    
    def overall_score(self) -> float:
        """计算综合评分"""
        # 权重配置
        weights = {
            'response_time': 0.3,
            'success_rate': 0.3,
            'throughput': 0.2,
            'accuracy': 0.2
        }
        
        # 归一化指标 (0-1)
        normalized_response_time = max(0, 1 - (self.response_time_ms / 1000))  # 1秒以内为满分
        normalized_success_rate = self.success_rate
        normalized_throughput = min(1, self.throughput_qps / 100)  # 100 QPS为满分
        normalized_accuracy = self.accuracy_score
        
        score = (
            weights['response_time'] * normalized_response_time +
            weights['success_rate'] * normalized_success_rate +
            weights['throughput'] * normalized_throughput +
            weights['accuracy'] * normalized_accuracy
        )
        
        return score


@dataclass
class QueryCharacteristics:
    """查询特征"""
    query_text: str
    query_length: int
    has_keywords: bool
    is_semantic_query: bool
    language: str = "zh"
    complexity_score: float = 0.0
    
    @classmethod
    def analyze(cls, query: str) -> 'QueryCharacteristics':
        """分析查询特征"""
        query_length = len(query.strip())
        
        # 简单的关键词检测
        has_keywords = any(char in query for char in ['AND', 'OR', 'NOT', '+', '-', '"'])
        
        # 语义查询检测（长度、自然语言特征等）
        is_semantic_query = query_length > 10 and not has_keywords
        
        # 复杂度评分
        complexity_score = min(1.0, query_length / 100)
        
        return cls(
            query_text=query,
            query_length=query_length,
            has_keywords=has_keywords,
            is_semantic_query=is_semantic_query,
            complexity_score=complexity_score
        )


class SearchStrategySelector:
    """智能搜索策略选择器"""
    
    def __init__(self):
        """初始化策略选择器"""
        self.engine_assessments: Dict[str, EngineCapabilityAssessment] = {}
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.strategy_performance: Dict[SearchStrategy, deque] = defaultdict(lambda: deque(maxlen=50))
        
        # 配置参数
        self.assessment_interval = 300  # 5分钟评估一次
        self.min_assessment_samples = 10
        self.degraded_threshold = 0.6
        self.unavailable_threshold = 0.3
        
        # 策略选择规则
        self.strategy_rules = {
            'vector_threshold': 0.7,
            'keyword_threshold': 0.7,
            'hybrid_threshold': 0.8,
            'fallback_on_failure': True
        }
        
        self._assessment_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> None:
        """初始化选择器"""
        try:
            # 启动定期评估任务
            self._running = True
            self._assessment_task = asyncio.create_task(self._periodic_assessment())
            
            # 初始评估
            await self.assess_all_engines()
            
            logger.info("搜索策略选择器初始化成功")
            
        except Exception as e:
            logger.error(f"搜索策略选择器初始化失败: {str(e)}")
            raise
    
    async def assess_engine_capability(self, engine_name: str, test_queries: List[str] = None) -> EngineCapabilityAssessment:
        """评估单个引擎能力"""
        if not test_queries:
            test_queries = [
                "测试查询",
                "人工智能的发展历史",
                "机器学习算法比较",
                "深度学习应用场景",
                "自然语言处理技术"
            ]
        
        start_time = time.time()
        response_times = []
        success_count = 0
        total_queries = len(test_queries)
        
        try:
            # 并发测试查询
            tasks = []
            for query in test_queries:
                task = self._test_query_performance(engine_name, query)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            for result in results:
                if isinstance(result, dict) and result.get('success'):
                    success_count += 1
                    response_times.append(result['response_time'])
                elif isinstance(result, Exception):
                    logger.warning(f"查询测试失败: {str(result)}")
            
            # 计算指标
            success_rate = success_count / total_queries
            avg_response_time = statistics.mean(response_times) if response_times else float('inf')
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else avg_response_time
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else avg_response_time
            
            # 估算吞吐量 (简化计算)
            throughput_qps = 1000 / avg_response_time if avg_response_time > 0 else 0
            
            # 确定状态
            overall_score = self._calculate_health_score(success_rate, avg_response_time, throughput_qps)
            
            if overall_score >= self.strategy_rules['hybrid_threshold']:
                status = EngineStatus.HEALTHY
            elif overall_score >= self.degraded_threshold:
                status = EngineStatus.DEGRADED
            elif overall_score >= self.unavailable_threshold:
                status = EngineStatus.UNAVAILABLE
            else:
                status = EngineStatus.UNKNOWN
            
            assessment = EngineCapabilityAssessment(
                engine_name=engine_name,
                status=status,
                response_time_ms=avg_response_time,
                success_rate=success_rate,
                throughput_qps=throughput_qps,
                accuracy_score=success_rate,  # 简化：使用成功率作为准确率
                last_assessment=time.time(),
                avg_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                error_rate=1 - success_rate
            )
            
            self.engine_assessments[engine_name] = assessment
            
            logger.info(
                f"引擎 {engine_name} 评估完成: "
                f"状态={status.value}, 成功率={success_rate:.2f}, "
                f"平均响应时间={avg_response_time:.2f}ms"
            )
            
            return assessment
            
        except Exception as e:
            logger.error(f"评估引擎 {engine_name} 时出错: {str(e)}")
            # 返回失败状态的评估
            return EngineCapabilityAssessment(
                engine_name=engine_name,
                status=EngineStatus.UNAVAILABLE,
                response_time_ms=float('inf'),
                success_rate=0.0,
                throughput_qps=0.0,
                accuracy_score=0.0,
                last_assessment=time.time()
            )
    
    async def _test_query_performance(self, engine_name: str, query: str) -> Dict[str, Any]:
        """测试查询性能"""
        start_time = time.time()
        
        try:
            # 这里需要根据实际引擎进行测试
            # 模拟不同引擎的测试逻辑
            if engine_name == "elasticsearch":
                await self._test_elasticsearch_query(query)
            elif engine_name == "milvus":
                await self._test_milvus_query(query)
            elif engine_name == "pgvector":
                await self._test_pgvector_query(query)
            else:
                # 模拟测试
                await asyncio.sleep(0.1)
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'success': True,
                'response_time': response_time,
                'engine': engine_name,
                'query': query
            }
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"引擎 {engine_name} 查询测试失败: {str(e)}")
            
            return {
                'success': False,
                'response_time': response_time,
                'engine': engine_name,
                'query': query,
                'error': str(e)
            }
    
    async def _test_elasticsearch_query(self, query: str) -> None:
        """测试 Elasticsearch 查询"""
        try:
            from app.utils.storage.elasticsearch_adapter import ElasticsearchVectorStore
            # 这里实现实际的ES测试逻辑
            pass
        except ImportError:
            # 模拟测试
            await asyncio.sleep(0.05)
    
    async def _test_milvus_query(self, query: str) -> None:
        """测试 Milvus 查询"""
        try:
            # 这里实现实际的Milvus测试逻辑
            pass
        except ImportError:
            # 模拟测试
            await asyncio.sleep(0.08)
    
    async def _test_pgvector_query(self, query: str) -> None:
        """测试 pgvector 查询"""
        try:
            # 这里实现实际的pgvector测试逻辑
            pass
        except ImportError:
            # 模拟测试
            await asyncio.sleep(0.12)
    
    def _calculate_health_score(self, success_rate: float, response_time: float, throughput: float) -> float:
        """计算引擎健康评分"""
        # 权重
        weights = {'success_rate': 0.5, 'response_time': 0.3, 'throughput': 0.2}
        
        # 归一化
        norm_success_rate = success_rate
        norm_response_time = max(0, 1 - (response_time / 1000))  # 1秒以内为满分
        norm_throughput = min(1, throughput / 100)  # 100 QPS为满分
        
        score = (
            weights['success_rate'] * norm_success_rate +
            weights['response_time'] * norm_response_time +
            weights['throughput'] * norm_throughput
        )
        
        return score
    
    async def assess_all_engines(self) -> Dict[str, EngineCapabilityAssessment]:
        """评估所有可用引擎"""
        engine_names = ["elasticsearch", "milvus", "pgvector"]
        
        tasks = []
        for engine_name in engine_names:
            task = self.assess_engine_capability(engine_name)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assessments = {}
        for i, result in enumerate(results):
            engine_name = engine_names[i]
            if isinstance(result, EngineCapabilityAssessment):
                assessments[engine_name] = result
            else:
                logger.error(f"评估引擎 {engine_name} 失败: {str(result)}")
        
        return assessments
    
    async def select_optimal_strategy(
        self, 
        query: str, 
        knowledge_base_id: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Tuple[SearchStrategy, Dict[str, Any]]:
        """
        选择最优搜索策略
        
        Args:
            query: 查询文本
            knowledge_base_id: 知识库ID
            user_preferences: 用户偏好设置
            
        Returns:
            (策略类型, 策略参数)
        """
        try:
            # 分析查询特征
            query_chars = QueryCharacteristics.analyze(query)
            
            # 获取可用引擎
            available_engines = await self._get_available_engines()
            
            if not available_engines:
                logger.warning("没有可用的搜索引擎，使用回退策略")
                return SearchStrategy.FALLBACK, {'reason': 'no_engines_available'}
            
            # 基于查询特征和引擎能力选择策略
            strategy, params = await self._select_strategy_by_analysis(
                query_chars, available_engines, user_preferences
            )
            
            # 记录策略选择
            self._record_strategy_selection(strategy, query_chars, available_engines)
            
            return strategy, params
            
        except Exception as e:
            logger.error(f"策略选择失败: {str(e)}")
            return SearchStrategy.FALLBACK, {'reason': 'selection_error', 'error': str(e)}
    
    async def _get_available_engines(self) -> List[str]:
        """获取当前可用的引擎列表"""
        available_engines = []
        
        for engine_name, assessment in self.engine_assessments.items():
            if assessment.status in [EngineStatus.HEALTHY, EngineStatus.DEGRADED]:
                available_engines.append(engine_name)
        
        return available_engines
    
    async def _select_strategy_by_analysis(
        self, 
        query_chars: QueryCharacteristics,
        available_engines: List[str],
        user_preferences: Optional[Dict[str, Any]]
    ) -> Tuple[SearchStrategy, Dict[str, Any]]:
        """基于分析结果选择策略"""
        
        # 用户偏好权重
        user_prefs = user_preferences or {}
        prefer_speed = user_prefs.get('prefer_speed', False)
        prefer_accuracy = user_prefs.get('prefer_accuracy', True)
        
        # 检查各引擎的健康状况
        es_available = "elasticsearch" in available_engines
        milvus_available = "milvus" in available_engines
        
        es_assessment = self.engine_assessments.get("elasticsearch")
        milvus_assessment = self.engine_assessments.get("milvus")
        
        # 策略选择逻辑
        if query_chars.has_keywords and es_available:
            # 关键词查询优先使用ES
            if es_assessment and es_assessment.overall_score() >= self.strategy_rules['keyword_threshold']:
                return SearchStrategy.KEYWORD_ONLY, {
                    'engine': 'elasticsearch',
                    'reason': 'keyword_query_detected',
                    'confidence': 0.8
                }
        
        if query_chars.is_semantic_query and milvus_available:
            # 语义查询优先使用向量搜索
            if milvus_assessment and milvus_assessment.overall_score() >= self.strategy_rules['vector_threshold']:
                return SearchStrategy.VECTOR_ONLY, {
                    'engine': 'milvus',
                    'reason': 'semantic_query_detected',
                    'confidence': 0.9
                }
        
        # 混合搜索条件检查
        if es_available and milvus_available:
            if (es_assessment and milvus_assessment and
                es_assessment.overall_score() >= self.strategy_rules['hybrid_threshold'] and
                milvus_assessment.overall_score() >= self.strategy_rules['hybrid_threshold']):
                
                return SearchStrategy.HYBRID, {
                    'primary_engine': 'milvus' if prefer_accuracy else 'elasticsearch',
                    'secondary_engine': 'elasticsearch' if prefer_accuracy else 'milvus',
                    'vector_weight': 0.7 if prefer_accuracy else 0.5,
                    'keyword_weight': 0.3 if prefer_accuracy else 0.5,
                    'reason': 'both_engines_healthy',
                    'confidence': 0.95
                }
        
        # 单引擎回退
        if es_available:
            return SearchStrategy.KEYWORD_ONLY, {
                'engine': 'elasticsearch',
                'reason': 'es_only_available',
                'confidence': 0.6
            }
        elif milvus_available:
            return SearchStrategy.VECTOR_ONLY, {
                'engine': 'milvus',
                'reason': 'milvus_only_available',
                'confidence': 0.6
            }
        
        # 最终回退
        return SearchStrategy.FALLBACK, {
            'reason': 'no_suitable_strategy',
            'confidence': 0.1
        }
    
    def _record_strategy_selection(
        self, 
        strategy: SearchStrategy, 
        query_chars: QueryCharacteristics,
        available_engines: List[str]
    ) -> None:
        """记录策略选择历史"""
        record = {
            'timestamp': time.time(),
            'strategy': strategy.value,
            'query_length': query_chars.query_length,
            'has_keywords': query_chars.has_keywords,
            'is_semantic': query_chars.is_semantic_query,
            'available_engines': available_engines,
            'complexity_score': query_chars.complexity_score
        }
        
        self.performance_history['strategy_selections'].append(record)
    
    async def _periodic_assessment(self) -> None:
        """定期评估任务"""
        while self._running:
            try:
                await asyncio.sleep(self.assessment_interval)
                
                logger.info("开始定期引擎能力评估")
                await self.assess_all_engines()
                
                # 清理过期记录
                self._cleanup_old_records()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定期评估任务出错: {str(e)}")
                await asyncio.sleep(60)  # 出错时等待1分钟
    
    def _cleanup_old_records(self) -> None:
        """清理过期记录"""
        current_time = time.time()
        cutoff_time = current_time - (24 * 3600)  # 保留24小时内的记录
        
        for key in list(self.performance_history.keys()):
            history = self.performance_history[key]
            # 清理24小时前的记录
            while history and history[0].get('timestamp', 0) < cutoff_time:
                history.popleft()
    
    async def get_strategy_recommendations(self, query: str) -> Dict[str, Any]:
        """获取策略推荐分析"""
        query_chars = QueryCharacteristics.analyze(query)
        available_engines = await self._get_available_engines()
        
        recommendations = {
            'query_analysis': {
                'length': query_chars.query_length,
                'has_keywords': query_chars.has_keywords,
                'is_semantic': query_chars.is_semantic_query,
                'complexity': query_chars.complexity_score
            },
            'available_engines': {},
            'recommended_strategies': []
        }
        
        # 引擎状态
        for engine_name in ["elasticsearch", "milvus", "pgvector"]:
            assessment = self.engine_assessments.get(engine_name)
            if assessment:
                recommendations['available_engines'][engine_name] = {
                    'status': assessment.status.value,
                    'score': assessment.overall_score(),
                    'response_time': assessment.response_time_ms,
                    'success_rate': assessment.success_rate
                }
        
        # 策略推荐
        strategy, params = await self._select_strategy_by_analysis(
            query_chars, available_engines, None
        )
        
        recommendations['recommended_strategies'].append({
            'strategy': strategy.value,
            'parameters': params,
            'confidence': params.get('confidence', 0.5)
        })
        
        return recommendations
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = {
            'engine_assessments': {},
            'strategy_distribution': defaultdict(int),
            'total_selections': 0
        }
        
        # 引擎评估统计
        for engine_name, assessment in self.engine_assessments.items():
            stats['engine_assessments'][engine_name] = {
                'status': assessment.status.value,
                'overall_score': assessment.overall_score(),
                'response_time': assessment.response_time_ms,
                'success_rate': assessment.success_rate,
                'throughput': assessment.throughput_qps,
                'last_assessment': assessment.last_assessment
            }
        
        # 策略选择统计
        for record in self.performance_history['strategy_selections']:
            strategy = record['strategy']
            stats['strategy_distribution'][strategy] += 1
            stats['total_selections'] += 1
        
        return stats
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._running = False
        
        if self._assessment_task:
            self._assessment_task.cancel()
            try:
                await self._assessment_task
            except asyncio.CancelledError:
                pass
        
        logger.info("搜索策略选择器清理完成")


# 全局策略选择器实例
_strategy_selector: Optional[SearchStrategySelector] = None


async def get_strategy_selector() -> SearchStrategySelector:
    """获取全局策略选择器实例"""
    global _strategy_selector
    
    if _strategy_selector is None:
        _strategy_selector = SearchStrategySelector()
        await _strategy_selector.initialize()
    
    return _strategy_selector 