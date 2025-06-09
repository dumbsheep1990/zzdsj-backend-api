#!/usr/bin/env python3
"""
高级配置管理器使用示例
演示热重载、版本管理、配置验证等高级功能
"""

import asyncio
import time
from pathlib import Path
from app.core.config.advanced_manager import (
    get_config_manager, 
    create_config_backup,
    restore_config_version,
    list_config_versions,
    get_config_health,
    add_config_reload_callback,
    ConfigChange
)


def basic_usage_example():
    """基础使用示例"""
    print("=== 基础配置管理示例 ===")
    
    # 获取配置管理器
    config_manager = get_config_manager("development")
    
    # 加载配置
    config = config_manager.load_configuration()
    print(f"加载了 {len(config)} 个配置项")
    
    # 获取单个配置值
    service_name = config_manager.get_config_value("SERVICE_NAME", "unknown")
    print(f"服务名称: {service_name}")
    
    # 验证配置
    validation_result = config_manager.validate_configuration()
    print(f"配置验证结果: {'通过' if validation_result.is_valid else '失败'}")
    
    # 获取配置总览
    summary = config_manager.get_configuration_summary()
    print(f"配置总览: {summary['total_configs']} 个配置项, 环境: {summary['environment']}")


def hot_reload_example():
    """配置热重载示例"""
    print("\n=== 配置热重载示例 ===")
    
    # 获取支持热重载的配置管理器
    config_manager = get_config_manager("development", enable_hot_reload=True)
    
    # 定义配置变更回调函数
    def on_config_changed(changes, new_config):
        print(f"检测到 {len(changes)} 个配置变更:")
        for change in changes:
            if change.change_type == "modified":
                print(f"  - {change.key}: {change.old_value} -> {change.new_value}")
            elif change.change_type == "added":
                print(f"  + {change.key}: {change.new_value}")
            elif change.change_type == "removed":
                print(f"  - {change.key}: {change.old_value} (已删除)")
    
    # 注册配置变更回调
    add_config_reload_callback(on_config_changed)
    
    print("配置热重载监控已启动，修改配置文件将自动触发重载...")
    print("提示: 修改 config.yaml 或 .env 文件测试热重载功能")
    
    # 模拟等待配置文件变更
    print("等待 10 秒检测配置文件变更...")
    time.sleep(10)


def version_management_example():
    """配置版本管理示例"""
    print("\n=== 配置版本管理示例 ===")
    
    # 获取支持版本管理的配置管理器
    config_manager = get_config_manager("development", enable_versioning=True)
    
    # 创建手动备份
    version = create_config_backup("示例备份 - 功能演示")
    if version:
        print(f"创建配置备份成功: {version.version}")
    
    # 列出版本历史
    versions = list_config_versions(limit=5)
    print(f"\n配置版本历史 (最近 {len(versions)} 个版本):")
    for v in versions:
        print(f"  - {v.version} ({v.timestamp.strftime('%Y-%m-%d %H:%M:%S')}) "
              f"[{v.environment}] {v.change_summary}")
    
    # 查看版本差异（如果有多个版本）
    if len(versions) >= 2:
        diff = config_manager.get_config_diff(versions[1].version, versions[0].version)
        if diff:
            print(f"\n版本差异 ({versions[1].version} -> {versions[0].version}):")
            for change in diff:
                print(f"  {change.change_type}: {change.key}")
    
    # 演示版本恢复（仅模拟，不实际执行）
    if versions:
        print(f"\n模拟恢复版本: {versions[0].version}")
        # success = restore_config_version(versions[0].version)
        # print(f"版本恢复{'成功' if success else '失败'}")


