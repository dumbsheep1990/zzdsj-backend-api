#!/usr/bin/env python3
"""
快速检查数据库初始化进度
"""

import psycopg2
from datetime import datetime

# 远程数据库连接配置
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

def check_progress():
    """检查数据库表创建进度"""
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 查询表数量
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        table_count = cursor.fetchone()[0]
        
        # 查询表名
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # 统计记录数
        total_records = 0
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                total_records += count
            except:
                pass
        
        cursor.close()
        conn.close()
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 📊 数据库状态:")
        print(f"  📋 表数量: {table_count}")
        print(f"  📝 总记录数: {total_records}")
        
        if table_count > 0:
            print(f"  📂 已创建的表:")
            for i, table in enumerate(tables, 1):
                print(f"    {i:2}. {table}")
        
        return table_count, total_records
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return 0, 0

if __name__ == "__main__":
    check_progress() 