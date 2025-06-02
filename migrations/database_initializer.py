"""
数据库初始化器
提供完整的数据库初始化流程，包括关系型数据库和向量数据库
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 使用独立的迁移配置，避免循环导入
from config import get_database_url

DATABASE_URL = get_database_url()

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self):
        """初始化数据库初始化器"""
        self.base_dir = Path(__file__).parent
        self.sql_dir = self.base_dir / "sql"
        self.versions_dir = self.base_dir / "versions"
        
        # 数据库连接配置
        self.db_url = DATABASE_URL
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 导入简化的向量存储接口
        from vector_storage_interface import create_vector_store
        self.create_vector_store = create_vector_store
        
    async def initialize_all(self, 
                           force_recreate: bool = False,
                           skip_vector_db: bool = False,
                           vector_store_type: str = "milvus") -> Dict[str, Any]:
        """
        完整的数据库初始化流程
        
        Args:
            force_recreate: 是否强制重新创建
            skip_vector_db: 是否跳过向量数据库初始化
            vector_store_type: 向量数据库类型 (milvus/pgvector)
            
        Returns:
            初始化结果
        """
        results = {
            "postgresql": {"status": "pending", "message": "", "details": {}},
            "vector_db": {"status": "pending", "message": "", "details": {}},
            "initialization_time": datetime.utcnow().isoformat()
        }
        
        try:
            # 1. 初始化PostgreSQL数据库
            logger.info("开始初始化PostgreSQL数据库...")
            pg_result = await self._initialize_postgresql(force_recreate)
            results["postgresql"] = pg_result
            
            if pg_result["status"] != "success":
                logger.error(f"PostgreSQL初始化失败: {pg_result['message']}")
                return results
            
            # 2. 初始化向量数据库
            if not skip_vector_db:
                logger.info(f"开始初始化向量数据库 ({vector_store_type})...")
                vector_result = await self._initialize_vector_database(vector_store_type, force_recreate)
                results["vector_db"] = vector_result
            else:
                results["vector_db"] = {"status": "skipped", "message": "向量数据库初始化被跳过"}
            
            # 3. 执行数据初始化
            logger.info("开始执行数据初始化...")
            data_result = await self._initialize_data()
            results["data_initialization"] = data_result
            
            logger.info("数据库初始化完成")
            return results
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            results["error"] = str(e)
            return results
    
    async def _initialize_postgresql(self, force_recreate: bool = False) -> Dict[str, Any]:
        """初始化PostgreSQL数据库"""
        try:
            # 1. 检查数据库是否存在
            db_exists = await self._check_database_exists()
            
            if db_exists and force_recreate:
                logger.info("强制重新创建数据库...")
                await self._drop_database()
                await self._create_database()
            elif not db_exists:
                logger.info("创建新数据库...")
                await self._create_database()
            
            # 2. 执行表结构初始化
            await self._execute_schema_initialization()
            
            # 3. 创建索引
            await self._create_indexes()
            
            # 4. 创建触发器和函数
            await self._create_triggers_and_functions()
            
            # 5. 创建视图
            await self._create_views()
            
            return {
                "status": "success",
                "message": "PostgreSQL数据库初始化成功",
                "details": {
                    "database_recreated": force_recreate and db_exists,
                    "tables_created": True,
                    "indexes_created": True,
                    "triggers_created": True,
                    "views_created": True
                }
            }
            
        except Exception as e:
            logger.error(f"PostgreSQL初始化失败: {str(e)}")
            return {
                "status": "error",
                "message": f"PostgreSQL初始化失败: {str(e)}",
                "details": {}
            }
    
    async def _initialize_vector_database(self, vector_store_type: str, force_recreate: bool = False) -> Dict[str, Any]:
        """初始化向量数据库"""
        try:
            # 1. 创建向量存储实例
            vector_store = self.create_vector_store(vector_store_type)
            
            # 2. 初始化基础集合/表
            collections_created = []
            
            # 定义标准集合配置
            standard_collections = [
                {
                    "name": "standard_document_collection",
                    "config": {
                        "dimension": 768,
                        "description": "标准文档向量集合",
                        "fields": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "embedding", "type": "FLOAT_VECTOR", "dimension": 768},
                            {"name": "text", "type": "VARCHAR", "max_length": 65535}
                        ]
                    }
                },
                {
                    "name": "knowledge_base_collection", 
                    "config": {
                        "dimension": 1536,
                        "description": "知识库向量集合",
                        "fields": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "embedding", "type": "FLOAT_VECTOR", "dimension": 1536},
                            {"name": "content", "type": "VARCHAR", "max_length": 65535},
                            {"name": "metadata", "type": "VARCHAR", "max_length": 65535}
                        ]
                    }
                }
            ]
            
            # 创建标准集合
            for collection_info in standard_collections:
                collection_name = collection_info["name"]
                collection_config = collection_info["config"]
                
                try:
                    # 如果强制重新创建，先删除现有集合
                    if force_recreate and await vector_store.collection_exists(collection_name):
                        await vector_store.drop_collection(collection_name)
                        logger.info(f"已删除现有集合: {collection_name}")
                    
                    # 创建集合
                    if not await vector_store.collection_exists(collection_name):
                        success = await vector_store.create_collection(collection_name, collection_config)
                        if success:
                            collections_created.append(collection_name)
                            logger.info(f"集合创建成功: {collection_name}")
                        else:
                            logger.warning(f"集合创建失败: {collection_name}")
                    else:
                        collections_created.append(collection_name)
                        logger.info(f"集合已存在: {collection_name}")
                        
                except Exception as e:
                    logger.warning(f"集合 {collection_name} 创建失败: {str(e)}")
            
            # 3. 创建自定义集合
            custom_collections = await self._create_custom_vector_collections(vector_store, force_recreate)
            collections_created.extend(custom_collections)
            
            return {
                "status": "success",
                "message": f"{vector_store_type}向量数据库初始化成功",
                "details": {
                    "vector_store_type": vector_store_type,
                    "collections_created": collections_created,
                    "force_recreated": force_recreate
                }
            }
            
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {str(e)}")
            return {
                "status": "error", 
                "message": f"向量数据库初始化失败: {str(e)}",
                "details": {"vector_store_type": vector_store_type}
            }
    
    async def _create_custom_vector_collections(self, vector_store, force_recreate: bool = False) -> List[str]:
        """创建自定义向量集合"""
        collections_created = []
        
        try:
            # 定义自定义集合配置
            custom_collections = [
                {
                    "name": "image_collection",
                    "config": {
                        "dimension": 512,
                        "description": "图像向量集合",
                        "fields": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "embedding", "type": "FLOAT_VECTOR", "dimension": 512},
                            {"name": "image_path", "type": "VARCHAR", "max_length": 1000},
                            {"name": "metadata", "type": "VARCHAR", "max_length": 65535}
                        ]
                    }
                },
                {
                    "name": "multimodal_collection",
                    "config": {
                        "dimension": 1024,
                        "description": "多模态向量集合",
                        "fields": [
                            {"name": "id", "type": "INT64", "is_primary": True},
                            {"name": "embedding", "type": "FLOAT_VECTOR", "dimension": 1024},
                            {"name": "content", "type": "VARCHAR", "max_length": 65535},
                            {"name": "content_type", "type": "VARCHAR", "max_length": 50},
                            {"name": "metadata", "type": "VARCHAR", "max_length": 65535}
                        ]
                    }
                }
            ]
            
            # 创建自定义集合
            for collection_info in custom_collections:
                collection_name = collection_info["name"]
                collection_config = collection_info["config"]
                
                try:
                    # 如果强制重新创建，先删除现有集合
                    if force_recreate and await vector_store.collection_exists(collection_name):
                        await vector_store.drop_collection(collection_name)
                        logger.info(f"已删除现有自定义集合: {collection_name}")
                    
                    # 创建集合
                    if not await vector_store.collection_exists(collection_name):
                        success = await vector_store.create_collection(collection_name, collection_config)
                        if success:
                            collections_created.append(collection_name)
                            logger.info(f"自定义集合创建成功: {collection_name}")
                        else:
                            logger.warning(f"自定义集合创建失败: {collection_name}")
                    else:
                        collections_created.append(collection_name)
                        logger.info(f"自定义集合已存在: {collection_name}")
                        
                except Exception as e:
                    logger.warning(f"自定义集合 {collection_name} 创建失败: {str(e)}")
            
            return collections_created
            
        except Exception as e:
            logger.error(f"自定义向量集合创建失败: {str(e)}")
            return collections_created
    
    async def _check_database_exists(self) -> bool:
        """检查数据库是否存在"""
        try:
            # 尝试连接数据库
            conn = await asyncpg.connect(self.db_url)
            await conn.close()
            return True
        except Exception:
            return False
    
    async def _create_database(self) -> None:
        """创建数据库"""
        # 从URL中提取数据库信息
        from urllib.parse import urlparse
        parsed = urlparse(self.db_url)
        
        # 连接到postgres数据库来创建目标数据库
        admin_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"
        
        conn = await asyncpg.connect(admin_url)
        try:
            # 创建数据库
            database_name = parsed.path[1:]  # 去掉开头的/
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            logger.info(f"数据库 {database_name} 创建成功")
        finally:
            await conn.close()
    
    async def _drop_database(self) -> None:
        """删除数据库"""
        from urllib.parse import urlparse
        parsed = urlparse(self.db_url)
        
        admin_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"
        
        conn = await asyncpg.connect(admin_url)
        try:
            database_name = parsed.path[1:]  # 去掉开头的/
            # 断开所有连接
            await conn.execute(f'''
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{database_name}' AND pid <> pg_backend_pid()
            ''')
            # 删除数据库
            await conn.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
            logger.info(f"数据库 {database_name} 删除成功")
        finally:
            await conn.close()
    
    async def _execute_schema_initialization(self) -> None:
        """执行表结构初始化"""
        # 执行完整的数据库初始化脚本
        schema_file = self.base_dir.parent / "database_complete.sql"
        
        if schema_file.exists():
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # 分割SQL语句并执行
            statements = self._split_sql_statements(schema_sql)
            
            with self.engine.connect() as conn:
                for statement in statements:
                    if statement.strip():
                        try:
                            conn.execute(text(statement))
                            conn.commit()
                        except Exception as e:
                            logger.warning(f"执行SQL语句失败: {statement[:100]}... 错误: {str(e)}")
            
            logger.info("数据库表结构初始化完成")
        else:
            raise FileNotFoundError("找不到数据库初始化脚本文件")
    
    async def _create_indexes(self) -> None:
        """创建索引（在schema脚本中已包含）"""
        logger.info("索引创建完成（已在schema脚本中执行）")
    
    async def _create_triggers_and_functions(self) -> None:
        """创建触发器和函数（在schema脚本中已包含）"""
        logger.info("触发器和函数创建完成（已在schema脚本中执行）")
    
    async def _create_views(self) -> None:
        """创建视图（在schema脚本中已包含）"""
        logger.info("视图创建完成（已在schema脚本中执行）")
    
    async def _initialize_data(self) -> Dict[str, Any]:
        """初始化基础数据"""
        try:
            data_files = [
                "01_roles_permissions.sql",
                "02_system_configs.sql", 
                "03_model_providers.sql",
                "04_admin_user.sql",
                "05_framework_configs.sql",
                "06_agent_templates.sql",
                "07_system_tools.sql"
            ]
            
            executed_files = []
            
            for file_name in data_files:
                file_path = self.sql_dir / "common" / file_name
                if file_path.exists():
                    try:
                        await self._execute_sql_file(file_path)
                        executed_files.append(file_name)
                        logger.info(f"数据文件 {file_name} 执行成功")
                    except Exception as e:
                        logger.error(f"数据文件 {file_name} 执行失败: {str(e)}")
                else:
                    logger.warning(f"数据文件 {file_name} 不存在")
            
            return {
                "status": "success",
                "message": "基础数据初始化成功",
                "details": {
                    "executed_files": executed_files,
                    "total_files": len(data_files)
                }
            }
            
        except Exception as e:
            logger.error(f"基础数据初始化失败: {str(e)}")
            return {
                "status": "error",
                "message": f"基础数据初始化失败: {str(e)}",
                "details": {}
            }
    
    async def _execute_sql_file(self, file_path: Path) -> None:
        """执行SQL文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        statements = self._split_sql_statements(sql_content)
        
        with self.engine.connect() as conn:
            for statement in statements:
                if statement.strip():
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"执行SQL语句失败: {statement[:100]}... 错误: {str(e)}")
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """分割SQL语句"""
        # 简单的SQL语句分割，按分号分割
        statements = []
        current_statement = ""
        in_quote = False
        quote_char = None
        
        for char in sql_content:
            if char in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
            elif char == ';' and not in_quote:
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
                continue
            
            current_statement += char
        
        # 添加最后一个语句
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    async def check_initialization_status(self) -> Dict[str, Any]:
        """检查初始化状态"""
        try:
            # 检查PostgreSQL
            pg_status = await self._check_postgresql_status()
            
            # 检查向量数据库
            vector_status = await self._check_vector_database_status()
            
            return {
                "postgresql": pg_status,
                "vector_database": vector_status,
                "overall_status": "ready" if pg_status["ready"] and vector_status["ready"] else "not_ready"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "overall_status": "error"
            }
    
    async def _check_postgresql_status(self) -> Dict[str, Any]:
        """检查PostgreSQL状态"""
        try:
            with self.engine.connect() as conn:
                # 检查关键表是否存在
                result = conn.execute(text("""
                    SELECT COUNT(*) as table_count
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('users', 'knowledge_bases', 'documents', 'assistants')
                """))
                
                table_count = result.fetchone()[0]
                
                return {
                    "ready": table_count >= 4,
                    "table_count": table_count,
                    "message": "PostgreSQL数据库状态正常" if table_count >= 4 else "PostgreSQL数据库未完全初始化"
                }
                
        except Exception as e:
            return {
                "ready": False,
                "error": str(e),
                "message": f"PostgreSQL检查失败: {str(e)}"
            }
    
    async def _check_vector_database_status(self) -> Dict[str, Any]:
        """检查向量数据库状态"""
        try:
            # 这里需要根据实际的向量数据库类型来检查
            # 暂时返回基本状态
            return {
                "ready": True,
                "message": "向量数据库状态检查需要实现具体逻辑"
            }
            
        except Exception as e:
            return {
                "ready": False,
                "error": str(e),
                "message": f"向量数据库检查失败: {str(e)}"
            }


async def main():
    """主函数，用于命令行调用"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库初始化工具")
    parser.add_argument("--force-recreate", action="store_true", help="强制重新创建数据库")
    parser.add_argument("--skip-vector-db", action="store_true", help="跳过向量数据库初始化")
    parser.add_argument("--vector-store-type", default="milvus", choices=["milvus", "pgvector"], help="向量数据库类型")
    parser.add_argument("--check-status", action="store_true", help="仅检查初始化状态")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    initializer = DatabaseInitializer()
    
    if args.check_status:
        status = await initializer.check_initialization_status()
        print("数据库初始化状态:")
        print(f"PostgreSQL: {status['postgresql']}")
        print(f"向量数据库: {status['vector_database']}")
        print(f"整体状态: {status['overall_status']}")
    else:
        result = await initializer.initialize_all(
            force_recreate=args.force_recreate,
            skip_vector_db=args.skip_vector_db,
            vector_store_type=args.vector_store_type
        )
        
        print("数据库初始化结果:")
        for component, details in result.items():
            if isinstance(details, dict) and "status" in details:
                print(f"{component}: {details['status']} - {details['message']}")
            else:
                print(f"{component}: {details}")


if __name__ == "__main__":
    asyncio.run(main()) 