"""
异步并发系统使用示例
展示如何使用异步执行引擎和通用适配器来实现多任务并发执行
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

# 导入异步并发组件
from core.tools.async_execution_engine import (
    AsyncExecutionEngine,
    ExecutionConfig,
    TaskType,
    get_global_engine
)
from core.tools.universal_async_adapter import (
    UniversalAsyncAdapter,
    AsyncTaskDefinition,
    CommonAggregators,
    get_global_adapter
)
from core.tools.search_result_aggregator import (
    SearchResult,
    SearchResultAggregator,
    create_policy_search_aggregator
)
from app.tools.advanced.search.policy_search_tool_async import (
    AsyncPolicySearchTool,
    async_policy_search
)

logger = logging.getLogger(__name__)


class AsyncConcurrentExamples:
    """异步并发系统使用示例"""
    
    def __init__(self):
        """初始化示例"""
        self.adapter: UniversalAsyncAdapter = None
        self.engine: AsyncExecutionEngine = None
        
    async def initialize(self):
        """初始化组件"""
        self.adapter = await get_global_adapter()
        self.engine = await get_global_engine()
    
    async def example_1_basic_concurrent_tasks(self):
        """示例1: 基础并发任务执行"""
        print("\n=== 示例1: 基础并发任务执行 ===")
        
        await self.initialize()
        
        # 定义一些模拟任务
        async def fetch_data(source: str, delay: float = 1.0) -> Dict[str, Any]:
            """模拟数据获取任务"""
            await asyncio.sleep(delay)
            return {
                "source": source,
                "data": f"来自 {source} 的数据",
                "timestamp": datetime.now().isoformat()
            }
        
        # 创建任务定义
        task_definitions = [
            AsyncTaskDefinition(
                task_func=fetch_data,
                task_name="fetch_from_api1",
                task_type=TaskType.IO_BOUND,
                parameters={"source": "API-1", "delay": 0.5}
            ),
            AsyncTaskDefinition(
                task_func=fetch_data,
                task_name="fetch_from_api2",
                task_type=TaskType.IO_BOUND,
                parameters={"source": "API-2", "delay": 0.8}
            ),
            AsyncTaskDefinition(
                task_func=fetch_data,
                task_name="fetch_from_api3",
                task_type=TaskType.IO_BOUND,
                parameters={"source": "API-3", "delay": 0.3}
            ),
        ]
        
        # 定义结果聚合函数
        def aggregate_api_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
            """聚合API结果"""
            aggregated = {
                "total_sources": len(results),
                "sources": [r["source"] for r in results],
                "data_combined": [r["data"] for r in results],
                "earliest_timestamp": min(r["timestamp"] for r in results),
                "latest_timestamp": max(r["timestamp"] for r in results)
            }
            return aggregated
        
        # 执行并发任务
        start_time = asyncio.get_event_loop().time()
        result = await self.adapter.run_concurrent_tasks(
            task_definitions=task_definitions,
            aggregator=aggregate_api_results
        )
        end_time = asyncio.get_event_loop().time()
        
        print(f"⏱️  并发执行耗时: {end_time - start_time:.2f}秒")
        print(f"✅ 成功任务: {result.success_count}")
        print(f"❌ 失败任务: {result.failure_count}")
        print(f"📊 聚合结果: {result.aggregated_data}")
        
        return result
    
    async def example_2_multi_keyword_policy_search(self):
        """示例2: 多关键词政策检索"""
        print("\n=== 示例2: 多关键词政策检索 ===")
        
        # 测试关键词
        keywords = ["创业补贴", "就业政策", "人才引进", "税收优惠"]
        
        # 创建异步政策检索工具
        policy_tool = AsyncPolicySearchTool()
        
        # 执行多关键词并发检索
        start_time = asyncio.get_event_loop().time()
        search_results = await policy_tool.search_multi_keywords_concurrent(
            keywords=keywords,
            region="六盘水",
            search_strategy="auto",
            max_results=20,
            enable_intelligent_crawling=True
        )
        end_time = asyncio.get_event_loop().time()
        
        print(f"⏱️  多关键词检索耗时: {end_time - start_time:.2f}秒")
        print(f"🔍 检索关键词: {', '.join(keywords)}")
        print(f"📄 找到结果数: {len(search_results)}")
        
        # 展示前3个结果
        for i, result in enumerate(search_results[:3], 1):
            print(f"\n结果 {i}:")
            print(f"  标题: {result.title}")
            print(f"  来源: {result.source}")
            print(f"  相关度: {result.relevance_score:.2f}")
            print(f"  匹配关键词: {', '.join(result.keywords_matched)}")
        
        return search_results
    
    async def example_3_parallel_tool_execution(self):
        """示例3: 并行工具执行"""
        print("\n=== 示例3: 并行工具执行 ===")
        
        await self.initialize()
        
        # 模拟不同的搜索工具
        async def web_search(query: str) -> List[Dict[str, Any]]:
            """模拟网络搜索"""
            await asyncio.sleep(0.5)
            return [
                {"title": f"网络搜索: {query} - 结果1", "source": "Web", "relevance": 0.8},
                {"title": f"网络搜索: {query} - 结果2", "source": "Web", "relevance": 0.7}
            ]
        
        async def knowledge_search(query: str) -> List[Dict[str, Any]]:
            """模拟知识库搜索"""
            await asyncio.sleep(0.8)
            return [
                {"title": f"知识库: {query} - 专业解答", "source": "Knowledge", "relevance": 0.9},
                {"title": f"知识库: {query} - 相关文档", "source": "Knowledge", "relevance": 0.6}
            ]
        
        async def document_search(query: str) -> List[Dict[str, Any]]:
            """模拟文档搜索"""
            await asyncio.sleep(0.3)
            return [
                {"title": f"文档库: {query} - 政策文件", "source": "Documents", "relevance": 0.85}
            ]
        
        # 创建并行搜索任务
        search_tools = [web_search, knowledge_search, document_search]
        query = "企业税收政策"
        
        task_definitions = []
        for i, tool in enumerate(search_tools):
            task_def = AsyncTaskDefinition(
                task_func=tool,
                task_name=f"search_tool_{i}",
                task_type=TaskType.IO_BOUND,
                parameters={"query": query}
            )
            task_definitions.append(task_def)
        
        # 定义搜索结果聚合函数
        def aggregate_search_results(results: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
            """聚合搜索结果"""
            all_results = []
            for result_list in results:
                all_results.extend(result_list)
            
            # 按相关度排序
            all_results.sort(key=lambda x: x["relevance"], reverse=True)
            
            return {
                "query": query,
                "total_results": len(all_results),
                "sources": list(set(r["source"] for r in all_results)),
                "top_results": all_results[:5],
                "avg_relevance": sum(r["relevance"] for r in all_results) / len(all_results)
            }
        
        # 执行并行搜索
        start_time = asyncio.get_event_loop().time()
        result = await self.adapter.run_concurrent_tasks(
            task_definitions=task_definitions,
            aggregator=aggregate_search_results
        )
        end_time = asyncio.get_event_loop().time()
        
        print(f"⏱️  并行搜索耗时: {end_time - start_time:.2f}秒")
        print(f"🔍 查询: {query}")
        print(f"📊 聚合结果: {result.aggregated_data}")
        
        return result
    
    async def example_4_mixed_task_types(self):
        """示例4: 混合任务类型执行"""
        print("\n=== 示例4: 混合任务类型执行 ===")
        
        await self.initialize()
        
        # CPU密集型任务
        def cpu_intensive_task(n: int) -> int:
            """模拟CPU密集型计算"""
            result = 0
            for i in range(n):
                result += i * i
            return result
        
        # IO密集型任务
        async def io_intensive_task(url: str) -> Dict[str, Any]:
            """模拟IO密集型网络请求"""
            await asyncio.sleep(0.5)
            return {"url": url, "status": "success", "data_size": 1024}
        
        # 创建混合任务
        task_definitions = [
            AsyncTaskDefinition(
                task_func=cpu_intensive_task,
                task_name="cpu_task_1",
                task_type=TaskType.CPU_BOUND,
                parameters={"n": 100000}
            ),
            AsyncTaskDefinition(
                task_func=io_intensive_task,
                task_name="io_task_1",
                task_type=TaskType.IO_BOUND,
                parameters={"url": "https://api1.example.com"}
            ),
            AsyncTaskDefinition(
                task_func=cpu_intensive_task,
                task_name="cpu_task_2",
                task_type=TaskType.CPU_BOUND,
                parameters={"n": 150000}
            ),
            AsyncTaskDefinition(
                task_func=io_intensive_task,
                task_name="io_task_2",
                task_type=TaskType.IO_BOUND,
                parameters={"url": "https://api2.example.com"}
            ),
        ]
        
        # 执行混合任务
        start_time = asyncio.get_event_loop().time()
        result = await self.adapter.run_concurrent_tasks(
            task_definitions=task_definitions,
            aggregator=CommonAggregators.merge_list_results
        )
        end_time = asyncio.get_event_loop().time()
        
        print(f"⏱️  混合任务执行耗时: {end_time - start_time:.2f}秒")
        print(f"✅ 成功任务: {result.success_count}")
        print(f"❌ 失败任务: {result.failure_count}")
        print(f"📊 任务结果: {result.aggregated_data}")
        
        return result
    
    async def example_5_error_handling_and_retry(self):
        """示例5: 错误处理和重试机制"""
        print("\n=== 示例5: 错误处理和重试机制 ===")
        
        await self.initialize()
        
        # 模拟不稳定的任务
        async def unreliable_task(task_id: str, failure_rate: float = 0.5) -> str:
            """模拟不稳定任务"""
            import random
            await asyncio.sleep(0.2)
            
            if random.random() < failure_rate:
                raise Exception(f"任务 {task_id} 执行失败")
            
            return f"任务 {task_id} 执行成功"
        
        # 创建包含可能失败任务的列表
        task_definitions = []
        for i in range(5):
            task_def = AsyncTaskDefinition(
                task_func=unreliable_task,
                task_name=f"unreliable_task_{i}",
                task_type=TaskType.IO_BOUND,
                parameters={"task_id": f"task_{i}", "failure_rate": 0.3},
                retry_count=2
            )
            task_definitions.append(task_def)
        
        # 执行任务并观察重试机制
        start_time = asyncio.get_event_loop().time()
        result = await self.adapter.run_concurrent_tasks(
            task_definitions=task_definitions,
            aggregator=CommonAggregators.merge_list_results
        )
        end_time = asyncio.get_event_loop().time()
        
        print(f"⏱️  任务执行耗时: {end_time - start_time:.2f}秒")
        print(f"✅ 成功任务: {result.success_count}")
        print(f"❌ 失败任务: {result.failure_count}")
        
        # 展示每个任务的详细结果
        for task_result in result.task_results:
            status_emoji = "✅" if task_result.status.value == "completed" else "❌"
            print(f"  {status_emoji} {task_result.task_id}: {task_result.status.value}")
            if task_result.retry_count > 0:
                print(f"    🔄 重试次数: {task_result.retry_count}")
            if task_result.error:
                print(f"    ⚠️  错误: {task_result.error}")
        
        return result


async def run_all_examples():
    """运行所有示例"""
    print("🚀 异步并发系统示例演示")
    print("=" * 50)
    
    examples = AsyncConcurrentExamples()
    
    try:
        # 运行示例1: 基础并发任务
        await examples.example_1_basic_concurrent_tasks()
        
        # 运行示例2: 多关键词政策检索
        await examples.example_2_multi_keyword_policy_search()
        
        # 运行示例3: 并行工具执行
        await examples.example_3_parallel_tool_execution()
        
        # 运行示例4: 混合任务类型
        await examples.example_4_mixed_task_types()
        
        # 运行示例5: 错误处理和重试
        await examples.example_5_error_handling_and_retry()
        
        print("\n🎉 所有示例执行完成!")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")
        logger.error(f"示例执行失败: {str(e)}", exc_info=True)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行示例
    asyncio.run(run_all_examples()) 