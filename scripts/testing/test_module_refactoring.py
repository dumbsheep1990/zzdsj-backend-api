#!/usr/bin/env python3
"""
模块化重构测试脚本
验证 app/utils 模块重构后的导入和结构是否正确
"""

import sys
import os
import traceback
from pathlib import Path

def test_module_imports():
    """测试模块导入"""
    print("\n=== 测试模块导入 ===")
    
    try:
        # 测试顶层模块导入
        import app.utils
        print("✓ 顶层模块导入成功: app.utils")
        
        # 测试核心模块
        from app.utils import core
        print("✓ 核心模块导入成功: app.utils.core")
        
        # 测试Phase 2专用工具模块
        from app.utils import text, security, storage, monitoring
        print("✓ Phase 2模块导入成功: text, security, storage, monitoring")
        
        # 测试Phase 3服务集成模块
        from app.utils import messaging, auth, services, web, common
        print("✓ Phase 3模块导入成功: messaging, auth, services, web, common")
        
        return True
    except Exception as e:
        print(f"✗ 模块导入测试失败: {e}")
        traceback.print_exc()
        return False

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

def test_module_exports():
    """测试模块导出"""
    print("\n=== 测试模块导出 ===")
    
    try:
        # 测试各模块的__all__属性
        import app.utils.text
        assert hasattr(app.utils.text, '__all__'), "text模块缺少__all__属性"
        print(f"✓ text模块导出: {len(app.utils.text.__all__)}个符号")
        
        import app.utils.security
        assert hasattr(app.utils.security, '__all__'), "security模块缺少__all__属性"
        print(f"✓ security模块导出: {len(app.utils.security.__all__)}个符号")
        
        import app.utils.storage
        assert hasattr(app.utils.storage, '__all__'), "storage模块缺少__all__属性"
        print(f"✓ storage模块导出: {len(app.utils.storage.__all__)}个符号")
        
        import app.utils.monitoring
        assert hasattr(app.utils.monitoring, '__all__'), "monitoring模块缺少__all__属性"
        print(f"✓ monitoring模块导出: {len(app.utils.monitoring.__all__)}个符号")
        
        import app.utils.messaging
        assert hasattr(app.utils.messaging, '__all__'), "messaging模块缺少__all__属性"
        print(f"✓ messaging模块导出: {len(app.utils.messaging.__all__)}个符号")
        
        import app.utils.auth
        assert hasattr(app.utils.auth, '__all__'), "auth模块缺少__all__属性"
        print(f"✓ auth模块导出: {len(app.utils.auth.__all__)}个符号")
        
        import app.utils.services
        assert hasattr(app.utils.services, '__all__'), "services模块缺少__all__属性"
        print(f"✓ services模块导出: {len(app.utils.services.__all__)}个符号")
        
        import app.utils.web
        assert hasattr(app.utils.web, '__all__'), "web模块缺少__all__属性"
        print(f"✓ web模块导出: {len(app.utils.web.__all__)}个符号")
        
        import app.utils.common
        assert hasattr(app.utils.common, '__all__'), "common模块缺少__all__属性"
        print(f"✓ common模块导出: {len(app.utils.common.__all__)}个符号")
        
        return True
    except Exception as e:
        print(f"✗ 模块导出测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("开始模块化重构测试...")
    
    tests = [
        test_module_imports,
        test_module_structure,
        test_file_migration,
        test_module_exports
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
        print("🎉 所有测试通过！模块化重构成功完成！")
        return True
    else:
        print("❌ 部分测试失败，需要检查和修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 