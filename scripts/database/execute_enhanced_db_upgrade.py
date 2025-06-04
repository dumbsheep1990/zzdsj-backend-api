#!/usr/bin/env python3
"""
自动化数据库增强版升级执行脚本
执行所有增强版文档管理表的创建和字段增加操作
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedDatabaseUpgrader:
    """数据库增强版升级器"""
    
    def __init__(self, db_config: Dict[str, Any] = None):
        """初始化升级器"""
        self.db_config = db_config or self._get_default_db_config()
        self.upgrade_results = []
        self.errors = []
        self.start_time = datetime.now()
        
    def _get_default_db_config(self) -> Dict[str, Any]:
        """获取默认数据库配置"""
        return {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "zzdsj"),
            "user": os.getenv("POSTGRES_USER", "zzdsj_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "zzdsj_pass")
        }
    
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
    
    def test_database_connection(self) -> bool:
        """测试数据库连接"""
        print("\n🔗 测试数据库连接...")
        
        try:
            start_time = time.time()
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 获取数据库版本信息
            cursor.execute("SELECT version()")
            version = cursor.fetchone()['version']
            
            cursor.close()
            conn.close()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self.log_operation(
                "数据库连接测试", True,
                f"PostgreSQL版本: {version.split(',')[0]}", duration_ms
            )
            
            print(f"📊 连接信息:")
            print(f"   主机: {self.db_config['host']}:{self.db_config['port']}")
            print(f"   数据库: {self.db_config['database']}")
            print(f"   用户: {self.db_config['user']}")
            
            return True
            
        except Exception as e:
            self.log_operation(
                "数据库连接测试", False,
                f"连接失败: {str(e)}"
            )
            return False
    
    def check_existing_tables(self) -> Dict[str, bool]:
        """检查现有表结构"""
        print("\n📊 检查现有表结构...")
        
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
            
            # 检查增强版表是否存在
            for table_name in enhanced_tables.keys():
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table_name,))
                
                exists = cursor.fetchone()['exists']
                enhanced_tables[table_name] = exists
                
                status_icon = "✅" if exists else "❌"
                print(f"   {status_icon} {table_name}: {'存在' if exists else '不存在'}")
            
            cursor.close()
            conn.close()
            
            existing_count = sum(enhanced_tables.values())
            total_count = len(enhanced_tables)
            
            self.log_operation(
                "表结构检查", True,
                f"增强版表: {existing_count}/{total_count} 存在"
            )
            
            return enhanced_tables
            
        except Exception as e:
            self.log_operation(
                "表结构检查", False,
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
            file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
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
            file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
            chunk_id VARCHAR(36) REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
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
            file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
            chunk_id VARCHAR(36) REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
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
            file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
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
    
    def verify_upgrade_results(self) -> bool:
        """验证升级结果"""
        print("\n🔍 验证升级结果...")
        
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
            
            cursor.close()
            conn.close()
            
            # 检查是否所有表都存在
            all_exist = all(count >= 0 for count in verification_results.values())
            
            self.log_operation(
                "升级结果验证", all_exist,
                f"表存在状态: {sum(1 for c in verification_results.values() if c >= 0)}/{len(tables_to_check)}"
            )
            
            return all_exist
            
        except Exception as e:
            self.log_operation(
                "升级结果验证", False,
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
    
    def execute_full_upgrade(self) -> bool:
        """执行完整的数据库升级"""
        print("🚀 开始执行数据库增强版升级...")
        print("="*80)
        
        upgrade_steps = [
            ("数据库连接测试", self.test_database_connection),
            ("检查现有表结构", lambda: self.check_existing_tables() is not None),
            ("创建文档注册表", self.create_enhanced_document_registry),
            ("创建文档切片表", self.create_document_chunks_table),
            ("创建向量关联表", self.create_vectors_enhanced_table),
            ("创建ES分片关联表", self.create_es_shards_table),
            ("创建处理历史表", self.create_processing_history_table),
            ("创建数据库索引", self.create_enhanced_indexes),
            ("创建演示数据", self.create_demo_data),
            ("验证升级结果", self.verify_upgrade_results)
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
        self._generate_upgrade_report(overall_success)
        
        return overall_success
    
    def _generate_upgrade_report(self, overall_success: bool):
        """生成升级报告"""
        end_time = datetime.now()
        total_duration = int((end_time - self.start_time).total_seconds() * 1000)
        
        print("\n" + "="*80)
        print("📊 数据库增强版升级报告")
        print("="*80)
        
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
            print("🎉 数据库增强版升级成功!")
            print("💡 所有增强版表结构已创建，系统已准备就绪。")
            print("📝 接下来可以:")
            print("   1. 使用增强版文档管理器进行文档操作")
            print("   2. 运行完整系统测试: ./run_complete_system_test.sh")
            print("   3. 启动混合搜索服务: ./scripts/start_with_hybrid_search.sh")
        else:
            print("❌ 数据库增强版升级部分失败!")
            print("💡 请检查错误信息并重试，或手动执行失败的步骤。")
        print("="*80)


def main():
    """主函数"""
    print("🚀 智政知识库数据库增强版自动化升级工具")
    print("包含：文档注册增强 + 切片追踪 + 向量关联 + ES分片关联 + 处理历史")
    print("="*80)
    
    # 检查环境变量
    required_env_vars = ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
        print("\n💡 请设置以下环境变量:")
        for var in missing_vars:
            print(f"   export {var}=<your_value>")
        return False
    
    try:
        upgrader = EnhancedDatabaseUpgrader()
        success = upgrader.execute_full_upgrade()
        
        return success
        
    except Exception as e:
        print(f"\n❌ 升级过程中发生异常: {e}")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断升级")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        sys.exit(1) 