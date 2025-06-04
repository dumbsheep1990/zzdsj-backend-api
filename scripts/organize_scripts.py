#!/usr/bin/env python3
"""
项目脚本整理工具
将散落在各处的脚本按功能分类整理到对应目录
"""

import os
import shutil
from pathlib import Path

# 定义脚本分类和目标目录结构
SCRIPT_CATEGORIES = {
    # 数据库相关脚本
    'database': {
        'patterns': [
            'postgres', 'db_', 'database', '_db_', 'sql', 'migration', 
            'uuid', 'trigger', 'permission', 'upgrade', 'remote_db'
        ],
        'keywords': ['postgres', 'database', 'db', 'sql', 'migration', 'upgrade', 'table', 'schema']
    },
    
    # 测试脚本
    'testing': {
        'patterns': [
            'test_', '_test', 'simple_test', 'enhanced_test', 'complete_test'
        ],
        'keywords': ['test', 'verify', 'check', 'validate']
    },
    
    # 配置和环境管理
    'config': {
        'patterns': [
            'config', 'env_', 'setup_', 'init_', '_config_'
        ],
        'keywords': ['config', 'setup', 'init', 'env', 'environment']
    },
    
    # 存储系统相关
    'storage': {
        'patterns': [
            'minio', 'storage', 'core_storage', 'vector_', 'elasticsearch'
        ],
        'keywords': ['minio', 'storage', 'vector', 'elasticsearch', 'es']
    },
    
    # 服务启动和部署
    'deployment': {
        'patterns': [
            'start_', 'run_', 'celery', 'hybrid_search', 'deploy'
        ],
        'keywords': ['start', 'run', 'celery', 'deploy', 'service']
    },
    
    # 数据修复和维护
    'maintenance': {
        'patterns': [
            'fix_', 'cleanup', 'repair', 'recreate', 'demo_data'
        ],
        'keywords': ['fix', 'cleanup', 'repair', 'recreate', 'demo', 'maintenance']
    },
    
    # 系统检查和监控
    'monitoring': {
        'patterns': [
            'check_', 'final_check', 'progress', 'monitor'
        ],
        'keywords': ['check', 'monitor', 'progress', 'final', 'status']
    }
}

def categorize_script(filename):
    """根据文件名判断脚本类别"""
    filename_lower = filename.lower()
    
    # 记录匹配分数
    category_scores = {}
    
    for category, config in SCRIPT_CATEGORIES.items():
        score = 0
        
        # 检查模式匹配
        for pattern in config['patterns']:
            if pattern in filename_lower:
                score += 2
        
        # 检查关键词匹配
        for keyword in config['keywords']:
            if keyword in filename_lower:
                score += 1
        
        if score > 0:
            category_scores[category] = score
    
    # 返回得分最高的类别
    if category_scores:
        return max(category_scores.items(), key=lambda x: x[1])[0]
    
    return 'misc'  # 无法分类的放入misc

def create_directory_structure():
    """创建规范的目录结构"""
    base_scripts_dir = Path('scripts')
    
    directories = {
        'database': '数据库相关脚本',
        'testing': '测试验证脚本', 
        'config': '配置管理脚本',
        'storage': '存储系统脚本',
        'deployment': '部署运行脚本',
        'maintenance': '维护修复脚本',
        'monitoring': '监控检查脚本',
        'misc': '其他未分类脚本'
    }
    
    print("🏗️ 创建目录结构...")
    
    for dir_name, description in directories.items():
        dir_path = base_scripts_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"   📁 {dir_name}/ - {description}")
        
        # 创建README文件
        readme_path = dir_path / 'README.md'
        if not readme_path.exists():
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(f"# {description}\n\n")
                f.write(f"此目录包含{description}相关的脚本文件。\n\n")
                f.write("## 脚本列表\n\n")
                f.write("| 脚本名称 | 功能描述 | 最后更新 |\n")
                f.write("|---------|---------|----------|\n")
                f.write("| | | |\n\n")
    
    return directories

