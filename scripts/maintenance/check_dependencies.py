#!/usr/bin/env python3
"""
依赖检查和管理脚本

功能：
1. 扫描所有Python文件的import语句
2. 识别缺失的依赖包
3. 检查已安装的包
4. 更新requirements文件
5. 自动安装缺失的包
"""

import ast
import os
import re
import sys
import subprocess
import pkg_resources
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict

class DependencyChecker:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.requirements_file = self.project_root / "requirements.txt"
        self.requirements_dev_file = self.project_root / "requirements-dev.txt"
        self.requirements_minimal_file = self.project_root / "requirements-minimal.txt"
        
        # 标准库模块（Python 3.8+）
        self.stdlib_modules = {
            'abc', 'aifc', 'argparse', 'array', 'ast', 'asyncio', 'atexit', 'audioop',
            'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins', 'bz2',
            'calendar', 'cgi', 'cgitb', 'chunk', 'cmd', 'code', 'codecs', 'codeop',
            'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
            'contextlib', 'copy', 'copyreg', 'cProfile', 'csv', 'ctypes', 'curses',
            'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'doctest',
            'email', 'encodings', 'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp',
            'fileinput', 'fnmatch', 'fractions', 'ftplib', 'functools', 'gc',
            'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip', 'hashlib',
            'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp', 'importlib',
            'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3',
            'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal',
            'math', 'mimetypes', 'mmap', 'modulefinder', 'multiprocessing', 'netrc',
            'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev',
            'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform',
            'plistlib', 'poplib', 'posix', 'pprint', 'profile', 'pstats', 'pty',
            'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random',
            're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy',
            'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
            'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
            'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct',
            'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog',
            'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'textwrap',
            'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace',
            'traceback', 'tracemalloc', 'tty', 'turtle', 'types', 'typing',
            'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings',
            'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref',
            'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib'
        }
        
        # 项目内部模块（相对导入）
        self.internal_modules = {'app', 'core', 'config', 'migrations', 'scripts', 'tests'}
        
        # 常见的包名映射（import名 -> PyPI包名）
        self.package_mapping = {
            'cv2': 'opencv-python',
            'PIL': 'Pillow',
            'sklearn': 'scikit-learn',
            'yaml': 'PyYAML',
            'dateutil': 'python-dateutil',
            'dotenv': 'python-dotenv',
            'multipart': 'python-multipart',
            'jwt': 'PyJWT',
            'bcrypt': 'bcrypt',
            'fitz': 'PyMuPDF',
            'docx': 'python-docx',
            'pptx': 'python-pptx',
            'speech_recognition': 'SpeechRecognition',
            'psutil': 'psutil',
            'minio': 'minio',
            'pymilvus': 'pymilvus',
            'elasticsearch': 'elasticsearch',
            'redis': 'redis',
            'celery': 'celery',
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
            'sqlalchemy': 'SQLAlchemy',
            'alembic': 'alembic',
            'pydantic': 'pydantic',
            'httpx': 'httpx',
            'aiohttp': 'aiohttp',
            'requests': 'requests',
            'numpy': 'numpy',
            'pandas': 'pandas',
            'matplotlib': 'matplotlib',
            'plotly': 'plotly',
            'dash': 'dash',
            'transformers': 'transformers',
            'sentence_transformers': 'sentence-transformers',
            'openai': 'openai',
            'anthropic': 'anthropic',
            'zhipuai': 'zhipuai',
            'dashscope': 'dashscope',
            'llama_index': 'llama-index',
            'langchain': 'langchain',
            'haystack': 'farm-haystack',
            'lightrag': 'lightrag',
            'autogen': 'autogen',
            'langgraph': 'langgraph',
            'rdflib': 'rdflib',
            'neo4j': 'neo4j',
            'networkx': 'networkx',
            'mcp': 'mcp',
            'fastmcp': 'fastmcp',
            'owl_toolkit': 'owl-toolkit',
            'toolforge': 'toolforge',
            'pytest': 'pytest',
            'rich': 'rich',
            'click': 'click',
            'tenacity': 'tenacity',
            'cachetools': 'cachetools',
            'structlog': 'structlog',
            'prefect': 'prefect',
            'docker': 'docker',
            'kubernetes': 'kubernetes',
            'nacos': 'nacos-sdk-python',
        }

    def extract_imports_from_file(self, file_path: Path) -> Set[str]:
        """从单个Python文件中提取所有导入的模块"""
        imports = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用AST解析
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
            except SyntaxError:
                # 如果AST解析失败，使用正则表达式
                import_pattern = r'^\s*(?:from\s+(\S+)\s+)?import\s+(.+)'
                for line in content.splitlines():
                    match = re.match(import_pattern, line.strip())
                    if match:
                        if match.group(1):  # from ... import
                            imports.add(match.group(1).split('.')[0])
                        else:  # import ...
                            imported_modules = match.group(2).split(',')
                            for module in imported_modules:
                                module_name = module.strip().split('.')[0].split(' as ')[0]
                                imports.add(module_name)
                                
        except Exception as e:
            print(f"警告：无法处理文件 {file_path}: {e}")
            
        return imports

    def scan_project_imports(self) -> Set[str]:
        """扫描整个项目的导入"""
        all_imports = set()
        
        # 扫描app目录
        app_dir = self.project_root / "app"
        if app_dir.exists():
            for py_file in app_dir.rglob("*.py"):
                imports = self.extract_imports_from_file(py_file)
                all_imports.update(imports)
        
        # 扫描core目录
        core_dir = self.project_root / "core"
        if core_dir.exists():
            for py_file in core_dir.rglob("*.py"):
                imports = self.extract_imports_from_file(py_file)
                all_imports.update(imports)
        
        # 扫描scripts目录
        scripts_dir = self.project_root / "scripts"
        if scripts_dir.exists():
            for py_file in scripts_dir.rglob("*.py"):
                imports = self.extract_imports_from_file(py_file)
                all_imports.update(imports)
        
        # 扫描根目录的Python文件
        for py_file in self.project_root.glob("*.py"):
            imports = self.extract_imports_from_file(py_file)
            all_imports.update(imports)
            
        return all_imports

    def filter_external_packages(self, imports: Set[str]) -> Set[str]:
        """过滤出外部包（非标准库、非项目内部模块）"""
        external_packages = set()
        
        for module in imports:
            # 跳过标准库模块
            if module in self.stdlib_modules:
                continue
            
            # 跳过项目内部模块
            if module in self.internal_modules:
                continue
                
            # 跳过以下划线开头的私有模块
            if module.startswith('_'):
                continue
                
            external_packages.add(module)
            
        return external_packages

    def get_package_name(self, import_name: str) -> str:
        """获取包的PyPI名称"""
        return self.package_mapping.get(import_name, import_name)

    def parse_requirements_file(self, file_path: Path) -> Dict[str, str]:
        """解析requirements文件，返回包名和版本的映射"""
        packages = {}
        
        if not file_path.exists():
            return packages
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析包名和版本
                    if '==' in line:
                        package, version = line.split('==', 1)
                        packages[package.strip()] = version.strip()
                    elif '>=' in line:
                        package = line.split('>=')[0].strip()
                        packages[package] = 'latest'
                    else:
                        packages[line.strip()] = 'latest'
                        
        except Exception as e:
            print(f"警告：无法解析 {file_path}: {e}")
            
        return packages

    def get_installed_packages(self) -> Dict[str, str]:
        """获取已安装的包列表"""
        installed = {}
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.splitlines():
                if '==' in line:
                    package, version = line.split('==', 1)
                    installed[package.strip()] = version.strip()
                    
        except subprocess.CalledProcessError as e:
            print(f"警告：无法获取已安装包列表: {e}")
            
        return installed

    def check_dependencies(self) -> Dict[str, List[str]]:
        """检查依赖情况"""
        print("🔍 扫描项目导入...")
        project_imports = self.scan_project_imports()
        external_packages = self.filter_external_packages(project_imports)
        
        print(f"📦 发现 {len(external_packages)} 个外部包")
        
        # 解析requirements文件
        print("📋 解析requirements文件...")
        requirements_packages = self.parse_requirements_file(self.requirements_file)
        
        # 获取已安装包
        print("🔧 检查已安装包...")
        installed_packages = self.get_installed_packages()
        
        # 分析缺失的包
        missing_in_requirements = []
        missing_installed = []
        package_mapping_needed = []
        
        for import_name in external_packages:
            package_name = self.get_package_name(import_name)
            
            # 检查是否在requirements中
            if package_name not in requirements_packages:
                # 检查是否可能是子包或不同名称
                found_in_requirements = False
                for req_package in requirements_packages:
                    if import_name.lower() in req_package.lower() or req_package.lower() in import_name.lower():
                        found_in_requirements = True
                        break
                
                if not found_in_requirements:
                    missing_in_requirements.append(f"{import_name} -> {package_name}")
            
            # 检查是否已安装
            if package_name not in installed_packages:
                # 检查是否以不同名称安装
                found_installed = False
                for installed_package in installed_packages:
                    if import_name.lower() in installed_package.lower() or installed_package.lower() in import_name.lower():
                        found_installed = True
                        break
                
                if not found_installed:
                    missing_installed.append(package_name)
            
            # 检查是否需要包名映射
            if import_name != package_name and import_name not in self.package_mapping:
                package_mapping_needed.append(f"{import_name} -> {package_name}")
        
        return {
            'all_imports': sorted(project_imports),
            'external_packages': sorted(external_packages),
            'missing_in_requirements': missing_in_requirements,
            'missing_installed': missing_installed,
            'package_mapping_needed': package_mapping_needed,
            'requirements_packages': list(requirements_packages.keys()),
            'installed_packages': list(installed_packages.keys())
        }

    def install_missing_packages(self, packages: List[str]) -> None:
        """安装缺失的包"""
        if not packages:
            print("✅ 没有需要安装的包")
            return
        
        print(f"📦 安装 {len(packages)} 个缺失的包...")
        
        for package in packages:
            print(f"  正在安装: {package}")
            try:
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', package],
                    check=True,
                    capture_output=True
                )
                print(f"  ✅ {package} 安装成功")
            except subprocess.CalledProcessError as e:
                print(f"  ❌ {package} 安装失败: {e}")

    def update_requirements_file(self, missing_packages: List[str]) -> None:
        """更新requirements文件"""
        if not missing_packages:
            print("✅ requirements文件无需更新")
            return
        
        print(f"📝 更新requirements文件，添加 {len(missing_packages)} 个包...")
        
        # 读取现有内容
        content = []
        if self.requirements_file.exists():
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                content = f.readlines()
        
        # 添加新包（获取最新版本）
        new_packages = []
        for package_info in missing_packages:
            if ' -> ' in package_info:
                _, package_name = package_info.split(' -> ', 1)
            else:
                package_name = package_info
            
            try:
                # 尝试获取包信息
                result = subprocess.run(
                    [sys.executable, '-c', f"import pkg_resources; print(pkg_resources.get_distribution('{package_name}').version)"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    version = result.stdout.strip()
                    new_packages.append(f"{package_name}=={version}")
                else:
                    new_packages.append(package_name)
                    
            except Exception:
                new_packages.append(package_name)
        
        # 写入文件
        if new_packages:
            content.append("\n# ===============================================================================\n")
            content.append("# 自动检测添加的依赖包\n")
            content.append("# ===============================================================================\n")
            for package in new_packages:
                content.append(f"{package}\n")
        
        with open(self.requirements_file, 'w', encoding='utf-8') as f:
            f.writelines(content)
        
        print(f"✅ requirements文件已更新，添加了 {len(new_packages)} 个包")

    def generate_report(self, results: Dict) -> str:
        """生成依赖检查报告"""
        report = []
        report.append("# 依赖检查报告")
        report.append("=" * 50)
        
        report.append(f"\n## 统计信息")
        report.append(f"- 总导入模块数: {len(results['all_imports'])}")
        report.append(f"- 外部包数: {len(results['external_packages'])}")
        report.append(f"- requirements中的包数: {len(results['requirements_packages'])}")
        report.append(f"- 已安装包数: {len(results['installed_packages'])}")
        
        if results['missing_in_requirements']:
            report.append(f"\n## 缺失在requirements中的包 ({len(results['missing_in_requirements'])}个)")
            for package in results['missing_in_requirements']:
                report.append(f"- {package}")
        
        if results['missing_installed']:
            report.append(f"\n## 未安装的包 ({len(results['missing_installed'])}个)")
            for package in results['missing_installed']:
                report.append(f"- {package}")
        
        if results['package_mapping_needed']:
            report.append(f"\n## 可能需要包名映射 ({len(results['package_mapping_needed'])}个)")
            for mapping in results['package_mapping_needed']:
                report.append(f"- {mapping}")
        
        report.append(f"\n## 所有外部包")
        for package in results['external_packages']:
            status = "✅"
            if package in [p.split(' -> ')[0] for p in results['missing_in_requirements']]:
                status = "❌ 缺失在requirements"
            elif package in results['missing_installed']:
                status = "⚠️ 未安装"
            report.append(f"- {status} {package}")
        
        return "\n".join(report)

def main():
    """主函数"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()
    
    checker = DependencyChecker(project_root)
    
    print("🚀 开始依赖检查...")
    print(f"📁 项目根目录: {project_root}")
    
    # 检查依赖
    results = checker.check_dependencies()
    
    # 生成报告
    report = checker.generate_report(results)
    print("\n" + report)
    
    # 询问是否安装缺失的包
    if results['missing_installed']:
        response = input(f"\n是否安装 {len(results['missing_installed'])} 个缺失的包？(y/N): ")
        if response.lower() == 'y':
            checker.install_missing_packages(results['missing_installed'])
    
    # 询问是否更新requirements文件
    if results['missing_in_requirements']:
        response = input(f"\n是否更新requirements文件，添加 {len(results['missing_in_requirements'])} 个包？(y/N): ")
        if response.lower() == 'y':
            checker.update_requirements_file(results['missing_in_requirements'])
    
    # 保存报告
    report_file = Path(project_root) / "dependency_check_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📊 报告已保存到: {report_file}")
    
    print("\n✅ 依赖检查完成！")

if __name__ == "__main__":
    main() 