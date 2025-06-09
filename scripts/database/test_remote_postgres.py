#!/usr/bin/env python3
"""
远程PostgreSQL数据库连接测试和初始化脚本 - 增强版
测试连接到远程服务器并执行完整的数据库初始化
包含增强版文档管理表结构，支持向量chunk ID、文档ID和ES分片数据的完整关联追踪
新增系统健康检查、性能监控、索引分析等高级功能
"""

import psycopg2
import psycopg2.extras
import os
import sys
from pathlib import Path
import time
from datetime import datetime, timedelta
import uuid
import json
import argparse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

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
        # 尝试连接数据库
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 执行简单查询
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print_step(f"数据库版本: {version}", "SUCCESS")
        
        # 检查当前数据库信息
        cursor.execute("SELECT current_database(), current_user, current_timestamp;")
        db_info = cursor.fetchone()
        print_step(f"数据库: {db_info[0]}, 用户: {db_info[1]}, 时间: {db_info[2]}", "SUCCESS")
        
        # 检查数据库权限
        cursor.execute("""
            SELECT datname, has_database_privilege(current_user, datname, 'CREATE') as can_create
            FROM pg_database 
            WHERE datname = current_database();
        """)
        perm_info = cursor.fetchone()
        print_step(f"数据库 '{perm_info[0]}' CREATE权限: {perm_info[1]}", "SUCCESS" if perm_info[1] else "WARNING")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        print_step("数据库连接测试成功！", "SUCCESS")
        return True
        
    except psycopg2.Error as e:
        print_step(f"数据库连接失败: {e}", "ERROR")
        return False
    except Exception as e:
        print_step(f"连接测试异常: {e}", "ERROR")
        return False

