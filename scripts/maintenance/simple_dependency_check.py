#!/usr/bin/env python3
"""
简化版依赖检查脚本
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Set, Dict, List

def extract_imports_from_file(file_path: Path) -> Set[str]:
    """从Python文件中提取导入的模块"""
    imports = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 使用正则表达式提取import语句
        patterns = [
            r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import',
        ]
        
        for line in content.splitlines():
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    module_name = match.group(1).split('.')[0]
                    imports.add(module_name)
                    
    except Exception as e:
        print(f"警告：无法处理文件 {file_path}: {e}")
        
    return imports

def scan_project_imports(project_root: Path) -> Set[str]:
    """扫描项目中的所有导入"""
    all_imports = set()
    
    # 扫描目录
    scan_dirs = ['app', 'core', 'scripts']
    
    for dir_name in scan_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            for py_file in dir_path.rglob("*.py"):
                imports = extract_imports_from_file(py_file)
                all_imports.update(imports)
    
    return all_imports

def parse_requirements(file_path: Path) -> Set[str]:
    """解析requirements文件"""
    packages = set()
    
    if not file_path.exists():
        return packages
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 提取包名
                    package = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    if package:
                        packages.add(package)
    except Exception as e:
        print(f"警告：无法解析 {file_path}: {e}")
    
    return packages

def get_installed_packages() -> Set[str]:
    """获取已安装的包"""
    installed = set()
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.splitlines():
            if '==' in line:
                package = line.split('==')[0].strip()
                installed.add(package)
                
    except subprocess.CalledProcessError as e:
        print(f"警告：无法获取已安装包列表: {e}")
    
    return installed

def main():
    """主函数"""
    project_root = Path(os.getcwd())
    
    print("🚀 开始简化依赖检查...")
    print(f"📁 项目根目录: {project_root}")
    
    # 扫描项目导入
    print("🔍 扫描项目导入...")
    project_imports = scan_project_imports(project_root)
    
    # 标准库模块（简化列表）
    stdlib_modules = {
        'os', 'sys', 'json', 'datetime', 'time', 'random', 'math', 'collections',
        'typing', 'pathlib', 'logging', 'asyncio', 'threading', 'subprocess',
        're', 'uuid', 'hashlib', 'base64', 'urllib', 'http', 'functools',
        'itertools', 'copy', 'pickle', 'tempfile', 'shutil', 'glob', 'io',
        'contextlib', 'inspect', 'dataclasses', 'enum', 'abc', 'warnings'
    }
    
    # 项目内部模块
    internal_modules = {'app', 'core', 'config', 'migrations', 'scripts', 'tests'}
    
    # 过滤外部包
    external_imports = set()
    for module in project_imports:
        if module not in stdlib_modules and module not in internal_modules and not module.startswith('_'):
            external_imports.add(module)
    
    print(f"📦 发现 {len(external_imports)} 个外部导入")
    
    # 解析requirements文件
    print("📋 解析requirements文件...")
    requirements_packages = parse_requirements(project_root / "requirements.txt")
    
    # 获取已安装包
    print("🔧 检查已安装包...")
    installed_packages = get_installed_packages()
    
    # 包名映射
    package_mapping = {
        'cv2': 'opencv-python',
        'PIL': 'Pillow',
        'sklearn': 'scikit-learn',
        'yaml': 'PyYAML',
        'dateutil': 'python-dateutil',
        'dotenv': 'python-dotenv',
        'multipart': 'python-multipart',
        'jwt': 'PyJWT',
        'fitz': 'PyMuPDF',
        'docx': 'python-docx',
        'pptx': 'python-pptx',
        'speech_recognition': 'SpeechRecognition',
        'llama_index': 'llama-index',
        'sentence_transformers': 'sentence-transformers',
    }
    
    # 分析缺失包
    missing_packages = []
    potentially_missing = []
    
    for import_name in sorted(external_imports):
        package_name = package_mapping.get(import_name, import_name)
        
        # 检查是否在requirements中
        found_in_requirements = False
        for req_package in requirements_packages:
            if (package_name.lower() == req_package.lower() or 
                import_name.lower() in req_package.lower() or 
                req_package.lower() in import_name.lower()):
                found_in_requirements = True
                break
        
        if not found_in_requirements:
            # 检查是否已安装
            found_installed = False
            for installed_package in installed_packages:
                if (package_name.lower() == installed_package.lower() or 
                    import_name.lower() in installed_package.lower() or 
                    installed_package.lower() in import_name.lower()):
                    found_installed = True
                    break
            
            if found_installed:
                potentially_missing.append(f"{import_name} -> {package_name}")
            else:
                missing_packages.append(package_name)
    
    # 打印结果
    print("\n" + "="*60)
    print("📊 依赖检查结果")
    print("="*60)
    
    print(f"\n📈 统计信息:")
    print(f"  - 总导入模块: {len(project_imports)}")
    print(f"  - 外部导入: {len(external_imports)}")
    print(f"  - requirements中的包: {len(requirements_packages)}")
    print(f"  - 已安装包: {len(installed_packages)}")
    
    if potentially_missing:
        print(f"\n📋 可能缺失在requirements中的包 ({len(potentially_missing)}个):")
        for package in potentially_missing[:20]:  # 只显示前20个
            print(f"  - {package}")
        if len(potentially_missing) > 20:
            print(f"  ... 还有 {len(potentially_missing) - 20} 个")
    
    if missing_packages:
        print(f"\n❌ 可能需要安装的包 ({len(missing_packages)}个):")
        for package in missing_packages[:20]:  # 只显示前20个
            print(f"  - {package}")
        if len(missing_packages) > 20:
            print(f"  ... 还有 {len(missing_packages) - 20} 个")
    
    # 显示一些常见的外部导入
    print(f"\n🔍 常见外部导入:")
    common_external = sorted(list(external_imports))[:30]
    for i, module in enumerate(common_external):
        if i % 6 == 0:
            print()
        print(f"  {module:<15}", end="")
    print()
    
    print(f"\n✅ 检查完成！")
    
    # 询问是否需要更新requirements
    if potentially_missing:
        print(f"\n💡 建议检查以上 {len(potentially_missing)} 个可能缺失的包")
        print("   这些包可能已安装但未在requirements.txt中列出")

if __name__ == "__main__":
    main() 