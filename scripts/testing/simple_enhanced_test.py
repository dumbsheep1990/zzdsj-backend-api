#!/usr/bin/env python3
import psycopg2
import uuid
import time

config = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

print('🚀 开始创建增强版PostgreSQL表结构...')

try:
    conn = psycopg2.connect(**config)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # 1. 文档注册表（增强版）
    print('📋 创建文档注册表（增强版）...')
    cursor.execute("""
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
    """)
    print('✅ 文档注册表创建成功')
    
    # 2. 文档切片表（增强版）
    print('📋 创建文档切片表（增强版）...')
    cursor.execute("""
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
    """)
    print('✅ 文档切片表创建成功')
    
    # 3. 向量数据关联表（增强版）
    print('📋 创建向量数据关联表（增强版）...')
    cursor.execute("""
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
    """)
    print('✅ 向量数据关联表创建成功')
    
    # 4. ES文档分片关联表
    print('📋 创建ES文档分片关联表...')
    cursor.execute("""
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
    """)
    print('✅ ES文档分片关联表创建成功')
    
    # 5. 文档处理历史表
    print('📋 创建文档处理历史表...')
    cursor.execute("""
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
    """)
    print('✅ 文档处理历史表创建成功')
    
    # 添加外键约束
    print('📋 添加外键约束...')
    constraints = [
        "ALTER TABLE document_chunks_enhanced ADD CONSTRAINT IF NOT EXISTS fk_chunks_enh_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;",
        "ALTER TABLE document_vectors_enhanced ADD CONSTRAINT IF NOT EXISTS fk_vectors_enh_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;",
        "ALTER TABLE document_vectors_enhanced ADD CONSTRAINT IF NOT EXISTS fk_vectors_enh_chunk_id FOREIGN KEY (chunk_id) REFERENCES document_chunks_enhanced(chunk_id) ON DELETE CASCADE;",
        "ALTER TABLE document_es_shards ADD CONSTRAINT IF NOT EXISTS fk_es_shards_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;",
        "ALTER TABLE document_es_shards ADD CONSTRAINT IF NOT EXISTS fk_es_shards_chunk_id FOREIGN KEY (chunk_id) REFERENCES document_chunks_enhanced(chunk_id) ON DELETE CASCADE;",
        "ALTER TABLE document_processing_history ADD CONSTRAINT IF NOT EXISTS fk_proc_hist_file_id FOREIGN KEY (file_id) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE;"
    ]
    
    for constraint in constraints:
        try:
            cursor.execute(constraint)
            print('✅ 约束添加成功')
        except Exception as e:
            print(f'⚠️ 约束添加跳过: {str(e)[:50]}...')
    
    # 创建测试数据
    print('📋 创建测试数据...')
    test_file_id = str(uuid.uuid4())
    file_hash = f"test_hash_{int(time.time())}"
    
    cursor.execute("""
        INSERT INTO document_registry_enhanced 
        (file_id, filename, content_type, file_size, file_hash, storage_backend, 
         storage_path, kb_id, doc_id, user_id, metadata, status, processing_status)
        VALUES (%s, 'test_document.pdf', 'application/pdf', 1024000, 
                %s, 'minio', '/test/test_document.pdf', 
                '1', 'test_doc_1', 'test_user', '{"source": "test", "category": "demo"}', 
                'uploaded', 'completed')
        ON CONFLICT (file_hash) DO NOTHING;
    """, (test_file_id, file_hash))
    
    chunk_id = str(uuid.uuid4())
    chunk_hash = f"chunk_hash_{int(time.time())}"
    cursor.execute("""
        INSERT INTO document_chunks_enhanced 
        (chunk_id, file_id, chunk_index, chunk_text, chunk_size, chunk_hash, processing_status)
        VALUES (%s, %s, 0, '这是一个测试文档切片的示例内容。', 50, %s, 'completed')
        ON CONFLICT (file_id, chunk_index) DO NOTHING;
    """, (chunk_id, test_file_id, chunk_hash))
    
    print('✅ 测试数据创建成功')
    
    # 验证安装
    print('📋 验证安装结果...')
    tables = ['document_registry_enhanced', 'document_chunks_enhanced', 
              'document_vectors_enhanced', 'document_es_shards', 'document_processing_history']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f'✅ 表 {table}: {count} 条记录')
    
    cursor.close()
    conn.close()
    print('🎉 增强版PostgreSQL表结构创建完成！')
    print('📋 新增功能:')
    print('  ✅ 完整的文档chunk追踪（document_chunks_enhanced）')
    print('  ✅ 向量数据精确关联（document_vectors_enhanced）')
    print('  ✅ ES文档分片关联（document_es_shards）')
    print('  ✅ 统一删除操作支持')
    print('  ✅ 详细的操作历史记录（document_processing_history）')
    
except Exception as e:
    print(f'❌ 创建失败: {e}') 