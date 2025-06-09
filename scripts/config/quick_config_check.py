#!/usr/bin/env python3
"""
快速配置检查脚本
验证Elasticsearch和MinIO作为基础必需组件的配置是否正确
适用于快速验证和日常检查
"""

import sys
import os
from typing import Dict, Any, List

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.utils.storage.storage_detector import StorageDetector

def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title: str):
    """打印章节"""
    print(f"\n📋 {title}")
    print("-" * 40)

def print_check(item: str, status: bool, details: str = ""):
    """打印检查项"""
    icon = "✅" if status else "❌"
    print(f"{icon} {item}")
    if details:
        print(f"   💡 {details}")

def check_basic_configuration():
    """检查基础配置"""
    print_section("基础配置检查")
    
    # 检查部署模式
    print_check(f"部署模式: {settings.DEPLOYMENT_MODE}", True, 
               f"当前使用 {settings.DEPLOYMENT_MODE} 模式")
    
    # 检查Elasticsearch配置
    es_configured = bool(settings.ELASTICSEARCH_URL)
    print_check("Elasticsearch URL配置", es_configured, 
               f"URL: {settings.ELASTICSEARCH_URL}")
    
    # 检查混合检索强制启用
    hybrid_enabled = settings.ELASTICSEARCH_HYBRID_SEARCH
    print_check("混合检索强制启用", hybrid_enabled, 
               f"权重: {settings.ELASTICSEARCH_HYBRID_WEIGHT}")
    
    # 检查MinIO配置
    minio_configured = bool(settings.MINIO_ENDPOINT and settings.MINIO_BUCKET)
    print_check("MinIO基础配置", minio_configured, 
               f"端点: {settings.MINIO_ENDPOINT}, 存储桶: {settings.MINIO_BUCKET}")
    
    return es_configured and hybrid_enabled and minio_configured

def check_core_components():
    """检查核心组件标识"""
    print_section("核心组件标识检查")
    
    detector = StorageDetector()
    storage_info = detector.get_vector_store_info()
    
    # 检查Elasticsearch核心组件标识
    es_config = storage_info.get("elasticsearch", {})
    es_is_required = es_config.get("is_required", False)
    es_is_core = es_config.get("component_type") == "core"
    print_check("Elasticsearch核心组件标识", es_is_required and es_is_core,
               f"必需: {es_is_required}, 类型: {es_config.get('component_type')}")
    
    # 检查MinIO核心组件标识
    minio_config = storage_info.get("minio", {})
    minio_is_required = minio_config.get("is_required", False)
    minio_is_core = minio_config.get("component_type") == "core"
    print_check("MinIO核心组件标识", minio_is_required and minio_is_core,
               f"必需: {minio_is_required}, 类型: {minio_config.get('component_type')}")
    
    # 检查Milvus可选组件标识
    milvus_config = storage_info.get("milvus", {})
    milvus_is_optional = not milvus_config.get("is_required", True)
    milvus_is_enhancement = milvus_config.get("component_type") == "enhancement"
    print_check("Milvus可选组件标识", milvus_is_optional and milvus_is_enhancement,
               f"必需: {milvus_config.get('is_required')}, 类型: {milvus_config.get('component_type')}")
    
    return es_is_required and es_is_core and minio_is_required and minio_is_core

def check_storage_architecture():
    """检查存储架构"""
    print_section("存储架构检查")
    
    detector = StorageDetector()
    storage_info = detector.get_vector_store_info()
    architecture = storage_info.get("storage_architecture", {})
    
    # 检查架构类型
    arch_type = architecture.get("type")
    is_dual_engine = arch_type in ["dual_engine", "insufficient"]
    print_check("双存储引擎架构", is_dual_engine,
               f"架构类型: {arch_type}")
    
    # 检查核心组件列表
    core_components = architecture.get("core_components", [])
    has_es_minio = "elasticsearch" in core_components and "minio" in core_components
    print_check("核心组件完整性", has_es_minio,
               f"核心组件: {core_components}")
    
    # 检查文件存储引擎
    file_storage = architecture.get("file_storage_engine")
    is_minio = file_storage == "MinIO"
    print_check("文件存储引擎", is_minio,
               f"存储引擎: {file_storage}")
    
    # 检查搜索引擎
    search_engine = architecture.get("search_engine")
    is_es = search_engine == "Elasticsearch"
    print_check("搜索引擎", is_es,
               f"搜索引擎: {search_engine}")
    
    return is_dual_engine and has_es_minio and is_minio and is_es

def check_deployment_mode_requirements():
    """检查部署模式要求"""
    print_section("部署模式要求检查")
    
    detector = StorageDetector()
    requirements = detector.get_system_requirements()
    
    # 检查核心要求
    core_requirements = requirements.get("core_requirements", [])
    core_names = [req["name"] for req in core_requirements]
    
    has_es = "Elasticsearch" in core_names
    has_minio = "MinIO" in core_names
    print_check("核心要求包含ES", has_es, 
               f"核心要求: {core_names}")
    print_check("核心要求包含MinIO", has_minio,
               f"核心要求: {core_names}")
    
    # 检查部署模式特定要求
    deployment_reqs = requirements.get("deployment_requirements", {}).get(settings.DEPLOYMENT_MODE, {})
    core_services = deployment_reqs.get("core_services", [])
    
    mode_has_es = "Elasticsearch" in core_services
    mode_has_minio = "MinIO" in core_services
    print_check(f"{settings.DEPLOYMENT_MODE}模式包含ES", mode_has_es,
               f"核心服务: {core_services}")
    print_check(f"{settings.DEPLOYMENT_MODE}模式包含MinIO", mode_has_minio,
               f"核心服务: {core_services}")
    
    # 检查Milvus在最小化模式下的处理
    if settings.DEPLOYMENT_MODE == "minimal":
        milvus_disabled = not settings.MILVUS_ENABLED
        print_check("最小化模式禁用Milvus", milvus_disabled,
                   f"Milvus启用状态: {settings.MILVUS_ENABLED}")
    
    return has_es and has_minio and mode_has_es and mode_has_minio

