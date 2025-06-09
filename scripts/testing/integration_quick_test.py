#!/usr/bin/env python3
"""快速集成测试"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

print("🚀 优化模块快速集成测试")
print("="*50)

# 测试1: 配置模块
try:
    from app.config.optimization import get_optimization_config, is_optimization_enabled
    config = get_optimization_config()
    enabled = is_optimization_enabled()
    print("✅ 配置模块: OK")
    print(f"   优化开关: {enabled}")
    print(f"   配置组件: {list(config.keys())}")
except Exception as e:
    print(f"❌ 配置模块: {e}")

# 测试2: 服务模块
try:
    from app.services.knowledge.optimized_search_service import OPTIMIZATION_AVAILABLE, get_optimized_search_service
    print("✅ 优化服务: OK")
    print(f"   优化可用: {OPTIMIZATION_AVAILABLE}")
    
    # 测试服务创建
    class MockDB: 
        pass
    service = get_optimized_search_service(MockDB(), enable_optimization=False)
    print("✅ 服务创建: OK")
except Exception as e:
    print(f"❌ 优化服务: {e}")

# 测试3: API模块  
try:
    from app.api.frontend.search.optimized import OptimizedSearchRequest, CONFIG_MANAGER_AVAILABLE
    request = OptimizedSearchRequest(query="test")
    print("✅ API模块: OK")
    print(f"   配置管理器: {CONFIG_MANAGER_AVAILABLE}")
    print(f"   请求模型: {request.query}")
except Exception as e:
    print(f"❌ API模块: {e}")

# 测试4: 路由集成
try:
    from app.api.frontend.search.router_integration import check_integration_status
    status = check_integration_status()
    print("✅ 路由集成: OK")
    print(f"   集成状态: {status['status']}")
except Exception as e:
    print(f"❌ 路由集成: {e}")

print("="*50)
print("🎉 快速集成测试完成！") 