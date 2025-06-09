#!/usr/bin/env python3
"""
核心存储系统初始化脚本
确保Elasticsearch和MinIO作为基础必需组件被正确初始化
无论在任何部署模式下都会执行此初始化过程
"""

import sys
import os
import time
import logging
from typing import Dict, Any, List
import asyncio
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

class CoreStorageInitializer:
    """核心存储系统初始化器"""
    
    def __init__(self):
        self.detector = StorageDetector()
        self.initialization_results = {
            "timestamp": datetime.now().isoformat(),
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "core_components": [],
            "summary": {}
        }
    
    def add_component_result(self, component_name: str, success: bool, details: Dict[str, Any]):
        """添加组件初始化结果"""
        self.initialization_results["core_components"].append({
            "component": component_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def wait_for_elasticsearch(self, timeout: int = 300) -> bool:
        """等待Elasticsearch服务就绪"""
        logger.info("🔍 等待Elasticsearch服务就绪 (基础必需组件)...")
        
        for attempt in range(timeout):
            try:
                if self.detector.check_elasticsearch():
                    logger.info("✅ Elasticsearch服务已就绪")
                    return True
            except Exception as e:
                logger.debug(f"Elasticsearch检查失败: {e}")
            
            time.sleep(1)
            if attempt % 30 == 0 and attempt > 0:
                logger.info(f"等待中... ({attempt}/{timeout}秒)")
        
        logger.error("❌ Elasticsearch服务未在指定时间内就绪")
        return False
    
    def wait_for_minio(self, timeout: int = 300) -> bool:
        """等待MinIO服务就绪"""
        logger.info("📁 等待MinIO服务就绪 (基础必需组件)...")
        
        for attempt in range(timeout):
            try:
                if self.detector.check_minio():
                    logger.info("✅ MinIO服务已就绪")
                    return True
            except Exception as e:
                logger.debug(f"MinIO检查失败: {e}")
            
            time.sleep(1)
            if attempt % 30 == 0 and attempt > 0:
                logger.info(f"等待中... ({attempt}/{timeout}秒)")
        
        logger.error("❌ MinIO服务未在指定时间内就绪")
        return False
    
    def initialize_elasticsearch(self) -> bool:
        """初始化Elasticsearch"""
        logger.info("🔧 初始化Elasticsearch混合检索配置...")
        
        try:
            # 运行ES初始化脚本
            import subprocess
            result = subprocess.run(
                [sys.executable, "scripts/init_elasticsearch.py"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            success = result.returncode == 0
            details = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr if result.stderr else None,
                "config": {
                    "url": settings.ELASTICSEARCH_URL,
                    "index": settings.ELASTICSEARCH_INDEX,
                    "hybrid_search": settings.ELASTICSEARCH_HYBRID_SEARCH,
                    "hybrid_weight": settings.ELASTICSEARCH_HYBRID_WEIGHT
                }
            }
            
            self.add_component_result("elasticsearch", success, details)
            
            if success:
                logger.info("✅ Elasticsearch初始化成功")
            else:
                logger.error(f"❌ Elasticsearch初始化失败: {result.stderr}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Elasticsearch初始化异常: {e}")
            self.add_component_result("elasticsearch", False, {"error": str(e)})
            return False
    
    def initialize_minio(self) -> bool:
        """初始化MinIO"""
        logger.info("🔧 初始化MinIO对象存储配置...")
        
        try:
            # 运行MinIO初始化脚本
            import subprocess
            result = subprocess.run(
                [sys.executable, "scripts/init_minio.py"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            success = result.returncode == 0
            details = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr if result.stderr else None,
                "config": {
                    "endpoint": settings.MINIO_ENDPOINT,
                    "bucket": settings.MINIO_BUCKET,
                    "secure": settings.MINIO_SECURE
                }
            }
            
            self.add_component_result("minio", success, details)
            
            if success:
                logger.info("✅ MinIO初始化成功")
            else:
                logger.error(f"❌ MinIO初始化失败: {result.stderr}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ MinIO初始化异常: {e}")
            self.add_component_result("minio", False, {"error": str(e)})
            return False
    
    def validate_core_storage(self) -> bool:
        """验证核心存储组件"""
        logger.info("🔍 验证核心存储组件状态...")
        
        validation_result = self.detector.validate_core_storage()
        
        is_healthy = validation_result["overall_status"] == "healthy"
        
        details = {
            "overall_status": validation_result["overall_status"],
            "elasticsearch_status": validation_result["core_components"]["elasticsearch"]["status"],
            "minio_status": validation_result["core_components"]["minio"]["status"],
            "recommendations": validation_result["recommendations"]
        }
        
        self.add_component_result("validation", is_healthy, details)
        
        if is_healthy:
            logger.info("✅ 核心存储组件验证通过")
        else:
            logger.error("❌ 核心存储组件验证失败")
            for rec in validation_result["recommendations"]:
                logger.error(f"   • {rec}")
        
        return is_healthy
    
    def generate_summary(self) -> Dict[str, Any]:
        """生成初始化总结"""
        total_components = len(self.initialization_results["core_components"])
        successful_components = sum(1 for comp in self.initialization_results["core_components"] if comp["success"])
        failed_components = total_components - successful_components
        
        success_rate = (successful_components / total_components * 100) if total_components > 0 else 0
        
        summary = {
            "total_components": total_components,
            "successful_components": successful_components,
            "failed_components": failed_components,
            "success_rate": f"{success_rate:.1f}%",
            "overall_status": "SUCCESS" if failed_components == 0 else "FAILURE",
            "core_storage_ready": successful_components >= 2,  # ES + MinIO
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "critical_failures": [],
            "warnings": [],
            "next_steps": []
        }
        
        # 检查关键失败
        for comp in self.initialization_results["core_components"]:
            if not comp["success"] and comp["component"] in ["elasticsearch", "minio"]:
                summary["critical_failures"].append(f"{comp['component']} 初始化失败")
        
        # 生成下一步建议
        if summary["core_storage_ready"]:
            summary["next_steps"].append("核心存储系统已就绪，可以启动应用程序")
        else:
            summary["next_steps"].append("请解决核心存储组件问题后重新初始化")
        
        # 根据部署模式提供建议
        if settings.DEPLOYMENT_MODE == "minimal":
            summary["next_steps"].append("最小化模式：仅需要Elasticsearch和MinIO正常工作")
        elif settings.DEPLOYMENT_MODE == "standard":
            summary["next_steps"].append("标准模式：建议检查Milvus和Nacos服务状态")
        elif settings.DEPLOYMENT_MODE == "production":
            summary["next_steps"].append("生产模式：建议启用完整监控和告警系统")
        
        self.initialization_results["summary"] = summary
        return summary
    
    def run_core_initialization(self) -> bool:
        """运行核心存储系统初始化"""
        logger.info("🚀 开始核心存储系统初始化...")
        logger.info("=" * 80)
        logger.info(f"部署模式: {settings.DEPLOYMENT_MODE}")
        logger.info(f"核心组件: Elasticsearch + MinIO (基础必需)")
        logger.info("=" * 80)
        
        # Step 1: 等待服务就绪
        logger.info("\n📋 Step 1: 等待核心服务就绪")
        
        es_ready = self.wait_for_elasticsearch()
        minio_ready = self.wait_for_minio()
        
        if not es_ready or not minio_ready:
            logger.error("❌ 核心服务未就绪，无法继续初始化")
            return False
        
        # Step 2: 初始化存储组件
        logger.info("\n📋 Step 2: 初始化存储组件")
        
        es_init_success = self.initialize_elasticsearch()
        minio_init_success = self.initialize_minio()
        
        # Step 3: 验证存储系统
        logger.info("\n📋 Step 3: 验证存储系统")
        
        validation_success = self.validate_core_storage()
        
        # Step 4: 生成总结
        logger.info("\n📋 Step 4: 生成初始化总结")
        
        summary = self.generate_summary()
        
        # 显示结果
        logger.info("\n" + "=" * 80)
        logger.info("📊 核心存储系统初始化结果")
        logger.info("=" * 80)
        logger.info(f"总组件数: {summary['total_components']}")
        logger.info(f"成功组件: {summary['successful_components']}")
        logger.info(f"失败组件: {summary['failed_components']}")
        logger.info(f"成功率: {summary['success_rate']}")
        logger.info(f"整体状态: {summary['overall_status']}")
        logger.info(f"核心存储就绪: {'是' if summary['core_storage_ready'] else '否'}")
        
        if summary["critical_failures"]:
            logger.error("\n❌ 关键失败:")
            for failure in summary["critical_failures"]:
                logger.error(f"  • {failure}")
        
        if summary["warnings"]:
            logger.warning("\n⚠️ 警告:")
            for warning in summary["warnings"]:
                logger.warning(f"  • {warning}")
        
        if summary["next_steps"]:
            logger.info("\n💡 下一步:")
            for step in summary["next_steps"]:
                logger.info(f"  • {step}")
        
        # 显示存储架构信息
        storage_info = self.detector.get_vector_store_info()
        logger.info("\n🏗️ 存储架构状态:")
        logger.info(f"  架构类型: {storage_info['storage_architecture']['type']}")
        logger.info(f"  部署模式: {storage_info['deployment_mode']}")
        logger.info(f"  文件存储: {storage_info['storage_architecture']['file_storage_engine']}")
        logger.info(f"  检索引擎: {storage_info['storage_architecture']['search_engine']}")
        logger.info(f"  混合检索: {'启用' if storage_info['hybrid_search_status']['enabled'] else '禁用'}")
        
        return summary["core_storage_ready"]
    
    def save_initialization_report(self, filename: str = None):
        """保存初始化报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"core_storage_init_report_{timestamp}.json"
        
        try:
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.initialization_results, f, indent=2, ensure_ascii=False)
            logger.info(f"📄 初始化报告已保存: {filename}")
        except Exception as e:
            logger.error(f"保存初始化报告失败: {e}")


def main():
    """主函数"""
    initializer = CoreStorageInitializer()
    
    try:
        # 运行核心存储系统初始化
        success = initializer.run_core_initialization()
        
        # 保存初始化报告
        initializer.save_initialization_report()
        
        # 返回结果
        if success:
            print("\n🎉 核心存储系统初始化成功！")
            print("✅ Elasticsearch和MinIO双存储引擎已就绪")
            print("✅ 系统可以开始处理文件上传和文档检索")
            print("\n📋 核心功能可用:")
            print("   📁 文件上传存储 (MinIO)")
            print("   🔍 文档分片检索 (Elasticsearch)")
            print("   🤖 混合搜索算法 (语义+关键词)")
            
            # 根据部署模式显示不同信息
            if settings.DEPLOYMENT_MODE == "minimal":
                print("\n💡 最小化模式:")
                print("   仅启用核心功能，适合开发和测试环境")
            elif settings.DEPLOYMENT_MODE == "standard":
                print("\n💡 标准模式:")
                print("   可考虑启用Milvus以获得更好的向量搜索性能")
            elif settings.DEPLOYMENT_MODE == "production":
                print("\n💡 生产模式:")
                print("   建议启用完整监控和告警系统")
            
            sys.exit(0)
        else:
            print("\n❌ 核心存储系统初始化失败！")
            print("⚠️ 请检查以下组件的状态:")
            print("   • Elasticsearch服务是否正常运行")
            print("   • MinIO服务是否正常运行")
            print("   • 网络连接是否正常")
            print("   • 配置参数是否正确")
            print("\n💡 可以尝试:")
            print("   1. 检查Docker Compose服务状态")
            print("   2. 查看服务日志排查问题")
            print("   3. 重新运行初始化脚本")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("初始化过程被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"初始化过程出现异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 