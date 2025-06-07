#!/usr/bin/env python3
"""
简化版数据库迁移执行器
避免循环导入，直接使用数据库连接执行智能内容处理表创建
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import List
from datetime import datetime
from pathlib import Path
import asyncpg

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleMigrationExecutor:
    """简化版数据库迁移执行器"""
    
    def __init__(self):
        # 从环境变量获取数据库连接信息
        self.db_host = os.getenv('DB_HOST', '167.71.85.231')
        self.db_port = int(os.getenv('DB_PORT', '5432'))
        self.db_name = os.getenv('DB_NAME', 'zzdsj')
        self.db_user = os.getenv('DB_USER', 'zzdsj')
        self.db_password = os.getenv('DB_PASSWORD', 'zzdsj')
        
        # 项目根目录
        current_dir = Path(__file__).parent
        self.project_root = current_dir.parent.parent
        self.migrations_dir = self.project_root / "migrations" / "sql" / "common"
        
    async def get_connection(self):
        """获取数据库连接"""
        try:
            connection = await asyncpg.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            return connection
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise
    
    async def execute_sql_file(self, file_path: Path) -> bool:
        """
        执行SQL迁移文件
        
        Args:
            file_path: SQL文件路径
            
        Returns:
            bool: 执行是否成功
        """
        try:
            logger.info(f"🚀 开始执行SQL文件: {file_path}")
            
            # 读取SQL文件内容
            if not file_path.exists():
                logger.error(f"❌ SQL文件不存在: {file_path}")
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            if not sql_content.strip():
                logger.warning(f"⚠️ SQL文件为空: {file_path}")
                return True
            
            # 获取数据库连接
            connection = await self.get_connection()
            
            try:
                # 分割SQL语句并执行
                statements = self._split_sql_statements(sql_content)
                
                logger.info(f"📝 准备执行 {len(statements)} 个SQL语句")
                
                for i, statement in enumerate(statements):
                    if statement.strip():
                        try:
                            # 显示正在执行的语句类型
                            statement_type = self._get_statement_type(statement)
                            logger.info(f"⚡ 执行 {statement_type} ({i+1}/{len(statements)})")
                            
                            await connection.execute(statement)
                            
                        except Exception as e:
                            logger.error(f"❌ 执行SQL语句失败 ({i+1}/{len(statements)}): {e}")
                            logger.error(f"失败的语句: {statement[:200]}...")
                            return False
                
                logger.info(f"✅ SQL文件执行成功: {file_path}")
                return True
                
            finally:
                await connection.close()
            
        except Exception as e:
            logger.error(f"❌ 执行SQL文件失败: {file_path}, 错误: {e}")
            return False
    
    def _get_statement_type(self, statement: str) -> str:
        """获取SQL语句类型"""
        statement = statement.strip().upper()
        if statement.startswith('CREATE TABLE'):
            return "创建表"
        elif statement.startswith('CREATE INDEX'):
            return "创建索引"
        elif statement.startswith('CREATE TRIGGER'):
            return "创建触发器"
        elif statement.startswith('INSERT'):
            return "插入数据"
        elif statement.startswith('SELECT'):
            return "查询验证"
        else:
            return "执行语句"
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """
        分割SQL内容为独立的语句
        
        Args:
            sql_content: SQL文件内容
            
        Returns:
            List[str]: SQL语句列表
        """
        # 移除单行注释
        lines = []
        for line in sql_content.split('\n'):
            # 保留空行和不是注释的行
            if not line.strip().startswith('--'):
                lines.append(line)
        
        # 重新组合
        content = '\n'.join(lines)
        
        # 按分号分割，但要考虑函数定义等复杂情况
        statements = []
        current_statement = ""
        in_function = False
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # 检查是否在函数定义中
            if 'CREATE FUNCTION' in line.upper() or 'CREATE OR REPLACE FUNCTION' in line.upper():
                in_function = True
            elif line.upper().startswith('$$') or line.upper().endswith('$$'):
                if in_function:
                    in_function = False
            
            current_statement += line + '\n'
            
            # 如果遇到分号且不在函数中，则为一个完整语句
            if line.endswith(';') and not in_function:
                statements.append(current_statement.strip())
                current_statement = ""
        
        # 处理最后一个语句
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return [stmt for stmt in statements if stmt.strip()]
    
    async def execute_intelligent_content_migration(self) -> bool:
        """
        执行智能内容处理功能的数据库迁移
        
        Returns:
            bool: 迁移是否成功
        """
        migration_file = self.migrations_dir / "04_intelligent_content_processing_tables.sql"
        
        logger.info("=" * 80)
        logger.info("🎯 智能内容处理功能数据库迁移")
        logger.info("=" * 80)
        logger.info(f"📁 迁移文件: {migration_file}")
        logger.info(f"🗄️ 数据库连接: {self.db_host}:{self.db_port}/{self.db_name}")
        
        # 检查文件是否存在
        if not migration_file.exists():
            logger.error(f"❌ 迁移文件不存在: {migration_file}")
            return False
        
        # 显示文件大小和创建时间
        file_stat = migration_file.stat()
        logger.info(f"📊 文件大小: {file_stat.st_size} 字节")
        logger.info(f"⏰ 文件修改时间: {datetime.fromtimestamp(file_stat.st_mtime)}")
        
        success = await self.execute_sql_file(migration_file)
        
        if success:
            logger.info("🎉 智能内容处理功能数据库迁移执行成功!")
        else:
            logger.error("💥 智能内容处理功能数据库迁移执行失败!")
            
        return success
    
    async def verify_tables_created(self) -> bool:
        """
        验证智能内容处理表是否成功创建
        
        Returns:
            bool: 验证是否通过
        """
        expected_tables = [
            'web_crawl_results',
            'content_processing_tasks',
            'content_quality_analysis',
            'crawler_scheduling_logs',
            'policy_portal_configs',
            'markitdown_processing_records'
        ]
        
        logger.info("🔍 验证数据库表创建状态...")
        
        try:
            connection = await self.get_connection()
            
            try:
                # 查询已创建的表
                result = await connection.fetch("""
                    SELECT tablename, schemaname
                    FROM pg_tables 
                    WHERE tablename = ANY($1)
                    AND schemaname = 'public'
                    ORDER BY tablename
                """, expected_tables)
                
                created_tables = [row['tablename'] for row in result]
                
                logger.info(f"📋 预期创建的表: {expected_tables}")
                logger.info(f"✅ 实际创建的表: {created_tables}")
                
                missing_tables = set(expected_tables) - set(created_tables)
                
                if missing_tables:
                    logger.error(f"❌ 以下表未成功创建: {missing_tables}")
                    return False
                else:
                    logger.info("🎊 所有预期的表都已成功创建!")
                    
                    # 检查每个表的记录数
                    for table in created_tables:
                        count_result = await connection.fetchval(f"SELECT COUNT(*) FROM {table}")
                        logger.info(f"📊 {table}: {count_result} 条记录")
                    
                    return True
                    
            finally:
                await connection.close()
                
        except Exception as e:
            logger.error(f"❌ 验证表创建失败: {e}")
            return False
    
    async def verify_indexes_created(self) -> bool:
        """
        验证索引是否成功创建
        
        Returns:
            bool: 验证是否通过
        """
        logger.info("🔍 验证数据库索引创建状态...")
        
        try:
            connection = await self.get_connection()
            
            try:
                # 查询与智能内容处理相关的索引
                result = await connection.fetch("""
                    SELECT indexname, tablename
                    FROM pg_indexes 
                    WHERE tablename IN (
                        'web_crawl_results',
                        'content_processing_tasks',
                        'content_quality_analysis',
                        'crawler_scheduling_logs',
                        'policy_portal_configs',
                        'markitdown_processing_records'
                    )
                    AND schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
                
                indexes_by_table = {}
                for row in result:
                    table = row['tablename']
                    index = row['indexname']
                    if table not in indexes_by_table:
                        indexes_by_table[table] = []
                    indexes_by_table[table].append(index)
                
                total_indexes = sum(len(indexes) for indexes in indexes_by_table.values())
                logger.info(f"📊 共创建了 {total_indexes} 个索引")
                
                for table, indexes in indexes_by_table.items():
                    logger.info(f"🗂️ {table}: {len(indexes)} 个索引")
                    for index in indexes:
                        logger.info(f"   └── {index}")
                
                return True
                
            finally:
                await connection.close()
                
        except Exception as e:
            logger.error(f"❌ 验证索引创建失败: {e}")
            return False
    
    async def test_portal_configs(self) -> bool:
        """
        测试政策门户配置数据
        
        Returns:
            bool: 测试是否通过
        """
        logger.info("🔍 测试政策门户配置数据...")
        
        try:
            connection = await self.get_connection()
            
            try:
                # 查询政策门户配置
                result = await connection.fetch("""
                    SELECT region_name, region_level, portal_name, is_active, priority
                    FROM policy_portal_configs
                    ORDER BY priority
                """)
                
                logger.info(f"📊 发现 {len(result)} 个政策门户配置:")
                
                for row in result:
                    status = "🟢 启用" if row['is_active'] else "🔴 禁用"
                    logger.info(f"  🏛️ {row['region_name']} ({row['region_level']}) - {row['portal_name']} - 优先级:{row['priority']} - {status}")
                
                return len(result) > 0
                
            finally:
                await connection.close()
                
        except Exception as e:
            logger.error(f"❌ 测试政策门户配置失败: {e}")
            return False

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='简化版智能内容处理数据库迁移脚本')
    parser.add_argument(
        '--verify-only', 
        action='store_true', 
        help='仅验证表和索引创建，不执行迁移'
    )
    parser.add_argument(
        '--test-configs', 
        action='store_true', 
        help='测试政策门户配置数据'
    )
    
    args = parser.parse_args()
    
    executor = SimpleMigrationExecutor()
    
    try:
        if args.verify_only:
            # 仅验证
            logger.info("🔍 开始验证模式...")
            tables_ok = await executor.verify_tables_created()
            indexes_ok = await executor.verify_indexes_created()
            success = tables_ok and indexes_ok
            sys.exit(0 if success else 1)
        
        if args.test_configs:
            # 测试配置
            logger.info("🧪 开始测试政策门户配置...")
            success = await executor.test_portal_configs()
            sys.exit(0 if success else 1)
        
        # 执行迁移
        logger.info("🚀 开始执行智能内容处理数据库迁移...")
        migration_success = await executor.execute_intelligent_content_migration()
        
        if migration_success:
            # 验证迁移结果
            logger.info("\n" + "="*80)
            logger.info("🔍 验证迁移结果...")
            logger.info("="*80)
            
            tables_ok = await executor.verify_tables_created()
            indexes_ok = await executor.verify_indexes_created()
            configs_ok = await executor.test_portal_configs()
            
            if tables_ok and indexes_ok and configs_ok:
                logger.info("\n" + "🎉" * 20)
                logger.info("✅ 智能内容处理功能数据库迁移完全成功!")
                logger.info("🎉" * 20)
                sys.exit(0)
            else:
                logger.error("\n" + "❌ 迁移验证失败，请检查上述错误信息")
                sys.exit(1)
        else:
            logger.error("\n" + "💥 迁移执行失败!")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 