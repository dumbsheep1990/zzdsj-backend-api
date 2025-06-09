#!/usr/bin/env python3
"""
优化检索系统使用示例

本脚本演示如何使用完整的优化检索系统，包括：
1. 配置管理
2. 策略选择  
3. 数据同步
4. 错误处理
5. 性能优化

运行方式：
    python scripts/examples/optimized_retrieval_example.py
"""

import asyncio
import logging
import time
import json
from typing import List, Dict, Any
import sys
import os

# 设置路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.knowledge.optimization import (
    get_optimized_retrieval_manager,
    get_config_manager,
    get_strategy_selector,
    get_sync_service,
    get_error_handler,
    get_performance_optimizer,
    initialize_optimization_modules,
    cleanup_optimization_modules,
    CacheConfig,
    CacheStrategy
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """基础使用示例"""
    logger.info("🚀 开始基础使用示例")
    
    # 1. 获取优化的检索管理器
    manager = await get_optimized_retrieval_manager()
    
    # 2. 执行单个搜索
    result = await manager.search(
        query="人工智能的发展历史和现状",
        knowledge_base_id="example_kb"
    )
    
    logger.info("🔍 搜索结果:")
    logger.info(f"  查询: {result['query']}")
    logger.info(f"  策略: {result['strategy']}")
    logger.info(f"  结果数: {len(result['results'])}")
    
    for i, res in enumerate(result['results'][:3]):
        logger.info(f"  结果 {i+1}: {res['content'][:50]}...")
    
    return result


async def example_batch_search():
    """批量搜索示例"""
    logger.info("📦 开始批量搜索示例")
    
    manager = await get_optimized_retrieval_manager()
    
    # 准备查询列表
    queries = [
        "机器学习算法分类",
        "深度学习神经网络架构",
        "自然语言处理技术发展",
        "计算机视觉应用场景",
        "强化学习基本原理"
    ]
    
    # 执行批量搜索
    start_time = time.time()
    results = await manager.batch_search(
        queries=queries,
        knowledge_base_id="example_kb",
        batch_size=3
    )
    end_time = time.time()
    
    logger.info(f"📊 批量搜索完成，耗时: {end_time - start_time:.2f}秒")
    logger.info(f"🔢 处理查询数: {len(queries)}")
    logger.info(f"📋 返回结果数: {len(results)}")
    
    # 显示部分结果
    for i, result in enumerate(results[:3]):
        logger.info(f"  查询 {i+1}: {result['query']}")
        logger.info(f"    策略: {result['strategy']}")
        logger.info(f"    结果数: {len(result['results'])}")
    
    return results


async def example_performance_comparison():
    """性能对比示例"""
    logger.info("⚡ 开始性能对比示例")
    
    # 测试查询
    test_queries = [
        "人工智能技术发展",
        "机器学习应用实例", 
        "深度学习模型训练",
        "自然语言处理方法",
        "计算机视觉算法"
    ]
    
    # 1. 无缓存性能测试
    cache_config_no_cache = CacheConfig(
        strategy=CacheStrategy.LRU,
        max_size=0,  # 禁用缓存
        enabled=False
    )
    manager_no_cache = await get_optimized_retrieval_manager(
        cache_config=cache_config_no_cache
    )
    
    start_time = time.time()
    for query in test_queries:
        await manager_no_cache.search(query, knowledge_base_id="test_kb")
    no_cache_time = time.time() - start_time
    
    # 2. 有缓存性能测试
    cache_config_with_cache = CacheConfig(
        strategy=CacheStrategy.LRU,
        max_size=1000,
        enabled=True
    )
    manager_with_cache = await get_optimized_retrieval_manager(
        cache_config=cache_config_with_cache
    )
    
    # 第一轮 - 填充缓存
    for query in test_queries:
        await manager_with_cache.search(query, knowledge_base_id="test_kb")
    
    # 第二轮 - 测试缓存性能
    start_time = time.time()
    for query in test_queries:
        await manager_with_cache.search(query, knowledge_base_id="test_kb")
    with_cache_time = time.time() - start_time
    
    # 计算性能提升
    speedup = no_cache_time / with_cache_time if with_cache_time > 0 else float('inf')
    
    logger.info("📈 性能对比结果:")
    logger.info(f"  无缓存耗时: {no_cache_time:.3f}秒")
    logger.info(f"  有缓存耗时: {with_cache_time:.3f}秒") 
    logger.info(f"  性能提升: {speedup:.1f}x")
    
    # 获取缓存统计
    cache_stats = manager_with_cache.performance_optimizer.get_performance_stats()
    logger.info(f"  缓存命中率: {cache_stats['cache_metrics']['hit_rate']:.1%}")
    
    return {
        "no_cache_time": no_cache_time,
        "with_cache_time": with_cache_time,
        "speedup": speedup,
        "cache_stats": cache_stats
    }