def check_hybrid_search_status():
    """检查混合检索状态"""
    print_section("混合检索状态检查")
    
    detector = StorageDetector()
    storage_info = detector.get_vector_store_info()
    hybrid_status = storage_info.get("hybrid_search_status", {})
    
    # 检查混合检索启用状态
    enabled = hybrid_status.get("enabled", False)
    forced_enabled = hybrid_status.get("forced_enabled", False)
    print_check("混合检索启用", enabled,
               f"启用状态: {enabled}")
    print_check("混合检索强制启用", forced_enabled,
               f"强制启用: {forced_enabled}")
    
    # 检查权重配置
    weight_config = hybrid_status.get("weight_config", {})
    semantic_weight = weight_config.get("semantic_weight", 0)
    keyword_weight = weight_config.get("keyword_weight", 0)
    weights_valid = abs(semantic_weight + keyword_weight - 1.0) < 0.01
    print_check("权重配置正确", weights_valid,
               f"语义: {semantic_weight}, 关键词: {keyword_weight}")
    
    return enabled and forced_enabled and weights_valid

def check_configuration_consistency():
    """检查配置一致性"""
    print_section("配置一致性检查")
    
    # 检查设置类配置
    storage_arch_info = settings.get_storage_architecture_info()
    storage_engines = storage_arch_info.get("storage_engines", {})
    
    # ES引擎一致性
    es_engine = storage_engines.get("elasticsearch", {})
    es_enabled = es_engine.get("enabled", False)
    print_check("设置类ES引擎启用", es_enabled,
               f"ES引擎启用: {es_enabled}")
    
    # MinIO引擎一致性
    minio_engine = storage_engines.get("minio", {})
    minio_enabled = minio_engine.get("enabled", False)
    print_check("设置类MinIO引擎启用", minio_enabled,
               f"MinIO引擎启用: {minio_enabled}")
    
    # 架构描述一致性
    arch_desc = storage_arch_info.get("architecture_description", "")
    is_dual_desc = "双存储引擎" in arch_desc
    print_check("架构描述一致", is_dual_desc,
               f"描述: {arch_desc}")
    
    return es_enabled and minio_enabled and is_dual_desc

def generate_quick_summary(checks: Dict[str, bool]) -> Dict[str, Any]:
    """生成快速总结"""
    total_checks = len(checks)
    passed_checks = sum(1 for status in checks.values() if status)
    failed_checks = total_checks - passed_checks
    
    success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "success_rate": f"{success_rate:.1f}%",
        "overall_status": "PASS" if failed_checks == 0 else "FAIL",
        "deployment_mode": settings.DEPLOYMENT_MODE
    }

def main():
    """主函数"""
    print_header("智政知识库核心存储配置快速检查")
    
    print(f"💡 部署模式: {settings.DEPLOYMENT_MODE}")
    print(f"🎯 检查目标: 验证ES和MinIO作为基础必需组件的配置")
    
    # 执行检查
    checks = {
        "基础配置": check_basic_configuration(),
        "核心组件标识": check_core_components(),
        "存储架构": check_storage_architecture(),
        "部署模式要求": check_deployment_mode_requirements(),
        "混合检索状态": check_hybrid_search_status(),
        "配置一致性": check_configuration_consistency()
    }
    
    # 生成总结
    summary = generate_quick_summary(checks)
    
    # 显示总结
    print_header("检查结果总结")
    
    print(f"📊 总检查项: {summary['total_checks']}")
    print(f"✅ 通过检查: {summary['passed_checks']}")
    print(f"❌ 失败检查: {summary['failed_checks']}")
    print(f"📈 成功率: {summary['success_rate']}")
    print(f"🎯 整体状态: {summary['overall_status']}")
    
    # 显示详细结果
    print_section("详细结果")
    for check_name, status in checks.items():
        print_check(check_name, status)
    
    # 根据结果提供建议
    if summary["overall_status"] == "PASS":
        print(f"\n🎉 配置检查全部通过！")
        print("✅ Elasticsearch和MinIO已正确配置为基础必需组件")
        print("✅ 双存储引擎架构配置正确")
        print("✅ 混合检索功能强制启用")
        print(f"✅ {settings.DEPLOYMENT_MODE}模式配置符合要求")
        
        print(f"\n💡 下一步建议:")
        print("  1. 运行完整测试: python3 scripts/test_core_storage_requirements.py")
        print("  2. 启动系统: ./scripts/start_with_hybrid_search.sh")
        print("  3. 验证服务: python3 scripts/validate_storage_system.py")
        
        return True
    else:
        print(f"\n❌ 部分配置检查失败！")
        print("⚠️ 存在以下问题需要修复:")
        
        for check_name, status in checks.items():
            if not status:
                print(f"  • {check_name} 检查失败")
        
        print(f"\n🔧 建议修复步骤:")
        print("  1. 检查环境变量配置文件 (.env)")
        print("  2. 确认Docker Compose服务配置")
        print("  3. 验证app/config.py设置")
        print("  4. 重新运行配置检查")
        
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n检查被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 检查过程出现异常: {e}")
        sys.exit(1) 