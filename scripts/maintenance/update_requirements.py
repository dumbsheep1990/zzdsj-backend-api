#!/usr/bin/env python3
"""
更新requirements文件
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict

def get_package_version(package_name: str) -> str:
    """获取包的版本"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', package_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.splitlines():
            if line.startswith('Version:'):
                return line.split(':', 1)[1].strip()
                
    except subprocess.CalledProcessError:
        pass
    
    return 'latest'

def update_requirements_file(requirements_file: Path, new_packages: Dict[str, str]) -> None:
    """更新requirements文件"""
    
    # 读取现有内容
    content = []
    if requirements_file.exists():
        with open(requirements_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
    
    # 添加新包到文件末尾
    if new_packages:
        content.append("\n# ===============================================================================\n")
        content.append("# 自动检测并安装的缺失依赖包\n")
        content.append("# ===============================================================================\n")
        
        for package, version in new_packages.items():
            if version and version != 'latest':
                content.append(f"{package}=={version}\n")
            else:
                content.append(f"{package}\n")
    
    # 写入文件
    with open(requirements_file, 'w', encoding='utf-8') as f:
        f.writelines(content)

def main():
    """主函数"""
    project_root = Path.cwd()
    requirements_file = project_root / "requirements.txt"
    
    # 新安装的包
    new_packages = [
        'beautifulsoup4',
        'langdetect',
        'markitdown',
        'ollama',
        'pgvector',
        'python-jose',
        'rank-bm25',
        'influxdb-client',
    ]
    
    print("📝 更新requirements文件...")
    
    # 获取包版本
    package_versions = {}
    for package in new_packages:
        version = get_package_version(package)
        package_versions[package] = version
        print(f"  - {package}: {version}")
    
    # 更新requirements文件
    update_requirements_file(requirements_file, package_versions)
    
    print(f"\n✅ requirements.txt 已更新，添加了 {len(new_packages)} 个包")

if __name__ == "__main__":
    main() 