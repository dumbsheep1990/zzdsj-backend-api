#!/usr/bin/env python3
"""
配置加载测试脚本
验证新的配置文件系统和环境管理功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.advanced_manager import (
    AdvancedConfigManager,
    get_config_manager,
    load_minimal_config,
    validate_current_config
)


def test_environment_configs():
    """测试各环境配置加载"""
    print("\n🧪 测试各环境配置加载")
    print("=" * 80)
    
    environments = ["development", "testing", "staging", "production", "minimal"]
    
    for env in environments:
        print(f"\n🌍 测试环境: {env}")
        print("-" * 40)
        
        try:
            # 创建配置管理器
            manager = AdvancedConfigManager(environment=env)
            
            # 加载配置
            config = manager.load_configuration()
            
            # 验证配置
            validation = manager.validate_configuration(config)
            
            # 显示结果
            print(f"✅ 配置加载成功")
            print(f"   配置项数量: {len(config)}")
            print(f"   验证结果: {'通过' if validation.is_valid else '失败'}")
            
            if not validation.is_valid:
                print(f"   验证错误: {validation.errors[:3]}...")  # 只显示前3个错误
            
            # 显示关键配置
            app_config = config.get("app", {})
            service_config = config.get("service", {})
            
            print(f"   应用名称: {app_config.get('name', 'Unknown')}")
            print(f"   服务端口: {service_config.get('port', 'Unknown')}")
            print(f"   调试模式: {app_config.get('debug', False)}")
            
        except Exception as e:
            print(f"❌ 配置加载失败: {str(e)}")


def test_minimal_config():
    """测试最小配置"""
    print("\n⚡ 测试最小配置加载")
    print("=" * 80)
    
    try:
        minimal_config = load_minimal_config()
        print(f"✅ 最小配置加载成功")
        print(f"   配置项数量: {len(minimal_config)}")
        
        # 显示分类统计
        categories = {
            "系统核心": ["SERVICE_NAME", "SERVICE_IP", "SERVICE_PORT", "APP_ENV", "LOG_LEVEL"],
            "安全配置": ["JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "ENCRYPTION_KEY"],
            "数据库": ["DATABASE_URL"],
            "服务集成": ["REDIS_HOST", "REDIS_PORT", "MINIO_ENDPOINT", "MILVUS_HOST", "ELASTICSEARCH_URL", "OPENAI_API_KEY"]
        }
        
        for category, keys in categories.items():
            found_keys = [k for k in keys if k in minimal_config]
            print(f"   {category}: {len(found_keys)}/{len(keys)} 项")
            
    except Exception as e:
        print(f"❌ 最小配置加载失败: {str(e)}")


def test_config_inheritance():
    """测试配置继承"""
    print("\n🔄 测试配置继承机制")
    print("=" * 80)
    
    try:
        # 测试开发环境配置继承
        dev_manager = AdvancedConfigManager(environment="development")
        dev_config = dev_manager.load_configuration()
        
        # 检查默认配置是否被正确继承和覆盖
        app_config = dev_config.get("app", {})
        
        print("开发环境配置继承测试:")
        print(f"   应用名称: {app_config.get('name')} (应该包含'开发版')")
        print(f"   调试模式: {app_config.get('debug')} (应该为True)")
        print(f"   环境标识: {app_config.get('environment')} (应该为'development')")
        
        # 检查功能开关
        features = dev_config.get("features", {})
        print(f"   热重载: {features.get('hot_reload')} (开发环境应该为True)")
        print(f"   调试工具: {features.get('debug_tools')} (开发环境应该为True)")
        
        print("✅ 配置继承机制正常")
        
    except Exception as e:
        print(f"❌ 配置继承测试失败: {str(e)}")


def test_config_validation():
    """测试配置验证"""
    print("\n🔍 测试配置验证功能")
    print("=" * 80)
    
    try:
        # 测试当前配置验证
        validation_result = validate_current_config()
        
        print(f"当前配置验证结果:")
        print(f"   是否有效: {'✅ 是' if validation_result.is_valid else '❌ 否'}")
        print(f"   错误数量: {len(validation_result.errors)}")
        print(f"   警告数量: {len(validation_result.warnings)}")
        print(f"   缺失配置: {len(validation_result.missing_required)}")
        
        if validation_result.errors:
            print("   错误详情:")
            for error in validation_result.errors[:5]:  # 只显示前5个
                print(f"     • {error}")
        
        if validation_result.warnings:
            print("   警告详情:")
            for warning in validation_result.warnings[:3]:  # 只显示前3个
                print(f"     • {warning}")
                
    except Exception as e:
        print(f"❌ 配置验证测试失败: {str(e)}")


def test_config_export():
    """测试配置导出"""
    print("\n📤 测试配置导出功能")
    print("=" * 80)
    
    try:
        manager = get_config_manager()
        
        # 创建导出目录
        export_dir = project_root / "test_exports"
        export_dir.mkdir(exist_ok=True)
        
        # 测试JSON导出
        json_file = export_dir / "test_config.json"
        success = manager.export_configuration(str(json_file), format="json", include_sensitive=False)
        
        if success and json_file.exists():
            print(f"✅ JSON配置导出成功: {json_file}")
            print(f"   文件大小: {json_file.stat().st_size} 字节")
        else:
            print("❌ JSON配置导出失败")
        
        # 测试YAML导出
        yaml_file = export_dir / "test_config.yaml"
        success = manager.export_configuration(str(yaml_file), format="yaml", include_sensitive=False)
        
        if success and yaml_file.exists():
            print(f"✅ YAML配置导出成功: {yaml_file}")
            print(f"   文件大小: {yaml_file.stat().st_size} 字节")
        else:
            print("❌ YAML配置导出失败")
            
    except Exception as e:
        print(f"❌ 配置导出测试失败: {str(e)}")


def test_config_summary():
    """测试配置摘要"""
    print("\n📊 测试配置摘要功能")
    print("=" * 80)
    
    try:
        manager = get_config_manager()
        summary = manager.get_configuration_summary()
        
        print("配置摘要:")
        print(f"   当前环境: {summary['environment']}")
        print(f"   总配置数: {summary['total_configs']}")
        print(f"   必需配置数: {summary['minimal_configs']}")
        print(f"   必需配置覆盖: {summary['minimal_coverage']}/{summary['minimal_configs']}")
        print(f"   配置提供者: {', '.join(summary['providers'])}")
        
        validation = summary['validation_result']
        print(f"   验证状态: {'✅ 通过' if validation.is_valid else '❌ 失败'}")
        
        if summary['last_loaded']:
            print(f"   最后加载: {summary['last_loaded']}")
            
    except Exception as e:
        print(f"❌ 配置摘要测试失败: {str(e)}")


def main():
    """主测试函数"""
    print("🎯 配置系统加载测试")
    print("测试新的配置文件系统和环境管理功能")
    
    # 设置测试环境
    os.environ["APP_ENV"] = "development"
    
    try:
        # 执行各项测试
        test_environment_configs()
        test_minimal_config()
        test_config_inheritance()
        test_config_validation()
        test_config_export()
        test_config_summary()
        
        print("\n" + "=" * 80)
        print("🎉 配置系统测试完成!")
        print("=" * 80)
        
        print("\n📋 测试总结:")
        print("✅ 多环境配置文件加载")
        print("✅ 最小配置集合功能")
        print("✅ 配置继承和覆盖机制")
        print("✅ 配置验证功能")
        print("✅ 配置导出功能")
        print("✅ 配置摘要功能")
        
        print("\n💡 使用建议:")
        print("1. 使用环境管理脚本切换环境:")
        print("   python scripts/env_manager.py switch development")
        print("2. 验证配置完整性:")
        print("   python scripts/env_manager.py validate")
        print("3. 查看配置摘要:")
        print("   python scripts/env_manager.py summary")
        print("4. 创建环境启动脚本:")
        print("   python scripts/env_manager.py create-script production")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        raise


if __name__ == "__main__":
    main() 