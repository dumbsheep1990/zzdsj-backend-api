#!/usr/bin/env python3
"""
存储系统验证脚本
检查MinIO和Elasticsearch的配置、连接状态和功能完整性
确保双存储引擎架构正常工作
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any, List
import json
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.utils.storage.storage_detector import StorageDetector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StorageSystemValidator:
    """存储系统验证器"""
    
    def __init__(self):
        self.detector = StorageDetector()
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
    
    def add_test_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """添加测试结果"""
        self.validation_results["tests"].append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_elasticsearch_connection(self) -> bool:
        """测试Elasticsearch连接"""
        logger.info("🔍 测试Elasticsearch连接...")
        
        try:
            from elasticsearch import Elasticsearch
            
            # 创建ES客户端
            es_client_kwargs = {}
            if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
                es_client_kwargs["basic_auth"] = (settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
            
            es = Elasticsearch(settings.ELASTICSEARCH_URL, **es_client_kwargs)
            
            # 测试集群健康状态
            health = es.cluster.health()
            cluster_status = health.get('status', 'unknown')
            
            # 测试索引操作
            index_exists = es.indices.exists(index=settings.ELASTICSEARCH_INDEX)
            
            details = {
                "url": settings.ELASTICSEARCH_URL,
                "cluster_status": cluster_status,
                "index_exists": index_exists,
                "index_name": settings.ELASTICSEARCH_INDEX,
                "cluster_info": {
                    "cluster_name": health.get('cluster_name'),
                    "number_of_nodes": health.get('number_of_nodes'),
                    "number_of_data_nodes": health.get('number_of_data_nodes')
                }
            }
            
            success = cluster_status in ['green', 'yellow']
            self.add_test_result("elasticsearch_connection", success, details)
            
            if success:
                logger.info(f"✅ Elasticsearch连接成功 - 状态: {cluster_status}")
            else:
                logger.error(f"❌ Elasticsearch连接失败 - 状态: {cluster_status}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Elasticsearch连接测试失败: {e}")
            self.add_test_result("elasticsearch_connection", False, {"error": str(e)})
            return False
    
    def test_minio_connection(self) -> bool:
        """测试MinIO连接"""
        logger.info("📁 测试MinIO连接...")
        
        try:
            from minio import Minio
            
            # 创建MinIO客户端
            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # 测试连接 - 列出存储桶
            buckets = list(client.list_buckets())
            bucket_exists = client.bucket_exists(settings.MINIO_BUCKET)
            
            details = {
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket_name": settings.MINIO_BUCKET,
                "bucket_exists": bucket_exists,
                "total_buckets": len(buckets),
                "secure": settings.MINIO_SECURE,
                "buckets": [{"name": b.name, "creation_date": b.creation_date.isoformat() if b.creation_date else None} for b in buckets]
            }
            
            success = True
            self.add_test_result("minio_connection", success, details)
            
            logger.info(f"✅ MinIO连接成功 - 存储桶数量: {len(buckets)}, 默认存储桶存在: {bucket_exists}")
            return success
            
        except Exception as e:
            logger.error(f"❌ MinIO连接测试失败: {e}")
            self.add_test_result("minio_connection", False, {"error": str(e)})
            return False
    
    def test_hybrid_search_config(self) -> bool:
        """测试混合检索配置"""
        logger.info("🔍 测试混合检索配置...")
        
        try:
            hybrid_enabled = getattr(settings, "ELASTICSEARCH_HYBRID_SEARCH", False)
            hybrid_weight = getattr(settings, "ELASTICSEARCH_HYBRID_WEIGHT", 0.5)
            
            details = {
                "hybrid_search_enabled": hybrid_enabled,
                "hybrid_weight": hybrid_weight,
                "semantic_weight": hybrid_weight,
                "keyword_weight": 1.0 - hybrid_weight,
                "recommended_weight": 0.7,
                "configuration_optimal": hybrid_enabled and 0.6 <= hybrid_weight <= 0.8
            }
            
            success = hybrid_enabled
            self.add_test_result("hybrid_search_config", success, details)
            
            if success:
                logger.info(f"✅ 混合检索已启用 - 权重配置: 语义搜索({hybrid_weight:.1f}) + 关键词搜索({1.0-hybrid_weight:.1f})")
            else:
                logger.warning("⚠️ 混合检索未启用")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 混合检索配置测试失败: {e}")
            self.add_test_result("hybrid_search_config", False, {"error": str(e)})
            return False
    
    def test_file_upload_simulation(self) -> bool:
        """测试文件上传模拟"""
        logger.info("📂 测试文件上传流程...")
        
        try:
            from app.utils.file_upload import FileUploadManager
            import tempfile
            import io
            from fastapi import UploadFile
            
            # 创建模拟文件
            test_content = "这是一个测试文档，用于验证文件上传功能。"
            test_file = io.BytesIO(test_content.encode('utf-8'))
            
            # 创建UploadFile对象
            upload_file = UploadFile(
                filename="test_document.txt",
                file=test_file,
                headers={"content-type": "text/plain"}
            )
            
            # 测试文件验证
            manager = FileUploadManager()
            is_valid, file_category, error_msg = manager.validate_file(upload_file)
            
            details = {
                "file_validation": {
                    "is_valid": is_valid,
                    "file_category": file_category,
                    "error_message": error_msg if not is_valid else None
                },
                "supported_types": manager.get_supported_types(),
                "max_file_sizes": manager.get_max_file_sizes()
            }
            
            success = is_valid
            self.add_test_result("file_upload_simulation", success, details)
            
            if success:
                logger.info(f"✅ 文件上传验证成功 - 文件类型: {file_category}")
            else:
                logger.error(f"❌ 文件上传验证失败: {error_msg}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 文件上传测试失败: {e}")
            self.add_test_result("file_upload_simulation", False, {"error": str(e)})
            return False
    
    def test_storage_architecture(self) -> bool:
        """测试存储架构"""
        logger.info("🏗️ 测试存储架构...")
        
        try:
            storage_info = self.detector.get_vector_store_info()
            requirements = self.detector.get_system_requirements()
            
            # 检查必需服务
            required_services_available = all(
                service["available"] for service in requirements["required_services"]
            )
            
            # 检查架构类型
            architecture = storage_info.get("storage_architecture", {})
            is_dual_engine = architecture.get("type") == "dual_engine"
            
            details = {
                "storage_strategy": storage_info["strategy"],
                "architecture_type": architecture.get("type"),
                "file_storage_engine": architecture.get("file_storage"),
                "search_engine": architecture.get("search_engine"),
                "is_dual_engine": is_dual_engine,
                "required_services_available": required_services_available,
                "architecture_description": architecture.get("architecture_description"),
                "services_status": {
                    "elasticsearch": storage_info["elasticsearch"]["available"],
                    "minio": storage_info["minio"]["available"],
                    "milvus": storage_info["milvus"]["available"]
                }
            }
            
            success = required_services_available and is_dual_engine
            self.add_test_result("storage_architecture", success, details)
            
            if success:
                logger.info("✅ 存储架构验证成功 - 双存储引擎架构正常")
            else:
                logger.warning("⚠️ 存储架构不完整 - 缺少必需服务或非双引擎架构")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 存储架构测试失败: {e}")
            self.add_test_result("storage_architecture", False, {"error": str(e)})
            return False
    
    def generate_summary(self) -> Dict[str, Any]:
        """生成验证总结"""
        total_tests = len(self.validation_results["tests"])
        passed_tests = sum(1 for test in self.validation_results["tests"] if test["success"])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": f"{success_rate:.1f}%",
            "overall_status": "PASS" if failed_tests == 0 else "FAIL",
            "critical_issues": [],
            "recommendations": []
        }
        
        # 检查关键问题
        for test in self.validation_results["tests"]:
            if not test["success"]:
                if test["test_name"] in ["elasticsearch_connection", "minio_connection"]:
                    summary["critical_issues"].append(f"关键服务不可用: {test['test_name']}")
        
        # 生成建议
        if "elasticsearch_connection" not in [t["test_name"] for t in self.validation_results["tests"] if t["success"]]:
            summary["recommendations"].append("请检查Elasticsearch服务状态和配置")
        
        if "minio_connection" not in [t["test_name"] for t in self.validation_results["tests"] if t["success"]]:
            summary["recommendations"].append("请检查MinIO服务状态和配置")
        
        if "hybrid_search_config" not in [t["test_name"] for t in self.validation_results["tests"] if t["success"]]:
            summary["recommendations"].append("请启用混合检索功能以获得最佳搜索体验")
        
        self.validation_results["summary"] = summary
        return summary
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        logger.info("🚀 开始存储系统验证...")
        logger.info("=" * 60)
        
        # 运行各项测试
        tests = [
            ("Elasticsearch连接", self.test_elasticsearch_connection),
            ("MinIO连接", self.test_minio_connection),
            ("混合检索配置", self.test_hybrid_search_config),
            ("文件上传流程", self.test_file_upload_simulation),
            ("存储架构", self.test_storage_architecture)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n📋 执行测试: {test_name}")
            test_func()
        
        # 生成总结
        summary = self.generate_summary()
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 验证结果总结")
        logger.info("=" * 60)
        logger.info(f"总测试数: {summary['total_tests']}")
        logger.info(f"通过测试: {summary['passed_tests']}")
        logger.info(f"失败测试: {summary['failed_tests']}")
        logger.info(f"成功率: {summary['success_rate']}")
        logger.info(f"整体状态: {summary['overall_status']}")
        
        if summary["critical_issues"]:
            logger.error("\n❌ 关键问题:")
            for issue in summary["critical_issues"]:
                logger.error(f"  • {issue}")
        
        if summary["recommendations"]:
            logger.info("\n💡 建议:")
            for rec in summary["recommendations"]:
                logger.info(f"  • {rec}")
        
        # 显示架构状态
        logger.info("\n🏗️ 当前存储架构:")
        for test in self.validation_results["tests"]:
            if test["test_name"] == "storage_architecture" and test["success"]:
                details = test["details"]
                logger.info(f"  📁 文件存储: {details['file_storage_engine']}")
                logger.info(f"  🔍 搜索引擎: {details['search_engine']}")
                logger.info(f"  ⚙️ 架构类型: {details['architecture_type']}")
                logger.info(f"  📖 描述: {details['architecture_description']}")
                break
        
        return summary["overall_status"] == "PASS"
    
    def save_report(self, filename: str = None):
        """保存验证报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"storage_validation_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
            logger.info(f"📄 验证报告已保存: {filename}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")


def main():
    """主函数"""
    validator = StorageSystemValidator()
    
    try:
        # 运行所有测试
        success = validator.run_all_tests()
        
        # 保存报告
        validator.save_report()
        
        # 返回结果
        if success:
            print("\n🎉 存储系统验证通过！")
            print("✅ MinIO和Elasticsearch双存储引擎架构正常工作")
            print("✅ 系统已准备好处理文件上传和混合检索")
            sys.exit(0)
        else:
            print("\n❌ 存储系统验证失败！")
            print("⚠️ 请检查日志和验证报告以了解详情")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("验证过程被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"验证过程出现异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 