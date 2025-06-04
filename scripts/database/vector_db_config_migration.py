#!/usr/bin/env python3
"""
向量数据库配置迁移和验证脚本
用于将现有的向量数据库配置迁移到新的集成配置系统
"""

import os
import sys
import yaml
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.vector_database_integration import (
    get_vector_db_config_manager,
    validate_integrated_vector_config
)
from app.schemas.vector_store import VectorBackendType


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="向量数据库配置迁移和验证工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 验证当前配置
  python scripts/vector_db_config_migration.py validate

  # 生成配置模板
  python scripts/vector_db_config_migration.py generate-template --backend milvus

  # 迁移旧配置
  python scripts/vector_db_config_migration.py migrate --source old_config.yaml

  # 导出当前配置
  python scripts/vector_db_config_migration.py export --output current_config.yaml

  # 检查配置兼容性
  python scripts/vector_db_config_migration.py check-compatibility
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 验证配置命令
    validate_parser = subparsers.add_parser("validate", help="验证向量数据库配置")
    validate_parser.add_argument("--environment", default=None, help="指定环境")
    validate_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    # 生成模板命令
    template_parser = subparsers.add_parser("generate-template", help="生成配置模板")
    template_parser.add_argument("--backend", choices=["milvus", "pgvector", "elasticsearch", "all"], 
                                default="all", help="后端类型")
    template_parser.add_argument("--output", "-o", help="输出文件路径")
    template_parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="输出格式")
    
    # 迁移配置命令
    migrate_parser = subparsers.add_parser("migrate", help="迁移旧配置")
    migrate_parser.add_argument("--source", "-s", required=True, help="源配置文件路径")
    migrate_parser.add_argument("--output", "-o", help="输出文件路径")
    migrate_parser.add_argument("--backup", action="store_true", help="备份原配置")
    
    # 导出配置命令
    export_parser = subparsers.add_parser("export", help="导出当前配置")
    export_parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    export_parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="输出格式")
    export_parser.add_argument("--include-env", action="store_true", help="包含环境变量")
    
    # 兼容性检查命令
    compat_parser = subparsers.add_parser("check-compatibility", help="检查配置兼容性")
    compat_parser.add_argument("--config", help="配置文件路径")
    
    # 配置总览命令
    summary_parser = subparsers.add_parser("summary", help="显示配置总览")
    summary_parser.add_argument("--environment", help="指定环境")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "validate":
            validate_config(args)
        elif args.command == "generate-template":
            generate_template(args)
        elif args.command == "migrate":
            migrate_config(args)
        elif args.command == "export":
            export_config(args)
        elif args.command == "check-compatibility":
            check_compatibility(args)
        elif args.command == "summary":
            show_summary(args)
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")
        sys.exit(1)


def validate_config(args):
    """验证配置"""
    print("🔍 验证向量数据库配置...")
    
    try:
        # 设置环境
        if args.environment:
            os.environ["APP_ENV"] = args.environment
            print(f"📍 使用环境: {args.environment}")
        
        # 验证配置
        validation_result = validate_integrated_vector_config()
        
        if validation_result["is_valid"]:
            print("✅ 配置验证通过")
        else:
            print("❌ 配置验证失败")
            
            if validation_result.get("errors"):
                print("\n🚨 错误:")
                for error in validation_result["errors"]:
                    print(f"  • {error}")
            
            if validation_result.get("warnings"):
                print("\n⚠️ 警告:")
                for warning in validation_result["warnings"]:
                    print(f"  • {warning}")
        
        # 详细信息
        if args.verbose:
            print("\n📊 配置详情:")
            config_manager = get_vector_db_config_manager()
            vector_config = config_manager.get_vector_database_config()
            
            print(f"  🎯 主要后端: {config_manager.get_primary_backend().value}")
            print(f"  🔄 备用后端: {[b.value for b in config_manager.get_fallback_backends()]}")
            print(f"  📦 自动创建集合: {config_manager.get_auto_create_collections()}")
            print(f"  🔧 自动初始化: {'启用' if config_manager.is_auto_init_enabled() else '禁用'}")
    
    except Exception as e:
        print(f"❌ 验证过程中发生异常: {str(e)}")
        sys.exit(1)


