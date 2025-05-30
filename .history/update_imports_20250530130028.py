#!/usr/bin/env python3
"""
批量更新导入路径的脚本
将 'from app.core' 改为 'from core'
"""

import os
import re
from pathlib import Path

def update_imports_in_file(file_path: Path):
    """更新单个文件中的导入路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录原始内容
        original_content = content
        
        # 替换 'from app.core' 为 'from core' (但排除core目录内的文件)
        if 'core/' not in str(file_path):
            content = re.sub(r'from app\.core', 'from core', content)
        else:
            # 对于core目录内的文件，将 'from app.core' 改为相对导入
            content = re.sub(r'from app\.core\.([^.\s]+)', r'from .\1', content)
            content = re.sub(r'from app\.core', 'from .', content)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 更新: {file_path}")
            return True
        
    except Exception as e:
        print(f"❌ 错误处理 {file_path}: {e}")
        return False
    
    return False

def main():
    """主函数"""
    print("🔄 开始批量更新导入路径...")
    
    # 需要更新的目录
    directories = [
        "app/",
        "core/", 
        "tests/",
        "main.py"
    ]
    
    updated_files = 0
    total_files = 0
    
    for directory in directories:
        if os.path.isfile(directory):
            # 处理单个文件
            if update_imports_in_file(Path(directory)):
                updated_files += 1
            total_files += 1
        else:
            # 处理目录
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        if update_imports_in_file(file_path):
                            updated_files += 1
                        total_files += 1
    
    print(f"\n📊 更新完成！")
    print(f"总文件数: {total_files}")
    print(f"更新文件数: {updated_files}")

if __name__ == "__main__":
    main() 