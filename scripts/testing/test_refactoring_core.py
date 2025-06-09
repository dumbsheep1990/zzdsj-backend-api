#!/usr/bin/env python3
"""
模块化重构核心测试脚本
验证 app/utils 模块重构后的结构是否正确，不依赖外部包
"""

import sys
import os
import traceback
from pathlib import Path

def test_module_structure():
    """测试模块结构"""
    print("\n=== 测试模块结构 ===")
    
    try:
        utils_path = Path("app/utils")
        
        # 检查核心模块结构
        core_modules = ["database", "config", "cache"]
        for module in core_modules:
            module_path = utils_path / "core" / module
            assert module_path.exists(), f"核心模块目录不存在: {module_path}"
            
            init_file = module_path / "__init__.py"
            assert init_file.exists(), f"__init__.py文件不存在: {init_file}"
            print(f"✓ 核心模块结构正确: core/{module}")
        
        # 检查Phase 2模块结构
        phase2_modules = ["text", "security", "storage", "monitoring"]
        for module in phase2_modules:
            module_path = utils_path / module
            assert module_path.exists(), f"Phase 2模块目录不存在: {module_path}"
            
            init_file = module_path / "__init__.py"
            assert init_file.exists(), f"__init__.py文件不存在: {init_file}"
            print(f"✓ Phase 2模块结构正确: {module}")
        
        # 检查Phase 3模块结构
        phase3_modules = ["messaging", "auth", "services", "web", "common"]
        for module in phase3_modules:
            module_path = utils_path / module
            assert module_path.exists(), f"Phase 3模块目录不存在: {module_path}"
            
            init_file = module_path / "__init__.py"
            assert init_file.exists(), f"__init__.py文件不存在: {init_file}"
            print(f"✓ Phase 3模块结构正确: {module}")
        
        return True
    except Exception as e:
        print(f"✗ 模块结构测试失败: {e}")
        traceback.print_exc()
        return False

def test_file_migration():
    """测试文件迁移"""
    print("\n=== 测试文件迁移 ===")
    
    try:
        utils_path = Path("app/utils")
        
        # 检查文件是否正确迁移
        expected_files = {
            # text模块
            "text/processor.py": "text_processing.py",
            "text/embedding_utils.py": "embedding_utils.py", 
            "text/template_renderer.py": "template_renderer.py",
            
            # security模块
            "security/rate_limiter.py": "rate_limiter.py",
            "security/sensitive_filter.py": "sensitive_word_filter.py",
            
            # storage模块
            "storage/vector_store.py": "vector_store.py",
            "storage/milvus_manager.py": "milvus_manager.py",
            "storage/elasticsearch_manager.py": "elasticsearch_manager.py",
            "storage/object_storage.py": "object_storage.py",
            "storage/storage_detector.py": "storage_detector.py",
            
            # monitoring模块
            "monitoring/token_metrics.py": "token_metrics.py",
            "monitoring/health_monitor.py": "service_health.py",
            
            # messaging模块
            "messaging/message_queue.py": "message_queue.py",
            
            # auth模块
            "auth/jwt_handler.py": "auth.py",
            
            # services模块
            "services/service_manager.py": "service_manager.py",
            "services/service_registry.py": "service_registry.py",
            "services/service_discovery.py": "service_discovery.py",
            "services/decorators.py": "service_decorators.py",
            "services/mcp_registrar.py": "mcp_service_registrar.py",
            
            # web模块
            "web/swagger_helper.py": "swagger_helper.py",
            
            # common模块
            "common/logging_config.py": "logging_config.py"
        }
        
        for new_path, old_name in expected_files.items():
            file_path = utils_path / new_path
            assert file_path.exists(), f"迁移文件不存在: {file_path} (原文件: {old_name})"
            print(f"✓ 文件迁移成功: {old_name} → {new_path}")
        
        # 检查重复文件是否已删除
        deleted_files = [
            "async_redis_client.py",
            "config_bootstrap.py", 
            "config_directory_manager.py",
            "config_state.py",
            "config_validator.py",
            "db_config.py",
            "db_init.py",
            "db_migration.py"
        ]
        
        for file_name in deleted_files:
            file_path = utils_path / file_name
            assert not file_path.exists(), f"重复文件未删除: {file_path}"
            print(f"✓ 重复文件已删除: {file_name}")
        
        return True
    except Exception as e:
        print(f"✗ 文件迁移测试失败: {e}")
        traceback.print_exc()
        return False

def test_init_files():
    """测试__init__.py文件内容"""
    print("\n=== 测试__init__.py文件 ===")
    
    try:
        utils_path = Path("app/utils")
        
        # 检查顶层__init__.py
        main_init = utils_path / "__init__.py"
        assert main_init.exists(), "顶层__init__.py文件不存在"
        
        with open(main_init, 'r', encoding='utf-8') as f:
            content = f.read()
            assert '__all__' in content, "顶层__init__.py缺少__all__定义"
            assert 'core' in content, "顶层__init__.py未导入core模块"
            print("✓ 顶层__init__.py文件正确")
        
        # 检查各模块的__init__.py
        modules = ["text", "security", "storage", "monitoring", "messaging", "auth", "services", "web", "common"]
        for module in modules:
            init_file = utils_path / module / "__init__.py"
            assert init_file.exists(), f"{module}模块__init__.py文件不存在"
            
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert '__all__' in content, f"{module}模块__init__.py缺少__all__定义"
                assert 'from .' in content, f"{module}模块__init__.py缺少相对导入"
                print(f"✓ {module}模块__init__.py文件正确")
        
        return True
    except Exception as e:
        print(f"✗ __init__.py文件测试失败: {e}")
        traceback.print_exc()
        return False

def test_directory_cleanup():
    """测试目录清理"""
    print("\n=== 测试目录清理 ===")
    
    try:
        utils_path = Path("app/utils")
        
        # 检查是否还有散落的.py文件（除了__init__.py）
        scattered_files = []
        for file_path in utils_path.glob("*.py"):
            if file_path.name != "__init__.py":
                scattered_files.append(file_path.name)
        
        assert len(scattered_files) == 0, f"还有散落的文件: {scattered_files}"
        print("✓ 没有散落的文件，目录清理完成")
        
        # 统计模块化后的文件分布
        total_files = 0
        for module_dir in utils_path.iterdir():
            if module_dir.is_dir() and module_dir.name != "__pycache__":
                py_files = list(module_dir.glob("**/*.py"))
                file_count = len(py_files)
                total_files += file_count
                print(f"✓ {module_dir.name}模块: {file_count}个文件")
        
        print(f"✓ 总计: {total_files}个Python文件已模块化")
        
        return True
    except Exception as e:
        print(f"✗ 目录清理测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("开始模块化重构核心测试...")
    
    tests = [
        test_module_structure,
        test_file_migration,
        test_init_files,
        test_directory_cleanup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有核心测试通过！模块化重构成功完成！")
        print("\n📋 重构总结:")
        print("✅ Phase 1: 核心基础设施模块 (core) - 已完成")
        print("✅ Phase 2: 专用工具模块 (text, security, storage, monitoring) - 已完成")
        print("✅ Phase 3: 服务集成模块 (messaging, auth, services, web, common) - 已完成")
        print("✅ 文件迁移和目录清理 - 已完成")
        print("✅ 模块导出接口 - 已完成")
        return True
    else:
        print("❌ 部分测试失败，需要检查和修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 