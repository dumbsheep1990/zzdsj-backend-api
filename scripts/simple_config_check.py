#!/usr/bin/env python3
"""
简化配置检查脚本
不依赖复杂模块导入，直接验证关键配置文件和Docker Compose
验证ES和MinIO作为基础必需组件的配置是否正确
"""

import os
import json
import yaml
import sys
from typing import Dict, Any, List

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

def check_docker_compose_configs():
    """检查Docker Compose配置文件"""
    print_section("Docker Compose配置检查")
    
    results = {}
    
    # 检查主配置文件
    main_compose_path = "docker-compose.yml"
    if os.path.exists(main_compose_path):
        try:
            with open(main_compose_path, 'r', encoding='utf-8') as f:
                main_compose = yaml.safe_load(f)
            
            services = main_compose.get('services', {})
            
            # 检查ES服务
            es_exists = 'elasticsearch' in services
            print_check("主配置包含Elasticsearch服务", es_exists)
            
            # 检查MinIO服务
            minio_exists = 'minio' in services
            print_check("主配置包含MinIO服务", minio_exists)
            
            # 检查服务依赖关系
            dependencies_correct = True
            for service_name, service_config in services.items():
                if service_name.startswith('celery-') or service_name in ['flower']:
                    depends_on = service_config.get('depends_on', [])
                    if 'elasticsearch' not in depends_on or 'minio' not in depends_on:
                        dependencies_correct = False
                        break
            
            print_check("服务依赖关系配置正确", dependencies_correct,
                       "Celery服务依赖ES和MinIO")
            
            results['main_compose'] = es_exists and minio_exists and dependencies_correct
            
        except Exception as e:
            print_check("主配置文件解析", False, f"错误: {e}")
            results['main_compose'] = False
    else:
        print_check("主配置文件存在", False, "docker-compose.yml不存在")
        results['main_compose'] = False
    
    # 检查最小化配置文件
    minimal_compose_path = "docker-compose.minimal.yml"
    if os.path.exists(minimal_compose_path):
        try:
            with open(minimal_compose_path, 'r', encoding='utf-8') as f:
                minimal_compose = yaml.safe_load(f)
            
            services = minimal_compose.get('services', {})
            
            # 检查最小化配置也包含ES和MinIO
            es_in_minimal = 'elasticsearch' in services
            minio_in_minimal = 'minio' in services
            
            print_check("最小化配置包含Elasticsearch", es_in_minimal)
            print_check("最小化配置包含MinIO", minio_in_minimal)
            
            results['minimal_compose'] = es_in_minimal and minio_in_minimal
            
        except Exception as e:
            print_check("最小化配置文件解析", False, f"错误: {e}")
            results['minimal_compose'] = False
    else:
        print_check("最小化配置文件存在", False, "docker-compose.minimal.yml不存在")
        results['minimal_compose'] = False
    
    return all(results.values())

