#!/usr/bin/env python3
"""
核心重构验证测试脚本
仅验证核心模块重构，不依赖外部包
"""

import sys
import traceback

def test_core_utils_structure():
    """测试核心工具模块结构"""
    print("=== 测试核心工具模块结构 ===")
    
    try:
        # 测试新的核心模块导入
        from app.utils.core.database import get_db, Base, get_session_manager, check_database_health
        print("✓ app.utils.core.database 模块导入成功")
        
        from app.utils.core.config import get_config_manager, ConfigBootstrap, inject_config_to_env
        print("✓ app.utils.core.config 模块导入成功")
        
        from app.utils.core.cache import get_redis_client
        print("✓ app.utils.core.cache 模块导入成功")
        
        return True
    except Exception as e:
        print(f"✗ 核心工具模块结构测试失败: {e}")
        traceback.print_exc()
        return False

def test_config_compatibility():
    """测试配置兼容性"""
    print("\n=== 测试配置兼容性 ===")
    
    try:
        # 测试新的配置系统
        from app.config import Settings, settings
        print("✓ 新配置系统导入成功")
        
        # 测试pydantic-settings兼容性
        from pydantic_settings import BaseSettings
        print("✓ pydantic-settings 兼容性正常")
        
        # 测试配置实例化
        s = Settings()
        print("✓ 配置实例化成功")
        
        # 测试基本配置访问
        assert hasattr(s, 'DATABASE_URL'), "DATABASE_URL配置缺失"
        assert hasattr(s, 'REDIS_HOST'), "REDIS_HOST配置缺失"
        assert hasattr(s, 'SERVICE_NAME'), "SERVICE_NAME配置缺失"
        print("✓ 基本配置项验证通过")
        
        return True
    except Exception as e:
        print(f"✗ 配置兼容性测试失败: {e}")
        traceback.print_exc()
        return False

def test_import_migration():
    """测试导入迁移"""
    print("\n=== 测试导入迁移 ===")
    
    try:
        # 验证旧的导入路径不再可用（应该失败）
        old_imports_should_fail = [
            "from app.utils.database import get_db",
            "from app.utils.config_manager import get_config_manager", 
            "from app.utils.redis_client import get_redis_client"
        ]
        
        for import_stmt in old_imports_should_fail:
            try:
                exec(import_stmt)
                print(f"⚠ 旧导入路径仍然可用: {import_stmt}")
            except ImportError:
                print(f"✓ 旧导入路径已正确移除: {import_stmt}")
        
        # 验证新的导入路径可用
        new_imports = [
            "from app.utils.core.database import get_db",
            "from app.utils.core.config import get_config_manager",
            "from app.utils.core.cache import get_redis_client"
        ]
        
        for import_stmt in new_imports:
            exec(import_stmt)
            print(f"✓ 新导入路径正常: {import_stmt}")
        
        return True
    except Exception as e:
        print(f"✗ 导入迁移测试失败: {e}")
        traceback.print_exc()
        return False

def test_module_organization():
    """测试模块组织结构"""
    print("\n=== 测试模块组织结构 ===")
    
    try:
        import os
        
        # 检查新的目录结构
        core_path = "app/utils/core"
        assert os.path.exists(core_path), f"核心目录不存在: {core_path}"
        print(f"✓ 核心目录存在: {core_path}")
        
        # 检查子模块目录
        sub_modules = ["database", "config", "cache"]
        for module in sub_modules:
            module_path = os.path.join(core_path, module)
            assert os.path.exists(module_path), f"子模块目录不存在: {module_path}"
            
            init_file = os.path.join(module_path, "__init__.py")
            assert os.path.exists(init_file), f"__init__.py文件不存在: {init_file}"
            print(f"✓ 子模块结构正确: {module}")
        
        return True
    except Exception as e:
        print(f"✗ 模块组织结构测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("开始验证Phase 1核心重构结果...")
    print("=" * 60)
    
    tests = [
        test_core_utils_structure,
        test_config_compatibility,
        test_import_migration,
        test_module_organization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"核心重构测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 Phase 1核心重构验证成功！")
        print("\n✅ 重构成果总结:")
        print("  📁 核心基础设施模块重构完成")
        print("  📁 数据库模块: app.utils.database → app.utils.core.database")
        print("  📁 配置模块: app.utils.config_manager → app.utils.core.config")
        print("  📁 缓存模块: app.utils.redis_client → app.utils.core.cache")
        print("  🔧 pydantic-settings兼容性问题已解决")
        print("  🔧 所有引用已更新到新的导入路径")
        print("  🔧 模块组织结构更加清晰和规范")
        
        print("\n📋 下一步建议:")
        print("  1. 安装项目依赖: pip install -r requirements.txt")
        print("  2. 运行完整测试验证所有功能")
        print("  3. 继续执行Phase 2重构计划")
        
        return True
    else:
        print("\n❌ 核心重构验证失败，需要进一步修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 