def scan_scripts():
    """扫描所有脚本文件"""
    script_files = []
    
    # 扫描项目根目录
    root_path = Path('.')
    for file_path in root_path.glob('*.py'):
        if file_path.name not in ['organize_scripts.py']:
            script_files.append(file_path)
    
    for file_path in root_path.glob('*.sh'):
        script_files.append(file_path)
    
    # 扫描scripts目录（当前的混乱状态）
    scripts_path = Path('scripts')
    if scripts_path.exists():
        for file_path in scripts_path.rglob('*.py'):
            if file_path.name not in ['organize_scripts.py']:
                script_files.append(file_path)
        for file_path in scripts_path.rglob('*.sh'):
            script_files.append(file_path)
    
    # 扫描zzdsj-backend-api/scripts目录
    backend_scripts_path = Path('zzdsj-backend-api/scripts')
    if backend_scripts_path.exists():
        for file_path in backend_scripts_path.rglob('*.py'):
            script_files.append(file_path)
        for file_path in backend_scripts_path.rglob('*.sh'):
            script_files.append(file_path)
    
    return script_files

def organize_scripts(dry_run=True):
    """整理脚本文件"""
    print("🚀 开始整理项目脚本...")
    print("=" * 60)
    
    # 创建目录结构
    directories = create_directory_structure()
    
    # 扫描所有脚本
    script_files = scan_scripts()
    
    print(f"\n🔍 发现 {len(script_files)} 个脚本文件")
    
    # 分类统计
    categorization = {}
    moves_planned = []
    
    for script_path in script_files:
        category = categorize_script(script_path.name)
        
        if category not in categorization:
            categorization[category] = []
        categorization[category].append(script_path)
        
        # 规划移动操作
        target_dir = Path('scripts') / category
        target_path = target_dir / script_path.name
        
        # 避免将文件移动到自己当前的位置
        if script_path.resolve() != target_path.resolve():
            moves_planned.append((script_path, target_path))
    
    # 显示分类结果
    print("\n📊 脚本分类结果:")
    for category, scripts in categorization.items():
        desc = directories.get(category, '未知类别')
        print(f"   📁 {category}/ ({desc}): {len(scripts)} 个脚本")
        for script in scripts:
            print(f"      • {script}")
    
    print(f"\n📋 计划执行 {len(moves_planned)} 个移动操作")
    
    if dry_run:
        print("\n🔍 预览模式 - 以下是计划的移动操作:")
        for src, dst in moves_planned:
            print(f"   {src} → {dst}")
        
        print(f"\n💡 如需实际执行整理，请运行:")
        print(f"   python3 scripts/organize_scripts.py --execute")
        return
    
    # 实际执行移动
    print("\n🔄 开始执行文件移动...")
    success_count = 0
    error_count = 0
    
    for src, dst in moves_planned:
        try:
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(str(src), str(dst))
            print(f"   ✅ {src} → {dst}")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ 移动失败 {src}: {e}")
            error_count += 1
    
    print(f"\n📈 整理完成统计:")
    print(f"   ✅ 成功移动: {success_count} 个文件")
    print(f"   ❌ 移动失败: {error_count} 个文件")
    
    # 更新README文件
    update_readme_files()

def update_readme_files():
    """更新各目录的README文件"""
    print("\n📝 更新README文件...")
    
    scripts_base = Path('scripts')
    
    for category_dir in scripts_base.iterdir():
        if category_dir.is_dir() and category_dir.name != '__pycache__':
            readme_path = category_dir / 'README.md'
            
            # 收集该目录下的脚本
            scripts = []
            for script_file in category_dir.glob('*.py'):
                if script_file.name != 'README.md':
                    scripts.append(script_file.name)
            for script_file in category_dir.glob('*.sh'):
                scripts.append(script_file.name)
            
            if scripts:
                # 更新README内容
                category_name = category_dir.name
                description = SCRIPT_CATEGORIES.get(category_name, {}).get('description', f'{category_name}相关脚本')
                
                readme_content = f"""# {category_name.title()} Scripts

此目录包含{description}相关的脚本文件。

## 脚本列表

| 脚本名称 | 类型 | 功能描述 |
|---------|------|----------|
"""
                
                for script in sorted(scripts):
                    script_type = "Python" if script.endswith('.py') else "Shell"
                    readme_content += f"| {script} | {script_type} | - |\n"
                
                readme_content += f"""
## 使用说明

请根据具体脚本的功能和要求来使用。大部分Python脚本可以通过以下方式运行：

```bash
python3 {category_dir.name}/script_name.py
```

Shell脚本可以通过以下方式运行：

```bash
chmod +x {category_dir.name}/script_name.sh
./{category_dir.name}/script_name.sh
```

## 注意事项

- 运行前请确保满足脚本的依赖要求
- 部分脚本可能需要特定的环境变量或配置文件
- 建议在测试环境中先验证脚本功能

"""
                
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                print(f"   📝 更新 {readme_path} ({len(scripts)} 个脚本)")

