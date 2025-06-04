#!/usr/bin/env python3
"""
配置管理系统演示脚本（简化版）
展示分层配置、最小配置和环境切换功能
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# 添加项目路径到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.advanced_manager import (
    AdvancedConfigManager, 
    get_config_manager,
    load_minimal_config,
    validate_current_config,
    switch_to_environment
)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigSystemDemo:
    """配置系统演示"""
    
    def __init__(self):
        self.manager = None
        
    def demo_basic_configuration(self):
        """演示基础配置管理功能"""
        print("\n" + "="*80)
        print("🔧 基础配置管理功能演示")
        print("="*80)
        
        # 1. 初始化配置管理器
        print("\n1️⃣ 初始化配置管理器...")
        self.manager = AdvancedConfigManager(environment="development")
        
        # 2. 加载配置
        print("\n2️⃣ 加载完整配置...")
        config = self.manager.load_configuration()
        print(f"✅ 加载了 {len(config)} 个配置项")
        
        # 3. 验证配置
        print("\n3️⃣ 验证配置完整性...")
        validation_result = self.manager.validate_configuration(config)
        print(f"✅ 配置验证结果: {'通过' if validation_result.is_valid else '失败'}")
        
        if not validation_result.is_valid:
            print(f"❌ 验证错误: {validation_result.errors}")
            print(f"⚠️ 验证警告: {validation_result.warnings}")
            print(f"❗ 缺失配置: {validation_result.missing_required}")
        
        # 4. 获取配置总览
        print("\n4️⃣ 配置总览...")
        summary = self.manager.get_configuration_summary()
        print(f"📊 环境: {summary['environment']}")
        print(f"📊 总配置数: {summary['total_configs']}")
        print(f"📊 必需配置数: {summary['minimal_configs']}")
        print(f"📊 必需配置覆盖率: {summary['minimal_coverage']}/{summary['minimal_configs']}")
        print(f"📊 配置提供者: {', '.join(summary['providers'])}")
        
    def demo_minimal_configuration(self):
        """演示最小配置功能"""
        print("\n" + "="*80)
        print("⚡ 最小配置功能演示")
        print("="*80)
        
        # 1. 加载最小配置
        print("\n1️⃣ 加载最小配置...")
        minimal_config = load_minimal_config()
        print(f"✅ 最小配置包含 {len(minimal_config)} 个核心配置项:")
        
        for category, configs in self._categorize_minimal_config(minimal_config).items():
            print(f"   📁 {category}: {len(configs)} 项")
            for key in configs[:3]:  # 只显示前3个
                value = minimal_config[key]
                # 屏蔽敏感信息
                if any(sensitive in key.upper() for sensitive in ["KEY", "SECRET", "PASSWORD"]):
                    value = f"{value[:8]}..." if len(str(value)) > 8 else "***"
                print(f"      - {key}: {value}")
            if len(configs) > 3:
                print(f"      ... 还有 {len(configs) - 3} 项")
        
        # 2. 验证最小配置
        print("\n2️⃣ 验证最小配置...")
        try:
            self.manager.minimal_config.validate_minimal_config(minimal_config)
            print("✅ 最小配置验证通过")
        except Exception as e:
            print(f"❌ 最小配置验证失败: {str(e)}")
        
        # 3. 展示最小配置的优势
        print("\n3️⃣ 最小配置特点:")
        print("   🚀 快速启动: 30秒内完成初始化")
        print("   💾 SQLite数据库: 无需外部数据库服务")
        print("   🏠 本地服务: 默认使用localhost")
        print("   🔐 自动安全: 启动时自动生成密钥")
        print("   📦 简化集成: 最少依赖服务")
        
    def demo_environment_switching(self):
        """演示环境切换功能"""
        print("\n" + "="*80)
        print("🔄 环境切换功能演示")
        print("="*80)
        
        environments = ["development", "testing", "minimal"]
        
        for env in environments:
            print(f"\n🌍 切换到 {env} 环境...")
            
            try:
                config = switch_to_environment(env)
                summary = self.manager.get_configuration_summary()
                
                print(f"✅ 成功切换到 {env} 环境")
                print(f"   📊 配置项数量: {summary['total_configs']}")
                print(f"   📊 当前环境: {summary['environment']}")
                print(f"   📊 配置提供者: {', '.join(summary['providers'])}")
                
                # 显示环境特定的配置
                env_specific_configs = self._get_environment_specific_configs(config, env)
                if env_specific_configs:
                    print(f"   🎯 {env} 环境特有配置:")
                    for key, value in list(env_specific_configs.items())[:3]:
                        print(f"      - {key}: {str(value)[:50]}...")
                
            except Exception as e:
                print(f"❌ 环境切换失败: {str(e)}")
        
        # 切换回开发环境
        print(f"\n🔙 切换回 development 环境...")
        switch_to_environment("development")
        
    def demo_configuration_export(self):
        """演示配置导出功能"""
        print("\n" + "="*80)
        print("📤 配置导出功能演示")
        print("="*80)
        
        export_dir = project_root / "exports"
        export_dir.mkdir(exist_ok=True)
        
        # 1. 导出JSON格式配置
        print("\n1️⃣ 导出JSON格式配置...")
        json_file = export_dir / "current_config.json"
        success = self.manager.export_configuration(str(json_file), format="json", include_sensitive=False)
        if success:
            print(f"✅ JSON配置导出成功: {json_file}")
            print(f"   文件大小: {json_file.stat().st_size} 字节")
        
        # 2. 导出YAML格式配置
        print("\n2️⃣ 导出YAML格式配置...")
        yaml_file = export_dir / "current_config.yaml"
        success = self.manager.export_configuration(str(yaml_file), format="yaml", include_sensitive=False)
        if success:
            print(f"✅ YAML配置导出成功: {yaml_file}")
            print(f"   文件大小: {yaml_file.stat().st_size} 字节")
        
        # 3. 导出最小配置
        print("\n3️⃣ 导出最小配置...")
        minimal_config = load_minimal_config()
        minimal_file = export_dir / "minimal_config.json"
        with open(minimal_file, 'w', encoding='utf-8') as f:
            json.dump(minimal_config, f, ensure_ascii=False, indent=2)
        print(f"✅ 最小配置导出成功: {minimal_file}")
        print(f"   配置项数: {len(minimal_config)}")
        
        print(f"\n📁 所有导出文件保存在: {export_dir}")
        
    def demo_config_performance(self):
        """演示配置性能测试"""
        print("\n" + "="*80)
        print("⚡ 配置管理性能测试")
        print("="*80)
        
        import time
        
        # 1. 测试配置加载性能
        print("\n1️⃣ 配置加载性能测试...")
        
        # 完整配置加载
        start_time = time.time()
        config = self.manager.load_configuration(use_cache=False)
        full_load_time = time.time() - start_time
        print(f"   完整配置加载: {full_load_time:.4f}秒 ({len(config)} 项)")
        
        # 缓存配置加载
        start_time = time.time()
        config = self.manager.load_configuration(use_cache=True)
        cached_load_time = time.time() - start_time
        print(f"   缓存配置加载: {cached_load_time:.4f}秒 ({len(config)} 项)")
        
        # 最小配置加载
        start_time = time.time()
        minimal_config = self.manager.load_configuration(minimal_mode=True)
        minimal_load_time = time.time() - start_time
        print(f"   最小配置加载: {minimal_load_time:.4f}秒 ({len(minimal_config)} 项)")
        
        # 2. 性能比较
        print("\n2️⃣ 性能比较:")
        print(f"   缓存加速比: {full_load_time/cached_load_time:.1f}x")
        print(f"   最小配置优势: {full_load_time/minimal_load_time:.1f}x")
        
        # 3. 配置验证性能
        print("\n3️⃣ 配置验证性能测试...")
        start_time = time.time()
        validation_result = self.manager.validate_configuration(config)
        validation_time = time.time() - start_time
        print(f"   配置验证时间: {validation_time:.4f}秒")
        print(f"   验证结果: {'通过' if validation_result.is_valid else '失败'}")
        
    def _categorize_minimal_config(self, config: Dict[str, Any]) -> Dict[str, list]:
        """将最小配置按类别分组"""
        categories = {
            "系统核心": [],
            "安全配置": [],
            "数据库": [],
            "服务集成": [],
            "其他": []
        }
        
        for key in config.keys():
            if key in ["SERVICE_NAME", "SERVICE_IP", "SERVICE_PORT", "APP_ENV", "LOG_LEVEL"]:
                categories["系统核心"].append(key)
            elif any(word in key for word in ["JWT", "SECRET", "KEY", "ENCRYPTION"]):
                categories["安全配置"].append(key)
            elif "DATABASE" in key:
                categories["数据库"].append(key)
            elif any(word in key for word in ["REDIS", "MINIO", "MILVUS", "ELASTICSEARCH", "OPENAI"]):
                categories["服务集成"].append(key)
            else:
                categories["其他"].append(key)
        
        return {k: v for k, v in categories.items() if v}
    
    def _get_environment_specific_configs(self, config: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """获取环境特定的配置"""
        env_keywords = {
            "development": ["DEBUG", "DEV", "LOCAL"],
            "testing": ["TEST", "MOCK", "SPEC"],
            "minimal": ["MINIMAL", "LITE", "BASIC"],
            "production": ["PROD", "LIVE", "RELEASE"]
        }
        
        keywords = env_keywords.get(environment, [])
        env_configs = {}
        
        for key, value in config.items():
            if any(keyword in key.upper() for keyword in keywords):
                env_configs[key] = value
        
        return env_configs


def main():
    """主演示函数"""
    print("🎉 高级配置管理系统演示")
    print("演示分层配置、最小配置和环境切换功能")
    
    demo = ConfigSystemDemo()
    
    try:
        # 基础配置管理
        demo.demo_basic_configuration()
        
        # 最小配置
        demo.demo_minimal_configuration()
        
        # 环境切换
        demo.demo_environment_switching()
        
        # 配置导出
        demo.demo_configuration_export()
        
        # 性能测试
        demo.demo_config_performance()
        
        print("\n" + "="*80)
        print("🎊 演示完成！高级配置管理系统功能展示结束")
        print("="*80)
        
        print("\n📚 相关文档:")
        print("   - 高级配置管理方案: docs/ADVANCED_CONFIG_MANAGEMENT_PLAN.md")
        print("   - 配置最佳实践: docs/CONFIG_BEST_PRACTICES.md")
        
        print("\n💡 使用建议:")
        print("   1. 开发环境: 使用完整配置，启用调试功能")
        print("   2. 测试环境: 使用测试专用配置，模拟生产环境")
        print("   3. 生产环境: 使用生产配置，启用监控和安全功能")
        print("   4. 快速验证: 使用最小配置，快速启动和测试")
        
        print("\n🚀 快速开始:")
        print("   # 最小配置模式启动")
        print("   export APP_ENV=minimal")
        print("   python main.py")
        print()
        print("   # 切换环境")
        print("   export APP_ENV=development")
        print("   python main.py")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {str(e)}")
        raise


if __name__ == "__main__":
    main() 