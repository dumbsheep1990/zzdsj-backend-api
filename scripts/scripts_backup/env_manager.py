#!/usr/bin/env python3
"""
环境管理脚本
用于管理不同环境的配置文件和环境切换
"""

import os
import sys
import json
import yaml
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class EnvironmentManager:
    """环境管理器"""
    
    def __init__(self):
        self.project_root = project_root
        self.config_dir = self.project_root / "config"
        self.env_config_file = self.project_root / ".env.config"
        
        # 支持的环境列表
        self.supported_environments = [
            "development", "testing", "staging", "production", "minimal"
        ]
        
        # 配置文件映射
        self.config_files = {
            env: self.config_dir / f"{env}.yaml" 
            for env in self.supported_environments
        }
        self.config_files["default"] = self.config_dir / "default.yaml"
        
        self.current_config = self._load_current_config()
        
    def _load_current_config(self) -> Dict[str, Any]:
        """加载当前环境配置"""
        if self.env_config_file.exists():
            try:
                with open(self.env_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载环境配置失败: {e}")
        
        # 默认配置
        return {
            "current_environment": "development",
            "config_version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "config_mode": "standard",
            "active_config_files": ["default.yaml", "development.yaml"]
        }
    
    def _save_current_config(self):
        """保存当前环境配置"""
        self.current_config["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.env_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, ensure_ascii=False, indent=2)
            print(f"✅ 环境配置已保存到 {self.env_config_file}")
        except Exception as e:
            print(f"❌ 保存环境配置失败: {e}")
    
    def list_environments(self):
        """列出所有支持的环境"""
        print("\n📋 支持的环境列表:")
        print("=" * 60)
        
        current_env = self.current_config.get("current_environment", "unknown")
        
        for env in self.supported_environments:
            config_file = self.config_files[env]
            status = "✅ 存在" if config_file.exists() else "❌ 缺失"
            current_mark = " (当前)" if env == current_env else ""
            
            print(f"  🌍 {env:<12} - {status} - {config_file.name}{current_mark}")
        
        print(f"\n当前环境: {current_env}")
        print(f"配置版本: {self.current_config.get('config_version', 'unknown')}")
        print(f"配置模式: {self.current_config.get('config_mode', 'unknown')}")
    
    def switch_environment(self, environment: str, config_mode: str = "standard") -> bool:
        """切换环境"""
        if environment not in self.supported_environments:
            print(f"❌ 不支持的环境: {environment}")
            print(f"支持的环境: {', '.join(self.supported_environments)}")
            return False
        
        config_file = self.config_files[environment]
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        
        print(f"\n🔄 切换环境: {self.current_config.get('current_environment')} -> {environment}")
        
        # 更新配置
        old_env = self.current_config.get('current_environment')
        self.current_config.update({
            "current_environment": environment,
            "config_mode": config_mode,
            "active_config_files": self._get_active_config_files(environment, config_mode)
        })
        
        # 设置环境变量
        os.environ["APP_ENV"] = environment
        os.environ["CONFIG_MODE"] = config_mode
        
        # 保存配置
        self._save_current_config()
        
        print(f"✅ 环境切换成功")
        print(f"   旧环境: {old_env}")
        print(f"   新环境: {environment}")
        print(f"   配置模式: {config_mode}")
        print(f"   激活的配置文件: {', '.join(self.current_config['active_config_files'])}")
        
        return True
    
    def _get_active_config_files(self, environment: str, config_mode: str) -> List[str]:
        """获取激活的配置文件列表"""
        files = ["default.yaml"]
        
        if config_mode == "minimal":
            files.append("minimal.yaml")
        elif config_mode == "standard":
            files.append(f"{environment}.yaml")
        else:  # custom
            files.append(f"{environment}.yaml")
            if environment != "minimal":
                files.append("minimal.yaml")
        
        return files
    
    def validate_environment(self, environment: str = None) -> bool:
        """验证环境配置"""
        env = environment or self.current_config.get("current_environment")
        
        print(f"\n🔍 验证环境配置: {env}")
        print("=" * 60)
        
        # 检查配置文件
        config_file = self.config_files[env]
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        
        # 加载并验证配置文件
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                print(f"❌ 配置文件为空: {config_file}")
                return False
            
            print(f"✅ 配置文件有效: {config_file.name}")
            print(f"   配置项数量: {len(self._flatten_dict(config))}")
            
            # 检查必需的配置项
            required_sections = ["app", "service", "logging"]
            missing_sections = []
            
            for section in required_sections:
                if section not in config:
                    missing_sections.append(section)
            
            if missing_sections:
                print(f"⚠️ 缺失配置节: {', '.join(missing_sections)}")
            else:
                print("✅ 所有必需配置节存在")
            
            return len(missing_sections) == 0
            
        except Exception as e:
            print(f"❌ 配置文件解析失败: {e}")
            return False
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """展平嵌套字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def show_config_summary(self, environment: str = None):
        """显示配置摘要"""
        env = environment or self.current_config.get("current_environment")
        config_file = self.config_files[env]
        
        print(f"\n📊 配置摘要: {env}")
        print("=" * 60)
        
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                print("❌ 配置文件为空")
                return
            
            # 显示基本信息
            app_config = config.get("app", {})
            print(f"应用名称: {app_config.get('name', 'Unknown')}")
            print(f"应用环境: {app_config.get('environment', 'Unknown')}")
            print(f"调试模式: {app_config.get('debug', False)}")
            
            # 显示服务配置
            service_config = config.get("service", {})
            print(f"服务IP: {service_config.get('ip', 'Unknown')}")
            print(f"服务端口: {service_config.get('port', 'Unknown')}")
            print(f"工作进程: {service_config.get('workers', 1)}")
            
            # 显示功能开关
            features = config.get("features", {})
            if features:
                print("\n功能开关:")
                for feature, enabled in features.items():
                    status = "✅" if enabled else "❌"
                    print(f"  {status} {feature}: {enabled}")
            
            # 显示配置统计
            flat_config = self._flatten_dict(config)
            print(f"\n配置统计:")
            print(f"  总配置项: {len(flat_config)}")
            print(f"  配置节数: {len(config)}")
            
        except Exception as e:
            print(f"❌ 读取配置失败: {e}")
    
    def create_environment_script(self, environment: str):
        """创建环境启动脚本"""
        script_content = f"""#!/bin/bash
# 环境启动脚本 - {environment}
# 自动生成，请勿手动修改

echo "🚀 启动 {environment} 环境..."

# 设置环境变量
export APP_ENV={environment}
export CONFIG_MODE=standard

# 激活Python虚拟环境 (如果存在)
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 已激活虚拟环境"
fi

# 切换到项目目录
cd "{self.project_root}"

# 验证环境配置
python scripts/env_manager.py validate --environment {environment}

if [ $? -eq 0 ]; then
    echo "✅ 环境配置验证通过"
    
    # 启动应用
    echo "🔥 启动应用..."
    python main.py
else
    echo "❌ 环境配置验证失败，请检查配置"
    exit 1
fi
"""
        
        script_file = self.project_root / f"start_{environment}.sh"
        
        try:
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 设置执行权限
            os.chmod(script_file, 0o755)
            
            print(f"✅ 已创建环境启动脚本: {script_file}")
            print(f"使用方法: ./{script_file.name}")
            
        except Exception as e:
            print(f"❌ 创建启动脚本失败: {e}")
    
    def backup_current_config(self):
        """备份当前配置"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / "config_backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份配置文件
        backed_up_files = []
        for env, config_file in self.config_files.items():
            if config_file.exists():
                backup_file = backup_dir / config_file.name
                shutil.copy2(config_file, backup_file)
                backed_up_files.append(config_file.name)
        
        # 备份环境配置
        if self.env_config_file.exists():
            backup_env_file = backup_dir / ".env.config"
            shutil.copy2(self.env_config_file, backup_env_file)
            backed_up_files.append(".env.config")
        
        print(f"✅ 配置备份完成: {backup_dir}")
        print(f"   备份文件: {', '.join(backed_up_files)}")
        
        return backup_dir
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "current_environment": self.current_config.get("current_environment"),
            "config_version": self.current_config.get("config_version"),
            "config_mode": self.current_config.get("config_mode"),
            "last_updated": self.current_config.get("last_updated"),
            "active_config_files": self.current_config.get("active_config_files", []),
            "available_environments": self.supported_environments,
            "config_files_status": {
                env: config_file.exists() 
                for env, config_file in self.config_files.items()
            }
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="知识QA系统环境管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出环境
    subparsers.add_parser("list", help="列出所有支持的环境")
    
    # 切换环境
    switch_parser = subparsers.add_parser("switch", help="切换环境")
    switch_parser.add_argument("environment", choices=EnvironmentManager().supported_environments, help="目标环境")
    switch_parser.add_argument("--mode", choices=["standard", "minimal", "custom"], default="standard", help="配置模式")
    
    # 验证环境
    validate_parser = subparsers.add_parser("validate", help="验证环境配置")
    validate_parser.add_argument("--environment", help="要验证的环境 (默认为当前环境)")
    
    # 显示摘要
    summary_parser = subparsers.add_parser("summary", help="显示配置摘要")
    summary_parser.add_argument("--environment", help="要显示的环境 (默认为当前环境)")
    
    # 创建启动脚本
    script_parser = subparsers.add_parser("create-script", help="创建环境启动脚本")
    script_parser.add_argument("environment", choices=EnvironmentManager().supported_environments, help="目标环境")
    
    # 备份配置
    subparsers.add_parser("backup", help="备份当前配置")
    
    # 显示状态
    subparsers.add_parser("status", help="显示当前状态")
    
    args = parser.parse_args()
    
    manager = EnvironmentManager()
    
    if args.command == "list":
        manager.list_environments()
    elif args.command == "switch":
        manager.switch_environment(args.environment, args.mode)
    elif args.command == "validate":
        success = manager.validate_environment(args.environment)
        sys.exit(0 if success else 1)
    elif args.command == "summary":
        manager.show_config_summary(args.environment)
    elif args.command == "create-script":
        manager.create_environment_script(args.environment)
    elif args.command == "backup":
        manager.backup_current_config()
    elif args.command == "status":
        status = manager.get_current_status()
        print("\n📋 当前状态:")
        print("=" * 60)
        for key, value in status.items():
            if isinstance(value, list):
                print(f"{key}: {', '.join(map(str, value))}")
            elif isinstance(value, dict):
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {'✅' if v else '❌'}")
            else:
                print(f"{key}: {value}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 