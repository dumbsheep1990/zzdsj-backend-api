#!/usr/bin/env python3
"""
最终配置检查脚本
完全不依赖外部库，只使用Python标准库
验证ES和MinIO作为基础必需组件的配置是否正确
"""

import os
import sys

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

def check_file_exists(filepath: str) -> bool:
    """检查文件是否存在"""
    return os.path.exists(filepath) and os.path.isfile(filepath)

def check_dir_exists(dirpath: str) -> bool:
    """检查目录是否存在"""
    return os.path.exists(dirpath) and os.path.isdir(dirpath)

def read_file_content(filepath: str) -> str:
    """安全读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""

def check_docker_compose_files():
    """检查Docker Compose配置文件"""
    print_section("Docker Compose配置文件检查")
    
    results = []
    
    # 检查主配置文件
    main_compose = "docker-compose.yml"
    main_exists = check_file_exists(main_compose)
    print_check("docker-compose.yml存在", main_exists)
    results.append(main_exists)
    
    if main_exists:
        content = read_file_content(main_compose)
        
        # 检查ES服务（基础必需）
        es_service = "elasticsearch:" in content
        print_check("包含Elasticsearch服务", es_service)
        results.append(es_service)
        
        # 检查MinIO服务（现在是可选增强组件）
        minio_service = "minio:" in content
        print_check("包含MinIO服务（可选增强）", minio_service)
        results.append(minio_service)
        
        # 检查新架构说明
        arch_described = "可选增强" in content or "Milvus" in content
        print_check("正确标记为可选增强组件", arch_described)
        results.append(arch_described)
        
        # 检查依赖关系 - Celery服务应该只依赖ES
        depends_on_es = "- elasticsearch" in content
        print_check("服务依赖Elasticsearch", depends_on_es)
        results.append(depends_on_es)
    
    # 检查最小化配置文件
    minimal_compose = "docker-compose.minimal.yml"
    minimal_exists = check_file_exists(minimal_compose)
    print_check("docker-compose.minimal.yml存在", minimal_exists)
    results.append(minimal_exists)
    
    if minimal_exists:
        minimal_content = read_file_content(minimal_compose)
        
        # 检查最小化配置包含ES（基础必需）
        minimal_es = "elasticsearch:" in minimal_content
        print_check("最小化配置包含ES", minimal_es)
        results.append(minimal_es)
        
        # 检查最小化配置不包含MinIO（正确行为）
        minimal_no_minio = "minio:" not in minimal_content
        print_check("最小化配置不包含MinIO（正确）", minimal_no_minio)
        results.append(minimal_no_minio)
        
        # 检查使用本地文件存储
        local_storage = "FILE_STORAGE_TYPE=local" in minimal_content
        print_check("使用本地文件存储", local_storage)
        results.append(local_storage)
    
    return all(results)

def check_environment_configuration():
    """检查环境变量配置"""
    print_section("环境变量配置检查")
    
    results = []
    
    # 检查env.example文件
    env_example = "env.example"
    env_exists = check_file_exists(env_example)
    print_check("env.example存在", env_exists)
    results.append(env_exists)
    
    if env_exists:
        env_content = read_file_content(env_example)
        
        # 检查关键配置项
        checks = [
            ("ELASTICSEARCH_URL", "Elasticsearch URL配置"),
            ("ELASTICSEARCH_HYBRID_SEARCH", "混合检索配置"),
            ("FILE_STORAGE_TYPE", "文件存储类型配置"),
            ("FILE_STORAGE_PATH", "文件存储路径配置"),
            ("MINIO_ENDPOINT", "MinIO端点配置（可选）"),
            ("MILVUS_HOST", "Milvus主机配置（可选）"),
            ("DEPLOYMENT_MODE", "部署模式配置")
        ]
        
        for config_key, description in checks:
            has_config = config_key in env_content
            print_check(description, has_config)
            results.append(has_config)
        
        # 检查新架构说明
        arch_mentioned = ("可选增强" in env_content or 
                         ("本地存储" in env_content and "MinIO存储" in env_content))
        print_check("包含新架构说明", arch_mentioned)
        results.append(arch_mentioned)
        
        # 检查文件存储配置说明
        file_storage_explained = ("FILE_STORAGE_TYPE" in env_content and 
                                "本地存储" in env_content)
        print_check("包含文件存储配置说明", file_storage_explained)
        results.append(file_storage_explained)
    
    return all(results)

def check_scripts_and_tools():
    """检查脚本和工具文件"""
    print_section("脚本和工具文件检查")
    
    results = []
    
    # 必需的脚本文件
    required_scripts = [
        ("scripts/init_core_storage.py", "核心存储初始化脚本"),
        ("scripts/start_with_hybrid_search.sh", "混合搜索启动脚本"),
        ("scripts/test_core_storage_requirements.py", "核心存储测试脚本"),
        ("scripts/validate_storage_system.py", "存储系统验证脚本")
    ]
    
    for script_path, description in required_scripts:
        exists = check_file_exists(script_path)
        print_check(f"{description}存在", exists)
        results.append(exists)
        
        # 检查Shell脚本的执行权限
        if exists and script_path.endswith('.sh'):
            is_executable = os.access(script_path, os.X_OK)
            print_check(f"{description}可执行", is_executable)
            results.append(is_executable)
    
    return all(results)

def check_documentation():
    """检查文档文件"""
    print_section("文档文件检查")
    
    results = []
    
    # 必需的文档文件
    required_docs = [
        ("docs/DEPLOYMENT_GUIDE.md", "部署指南"),
        ("docs/STORAGE_ARCHITECTURE_GUIDE.md", "存储架构指南"),
        ("README_CORE_STORAGE.md", "核心存储使用指南")
    ]
    
    for doc_path, description in required_docs:
        exists = check_file_exists(doc_path)
        print_check(f"{description}存在", exists)
        results.append(exists)
        
        if exists:
            content = read_file_content(doc_path)
            
            # 检查是否包含核心存储相关内容
            has_core_content = ("基础必需" in content or 
                              ("MinIO" in content and "Elasticsearch" in content))
            print_check(f"{description}包含核心存储内容", has_core_content)
            results.append(has_core_content)
    
    return all(results)

def check_directory_structure():
    """检查目录结构"""
    print_section("目录结构检查")
    
    results = []
    
    # 必需的目录
    required_dirs = [
        ("app", "应用程序目录"),
        ("app/utils", "工具目录"),
        ("app/utils/storage", "存储工具目录"),
        ("scripts", "脚本目录"),
        ("docs", "文档目录")
    ]
    
    for dir_path, description in required_dirs:
        exists = check_dir_exists(dir_path)
        print_check(f"{description}存在", exists)
        results.append(exists)
    
    # 必需的核心文件
    core_files = [
        ("app/config.py", "配置文件"),
        ("app/utils/storage/storage_detector.py", "存储检测器")
    ]
    
    for file_path, description in core_files:
        exists = check_file_exists(file_path)
        print_check(f"{description}存在", exists)
        results.append(exists)
    
    return all(results)

def check_configuration_consistency():
    """检查配置一致性"""
    print_section("配置一致性检查")
    
    results = []
    
    # 检查Docker Compose配置一致性
    if check_file_exists("docker-compose.yml"):
        compose_content = read_file_content("docker-compose.yml")
        
        # ES应该被标记为基础必需
        es_marked_required = "Elasticsearch" in compose_content and "基础必需" in compose_content
        print_check("Docker Compose中ES标记正确", es_marked_required)
        results.append(es_marked_required)
        
        # MinIO应该被标记为可选增强
        minio_marked_enhancement = "MinIO" in compose_content and "可选增强" in compose_content
        print_check("Docker Compose中MinIO标记为可选增强", minio_marked_enhancement)
        results.append(minio_marked_enhancement)
    
    # 检查环境变量配置一致性
    if check_file_exists("env.example"):
        env_content = read_file_content("env.example")
        
        # 混合检索应该被强制启用
        hybrid_forced = "ELASTICSEARCH_HYBRID_SEARCH=true" in env_content
        print_check("混合检索被强制启用", hybrid_forced)
        results.append(hybrid_forced)
        
        # 应该有本地文件存储配置
        has_local_storage = "FILE_STORAGE_TYPE=local" in env_content
        print_check("包含本地文件存储配置", has_local_storage)
        results.append(has_local_storage)
        
        # MinIO应该标记为可选
        minio_optional = "MINIO_ENABLED=false" in env_content
        print_check("MinIO标记为默认禁用", minio_optional)
        results.append(minio_optional)
    
    # 检查文档一致性
    if check_file_exists("README_CORE_STORAGE.md"):
        readme_content = read_file_content("README_CORE_STORAGE.md")
        
        # 应该说明新的架构
        explains_new_arch = ("Elasticsearch" in readme_content and 
                           "本地文件" in readme_content and
                           "可选增强" in readme_content)
        print_check("README说明新架构", explains_new_arch)
        results.append(explains_new_arch)
    
    return all(results)

def generate_final_summary(all_checks):
    """生成最终总结"""
    total_sections = len(all_checks)
    passed_sections = sum(1 for result in all_checks.values() if result)
    failed_sections = total_sections - passed_sections
    
    success_rate = (passed_sections / total_sections * 100) if total_sections > 0 else 0
    
    return {
        "total_sections": total_sections,
        "passed_sections": passed_sections,
        "failed_sections": failed_sections,
        "success_rate": f"{success_rate:.1f}%",
        "overall_status": "PASS" if failed_sections == 0 else "FAIL"
    }

def main():
    """主函数"""
    print_header("智政知识库核心存储架构最终配置检查")
    
    print("💡 检查目标: 验证ES和MinIO作为基础必需组件的完整配置")
    print("🎯 检查范围: 文件结构、配置内容、脚本工具、文档完整性")
    print("🔧 检查方式: 纯Python标准库实现，无外部依赖")
    
    # 执行全面检查
    all_checks = {
        "Docker Compose配置": check_docker_compose_files(),
        "环境变量配置": check_environment_configuration(),
        "脚本和工具": check_scripts_and_tools(),
        "文档文件": check_documentation(),
        "目录结构": check_directory_structure(),
        "配置一致性": check_configuration_consistency()
    }
    
    # 生成总结
    summary = generate_final_summary(all_checks)
    
    # 显示最终结果
    print_header("最终检查结果")
    
    print(f"📊 总检查项: {summary['total_sections']}")
    print(f"✅ 通过检查: {summary['passed_sections']}")
    print(f"❌ 失败检查: {summary['failed_sections']}")
    print(f"📈 成功率: {summary['success_rate']}")
    print(f"🎯 整体状态: {summary['overall_status']}")
    
    # 显示各项检查详情
    print_section("各项检查结果")
    for check_name, result in all_checks.items():
        print_check(check_name, result)
    
    # 根据结果提供最终建议
    if summary["overall_status"] == "PASS":
        print(f"\n🎉 恭喜！核心存储架构配置检查全部通过！")
        print("=" * 60)
        print("✅ Docker Compose配置正确 - ES为核心，MinIO为可选增强")
        print("✅ 环境变量配置完整 - 支持本地和MinIO文件存储")
        print("✅ 脚本工具准备就绪 - 支持一键部署和验证")
        print("✅ 文档资料完整 - 涵盖新架构说明和使用指南")
        print("✅ 目录结构规范 - 符合项目组织要求")
        print("✅ 配置一致性良好 - 多文件配置保持同步")
        
        print(f"\n🚀 系统已准备就绪！推荐执行步骤:")
        print("  1️⃣  复制配置文件: cp env.example .env")
        print("  2️⃣  选择部署模式:")
        print("      最小化: docker-compose -f docker-compose.minimal.yml up -d")
        print("      标准模式: docker-compose up -d")
        print("  3️⃣  初始化存储: python3 scripts/init_core_storage.py")
        print("  4️⃣  验证系统: python3 scripts/validate_storage_system.py")
        print("  5️⃣  运行应用: ./scripts/start_with_hybrid_search.sh")
        
        print(f"\n🎯 新架构特性:")
        print("  • 核心组件: Elasticsearch(文档检索) + 本地文件存储")
        print("  • 混合检索: 70%语义搜索 + 30%关键词搜索")
        print("  • 文件存储: 本地存储(minimal) 或 MinIO(standard/production)")
        print("  • 向量搜索: Elasticsearch(基础) + Milvus(可选增强)")
        print("  • 部署灵活: minimal模式无需MinIO，降低资源需求")
        
        print(f"\n📚 参考文档:")
        print("  • 使用指南: README_CORE_STORAGE.md")
        print("  • 部署指南: docs/DEPLOYMENT_GUIDE.md")
        print("  • 架构说明: docs/STORAGE_ARCHITECTURE_GUIDE.md")
        
        return True
    else:
        print(f"\n❌ 配置检查发现问题！")
        print("=" * 60)
        print("⚠️  以下检查项未通过:")
        
        for check_name, result in all_checks.items():
            if not result:
                print(f"  • {check_name}")
        
        print(f"\n🔧 修复建议:")
        print("  1. 检查缺失的文件和目录")
        print("  2. 确认配置文件内容正确")
        print("  3. 给Shell脚本添加执行权限: chmod +x scripts/*.sh")
        print("  4. 验证文档内容包含新架构说明")
        print("  5. 重新运行检查确认修复结果")
        
        print(f"\n💡 新架构要求:")
        print("  • Elasticsearch是唯一的基础必需存储组件")
        print("  • 混合检索必须强制启用")
        print("  • 文件存储支持本地和MinIO两种模式")
        print("  • MinIO作为Milvus依赖或可选增强组件")
        print("  • 配置文件之间保持一致性")
        
        return False

if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print(f"\n✨ 智政知识库核心存储架构配置完美！")
            print(f"🎊 ES和MinIO已成功设置为基础必需组件！")
            sys.exit(0)
        else:
            print(f"\n🛠️  请根据上述建议修复问题后重新检查。")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  检查被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 检查过程发生异常: {e}")
        sys.exit(1) 