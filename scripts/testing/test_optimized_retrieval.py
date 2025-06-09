#!/usr/bin/env python3
"""
检索系统优化模块集成测试
测试所有5个优化模块的功能和性能
"""

import asyncio
import logging
import time
import random
import json
from typing import Dict, Any, List
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

# 设置测试环境
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.knowledge.optimization import (
    RetrievalConfigManager,
    SearchStrategySelector,
    DataSyncService,
    EnhancedErrorHandler,
    PerformanceOptimizer,
    CacheConfig,
    CacheStrategy,
    SyncJobConfig,
    SyncOperation,
    CircuitBreakerConfig
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestOptimizedRetrieval(unittest.IsolatedAsyncioTestCase):
    """优化检索系统集成测试"""
    
    async def asyncSetUp(self):
        """测试初始化"""
        logger.info("🚀 开始集成测试初始化")
        
        # 创建临时配置文件
        self.temp_config_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        )
        
        # 写入测试配置
        test_config = """
vector_search:
  top_k: 10
  similarity_threshold: 0.7
  engine: "milvus"
  timeout: 30

keyword_search:
  top_k: 10
  engine: "elasticsearch"
  analyzer: "standard"
  fuzzy_enabled: true

hybrid_search:
  vector_weight: 0.7
  keyword_weight: 0.3
  rrf_k: 60
  top_k: 10

cache:
  enabled: true
  strategy: "lru"
  max_size: 100
  ttl_seconds: 300

performance:
  max_concurrent_requests: 10
  enable_query_optimization: true
  monitoring_enabled: true
"""
        self.temp_config_file.write(test_config)
        self.temp_config_file.close()
        
        # 初始化所有组件
        self.config_manager = RetrievalConfigManager(self.temp_config_file.name)
        await self.config_manager.initialize()
        
        self.strategy_selector = SearchStrategySelector()
        await self.strategy_selector.initialize()
        
        self.sync_service = DataSyncService()
        await self.sync_service.initialize()
        
        self.error_handler = EnhancedErrorHandler()
        
        cache_config = CacheConfig(
            strategy=CacheStrategy.LRU,
            max_size=100,
            ttl_seconds=300
        )
        self.performance_optimizer = PerformanceOptimizer(cache_config)
        
        logger.info("✅ 集成测试初始化完成")
    
    async def asyncTearDown(self):
        """测试清理"""
        logger.info("🧹 开始集成测试清理")
        
        # 清理所有组件
        await self.config_manager.cleanup()
        await self.strategy_selector.cleanup()
        await self.sync_service.cleanup()
        await self.error_handler.cleanup()
        self.performance_optimizer.cleanup()
        
        # 删除临时文件
        if os.path.exists(self.temp_config_file.name):
            os.unlink(self.temp_config_file.name)
        
        logger.info("✅ 集成测试清理完成")
    
    async def test_01_config_manager_functionality(self):
        """测试配置管理器功能"""
        logger.info("🔧 测试配置管理器功能")
        
        # 测试配置获取
        config = self.config_manager.get_config()
        self.assertIsNotNone(config)
        
        vector_config = self.config_manager.get_vector_search_config()
        self.assertEqual(vector_config.top_k, 10)
        self.assertEqual(vector_config.similarity_threshold, 0.7)
        
        # 测试配置验证
        self.assertTrue(self.config_manager.validate_config())
        
        # 测试动态更新
        success = await self.config_manager.update_config({
            "cache": {"max_size": 200}
        })
        self.assertTrue(success)
        
        updated_config = self.config_manager.get_cache_config()
        self.assertEqual(updated_config.max_size, 200)
        
        logger.info("✅ 配置管理器功能测试通过")
    
    async def test_02_strategy_selector_functionality(self):
        """测试策略选择器功能"""
        logger.info("🎯 测试策略选择器功能")
        
        # 测试引擎能力评估
        assessment = await self.strategy_selector.assess_engine_capability("elasticsearch")
        self.assertIsNotNone(assessment)
        self.assertGreaterEqual(assessment.overall_score(), 0)
        
        # 测试策略选择
        strategy, params = await self.strategy_selector.select_optimal_strategy(
            query="人工智能的发展历史",
            knowledge_base_id="test_kb"
        )
        self.assertIsNotNone(strategy)
        self.assertIsNotNone(params)
        
        # 测试策略推荐
        recommendations = await self.strategy_selector.get_strategy_recommendations(
            "机器学习算法"
        )
        self.assertIn('query_analysis', recommendations)
        self.assertIn('recommended_strategies', recommendations)
        
        # 测试性能统计
        stats = self.strategy_selector.get_performance_stats()
        self.assertIn('engine_assessments', stats)
        
        logger.info("✅ 策略选择器功能测试通过")
    
    async def test_03_sync_service_functionality(self):
        """测试数据同步服务功能"""
        logger.info("🔄 测试数据同步服务功能")
        
        # 测试文档分块同步
        job_id = await self.sync_service.sync_document_chunks(
            knowledge_base_id="test_kb",
            document_id="test_doc"
        )
        self.assertIsNotNone(job_id)
        
        # 等待任务完成（简化测试）
        await asyncio.sleep(1)
        
        # 检查任务状态
        result = await self.sync_service.get_job_status(job_id)
        self.assertIsNotNone(result)
        
        # 测试增量同步
        incremental_job_id = await self.sync_service.incremental_sync(
            data_type="document_chunk",
            last_sync_time=time.time() - 3600
        )
        self.assertIsNotNone(incremental_job_id)
        
        # 测试同步统计
        stats = await self.sync_service.get_sync_statistics()
        self.assertIn('active_jobs', stats)
        self.assertIn('total_jobs', stats)
        
        logger.info("✅ 数据同步服务功能测试通过")
    
    async def test_04_error_handler_functionality(self):
        """测试错误处理器功能"""
        logger.info("🛡️ 测试错误处理器功能")
        
        # 测试熔断器创建
        cb = self.error_handler.get_or_create_circuit_breaker("test_cb")
        self.assertIsNotNone(cb)
        
        # 模拟成功请求
        async def success_func():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await cb.call(success_func)
        self.assertEqual(result, "success")
        
        # 模拟失败请求
        async def fail_func():
            raise ValueError("测试错误")
        
        with self.assertRaises(ValueError):
            await cb.call(fail_func)
        
        # 测试错误统计
        stats = self.error_handler.get_error_statistics()
        self.assertIn('global_stats', stats)
        self.assertIn('circuit_breakers', stats)
        
        # 测试健康检查
        health = await self.error_handler.health_check()
        self.assertIn('status', health)
        
        logger.info("✅ 错误处理器功能测试通过")
    
    async def test_05_performance_optimizer_functionality(self):
        """测试性能优化器功能"""
        logger.info("⚡ 测试性能优化器功能")
        
        # 测试缓存功能
        cache_key = self.performance_optimizer._generate_cache_key(
            "test query", {"param": "value"}
        )
        
        # 设置缓存
        await self.performance_optimizer.set_cached_result(cache_key, "test_result")
        
        # 获取缓存
        cached_result = await self.performance_optimizer.get_cached_result(cache_key)
        self.assertEqual(cached_result, "test_result")
        
        # 测试查询优化
        optimized_query = self.performance_optimizer.query_optimizer.optimize_query(
            "   这是一个  测试查询   "
        )
        self.assertEqual(optimized_query.strip(), "这是一个 测试查询")
        
        # 测试优化执行
        async def mock_query_func(query, **kwargs):
            await asyncio.sleep(0.05)  # 模拟查询延迟
            return f"结果for: {query}"
        
        result = await self.performance_optimizer.optimize_and_execute(
            query_func=mock_query_func,
            query="test query",
            parameters={"top_k": 5}
        )
        self.assertIn("test query", result)
        
        # 测试性能统计
        stats = self.performance_optimizer.get_performance_stats()
        self.assertIn('request_metrics', stats)
        self.assertIn('cache_metrics', stats)
        
        logger.info("✅ 性能优化器功能测试通过")
    
    async def test_06_integration_workflow(self):
        """测试完整集成工作流"""
        logger.info("🔗 测试完整集成工作流")
        
        # 模拟完整的搜索请求处理流程
        async def integrated_search(query: str, knowledge_base_id: str = "test_kb"):
            """集成的搜索函数"""
            
            # 1. 策略选择
            strategy, strategy_params = await self.strategy_selector.select_optimal_strategy(
                query=query,
                knowledge_base_id=knowledge_base_id
            )
            
            # 2. 性能优化执行
            async def search_func(optimized_query, **params):
                # 模拟搜索逻辑
                await asyncio.sleep(0.1)
                return {
                    "results": [
                        {"id": f"doc_{i}", "content": f"结果 {i}: {optimized_query}"}
                        for i in range(5)
                    ],
                    "strategy": strategy.value,
                    "params": strategy_params
                }
            
            result = await self.performance_optimizer.optimize_and_execute(
                query_func=search_func,
                query=query,
                parameters={"knowledge_base_id": knowledge_base_id}
            )
            
            return result
        
        # 执行集成搜索
        search_result = await integrated_search("人工智能技术发展")
        
        self.assertIsNotNone(search_result)
        self.assertIn("results", search_result)
        self.assertIn("strategy", search_result)
        self.assertEqual(len(search_result["results"]), 5)
        
        logger.info("✅ 完整集成工作流测试通过")
    
    async def test_07_concurrent_performance(self):
        """测试并发性能"""
        logger.info("🚀 测试并发性能")
        
        async def concurrent_search(query_id: int):
            """并发搜索函数"""
            query = f"测试查询 {query_id}"
            
            async def mock_search(q, **kwargs):
                # 模拟随机延迟
                await asyncio.sleep(random.uniform(0.05, 0.2))
                return f"结果 for {q}"
            
            return await self.performance_optimizer.optimize_and_execute(
                query_func=mock_search,
                query=query
            )
        
        # 创建并发任务
        num_concurrent = 20
        tasks = [
            concurrent_search(i) for i in range(num_concurrent)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 验证结果
        self.assertEqual(len(results), num_concurrent)
        for i, result in enumerate(results):
            self.assertIn(f"测试查询 {i}", result)
        
        # 检查性能
        total_time = end_time - start_time
        self.assertLess(total_time, 5.0)  # 应该在5秒内完成
        
        # 检查性能统计
        stats = self.performance_optimizer.get_performance_stats()
        cache_hit_rate = stats['cache_metrics']['hit_rate']
        
        logger.info(f"并发测试完成: {num_concurrent}个请求, 耗时: {total_time:.2f}s, 缓存命中率: {cache_hit_rate:.2%}")
        logger.info("✅ 并发性能测试通过")
    
    async def test_08_error_recovery(self):
        """测试错误恢复机制"""
        logger.info("🔧 测试错误恢复机制")
        
        # 创建会失败的函数
        failure_count = 0
        
        async def unreliable_function():
            nonlocal failure_count
            failure_count += 1
            
            if failure_count <= 3:
                raise ConnectionError(f"模拟连接错误 {failure_count}")
            else:
                return "最终成功"
        
        # 测试重试机制
        @self.error_handler.retry_on_failure(max_retries=5, base_delay=0.1)
        async def retry_test():
            return await unreliable_function()
        
        result = await retry_test()
        self.assertEqual(result, "最终成功")
        self.assertEqual(failure_count, 4)  # 3次失败 + 1次成功
        
        # 测试熔断器恢复
        cb = self.error_handler.get_or_create_circuit_breaker(
            "recovery_test",
            CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
        )
        
        # 触发熔断器
        for _ in range(3):
            try:
                await cb.call(lambda: exec('raise ValueError("测试失败")'))
            except:
                pass
        
        # 验证熔断器开启
        stats = cb.get_stats()
        self.assertEqual(stats['state'], 'open')
        
        # 等待恢复时间
        await asyncio.sleep(1.1)
        
        # 测试恢复
        await cb.call(lambda: "恢复成功")
        
        logger.info("✅ 错误恢复机制测试通过")
    
    async def test_09_performance_benchmarks(self):
        """性能基准测试"""
        logger.info("📊 执行性能基准测试")
        
        # 基准测试配置
        test_cases = [
            {"queries": 100, "cache_enabled": False, "name": "无缓存"},
            {"queries": 100, "cache_enabled": True, "name": "有缓存"},
        ]
        
        results = {}
        
        for test_case in test_cases:
            # 重置优化器
            cache_config = CacheConfig(
                strategy=CacheStrategy.LRU,
                max_size=1000 if test_case["cache_enabled"] else 0
            )
            optimizer = PerformanceOptimizer(cache_config)
            
            async def benchmark_search(query, **kwargs):
                await asyncio.sleep(0.01)  # 模拟搜索延迟
                return f"结果 for {query}"
            
            # 执行基准测试
            start_time = time.time()
            
            tasks = []
            for i in range(test_case["queries"]):
                query = f"基准测试查询 {i % 10}"  # 重复查询以测试缓存效果
                task = optimizer.optimize_and_execute(
                    query_func=benchmark_search,
                    query=query,
                    use_cache=test_case["cache_enabled"]
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            # 收集统计
            stats = optimizer.get_performance_stats()
            results[test_case["name"]] = {
                "total_time": end_time - start_time,
                "avg_response_time": stats['request_metrics']['avg_response_time'],
                "cache_hit_rate": stats['cache_metrics']['hit_rate'],
                "total_requests": stats['request_metrics']['total_requests']
            }
            
            optimizer.cleanup()
        
        # 验证缓存效果
        cache_result = results["有缓存"]
        no_cache_result = results["无缓存"]
        
        self.assertLess(cache_result["total_time"], no_cache_result["total_time"])
        self.assertGreater(cache_result["cache_hit_rate"], 0.5)  # 缓存命中率应该大于50%
        
        logger.info("基准测试结果:")
        for name, result in results.items():
            logger.info(f"  {name}:")
            logger.info(f"    总时间: {result['total_time']:.2f}s")
            logger.info(f"    平均响应时间: {result['avg_response_time']:.2f}ms")
            logger.info(f"    缓存命中率: {result['cache_hit_rate']:.2%}")
        
        logger.info("✅ 性能基准测试通过")
    
    async def test_10_comprehensive_integration(self):
        """综合集成测试"""
        logger.info("🎯 执行综合集成测试")
        
        # 模拟真实的搜索服务
        class OptimizedSearchService:
            def __init__(self):
                self.config_manager = self.config_manager
                self.strategy_selector = self.strategy_selector
                self.sync_service = self.sync_service
                self.error_handler = self.error_handler
                self.optimizer = self.performance_optimizer
            
            @self.error_handler.circuit_breaker("search_service")
            @self.optimizer.cache_decorator()
            async def search(self, query: str, **params):
                # 选择策略
                strategy, strategy_params = await self.strategy_selector.select_optimal_strategy(
                    query=query
                )
                
                # 模拟搜索
                await asyncio.sleep(0.05)
                
                return {
                    "query": query,
                    "strategy": strategy.value,
                    "results": [
                        {"id": f"result_{i}", "score": 0.9 - i * 0.1}
                        for i in range(5)
                    ],
                    "total": 5,
                    "strategy_params": strategy_params
                }
        
        # 使用优化的搜索服务
        search_service = OptimizedSearchService()
        
        # 执行多个搜索请求
        queries = [
            "人工智能发展历史",
            "机器学习算法",
            "深度学习应用",
            "自然语言处理",
            "计算机视觉技术"
        ]
        
        results = []
        for query in queries:
            try:
                result = await search_service.search(query)
                results.append(result)
            except Exception as e:
                logger.warning(f"搜索失败: {query} - {str(e)}")
        
        # 验证结果
        self.assertEqual(len(results), len(queries))
        for result in results:
            self.assertIn("query", result)
            self.assertIn("strategy", result)
            self.assertIn("results", result)
            self.assertEqual(len(result["results"]), 5)
        
        # 检查系统整体状态
        overall_stats = {
            "config_version": self.config_manager.get_config_version(),
            "strategy_stats": self.strategy_selector.get_performance_stats(),
            "sync_stats": await self.sync_service.get_sync_statistics(),
            "error_stats": self.error_handler.get_error_statistics(),
            "performance_stats": self.performance_optimizer.get_performance_stats()
        }
        
        logger.info("系统整体状态检查:")
        logger.info(f"  配置版本: {overall_stats['config_version']}")
        logger.info(f"  同步任务: {overall_stats['sync_stats']['total_jobs']}")
        logger.info(f"  错误率: {overall_stats['error_stats']['global_stats']['failure_rate']:.2%}")
        logger.info(f"  缓存命中率: {overall_stats['performance_stats']['cache_metrics']['hit_rate']:.2%}")
        
        logger.info("✅ 综合集成测试通过")


async def run_integration_tests():
    """运行集成测试"""
    logger.info("🚀 开始运行检索系统优化集成测试")
    
    # 创建测试套件
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestOptimizedRetrieval)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出测试结果摘要
    logger.info("\n" + "="*60)
    logger.info("📊 集成测试结果摘要")
    logger.info("="*60)
    logger.info(f"总测试数: {result.testsRun}")
    logger.info(f"成功数: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"失败数: {len(result.failures)}")
    logger.info(f"错误数: {len(result.errors)}")
    
    if result.failures:
        logger.error("❌ 失败的测试:")
        for test, traceback in result.failures:
            logger.error(f"  - {test}: {traceback}")
    
    if result.errors:
        logger.error("💥 错误的测试:")
        for test, traceback in result.errors:
            logger.error(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        logger.info("🎉 所有测试通过！检索系统优化模块集成成功！")
        return True
    else:
        logger.error("❌ 测试失败，请检查上述错误信息")
        return False


if __name__ == "__main__":
    # 运行集成测试
    success = asyncio.run(run_integration_tests())
    exit(0 if success else 1) 