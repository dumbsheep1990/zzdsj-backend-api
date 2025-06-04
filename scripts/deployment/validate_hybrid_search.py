#!/usr/bin/env python3
"""
混合检索配置验证脚本
检查系统中所有混合检索相关的配置是否正确设置
确保ES存储、配置参数、环境变量等都符合要求
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.config import settings
    from app.utils.storage.detection import StorageDetector  
    from elasticsearch import Elasticsearch
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HybridSearchValidator:
    """混合检索配置验证器"""
    
    def __init__(self):
        self.validation_results = []
        self.errors = []
        self.warnings = []
        
    def add_result(self, component: str, check: str, status: bool, 
                   details: str = "", level: str = "info"):
        """添加验证结果"""
        result = {
            "component": component,
            "check": check,
            "status": status,
            "details": details,
            "level": level
        }
        self.validation_results.append(result)
        
        if not status and level == "error":
            self.errors.append(f"{component} - {check}: {details}")
        elif not status and level == "warning":
            self.warnings.append(f"{component} - {check}: {details}")
    
    def validate_environment_variables(self) -> bool:
        """验证环境变量配置"""
        logger.info("验证环境变量配置...")
        all_valid = True
        
        # 必需的ES配置
        required_vars = {
            "ELASTICSEARCH_URL": os.getenv("ELASTICSEARCH_URL"),
            "ELASTICSEARCH_HYBRID_SEARCH": os.getenv("ELASTICSEARCH_HYBRID_SEARCH"),
            "ELASTICSEARCH_HYBRID_WEIGHT": os.getenv("ELASTICSEARCH_HYBRID_WEIGHT")
        }
        
        for var_name, var_value in required_vars.items():
            if var_value is None:
                self.add_result(
                    "环境变量", var_name, False,
                    f"环境变量未设置，将使用默认值", "warning"
                )
            else:
                self.add_result(
                    "环境变量", var_name, True,
                    f"值: {var_value}"
                )
        
        # 验证混合检索开关
        hybrid_enabled = str(os.getenv("ELASTICSEARCH_HYBRID_SEARCH", "true")).lower()
        if hybrid_enabled != "true":
            self.add_result(
                "环境变量", "ELASTICSEARCH_HYBRID_SEARCH", False,
                f"混合检索未启用 (值: {hybrid_enabled})，这将影响搜索质量", "error"
            )
            all_valid = False
        else:
            self.add_result(
                "环境变量", "ELASTICSEARCH_HYBRID_SEARCH", True,
                "混合检索已启用"
            )
        
        # 验证权重配置
        try:
            weight = float(os.getenv("ELASTICSEARCH_HYBRID_WEIGHT", "0.7"))
            if not 0.0 <= weight <= 1.0:
                self.add_result(
                    "环境变量", "ELASTICSEARCH_HYBRID_WEIGHT", False,
                    f"权重值超出范围 (0-1): {weight}", "error"
                )
                all_valid = False
            elif weight < 0.5:
                self.add_result(
                    "环境变量", "ELASTICSEARCH_HYBRID_WEIGHT", True,
                    f"当前权重 {weight} 偏向关键词搜索", "warning"
                )
            else:
                self.add_result(
                    "环境变量", "ELASTICSEARCH_HYBRID_WEIGHT", True,
                    f"权重配置合理: {weight} (语义搜索优先)"
                )
        except ValueError:
            self.add_result(
                "环境变量", "ELASTICSEARCH_HYBRID_WEIGHT", False,
                "权重值格式错误，无法转换为浮点数", "error"
            )
            all_valid = False
        
        return all_valid
    
    def validate_settings_configuration(self) -> bool:
        """验证Settings类配置"""
        logger.info("验证Settings类配置...")
        all_valid = True
        
        try:
            # 检查基本配置
            self.add_result(
                "Settings配置", "ELASTICSEARCH_URL", True,
                f"值: {settings.ELASTICSEARCH_URL}"
            )
            
            # 检查混合检索配置
            if hasattr(settings, "ELASTICSEARCH_HYBRID_SEARCH"):
                if settings.ELASTICSEARCH_HYBRID_SEARCH:
                    self.add_result(
                        "Settings配置", "ELASTICSEARCH_HYBRID_SEARCH", True,
                        "混合检索已启用"
                    )
                else:
                    self.add_result(
                        "Settings配置", "ELASTICSEARCH_HYBRID_SEARCH", False,
                        "混合检索未启用", "error"
                    )
                    all_valid = False
            else:
                self.add_result(
                    "Settings配置", "ELASTICSEARCH_HYBRID_SEARCH", False,
                    "混合检索配置缺失", "error"
                )
                all_valid = False
            
            # 检查权重配置
            if hasattr(settings, "ELASTICSEARCH_HYBRID_WEIGHT"):
                weight = settings.ELASTICSEARCH_HYBRID_WEIGHT
                if 0.0 <= weight <= 1.0:
                    self.add_result(
                        "Settings配置", "ELASTICSEARCH_HYBRID_WEIGHT", True,
                        f"权重: {weight}"
                    )
                else:
                    self.add_result(
                        "Settings配置", "ELASTICSEARCH_HYBRID_WEIGHT", False,
                        f"权重超出范围: {weight}", "error"
                    )
                    all_valid = False
            else:
                self.add_result(
                    "Settings配置", "ELASTICSEARCH_HYBRID_WEIGHT", False,
                    "权重配置缺失", "error"
                )
                all_valid = False
            
        except Exception as e:
            self.add_result(
                "Settings配置", "配置访问", False,
                f"无法访问配置: {str(e)}", "error"
            )
            all_valid = False
        
        return all_valid
    
    def validate_elasticsearch_connection(self) -> bool:
        """验证Elasticsearch连接"""
        logger.info("验证Elasticsearch连接...")
        all_valid = True
        
        try:
            # 构建ES客户端
            es_kwargs = {}
            if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
                es_kwargs["basic_auth"] = (settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
            if settings.ELASTICSEARCH_API_KEY:
                es_kwargs["api_key"] = settings.ELASTICSEARCH_API_KEY
            
            es = Elasticsearch(settings.ELASTICSEARCH_URL, **es_kwargs)
            
            # 测试连接
            health = es.cluster.health()
            status = health.get("status", "unknown")
            
            if status in ["green", "yellow"]:
                self.add_result(
                    "Elasticsearch连接", "健康检查", True,
                    f"集群状态: {status}"
                )
            else:
                self.add_result(
                    "Elasticsearch连接", "健康检查", False,
                    f"集群状态异常: {status}", "warning"
                )
            
            # 检查版本
            info = es.info()
            version = info.get("version", {}).get("number", "unknown")
            self.add_result(
                "Elasticsearch连接", "版本信息", True,
                f"版本: {version}"
            )
            
        except Exception as e:
            self.add_result(
                "Elasticsearch连接", "连接测试", False,
                f"连接失败: {str(e)}", "error"
            )
            all_valid = False
        
        return all_valid
    
    def validate_storage_detector(self) -> bool:
        """验证存储检测器配置"""
        logger.info("验证存储检测器配置...")
        all_valid = True
        
        try:
            # 获取存储信息
            storage_info = StorageDetector.get_vector_store_info()
            
            # 检查ES可用性
            es_info = storage_info.get("elasticsearch", {})
            if es_info.get("available", False):
                self.add_result(
                    "存储检测器", "Elasticsearch可用性", True,
                    "Elasticsearch可用"
                )
            else:
                self.add_result(
                    "存储检测器", "Elasticsearch可用性", False,
                    "Elasticsearch不可用", "error"
                )
                all_valid = False
            
            # 检查混合检索配置
            if es_info.get("hybrid_search", False):
                self.add_result(
                    "存储检测器", "混合检索配置", True,
                    f"权重: {es_info.get('hybrid_weight', 'unknown')}"
                )
            else:
                self.add_result(
                    "存储检测器", "混合检索配置", False,
                    "混合检索未配置", "error"
                )
                all_valid = False
            
            # 检查策略
            strategy = storage_info.get("strategy", "unknown")
            if strategy in ["hybrid", "elasticsearch"]:
                self.add_result(
                    "存储检测器", "存储策略", True,
                    f"策略: {strategy}"
                )
            else:
                self.add_result(
                    "存储检测器", "存储策略", False,
                    f"策略不支持混合检索: {strategy}", "warning"
                )
            
        except Exception as e:
            self.add_result(
                "存储检测器", "配置检查", False,
                f"检查失败: {str(e)}", "error"
            )
            all_valid = False
        
        return all_valid
    
    def validate_docker_configuration(self) -> bool:
        """验证Docker配置"""
        logger.info("验证Docker配置...")
        all_valid = True
        
        docker_compose_path = project_root / "docker-compose.yml"
        
        if docker_compose_path.exists():
            try:
                with open(docker_compose_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查Elasticsearch服务
                if "elasticsearch:" in content:
                    self.add_result(
                        "Docker配置", "Elasticsearch服务", True,
                        "Docker Compose中包含Elasticsearch服务"
                    )
                else:
                    self.add_result(
                        "Docker配置", "Elasticsearch服务", False,
                        "Docker Compose中缺少Elasticsearch服务", "error"
                    )
                    all_valid = False
                
                # 检查环境变量设置
                if "ELASTICSEARCH_HYBRID_SEARCH=true" in content:
                    self.add_result(
                        "Docker配置", "混合检索环境变量", True,
                        "Docker中已配置混合检索环境变量"
                    )
                else:
                    self.add_result(
                        "Docker配置", "混合检索环境变量", False,
                        "Docker中缺少混合检索环境变量配置", "warning"
                    )
                
            except Exception as e:
                self.add_result(
                    "Docker配置", "文件读取", False,
                    f"无法读取docker-compose.yml: {str(e)}", "error"
                )
                all_valid = False
        else:
            self.add_result(
                "Docker配置", "配置文件", False,
                "docker-compose.yml文件不存在", "warning"
            )
        
        return all_valid
    
    def validate_all(self) -> Tuple[bool, Dict[str, Any]]:
        """执行所有验证"""
        logger.info("开始混合检索配置验证...")
        
        validations = [
            ("环境变量", self.validate_environment_variables),
            ("Settings配置", self.validate_settings_configuration), 
            ("Elasticsearch连接", self.validate_elasticsearch_connection),
            ("存储检测器", self.validate_storage_detector),
            ("Docker配置", self.validate_docker_configuration)
        ]
        
        success_count = 0
        for name, validation_func in validations:
            try:
                if validation_func():
                    success_count += 1
                    logger.info(f"✅ {name} 验证通过")
                else:
                    logger.warning(f"⚠️ {name} 验证存在问题")
            except Exception as e:
                logger.error(f"❌ {name} 验证失败: {str(e)}")
        
        # 生成验证报告
        report = {
            "summary": {
                "total_validations": len(validations),
                "passed_validations": success_count,
                "success_rate": success_count / len(validations) * 100,
                "errors_count": len(self.errors),
                "warnings_count": len(self.warnings)
            },
            "results": self.validation_results,
            "errors": self.errors,
            "warnings": self.warnings,
            "recommendations": self._generate_recommendations()
        }
        
        overall_success = len(self.errors) == 0
        return overall_success, report
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if len(self.errors) > 0:
            recommendations.append("🔧 发现严重配置问题，请立即修复以下错误:")
            for error in self.errors:
                recommendations.append(f"   • {error}")
        
        if len(self.warnings) > 0:
            recommendations.append("⚠️ 发现配置警告，建议优化以下项目:")
            for warning in self.warnings:
                recommendations.append(f"   • {warning}")
        
        # 通用建议
        recommendations.extend([
            "",
            "💡 混合检索最佳实践建议:",
            "   • 保持 ELASTICSEARCH_HYBRID_SEARCH=true",
            "   • 建议 ELASTICSEARCH_HYBRID_WEIGHT=0.7 (语义搜索优先)",
            "   • 确保Elasticsearch服务在Docker Compose中正确配置",
            "   • 使用scripts/start_with_hybrid_search.sh启动系统",
            "   • 定期运行此验证脚本检查配置状态"
        ])
        
        return recommendations


def print_report(success: bool, report: Dict[str, Any]):
    """打印验证报告"""
    print("\n" + "="*60)
    print("🔍 混合检索配置验证报告")
    print("="*60)
    
    summary = report["summary"]
    print(f"\n📊 验证统计:")
    print(f"   总验证项: {summary['total_validations']}")
    print(f"   通过验证: {summary['passed_validations']}")
    print(f"   成功率: {summary['success_rate']:.1f}%")
    print(f"   错误数: {summary['errors_count']}")
    print(f"   警告数: {summary['warnings_count']}")
    
    # 详细结果
    print(f"\n📋 详细验证结果:")
    for result in report["results"]:
        status_icon = "✅" if result["status"] else ("❌" if result["level"] == "error" else "⚠️")
        print(f"   {status_icon} {result['component']} - {result['check']}")
        if result["details"]:
            print(f"      └─ {result['details']}")
    
    # 错误和警告
    if report["errors"]:
        print(f"\n❌ 错误列表:")
        for error in report["errors"]:
            print(f"   • {error}")
    
    if report["warnings"]:
        print(f"\n⚠️ 警告列表:")
        for warning in report["warnings"]:
            print(f"   • {warning}")
    
    # 建议
    print(f"\n💡 改进建议:")
    for rec in report["recommendations"]:
        print(rec)
    
    # 总结
    print(f"\n{'='*60}")
    if success:
        print("🎉 验证成功! 混合检索配置正确，系统可以正常使用混合检索功能。")
    else:
        print("❌ 验证失败! 请根据以上错误和建议修复配置问题。")
    print("="*60)


def main():
    """主函数"""
    try:
        validator = HybridSearchValidator()
        success, report = validator.validate_all()
        
        print_report(success, report)
        
        # 保存报告到文件
        report_file = project_root / "validation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"验证过程中发生异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 