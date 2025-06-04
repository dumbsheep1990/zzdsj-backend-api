#!/usr/bin/env python3
"""
知识库服务迁移验证脚本
用于验证统一知识库服务是否正常工作，以及与原有服务的兼容性
"""

import asyncio
import sys
import logging
from typing import Dict, Any, List
import traceback
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationVerifier:
    """迁移验证器"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有验证测试"""
        logger.info("🚀 开始知识库服务迁移验证")
        
        tests = [
            ("导入测试", self.test_imports),
            ("统一服务基础功能", self.test_unified_service_basic),
            ("兼容性测试", self.test_compatibility),
            ("API层集成测试", self.test_api_integration),
            ("数据库操作测试", self.test_database_operations),
            ("错误处理测试", self.test_error_handling),
            ("性能基准测试", self.test_performance_benchmark)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"🔍 执行测试: {test_name}")
            try:
                result = await test_func()
                self.test_results.append({
                    "test": test_name,
                    "status": "PASS" if result else "FAIL",
                    "details": result if isinstance(result, dict) else {"success": result}
                })
                logger.info(f"✅ {test_name}: {'通过' if result else '失败'}")
            except Exception as e:
                error_info = {
                    "test": test_name,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                self.errors.append(error_info)
                self.test_results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "details": error_info
                })
                logger.error(f"❌ {test_name}: 错误 - {str(e)}")
        
        return self.generate_report()
    
    async def test_imports(self) -> bool:
        """测试导入功能"""
        try:
            # 测试统一服务导入
            from app.services.unified_knowledge_service import (
                UnifiedKnowledgeService,
                LegacyKnowledgeServiceAdapter,
                get_unified_knowledge_service,
                get_legacy_adapter
            )
            
            # 测试统一工具导入
            from app.tools.base.knowledge_management import get_knowledge_manager
            from app.tools.base.document_chunking import get_chunking_tool
            
            # 测试Agno框架导入
            from app.frameworks.agno.knowledge_base import AgnoKnowledgeBase
            
            logger.info("✅ 所有必要模块导入成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导入测试失败: {str(e)}")
            return False
    
    async def test_unified_service_basic(self) -> Dict[str, Any]:
        """测试统一服务基础功能"""
        try:
            # 模拟数据库会话
            from app.utils.database import get_db
            db = next(get_db())
            
            from app.services.unified_knowledge_service import get_unified_knowledge_service
            service = get_unified_knowledge_service(db)
            
            # 测试服务初始化
            assert hasattr(service, 'unified_manager')
            assert hasattr(service, 'chunking_tool')
            assert hasattr(service, 'db')
            
            # 测试基本方法存在
            methods_to_check = [
                'get_knowledge_bases',
                'get_knowledge_base',
                'create_knowledge_base',
                'update_knowledge_base',
                'delete_knowledge_base',
                'get_documents',
                'create_document',
                'search',
                'get_knowledge_base_stats'
            ]
            
            for method in methods_to_check:
                assert hasattr(service, method), f"缺少方法: {method}"
                assert callable(getattr(service, method)), f"方法不可调用: {method}"
            
            return {
                "service_initialized": True,
                "methods_available": len(methods_to_check),
                "database_connected": db is not None
            }
            
        except Exception as e:
            logger.error(f"❌ 统一服务基础功能测试失败: {str(e)}")
            raise
    
    async def test_compatibility(self) -> Dict[str, Any]:
        """测试向后兼容性"""
        try:
            from app.utils.database import get_db
            db = next(get_db())
            
            # 测试适配器
            from app.services.unified_knowledge_service import get_legacy_adapter
            adapter = get_legacy_adapter(db)
            
            # 测试适配器方法
            adapter_methods = [
                'get_knowledge_bases',
                'get_knowledge_base',
                'create_knowledge_base',
                'search'
            ]
            
            for method in adapter_methods:
                assert hasattr(adapter, method), f"适配器缺少方法: {method}"
            
            # 测试直接导入（如果兼容层已创建）
            compatibility_tests = []
            
            try:
                # 尝试原有的导入路径
                from app.services.knowledge_service import KnowledgeService as KS1
                compatibility_tests.append("knowledge_service导入: 成功")
            except ImportError as e:
                compatibility_tests.append(f"knowledge_service导入: 失败 - {str(e)}")
            
            try:
                from app.services.knowledge import KnowledgeService as KS2
                compatibility_tests.append("knowledge导入: 成功")
            except ImportError as e:
                compatibility_tests.append(f"knowledge导入: 失败 - {str(e)}")
            
            return {
                "adapter_initialized": True,
                "adapter_methods": len(adapter_methods),
                "compatibility_tests": compatibility_tests
            }
            
        except Exception as e:
            logger.error(f"❌ 兼容性测试失败: {str(e)}")
            raise
    
    async def test_api_integration(self) -> Dict[str, Any]:
        """测试API层集成"""
        try:
            # 测试依赖注入更新
            dependency_tests = []
            
            # 检查dependencies.py
            try:
                from app.dependencies import knowledge_service_dependency
                dependency_tests.append("dependencies.knowledge_service_dependency: 可用")
            except ImportError as e:
                dependency_tests.append(f"dependencies.knowledge_service_dependency: 失败 - {str(e)}")
            
            # 检查api/dependencies.py
            try:
                from app.api.dependencies import get_knowledge_service
                dependency_tests.append("api.dependencies.get_knowledge_service: 可用")
            except ImportError as e:
                dependency_tests.append(f"api.dependencies.get_knowledge_service: 失败 - {str(e)}")
            
            return {
                "dependency_injection_tests": dependency_tests,
                "api_layer_ready": len([t for t in dependency_tests if "可用" in t]) > 0
            }
            
        except Exception as e:
            logger.error(f"❌ API层集成测试失败: {str(e)}")
            raise
    
    async def test_database_operations(self) -> Dict[str, Any]:
        """测试数据库操作"""
        try:
            from app.utils.database import get_db
            from app.services.unified_knowledge_service import get_unified_knowledge_service
            
            db = next(get_db())
            service = get_unified_knowledge_service(db)
            
            # 测试获取知识库列表
            kbs = await service.get_knowledge_bases(limit=5)
            
            # 测试统计信息
            if kbs:
                kb_id = kbs[0]["id"]
                stats = await service.get_knowledge_base_stats(kb_id)
                
                return {
                    "knowledge_bases_retrieved": len(kbs),
                    "stats_available": stats is not None,
                    "stats_keys": list(stats.keys()) if stats else [],
                    "database_accessible": True
                }
            else:
                return {
                    "knowledge_bases_retrieved": 0,
                    "stats_available": False,
                    "database_accessible": True,
                    "note": "无现有知识库数据"
                }
                
        except Exception as e:
            logger.error(f"❌ 数据库操作测试失败: {str(e)}")
            raise
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """测试错误处理"""
        try:
            from app.utils.database import get_db
            from app.services.unified_knowledge_service import get_unified_knowledge_service
            from fastapi import HTTPException
            
            db = next(get_db())
            service = get_unified_knowledge_service(db)
            
            error_tests = []
            
            # 测试获取不存在的知识库
            try:
                result = await service.get_knowledge_base("non_existent_id")
                error_tests.append(f"不存在知识库: 返回 {result}")
            except Exception as e:
                error_tests.append(f"不存在知识库: 异常 {type(e).__name__}")
            
            # 测试获取不存在文档的统计
            try:
                stats = await service.get_knowledge_base_stats("non_existent_id")
                error_tests.append(f"不存在知识库统计: 返回 {type(stats)}")
            except Exception as e:
                error_tests.append(f"不存在知识库统计: 异常 {type(e).__name__}")
            
            return {
                "error_handling_tests": error_tests,
                "graceful_error_handling": True
            }
            
        except Exception as e:
            logger.error(f"❌ 错误处理测试失败: {str(e)}")
            raise
    
    async def test_performance_benchmark(self) -> Dict[str, Any]:
        """测试性能基准"""
        try:
            import time
            from app.utils.database import get_db
            from app.services.unified_knowledge_service import get_unified_knowledge_service
            
            db = next(get_db())
            service = get_unified_knowledge_service(db)
            
            # 测试知识库列表获取性能
            start_time = time.time()
            kbs = await service.get_knowledge_bases(limit=10)
            list_time = time.time() - start_time
            
            # 测试切分工具性能
            start_time = time.time()
            chunking_tool = service.chunking_tool
            test_content = "这是一个性能测试文档。" * 50
            
            from app.tools.base.document_chunking import ChunkingConfig
            config = ChunkingConfig(strategy="sentence", chunk_size=100)
            
            if hasattr(chunking_tool, 'chunk_document'):
                result = chunking_tool.chunk_document(test_content, config)
                chunk_time = time.time() - start_time
                chunk_count = len(result.chunks) if hasattr(result, 'chunks') else 0
            else:
                chunk_time = 0
                chunk_count = 0
            
            return {
                "knowledge_base_list_time": list_time,
                "chunking_time": chunk_time,
                "knowledge_bases_count": len(kbs),
                "chunks_created": chunk_count,
                "performance_acceptable": list_time < 2.0 and chunk_time < 5.0
            }
            
        except Exception as e:
            logger.error(f"❌ 性能基准测试失败: {str(e)}")
            raise
    
    def generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])
        
        overall_status = "SUCCESS" if error_tests == 0 and failed_tests == 0 else "FAILED"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
            },
            "test_results": self.test_results,
            "errors": self.errors
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """打印验证报告"""
        print("\n" + "="*60)
        print("🔍 知识库服务迁移验证报告")
        print("="*60)
        
        print(f"⏰ 验证时间: {report['timestamp']}")
        print(f"📊 总体状态: {report['overall_status']}")
        print()
        
        summary = report['summary']
        print("📈 测试摘要:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  通过测试: {summary['passed']}")
        print(f"  失败测试: {summary['failed']}")
        print(f"  错误测试: {summary['errors']}")
        print(f"  成功率: {summary['success_rate']}")
        print()
        
        print("📋 详细结果:")
        for result in report['test_results']:
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[result['status']]
            print(f"  {status_icon} {result['test']}: {result['status']}")
            
            if result['status'] in ['FAIL', 'ERROR'] and result.get('details'):
                if isinstance(result['details'], dict) and 'error' in result['details']:
                    print(f"      错误: {result['details']['error']}")
        
        if report['errors']:
            print("\n💥 错误详情:")
            for error in report['errors']:
                print(f"  测试: {error['test']}")
                print(f"  错误: {error['error']}")
                print()
        
        print("="*60)
        
        if report['overall_status'] == "SUCCESS":
            print("🎉 所有测试通过！知识库服务迁移验证成功！")
        else:
            print("⚠️  部分测试失败，请检查错误信息并修复问题。")
        
        print("="*60)

async def main():
    """主函数"""
    try:
        verifier = MigrationVerifier()
        report = await verifier.run_all_tests()
        verifier.print_report(report)
        
        # 如果有错误，返回非零退出码
        if report['overall_status'] != "SUCCESS":
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"验证脚本执行失败: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 设置事件循环策略（兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 