def generate_template(args):
    """生成配置模板"""
    print(f"📝 生成向量数据库配置模板 ({args.backend})...")
    
    template = {}
    
    if args.backend in ["milvus", "all"]:
        template.update(_get_milvus_template())
    
    if args.backend in ["pgvector", "all"]:
        template.update(_get_pgvector_template())
    
    if args.backend in ["elasticsearch", "all"]:
        template.update(_get_elasticsearch_template())
    
    if args.backend == "all":
        template = _get_complete_template()
    
    # 输出模板
    output_path = args.output or f"vector_db_template_{args.backend}.{args.format}"
    
    try:
        if args.format == "yaml":
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(template, f, default_flow_style=False, allow_unicode=True, indent=2)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 模板已生成: {output_path}")
        
    except Exception as e:
        print(f"❌ 生成模板失败: {str(e)}")
        sys.exit(1)


def migrate_config(args):
    """迁移配置"""
    print(f"🔄 迁移配置文件: {args.source}")
    
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ 源文件不存在: {args.source}")
        sys.exit(1)
    
    try:
        # 备份原文件
        if args.backup:
            backup_path = source_path.with_suffix(source_path.suffix + ".backup")
            source_path.rename(backup_path)
            print(f"💾 已备份原文件: {backup_path}")
        
        # 读取原配置
        with open(source_path, 'r', encoding='utf-8') as f:
            if source_path.suffix in ['.yaml', '.yml']:
                old_config = yaml.safe_load(f)
            else:
                old_config = json.load(f)
        
        # 迁移配置
        new_config = _migrate_old_config(old_config)
        
        # 输出新配置
        output_path = args.output or source_path.with_name("migrated_" + source_path.name)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print(f"✅ 配置迁移完成: {output_path}")
        
        # 验证迁移结果
        print("🔍 验证迁移结果...")
        
        # 实现迁移验证逻辑
        try:
            # 1. 检查生成的配置文件是否有效
            with open(output_path, 'r', encoding='utf-8') as f:
                migrated_config = yaml.safe_load(f)
                
            print("✅ 迁移的配置文件格式正确")
            
            # 2. 验证配置结构
            required_sections = ["vector_database"]
            for section in required_sections:
                if section in migrated_config:
                    print(f"✅ 必需配置节存在: {section}")
                else:
                    print(f"❌ 缺少必需配置节: {section}")
                    
            # 3. 验证向量数据库配置
            vector_db_config = migrated_config.get("vector_database", {})
            if vector_db_config:
                print(f"✅ 向量数据库配置包含 {len(vector_db_config)} 个后端")
                
                # 检查支持的后端
                supported_backends = ["milvus", "pgvector", "elasticsearch"]
                configured_backends = [b for b in supported_backends if b in vector_db_config]
                
                if configured_backends:
                    print(f"✅ 已配置的后端: {', '.join(configured_backends)}")
                else:
                    print("⚠️ 没有配置任何向量数据库后端")
                    
                # 验证每个后端的配置完整性
                for backend in configured_backends:
                    backend_config = vector_db_config[backend]
                    if "connection" in backend_config:
                        connection_config = backend_config["connection"]
                        if connection_config:
                            print(f"✅ {backend} 连接配置完整")
                        else:
                            print(f"⚠️ {backend} 连接配置为空")
                    else:
                        print(f"❌ {backend} 缺少连接配置")
            else:
                print("❌ 向量数据库配置为空")
                
            # 4. 验证环境变量引用
            config_str = str(migrated_config)
            env_vars = []
            import re
            env_var_pattern = r'\$\{([^}]+)\}'
            matches = re.findall(env_var_pattern, config_str)
            
            for match in matches:
                var_name = match.split(':')[0]  # 移除默认值部分
                env_vars.append(var_name)
                
            if env_vars:
                unique_env_vars = list(set(env_vars))
                print(f"✅ 发现 {len(unique_env_vars)} 个环境变量引用")
                for var in unique_env_vars[:5]:  # 显示前5个
                    print(f"  • {var}")
                if len(unique_env_vars) > 5:
                    print(f"  ... 和其他 {len(unique_env_vars) - 5} 个变量")
            else:
                print("ℹ️ 没有发现环境变量引用")
                
            # 5. 比较迁移前后的差异
            if os.path.exists(args.source):
                print("📊 迁移前后对比:")
                
                # 统计原配置的向量数据库数量
                original_backends = set()
                if "vector_database" in old_config:
                    original_backends = set(old_config["vector_database"].keys())
                    
                # 统计新配置的向量数据库数量
                new_backends = set()
                if "vector_database" in migrated_config:
                    new_backends = set(migrated_config["vector_database"].keys())
                    
                print(f"  原配置后端: {', '.join(original_backends) if original_backends else '无'}")
                print(f"  新配置后端: {', '.join(new_backends) if new_backends else '无'}")
                
                if new_backends == original_backends:
                    print("✅ 向量数据库后端配置保持一致")
                elif new_backends.issuperset(original_backends):
                    print("✅ 新配置包含了所有原有后端，并可能增加了新后端")
                else:
                    print("⚠️ 配置迁移后可能缺少某些原有后端")
                    
            print("✅ 迁移验证完成")
                
        except yaml.YAMLError as e:
            print(f"❌ 迁移的配置文件YAML格式错误: {e}")
        except Exception as e:
            print(f"❌ 迁移验证失败: {e}")
        
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        sys.exit(1)


