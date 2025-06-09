#!/usr/bin/env python3
"""
优化模块集成测试脚本
验证所有优化组件的集成状态和功能正确性
"""

import asyncio
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationTester:
    """集成测试器"""
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有集成测试"""
        logger.info("🚀 开始运行优化模块集成测试")
        
        test_suites = [
            ("配置系统测试", self.test_configuration_system),
            ("服务层集成测试", self.test_service_layer_integration),
            ("API层集成测试", self.test_api_layer_integration),
            ("向后兼容性测试", self.test_backward_compatibility),
            ("错误处理测试", self.test_error_handling),
            ("性能基准测试", self.test_performance_baseline)
        ]
        
        for suite_name, test_func in test_suites:
            logger.info(f"\n📋 运行测试套件: {suite_name}")
            try:
                await test_func()
                logger.info(f"✅ {suite_name} 通过")
            except Exception as e:
                logger.error(f"❌ {suite_name} 失败: {str(e)}")
                self._record_test_failure(suite_name, str(e))
        
        # 生成测试报告
        return self._generate_test_report()
    
    def _record_test_success(self, test_name: str, details: str = ""):
        """记录测试成功"""
        self.test_results["total_tests"] += 1
        self.test_results["passed_tests"] += 1
        self.test_results["test_details"].append({
            "test": test_name,
            "status": "PASS",
            "details": details
        })
    
    def _record_test_failure(self, test_name: str, error: str):
        """记录测试失败"""
        self.test_results["total_tests"] += 1
        self.test_results["failed_tests"] += 1
        self.test_results["test_details"].append({
            "test": test_name,
            "status": "FAIL",
            "error": error
        })
    
    async def test_configuration_system(self):
        """测试配置系统"""
        
        # 测试应用配置集成
        try:
            from app.config.optimization import (
                optimization_settings,
                get_optimization_config,
                is_optimization_enabled
            )
            
            # 验证配置结构
            config = get_optimization_config()
            required_sections = ['vector_search', 'keyword_search', 'hybrid_search', 'cache']
            
            for section in required_sections:
                assert section in config, f"配置缺少必需部分: {section}"
            
            # 验证配置访问
            enabled = is_optimization_enabled()
            assert isinstance(enabled, bool), "优化开关类型错误"
            
            self._record_test_success("应用配置集成", f"配置完整性验证通过，优化开关: {enabled}")
            
        except Exception as e:
            self._record_test_failure("应用配置集成", str(e))
        
        # 测试优化配置管理器（如果可用）
        try:
            from core.knowledge.optimization import get_config_manager
            
            config_manager = await get_config_manager()
            config = config_manager.get_config()
            
            assert hasattr(config, 'vector_search'), "优化配置缺少向量搜索配置"
            assert hasattr(config, 'cache'), "优化配置缺少缓存配置"
            
            self._record_test_success("优化配置管理器", "配置管理器工作正常")
            
        except ImportError:
            logger.warning("优化配置管理器不可用，跳过测试")
        except Exception as e:
            self._record_test_failure("优化配置管理器", str(e))
    
    async def test_service_layer_integration(self):
        """测试服务层集成"""
        
        # 模拟数据库会话
        class MockDB:
            pass
        
        mock_db = MockDB()
        
        # 测试优化搜索服务
        try:
            from app.services.knowledge.optimized_search_service import (
                get_optimized_search_service,
                OptimizedSearchService,
                OPTIMIZATION_AVAILABLE
            )
            
            # 创建服务实例
            service = get_optimized_search_service(mock_db, enable_optimization=False)
            assert isinstance(service, OptimizedSearchService), "服务类型错误"
            
            # 验证服务状态
            status = await service.get_optimization_status()
            assert "enabled" in status, "状态信息缺少enabled字段"
            assert "status" in status, "状态信息缺少status字段"
            
            self._record_test_success("优化搜索服务", f"服务创建成功，优化可用: {OPTIMIZATION_AVAILABLE}")
            
        except Exception as e:
            self._record_test_failure("优化搜索服务", str(e))
        
        # 测试向后兼容
        try:
            from app.services.knowledge.optimized_search_service import get_hybrid_search_service
            
            service = get_hybrid_search_service(mock_db)
            assert service is not None, "向后兼容服务创建失败"
            
            self._record_test_success("向后兼容服务", "兼容性工厂函数工作正常")
            
        except Exception as e:
            self._record_test_failure("向后兼容服务", str(e))
    
    async def test_api_layer_integration(self):
        """测试API层集成"""
        
        # 测试路由集成
        try:
            from app.api.frontend.search.router_integration import (
                check_integration_status,
                is_optimization_integrated
            )
            
            status = check_integration_status()
            assert "optimized_routes" in status, "集成状态缺少路由信息"
            assert "status" in status, "集成状态缺少状态信息"
            
            integrated = is_optimization_integrated()
            assert isinstance(integrated, bool), "集成检查结果类型错误"
            
            self._record_test_success("路由集成", f"集成状态: {status['status']}")
            
        except Exception as e:
            self._record_test_failure("路由集成", str(e))
        
        # 测试API端点（如果可用）
        try:
            from app.api.frontend.search.optimized import (
                OptimizedSearchRequest,
                OptimizedSearchResponse,
                CONFIG_MANAGER_AVAILABLE
            )
            
            # 验证请求模型
            request = OptimizedSearchRequest(query="test")
            assert request.query == "test", "请求模型验证失败"
            assert request.size == 10, "默认参数设置错误"
            
            self._record_test_success("API模型", f"API模型验证通过，配置管理器可用: {CONFIG_MANAGER_AVAILABLE}")
            
        except Exception as e:
            self._record_test_failure("API模型", str(e))
    
    async def test_backward_compatibility(self):
        """测试向后兼容性"""
        
        # 模拟传统搜索配置
        class MockSearchConfig:
            def __init__(self):
                self.query_text = "test query"
                self.knowledge_base_ids = []
                self.vector_weight = 0.7
                self.text_weight = 0.3
                self.size = 10
                self.search_engine = "hybrid"
                self.hybrid_method = "weighted_sum"
                self.threshold = 0.7
        
        config = MockSearchConfig()
        
        # 测试配置兼容性
        try:
            from app.services.knowledge.optimized_search_service import OptimizedSearchService
            
            class MockDB:
                pass
            
            service = OptimizedSearchService(MockDB(), enable_optimization=False)
            
            # 验证配置映射
            engine_type = service._map_search_engine("hybrid")
            assert engine_type == "hybrid", "搜索引擎映射错误"
            
            engine_type = service._map_search_engine("es")
            assert engine_type == "keyword", "ES引擎映射错误"
            
            self._record_test_success("配置兼容性", "搜索引擎映射正确")
            
        except Exception as e:
            self._record_test_failure("配置兼容性", str(e))
        
        # 测试接口兼容性
        try:
            from app.services.knowledge.hybrid_search_service import SearchConfig
            
            search_config = SearchConfig(
                query_text="test",
                knowledge_base_ids=[],
                vector_weight=0.7,
                text_weight=0.3
            )
            
            assert search_config.query_text == "test", "配置创建失败"
            assert search_config.vector_weight == 0.7, "权重设置错误"
            
            self._record_test_success("接口兼容性", "SearchConfig接口兼容")
            
        except Exception as e:
            self._record_test_failure("接口兼容性", str(e))
    
    async def test_error_handling(self):
        """测试错误处理"""
        
        # 测试导入错误处理
        try:
            from app.services.knowledge.optimized_search_service import OPTIMIZATION_AVAILABLE
            
            # 验证导入错误被正确处理
            if not OPTIMIZATION_AVAILABLE:
                logger.info("优化模块不可用，但错误处理正常")
            
            self._record_test_success("导入错误处理", f"优化可用: {OPTIMIZATION_AVAILABLE}")
            
        except Exception as e:
            self._record_test_failure("导入错误处理", str(e))
        
        # 测试服务降级
        try:
            from app.services.knowledge.optimized_search_service import OptimizedSearchService
            
            class MockDB:
                pass
            
            # 测试禁用优化时的降级
            service = OptimizedSearchService(MockDB(), enable_optimization=False)
            assert hasattr(service, 'legacy_service'), "降级服务未创建"
            
            self._record_test_success("服务降级", "优化禁用时正确降级到传统服务")
            
        except Exception as e:
            self._record_test_failure("服务降级", str(e))
    
    async def test_performance_baseline(self):
        """测试性能基准"""
        
        # 模拟性能测试
        try:
            start_time = time.time()
            
            # 模拟创建服务的开销
            from app.services.knowledge.optimized_search_service import get_optimized_search_service
            
            class MockDB:
                pass
            
            for i in range(10):
                service = get_optimized_search_service(MockDB(), enable_optimization=False)
                status = await service.get_optimization_status()
            
            duration = time.time() - start_time
            
            # 验证性能基准
            assert duration < 1.0, f"服务创建耗时过长: {duration:.3f}s"
            
            self._record_test_success("性能基准", f"10次服务创建耗时: {duration:.3f}s")
            
        except Exception as e:
            self._record_test_failure("性能基准", str(e))
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        success_rate = (self.test_results["passed_tests"] / max(self.test_results["total_tests"], 1)) * 100
        
        report = {
            "summary": {
                "total_tests": self.test_results["total_tests"],
                "passed_tests": self.test_results["passed_tests"],
                "failed_tests": self.test_results["failed_tests"],
                "success_rate": f"{success_rate:.1f}%"
            },
            "details": self.test_results["test_details"],
            "overall_status": "PASS" if self.test_results["failed_tests"] == 0 else "FAIL"
        }
        
        return report


async def main():
    """主函数"""
    logger.info("🧪 启动优化模块集成测试")
    
    tester = IntegrationTester()
    report = await tester.run_all_tests()
    
    # 打印测试报告
    print("\n" + "="*60)
    print("📊 集成测试报告")
    print("="*60)
    print(f"总测试数: {report['summary']['total_tests']}")
    print(f"通过测试: {report['summary']['passed_tests']}")
    print(f"失败测试: {report['summary']['failed_tests']}")
    print(f"成功率: {report['summary']['success_rate']}")
    print(f"总体状态: {report['overall_status']}")
    print("="*60)
    
    # 打印详细结果
    print("\n📋 详细测试结果:")
    for detail in report["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌"
        print(f"{status_icon} {detail['test']}: {detail['status']}")
        if detail["status"] == "PASS" and "details" in detail:
            print(f"   📝 {detail['details']}")
        elif detail["status"] == "FAIL":
            print(f"   💥 {detail['error']}")
    
    # 总结和建议
    print(f"\n🎯 集成状态总结:")
    if report["overall_status"] == "PASS":
        print("✅ 所有测试通过，优化模块集成成功！")
        print("\n📌 后续步骤:")
        print("1. 可以安全启用优化功能")
        print("2. 监控系统性能指标") 
        print("3. 根据需要调整优化参数")
    else:
        print("⚠️ 部分测试失败，请检查失败项并修复")
        print("\n🔧 建议:")
        print("1. 检查依赖是否正确安装")
        print("2. 验证配置文件是否存在")
        print("3. 确认所有必需的环境变量已设置")
    
    # 退出码
    sys.exit(0 if report["overall_status"] == "PASS" else 1)


if __name__ == "__main__":
    asyncio.run(main()) 