def create_master_index():
    """创建主索引文件"""
    print("\n📑 创建主索引文件...")
    
    index_content = """# 项目脚本索引

本文档提供了项目中所有脚本的完整索引和使用指南。

## 目录结构

```
scripts/
├── database/       # 数据库相关脚本
├── testing/        # 测试验证脚本  
├── config/         # 配置管理脚本
├── storage/        # 存储系统脚本
├── deployment/     # 部署运行脚本
├── maintenance/    # 维护修复脚本
├── monitoring/     # 监控检查脚本
└── misc/          # 其他未分类脚本
```

## 快速导航

"""
    
    scripts_base = Path('scripts')
    
    for category_dir in sorted(scripts_base.iterdir()):
        if category_dir.is_dir() and category_dir.name != '__pycache__':
            scripts = []
            for ext in ['*.py', '*.sh']:
                scripts.extend(category_dir.glob(ext))
            
            if scripts:
                category_desc = {
                    'database': '数据库操作、迁移、升级相关脚本',
                    'testing': '各种测试验证脚本',
                    'config': '系统配置和环境管理脚本', 
                    'storage': '存储系统(MinIO、ES、向量数据库)相关脚本',
                    'deployment': '服务启动和部署脚本',
                    'maintenance': '系统维护和修复脚本',
                    'monitoring': '系统监控和状态检查脚本',
                    'misc': '其他功能脚本'
                }.get(category_dir.name, f'{category_dir.name}相关脚本')
                
                index_content += f"""
### {category_dir.name.title()} ({len(scripts)} 个脚本)

{category_desc}

"""
                for script in sorted(scripts):
                    index_content += f"- [`{script.name}`](./{category_dir.name}/{script.name})\n"
    
    index_content += """

## 使用建议

1. **首次使用**: 从 `config/` 目录的配置脚本开始
2. **系统测试**: 使用 `testing/` 目录的各种测试脚本
3. **数据库操作**: 参考 `database/` 目录的相关脚本
4. **生产部署**: 使用 `deployment/` 目录的启动脚本
5. **日常维护**: 参考 `maintenance/` 和 `monitoring/` 目录

## 注意事项

- 所有脚本都经过重新整理，请更新你的引用路径
- 运行前请仔细阅读各脚本的文档和注释
- 建议在测试环境中先验证功能再用于生产环境

---

*此索引由 `organize_scripts.py` 自动生成*
"""
    
    index_path = Path('scripts/README.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    print(f"   📑 创建主索引: {index_path}")

def main():
    """主函数"""
    import sys
    
    # 检查执行模式
    execute_mode = '--execute' in sys.argv or '-e' in sys.argv
    
    print("🗂️ 项目脚本整理工具")
    print("=" * 50)
    print("功能: 将散落的脚本按功能分类整理到对应目录")
    print()
    
    if not execute_mode:
        print("⚠️ 当前为预览模式，不会实际移动文件")
        print("   如需执行实际整理，请使用 --execute 参数")
        print()
    
    # 执行整理
    organize_scripts(dry_run=not execute_mode)
    
    if execute_mode:
        # 创建主索引
        create_master_index()
        
        print("\n🎉 脚本整理完成!")
        print("📚 新的目录结构已建立，请查看 scripts/README.md 了解详情")

if __name__ == "__main__":
    main() 