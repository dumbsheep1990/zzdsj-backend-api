#!/usr/bin/env python3
"""
简化的PostgreSQL连接和权限测试脚本
"""

import psycopg2
import sys
from datetime import datetime

# 远程数据库连接配置
REMOTE_DB_CONFIG = {
    'host': '167.71.85.231',
    'port': 5432,
    'user': 'zzdsj',
    'password': 'zzdsj123',
    'database': 'zzdsj'
}

def print_step(step: str, status: str = "INFO"):
    """打印步骤信息"""
    icons = {"INFO": "📋", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(status, "📋")
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {icon} {step}")

def test_connection_and_permissions():
    """测试连接和权限"""
    print("=" * 60)
    print("🔗 PostgreSQL连接和权限测试")
    print("=" * 60)
    
    try:
        # 连接数据库
        print_step("正在连接远程PostgreSQL数据库...")
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 基本信息
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print_step(f"数据库版本: {version}", "SUCCESS")
        
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print_step(f"数据库: {db_info[0]}, 用户: {db_info[1]}", "SUCCESS")
        
        # 检查各种权限
        print_step("检查用户权限...", "INFO")
        
        # 检查数据库级别权限
        cursor.execute("""
            SELECT 
                datname,
                has_database_privilege(current_user, datname, 'CREATE') as can_create,
                has_database_privilege(current_user, datname, 'CONNECT') as can_connect,
                has_database_privilege(current_user, datname, 'TEMPORARY') as can_temp
            FROM pg_database 
            WHERE datname = current_database();
        """)
        db_perms = cursor.fetchone()
        print_step(f"CREATE权限: {db_perms[1]}", "SUCCESS" if db_perms[1] else "ERROR")
        print_step(f"CONNECT权限: {db_perms[2]}", "SUCCESS" if db_perms[2] else "ERROR")
        print_step(f"TEMPORARY权限: {db_perms[3]}", "SUCCESS" if db_perms[3] else "WARNING")
        
        # 检查schema权限
        cursor.execute("""
            SELECT 
                has_schema_privilege(current_user, 'public', 'CREATE') as can_create_in_public,
                has_schema_privilege(current_user, 'public', 'USAGE') as can_use_public
        """)
        schema_perms = cursor.fetchone()
        print_step(f"PUBLIC schema CREATE权限: {schema_perms[0]}", "SUCCESS" if schema_perms[0] else "ERROR")
        print_step(f"PUBLIC schema USAGE权限: {schema_perms[1]}", "SUCCESS" if schema_perms[1] else "ERROR")
        
        # 尝试创建一个测试表
        print_step("测试CREATE TABLE权限...", "INFO")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_table_permissions (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print_step("CREATE TABLE权限测试成功！", "SUCCESS")
            
            # 尝试插入数据
            cursor.execute("INSERT INTO test_table_permissions (name) VALUES ('test');")
            print_step("INSERT权限测试成功！", "SUCCESS")
            
            # 尝试查询数据
            cursor.execute("SELECT COUNT(*) FROM test_table_permissions;")
            count = cursor.fetchone()[0]
            print_step(f"SELECT权限测试成功！表中有 {count} 条记录", "SUCCESS")
            
            # 清理测试表
            cursor.execute("DROP TABLE test_table_permissions;")
            print_step("DROP TABLE权限测试成功！", "SUCCESS")
            
        except psycopg2.Error as e:
            print_step(f"CREATE TABLE权限测试失败: {e}", "ERROR")
            return False
        
        # 检查现有表
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        table_count = cursor.fetchone()[0]
        print_step(f"当前public schema中有 {table_count} 个表", "INFO")
        
        # 检查用户角色
        cursor.execute("""
            SELECT 
                r.rolname as role_name,
                r.rolsuper as is_superuser,
                r.rolcreaterole as can_create_role,
                r.rolcreatedb as can_create_db
            FROM pg_roles r 
            WHERE r.rolname = current_user;
        """)
        role_info = cursor.fetchone()
        if role_info:
            print_step(f"用户角色: {role_info[0]}", "INFO")
            print_step(f"超级用户: {role_info[1]}", "SUCCESS" if role_info[1] else "INFO")
            print_step(f"可创建角色: {role_info[2]}", "SUCCESS" if role_info[2] else "INFO")
            print_step(f"可创建数据库: {role_info[3]}", "SUCCESS" if role_info[3] else "INFO")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_step("数据库连接和权限测试完成！", "SUCCESS")
        return True
        
    except psycopg2.Error as e:
        print_step(f"数据库连接失败: {e}", "ERROR")
        return False
    except Exception as e:
        print_step(f"测试过程异常: {e}", "ERROR")
        return False

if __name__ == "__main__":
    success = test_connection_and_permissions()
    if success:
        print("\n🎉 连接和权限测试成功！可以继续执行数据库初始化。")
    else:
        print("\n❌ 连接或权限测试失败！请检查数据库配置和用户权限。")
    
    sys.exit(0 if success else 1) 