#!/usr/bin/env python3
"""
PostgreSQL权限设置和测试脚本
"""

import psycopg2
import sys
from datetime import datetime

def print_step(step: str, status: str = "INFO"):
    """打印步骤信息"""
    icons = {"INFO": "📋", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(status, "📋")
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {icon} {step}")

def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def setup_permissions_with_admin():
    """使用管理员权限设置用户权限"""
    print_header("使用管理员权限设置用户权限")
    
    # 尝试使用postgres超级用户
    admin_configs = [
        {
            'host': '167.71.85.231',
            'port': 5432,
            'user': 'postgres',  # 尝试使用postgres超级用户
            'password': input("请输入postgres用户密码: ").strip(),
            'database': 'zzdsj'
        }
    ]
    
    # 也可以尝试其他管理员用户
    other_admin = input("如果有其他管理员用户，请输入用户名（留空跳过）: ").strip()
    if other_admin:
        admin_password = input(f"请输入{other_admin}用户密码: ").strip()
        admin_configs.append({
            'host': '167.71.85.231',
            'port': 5432,
            'user': other_admin,
            'password': admin_password,
            'database': 'zzdsj'
        })
    
    for config in admin_configs:
        try:
            print_step(f"尝试使用 {config['user']} 用户连接...")
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            print_step(f"成功连接为 {config['user']} 用户", "SUCCESS")
            
            # 执行权限授予命令
            permissions_sql = [
                "GRANT CREATE ON DATABASE zzdsj TO zzdsj;",
                "GRANT CONNECT ON DATABASE zzdsj TO zzdsj;", 
                "GRANT TEMPORARY ON DATABASE zzdsj TO zzdsj;",
                "GRANT CREATE ON SCHEMA public TO zzdsj;",
                "GRANT USAGE ON SCHEMA public TO zzdsj;",
                "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO zzdsj;",
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO zzdsj;",
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zzdsj;",
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zzdsj;",
                "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO zzdsj;",
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO zzdsj;"
            ]
            
            print_step("开始授予权限...")
            for sql in permissions_sql:
                try:
                    cursor.execute(sql)
                    print_step(f"执行成功: {sql[:50]}...", "SUCCESS")
                except psycopg2.Error as e:
                    print_step(f"执行失败: {str(e)[:100]}...", "WARNING")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print_step("权限授予完成！", "SUCCESS")
            return True
            
        except psycopg2.Error as e:
            print_step(f"使用 {config['user']} 连接失败: {e}", "ERROR")
            continue
        except Exception as e:
            print_step(f"授予权限异常: {e}", "ERROR")
            continue
    
    return False

def test_zzdsj_permissions():
    """测试zzdsj用户权限"""
    print_header("测试zzdsj用户权限")
    
    config = {
        'host': '167.71.85.231',
        'port': 5432,
        'user': 'zzdsj',
        'password': 'zzdsj123',
        'database': 'zzdsj'
    }
    
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        print_step("zzdsj用户连接成功", "SUCCESS")
        
        # 检查权限
        cursor.execute("""
            SELECT 
                has_database_privilege('zzdsj', 'zzdsj', 'CREATE') as db_create,
                has_schema_privilege('zzdsj', 'public', 'CREATE') as schema_create
        """)
        perms = cursor.fetchone()
        
        print_step(f"数据库CREATE权限: {perms[0]}", "SUCCESS" if perms[0] else "ERROR")
        print_step(f"Schema CREATE权限: {perms[1]}", "SUCCESS" if perms[1] else "ERROR")
        
        if perms[0] and perms[1]:
            # 测试创建表
            print_step("测试创建表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS permission_test (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print_step("创建表成功！", "SUCCESS")
            
            cursor.execute("INSERT INTO permission_test (name) VALUES ('权限测试');")
            print_step("插入数据成功！", "SUCCESS")
            
            cursor.execute("SELECT COUNT(*) FROM permission_test;")
            count = cursor.fetchone()[0]
            print_step(f"查询数据成功！共 {count} 条记录", "SUCCESS")
            
            cursor.execute("DROP TABLE permission_test;")
            print_step("删除表成功！", "SUCCESS")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print_step("权限测试完全通过！", "SUCCESS")
            return True
        else:
            cursor.close()
            conn.close()
            return False
            
    except psycopg2.Error as e:
        print_step(f"权限测试失败: {e}", "ERROR")
        return False

def main():
    """主函数"""
    print_header("PostgreSQL权限设置向导")
    
    print("此脚本将帮助您为zzdsj用户设置必要的数据库权限。")
    print("需要使用具有管理员权限的用户（如postgres）来授予权限。")
    
    # 首先测试当前权限
    print_step("首先测试zzdsj用户当前权限...")
    if test_zzdsj_permissions():
        print_step("zzdsj用户权限已经正确配置！", "SUCCESS")
        return True
    
    # 如果权限不足，尝试设置权限
    print_step("权限不足，需要使用管理员权限设置", "WARNING")
    
    choice = input("\n是否使用管理员账户授予权限？(y/N): ").strip().lower()
    if choice not in ['y', 'yes', '是']:
        print_step("用户选择不设置权限", "INFO")
        print("\n手动设置权限的方法：")
        print("1. 使用postgres或其他超级用户连接到数据库")
        print("2. 执行以下SQL命令：")
        print("   GRANT CREATE ON DATABASE zzdsj TO zzdsj;")
        print("   GRANT CREATE ON SCHEMA public TO zzdsj;")
        print("   GRANT USAGE ON SCHEMA public TO zzdsj;")
        return False
    
    # 设置权限
    if setup_permissions_with_admin():
        print_step("权限设置完成，重新测试...", "INFO")
        if test_zzdsj_permissions():
            print_step("🎉 权限设置成功！可以继续数据库初始化。", "SUCCESS")
            return True
        else:
            print_step("权限设置后测试仍失败", "ERROR")
            return False
    else:
        print_step("权限设置失败", "ERROR")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 