def export_config(args):
    """导出配置"""
    print("📤 导出当前向量数据库配置...")
    
    try:
        config_manager = get_vector_db_config_manager()
        
        # 导出配置
        success = config_manager.export_vector_config(args.output, args.format)
        
        if success:
            print(f"✅ 配置已导出: {args.output}")
            
            # 显示配置统计
            vector_config = config_manager.get_vector_database_config()
            print(f"📊 配置统计: {len(vector_config)} 个配置项")
        else:
            print("❌ 导出失败")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ 导出过程中发生异常: {str(e)}")
        sys.exit(1)


def check_compatibility(args):
    """检查兼容性"""
    print("🔍 检查配置兼容性...")
    
    try:
        # 检查依赖
        compatibility_issues = []
        
        # 检查Milvus依赖
        try:
            import pymilvus
            print("✅ Milvus依赖可用")
        except ImportError:
            compatibility_issues.append("Milvus依赖未安装 (pip install pymilvus)")
        
        # 检查PostgreSQL依赖
        try:
            import asyncpg
            import pgvector
            print("✅ PostgreSQL+pgvector依赖可用")
        except ImportError:
            compatibility_issues.append("PostgreSQL+pgvector依赖未安装 (pip install asyncpg pgvector)")
        
        # 检查Elasticsearch依赖
        try:
            import elasticsearch
            print("✅ Elasticsearch依赖可用")
        except ImportError:
            compatibility_issues.append("Elasticsearch依赖未安装 (pip install elasticsearch)")
        
        # 检查配置文件
        project_root = Path(__file__).parent.parent
        config_files = [
            project_root / "config" / "vector_database.yaml",
            project_root / "config" / "default.yaml",
            project_root / "config" / "development.yaml",
        ]
        
        for config_file in config_files:
            if config_file.exists():
                print(f"✅ 配置文件存在: {config_file.name}")
            else:
                compatibility_issues.append(f"配置文件缺失: {config_file}")
        
        # 输出结果
        if compatibility_issues:
            print(f"\n⚠️ 发现 {len(compatibility_issues)} 个兼容性问题:")
            for issue in compatibility_issues:
                print(f"  • {issue}")
        else:
            print("\n✅ 所有兼容性检查通过")
    
    except Exception as e:
        print(f"❌ 兼容性检查失败: {str(e)}")
        sys.exit(1)


def show_summary(args):
    """显示配置总览"""
    print("📊 向量数据库配置总览")
    print("=" * 80)
    
    try:
        # 设置环境
        if args.environment:
            os.environ["APP_ENV"] = args.environment
        
        config_manager = get_vector_db_config_manager()
        vector_config = config_manager.get_vector_database_config()
        
        # 基本信息
        print(f"环境: {os.getenv('APP_ENV', 'development')}")
        print(f"主要后端: {config_manager.get_primary_backend().value}")
        print(f"备用后端: {', '.join([b.value for b in config_manager.get_fallback_backends()])}")
        print(f"自动初始化: {'启用' if config_manager.is_auto_init_enabled() else '禁用'}")
        
        # 后端配置状态
        print("\n🔧 后端配置状态:")
        for backend_type in [VectorBackendType.MILVUS, VectorBackendType.PGVECTOR, VectorBackendType.ELASTICSEARCH]:
            try:
                backend_config = config_manager.get_backend_config(backend_type)
                connection_config = backend_config.get("connection", {})
                
                if connection_config:
                    print(f"  ✅ {backend_type.value}: 已配置")
                else:
                    print(f"  ❌ {backend_type.value}: 未配置")
            except:
                print(f"  ❌ {backend_type.value}: 配置错误")
        
        # 集合配置
        print(f"\n📦 自动创建集合: {', '.join(config_manager.get_auto_create_collections())}")
        
        # 配置验证
        print("\n🔍 配置验证:")
        validation_result = validate_integrated_vector_config()
        if validation_result["is_valid"]:
            print("  ✅ 配置验证通过")
        else:
            print("  ❌ 配置验证失败")
            if validation_result.get("errors"):
                for error in validation_result["errors"][:3]:  # 只显示前3个错误
                    print(f"    • {error}")
        
    except Exception as e:
        print(f"❌ 获取配置总览失败: {str(e)}")
        sys.exit(1)