def check_env_configuration():
    """检查环境变量配置"""
    print_section("环境变量配置检查")
    
    # 检查env.example文件
    env_example_path = "env.example"
    if not os.path.exists(env_example_path):
        print_check("env.example文件存在", False, "配置模板不存在")
        return False
    
    try:
        with open(env_example_path, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        # 检查关键配置项
        es_config_present = 'ELASTICSEARCH_URL' in env_content
        es_hybrid_present = 'ELASTICSEARCH_HYBRID_SEARCH' in env_content
        minio_config_present = 'MINIO_ENDPOINT' in env_content
        deployment_mode_present = 'DEPLOYMENT_MODE' in env_content
        
        print_check("Elasticsearch配置项", es_config_present)
        print_check("混合检索配置项", es_hybrid_present)
        print_check("MinIO配置项", minio_config_present)
        print_check("部署模式配置项", deployment_mode_present)
        
        # 检查基础必需的说明
        core_components_mentioned = '基础必需' in env_content or 'core' in env_content.lower()
        print_check("基础必需组件说明", core_components_mentioned,
                   "配置文件包含核心组件说明")
        
        return all([es_config_present, es_hybrid_present, minio_config_present, 
                   deployment_mode_present, core_components_mentioned])
        
    except Exception as e:
        print_check("环境变量配置解析", False, f"错误: {e}")
        return False

def check_scripts_availability():
    """检查相关脚本文件"""
    print_section("脚本文件检查")
    
    required_scripts = [
        "scripts/init_core_storage.py",
        "scripts/start_with_hybrid_search.sh",
        "scripts/test_core_storage_requirements.py",
        "scripts/validate_storage_system.py"
    ]
    
    all_scripts_exist = True
    for script_path in required_scripts:
        exists = os.path.exists(script_path)
        is_executable = os.access(script_path, os.X_OK) if exists else False
        
        script_name = os.path.basename(script_path)
        print_check(f"{script_name}存在", exists)
        
        if exists and script_path.endswith('.sh'):
            print_check(f"{script_name}可执行", is_executable)
            if not is_executable:
                all_scripts_exist = False
        
        if not exists:
            all_scripts_exist = False
    
    return all_scripts_exist

def check_documentation():
    """检查文档文件"""
    print_section("文档文件检查")
    
    required_docs = [
        "docs/DEPLOYMENT_GUIDE.md",
        "docs/STORAGE_ARCHITECTURE_GUIDE.md",
        "README_CORE_STORAGE.md"
    ]
    
    all_docs_exist = True
    for doc_path in required_docs:
        exists = os.path.exists(doc_path)
        doc_name = os.path.basename(doc_path)
        print_check(f"{doc_name}存在", exists)
        
        if exists:
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查文档是否包含核心概念
                has_core_storage = '基础必需' in content or 'MinIO' in content and 'Elasticsearch' in content
                print_check(f"{doc_name}包含核心存储说明", has_core_storage)
                
                if not has_core_storage:
                    all_docs_exist = False
                    
            except Exception as e:
                print_check(f"{doc_name}可读取", False, f"错误: {e}")
                all_docs_exist = False
        else:
            all_docs_exist = False
    
    return all_docs_exist

def check_directory_structure():
    """检查目录结构"""
    print_section("目录结构检查")
    
    required_dirs = [
        "app",
        "app/utils/storage",
        "scripts",
        "docs"
    ]
    
    all_dirs_exist = True
    for dir_path in required_dirs:
        exists = os.path.isdir(dir_path)
        print_check(f"{dir_path}/目录存在", exists)
        
        if not exists:
            all_dirs_exist = False
    
    # 检查关键文件
    key_files = [
        "app/config.py",
        "app/utils/storage/storage_detector.py"
    ]
    
    for file_path in key_files:
        exists = os.path.isfile(file_path)
        print_check(f"{file_path}存在", exists)
        
        if not exists:
            all_dirs_exist = False
    
    return all_dirs_exist

def check_configuration_consistency():
    """检查配置一致性"""
    print_section("配置一致性检查")
    
    # 检查Docker Compose和环境变量的一致性
    consistency_checks = []
    
    # 1. 检查Docker Compose中ES和MinIO的配置
    try:
        if os.path.exists("docker-compose.yml"):
            with open("docker-compose.yml", 'r', encoding='utf-8') as f:
                compose_content = f.read()
            
            # 检查ES配置描述
            es_described_as_required = "基础必需" in compose_content and "elasticsearch" in compose_content.lower()
            print_check("Docker Compose中ES标记为基础必需", es_described_as_required)
            consistency_checks.append(es_described_as_required)
            
            # 检查MinIO配置描述
            minio_described_as_required = "基础必需" in compose_content and "minio" in compose_content.lower()
            print_check("Docker Compose中MinIO标记为基础必需", minio_described_as_required)
            consistency_checks.append(minio_described_as_required)
        
        # 2. 检查环境变量中的一致性描述
        if os.path.exists("env.example"):
            with open("env.example", 'r', encoding='utf-8') as f:
                env_content = f.read()
            
            # 检查双存储引擎架构描述
            dual_storage_mentioned = "双存储引擎" in env_content or "MinIO" in env_content and "Elasticsearch" in env_content
            print_check("环境变量中提及双存储引擎架构", dual_storage_mentioned)
            consistency_checks.append(dual_storage_mentioned)
        
        return all(consistency_checks)
        
    except Exception as e:
        print_check("配置一致性检查", False, f"错误: {e}")
        return False

def generate_summary(check_results: Dict[str, bool]) -> Dict[str, Any]:
    """生成检查总结"""
    total_checks = len(check_results)
    passed_checks = sum(1 for status in check_results.values() if status)
    failed_checks = total_checks - passed_checks
    
    success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "success_rate": f"{success_rate:.1f}%",
        "overall_status": "PASS" if failed_checks == 0 else "FAIL"
    }

def main():
    """主函数"""
    print_header("智政知识库核心存储配置简化检查")
    
    print("💡 检查目标: 验证ES和MinIO作为基础必需组件的配置文件")
    print("🎯 检查范围: Docker Compose、环境变量、脚本、文档")
    
    # 执行各项检查
    check_results = {
        "Docker Compose配置": check_docker_compose_configs(),
        "环境变量配置": check_env_configuration(),
        "脚本文件": check_scripts_availability(),
        "文档文件": check_documentation(),
        "目录结构": check_directory_structure(),
        "配置一致性": check_configuration_consistency()
    }
    
    # 生成总结
    summary = generate_summary(check_results)
    
    # 显示总结
    print_header("检查结果总结")
    
    print(f"📊 总检查项: {summary['total_checks']}")
    print(f"✅ 通过检查: {summary['passed_checks']}")
    print(f"❌ 失败检查: {summary['failed_checks']}")
    print(f"📈 成功率: {summary['success_rate']}")
    print(f"🎯 整体状态: {summary['overall_status']}")
    
    # 显示详细结果
    print_section("详细结果")
    for check_name, status in check_results.items():
        print_check(check_name, status)
    
    # 提供建议
    if summary["overall_status"] == "PASS":
        print(f"\n🎉 配置文件检查全部通过！")
        print("✅ Docker Compose配置正确")
        print("✅ 环境变量配置完整")
        print("✅ 脚本文件准备就绪")
        print("✅ 文档文件完整")
        print("✅ ES和MinIO已正确配置为基础必需组件")
        
        print(f"\n💡 下一步建议:")
        print("  1. 启动Docker服务: docker-compose up -d")
        print("  2. 运行核心存储初始化: python3 scripts/init_core_storage.py")
        print("  3. 使用启动脚本: ./scripts/start_with_hybrid_search.sh")
        print("  4. 运行完整测试: python3 scripts/test_core_storage_requirements.py")
        
        return True
    else:
        print(f"\n❌ 部分配置文件检查失败！")
        print("⚠️ 存在以下问题需要修复:")
        
        for check_name, status in check_results.items():
            if not status:
                print(f"  • {check_name} 检查失败")
        
        print(f"\n🔧 建议修复步骤:")
        print("  1. 检查缺失的文件并补充")
        print("  2. 确认配置文件内容正确")
        print("  3. 给脚本文件添加执行权限: chmod +x scripts/*.sh")
        print("  4. 重新运行检查")
        
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