def check_existing_tables():
    """检查现有表结构"""
    print_step("检查数据库现有表结构...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 查询所有表
        cursor.execute("""
            SELECT schemaname, tablename, tableowner 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print_step(f"发现 {len(tables)} 个现有表:", "INFO")
            for schema, table, owner in tables:
                print(f"  • {table} (owner: {owner})")
        else:
            print_step("数据库中暂无用户表", "INFO")
        
        # 检查是否有数据
        total_rows = 0
        for schema, table, owner in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                if count > 0:
                    print_step(f"表 '{table}' 包含 {count} 行数据", "INFO")
                    total_rows += count
            except Exception as e:
                print_step(f"表 '{table}' 查询失败: {str(e)[:50]}...", "WARNING")
        
        print_step(f"数据库总记录数: {total_rows}", "INFO")
        
        cursor.close()
        conn.close()
        
        return len(tables)
        
    except psycopg2.Error as e:
        print_step(f"检查表结构失败: {e}", "ERROR")
        return -1

def create_enhanced_document_tables():
    """创建增强版文档管理表结构"""
    print_step("创建增强版文档管理表结构...")
    
    enhanced_tables_sql = """
    -- 1. 文档注册表（增强版）
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

    -- 2. 文档切片表（chunk级别的追踪）
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

    -- 3. 向量数据关联表（增强版）
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

    -- 4. ES文档分片关联表
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

    -- 5. 文档处理历史表
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

    -- 创建索引
    -- 文档注册表索引
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_filename ON document_registry_enhanced(filename);
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_hash ON document_registry_enhanced(file_hash);
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_kb_id ON document_registry_enhanced(kb_id);
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_doc_id ON document_registry_enhanced(doc_id);
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_user_id ON document_registry_enhanced(user_id);
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_status ON document_registry_enhanced(status);
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_proc_status ON document_registry_enhanced(processing_status);
    CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_upload_time ON document_registry_enhanced(upload_time);

    -- 文档切片表索引
    CREATE INDEX IF NOT EXISTS idx_doc_chunks_file_id ON document_chunks(file_id);
    CREATE INDEX IF NOT EXISTS idx_doc_chunks_index ON document_chunks(chunk_index);
    CREATE INDEX IF NOT EXISTS idx_doc_chunks_hash ON document_chunks(chunk_hash);
    CREATE INDEX IF NOT EXISTS idx_doc_chunks_status ON document_chunks(processing_status);

    -- 向量数据表索引
    CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_file_id ON document_vectors_enhanced(file_id);
    CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_chunk_id ON document_vectors_enhanced(chunk_id);
    CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_vector_id ON document_vectors_enhanced(vector_id);
    CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_collection ON document_vectors_enhanced(vector_collection);
    CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_index ON document_vectors_enhanced(vector_index);
    CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_model ON document_vectors_enhanced(embedding_model);

    -- ES分片表索引
    CREATE INDEX IF NOT EXISTS idx_doc_es_file_id ON document_es_shards(file_id);
    CREATE INDEX IF NOT EXISTS idx_doc_es_chunk_id ON document_es_shards(chunk_id);
    CREATE INDEX IF NOT EXISTS idx_doc_es_index ON document_es_shards(es_index);
    CREATE INDEX IF NOT EXISTS idx_doc_es_doc_id ON document_es_shards(es_doc_id);
    CREATE INDEX IF NOT EXISTS idx_doc_es_shard_id ON document_es_shards(es_shard_id);
    CREATE INDEX IF NOT EXISTS idx_doc_es_routing ON document_es_shards(es_routing);

    -- 处理历史表索引
    CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_file_id ON document_processing_history(file_id);
    CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_op_type ON document_processing_history(operation_type);
    CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_status ON document_processing_history(operation_status);
    CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_started ON document_processing_history(started_at);
    CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_user ON document_processing_history(operated_by);

    -- 兼容旧版本：创建原有文档表（如果需要）
    CREATE TABLE IF NOT EXISTS document_registry (
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
        metadata TEXT,
        status VARCHAR(20) DEFAULT 'uploaded',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(file_hash)
    );

    CREATE TABLE IF NOT EXISTS document_vectors (
        id SERIAL PRIMARY KEY,
        file_id VARCHAR(36) REFERENCES document_registry(file_id) ON DELETE CASCADE,
        vector_id VARCHAR(100) NOT NULL,
        chunk_id VARCHAR(100),
        vector_collection VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(file_id, vector_id)
    );

    -- 创建原有表的索引
    CREATE INDEX IF NOT EXISTS idx_document_registry_filename ON document_registry(filename);
    CREATE INDEX IF NOT EXISTS idx_document_registry_hash ON document_registry(file_hash);
    CREATE INDEX IF NOT EXISTS idx_document_registry_kb_id ON document_registry(kb_id);
    CREATE INDEX IF NOT EXISTS idx_document_registry_doc_id ON document_registry(doc_id);
    CREATE INDEX IF NOT EXISTS idx_document_registry_status ON document_registry(status);

    CREATE INDEX IF NOT EXISTS idx_document_vectors_file_id ON document_vectors(file_id);
    CREATE INDEX IF NOT EXISTS idx_document_vectors_vector_id ON document_vectors(vector_id);
    CREATE INDEX IF NOT EXISTS idx_document_vectors_collection ON document_vectors(vector_collection);
    """
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print_step("执行增强版文档管理表创建SQL...", "INFO")
        cursor.execute(enhanced_tables_sql)
        
        print_step("增强版文档管理表创建成功！", "SUCCESS")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print_step(f"创建增强版表失败: {e}", "ERROR")
        return False

def execute_sql_file(sql_file_path: str, confirm_required: bool = True):
    """执行SQL文件"""
    
    if not os.path.exists(sql_file_path):
        print_step(f"SQL文件不存在: {sql_file_path}", "ERROR")
        return False
    
    print_step(f"准备执行SQL文件: {sql_file_path}")
    
    # 读取SQL文件内容
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print_step(f"SQL文件大小: {len(sql_content)} 字符", "INFO")
        
        # 显示文件前几行预览
        lines = sql_content.split('\n')[:10]
        print_step("SQL文件预览:", "INFO")
        for i, line in enumerate(lines, 1):
            if line.strip():
                print(f"  {i:2}: {line}")
        print("  ...")
        
    except Exception as e:
        print_step(f"读取SQL文件失败: {e}", "ERROR")
        return False
    
    # 确认执行
    if confirm_required:
        print_step("即将执行数据库初始化脚本", "WARNING")
        confirmation = input("\n是否继续执行？这将创建/修改数据库表结构 (y/N): ").strip().lower()
        if confirmation not in ['y', 'yes', '是']:
            print_step("用户取消执行", "INFO")
            return False
    
    # 执行SQL
    try:
        print_step("开始执行SQL脚本...", "INFO")
        start_time = time.time()
        
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        conn.autocommit = True  # 启用自动提交
        cursor = conn.cursor()
        
        # 分割并执行SQL语句
        # 这里简单按分号分割，实际可能需要更复杂的解析
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        print_step(f"共有 {len(statements)} 个SQL语句待执行", "INFO")
        
        executed_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue
                
            try:
                cursor.execute(statement)
                executed_count += 1
                
                # 每100个语句报告一次进度
                if i % 100 == 0:
                    print_step(f"已执行 {i}/{len(statements)} 个语句", "INFO")
                    
            except psycopg2.Error as e:
                error_count += 1
                # 只显示前几个错误，避免刷屏
                if error_count <= 5:
                    print_step(f"语句 {i} 执行失败: {str(e)[:100]}...", "WARNING")
                elif error_count == 6:
                    print_step("更多错误已省略...", "WARNING")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print_step(f"SQL执行完成！", "SUCCESS")
        print_step(f"执行时间: {duration:.2f} 秒", "INFO")
        print_step(f"成功执行: {executed_count} 个语句", "SUCCESS")
        if error_count > 0:
            print_step(f"执行错误: {error_count} 个语句", "WARNING")
        
        cursor.close()
        conn.close()
        
        return error_count == 0
        
    except psycopg2.Error as e:
        print_step(f"执行SQL文件失败: {e}", "ERROR")
        return False
    except Exception as e:
        print_step(f"执行过程异常: {e}", "ERROR")
        return False

def create_test_data():
    """创建测试数据"""
    print_step("创建基础测试数据...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 创建默认管理员用户
        admin_id = str(uuid.uuid4())
        admin_sql = """
            INSERT INTO users (id, username, email, hashed_password, full_name, is_superuser)
            VALUES (%s, 'admin', 'admin@zzdsj.com', '$2b$12$LQv3c1yqBo69SFqjfUmNnuebNZr8cCsVIIuQ1y.U9VC.ExnQd7CtO', '系统管理员', true)
            ON CONFLICT (username) DO NOTHING;
        """
        cursor.execute(admin_sql, (admin_id,))
        
        # 创建默认角色
        try:
            role_id = str(uuid.uuid4())
            role_sql = """
                INSERT INTO roles (id, name, description, is_default)
                VALUES (%s, 'admin', '系统管理员角色', false)
                ON CONFLICT (name) DO NOTHING;
            """
            cursor.execute(role_sql, (role_id,))
        except psycopg2.Error as e:
            print_step(f"创建角色时跳过: {str(e)[:50]}...", "INFO")
        
        # 创建基础权限
        permissions = [
            ('user_management', '用户管理', '管理系统用户'),
            ('knowledge_base_management', '知识库管理', '管理知识库'),
            ('system_config', '系统配置', '配置系统参数'),
            ('file_management', '文件管理', '管理文件上传和存储'),
            ('document_processing', '文档处理', '处理文档向量化和索引')
        ]
        
        for code, name, desc in permissions:
            try:
                perm_id = str(uuid.uuid4())
                perm_sql = """
                    INSERT INTO permissions (id, code, name, description)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (code) DO NOTHING;
                """
                cursor.execute(perm_sql, (perm_id, code, name, desc))
            except psycopg2.Error:
                # 权限表可能不存在，跳过
                pass
        
        # 创建配置类别
        categories = [
            ('system', '系统配置', '基础系统配置'),
            ('ai_models', 'AI模型', 'AI模型相关配置'),
            ('storage', '存储配置', '文件和数据存储配置'),
            ('document_processing', '文档处理', '文档处理和向量化配置')
        ]
        
        for code, name, desc in categories:
            try:
                cat_id = str(uuid.uuid4())
                cat_sql = """
                    INSERT INTO config_categories (id, name, description, is_system)
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (name) DO NOTHING;
                """
                cursor.execute(cat_sql, (cat_id, name, desc))
            except psycopg2.Error:
                # 配置类别表可能不存在，跳过
                pass
        
        # 创建默认知识库
        try:
            kb_sql = """
                INSERT INTO knowledge_bases (name, description, type)
                VALUES ('默认知识库', '系统默认知识库', 'default')
                ON CONFLICT DO NOTHING;
            """
            cursor.execute(kb_sql)
        except psycopg2.Error:
            # 知识库表可能不存在，跳过
            pass
        
        # 创建测试文档数据（演示增强版表的使用）
        try:
            # 测试文档
            test_file_id = str(uuid.uuid4())
            test_doc_sql = """
                INSERT INTO document_registry_enhanced 
                (file_id, filename, content_type, file_size, file_hash, storage_backend, 
                 storage_path, kb_id, doc_id, user_id, metadata, status, processing_status)
                VALUES (%s, 'test_document.pdf', 'application/pdf', 1024000, 
                        'test_hash_123', 'minio', '/test/test_document.pdf', 
                        '1', 'test_doc_1', %s, '{"source": "test", "category": "demo"}', 
                        'uploaded', 'completed')
                ON CONFLICT (file_hash) DO NOTHING;
            """
            cursor.execute(test_doc_sql, (test_file_id, admin_id))
            
            # 测试切片
            chunk_id = str(uuid.uuid4())
            chunk_sql = """
                INSERT INTO document_chunks 
                (chunk_id, file_id, chunk_index, chunk_text, chunk_size, chunk_hash, processing_status)
                VALUES (%s, %s, 0, '这是一个测试文档切片的示例内容。', 50, 'chunk_hash_1', 'completed')
                ON CONFLICT (file_id, chunk_index) DO NOTHING;
            """
            cursor.execute(chunk_sql, (chunk_id, test_file_id))
            
            # 测试向量关联
            vector_sql = """
                INSERT INTO document_vectors_enhanced 
                (file_id, chunk_id, vector_id, vector_collection, vector_index, 
                 embedding_model, embedding_dimension)
                VALUES (%s, %s, 'vec_001', 'default_collection', 'default_index', 
                        'text-embedding-ada-002', 1536)
                ON CONFLICT (file_id, chunk_id, vector_id) DO NOTHING;
            """
            cursor.execute(vector_sql, (test_file_id, chunk_id))
            
            # 测试ES分片关联
            es_sql = """
                INSERT INTO document_es_shards 
                (file_id, chunk_id, es_index, es_doc_id, es_doc_type)
                VALUES (%s, %s, 'documents', 'doc_001', 'document')
                ON CONFLICT (es_index, es_doc_id) DO NOTHING;
            """
            cursor.execute(es_sql, (test_file_id, chunk_id))
            
            print_step("创建了演示数据（增强版文档管理）", "SUCCESS")
            
        except psycopg2.Error as e:
            print_step(f"创建演示数据失败（可能表不存在）: {str(e)[:50]}...", "INFO")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_step("测试数据创建成功！", "SUCCESS")
        return True
        
    except psycopg2.Error as e:
        print_step(f"创建测试数据失败: {e}", "ERROR")
        return False

def verify_installation():
    """验证安装结果"""
    print_step("验证数据库安装结果...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查关键表是否存在
        required_tables = [
            'users', 'document_registry_enhanced', 'document_chunks', 
            'document_vectors_enhanced', 'document_es_shards', 'document_processing_history'
        ]
        
        # 可选表（原有系统表）
        optional_tables = [
            'roles', 'permissions', 'knowledge_bases', 
            'documents', 'assistants', 'system_configs', 'model_providers',
            'document_registry', 'document_vectors'
        ]
        
        missing_tables = []
        existing_tables = []
        optional_existing = []
        
        # 检查必需表
        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            
            if cursor.fetchone()[0]:
                existing_tables.append(table)
            else:
                missing_tables.append(table)
        
        # 检查可选表
        for table in optional_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            
            if cursor.fetchone()[0]:
                optional_existing.append(table)
        
        print_step(f"核心表检查: {len(existing_tables)}/{len(required_tables)} 存在", 
                  "SUCCESS" if not missing_tables else "WARNING")
        
        print_step(f"可选表检查: {len(optional_existing)}/{len(optional_tables)} 存在", "INFO")
        
        if missing_tables:
            print_step(f"缺失核心表: {', '.join(missing_tables)}", "WARNING")
        
        # 检查增强版文档管理表的数据
        if 'document_registry_enhanced' in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM document_registry_enhanced;")
            doc_count = cursor.fetchone()[0]
            print_step(f"增强版文档注册表记录数: {doc_count}", "INFO")
            
            if 'document_chunks' in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM document_chunks;")
                chunk_count = cursor.fetchone()[0]
                print_step(f"文档切片记录数: {chunk_count}", "INFO")
            
            if 'document_vectors_enhanced' in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM document_vectors_enhanced;")
                vector_count = cursor.fetchone()[0]
                print_step(f"增强版向量关联记录数: {vector_count}", "INFO")
            
            if 'document_es_shards' in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM document_es_shards;")
                es_count = cursor.fetchone()[0]
                print_step(f"ES分片关联记录数: {es_count}", "INFO")
        
        # 检查用户数据
        if 'users' in existing_tables:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_superuser = true;")
            admin_count = cursor.fetchone()[0]
            print_step(f"管理员用户数: {admin_count}", "SUCCESS" if admin_count > 0 else "WARNING")
        
        cursor.close()
        conn.close()
        
        success = len(missing_tables) == 0
        print_step("数据库验证完成！", "SUCCESS" if success else "WARNING")
        return success
        
    except psycopg2.Error as e:
        print_step(f"验证安装失败: {e}", "ERROR")
        return False

@dataclass
class DatabaseHealthReport:
    """数据库健康报告"""
    timestamp: str
    connection_status: str
    performance_metrics: Dict
    index_analysis: Dict
    query_analysis: Dict
    recommendations: List[str]
    overall_score: int

class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def check_performance_metrics(self, cursor) -> Dict:
        """检查性能指标"""
        metrics = {}
        
        try:
            # 1. 数据库大小和增长趋势
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    pg_database_size(current_database()) as db_size_bytes
            """)
            size_info = cursor.fetchone()
            metrics['database_size'] = {
                'human_readable': size_info[0],
                'bytes': size_info[1]
            }
            
            # 2. 连接统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_connections,
                    COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                    COUNT(*) FILTER (WHERE state = 'idle') as idle_connections,
                    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            conn_stats = cursor.fetchone()
            metrics['connections'] = {
                'total': conn_stats[0],
                'active': conn_stats[1],
                'idle': conn_stats[2],
                'idle_in_transaction': conn_stats[3]
            }
            
            # 3. 缓存命中率
            cursor.execute("""
                SELECT 
                    ROUND(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0), 2) as cache_hit_ratio,
                    sum(blks_read) as blocks_read,
                    sum(blks_hit) as blocks_hit
                FROM pg_stat_database 
                WHERE datname = current_database()
            """)
            cache_stats = cursor.fetchone()
            metrics['cache'] = {
                'hit_ratio': cache_stats[0] or 0.0,
                'blocks_read': cache_stats[1] or 0,
                'blocks_hit': cache_stats[2] or 0
            }
            
            # 4. 事务统计
            cursor.execute("""
                SELECT 
                    xact_commit,
                    xact_rollback,
                    deadlocks,
                    conflicts,
                    temp_files,
                    temp_bytes
                FROM pg_stat_database 
                WHERE datname = current_database()
            """)
            tx_stats = cursor.fetchone()
            metrics['transactions'] = {
                'commits': tx_stats[0] or 0,
                'rollbacks': tx_stats[1] or 0,
                'deadlocks': tx_stats[2] or 0,
                'conflicts': tx_stats[3] or 0,
                'temp_files': tx_stats[4] or 0,
                'temp_bytes': tx_stats[5] or 0
            }
            
            # 5. WAL统计
            cursor.execute("""
                SELECT 
                    pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0') / 1024 / 1024 as wal_size_mb,
                    pg_current_wal_lsn() as current_wal_lsn
            """)
            wal_stats = cursor.fetchone()
            metrics['wal'] = {
                'size_mb': round(wal_stats[0], 2),
                'current_lsn': str(wal_stats[1])
            }
            
        except Exception as e:
            metrics['error'] = str(e)
            
        return metrics
    
    def analyze_indexes(self, cursor) -> Dict:
        """分析索引使用情况"""
        analysis = {}
        
        try:
            # 1. 未使用的索引
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes 
                WHERE idx_scan = 0 
                AND schemaname = 'public'
                ORDER BY pg_relation_size(indexrelid) DESC
            """)
            unused_indexes = cursor.fetchall()
            analysis['unused_indexes'] = [
                {
                    'table': row[1],
                    'index': row[2],
                    'size': row[4]
                }
                for row in unused_indexes
            ]
            
            # 2. 低效索引 (扫描次数少但占用空间大)
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                    pg_relation_size(indexrelid) as index_bytes
                FROM pg_stat_user_indexes 
                WHERE schemaname = 'public'
                AND pg_relation_size(indexrelid) > 1024 * 1024  -- 大于1MB
                AND idx_scan < 100  -- 扫描次数少于100次
                ORDER BY pg_relation_size(indexrelid) DESC
            """)
            inefficient_indexes = cursor.fetchall()
            analysis['inefficient_indexes'] = [
                {
                    'table': row[1],
                    'index': row[2],
                    'scan_count': row[3],
                    'size': row[6],
                    'efficiency_score': round((row[3] or 0) / max(row[7] / (1024*1024), 1), 2)
                }
                for row in inefficient_indexes
            ]
            
            # 3. 缺失索引建议 (基于查询模式)
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch,
                    CASE 
                        WHEN seq_scan > 0 THEN seq_tup_read / seq_scan 
                        ELSE 0 
                    END as avg_seq_read
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                AND seq_scan > idx_scan  -- 顺序扫描多于索引扫描
                ORDER BY seq_tup_read DESC
            """)
            seq_scan_heavy = cursor.fetchall()
            analysis['missing_index_candidates'] = [
                {
                    'table': row[1],
                    'seq_scans': row[2],
                    'seq_reads': row[3],
                    'avg_read_per_scan': round(row[6], 2),
                    'priority': 'HIGH' if row[6] > 1000 else 'MEDIUM'
                }
                for row in seq_scan_heavy if row[6] > 100
            ]
            
        except Exception as e:
            analysis['error'] = str(e)
            
        return analysis
    
    def analyze_queries(self, cursor) -> Dict:
        """分析查询性能"""
        analysis = {}
        
        try:
            # 检查是否启用了pg_stat_statements
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                );
            """)
            has_pg_stat_statements = cursor.fetchone()[0]
            
            if has_pg_stat_statements:
                # 最耗时的查询
                cursor.execute("""
                    SELECT 
                        LEFT(query, 100) as query_snippet,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time,
                        stddev_exec_time
                    FROM pg_stat_statements 
                    WHERE query NOT LIKE '%pg_stat_statements%'
                    ORDER BY total_exec_time DESC 
                    LIMIT 10
                """)
                slow_queries = cursor.fetchall()
                analysis['slow_queries'] = [
                    {
                        'query': row[0],
                        'calls': row[1],
                        'total_time': round(row[2], 2),
                        'mean_time': round(row[3], 2),
                        'max_time': round(row[4], 2)
                    }
                    for row in slow_queries
                ]
                
                # 调用频率最高的查询
                cursor.execute("""
                    SELECT 
                        LEFT(query, 100) as query_snippet,
                        calls,
                        total_exec_time,
                        mean_exec_time
                    FROM pg_stat_statements 
                    WHERE query NOT LIKE '%pg_stat_statements%'
                    ORDER BY calls DESC 
                    LIMIT 10
                """)
                frequent_queries = cursor.fetchall()
                analysis['frequent_queries'] = [
                    {
                        'query': row[0],
                        'calls': row[1],
                        'total_time': round(row[2], 2),
                        'mean_time': round(row[3], 2)
                    }
                    for row in frequent_queries
                ]
            else:
                analysis['pg_stat_statements'] = 'not_enabled'
                analysis['recommendation'] = 'Enable pg_stat_statements extension for query analysis'
            
            # 当前活跃的长时间运行查询
            cursor.execute("""
                SELECT 
                    pid,
                    now() - query_start as duration,
                    state,
                    LEFT(query, 100) as query_snippet
                FROM pg_stat_activity 
                WHERE state = 'active' 
                AND query_start < now() - interval '30 seconds'
                AND query NOT LIKE '%pg_stat_activity%'
                ORDER BY query_start ASC
            """)
            long_running = cursor.fetchall()
            analysis['long_running_queries'] = [
                {
                    'pid': row[0],
                    'duration': str(row[1]),
                    'state': row[2],
                    'query': row[3]
                }
                for row in long_running
            ]
            
        except Exception as e:
            analysis['error'] = str(e)
            
        return analysis
    
    def generate_recommendations(self, metrics: Dict, index_analysis: Dict, query_analysis: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 性能相关建议
        if 'cache' in metrics:
            cache_hit_ratio = metrics['cache']['hit_ratio']
            if cache_hit_ratio < 90:
                recommendations.append(f"⚠️ 缓存命中率较低 ({cache_hit_ratio}%)，建议调整shared_buffers参数")
        
        # 连接相关建议
        if 'connections' in metrics:
            idle_in_tx = metrics['connections']['idle_in_transaction']
            if idle_in_tx > 5:
                recommendations.append(f"⚠️ 发现 {idle_in_tx} 个空闲事务连接，可能存在连接泄漏")
        
        # 索引相关建议
        if 'unused_indexes' in index_analysis:
            unused_count = len(index_analysis['unused_indexes'])
            if unused_count > 0:
                recommendations.append(f"💡 发现 {unused_count} 个未使用的索引，建议清理以节省空间")
        
        if 'missing_index_candidates' in index_analysis:
            missing_count = len(index_analysis['missing_index_candidates'])
            if missing_count > 0:
                recommendations.append(f"💡 发现 {missing_count} 个表可能需要添加索引以提高查询性能")
        
        # 查询相关建议
        if 'long_running_queries' in query_analysis:
            long_count = len(query_analysis['long_running_queries'])
            if long_count > 0:
                recommendations.append(f"⚠️ 发现 {long_count} 个长时间运行的查询，建议检查和优化")
        
        if query_analysis.get('pg_stat_statements') == 'not_enabled':
            recommendations.append("💡 建议启用pg_stat_statements扩展以获得更详细的查询分析")
        
        # WAL相关建议
        if 'wal' in metrics:
            wal_size = metrics['wal']['size_mb']
            if wal_size > 1000:  # 大于1GB
                recommendations.append(f"⚠️ WAL大小较大 ({wal_size} MB)，建议检查checkpoint配置")
        
        if not recommendations:
            recommendations.append("✅ 数据库状态良好，未发现明显的性能问题")
        
        return recommendations
    
    def calculate_health_score(self, metrics: Dict, index_analysis: Dict, query_analysis: Dict) -> int:
        """计算健康评分 (0-100)"""
        score = 100
        
        # 缓存命中率影响 (最多扣30分)
        if 'cache' in metrics:
            cache_ratio = metrics['cache']['hit_ratio']
            if cache_ratio < 95:
                score -= min(30, (95 - cache_ratio) * 2)
        
        # 空闲事务连接影响 (每个扣5分)
        if 'connections' in metrics:
            idle_in_tx = metrics['connections']['idle_in_transaction']
            score -= min(25, idle_in_tx * 5)
        
        # 未使用索引影响 (每个扣2分)
        if 'unused_indexes' in index_analysis:
            unused_count = len(index_analysis['unused_indexes'])
            score -= min(20, unused_count * 2)
        
        # 长时间运行查询影响 (每个扣3分)
        if 'long_running_queries' in query_analysis:
            long_count = len(query_analysis['long_running_queries'])
            score -= min(15, long_count * 3)
        
        return max(0, score)
    
    def run_health_check(self) -> DatabaseHealthReport:
        """执行完整的健康检查"""
        print_step("开始数据库健康检查...", "INFO")
        
        try:
            conn = psycopg2.connect(**self.config)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # 检查各项指标
            performance_metrics = self.check_performance_metrics(cursor)
            index_analysis = self.analyze_indexes(cursor)
            query_analysis = self.analyze_queries(cursor)
            
            # 生成建议
            recommendations = self.generate_recommendations(
                performance_metrics, index_analysis, query_analysis
            )
            
            # 计算健康评分
            health_score = self.calculate_health_score(
                performance_metrics, index_analysis, query_analysis
            )
            
            cursor.close()
            conn.close()
            
            # 创建健康报告
            report = DatabaseHealthReport(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                connection_status="connected",
                performance_metrics=performance_metrics,
                index_analysis=index_analysis,
                query_analysis=query_analysis,
                recommendations=recommendations,
                overall_score=health_score
            )
            
            return report
            
        except Exception as e:
            print_step(f"健康检查失败: {e}", "ERROR")
            return DatabaseHealthReport(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                connection_status="failed",
                performance_metrics={},
                index_analysis={},
                query_analysis={},
                recommendations=[f"连接失败: {e}"],
                overall_score=0
            )

def print_health_report(report: DatabaseHealthReport):
    """打印健康检查报告"""
    print_header("数据库健康检查报告")
    
    # 整体评分
    score_color = "SUCCESS" if report.overall_score >= 80 else "WARNING" if report.overall_score >= 60 else "ERROR"
    print_step(f"整体健康评分: {report.overall_score}/100", score_color)
    
    # 性能指标
    if report.performance_metrics:
        print_step("性能指标:", "INFO")
        metrics = report.performance_metrics
        
        if 'database_size' in metrics:
            print(f"  📊 数据库大小: {metrics['database_size']['human_readable']}")
        
        if 'connections' in metrics:
            conn = metrics['connections']
            print(f"  🔗 连接统计: 总计 {conn['total']}, 活跃 {conn['active']}, 空闲 {conn['idle']}")
            if conn['idle_in_transaction'] > 0:
                print(f"  ⚠️  空闲事务: {conn['idle_in_transaction']} 个")
        
        if 'cache' in metrics:
            print(f"  💾 缓存命中率: {metrics['cache']['hit_ratio']}%")
        
        if 'transactions' in metrics:
            tx = metrics['transactions']
            if tx['deadlocks'] > 0:
                print(f"  🔒 死锁数: {tx['deadlocks']}")
    
    # 索引分析
    if report.index_analysis:
        print_step("索引分析:", "INFO")
        
        unused = report.index_analysis.get('unused_indexes', [])
        if unused:
            print(f"  🗑️  未使用索引: {len(unused)} 个")
            for idx in unused[:3]:  # 只显示前3个
                print(f"    • {idx['table']}.{idx['index']} ({idx['size']})")
        
        missing = report.index_analysis.get('missing_index_candidates', [])
        if missing:
            print(f"  💡 建议添加索引的表: {len(missing)} 个")
            for table in missing[:3]:
                print(f"    • {table['table']} (优先级: {table['priority']})")
    
    # 查询分析
    if report.query_analysis:
        print_step("查询分析:", "INFO")
        
        long_running = report.query_analysis.get('long_running_queries', [])
        if long_running:
            print(f"  🐌 长时间运行查询: {len(long_running)} 个")
            for query in long_running[:2]:
                print(f"    • PID {query['pid']}: {query['duration']} - {query['query'][:50]}...")
        
        if 'slow_queries' in report.query_analysis:
            slow_count = len(report.query_analysis['slow_queries'])
            print(f"  📈 慢查询统计: {slow_count} 条记录")
    
    # 优化建议
    if report.recommendations:
        print_step("优化建议:", "INFO")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
    
    print(f"\n📅 报告时间: {report.timestamp}")

def system_health_check():
    """执行系统健康检查"""
    checker = DatabaseHealthChecker(REMOTE_DB_CONFIG)
    report = checker.run_health_check()
    
    # 打印报告
    print_health_report(report)
    
    # 保存报告到文件
    report_dir = Path("health_reports")
    report_dir.mkdir(exist_ok=True)
    
    report_file = report_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    
    print_step(f"健康检查报告已保存到: {report_file}", "SUCCESS")
    
    return report.overall_score >= 70

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="远程PostgreSQL数据库管理工具")
    parser.add_argument('--mode', choices=['full', 'test', 'health', 'init'], default='full',
                       help='运行模式: full(完整初始化), test(仅测试连接), health(健康检查), init(仅初始化)')
    parser.add_argument('--skip-confirmation', action='store_true',
                       help='跳过确认提示')
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        # 仅测试连接
        print_header("数据库连接测试")
        return test_connection()
    
    elif args.mode == 'health':
        # 仅执行健康检查
        print_header("数据库健康检查")
        return system_health_check()
    
    elif args.mode == 'init':
        # 仅执行初始化
        print_header("数据库初始化")
        
        # 测试连接
        if not test_connection():
            print_step("连接测试失败，请检查网络和配置", "ERROR")
            return False
        
        # 创建增强版文档管理表
        if not create_enhanced_document_tables():
            print_step("增强版表创建失败", "ERROR")
            return False
        
        # 执行数据库初始化
        sql_file_path = "database_complete.sql"
        if os.path.exists(sql_file_path):
            if not execute_sql_file(sql_file_path, confirm_required=not args.skip_confirmation):
                print_step("数据库初始化失败", "WARNING")
        
        return True
    
    else:  # full mode
        print_header("远程PostgreSQL数据库连接测试和增强版初始化")
        
        print("🎯 目标服务器信息:")
        print(f"  📍 地址: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")
        print(f"  👤 用户: {REMOTE_DB_CONFIG['user']}")
        print(f"  🗄️  数据库: {REMOTE_DB_CONFIG['database']}")
        print("\n🔧 增强版功能:")
        print("  • 完整的向量chunk ID追踪")
        print("  • ES文档分片数据关联")
        print("  • 统一删除操作支持")
        print("  • 详细的处理历史记录")
        print("  • 系统健康检查和性能监控")
        print("  • 索引使用分析和优化建议")
        
        # 步骤1: 测试连接
        if not test_connection():
            print_step("连接测试失败，请检查网络和配置", "ERROR")
            return False
        
        # 步骤2: 检查现有表
        table_count = check_existing_tables()
        if table_count == -1:
            print_step("无法检查现有表结构", "ERROR")
            return False
        
        # 步骤3: 创建增强版文档管理表
        print_step("开始创建增强版文档管理表结构...", "INFO")
        if not create_enhanced_document_tables():
            print_step("增强版表创建失败", "ERROR")
            return False
        
        # 步骤4: 执行数据库初始化（如果存在）
        sql_file_path = "database_complete.sql"
        if os.path.exists(sql_file_path):
            print_step("发现数据库初始化文件，准备执行...", "INFO")
            if not execute_sql_file(sql_file_path, confirm_required=not args.skip_confirmation):
                print_step("数据库初始化失败", "WARNING")
        else:
            print_step(f"未找到数据库初始化文件: {sql_file_path} (跳过)", "INFO")
        
        # 步骤5: 创建测试数据
        if not create_test_data():
            print_step("创建测试数据失败", "WARNING")
        
        # 步骤6: 验证安装
        if not verify_installation():
            print_step("数据库验证失败", "WARNING")
            return False
        
        # 步骤7: 执行系统健康检查
        if not system_health_check():
            print_step("系统健康检查失败", "WARNING")
            return False
        
        # 成功完成
        print_header("增强版数据库初始化完成")
    print_step("🎉 远程PostgreSQL数据库增强版初始化成功！", "SUCCESS")
    print_step("📋 新增功能:", "INFO")
    print("  ✅ 完整的文档chunk追踪")
    print("  ✅ 向量数据精确关联")
    print("  ✅ ES文档分片关联")
    print("  ✅ 统一删除操作支持")
    print("  ✅ 详细的操作历史记录")
    
    print_step("🔧 后续步骤:", "INFO")
    print("  1. 更新应用程序使用增强版文档管理器")
    print("  2. 配置ES和向量数据库连接")
    print("  3. 测试统一删除功能")
    print("  4. 迁移现有文档数据（如需要）")
    
    print_step("🔑 默认管理员账户:", "INFO")
    print("  用户名: admin")
    print("  邮箱: admin@zzdsj.com")
    print("  密码: admin123 (请及时修改)")
    
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