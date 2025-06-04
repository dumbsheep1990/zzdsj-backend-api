#!/usr/bin/env python3
"""
脚本清理工具
整理scripts目录，删除历史和重复的配置管理脚本
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any


class ScriptCleaner:
    """脚本清理器"""
    
    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        
        # 核心保留脚本 - 这些是主要功能脚本
        self.core_scripts = {
            "env_manager.py": "环境管理主脚本 - 配置环境切换、验证和管理",
            "test_config_loading.py": "配置加载测试脚本 - 验证配置系统功能",
        }
        
        # 可选保留脚本 - 有用但非核心的脚本
        self.optional_scripts = {
            "config_system_demo.py": "配置系统演示脚本 - 展示配置管理功能",
            "advanced_config_demo.py": "高级配置演示脚本 - 展示高级功能",
            "verify_knowledge_service_migration.py": "服务迁移验证脚本 - 特定用途",
        }
        
        # 历史脚本 - 需要删除的脚本
        self.deprecated_scripts = [
            # 备份文件
            "config_validation_standalone.py.backup",
            "config_validation_standalone.py.backup2", 
            "config_validation_standalone_backup.py",
            
            # 重复的配置修复脚本（功能已整合到env_manager中）
            "config_optimization_executor.py",
            "config_cleanup_executor.py", 
            "config_repair_executor.py",
            "comprehensive_config_fix.py",
            "config_completeness_fix.py",
            "add_missing_configs.py",
            
            # 分析脚本（一次性使用，已完成任务）
            "config_reference_mapper.py",
            "config_usage_analyzer.py", 
            "analyze_missing_configs.py",
            "update_config_definitions.py",
            
            # 独立验证脚本（功能已整合）
            "config_validation_standalone.py",
            "config_validation.py",
            "config_sync.py",
            "config_hardcode_cleanup.py",
        ]
    
    def analyze_scripts(self):
        """分析当前scripts目录的脚本"""
        print("📊 脚本目录分析")
        print("=" * 80)
        
        all_scripts = [f for f in self.scripts_dir.glob("*.py") if f.name != "cleanup_scripts.py"]
        
        print(f"总脚本数量: {len(all_scripts)}")
        print(f"核心脚本: {len(self.core_scripts)}")
        print(f"可选脚本: {len(self.optional_scripts)}")
        print(f"待删除脚本: {len(self.deprecated_scripts)}")
        
        # 检查脚本状态
        print("\n📋 脚本分类:")
        print("-" * 40)
        
        print("🔵 核心脚本 (保留):")
        for script, desc in self.core_scripts.items():
            status = "✅ 存在" if (self.scripts_dir / script).exists() else "❌ 缺失"
            print(f"  • {script:<30} - {status}")
            print(f"    {desc}")
        
        print("\n🟡 可选脚本 (可保留):")
        for script, desc in self.optional_scripts.items():
            status = "✅ 存在" if (self.scripts_dir / script).exists() else "❌ 缺失" 
            print(f"  • {script:<30} - {status}")
            print(f"    {desc}")
        
        print("\n🔴 历史脚本 (建议删除):")
        for script in self.deprecated_scripts:
            status = "✅ 存在" if (self.scripts_dir / script).exists() else "❌ 已删除"
            print(f"  • {script:<40} - {status}")
        
        # 检查未分类脚本
        all_known_scripts = set(self.core_scripts.keys()) | set(self.optional_scripts.keys()) | set(self.deprecated_scripts)
        unknown_scripts = [f.name for f in all_scripts if f.name not in all_known_scripts]
        
        if unknown_scripts:
            print("\n⚠️ 未分类脚本:")
            for script in unknown_scripts:
                print(f"  • {script}")
    
    def create_backup(self):
        """创建备份"""
        backup_dir = self.scripts_dir.parent / "scripts_backup"
        
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        shutil.copytree(self.scripts_dir, backup_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"✅ 脚本备份已创建: {backup_dir}")
        
        return backup_dir
    
    def cleanup_deprecated_scripts(self, create_backup: bool = True):
        """清理历史脚本"""
        print("\n🧹 清理历史脚本")
        print("=" * 80)
        
        if create_backup:
            backup_dir = self.create_backup()
            print(f"📦 备份位置: {backup_dir}")
        
        deleted_count = 0
        not_found_count = 0
        
        for script_name in self.deprecated_scripts:
            script_path = self.scripts_dir / script_name
            
            if script_path.exists():
                try:
                    script_path.unlink()
                    print(f"🗑️ 已删除: {script_name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ 删除失败 {script_name}: {e}")
            else:
                print(f"⚪ 未找到: {script_name}")
                not_found_count += 1
        
        print(f"\n📊 清理结果:")
        print(f"  删除成功: {deleted_count}")
        print(f"  未找到: {not_found_count}")
        print(f"  删除失败: {len(self.deprecated_scripts) - deleted_count - not_found_count}")
    
    def cleanup_pycache(self):
        """清理Python缓存"""
        print("\n🧹 清理Python缓存")
        print("-" * 40)
        
        pycache_dir = self.scripts_dir / "__pycache__"
        if pycache_dir.exists():
            shutil.rmtree(pycache_dir)
            print("✅ 已删除 __pycache__ 目录")
        else:
            print("⚪ __pycache__ 目录不存在")
        
        # 删除.pyc文件
        pyc_files = list(self.scripts_dir.glob("*.pyc"))
        for pyc_file in pyc_files:
            pyc_file.unlink()
            print(f"🗑️ 已删除: {pyc_file.name}")
        
        if not pyc_files:
            print("⚪ 未找到.pyc文件")
    
    def create_scripts_readme(self):
        """创建scripts目录的README文档"""
        readme_content = """# Scripts Directory

