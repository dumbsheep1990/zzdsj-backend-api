#!/usr/bin/env python3
"""
检查远程数据库表结构的脚本
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# 远程数据库连接配置
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

def check_table_structure(table_name):
    """检查指定表的结构"""
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        print(f'🔍 检查 {table_name} 表结构...')
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = cursor.fetchall()
        print(f'📋 {table_name} 表有 {len(columns)} 个字段:')
        for col in columns:
            nullable = '可空' if col['is_nullable'] == 'YES' else '不可空'
            default = f" (默认: {col['column_default']})" if col['column_default'] else ''
            print(f'   • {col["column_name"]}: {col["data_type"]} - {nullable}{default}')
        
        cursor.close()
        conn.close()
        
        return columns
        
    except Exception as e:
        print(f'❌ 检查 {table_name} 失败: {e}')
        return []

def main():
    """主函数"""
    print("🚀 远程数据库表结构检查工具")
    print("="*50)
    
    # 检查相关表的结构
    tables_to_check = [
        'document_chunks',
        'document_registry_enhanced',
        'document_vectors_enhanced',
        'document_es_shards',
        'document_processing_history'
    ]
    
    for table in tables_to_check:
        print()
        columns = check_table_structure(table)
        if not columns:
            print(f'⚠️ 表 {table} 不存在或无法访问')

if __name__ == "__main__":
    main() 