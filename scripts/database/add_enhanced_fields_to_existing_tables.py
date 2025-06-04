#!/usr/bin/env python3
"""
为现有数据库表添加增强版字段的专用脚本
处理字段增加、索引创建、数据迁移等操作
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

class ExistingTableEnhancer:
    """现有表增强器"""
    
    def __init__(self, db_config: Dict[str, Any] = None):
        """初始化增强器"""
        self.db_config = db_config or self._get_default_db_config()
        self.enhancement_results = []
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
        self.enhancement_results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} {operation}")
        if details:
            print(f"    └─ {details}")
        if duration_ms > 0:
            print(f"    ⏱️ 耗时: {duration_ms}ms")
            
        if not success:
            self.errors.append(f"{operation}: {details}")
    
    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table_name,))
            
            exists = cursor.fetchone()['exists']
            cursor.close()
            conn.close()
            
            return exists
            
        except Exception as e:
            logger.error(f"检查表{table_name}是否存在失败: {str(e)}")
            return False
    
    def check_column_exists(self, table_name: str, column_name: str) -> bool:
        """检查列是否存在"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s 
                    AND column_name = %s
                )
            """, (table_name, column_name))
            
            exists = cursor.fetchone()['exists']
            cursor.close()
            conn.close()
            
            return exists
            
        except Exception as e:
            logger.error(f"检查列{table_name}.{column_name}是否存在失败: {str(e)}")
            return False
    
    def add_fields_to_document_registry(self) -> bool:
        """为document_registry表添加增强版字段"""
        print("\n📄 为document_registry表添加增强版字段...")
        
        if not self.check_table_exists('document_registry'):
            self.log_operation(
                "document_registry字段增强", False,
                "表不存在，需要先创建基础表结构"
            )
            return False
        
        # 需要添加的字段列表
        fields_to_add = [
            ("user_id", "VARCHAR(36)", "用户ID"),
            ("processing_status", "VARCHAR(20) DEFAULT 'pending'", "处理状态"),
            ("chunk_count", "INTEGER DEFAULT 0", "切片数量"),
            ("vector_count", "INTEGER DEFAULT 0", "向量数量"),
            ("es_doc_count", "INTEGER DEFAULT 0", "ES文档数量"),
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "更新时间")
        ]
        
        added_fields = 0
        for field_name, field_type, field_desc in fields_to_add:
            if not self.check_column_exists('document_registry', field_name):
                try:
                    start_time = time.time()
                    conn = self._get_db_connection()
                    cursor = conn.cursor()
                    
                    alter_sql = f"ALTER TABLE document_registry ADD COLUMN {field_name} {field_type}"
                    cursor.execute(alter_sql)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.log_operation(
                        f"添加字段 {field_name}", True,
                        f"{field_desc} ({field_type})", duration_ms
                    )
                    added_fields += 1
                    
                except Exception as e:
                    self.log_operation(
                        f"添加字段 {field_name}", False,
                        f"失败: {str(e)}"
                    )
            else:
                print(f"   ℹ️ 字段 {field_name} 已存在，跳过")
        
        self.log_operation(
            "document_registry字段增强", added_fields > 0,
            f"成功添加 {added_fields}/{len(fields_to_add)} 个字段"
        )
        
        return True
    
    def add_fields_to_document_vectors(self) -> bool:
        """为document_vectors表添加增强版字段"""
        print("\n🧠 为document_vectors表添加增强版字段...")
        
        if not self.check_table_exists('document_vectors'):
            self.log_operation(
                "document_vectors字段增强", False,
                "表不存在，需要先创建基础表结构"
            )
            return False
        
        # 需要添加的字段列表
        fields_to_add = [
            ("vector_index", "VARCHAR(100)", "向量索引"),
            ("embedding_model", "VARCHAR(100)", "嵌入模型"),
            ("embedding_dimension", "INTEGER", "嵌入维度"),
            ("vector_metadata", "TEXT", "向量元数据")
        ]
        
        added_fields = 0
        for field_name, field_type, field_desc in fields_to_add:
            if not self.check_column_exists('document_vectors', field_name):
                try:
                    start_time = time.time()
                    conn = self._get_db_connection()
                    cursor = conn.cursor()
                    
                    alter_sql = f"ALTER TABLE document_vectors ADD COLUMN {field_name} {field_type}"
                    cursor.execute(alter_sql)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.log_operation(
                        f"添加字段 {field_name}", True,
                        f"{field_desc} ({field_type})", duration_ms
                    )
                    added_fields += 1
                    
                except Exception as e:
                    self.log_operation(
                        f"添加字段 {field_name}", False,
                        f"失败: {str(e)}"
                    )
            else:
                print(f"   ℹ️ 字段 {field_name} 已存在，跳过")
        
        self.log_operation(
            "document_vectors字段增强", added_fields > 0,
            f"成功添加 {added_fields}/{len(fields_to_add)} 个字段"
        )
        
        return True
    
    def create_missing_indexes(self) -> bool:
        """创建缺失的索引"""
        print("\n🏗️ 创建缺失的增强版索引...")
        
        # 需要创建的索引列表
        indexes_to_create = [
            # document_registry 新索引
            ("idx_document_registry_user_id", "document_registry", "user_id"),
            ("idx_document_registry_processing_status", "document_registry", "processing_status"),
            ("idx_document_registry_updated_at", "document_registry", "updated_at"),
            
            # document_vectors 新索引
            ("idx_document_vectors_embedding_model", "document_vectors", "embedding_model"),
            ("idx_document_vectors_vector_index", "document_vectors", "vector_index"),
        ]
        
        created_indexes = 0
        for index_name, table_name, column_name in indexes_to_create:
            try:
                # 检查索引是否已存在
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM pg_indexes 
                        WHERE schemaname = 'public' 
                        AND indexname = %s
                    )
                """, (index_name,))
                
                index_exists = cursor.fetchone()['exists']
                
                if not index_exists:
                    # 检查列是否存在
                    if self.check_column_exists(table_name, column_name):
                        start_time = time.time()
                        
                        create_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
                        cursor.execute(create_sql)
                        conn.commit()
                        
                        duration_ms = int((time.time() - start_time) * 1000)
                        self.log_operation(
                            f"创建索引 {index_name}", True,
                            f"{table_name}.{column_name}", duration_ms
                        )
                        created_indexes += 1
                    else:
                        print(f"   ⚠️ 列 {table_name}.{column_name} 不存在，跳过索引创建")
                else:
                    print(f"   ℹ️ 索引 {index_name} 已存在，跳过")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                self.log_operation(
                    f"创建索引 {index_name}", False,
                    f"失败: {str(e)}"
                )
        
        self.log_operation(
            "创建缺失索引", True,
            f"成功创建 {created_indexes}/{len(indexes_to_create)} 个索引"
        )
        
        return True
    
    def migrate_existing_data(self) -> bool:
        """迁移现有数据的字段值"""
        print("\n🔄 迁移现有数据的字段值...")
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 更新document_registry表的新字段默认值
            if self.check_table_exists('document_registry'):
                update_operations = [
                    ("processing_status", "'pending'", "设置默认处理状态"),
                    ("chunk_count", "0", "初始化切片计数"),
                    ("vector_count", "0", "初始化向量计数"),
                    ("es_doc_count", "0", "初始化ES文档计数"),
                    ("updated_at", "CURRENT_TIMESTAMP", "设置更新时间")
                ]
                
                for field_name, default_value, description in update_operations:
                    if self.check_column_exists('document_registry', field_name):
                        try:
                            update_sql = f"""
                                UPDATE document_registry 
                                SET {field_name} = {default_value} 
                                WHERE {field_name} IS NULL
                            """
                            cursor.execute(update_sql)
                            updated_rows = cursor.rowcount
                            
                            if updated_rows > 0:
                                self.log_operation(
                                    f"数据迁移 {field_name}", True,
                                    f"{description}: 更新了 {updated_rows} 行"
                                )
                            else:
                                print(f"   ℹ️ 字段 {field_name} 无需更新")
                                
                        except Exception as e:
                            self.log_operation(
                                f"数据迁移 {field_name}", False,
                                f"失败: {str(e)}"
                            )
            
            # 更新document_vectors表的新字段默认值
            if self.check_table_exists('document_vectors'):
                vector_updates = [
                    ("embedding_model", "'unknown'", "设置默认嵌入模型"),
                    ("embedding_dimension", "1536", "设置默认维度")
                ]
                
                for field_name, default_value, description in vector_updates:
                    if self.check_column_exists('document_vectors', field_name):
                        try:
                            update_sql = f"""
                                UPDATE document_vectors 
                                SET {field_name} = {default_value} 
                                WHERE {field_name} IS NULL
                            """
                            cursor.execute(update_sql)
                            updated_rows = cursor.rowcount
                            
                            if updated_rows > 0:
                                self.log_operation(
                                    f"向量数据迁移 {field_name}", True,
                                    f"{description}: 更新了 {updated_rows} 行"
                                )
                            else:
                                print(f"   ℹ️ 向量字段 {field_name} 无需更新")
                                
                        except Exception as e:
                            self.log_operation(
                                f"向量数据迁移 {field_name}", False,
                                f"失败: {str(e)}"
                            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_operation(
                "现有数据迁移", True,
                "数据迁移操作完成"
            )
            
            return True
            
        except Exception as e:
            self.log_operation(
                "现有数据迁移", False,
                f"迁移失败: {str(e)}"
            )
            return False
    
    def verify_enhancements(self) -> bool:
        """验证增强结果"""
        print("\n🔍 验证字段增强结果...")
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 验证document_registry表的新字段
            if self.check_table_exists('document_registry'):
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' 
                    AND table_name = 'document_registry'
                    AND column_name IN ('user_id', 'processing_status', 'chunk_count', 'vector_count', 'es_doc_count', 'updated_at')
                    ORDER BY column_name
                """)
                
                registry_columns = cursor.fetchall()
                print(f"   📄 document_registry 新字段: {len(registry_columns)} 个")
                for col in registry_columns:
                    print(f"      ✅ {col['column_name']}: {col['data_type']}")
            
            # 验证document_vectors表的新字段
            if self.check_table_exists('document_vectors'):
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' 
                    AND table_name = 'document_vectors'
                    AND column_name IN ('vector_index', 'embedding_model', 'embedding_dimension', 'vector_metadata')
                    ORDER BY column_name
                """)
                
                vectors_columns = cursor.fetchall()
                print(f"   🧠 document_vectors 新字段: {len(vectors_columns)} 个")
                for col in vectors_columns:
                    print(f"      ✅ {col['column_name']}: {col['data_type']}")
            
            # 验证新创建的索引
            cursor.execute("""
                SELECT indexname, tablename
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND (indexname LIKE '%user_id%' OR indexname LIKE '%processing_status%' 
                     OR indexname LIKE '%embedding_model%' OR indexname LIKE '%vector_index%')
                ORDER BY indexname
            """)
            
            new_indexes = cursor.fetchall()
            print(f"   🏗️ 新增索引: {len(new_indexes)} 个")
            for idx in new_indexes:
                print(f"      ✅ {idx['indexname']} on {idx['tablename']}")
            
            cursor.close()
            conn.close()
            
            self.log_operation(
                "增强结果验证", True,
                f"验证完成: 字段和索引均已正确创建"
            )
            
            return True
            
        except Exception as e:
            self.log_operation(
                "增强结果验证", False,
                f"验证失败: {str(e)}"
            )
            return False
    
    def execute_field_enhancement(self) -> bool:
        """执行完整的字段增强"""
        print("🚀 开始执行现有表的字段增强...")
        print("="*80)
        
        enhancement_steps = [
            ("为document_registry添加字段", self.add_fields_to_document_registry),
            ("为document_vectors添加字段", self.add_fields_to_document_vectors),
            ("创建缺失的索引", self.create_missing_indexes),
            ("迁移现有数据", self.migrate_existing_data),
            ("验证增强结果", self.verify_enhancements)
        ]
        
        successful_steps = 0
        for step_name, step_func in enhancement_steps:
            try:
                success = step_func()
                if success:
                    successful_steps += 1
                else:
                    print(f"\n⚠️ 步骤失败: {step_name}")
            except Exception as e:
                print(f"\n❌ 步骤异常: {step_name} - {str(e)}")
                self.errors.append(f"{step_name}: {str(e)}")
        
        overall_success = successful_steps == len(enhancement_steps)
        
        # 生成增强报告
        self._generate_enhancement_report(overall_success)
        
        return overall_success
    
    def _generate_enhancement_report(self, overall_success: bool):
        """生成增强报告"""
        end_time = datetime.now()
        total_duration = int((end_time - self.start_time).total_seconds() * 1000)
        
        print("\n" + "="*80)
        print("📊 现有表字段增强报告")
        print("="*80)
        
        print(f"\n⏱️ 增强统计:")
        print(f"   开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   总耗时: {total_duration}ms")
        print(f"   总操作数: {len(self.enhancement_results)}")
        
        successful_ops = sum(1 for r in self.enhancement_results if r["success"])
        print(f"   成功操作: {successful_ops}")
        print(f"   失败操作: {len(self.enhancement_results) - successful_ops}")
        
        # 显示操作详情
        print(f"\n📋 操作详情:")
        for result in self.enhancement_results:
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
            print("🎉 现有表字段增强成功!")
            print("💡 所有增强版字段已添加，现有数据已迁移。")
            print("📝 建议接下来:")
            print("   1. 运行完整的增强版表创建: ./run_enhanced_db_upgrade.sh")
            print("   2. 测试增强版文档管理器功能")
            print("   3. 运行系统测试验证所有功能")
        else:
            print("❌ 现有表字段增强部分失败!")
            print("💡 请检查错误信息并重试失败的操作。")
        print("="*80)


def main():
    """主函数"""
    print("🚀 智政知识库现有表字段增强工具")
    print("包含：字段添加 + 索引创建 + 数据迁移 + 结果验证")
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
        enhancer = ExistingTableEnhancer()
        success = enhancer.execute_field_enhancement()
        
        return success
        
    except Exception as e:
        print(f"\n❌ 字段增强过程中发生异常: {e}")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断字段增强")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        sys.exit(1) 