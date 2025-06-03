#!/usr/bin/env python3
"""
核心存储系统要求测试脚本
验证Elasticsearch和MinIO作为基础必需组件的配置是否正确
测试在不同部署模式下的行为
"""

import sys
import os
import unittest
import json
from typing import Dict, Any, List
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.utils.storage.storage_detector import StorageDetector

class CoreStorageRequirementsTest(unittest.TestCase):
    """核心存储系统要求测试类"""
    
    def setUp(self):
        """测试前置设置"""
        self.detector = StorageDetector()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "test_cases": [],
            "summary": {}
        }
    
    def add_test_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """添加测试结果"""
        self.test_results["test_cases"].append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_elasticsearch_is_core_requirement(self):
        """测试Elasticsearch是否被正确识别为核心必需组件"""
        print("🔍 测试 Elasticsearch 核心必需组件状态...")
        
        # 获取存储信息
        storage_info = self.detector.get_vector_store_info()
        
        # 检查Elasticsearch配置
        es_config = storage_info.get("elasticsearch", {})
        
        # 验证核心必需组件标识
        self.assertTrue(es_config.get("is_required", False), 
                       "Elasticsearch应该被标记为基础必需组件")
        self.assertEqual(es_config.get("component_type"), "core", 
                        "Elasticsearch应该被标记为核心组件类型")
        
        # 验证描述信息
        description = es_config.get("description", "")
        self.assertIn("基础必需", description, 
                     "Elasticsearch描述应包含'基础必需'")
        
        # 验证混合检索强制启用
        self.assertTrue(settings.ELASTICSEARCH_HYBRID_SEARCH, 
                       "混合检索应该被强制启用")
        
        details = {
            "is_required": es_config.get("is_required"),
            "component_type": es_config.get("component_type"),
            "description": description,
            "hybrid_search_enabled": settings.ELASTICSEARCH_HYBRID_SEARCH,
            "hybrid_weight": settings.ELASTICSEARCH_HYBRID_WEIGHT
        }
        
        self.add_test_result("elasticsearch_core_requirement", True, details)
        print("✅ Elasticsearch 核心必需组件状态验证通过")
    
    def test_minio_is_core_requirement(self):
        """测试MinIO是否被正确识别为核心必需组件"""
        print("📁 测试 MinIO 核心必需组件状态...")
        
        # 获取存储信息
        storage_info = self.detector.get_vector_store_info()
        
        # 检查MinIO配置
        minio_config = storage_info.get("minio", {})
        
        # 验证核心必需组件标识
        self.assertTrue(minio_config.get("is_required", False), 
                       "MinIO应该被标记为基础必需组件")
        self.assertEqual(minio_config.get("component_type"), "core", 
                        "MinIO应该被标记为核心组件类型")
        
        # 验证描述信息
        description = minio_config.get("description", "")
        self.assertIn("基础必需", description, 
                     "MinIO描述应包含'基础必需'")
        
        # 验证配置信息
        self.assertTrue(settings.MINIO_ENDPOINT, "MinIO端点应该被配置")
        self.assertTrue(settings.MINIO_BUCKET, "MinIO存储桶应该被配置")
        
        details = {
            "is_required": minio_config.get("is_required"),
            "component_type": minio_config.get("component_type"),
            "description": description,
            "endpoint": settings.MINIO_ENDPOINT,
            "bucket": settings.MINIO_BUCKET
        }
        
        self.add_test_result("minio_core_requirement", True, details)
        print("✅ MinIO 核心必需组件状态验证通过")
    
    def test_milvus_is_optional_enhancement(self):
        """测试Milvus是否被正确识别为可选增强组件"""
        print("🚀 测试 Milvus 可选增强组件状态...")
        
        # 获取存储信息
        storage_info = self.detector.get_vector_store_info()
        
        # 检查Milvus配置
        milvus_config = storage_info.get("milvus", {})
        
        # 验证可选组件标识
        self.assertFalse(milvus_config.get("is_required", True), 
                        "Milvus应该被标记为可选组件")
        self.assertEqual(milvus_config.get("component_type"), "enhancement", 
                        "Milvus应该被标记为增强组件类型")
        
        # 验证在最小化模式下的行为
        if settings.DEPLOYMENT_MODE == "minimal":
            self.assertFalse(settings.MILVUS_ENABLED, 
                           "在最小化模式下Milvus应该被禁用")
        
        details = {
            "is_required": milvus_config.get("is_required"),
            "component_type": milvus_config.get("component_type"),
            "enabled": settings.MILVUS_ENABLED,
            "deployment_mode": settings.DEPLOYMENT_MODE
        }
        
        self.add_test_result("milvus_optional_enhancement", True, details)
        print("✅ Milvus 可选增强组件状态验证通过")
    
    def test_deployment_mode_core_requirements(self):
        """测试不同部署模式下的核心要求"""
        print(f"🎯 测试部署模式 '{settings.DEPLOYMENT_MODE}' 的核心要求...")
        
        # 获取系统要求
        requirements = self.detector.get_system_requirements()
        
        # 检查核心要求
        core_requirements = requirements.get("core_requirements", [])
        core_names = [req["name"] for req in core_requirements]
        
        # 验证核心组件必须包含ES和MinIO
        self.assertIn("Elasticsearch", core_names, 
                     "核心要求必须包含Elasticsearch")
        self.assertIn("MinIO", core_names, 
                     "核心要求必须包含MinIO")
        
        # 验证所有核心组件都标记为critical
        for req in core_requirements:
            self.assertTrue(req.get("critical", False), 
                           f"{req['name']} 应该被标记为关键组件")
            self.assertEqual(req.get("status"), "required", 
                           f"{req['name']} 应该被标记为必需状态")
        
        # 检查部署模式特定要求
        deployment_reqs = requirements.get("deployment_requirements", {}).get(settings.DEPLOYMENT_MODE, {})
        core_services = deployment_reqs.get("core_services", [])
        
        self.assertIn("Elasticsearch", core_services, 
                     f"{settings.DEPLOYMENT_MODE}模式必须包含Elasticsearch")
        self.assertIn("MinIO", core_services, 
                     f"{settings.DEPLOYMENT_MODE}模式必须包含MinIO")
        
        details = {
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "core_requirements": core_names,
            "core_services": core_services,
            "critical_warning": requirements.get("critical_warning")
        }
        
        self.add_test_result("deployment_mode_requirements", True, details)
        print("✅ 部署模式核心要求验证通过")
    
    def test_storage_architecture_validation(self):
        """测试存储架构验证"""
        print("🏗️ 测试存储架构验证...")
        
        # 获取存储架构信息
        storage_info = self.detector.get_vector_store_info()
        architecture = storage_info.get("storage_architecture", {})
        
        # 验证核心组件列表
        core_components = architecture.get("core_components", [])
        self.assertIn("elasticsearch", core_components, 
                     "核心组件必须包含elasticsearch")
        self.assertIn("minio", core_components, 
                     "核心组件必须包含minio")
        
        # 验证文件存储引擎
        file_storage_engine = architecture.get("file_storage_engine")
        self.assertEqual(file_storage_engine, "MinIO", 
                        "文件存储引擎应该是MinIO")
        
        # 验证搜索引擎
        search_engine = architecture.get("search_engine")
        self.assertEqual(search_engine, "Elasticsearch", 
                        "搜索引擎应该是Elasticsearch")
        
        # 验证混合检索状态
        hybrid_search_status = storage_info.get("hybrid_search_status", {})
        self.assertTrue(hybrid_search_status.get("enabled", False), 
                       "混合检索应该被启用")
        self.assertTrue(hybrid_search_status.get("forced_enabled", False), 
                       "混合检索应该被强制启用")
        
        details = {
            "architecture_type": architecture.get("type"),
            "core_components": core_components,
            "file_storage_engine": file_storage_engine,
            "search_engine": search_engine,
            "hybrid_search_enabled": hybrid_search_status.get("enabled"),
            "architecture_description": architecture.get("architecture_description")
        }
        
        self.add_test_result("storage_architecture_validation", True, details)
        print("✅ 存储架构验证通过")
    
    def test_configuration_validation(self):
        """测试配置验证"""
        print("⚙️ 测试配置验证...")
        
        # 验证必需配置
        config_errors = settings.validate_required_config()
        
        # 在测试环境中，某些配置可能未设置，这是正常的
        # 但ES和MinIO的基本配置应该存在
        
        # 验证ES配置
        self.assertTrue(settings.ELASTICSEARCH_URL, 
                       "Elasticsearch URL应该被配置")
        self.assertTrue(settings.ELASTICSEARCH_HYBRID_SEARCH, 
                       "Elasticsearch混合检索应该被启用")
        
        # 验证MinIO配置
        self.assertTrue(settings.MINIO_ENDPOINT, 
                       "MinIO端点应该被配置")
        self.assertTrue(settings.MINIO_BUCKET, 
                       "MinIO存储桶应该被配置")
        
        # 验证存储架构信息
        storage_arch_info = settings.get_storage_architecture_info()
        storage_engines = storage_arch_info.get("storage_engines", {})
        
        # ES应该始终启用
        es_engine = storage_engines.get("elasticsearch", {})
        self.assertTrue(es_engine.get("enabled", False), 
                       "Elasticsearch引擎应该始终启用")
        
        # MinIO应该始终启用
        minio_engine = storage_engines.get("minio", {})
        self.assertTrue(minio_engine.get("enabled", False), 
                       "MinIO引擎应该始终启用")
        
        details = {
            "config_errors": config_errors,
            "elasticsearch_url": settings.ELASTICSEARCH_URL,
            "elasticsearch_hybrid_search": settings.ELASTICSEARCH_HYBRID_SEARCH,
            "minio_endpoint": settings.MINIO_ENDPOINT,
            "minio_bucket": settings.MINIO_BUCKET,
            "storage_engines": storage_engines
        }
        
        self.add_test_result("configuration_validation", True, details)
        print("✅ 配置验证通过")
    
    def test_core_storage_validation_function(self):
        """测试核心存储验证功能"""
        print("🔍 测试核心存储验证功能...")
        
        # 运行核心存储验证
        validation_result = self.detector.validate_core_storage()
        
        # 验证返回结果结构
        self.assertIn("overall_status", validation_result, 
                     "验证结果应包含整体状态")
        self.assertIn("core_components", validation_result, 
                     "验证结果应包含核心组件状态")
        self.assertIn("recommendations", validation_result, 
                     "验证结果应包含建议")
        
        # 验证核心组件检查
        core_components = validation_result.get("core_components", {})
        self.assertIn("elasticsearch", core_components, 
                     "应该检查Elasticsearch状态")
        self.assertIn("minio", core_components, 
                     "应该检查MinIO状态")
        
        # 验证状态值
        for component_name, component_status in core_components.items():
            self.assertIn("status", component_status, 
                         f"{component_name}应该有状态信息")
            self.assertIn("message", component_status, 
                         f"{component_name}应该有状态消息")
        
        details = {
            "overall_status": validation_result.get("overall_status"),
            "core_components_status": {
                name: status.get("status") 
                for name, status in core_components.items()
            },
            "recommendations_count": len(validation_result.get("recommendations", []))
        }
        
        self.add_test_result("core_storage_validation_function", True, details)
        print("✅ 核心存储验证功能测试通过")
    
    def generate_test_summary(self):
        """生成测试总结"""
        total_tests = len(self.test_results["test_cases"])
        successful_tests = sum(1 for test in self.test_results["test_cases"] if test["success"])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": f"{success_rate:.1f}%",
            "overall_status": "PASS" if failed_tests == 0 else "FAIL",
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "test_conclusion": "",
            "key_findings": []
        }
        
        # 生成结论
        if failed_tests == 0:
            summary["test_conclusion"] = "所有测试通过，ES和MinIO作为基础必需组件的配置正确"
            summary["key_findings"].append("✅ Elasticsearch和MinIO被正确标记为基础必需组件")
            summary["key_findings"].append("✅ 混合检索功能强制启用")
            summary["key_findings"].append("✅ 存储架构配置符合预期")
            summary["key_findings"].append("✅ 部署模式相关配置正确")
        else:
            summary["test_conclusion"] = "部分测试失败，需要检查配置"
            summary["key_findings"].append("❌ 存在配置问题需要修复")
        
        self.test_results["summary"] = summary
        return summary
    
    def save_test_report(self, filename: str = None):
        """保存测试报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"core_storage_requirements_test_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            print(f"📄 测试报告已保存: {filename}")
        except Exception as e:
            print(f"❌ 保存测试报告失败: {e}")


def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 开始核心存储系统要求综合测试...")
    print("=" * 80)
    print(f"部署模式: {settings.DEPLOYMENT_MODE}")
    print(f"测试目标: 验证ES和MinIO作为基础必需组件的配置")
    print("=" * 80)
    
    # 创建测试实例
    test_instance = CoreStorageRequirementsTest()
    test_instance.setUp()
    
    # 运行测试
    test_methods = [
        test_instance.test_elasticsearch_is_core_requirement,
        test_instance.test_minio_is_core_requirement,
        test_instance.test_milvus_is_optional_enhancement,
        test_instance.test_deployment_mode_core_requirements,
        test_instance.test_storage_architecture_validation,
        test_instance.test_configuration_validation,
        test_instance.test_core_storage_validation_function
    ]
    
    print("\n🔍 执行测试用例:")
    for i, test_method in enumerate(test_methods, 1):
        try:
            print(f"\n[{i}/{len(test_methods)}] {test_method.__name__}")
            test_method()
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            test_instance.add_test_result(test_method.__name__, False, {"error": str(e)})
    
    # 生成测试总结
    print("\n📊 生成测试总结...")
    summary = test_instance.generate_test_summary()
    
    # 显示结果
    print("\n" + "=" * 80)
    print("📊 核心存储系统要求测试结果")
    print("=" * 80)
    print(f"总测试数: {summary['total_tests']}")
    print(f"成功测试: {summary['successful_tests']}")
    print(f"失败测试: {summary['failed_tests']}")
    print(f"成功率: {summary['success_rate']}")
    print(f"整体状态: {summary['overall_status']}")
    print(f"测试结论: {summary['test_conclusion']}")
    
    if summary["key_findings"]:
        print("\n🔍 关键发现:")
        for finding in summary["key_findings"]:
            print(f"  • {finding}")
    
    # 保存测试报告
    test_instance.save_test_report()
    
    return summary["overall_status"] == "PASS"


if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        
        if success:
            print("\n🎉 核心存储系统要求测试全部通过！")
            print("✅ ES和MinIO作为基础必需组件的配置正确")
            print("✅ 系统满足双存储引擎架构要求")
            sys.exit(0)
        else:
            print("\n❌ 部分测试失败！")
            print("⚠️ 请检查配置并修复问题")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程出现异常: {e}")
        sys.exit(1) 