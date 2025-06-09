#!/usr/bin/env python3
"""
远程PostgreSQL数据库连接测试和初始化脚本（修复版）
测试连接到远程服务器并执行完整的数据库初始化
包含增强版文档管理表结构，支持向量chunk ID、文档ID和ES分片数据的完整关联追踪
"""

import psycopg2
import psycopg2.extras
import os
import sys
from pathlib import Path
import time
from datetime import datetime
import uuid

# 远程数据库连接配置
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🔗 {title}")
    print(f"{'='*60}")

def print_step(step: str, status: str = "INFO"):
    """打印步骤信息"""
    icons = {"INFO": "📋", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(status, "📋")
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {icon} {step}")

def test_connection():
    """测试数据库连接"""
    print_step("测试远程PostgreSQL数据库连接...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print_step(f"数据库版本: {version}", "SUCCESS")
        
        cursor.execute("SELECT current_database(), current_user, current_timestamp;")
        db_info = cursor.fetchone()
        print_step(f"数据库: {db_info[0]}, 用户: {db_info[1]}", "SUCCESS")
        
        cursor.close()
        conn.close()
        
        print_step("数据库连接测试成功！", "SUCCESS")
        return True
        
    except psycopg2.Error as e:
        print_step(f"数据库连接失败: {e}", "ERROR")
        return False

def create_enhanced_tables():
    """创建增强版文档管理表结构"""
    print_step("创建增强版文档管理表结构...")
    
    # 分步创建表，避免外键约束问题
    tables_sql = [
        # 1. 文档注册表（增强版）
        """
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
        """,
        
        # 2. 文档切片表（增强版，使用新名称避免冲突）
        """
        CREATE TABLE IF NOT EXISTS document_chunks_enhanced (
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
        """,
        
        # 3. 向量数据关联表（增强版）
        """
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
        """,
        
        # 4. ES文档分片关联表
        """
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
        """,
        
        # 5. 文档处理历史表
        """
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
    ]
    
    # 外键约束
    constraints_sql = [
        "ALTER TABLE document_chunks_enhanced ADD CONSTRAINT IF NOT EXISTS fk_chunks_enh_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;",
        "ALTER TABLE document_vectors_enhanced ADD CONSTRAINT IF NOT EXISTS fk_vectors_enh_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;",
        "ALTER TABLE document_vectors_enhanced ADD CONSTRAINT IF NOT EXISTS fk_vectors_enh_chunk_id FOREIGN KEY (chunk_id) REFERENCES document_chunks_enhanced(chunk_id) ON DELETE CASCADE;",
        "ALTER TABLE document_es_shards ADD CONSTRAINT IF NOT EXISTS fk_es_shards_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;",
        "ALTER TABLE document_es_shards ADD CONSTRAINT IF NOT EXISTS fk_es_shards_chunk_id FOREIGN KEY (chunk_id) REFERENCES document_chunks_enhanced(chunk_id) ON DELETE CASCADE;",
        "ALTER TABLE document_processing_history ADD CONSTRAINT IF NOT EXISTS fk_proc_hist_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;"
    ]
    
    # 索引
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_filename ON document_registry_enhanced(filename);",
        "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_hash ON document_registry_enhanced(file_hash);",
        "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_kb_id ON document_registry_enhanced(kb_id);",
        "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_status ON document_registry_enhanced(status);",
        "CREATE INDEX IF NOT EXISTS idx_chunks_enh_file_id ON document_chunks_enhanced(file_id);",
        "CREATE INDEX IF NOT EXISTS idx_chunks_enh_index ON document_chunks_enhanced(chunk_index);",
        "CREATE INDEX IF NOT EXISTS idx_vectors_enh_file_id ON document_vectors_enhanced(file_id);",
        "CREATE INDEX IF NOT EXISTS idx_vectors_enh_chunk_id ON document_vectors_enhanced(chunk_id);",
        "CREATE INDEX IF NOT EXISTS idx_vectors_enh_vector_id ON document_vectors_enhanced(vector_id);",
        "CREATE INDEX IF NOT EXISTS idx_es_shards_file_id ON document_es_shards(file_id);",
        "CREATE INDEX IF NOT EXISTS idx_es_shards_es_index ON document_es_shards(es_index);",
        "CREATE INDEX IF NOT EXISTS idx_proc_hist_file_id ON document_processing_history(file_id);"
    ]
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 步骤1：创建表
        print_step("步骤1: 创建增强版表结构...", "INFO")
        for i, sql in enumerate(tables_sql, 1):
            cursor.execute(sql)
            print_step(f"创建表 {i}/{len(tables_sql)}", "SUCCESS")
        
        # 步骤2：添加外键约束
        print_step("步骤2: 添加外键约束...", "INFO")
        for constraint in constraints_sql:
            try:
                cursor.execute(constraint)
            except psycopg2.Error as e:
                print_step(f"添加约束跳过: {str(e)[:50]}...", "WARNING")
        
        # 步骤3：创建索引
        print_step("步骤3: 创建索引...", "INFO")
        for index_sql in indexes_sql:
            cursor.execute(index_sql)
        
        print_step("增强版文档管理表创建完成！", "SUCCESS")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print_step(f"创建增强版表失败: {e}", "ERROR")
        return False

def create_test_data():
    """创建测试数据"""
    print_step("创建测试数据...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 测试文档
        test_file_id = str(uuid.uuid4())
        test_doc_sql = """
            INSERT INTO document_registry_enhanced 
            (file_id, filename, content_type, file_size, file_hash, storage_backend, 
             storage_path, kb_id, doc_id, user_id, metadata, status, processing_status)
            VALUES (%s, 'test_document.pdf', 'application/pdf', 1024000, 
                    %s, 'minio', '/test/test_document.pdf', 
                    '1', 'test_doc_1', 'test_user', '{"source": "test", "category": "demo"}', 
                    'uploaded', 'completed')
            ON CONFLICT (file_hash) DO NOTHING;
        """
        file_hash = f"test_hash_{int(time.time())}"
        cursor.execute(test_doc_sql, (test_file_id, file_hash))
        
        # 测试切片
        chunk_id = str(uuid.uuid4())
        chunk_sql = """
            INSERT INTO document_chunks_enhanced 
            (chunk_id, file_id, chunk_index, chunk_text, chunk_size, chunk_hash, processing_status)
            VALUES (%s, %s, 0, '这是一个测试文档切片的示例内容。', 50, %s, 'completed')
            ON CONFLICT (file_id, chunk_index) DO NOTHING;
        """
        chunk_hash = f"chunk_hash_{int(time.time())}"
        cursor.execute(chunk_sql, (chunk_id, test_file_id, chunk_hash))
        
        # 测试向量关联
        vector_sql = """
            INSERT INTO document_vectors_enhanced 
            (file_id, chunk_id, vector_id, vector_collection, vector_index, 
             embedding_model, embedding_dimension)
            VALUES (%s, %s, %s, 'default_collection', 'default_index', 
                    'text-embedding-ada-002', 1536)
            ON CONFLICT (file_id, chunk_id, vector_id) DO NOTHING;
        """
        vector_id = f"vec_{int(time.time())}"
        cursor.execute(vector_sql, (test_file_id, chunk_id, vector_id))
        
        # 测试ES分片关联
        es_sql = """
            INSERT INTO document_es_shards 
            (file_id, chunk_id, es_index, es_doc_id, es_doc_type)
            VALUES (%s, %s, 'documents', %s, 'document')
            ON CONFLICT (es_index, es_doc_id) DO NOTHING;
        """
        es_doc_id = f"doc_{int(time.time())}"
        cursor.execute(es_sql, (test_file_id, chunk_id, es_doc_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_step("创建了演示数据（增强版文档管理）", "SUCCESS")
        return True
        
    except psycopg2.Error as e:
        print_step(f"创建演示数据失败: {e}", "ERROR")
        return False

def verify_installation():
    """验证安装结果"""
    print_step("验证数据库安装结果...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查增强版表
        enhanced_tables = [
            'document_registry_enhanced', 'document_chunks_enhanced', 
            'document_vectors_enhanced', 'document_es_shards', 'document_processing_history'
        ]
        
        existing_tables = []
        for table in enhanced_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            
            if cursor.fetchone()[0]:
                existing_tables.append(table)
                
                # 检查记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print_step(f"表 '{table}' 记录数: {count}", "INFO")
        
        print_step(f"增强版表检查: {len(existing_tables)}/{len(enhanced_tables)} 存在", 
                  "SUCCESS" if len(existing_tables) == len(enhanced_tables) else "WARNING")
        
        cursor.close()
        conn.close()
        
        return len(existing_tables) == len(enhanced_tables)
        
    except psycopg2.Error as e:
        print_step(f"验证安装失败: {e}", "ERROR")
        return False

def main():
    """主函数"""
    print_header("远程PostgreSQL数据库连接测试和增强版初始化（修复版）")
    
    print("🎯 目标服务器信息:")
    print(f"  📍 地址: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")
    print(f"  👤 用户: {REMOTE_DB_CONFIG['user']}")
    print(f"  🗄️  数据库: {REMOTE_DB_CONFIG['database']}")
    print("\n🔧 增强版功能:")
    print("  • 完整的向量chunk ID追踪")
    print("  • ES文档分片数据关联")
    print("  • 统一删除操作支持")
    print("  • 详细的处理历史记录")
    
    # 步骤1: 测试连接
    if not test_connection():
        return False
    
    # 步骤2: 创建增强版表
    if not create_enhanced_tables():
        return False
    
    # 步骤3: 创建测试数据
    if not create_test_data():
        print_step("测试数据创建失败，但表结构已创建", "WARNING")
    
    # 步骤4: 验证安装
    if not verify_installation():
        return False
    
    # 成功完成
    print_header("增强版数据库初始化完成")
    print_step("🎉 远程PostgreSQL数据库增强版初始化成功！", "SUCCESS")
    print_step("📋 新增功能:", "INFO")
    print("  ✅ 完整的文档chunk追踪（document_chunks_enhanced）")
    print("  ✅ 向量数据精确关联（document_vectors_enhanced）")
    print("  ✅ ES文档分片关联（document_es_shards）")
    print("  ✅ 统一删除操作支持")
    print("  ✅ 详细的操作历史记录（document_processing_history）")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_step("\n用户中断操作", "INFO")
        sys.exit(1)
    except Exception as e:
        print_step(f"程序异常: {e}", "ERROR")
        sys.exit(1) 