def health_monitoring_example():
    """配置健康监控示例"""
    print("\n=== 配置健康监控示例 ===")
    
    # 获取配置健康状态
    health_status = get_config_health()
    
    print(f"整体健康状态: {health_status['overall_health']}")
    print(f"验证结果: {'通过' if health_status['validation_result'].is_valid else '失败'}")
    
    # 缓存状态
    cache_status = health_status['cache_status']
    print(f"缓存状态: {'已缓存' if cache_status['cached'] else '未缓存'}")
    if cache_status['cache_age_seconds']:
        print(f"缓存年龄: {cache_status['cache_age_seconds']:.1f} 秒")
    
    # 热重载状态
    hot_reload_status = health_status['hot_reload_status']
    print(f"热重载: {'启用' if hot_reload_status['enabled'] else '禁用'}, "
          f"状态: {'活跃' if hot_reload_status['active'] else '非活跃'}")
    
    # 版本管理状态
    versioning_status = health_status['versioning_status']
    print(f"版本管理: {'启用' if versioning_status['enabled'] else '禁用'}")
    print(f"版本数量: {versioning_status['version_count']}")
    if versioning_status['latest_version']:
        print(f"最新版本: {versioning_status['latest_version']}")


def environment_switching_example():
    """环境切换示例"""
    print("\n=== 环境切换示例 ===")
    
    config_manager = get_config_manager("development")
    
    # 显示当前环境
    print(f"当前环境: {config_manager.environment}")
    
    # 切换到测试环境
    print("切换到测试环境...")
    new_config = config_manager.switch_environment("testing")
    print(f"新环境配置项数量: {len(new_config)}")
    
    # 切换回开发环境
    print("切换回开发环境...")
    config_manager.switch_environment("development")
    print(f"当前环境: {config_manager.environment}")


def minimal_config_example():
    """最小配置模式示例"""
    print("\n=== 最小配置模式示例 ===")
    
    config_manager = get_config_manager("development")
    
    # 加载最小配置
    minimal_config = config_manager.load_configuration(minimal_mode=True)
    print(f"最小配置项数量: {len(minimal_config)}")
    
    # 显示最小配置项
    print("最小配置项:")
    for key, value in minimal_config.items():
        # 隐藏敏感信息
        if any(keyword in key.upper() for keyword in ["PASSWORD", "SECRET", "KEY"]):
            display_value = "***"
        else:
            display_value = value
        print(f"  {key}: {display_value}")


def export_import_example():
    """配置导出导入示例"""
    print("\n=== 配置导出导入示例 ===")
    
    config_manager = get_config_manager("development")
    
    # 导出配置到JSON文件
    json_path = "/tmp/config_export.json"
    success = config_manager.export_config_with_version(
        json_path, 
        format="json", 
        include_sensitive=False,
        create_version=True
    )
    print(f"配置导出到JSON: {'成功' if success else '失败'}")
    
    # 导出配置到YAML文件
    yaml_path = "/tmp/config_export.yaml"
    success = config_manager.export_configuration(
        yaml_path, 
        format="yaml", 
        include_sensitive=False
    )
    print(f"配置导出到YAML: {'成功' if success else '失败'}")


async def async_usage_example():
    """异步使用示例"""
    print("\n=== 异步使用示例 ===")
    
    config_manager = get_config_manager("development")
    
    # 模拟异步配置加载
    async def load_config_async():
        await asyncio.sleep(0.1)  # 模拟异步操作
        return config_manager.load_configuration()
    
    config = await load_config_async()
    print(f"异步加载配置完成: {len(config)} 个配置项")


def cleanup_example():
    """资源清理示例"""
    print("\n=== 资源清理示例 ===")
    
    config_manager = get_config_manager("development")
    
    # 停止热重载监控
    if config_manager.enable_hot_reload:
        config_manager.stop_hot_reload()
        print("热重载监控已停止")
    
    print("配置管理器资源清理完成")


def main():
    """主函数 - 运行所有示例"""
    print("高级配置管理器功能演示")
    print("=" * 50)
    
    try:
        # 基础功能示例
        basic_usage_example()
        
        # 版本管理示例
        version_management_example()
        
        # 健康监控示例
        health_monitoring_example()
        
        # 环境切换示例
        environment_switching_example()
        
        # 最小配置示例
        minimal_config_example()
        
        # 导出导入示例
        export_import_example()
        
        # 异步使用示例
        asyncio.run(async_usage_example())
        
        # 热重载示例（最后执行，因为会阻塞）
        # hot_reload_example()
        
        print("\n所有示例执行完成!")
        
    except Exception as e:
        print(f"示例执行出错: {str(e)}")
        
    finally:
        # 资源清理
        cleanup_example()


if __name__ == "__main__":
    main() 