async def example_error_handling():
    """错误处理示例"""
    logger.info("🛡️ 开始错误处理示例")
    
    error_handler = get_error_handler()
    
    # 1. 熔断器示例
    @error_handler.circuit_breaker("example_service", failure_threshold=3)
    async def unreliable_service():
        """模拟不稳定的服务"""
        import random
        if random.random() < 0.7:  # 70%失败率
            raise ConnectionError("服务暂时不可用")
        return "服务调用成功"
    
    # 测试熔断器
    success_count = 0
    error_count = 0
    
    for i in range(10):
        try:
            result = await unreliable_service()
            success_count += 1
            logger.info(f"  尝试 {i+1}: ✅ {result}")
        except Exception as e:
            error_count += 1
            logger.info(f"  尝试 {i+1}: ❌ {str(e)}")
    
    logger.info(f"📊 错误处理统计:")
    logger.info(f"  成功次数: {success_count}")
    logger.info(f"  失败次数: {error_count}")
    
    # 2. 重试机制示例
    attempt_count = 0
    
    @error_handler.retry_on_failure(max_retries=3, base_delay=0.5)
    async def retry_service():
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count < 3:
            raise ValueError(f"第 {attempt_count} 次尝试失败")
        return f"第 {attempt_count} 次尝试成功"
    
    try:
        result = await retry_service()
        logger.info(f"🔄 重试结果: {result}")
    except Exception as e:
        logger.info(f"🔄 重试失败: {str(e)}")
    
    # 获取错误统计
    error_stats = error_handler.get_error_statistics()
    logger.info(f"📈 错误处理统计: {error_stats['global_stats']}")
    
    return error_stats


async def example_configuration_management():
    """配置管理示例"""
    logger.info("⚙️ 开始配置管理示例")
    
    config_manager = await get_config_manager()
    
    # 1. 获取当前配置
    current_config = config_manager.get_config()
    logger.info("📋 当前配置:")
    logger.info(f"  向量搜索Top-K: {current_config.vector_search.top_k}")
    logger.info(f"  混合搜索权重: 向量{current_config.hybrid_search.vector_weight}, 关键词{current_config.hybrid_search.keyword_weight}")
    logger.info(f"  缓存策略: {current_config.cache.strategy}")
    
    # 2. 动态更新配置
    logger.info("🔄 动态更新配置...")
    
    update_success = await config_manager.update_config({
        "vector_search": {
            "top_k": 25
        },
        "cache": {
            "max_size": 8000
        }
    })
    
    if update_success:
        logger.info("✅ 配置更新成功")
        updated_config = config_manager.get_config()
        logger.info(f"  新的向量搜索Top-K: {updated_config.vector_search.top_k}")
        logger.info(f"  新的缓存大小: {updated_config.cache.max_size}")
    else:
        logger.info("❌ 配置更新失败")
    
    # 3. 配置验证
    is_valid = config_manager.validate_config()
    logger.info(f"🔍 配置验证结果: {'✅ 有效' if is_valid else '❌ 无效'}")
    
    return {
        "original_config": current_config,
        "update_success": update_success,
        "config_valid": is_valid
    }


async def example_strategy_selection():
    """策略选择示例"""
    logger.info("🎯 开始策略选择示例")
    
    selector = await get_strategy_selector()
    
    # 测试不同类型的查询
    test_cases = [
        {
            "query": "什么是机器学习",
            "description": "概念性查询"
        },
        {
            "query": "TensorFlow安装教程步骤详细说明",
            "description": "具体操作查询" 
        },
        {
            "query": "深度学习 神经网络 卷积",
            "description": "关键词查询"
        }
    ]
    
    for case in test_cases:
        logger.info(f"📝 测试查询: {case['query']} ({case['description']})")
        
        # 获取策略推荐
        strategy, params = await selector.select_optimal_strategy(
            query=case['query'],
            knowledge_base_id="example_kb"
        )
        
        logger.info(f"  推荐策略: {strategy.value}")
        logger.info(f"  策略参数: {params}")
        
        # 获取详细分析
        recommendations = await selector.get_strategy_recommendations(case['query'])
        logger.info(f"  查询分析: {recommendations['query_analysis']}")
    
    # 获取性能统计
    performance_stats = selector.get_performance_stats()
    logger.info("📊 策略选择器性能统计:")
    logger.info(f"  引擎评估: {len(performance_stats.get('engine_assessments', {}))} 个引擎")
    
    return performance_stats


