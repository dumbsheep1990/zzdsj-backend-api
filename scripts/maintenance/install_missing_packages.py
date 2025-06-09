#!/usr/bin/env python3
"""
安装缺失的第三方包
"""

import subprocess
import sys
from typing import List

def install_packages(packages: List[str]) -> None:
    """安装包列表"""
    for package in packages:
        print(f"📦 正在安装: {package}")
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✅ {package} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ {package} 安装失败: {e.stderr}")

def main():
    """主函数"""
    # 确定需要安装的真正第三方包
    missing_packages = [
        'beautifulsoup4',  # bs4
        'langdetect',      # 语言检测
        'markitdown',      # Markdown转换
        'ollama',          # Ollama客户端
        'pgvector',        # PostgreSQL向量扩展
        'python-jose',     # jose -> python-jose
        'rank-bm25',       # BM25算法
        'influxdb-client', # InfluxDB客户端
    ]
    
    print(f"🚀 开始安装 {len(missing_packages)} 个缺失的包...")
    
    # 安装包
    install_packages(missing_packages)
    
    print("\n✅ 安装完成！")

if __name__ == "__main__":
    main() 