def _get_milvus_template() -> Dict[str, Any]:
    """获取Milvus配置模板"""
    return {
        "vector_database": {
            "milvus": {
                "connection": {
                    "host": "${MILVUS_HOST:localhost}",
                    "port": "${MILVUS_PORT:19530}",
                    "user": "${MILVUS_USER:}",
                    "password": "${MILVUS_PASSWORD:}",
                    "secure": "${MILVUS_SECURE:false}",
                    "timeout": "${MILVUS_TIMEOUT:10}"
                }
            }
        }
    }


def _get_pgvector_template() -> Dict[str, Any]:
    """获取PostgreSQL+pgvector配置模板"""
    return {
        "vector_database": {
            "pgvector": {
                "connection": {
                    "database_url": "${PGVECTOR_DATABASE_URL:}",
                    "host": "${PGVECTOR_HOST:localhost}",
                    "port": "${PGVECTOR_PORT:5432}",
                    "user": "${PGVECTOR_USER:postgres}",
                    "password": "${PGVECTOR_PASSWORD:password}",
                    "database": "${PGVECTOR_DATABASE:postgres}",
                    "schema_name": "${PGVECTOR_SCHEMA:public}"
                }
            }
        }
    }


def _get_elasticsearch_template() -> Dict[str, Any]:
    """获取Elasticsearch配置模板"""
    return {
        "vector_database": {
            "elasticsearch": {
                "connection": {
                    "es_url": "${ELASTICSEARCH_URL:http://localhost:9200}",
                    "username": "${ELASTICSEARCH_USERNAME:}",
                    "password": "${ELASTICSEARCH_PASSWORD:}",
                    "api_key": "${ELASTICSEARCH_API_KEY:}",
                    "timeout": "${ELASTICSEARCH_TIMEOUT:30}"
                }
            }
        }
    }


def _get_complete_template() -> Dict[str, Any]:
    """获取完整配置模板"""
    return {
        "vector_database": {
            "auto_init": {
                "enabled": True,
                "primary_backend": "milvus",
                "fallback_backends": ["pgvector", "elasticsearch"],
                "auto_create_collections": ["document_collection", "knowledge_base_collection"]
            },
            "common": {
                "default_dimension": 1536,
                "batch_size": 1000,
                "max_connections": 10
            },
            "milvus": _get_milvus_template()["vector_database"]["milvus"],
            "pgvector": _get_pgvector_template()["vector_database"]["pgvector"],
            "elasticsearch": _get_elasticsearch_template()["vector_database"]["elasticsearch"]
        }
    }


def _migrate_old_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """迁移旧配置格式"""
    new_config = {"vector_database": {}}
    
    # 迁移旧的向量存储配置
    if "vector_store" in old_config:
        old_vector = old_config["vector_store"]
        
        # 迁移Milvus配置
        if "milvus" in old_vector:
            old_milvus = old_vector["milvus"]
            new_config["vector_database"]["milvus"] = {
                "connection": {
                    "host": old_milvus.get("host", "localhost"),
                    "port": old_milvus.get("port", 19530),
                    "timeout": 10
                }
            }
    
    # 设置默认的自动初始化配置
    new_config["vector_database"]["auto_init"] = {
        "enabled": True,
        "primary_backend": "milvus",
        "fallback_backends": ["pgvector"],
        "auto_create_collections": ["document_collection", "knowledge_base_collection"]
    }
    
    return new_config


if __name__ == "__main__":
    main() 