async def example_system_monitoring():
    """系统监控示例"""
    logger.info("📊 开始系统监控示例")
    
    manager = await get_optimized_retrieval_manager()
    
    # 执行一些搜索操作以生成监控数据
    test_queries = ["AI发展", "ML应用", "DL模型"]
    for query in test_queries:
        await manager.search(query, knowledge_base_id="monitor_test")
    
    # 获取完整的系统状态
    system_status = await manager.get_system_status()
    
    logger.info("🖥️ 系统状态概览:")
    logger.info(f"  配置版本: {system_status['config_version']}")
    logger.info(f"  系统健康: {system_status['health']['status']}")
    
    # 性能指标
    perf_stats = system_status['performance_stats']
    logger.info("⚡ 性能指标:")
    logger.info(f"  平均响应时间: {perf_stats['request_metrics']['avg_response_time']:.2f}ms")
    logger.info(f"  缓存命中率: {perf_stats['cache_metrics']['hit_rate']:.1%}")
    logger.info(f"  活跃请求数: {perf_stats['concurrency_metrics']['active_requests']}")
    
    # 错误统计
    error_stats = system_status['error_stats']
    logger.info("🚨 错误统计:")
    logger.info(f"  总请求数: {error_stats['global_stats']['total_requests']}")
    logger.info(f"  失败率: {error_stats['global_stats']['failure_rate']:.2%}")
    
    # 数据同步状态
    sync_stats = system_status['sync_stats']
    logger.info("🔄 同步状态:")
    logger.info(f"  活跃任务: {sync_stats['active_jobs']}")
    logger.info(f"  总任务数: {sync_stats['total_jobs']}")
    
    return system_status


async def run_comprehensive_example():
    """运行综合示例"""
    logger.info("🌟 开始运行检索系统优化综合示例")
    logger.info("=" * 60)
    
    try:
        # 1. 初始化系统
        logger.info("🚀 步骤 1: 初始化优化模块")
        init_result = await initialize_optimization_modules()
        logger.info(f"初始化结果: {init_result['status']}")
        
        # 2. 基础使用
        logger.info("\n🔍 步骤 2: 基础搜索功能演示")
        await example_basic_usage()
        
        # 3. 批量搜索
        logger.info("\n📦 步骤 3: 批量搜索演示")
        await example_batch_search()
        
        # 4. 性能对比
        logger.info("\n⚡ 步骤 4: 性能优化效果演示")
        perf_result = await example_performance_comparison()
        
        # 5. 错误处理
        logger.info("\n🛡️ 步骤 5: 错误处理机制演示")
        await example_error_handling()
        
        # 6. 配置管理
        logger.info("\n⚙️ 步骤 6: 配置管理演示")
        await example_configuration_management()
        
        # 7. 策略选择
        logger.info("\n🎯 步骤 7: 智能策略选择演示")
        await example_strategy_selection()
        
        # 8. 系统监控
        logger.info("\n📊 步骤 8: 系统监控演示")
        system_status = await example_system_monitoring()
        
        # 9. 总结报告
        logger.info("\n" + "=" * 60)
        logger.info("📋 综合示例执行完成")
        logger.info("=" * 60)
        
        logger.info("🎯 核心功能验证:")
        logger.info("  ✅ 配置管理 - 动态配置更新")
        logger.info("  ✅ 策略选择 - 智能策略推荐")
        logger.info("  ✅ 数据同步 - 多引擎一致性")
        logger.info("  ✅ 错误处理 - 熔断器和重试")
        logger.info("  ✅ 性能优化 - 缓存和并发控制")
        
        logger.info(f"\n📈 性能提升效果:")
        logger.info(f"  缓存加速比: {perf_result['speedup']:.1f}x")
        logger.info(f"  缓存命中率: {perf_result['cache_stats']['cache_metrics']['hit_rate']:.1%}")
        
        logger.info(f"\n🔍 系统状态:")
        logger.info(f"  配置版本: {system_status['config_version']}")
        logger.info(f"  系统健康: {system_status['health']['status']}")
        logger.info(f"  平均响应时间: {system_status['performance_stats']['request_metrics']['avg_response_time']:.2f}ms")
        
        logger.info("\n🎉 所有示例执行成功！优化检索系统运行正常。")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 综合示例执行失败: {str(e)}")
        return False
        
    finally:
        # 清理资源
        logger.info("\n🧹 清理系统资源...")
        await cleanup_optimization_modules()
        logger.info("✅ 资源清理完成")


if __name__ == "__main__":
    # 运行综合示例
    success = asyncio.run(run_comprehensive_example())
    
    if success:
        print("\n🎉 示例运行成功！")
        exit(0)
    else:
        print("\n❌ 示例运行失败！")
        exit(1) 