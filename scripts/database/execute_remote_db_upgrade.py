#!/usr/bin/env python3
"""
基于远程数据库连接的增强版数据库升级脚本
使用昨天的远程PostgreSQL连接配置执行数据库表更新
确保数据库结构完全符合增强版要求
"""

import os
import sys
import time
import logging
import psycopg2
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 远程数据库连接配置（基于昨天的测试脚本）
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RemoteDatabaseUpgrader:
    """远程数据库增强版升级器"""
    
    def __init__(self):
        """初始化升级器"""
        self.db_config = REMOTE_DB_CONFIG
        self.upgrade_results = []
        self.errors = []
        self.start_time = datetime.now()
        
    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            **self.db_config,
            cursor_factory=RealDictCursor
        )
    
    def log_operation(self, operation: str, success: bool, details: str = "", duration_ms: int = 0):
        """记录操作结果"""
        result = {
            "operation": operation,
            "success": success,
            "details": details,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }
        self.upgrade_results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} {operation}")
        if details:
            print(f"    └─ {details}")
        if duration_ms > 0:
            print(f"    ⏱️ 耗时: {duration_ms}ms")
            
        if not success:
            self.errors.append(f"{operation}: {details}")
    
    def test_remote_database_connection(self) -> bool:
        """测试远程数据库连接"""
        print("\n🔗 测试远程数据库连接...")
        print(f"📍 目标服务器: {self.db_config['host']}:{self.db_config['port']}")
        print(f"👤 用户: {self.db_config['user']}")
        print(f"🗄️ 数据库: {self.db_config['database']}")
        
        try:
            start_time = time.time()
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 获取数据库版本信息
            cursor.execute("SELECT version()")
            version = cursor.fetchone()['version']
            
            # 获取数据库基本信息
            cursor.execute("SELECT current_database(), current_user, current_timestamp")
            db_info = cursor.fetchone()
            
            # 检查数据库权限
            cursor.execute("""
                SELECT datname, has_database_privilege(current_user, datname, 'CREATE') as can_create
                FROM pg_database 
                WHERE datname = current_database()
            """)
            perm_info = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.log_operation(
                "远程数据库连接测试", True,
                f"PostgreSQL版本: {version.split(',')[0]}", duration_ms
            )
            
            print(f"📊 连接信息:")
            print(f"   数据库: {db_info['current_database']}")
            print(f"   用户: {db_info['current_user']}")
            print(f"   时间: {db_info['current_timestamp']}")
            print(f"   CREATE权限: {'✅' if perm_info['can_create'] else '❌'}")
            
            if not perm_info['can_create']:
                self.log_operation(
                    "数据库权限检查", False,
                    "用户缺少CREATE权限，可能影响表创建"
                )
                return False
            
            return True
            
        except Exception as e:
            self.log_operation(
                "远程数据库连接测试", False,
                f"连接失败: {str(e)}"
            )
            return False
    
    def check_existing_remote_tables(self) -> Dict[str, bool]:
        """检查远程数据库的现有表结构"""
        print("\n📊 检查远程数据库现有表结构...")
        
        enhanced_tables = {
            'document_registry_enhanced': False,
            'document_chunks': False,
            'document_vectors_enhanced': False,
            'document_es_shards': False,
            'document_processing_history': False
        }
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 查询所有现有表
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            existing_tables = [row['tablename'] for row in cursor.fetchall()]
            
            print(f"📋 发现 {len(existing_tables)} 个现有表:")
            for table in existing_tables:
                print(f"   • {table}")
            
            # 检查增强版表是否存在
            for table_name in enhanced_tables.keys():
                enhanced_tables[table_name] = table_name in existing_tables
                
                status_icon = "✅" if enhanced_tables[table_name] else "❌"
                print(f"   {status_icon} {table_name}: {'存在' if enhanced_tables[table_name] else '不存在'}")
            
            # 统计现有数据
            total_records = 0
            for table in existing_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()['count']
                    total_records += count
                    if count > 0:
                        print(f"      └─ {count} 条记录")
                except Exception as e:
                    print(f"      └─ 查询失败: {str(e)[:30]}...")
            
            cursor.close()
            conn.close()
            
            existing_count = sum(enhanced_tables.values())
            total_count = len(enhanced_tables)
            
            self.log_operation(
                "远程表结构检查", True,
                f"增强版表: {existing_count}/{total_count} 存在, 总记录数: {total_records}"
            )
            
            return enhanced_tables
            
        except Exception as e:
            self.log_operation(
                "远程表结构检查", False,
                f"检查失败: {str(e)}"
            )
            return enhanced_tables
    
    def create_enhanced_document_registry(self) -> bool:
        """创建增强版文档注册表"""
        print("\n📄 创建增强版文档注册表...")
        
        sql = """
        CREATE TABLE IF NOT EXISTS document_registry_enhanced (
            file_id VARCHAR(36) PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            content_type VARCHAR(100),
            file_size BIGINT NOT NULL,
            file_hash VARCHAR(64) NOT NULL,
            storage_backend VARCHAR(50) NOT NULL,
            storage_path VARCHAR(500),
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            kb_id VARCHAR(36),
            doc_id VARCHAR(36),
            user_id VARCHAR(36),
            metadata TEXT,
            status VARCHAR(20) DEFAULT 'uploaded',
            processing_status VARCHAR(20) DEFAULT 'pending',
            chunk_count INTEGER DEFAULT 0,
            vector_count INTEGER DEFAULT 0,
            es_doc_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(file_hash)
        );
        """
        
        return self._execute_sql("创建文档注册表", sql)
    
    def create_document_chunks_table(self) -> bool:
        """创建文档切片表"""
        print("\n🔪 创建文档切片表...")
        
        sql = """
        CREATE TABLE IF NOT EXISTS document_chunks (
            chunk_id VARCHAR(36) PRIMARY KEY,
            file_id VARCHAR(36),
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT,
            chunk_size INTEGER,
            chunk_hash VARCHAR(64),
            chunk_metadata TEXT,
            processing_status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(file_id, chunk_index)
        );
        """
        
        return self._execute_sql("创建文档切片表", sql)
    
    def create_vectors_enhanced_table(self) -> bool:
        """创建增强版向量关联表"""
        print("\n🧠 创建增强版向量关联表...")
        
        sql = """
        CREATE TABLE IF NOT EXISTS document_vectors_enhanced (
            id SERIAL PRIMARY KEY,
            file_id VARCHAR(36),
            chunk_id VARCHAR(36),
            vector_id VARCHAR(100) NOT NULL,
            vector_collection VARCHAR(100),
            vector_index VARCHAR(100),
            embedding_model VARCHAR(100),
            embedding_dimension INTEGER,
            vector_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(file_id, chunk_id, vector_id)
        );
        """
        
        return self._execute_sql("创建向量关联表", sql)
    
    def create_es_shards_table(self) -> bool:
        """创建ES分片关联表"""
        print("\n🔍 创建ES分片关联表...")
        
        sql = """
        CREATE TABLE IF NOT EXISTS document_es_shards (
            id SERIAL PRIMARY KEY,
            file_id VARCHAR(36),
            chunk_id VARCHAR(36),
            es_index VARCHAR(100) NOT NULL,
            es_doc_id VARCHAR(100) NOT NULL,
            es_shard_id VARCHAR(50),
            es_routing VARCHAR(100),
            es_doc_type VARCHAR(50),
            es_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(es_index, es_doc_id)
        );
        """
        
        return self._execute_sql("创建ES分片关联表", sql)
    
    def create_processing_history_table(self) -> bool:
        """创建处理历史表"""
        print("\n📈 创建处理历史表...")
        
        sql = """
        CREATE TABLE IF NOT EXISTS document_processing_history (
            id SERIAL PRIMARY KEY,
            file_id VARCHAR(36),
            operation_type VARCHAR(50) NOT NULL,
            operation_status VARCHAR(20) NOT NULL,
            operation_details TEXT,
            error_message TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            duration_ms INTEGER,
            operated_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        return self._execute_sql("创建处理历史表", sql)
    
    def add_foreign_key_constraints(self) -> bool:
        """添加外键约束"""
        print("\n🔗 添加外键约束...")
        
        constraints = [
            """
            ALTER TABLE document_chunks 
            ADD CONSTRAINT fk_chunks_file_id 
            FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) 
            ON DELETE CASCADE
            """,
            """
            ALTER TABLE document_vectors_enhanced 
            ADD CONSTRAINT fk_vectors_file_id 
            FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) 
            ON DELETE CASCADE
            """,
            """
            ALTER TABLE document_vectors_enhanced 
            ADD CONSTRAINT fk_vectors_chunk_id 
            FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id) 
            ON DELETE CASCADE
            """,
            """
            ALTER TABLE document_es_shards 
            ADD CONSTRAINT fk_es_file_id 
            FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) 
            ON DELETE CASCADE
            """,
            """
            ALTER TABLE document_es_shards 
            ADD CONSTRAINT fk_es_chunk_id 
            FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id) 
            ON DELETE CASCADE
            """,
            """
            ALTER TABLE document_processing_history 
            ADD CONSTRAINT fk_history_file_id 
            FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) 
            ON DELETE CASCADE
            """
        ]
        
        added_constraints = 0
        for constraint_sql in constraints:
            try:
                if self._execute_sql("添加外键约束", constraint_sql, log_details=False):
                    added_constraints += 1
            except Exception as e:
                # 外键约束可能已经存在，忽略错误
                logger.debug(f"添加外键约束时可能遇到重复: {str(e)}")
        
        self.log_operation(
            "添加外键约束", True,
            f"成功添加 {added_constraints}/{len(constraints)} 个约束"
        )
        
        return True
    
    def create_enhanced_indexes(self) -> bool:
        """创建增强版索引"""
        print("\n🏗️ 创建增强版索引...")
        
        indexes = [
            # 文档注册表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_filename ON document_registry_enhanced(filename)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_hash ON document_registry_enhanced(file_hash)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_kb_id ON document_registry_enhanced(kb_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_doc_id ON document_registry_enhanced(doc_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_user_id ON document_registry_enhanced(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_status ON document_registry_enhanced(status)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_proc_status ON document_registry_enhanced(processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_upload_time ON document_registry_enhanced(upload_time)",
            
            # 文档切片表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_file_id ON document_chunks(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_index ON document_chunks(chunk_index)",
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_hash ON document_chunks(chunk_hash)",
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_status ON document_chunks(processing_status)",
            
            # 向量数据表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_file_id ON document_vectors_enhanced(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_chunk_id ON document_vectors_enhanced(chunk_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_vector_id ON document_vectors_enhanced(vector_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_collection ON document_vectors_enhanced(vector_collection)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_index ON document_vectors_enhanced(vector_index)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_model ON document_vectors_enhanced(embedding_model)",
            
            # ES分片表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_es_file_id ON document_es_shards(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_chunk_id ON document_es_shards(chunk_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_index ON document_es_shards(es_index)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_doc_id ON document_es_shards(es_doc_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_shard_id ON document_es_shards(es_shard_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_routing ON document_es_shards(es_routing)",
            
            # 处理历史表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_file_id ON document_processing_history(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_op_type ON document_processing_history(operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_status ON document_processing_history(operation_status)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_started ON document_processing_history(started_at)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_user ON document_processing_history(operated_by)"
        ]
        
        successful_indexes = 0
        for index_sql in indexes:
            try:
                if self._execute_sql(f"索引创建", index_sql, log_details=False):
                    successful_indexes += 1
            except Exception as e:
                logger.warning(f"创建索引失败: {index_sql} - {str(e)}")
        
        self.log_operation(
            "创建增强版索引", True,
            f"成功创建 {successful_indexes}/{len(indexes)} 个索引"
        )
        
        return successful_indexes == len(indexes)
    
    def create_demo_data(self) -> bool:
        """创建演示数据"""
        print("\n🎲 创建演示数据...")
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 1. 创建测试文档
            demo_file_id = "demo_file_" + str(int(time.time()))
            cursor.execute("""
                INSERT INTO document_registry_enhanced 
                (file_id, filename, content_type, file_size, file_hash, storage_backend, 
                 storage_path, kb_id, doc_id, user_id, chunk_count, vector_count, es_doc_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_hash) DO NOTHING
            """, (
                demo_file_id, "demo_document.pdf", "application/pdf", 1024000, 
                "demo_hash_" + str(int(time.time())), "minio", "/demo/path/demo_document.pdf",
                "demo_kb_001", "demo_doc_001", "demo_user_001", 3, 3, 3
            ))
            
            # 2. 创建文档切片
            for i in range(3):
                chunk_id = f"demo_chunk_{i+1}_{int(time.time())}"
                cursor.execute("""
                    INSERT INTO document_chunks 
                    (chunk_id, file_id, chunk_index, chunk_text, chunk_size, chunk_hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    chunk_id, demo_file_id, i, f"这是演示文档的第{i+1}个切片内容...", 
                    200 + i*50, f"chunk_hash_{i+1}_{int(time.time())}"
                ))
                
                # 3. 创建向量关联
                cursor.execute("""
                    INSERT INTO document_vectors_enhanced 
                    (file_id, chunk_id, vector_id, vector_collection, embedding_model, embedding_dimension)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    demo_file_id, chunk_id, f"vector_{i+1}_{int(time.time())}", 
                    "demo_collection", "text-embedding-ada-002", 1536
                ))
                
                # 4. 创建ES分片关联
                cursor.execute("""
                    INSERT INTO document_es_shards 
                    (file_id, chunk_id, es_index, es_doc_id, es_shard_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    demo_file_id, chunk_id, "demo_index", f"es_doc_{i+1}_{int(time.time())}", 
                    f"shard_{i+1}"
                ))
            
            # 5. 创建处理历史
            cursor.execute("""
                INSERT INTO document_processing_history 
                (file_id, operation_type, operation_status, operation_details, 
                 started_at, completed_at, duration_ms, operated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                demo_file_id, "demo_creation", "completed", 
                "演示数据创建完成", datetime.now(), datetime.now(), 100, "system"
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_operation(
                "创建演示数据", True,
                f"文档ID: {demo_file_id}, 包含3个切片、3个向量、3个ES分片"
            )
            
            return True
            
        except Exception as e:
            self.log_operation(
                "创建演示数据", False,
                f"创建失败: {str(e)}"
            )
            return False
    
    def verify_remote_upgrade_results(self) -> bool:
        """验证远程升级结果"""
        print("\n🔍 验证远程升级结果...")
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 验证表结构
            tables_to_check = [
                'document_registry_enhanced',
                'document_chunks',
                'document_vectors_enhanced',
                'document_es_shards',
                'document_processing_history'
            ]
            
            verification_results = {}
            
            for table in tables_to_check:
                # 检查表是否存在
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                """, (table,))
                
                exists = cursor.fetchone()['exists']
                
                if exists:
                    # 统计记录数量
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()['count']
                    verification_results[table] = count
                    print(f"   ✅ {table}: {count} 条记录")
                else:
                    verification_results[table] = -1
                    print(f"   ❌ {table}: 不存在")
            
            # 检查索引
            cursor.execute("""
                SELECT count(*) as index_count
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND (indexname LIKE 'idx_doc_%')
            """)
            index_count = cursor.fetchone()['index_count']
            print(f"   🏗️ 增强版索引: {index_count} 个")
            
            cursor.close()
            conn.close()
            
            # 检查是否所有表都存在
            all_exist = all(count >= 0 for count in verification_results.values())
            
            self.log_operation(
                "远程升级结果验证", all_exist,
                f"表存在状态: {sum(1 for c in verification_results.values() if c >= 0)}/{len(tables_to_check)}, 索引: {index_count}"
            )
            
            return all_exist
            
        except Exception as e:
            self.log_operation(
                "远程升级结果验证", False,
                f"验证失败: {str(e)}"
            )
            return False
    
    def _execute_sql(self, operation_name: str, sql: str, log_details: bool = True) -> bool:
        """执行SQL语句"""
        try:
            start_time = time.time()
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(sql)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if log_details:
                self.log_operation(operation_name, True, "执行成功", duration_ms)
            
            return True
            
        except Exception as e:
            if log_details:
                self.log_operation(operation_name, False, f"执行失败: {str(e)}")
            return False
    
    def execute_remote_full_upgrade(self) -> bool:
        """执行完整的远程数据库升级"""
        print("🚀 开始执行远程数据库增强版升级...")
        print(f"🌍 目标服务器: {self.db_config['host']}:{self.db_config['port']}")
        print("="*80)
        
        upgrade_steps = [
            ("远程数据库连接测试", self.test_remote_database_connection),
            ("检查远程现有表结构", lambda: self.check_existing_remote_tables() is not None),
            ("创建文档注册表", self.create_enhanced_document_registry),
            ("创建文档切片表", self.create_document_chunks_table),
            ("创建向量关联表", self.create_vectors_enhanced_table),
            ("创建ES分片关联表", self.create_es_shards_table),
            ("创建处理历史表", self.create_processing_history_table),
            ("添加外键约束", self.add_foreign_key_constraints),
            ("创建数据库索引", self.create_enhanced_indexes),
            ("创建演示数据", self.create_demo_data),
            ("验证远程升级结果", self.verify_remote_upgrade_results)
        ]
        
        successful_steps = 0
        for step_name, step_func in upgrade_steps:
            try:
                success = step_func()
                if success:
                    successful_steps += 1
                else:
                    print(f"\n⚠️ 步骤失败: {step_name}")
            except Exception as e:
                print(f"\n❌ 步骤异常: {step_name} - {str(e)}")
                self.errors.append(f"{step_name}: {str(e)}")
        
        overall_success = successful_steps == len(upgrade_steps)
        
        # 生成升级报告
        self._generate_remote_upgrade_report(overall_success)
        
        return overall_success
    
    def _generate_remote_upgrade_report(self, overall_success: bool):
        """生成远程升级报告"""
        end_time = datetime.now()
        total_duration = int((end_time - self.start_time).total_seconds() * 1000)
        
        print("\n" + "="*80)
        print("📊 远程数据库增强版升级报告")
        print("="*80)
        
        print(f"\n🌍 远程服务器信息:")
        print(f"   地址: {self.db_config['host']}:{self.db_config['port']}")
        print(f"   数据库: {self.db_config['database']}")
        print(f"   用户: {self.db_config['user']}")
        
        print(f"\n⏱️ 升级统计:")
        print(f"   开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   总耗时: {total_duration}ms")
        print(f"   总操作数: {len(self.upgrade_results)}")
        
        successful_ops = sum(1 for r in self.upgrade_results if r["success"])
        print(f"   成功操作: {successful_ops}")
        print(f"   失败操作: {len(self.upgrade_results) - successful_ops}")
        
        # 显示操作详情
        print(f"\n📋 操作详情:")
        for result in self.upgrade_results:
            status_icon = "✅" if result["success"] else "❌"
            print(f"   {status_icon} {result['operation']}")
            if result["details"]:
                print(f"      └─ {result['details']}")
        
        # 显示错误
        if self.errors:
            print(f"\n❌ 错误列表:")
            for error in self.errors:
                print(f"   • {error}")
        
        # 总结
        print(f"\n{'='*80}")
        if overall_success:
            print("🎉 远程数据库增强版升级成功!")
            print("💡 所有增强版表结构已在远程服务器创建，系统已准备就绪。")
            print("📝 接下来可以:")
            print("   1. 使用增强版文档管理器连接远程数据库")
            print("   2. 配置应用程序使用远程数据库连接")
            print("   3. 运行完整系统测试验证远程连接")
        else:
            print("❌ 远程数据库增强版升级部分失败!")
            print("💡 请检查错误信息和网络连接，然后重试失败的步骤。")
        print("="*80)


def main():
    """主函数"""
    print("🚀 智政知识库远程数据库增强版自动化升级工具")
    print("基于昨天的远程数据库连接配置")
    print("包含：文档注册增强 + 切片追踪 + 向量关联 + ES分片关联 + 处理历史")
    print("="*80)
    
    print(f"🌍 目标远程服务器信息:")
    print(f"   地址: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")
    print(f"   数据库: {REMOTE_DB_CONFIG['database']}")
    print(f"   用户: {REMOTE_DB_CONFIG['user']}")
    
    try:
        upgrader = RemoteDatabaseUpgrader()
        success = upgrader.execute_remote_full_upgrade()
        
        return success
        
    except Exception as e:
        print(f"\n❌ 远程升级过程中发生异常: {e}")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断远程升级")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        sys.exit(1) 