## 📁 目录说明

此目录包含项目的配置管理和环境管理脚本。

## 🔧 核心脚本

### env_manager.py
环境管理主脚本，提供以下功能：
- 环境切换和验证
- 配置文件管理
- 启动脚本生成
- 配置备份和恢复

使用方法：
```bash
# 列出所有环境
python scripts/env_manager.py list

# 切换环境
python scripts/env_manager.py switch development

# 验证环境配置
python scripts/env_manager.py validate

# 查看配置摘要
python scripts/env_manager.py summary

# 创建启动脚本
python scripts/env_manager.py create-script development

# 备份当前配置
python scripts/env_manager.py backup

# 查看状态
python scripts/env_manager.py status
```

### test_config_loading.py
配置加载测试脚本，验证配置系统功能：
- 多环境配置加载测试
- 最小配置测试
- 配置继承机制测试
- 配置验证测试
- 配置导出测试

使用方法：
```bash
python scripts/test_config_loading.py
```

## 🎯 可选脚本

### config_system_demo.py
配置系统演示脚本，展示配置管理功能的使用示例。

### advanced_config_demo.py  
高级配置演示脚本，展示高级配置管理功能。

### verify_knowledge_service_migration.py
服务迁移验证脚本，用于特定的服务迁移验证任务。

## 📖 使用指南

1. **环境管理**：使用 `env_manager.py` 进行环境切换和配置管理
2. **配置测试**：使用 `test_config_loading.py` 验证配置系统
3. **功能演示**：使用demo脚本了解配置系统功能

## 🔗 相关文档

- [配置系统使用指南](../docs/CONFIG_USAGE_GUIDE.md)
- [最小配置使用指南](../docs/MINIMAL_CONFIG_GUIDE.md)
- [启动流程改进总结](../docs/STARTUP_IMPROVEMENTS.md)

---

*最后更新: 2024-12-02*
"""
        
        readme_path = self.scripts_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ 已创建README文档: {readme_path}")
    
    def generate_cleanup_report(self):
        """生成清理报告"""
        report_content = f"""# Scripts 清理报告

## 📊 清理统计

- **总脚本数**: 原有 {len(list(self.scripts_dir.glob('*.py')))} 个
- **保留核心脚本**: {len(self.core_scripts)} 个
- **保留可选脚本**: {len(self.optional_scripts)} 个  
- **删除历史脚本**: {len(self.deprecated_scripts)} 个

## 🔵 保留的核心脚本

"""
        for script, desc in self.core_scripts.items():
            report_content += f"- **{script}**: {desc}\n"
        
        report_content += "\n## 🟡 保留的可选脚本\n\n"
        for script, desc in self.optional_scripts.items():
            report_content += f"- **{script}**: {desc}\n"
        
        report_content += "\n## 🔴 删除的历史脚本\n\n"
        for script in self.deprecated_scripts:
            report_content += f"- ~~{script}~~ (已删除)\n"
        
        report_content += f"""
## ✅ 清理效果

清理后的scripts目录更加简洁和维护友好：

1. **功能集中**: 主要功能集中在 `env_manager.py` 中
2. **减少冗余**: 删除了重复和过时的脚本
3. **文档完善**: 添加了README文档说明
4. **结构清晰**: 明确了核心脚本和可选脚本

## 🔗 使用建议

- 日常使用：主要使用 `env_manager.py` 进行环境和配置管理
- 测试验证：使用 `test_config_loading.py` 验证配置系统
- 功能学习：参考demo脚本了解高级功能

---

*清理时间: {os.popen('date').read().strip()}*
"""
        
        report_path = self.scripts_dir.parent / "scripts_cleanup_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ 已生成清理报告: {report_path}")


def main():
    """主函数"""
    print("🧹 Scripts 目录清理工具")
    print("=" * 80)
    
    cleaner = ScriptCleaner()
    
    # 分析当前状态
    cleaner.analyze_scripts()
    
    # 询问是否执行清理
    print(f"\n❓ 是否执行清理操作？")
    print(f"   将删除 {len(cleaner.deprecated_scripts)} 个历史脚本")
    print(f"   保留 {len(cleaner.core_scripts) + len(cleaner.optional_scripts)} 个有用脚本")
    
    response = input("\n请输入 'yes' 确认执行清理: ").strip().lower()
    
    if response == 'yes':
        # 执行清理
        cleaner.cleanup_deprecated_scripts(create_backup=True)
        cleaner.cleanup_pycache()
        cleaner.create_scripts_readme()
        cleaner.generate_cleanup_report()
        
        print("\n🎉 脚本清理完成！")
        print("\n💡 清理后的目录结构更加简洁，主要使用以下脚本：")
        print("   • env_manager.py - 环境管理")
        print("   • test_config_loading.py - 配置测试")
        print("   • README.md - 使用说明")
        
    else:
        print("\n❌ 清理操作已取消")
        print("💡 如需手动清理，可以删除以下脚本：")
        for script in cleaner.deprecated_scripts:
            print(f"   • {script}")


if __name__ == "__main__":
    main() 