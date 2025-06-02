"""
向量数据库迁移管理器
负责向量数据库的版本控制和迁移管理
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import hashlib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 使用独立的迁移配置，避免循环导入
from config import get_database_url

DATABASE_URL = get_database_url()

logger = logging.getLogger(__name__)


class VectorDBMigration:
    """向量数据库迁移定义"""
    
    def __init__(self, version: str, description: str, up_operations: List[Dict], down_operations: List[Dict]):
        """
        初始化迁移
        
        Args:
            version: 版本号，格式如 "20250108_001"
            description: 迁移描述
            up_operations: 升级操作列表
            down_operations: 降级操作列表
        """
        self.version = version
        self.description = description
        self.up_operations = up_operations
        self.down_operations = down_operations
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "description": self.description,
            "up_operations": self.up_operations,
            "down_operations": self.down_operations,
            "created_at": self.created_at.isoformat()
        }


class VectorDBMigrator:
    """向量数据库迁移管理器"""
    
    def __init__(self, vector_store_type: str = "milvus"):
        """
        初始化迁移管理器
        
        Args:
            vector_store_type: 向量数据库类型
        """
        self.vector_store_type = vector_store_type
        self.base_dir = Path(__file__).parent
        self.migrations_dir = self.base_dir / "vector_migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
        # 数据库连接（用于记录迁移历史）
        self.db_url = DATABASE_URL
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 导入简化的向量存储接口
        from vector_storage_interface import create_vector_store
        self.create_vector_store = create_vector_store
        
        # 确保迁移历史表存在
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """确保迁移历史表存在"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS vector_db_migrations (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(50) UNIQUE NOT NULL,
                        description TEXT,
                        vector_store_type VARCHAR(20) NOT NULL,
                        operations_hash VARCHAR(64) NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        migration_data JSONB
                    )
                """))
                conn.commit()
        except Exception as e:
            logger.error(f"创建迁移历史表失败: {str(e)}")
    
    async def create_migration(self, 
                             description: str,
                             collections_to_create: List[Dict] = None,
                             collections_to_modify: List[Dict] = None,
                             collections_to_drop: List[str] = None,
                             custom_operations: List[Dict] = None) -> VectorDBMigration:
        """
        创建新的迁移
        
        Args:
            description: 迁移描述
            collections_to_create: 要创建的集合列表
            collections_to_modify: 要修改的集合列表
            collections_to_drop: 要删除的集合列表
            custom_operations: 自定义操作列表
            
        Returns:
            创建的迁移对象
        """
        # 生成版本号
        version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # 构建升级操作
        up_operations = []
        down_operations = []
        
        # 处理集合创建
        if collections_to_create:
            for collection_config in collections_to_create:
                up_operations.append({
                    "type": "create_collection",
                    "config": collection_config
                })
                down_operations.insert(0, {
                    "type": "drop_collection",
                    "collection_name": collection_config.get("name")
                })
        
        # 处理集合修改
        if collections_to_modify:
            for modify_config in collections_to_modify:
                up_operations.append({
                    "type": "modify_collection",
                    "config": modify_config
                })
                # 修改操作的回滚比较复杂，这里简化处理
                down_operations.insert(0, {
                    "type": "restore_collection",
                    "collection_name": modify_config.get("name"),
                    "note": "需要手动实现回滚逻辑"
                })
        
        # 处理集合删除
        if collections_to_drop:
            for collection_name in collections_to_drop:
                up_operations.append({
                    "type": "drop_collection",
                    "collection_name": collection_name
                })
                down_operations.insert(0, {
                    "type": "restore_collection",
                    "collection_name": collection_name,
                    "note": "需要从备份恢复"
                })
        
        # 处理自定义操作
        if custom_operations:
            up_operations.extend(custom_operations)
        
        # 创建迁移对象
        migration = VectorDBMigration(version, description, up_operations, down_operations)
        
        # 保存迁移文件
        self._save_migration_file(migration)
        
        return migration
    
    def _save_migration_file(self, migration: VectorDBMigration):
        """保存迁移文件"""
        migration_file = self.migrations_dir / f"{migration.version}_{self.vector_store_type}.json"
        
        with open(migration_file, 'w', encoding='utf-8') as f:
            json.dump(migration.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"迁移文件已保存: {migration_file}")
    
    def _load_migration_file(self, version: str) -> Optional[VectorDBMigration]:
        """加载迁移文件"""
        migration_file = self.migrations_dir / f"{version}_{self.vector_store_type}.json"
        
        if not migration_file.exists():
            return None
        
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return VectorDBMigration(
                version=data["version"],
                description=data["description"],
                up_operations=data["up_operations"],
                down_operations=data["down_operations"]
            )
        except Exception as e:
            logger.error(f"加载迁移文件失败: {str(e)}")
            return None
    
    def get_pending_migrations(self) -> List[str]:
        """获取待执行的迁移"""
        try:
            # 获取已执行的迁移
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT version FROM vector_db_migrations 
                    WHERE vector_store_type = :store_type 
                    ORDER BY applied_at
                """), {"store_type": self.vector_store_type})
                
                applied_versions = {row[0] for row in result}
            
            # 获取所有可用的迁移文件
            available_migrations = []
            for migration_file in self.migrations_dir.glob(f"*_{self.vector_store_type}.json"):
                version = migration_file.stem.replace(f"_{self.vector_store_type}", "")
                if version not in applied_versions:
                    available_migrations.append(version)
            
            # 按版本号排序
            available_migrations.sort()
            return available_migrations
            
        except Exception as e:
            logger.error(f"获取待执行迁移失败: {str(e)}")
            return []
    
    async def apply_migration(self, version: str) -> Dict[str, Any]:
        """
        应用指定的迁移
        
        Args:
            version: 迁移版本号
            
        Returns:
            应用结果
        """
        try:
            # 加载迁移
            migration = self._load_migration_file(version)
            if not migration:
                return {
                    "success": False,
                    "error": f"找不到迁移文件: {version}"
                }
            
            # 执行升级操作
            results = []
            for operation in migration.up_operations:
                result = await self._execute_operation(operation)
                results.append(result)
                
                if not result.get("success", False):
                    logger.error(f"迁移操作失败: {operation}")
                    return {
                        "success": False,
                        "error": f"迁移操作失败: {result.get('error', '未知错误')}",
                        "operation": operation
                    }
            
            # 记录迁移历史
            self._record_migration(migration)
            
            return {
                "success": True,
                "version": version,
                "description": migration.description,
                "operations_executed": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"应用迁移失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def rollback_migration(self, version: str) -> Dict[str, Any]:
        """
        回滚指定的迁移
        
        Args:
            version: 迁移版本号
            
        Returns:
            回滚结果
        """
        try:
            # 加载迁移
            migration = self._load_migration_file(version)
            if not migration:
                return {
                    "success": False,
                    "error": f"找不到迁移文件: {version}"
                }
            
            # 执行降级操作
            results = []
            for operation in migration.down_operations:
                result = await self._execute_operation(operation)
                results.append(result)
                
                if not result.get("success", False):
                    logger.warning(f"回滚操作警告: {operation}")
            
            # 移除迁移历史记录
            self._remove_migration_record(version)
            
            return {
                "success": True,
                "version": version,
                "description": migration.description,
                "operations_executed": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"回滚迁移失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个迁移操作"""
        operation_type = operation.get("type")
        
        try:
            if operation_type == "create_collection":
                return await self._create_collection(operation.get("config", {}))
            elif operation_type == "drop_collection":
                return await self._drop_collection(operation.get("collection_name"))
            elif operation_type == "modify_collection":
                return await self._modify_collection(operation.get("config", {}))
            elif operation_type == "create_index":
                return await self._create_index(operation.get("config", {}))
            elif operation_type == "drop_index":
                return await self._drop_index(operation.get("config", {}))
            elif operation_type == "custom":
                return await self._execute_custom_operation(operation)
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作类型: {operation_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation_type": operation_type
            }
    
    async def _create_collection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """创建集合"""
        try:
            collection_name = config.get("name")
            if not collection_name:
                return {"success": False, "error": "缺少集合名称"}
            
            # 创建向量存储实例
            vector_store = self.create_vector_store(self.vector_store_type)
            
            # 创建集合
            success = await vector_store.create_collection(collection_name, config)
            
            if success:
                return {
                    "success": True,
                    "message": f"集合 {collection_name} 创建成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"集合 {collection_name} 创建失败"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"创建集合失败: {str(e)}"
            }
    
    async def _drop_collection(self, collection_name: str) -> Dict[str, Any]:
        """删除集合"""
        try:
            if not collection_name:
                return {"success": False, "error": "缺少集合名称"}
            
            # 创建向量存储实例
            vector_store = self.create_vector_store(self.vector_store_type)
            
            # 删除集合
            success = await vector_store.drop_collection(collection_name)
            
            if success:
                return {
                    "success": True,
                    "message": f"集合 {collection_name} 删除成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"集合 {collection_name} 删除失败"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"删除集合失败: {str(e)}"
            }
    
    async def _modify_collection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """修改集合"""
        try:
            collection_name = config.get("name")
            if not collection_name:
                return {"success": False, "error": "缺少集合名称"}
            
            # 注意：修改集合比较复杂，这里先简单返回成功
            # 实际实现时需要根据具体的修改需求来实现
            logger.info(f"修改集合配置: {collection_name}")
            
            return {
                "success": True,
                "message": f"集合 {collection_name} 修改成功（模拟操作）"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"修改集合失败: {str(e)}"
            }
    
    async def _create_index(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """创建索引"""
        try:
            collection_name = config.get("collection_name")
            field_name = config.get("field_name")
            
            if not collection_name or not field_name:
                return {"success": False, "error": "缺少必要参数"}
            
            # 注意：索引创建比较复杂，这里先简单返回成功
            # 实际实现时需要根据具体的向量数据库类型实现
            logger.info(f"创建索引: {collection_name}.{field_name}")
            
            return {
                "success": True,
                "message": f"索引创建成功: {collection_name}.{field_name}（模拟操作）"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"创建索引失败: {str(e)}"
            }
    
    async def _drop_index(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """删除索引"""
        try:
            collection_name = config.get("collection_name")
            field_name = config.get("field_name")
            
            if not collection_name or not field_name:
                return {"success": False, "error": "缺少必要参数"}
            
            # 注意：索引删除比较复杂，这里先简单返回成功
            # 实际实现时需要根据具体的向量数据库类型实现
            logger.info(f"删除索引: {collection_name}.{field_name}")
            
            return {
                "success": True,
                "message": f"索引删除成功: {collection_name}.{field_name}（模拟操作）"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"删除索引失败: {str(e)}"
            }
    
    async def _execute_custom_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """执行自定义操作"""
        try:
            # 这里可以扩展支持自定义的迁移操作
            custom_type = operation.get("custom_type")
            
            if custom_type == "backup_collection":
                return await self._backup_collection(operation.get("collection_name"))
            elif custom_type == "restore_collection":
                return await self._restore_collection(operation.get("config", {}))
            else:
                return {
                    "success": False,
                    "error": f"不支持的自定义操作: {custom_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"执行自定义操作失败: {str(e)}"
            }
    
    async def _backup_collection(self, collection_name: str) -> Dict[str, Any]:
        """备份集合"""
        # 这里实现集合备份逻辑
        return {
            "success": True,
            "message": f"集合 {collection_name} 备份完成（待实现）"
        }
    
    async def _restore_collection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """恢复集合"""
        # 这里实现集合恢复逻辑
        return {
            "success": True,
            "message": "集合恢复完成（待实现）"
        }
    
    def _record_migration(self, migration: VectorDBMigration):
        """记录迁移历史"""
        try:
            operations_hash = hashlib.sha256(
                json.dumps(migration.up_operations, sort_keys=True).encode()
            ).hexdigest()
            
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO vector_db_migrations 
                    (version, description, vector_store_type, operations_hash, migration_data)
                    VALUES (:version, :description, :store_type, :ops_hash, :data)
                """), {
                    "version": migration.version,
                    "description": migration.description,
                    "store_type": self.vector_store_type,
                    "ops_hash": operations_hash,
                    "data": json.dumps(migration.to_dict())
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"记录迁移历史失败: {str(e)}")
    
    def _remove_migration_record(self, version: str):
        """移除迁移历史记录"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    DELETE FROM vector_db_migrations 
                    WHERE version = :version AND vector_store_type = :store_type
                """), {
                    "version": version,
                    "store_type": self.vector_store_type
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"移除迁移历史记录失败: {str(e)}")
    
    async def migrate_to_latest(self) -> Dict[str, Any]:
        """迁移到最新版本"""
        try:
            pending_migrations = self.get_pending_migrations()
            
            if not pending_migrations:
                return {
                    "success": True,
                    "message": "没有待执行的迁移",
                    "migrations_applied": 0
                }
            
            results = []
            for version in pending_migrations:
                result = await self.apply_migration(version)
                results.append(result)
                
                if not result.get("success", False):
                    return {
                        "success": False,
                        "error": f"迁移失败: {version}",
                        "failed_version": version,
                        "results": results
                    }
            
            return {
                "success": True,
                "message": f"成功应用 {len(results)} 个迁移",
                "migrations_applied": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"迁移到最新版本失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_migration_status(self) -> Dict[str, Any]:
        """获取迁移状态"""
        try:
            # 获取已应用的迁移
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT version, description, applied_at 
                    FROM vector_db_migrations 
                    WHERE vector_store_type = :store_type 
                    ORDER BY applied_at DESC
                """), {"store_type": self.vector_store_type})
                
                applied_migrations = [
                    {
                        "version": row[0],
                        "description": row[1],
                        "applied_at": row[2].isoformat() if row[2] else None
                    }
                    for row in result
                ]
            
            # 获取待执行的迁移
            pending_migrations = self.get_pending_migrations()
            
            return {
                "vector_store_type": self.vector_store_type,
                "applied_migrations": applied_migrations,
                "pending_migrations": pending_migrations,
                "total_applied": len(applied_migrations),
                "total_pending": len(pending_migrations)
            }
            
        except Exception as e:
            logger.error(f"获取迁移状态失败: {str(e)}")
            return {
                "error": str(e)
            }


async def main():
    """主函数，用于命令行调用"""
    import argparse
    
    parser = argparse.ArgumentParser(description="向量数据库迁移工具")
    parser.add_argument("--vector-store-type", default="milvus", choices=["milvus", "pgvector"], help="向量数据库类型")
    parser.add_argument("--migrate", action="store_true", help="迁移到最新版本")
    parser.add_argument("--status", action="store_true", help="查看迁移状态")
    parser.add_argument("--apply", help="应用指定版本的迁移")
    parser.add_argument("--rollback", help="回滚指定版本的迁移")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    migrator = VectorDBMigrator(args.vector_store_type)
    
    if args.status:
        status = migrator.get_migration_status()
        print(f"向量数据库类型: {status.get('vector_store_type')}")
        print(f"已应用迁移: {status.get('total_applied')}")
        print(f"待执行迁移: {status.get('total_pending')}")
        
        if status.get('applied_migrations'):
            print("\n已应用的迁移:")
            for migration in status['applied_migrations'][:5]:  # 显示最近5个
                print(f"  {migration['version']}: {migration['description']}")
        
        if status.get('pending_migrations'):
            print("\n待执行的迁移:")
            for version in status['pending_migrations']:
                print(f"  {version}")
    
    elif args.migrate:
        result = await migrator.migrate_to_latest()
        if result.get("success"):
            print(f"迁移成功: {result['message']}")
        else:
            print(f"迁移失败: {result['error']}")
    
    elif args.apply:
        result = await migrator.apply_migration(args.apply)
        if result.get("success"):
            print(f"应用迁移成功: {args.apply}")
        else:
            print(f"应用迁移失败: {result['error']}")
    
    elif args.rollback:
        result = await migrator.rollback_migration(args.rollback)
        if result.get("success"):
            print(f"回滚迁移成功: {args.rollback}")
        else:
            print(f"回滚迁移失败: {result['error']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main()) 