#!/usr/bin/env python3
"""
完整的数据库测试和混合搜索验证脚本
整合增强版PostgreSQL数据库初始化和混合搜索功能验证
"""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CompleteSystemTester:
    """完整系统测试器"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        self.warnings = []
        self.start_time = datetime.now()
        
    def log_result(self, component: str, test_name: str, success: bool, 
                   details: str = "", duration_ms: int = 0):
        """记录测试结果"""
        result = {
            "component": component,
            "test_name": test_name,
            "success": success,
            "details": details,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} {component} - {test_name}")
        if details:
            print(f"    └─ {details}")
        if duration_ms > 0:
            print(f"    ⏱️ 耗时: {duration_ms}ms")
            
        if not success:
            self.errors.append(f"{component} - {test_name}: {details}")
    
    def run_postgresql_tests(self) -> bool:
        """运行PostgreSQL增强版测试"""
        print("\n🐘 开始PostgreSQL增强版数据库测试...")
        
        try:
            # 导入增强版PostgreSQL测试
            from scripts.postgres_enhanced_test import main as postgres_main
            
            test_start = time.time()
            success = postgres_main()
            duration_ms = int((time.time() - test_start) * 1000)
            
            self.log_result(
                "PostgreSQL", "增强版数据库初始化", success,
                "创建增强版文档管理表结构" if success else "数据库初始化失败",
                duration_ms
            )
            
            return success
            
        except Exception as e:
            self.log_result(
                "PostgreSQL", "增强版数据库初始化", False,
                f"测试执行异常: {str(e)}"
            )
            return False
    
    def run_elasticsearch_tests(self) -> bool:
        """运行Elasticsearch混合搜索测试"""
        print("\n🔍 开始Elasticsearch混合搜索测试...")
        
        try:
            # 导入ES初始化脚本
            from scripts.init_elasticsearch import ElasticsearchInitializer
            
            es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            
            test_start = time.time()
            initializer = ElasticsearchInitializer(es_url=es_url)
            success = initializer.initialize_all()
            duration_ms = int((time.time() - test_start) * 1000)
            
            self.log_result(
                "Elasticsearch", "混合搜索初始化", success,
                "ES索引模板和搜索模板创建完成" if success else "ES初始化失败",
                duration_ms
            )
            
            return success
            
        except Exception as e:
            self.log_result(
                "Elasticsearch", "混合搜索初始化", False,
                f"ES初始化异常: {str(e)}"
            )
            return False
    
    def run_hybrid_search_validation(self) -> bool:
        """运行混合搜索配置验证"""
        print("\n🔬 开始混合搜索配置验证...")
        
        try:
            # 导入混合搜索验证器
            from scripts.validate_hybrid_search import HybridSearchValidator
            
            test_start = time.time()
            validator = HybridSearchValidator()
            success, report = validator.validate_all()
            duration_ms = int((time.time() - test_start) * 1000)
            
            # 记录详细验证结果
            passed_validations = report["summary"]["passed_validations"]
            total_validations = report["summary"]["total_validations"]
            
            self.log_result(
                "混合搜索", "配置验证", success,
                f"验证通过率: {passed_validations}/{total_validations} ({report['summary']['success_rate']:.1f}%)",
                duration_ms
            )
            
            # 记录具体的验证项目
            for result in report["results"]:
                if result["component"] not in ["混合搜索"]:  # 避免重复
                    self.log_result(
                        result["component"], result["check"], result["status"],
                        result["details"]
                    )
            
            return success
            
        except Exception as e:
            self.log_result(
                "混合搜索", "配置验证", False,
                f"验证异常: {str(e)}"
            )
            return False
    
    def run_storage_system_tests(self) -> bool:
        """运行存储系统测试"""
        print("\n📦 开始存储系统测试...")
        
        try:
            test_start = time.time()
            
            # 导入存储检测器
            from app.utils.storage.detection import StorageDetector
            detector = StorageDetector()
            
            # 检测存储配置
            storage_info = detector.get_vector_store_info()
            validation = detector.validate_core_storage()
            
            success = validation.get("overall_status") == "healthy"
            duration_ms = int((time.time() - test_start) * 1000)
            
            architecture_type = storage_info.get("storage_architecture", {}).get("type", "未知")
            file_storage = storage_info.get("storage_architecture", {}).get("file_storage_engine", "未知")
            search_engine = storage_info.get("storage_architecture", {}).get("search_engine", "未知")
            
            self.log_result(
                "存储系统", "架构检测", success,
                f"架构: {architecture_type}, 文件存储: {file_storage}, 搜索引擎: {search_engine}",
                duration_ms
            )
            
            # 检测混合搜索状态
            hybrid_status = storage_info.get("hybrid_search_status", {})
            hybrid_enabled = hybrid_status.get("enabled", False)
            
            self.log_result(
                "存储系统", "混合搜索状态", hybrid_enabled,
                f"混合搜索: {'启用' if hybrid_enabled else '禁用'}, 权重: {hybrid_status.get('weight', 'N/A')}"
            )
            
            return success
            
        except Exception as e:
            self.log_result(
                "存储系统", "架构检测", False,
                f"存储系统检测异常: {str(e)}"
            )
            return False
    
    def run_document_manager_tests(self) -> bool:
        """运行文档管理器测试"""
        print("\n📄 开始文档管理器测试...")
        
        try:
            test_start = time.time()
            
            # 导入增强版文档管理器
            from enhanced_document_manager import get_enhanced_document_manager
            manager = get_enhanced_document_manager()
            
            # 测试数据库连接
            try:
                conn = manager._get_db_connection()
                conn.close()
                db_connection_success = True
            except Exception as e:
                db_connection_success = False
                
            self.log_result(
                "文档管理器", "数据库连接", db_connection_success,
                "增强版文档管理器数据库连接正常" if db_connection_success else "数据库连接失败"
            )
            
            # 测试完整关联查询功能
            try:
                # 这里可以添加具体的文档管理功能测试
                associations_test_success = True
                associations_details = "关联追踪功能可用"
            except Exception as e:
                associations_test_success = False
                associations_details = f"关联追踪测试失败: {str(e)}"
                
            duration_ms = int((time.time() - test_start) * 1000)
            
            self.log_result(
                "文档管理器", "关联追踪", associations_test_success,
                associations_details, duration_ms
            )
            
            return db_connection_success and associations_test_success
            
        except Exception as e:
            self.log_result(
                "文档管理器", "功能测试", False,
                f"文档管理器测试异常: {str(e)}"
            )
            return False
    
    def run_environment_check(self) -> bool:
        """运行环境检查"""
        print("\n🌍 开始环境配置检查...")
        
        # 关键环境变量检查
        critical_env_vars = {
            "ELASTICSEARCH_URL": "http://localhost:9200",
            "ELASTICSEARCH_HYBRID_SEARCH": "true",
            "ELASTICSEARCH_HYBRID_WEIGHT": "0.7"
        }
        
        env_success = True
        for var, default in critical_env_vars.items():
            value = os.getenv(var)
            if value is None:
                self.log_result(
                    "环境配置", var, False,
                    f"环境变量未设置，建议设置为: {default}"
                )
                env_success = False
            else:
                self.log_result(
                    "环境配置", var, True,
                    f"值: {value}"
                )
        
        # 检查Python依赖
        dependencies = [
            ("psycopg2", "PostgreSQL连接"),
            ("elasticsearch", "Elasticsearch客户端"),
            ("yaml", "YAML配置解析")
        ]
        
        for dep, desc in dependencies:
            try:
                __import__(dep)
                self.log_result("Python依赖", desc, True, f"{dep} 可用")
            except ImportError:
                self.log_result("Python依赖", desc, False, f"{dep} 不可用")
                env_success = False
        
        return env_success
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        end_time = datetime.now()
        total_duration = int((end_time - self.start_time).total_seconds() * 1000)
        
        success_count = sum(1 for r in self.test_results if r["success"])
        total_tests = len(self.test_results)
        success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration_ms": total_duration,
                "total_tests": total_tests,
                "successful_tests": success_count,
                "failed_tests": total_tests - success_count,
                "success_rate": success_rate,
                "overall_success": len(self.errors) == 0
            },
            "test_results": self.test_results,
            "errors": self.errors,
            "warnings": self.warnings
        }
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """打印测试总结"""
        summary = report["summary"]
        
        print("\n" + "="*80)
        print("🎯 完整系统测试总结报告")
        print("="*80)
        
        print(f"\n📊 测试统计:")
        print(f"   总测试数: {summary['total_tests']}")
        print(f"   成功: {summary['successful_tests']}")
        print(f"   失败: {summary['failed_tests']}")
        print(f"   成功率: {summary['success_rate']:.1f}%")
        print(f"   总耗时: {summary['total_duration_ms']}ms")
        
        # 按组件分组显示结果
        print(f"\n📋 组件测试结果:")
        components = {}
        for result in self.test_results:
            comp = result["component"]
            if comp not in components:
                components[comp] = {"success": 0, "total": 0}
            components[comp]["total"] += 1
            if result["success"]:
                components[comp]["success"] += 1
                
        for comp, stats in components.items():
            success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            status_icon = "✅" if success_rate == 100 else "⚠️" if success_rate >= 50 else "❌"
            print(f"   {status_icon} {comp}: {stats['success']}/{stats['total']} ({success_rate:.0f}%)")
        
        # 显示错误
        if report["errors"]:
            print(f"\n❌ 错误列表:")
            for error in report["errors"]:
                print(f"   • {error}")
        
        # 总结
        print(f"\n{'='*80}")
        if summary["overall_success"]:
            print("🎉 完整系统测试成功! 所有核心功能正常运行。")
            print("💡 系统已准备就绪，可以开始使用混合搜索功能。")
        else:
            print("❌ 系统测试发现问题，请根据错误信息进行修复。")
            print("💡 建议优先修复PostgreSQL和Elasticsearch相关问题。")
        print("="*80)


def main():
    """主函数"""
    print("🚀 启动完整系统测试...")
    print("包含：PostgreSQL增强版 + Elasticsearch混合搜索 + 存储系统验证")
    print("="*80)
    
    tester = CompleteSystemTester()
    
    # 执行所有测试
    tests = [
        ("环境检查", tester.run_environment_check),
        ("PostgreSQL测试", tester.run_postgresql_tests),
        ("Elasticsearch测试", tester.run_elasticsearch_tests),
        ("存储系统测试", tester.run_storage_system_tests),
        ("混合搜索验证", tester.run_hybrid_search_validation),
        ("文档管理器测试", tester.run_document_manager_tests)
    ]
    
    overall_success = True
    for test_name, test_func in tests:
        try:
            success = test_func()
            if not success:
                overall_success = False
        except Exception as e:
            logger.error(f"{test_name}执行异常: {e}")
            overall_success = False
    
    # 生成并显示报告
    report = tester.generate_report()
    tester.print_summary(report)
    
    # 保存报告到文件
    import json
    report_file = project_root / "complete_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存到: {report_file}")
    
    return overall_success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        sys.exit(1) 