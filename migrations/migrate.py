#!/usr/bin/env python3
"""
统一数据库迁移管理工具
支持关系型数据库和向量数据库的完整迁移流程
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database_initializer import DatabaseInitializer
from vector_db_migrator import VectorDBMigrator


def setup_logging(level: str = "INFO"):
    """设置日志配置"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('migrations.log')
        ]
    )


async def init_databases(args) -> Dict[str, Any]:
    """初始化数据库"""
    print("🚀 开始初始化数据库...")
    
    initializer = DatabaseInitializer()
    result = await initializer.initialize_all(
        force_recreate=args.force_recreate,
        skip_vector_db=args.skip_vector_db,
        vector_store_type=args.vector_store_type
    )
    
    # 打印结果
    print("\n📊 初始化结果:")
    for component, details in result.items():
        if isinstance(details, dict) and "status" in details:
            status = "✅" if details["status"] == "success" else "❌" if details["status"] == "error" else "⏭️"
            print(f"{status} {component}: {details['message']}")
            
            # 显示详细信息
            if details.get("details"):
                for key, value in details["details"].items():
                    print(f"    {key}: {value}")
        else:
            print(f"ℹ️  {component}: {details}")
    
    return result


async def migrate_databases(args) -> Dict[str, Any]:
    """迁移数据库到最新版本"""
    print("🔄 开始数据库迁移...")
    
    results = {}
    
    # 向量数据库迁移
    if not args.skip_vector_db:
        print(f"\n📡 迁移向量数据库 ({args.vector_store_type})...")
        vector_migrator = VectorDBMigrator(args.vector_store_type)
        vector_result = await vector_migrator.migrate_to_latest()
        results["vector_db"] = vector_result
        
        if vector_result.get("success"):
            print(f"✅ 向量数据库迁移成功: {vector_result['message']}")
        else:
            print(f"❌ 向量数据库迁移失败: {vector_result['error']}")
    
    # 关系型数据库迁移（使用Alembic）
    print("\n🗃️  迁移关系型数据库...")
    try:
        from alembic.config import Config
        from alembic import command
        
        # 设置Alembic配置
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        
        results["postgresql"] = {
            "success": True,
            "message": "PostgreSQL迁移成功"
        }
        print("✅ PostgreSQL迁移成功")
        
    except Exception as e:
        results["postgresql"] = {
            "success": False,
            "error": str(e)
        }
        print(f"❌ PostgreSQL迁移失败: {str(e)}")
    
    return results


async def check_status(args) -> Dict[str, Any]:
    """检查数据库状态"""
    print("🔍 检查数据库状态...")
    
    results = {}
    
    # 检查关系型数据库状态
    print("\n🗃️  PostgreSQL状态:")
    initializer = DatabaseInitializer()
    pg_status = await initializer.check_initialization_status()
    results["postgresql"] = pg_status
    
    if pg_status.get("overall_status") == "ready":
        print("✅ PostgreSQL数据库就绪")
    else:
        print("❌ PostgreSQL数据库未就绪")
    
    # 检查向量数据库状态
    if not args.skip_vector_db:
        print(f"\n📡 向量数据库状态 ({args.vector_store_type}):")
        vector_migrator = VectorDBMigrator(args.vector_store_type)
        vector_status = vector_migrator.get_migration_status()
        results["vector_db"] = vector_status
        
        print(f"已应用迁移: {vector_status.get('total_applied', 0)}")
        print(f"待执行迁移: {vector_status.get('total_pending', 0)}")
        
        if vector_status.get('pending_migrations'):
            print("待执行的迁移:")
            for version in vector_status['pending_migrations']:
                print(f"  📋 {version}")
    
    return results


async def create_vector_migration(args) -> Dict[str, Any]:
    """创建向量数据库迁移"""
    if not args.description:
        print("❌ 缺少迁移描述，请使用 --description 参数")
        return {"success": False, "error": "缺少迁移描述"}
    
    print(f"📝 创建向量数据库迁移: {args.description}")
    
    vector_migrator = VectorDBMigrator(args.vector_store_type)
    
    # 解析迁移操作
    collections_to_create = []
    if args.create_collections:
        for template_name in args.create_collections:
            collections_to_create.append({
                "name": f"{template_name}_collection",
                "template": template_name
            })
    
    migration = await vector_migrator.create_migration(
        description=args.description,
        collections_to_create=collections_to_create
    )
    
    print(f"✅ 迁移文件已创建: {migration.version}")
    return {
        "success": True,
        "version": migration.version,
        "description": migration.description
    }


async def reset_databases(args) -> Dict[str, Any]:
    """重置数据库"""
    if not args.confirm_reset:
        print("⚠️  这将删除所有数据！如果确认要重置，请添加 --confirm-reset 参数")
        return {"success": False, "error": "需要确认重置"}
    
    print("🔥 重置数据库...")
    
    # 重置所有数据库
    initializer = DatabaseInitializer()
    result = await initializer.initialize_all(
        force_recreate=True,
        skip_vector_db=args.skip_vector_db,
        vector_store_type=args.vector_store_type
    )
    
    print("🔄 数据库重置完成")
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="统一数据库迁移管理工具",
        epilog="""
示例用法:
  python migrate.py init --vector-store-type milvus
  python migrate.py migrate --skip-vector-db
  python migrate.py status
  python migrate.py create-migration --description "添加新的集合" --create-collections document image
  python migrate.py reset --confirm-reset
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 通用参数
    parser.add_argument("--vector-store-type", default="milvus", choices=["milvus", "pgvector"], 
                       help="向量数据库类型")
    parser.add_argument("--skip-vector-db", action="store_true", 
                       help="跳过向量数据库操作")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="日志级别")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化数据库")
    init_parser.add_argument("--force-recreate", action="store_true", 
                           help="强制重新创建数据库")
    
    # migrate 命令
    migrate_parser = subparsers.add_parser("migrate", help="迁移数据库到最新版本")
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="检查数据库状态")
    
    # create-migration 命令
    create_parser = subparsers.add_parser("create-migration", help="创建向量数据库迁移")
    create_parser.add_argument("--description", required=True, help="迁移描述")
    create_parser.add_argument("--create-collections", nargs="*", 
                             help="要创建的集合模板名称")
    
    # reset 命令
    reset_parser = subparsers.add_parser("reset", help="重置数据库（危险操作）")
    reset_parser.add_argument("--confirm-reset", action="store_true", 
                            help="确认要重置数据库")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    async def run_command():
        if args.command == "init":
            return await init_databases(args)
        elif args.command == "migrate":
            return await migrate_databases(args)
        elif args.command == "status":
            return await check_status(args)
        elif args.command == "create-migration":
            return await create_vector_migration(args)
        elif args.command == "reset":
            return await reset_databases(args)
        else:
            print(f"❌ 未知命令: {args.command}")
            return {"success": False, "error": f"未知命令: {args.command}"}
    
    try:
        result = asyncio.run(run_command())
        
        # 打印最终结果
        if result.get("success", True):
            print("\n🎉 操作完成!")
            sys.exit(0)
        else:
            print(f"\n💥 操作失败: {result.get('error', '未知错误')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 发生异常: {str(e)}")
        logging.exception("执行命令时发生异常")
        sys.exit(1)


if __name__ == "__main__":
    main() 