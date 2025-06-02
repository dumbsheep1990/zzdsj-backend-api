#!/usr/bin/env python3
"""
迁移系统测试脚本
用于测试数据库迁移和初始化功能
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database_initializer import DatabaseInitializer
from vector_db_migrator import VectorDBMigrator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_database_initializer():
    """测试数据库初始化器"""
    print("🧪 测试数据库初始化器...")
    
    initializer = DatabaseInitializer()
    
    # 测试状态检查
    print("📊 检查初始化状态...")
    status = await initializer.check_initialization_status()
    print(f"PostgreSQL状态: {status['postgresql']}")
    print(f"向量数据库状态: {status['vector_database']}")
    print(f"整体状态: {status['overall_status']}")
    
    return status


async def test_vector_db_migrator():
    """测试向量数据库迁移器"""
    print("\n🧪 测试向量数据库迁移器...")
    
    try:
        migrator = VectorDBMigrator("milvus")
        
        # 测试迁移状态
        print("📊 检查向量数据库迁移状态...")
        status = migrator.get_migration_status()
        print(f"向量数据库类型: {status.get('vector_store_type', 'N/A')}")
        print(f"已应用迁移: {status.get('total_applied', 0)}")
        print(f"待执行迁移: {status.get('total_pending', 0)}")
        
        # 获取待执行的迁移
        pending = migrator.get_pending_migrations()
        if pending:
            print("待执行的迁移:")
            for version in pending:
                print(f"  📋 {version}")
        else:
            print("✅ 没有待执行的迁移")
        
        return status
        
    except Exception as e:
        print(f"❌ 向量数据库迁移器测试失败: {str(e)}")
        return {"error": str(e)}


async def test_migration_creation():
    """测试迁移创建功能"""
    print("\n🧪 测试迁移创建功能...")
    
    try:
        migrator = VectorDBMigrator("milvus")
        
        # 创建测试迁移
        print("📝 创建测试迁移...")
        migration = await migrator.create_migration(
            description="测试迁移 - 添加示例集合",
            collections_to_create=[
                {
                    "name": "test_collection",
                    "dimension": 768,
                    "metric_type": "COSINE"
                }
            ]
        )
        
        print(f"✅ 迁移创建成功: {migration.version}")
        print(f"描述: {migration.description}")
        print(f"升级操作数: {len(migration.up_operations)}")
        print(f"降级操作数: {len(migration.down_operations)}")
        
        return migration
        
    except Exception as e:
        print(f"❌ 迁移创建测试失败: {str(e)}")
        return None


def test_file_structure():
    """测试文件结构"""
    print("\n🧪 测试文件结构...")
    
    base_dir = Path(__file__).parent
    
    # 检查必要的文件和目录
    required_paths = [
        base_dir / "database_initializer.py",
        base_dir / "vector_db_migrator.py", 
        base_dir / "migrate.py",
        base_dir / "versions",
        base_dir / "vector_migrations",
        base_dir / "sql" / "common",
        base_dir / "README.md"
    ]
    
    missing_paths = []
    for path in required_paths:
        if path.exists():
            print(f"✅ {path.name}: 存在")
        else:
            print(f"❌ {path.name}: 不存在")
            missing_paths.append(path)
    
    if missing_paths:
        print(f"\n⚠️  缺少 {len(missing_paths)} 个必要文件/目录")
        return False
    else:
        print(f"\n✅ 所有必要文件/目录都存在")
        return True


async def main():
    """主测试函数"""
    print("🚀 开始测试迁移系统...")
    print("=" * 60)
    
    # 测试文件结构
    file_structure_ok = test_file_structure()
    
    # 测试数据库初始化器
    db_status = await test_database_initializer()
    
    # 测试向量数据库迁移器
    vector_status = await test_vector_db_migrator()
    
    # 测试迁移创建
    migration = await test_migration_creation()
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("📋 测试报告")
    print("=" * 60)
    
    print(f"文件结构: {'✅ 正常' if file_structure_ok else '❌ 异常'}")
    print(f"数据库初始化器: {'✅ 正常' if 'error' not in db_status else '❌ 异常'}")
    print(f"向量数据库迁移器: {'✅ 正常' if 'error' not in vector_status else '❌ 异常'}")
    print(f"迁移创建功能: {'✅ 正常' if migration is not None else '❌ 异常'}")
    
    # 给出建议
    print("\n💡 建议:")
    if not file_structure_ok:
        print("- 确保所有必要的文件和目录都存在")
    
    if 'error' in db_status:
        print("- 检查数据库连接配置")
        print("- 确保PostgreSQL服务正在运行")
    
    if 'error' in vector_status:
        print("- 检查向量数据库服务状态")
        print("- 确保向量存储模块正确安装")
    
    print("\n🎯 下一步:")
    print("1. 使用 `python migrate.py status` 检查系统状态")
    print("2. 使用 `python migrate.py init` 初始化数据库")
    print("3. 使用 `python migrate.py migrate` 应用迁移")
    
    print("\n🎉 测试完成!")


if __name__ == "__main__":
    asyncio.run(main()) 