#!/usr/bin/env python3
"""
修复远程数据库演示数据创建的脚本
适配现有的表结构，正确创建演示数据
"""

import psycopg2
import time
import json
from datetime import datetime
from psycopg2.extras import RealDictCursor, Json

# 远程数据库连接配置
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

def get_or_create_document():
    """获取或创建一个有效的document记录"""
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # 检查是否有现有文档
        cursor.execute("SELECT id FROM documents LIMIT 1")
        existing_doc = cursor.fetchone()
        
        if existing_doc:
            doc_id = existing_doc['id']
            print(f"   使用现有文档ID: {doc_id}")
        else:
            # 创建一个新的文档记录
            cursor.execute("""
                INSERT INTO documents (title, content, knowledge_base_id)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (
                "演示文档", 
                "这是一个演示文档，用于测试增强版文档管理系统", 
                1  # 假设knowledge_base_id为1
            ))
            
            doc_result = cursor.fetchone()
            doc_id = doc_result['id']
            print(f"   创建新文档ID: {doc_id}")
            conn.commit()
        
        cursor.close()
        conn.close()
        return doc_id
        
    except Exception as e:
        print(f"   ❌ 获取文档ID失败: {e}")
        # 如果失败，返回None，后续跳过document_chunks的插入
        return None

def create_compatible_demo_data():
    """创建兼容现有表结构的演示数据"""
    print("🎲 创建兼容的演示数据...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # 1. 创建测试文档到增强版注册表
        demo_file_id = "demo_file_" + str(int(time.time()))
        print(f"📄 创建测试文档: {demo_file_id}")
        
        cursor.execute("""
            INSERT INTO document_registry_enhanced 
            (file_id, filename, content_type, file_size, file_hash, storage_backend, 
             storage_path, kb_id, doc_id, user_id, chunk_count, vector_count, es_doc_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (file_hash) DO NOTHING
            RETURNING file_id
        """, (
            demo_file_id, "demo_document.pdf", "application/pdf", 1024000, 
            "demo_hash_" + str(int(time.time())), "minio", "/demo/path/demo_document.pdf",
            "demo_kb_001", "demo_doc_001", "demo_user_001", 3, 3, 3
        ))
        
        result = cursor.fetchone()
        if result:
            created_file_id = result['file_id']
            print(f"✅ 文档创建成功: {created_file_id}")
        else:
            print("ℹ️ 文档已存在（基于hash冲突检测）")
            created_file_id = demo_file_id
        
        # 2. 获取或创建有效的document ID
        print("🔗 处理document_chunks的外键约束...")
        document_id = get_or_create_document()
        
        # 3. 向现有的document_chunks表添加数据（使用现有结构）
        if document_id:
            print("🔪 向现有document_chunks表添加演示数据...")
            for i in range(3):
                # 使用Json包装器来正确处理JSONB数据
                metadata = Json({
                    "chunk_index": i,
                    "source_file": demo_file_id,
                    "chunk_type": "demo",
                    "created_at": datetime.now().isoformat()
                })
                
                cursor.execute("""
                    INSERT INTO document_chunks 
                    (document_id, content, metadata, embedding_id, token_count)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    document_id,  # 使用有效的document_id
                    f"这是演示文档的第{i+1}个切片内容...包含了重要的信息和知识点。这个切片包含了关于智政知识库系统的详细说明，展示了如何进行文档管理和向量搜索。",
                    metadata,
                    f"embedding_{i+1}_{int(time.time())}", 
                    200 + i*50
                ))
                
                chunk_result = cursor.fetchone()
                chunk_db_id = chunk_result['id']
                print(f"   ✅ 切片 {i+1} 创建成功，ID: {chunk_db_id}")
        else:
            print("⚠️ 跳过document_chunks插入（无法获取有效的document_id）")
        
        # 4. 创建增强版向量关联数据
        print("🧠 创建增强版向量关联数据...")
        for i in range(3):
            # 生成虚拟的chunk_id用于增强版表
            virtual_chunk_id = f"demo_chunk_{i+1}_{int(time.time())}"
            
            # 使用JSON字符串而不是字典
            vector_metadata = json.dumps({
                "chunk_index": i,
                "demo": True,
                "created_at": datetime.now().isoformat(),
                "embedding_model": "text-embedding-ada-002",
                "vector_source": "demo_creation"
            })
            
            cursor.execute("""
                INSERT INTO document_vectors_enhanced 
                (file_id, chunk_id, vector_id, vector_collection, embedding_model, embedding_dimension, vector_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                created_file_id, virtual_chunk_id, f"vector_{i+1}_{int(time.time())}", 
                "demo_collection", "text-embedding-ada-002", 1536, vector_metadata
            ))
            print(f"   ✅ 向量关联 {i+1} 创建成功")
        
        # 5. 创建ES分片关联数据
        print("🔍 创建ES分片关联数据...")
        for i in range(3):
            virtual_chunk_id = f"demo_chunk_{i+1}_{int(time.time())}"
            
            # 使用JSON字符串
            es_metadata = json.dumps({
                "chunk_index": i,
                "demo": True,
                "es_version": "8.x",
                "shard_info": f"shard_{i+1}",
                "created_at": datetime.now().isoformat()
            })
            
            cursor.execute("""
                INSERT INTO document_es_shards 
                (file_id, chunk_id, es_index, es_doc_id, es_shard_id, es_doc_type, es_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                created_file_id, virtual_chunk_id, "demo_index", f"es_doc_{i+1}_{int(time.time())}", 
                f"shard_{i+1}", "document", es_metadata
            ))
            print(f"   ✅ ES分片关联 {i+1} 创建成功")
        
        # 6. 创建处理历史记录
        print("📈 创建处理历史记录...")
        cursor.execute("""
            INSERT INTO document_processing_history 
            (file_id, operation_type, operation_status, operation_details, 
             started_at, completed_at, duration_ms, operated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            created_file_id, "demo_creation", "completed", 
            "演示数据创建完成 - 兼容现有表结构版本，包含JSON格式元数据，处理了外键约束", 
            datetime.now(), datetime.now(), 150, "system"
        ))
        print("   ✅ 处理历史记录创建成功")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n🎉 兼容演示数据创建成功!")
        print(f"📊 创建的数据:")
        print(f"   • 文档ID: {created_file_id}")
        if document_id:
            print(f"   • 3个文档切片（现有表结构，带JSONB元数据）")
        else:
            print(f"   • 文档切片创建跳过（外键约束问题）")
        print(f"   • 3个向量关联（增强版表）")
        print(f"   • 3个ES分片关联（增强版表）")
        print(f"   • 1个处理历史记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建演示数据失败: {e}")
        return False

def verify_demo_data():
    """验证演示数据"""
    print("\n🔍 验证演示数据...")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # 检查各表的数据量
        tables_to_check = [
            'document_registry_enhanced',
            'document_chunks', 
            'document_vectors_enhanced',
            'document_es_shards',
            'document_processing_history'
        ]
        
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"   📋 {table}: {count} 条记录")
        
        # 检查最新的演示数据
        cursor.execute("""
            SELECT file_id, filename, chunk_count, vector_count, es_doc_count 
            FROM document_registry_enhanced 
            WHERE filename = 'demo_document.pdf'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        demo_doc = cursor.fetchone()
        if demo_doc:
            print(f"\n📄 最新演示文档:")
            print(f"   • 文件ID: {demo_doc['file_id']}")
            print(f"   • 文件名: {demo_doc['filename']}")
            print(f"   • 切片数: {demo_doc['chunk_count']}")
            print(f"   • 向量数: {demo_doc['vector_count']}")
            print(f"   • ES文档数: {demo_doc['es_doc_count']}")
        
        # 检查document_chunks的JSONB数据
        cursor.execute("""
            SELECT id, metadata, token_count
            FROM document_chunks 
            WHERE metadata->>'chunk_type' = 'demo'
            ORDER BY id DESC 
            LIMIT 3
        """)
        
        demo_chunks = cursor.fetchall()
        if demo_chunks:
            print(f"\n🔪 演示切片数据:")
            for chunk in demo_chunks:
                print(f"   • 切片ID: {chunk['id']}, 令牌数: {chunk['token_count']}")
                print(f"     元数据: {chunk['metadata']}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 远程数据库演示数据修复工具")
    print("适配现有表结构，创建兼容的演示数据")
    print("="*60)
    
    # 创建演示数据
    if create_compatible_demo_data():
        # 验证数据
        verify_demo_data()
        
        print("\n✅ 演示数据修复完成!")
        print("💡 现在远程数据库已包含完整的演示数据，")
        print("   可以测试增强版文档管理功能。")
        print("\n🔧 下一步建议:")
        print("   1. 测试增强版文档管理器连接")
        print("   2. 验证混合搜索功能")
        print("   3. 运行完整系统测试")
        
        return True
    else:
        print("\n❌ 演示数据修复失败!")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        exit(1)
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        exit(1) 