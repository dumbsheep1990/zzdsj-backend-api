#!/usr/bin/env python3
"""
快速集成测试脚本
验证优化模块的基本集成状态
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def test_basic_imports():
    """测试基本导入"""
    print("🔍 测试基本导入...")
    
    # 测试配置模块
    try:
        from app.config.optimization import (
            optimization_settings,
            get_optimization_config,
            is_optimization_enabled
        )
        print("✅ 配置模块导入成功")
        
        # 验证配置
        config = get_optimization_config()
        enabled = is_optimization_enabled()
        print(f"   优化开关: {enabled}")
        print(f"   配置部分: {list(config.keys())}")
        
    except Exception as e:
        print(f"❌ 配置模块导入失败: {str(e)}")
        return False
    
    # 测试服务模块
    try:
        from app.services.knowledge.optimized_search_service import (
            get_optimized_search_service,
            OPTIMIZATION_AVAILABLE
        )
        print("✅ 优化搜索服务导入成功")
        print(f"   优化模块可用: {OPTIMIZATION_AVAILABLE}")
        
    except Exception as e:
        print(f"❌ 优化搜索服务导入失败: {str(e)}")
        return False
    
    # 测试API模块
    try:
        from app.api.frontend.search.optimized import (
            OptimizedSearchRequest,
            CONFIG_MANAGER_AVAILABLE
        )
        print("✅ 优化API模块导入成功")
        print(f"   配置管理器可用: {CONFIG_MANAGER_AVAILABLE}")
        
    except Exception as e:
        print(f"❌ 优化API模块导入失败: {str(e)}")
        return False
    
    return True

def test_service_creation():
    """测试服务创建"""
    print("\n🔧 测试服务创建...")
    
    try:
        from app.services.knowledge.optimized_search_service import get_optimized_search_service
        
        # 模拟数据库会话
        class MockDB:
            pass
        
        # 创建服务（禁用优化）
        service = get_optimized_search_service(MockDB(), enable_optimization=False)
        print("✅ 服务创建成功（传统模式）")
        
        # 创建服务（启用优化）
        service = get_optimized_search_service(MockDB(), enable_optimization=True)
        print("✅ 服务创建成功（优化模式）")
        
        return True
        
    except Exception as e:
        print(f"❌ 服务创建失败: {str(e)}")
        return False

def test_api_models():
    """测试API模型"""
    print("\n📋 测试API模型...")
    
    try:
        from app.api.frontend.search.optimized import OptimizedSearchRequest
        
        # 创建请求模型
        request = OptimizedSearchRequest(query="test query")
        print("✅ API请求模型创建成功")
        print(f"   查询: {request.query}")
        print(f"   默认大小: {request.size}")
        print(f"   向量权重: {request.vector_weight}")
        
        return True
        
    except Exception as e:
        print(f"❌ API模型测试失败: {str(e)}")
        return False

def test_integration_status():
    """测试集成状态"""
    print("\n📊 测试集成状态...")
    
    try:
        from app.api.frontend.search.router_integration import check_integration_status
        
        status = check_integration_status()
        print("✅ 集成状态检查成功")
        print(f"   优化路由: {status.get('optimized_routes', 'N/A')}")
        print(f"   优化模块: {status.get('optimization_modules', 'N/A')}")
        print(f"   集成状态: {status.get('status', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成状态检查失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 开始快速集成测试\n")
    
    tests = [
        ("基本导入测试", test_basic_imports),
        ("服务创建测试", test_service_creation),
        ("API模型测试", test_api_models),
        ("集成状态测试", test_integration_status)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"📋 {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"💥 {test_name} 异常: {str(e)}")
    
    # 总结
    print(f"\n{'='*60}")
    print(f"📊 测试总结")
    print(f"{'='*60}")
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！优化模块集成成功！")
        print("\n📌 后续步骤:")
        print("1. 运行完整集成测试")
        print("2. 配置环境变量启用优化")
        print("3. 监控系统性能")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查相关组件")
        print("\n🔧 建议:")
        print("1. 检查文件路径和导入")
        print("2. 确认所有依赖已安装")
        print("3. 验证配置文件存在")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 