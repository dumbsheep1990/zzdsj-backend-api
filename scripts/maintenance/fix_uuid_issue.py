#!/usr/bin/env python3
"""
修复UUID函数类型问题的脚本
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

def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def fix_uuid_function():
    """修复UUID函数类型问题"""
    print_header("修复UUID函数类型问题")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 删除现有的uuid_generate_v4函数
        cursor.execute("DROP FUNCTION IF EXISTS uuid_generate_v4();")
        print_step("删除现有uuid_generate_v4函数", "SUCCESS")
        
        # 创建新的uuid_generate_v4函数，返回TEXT类型
        cursor.execute("""
            CREATE OR REPLACE FUNCTION uuid_generate_v4() 
            RETURNS TEXT 
            LANGUAGE sql 
            AS $$ SELECT gen_random_uuid()::text; $$;
        """)
        print_step("创建新的uuid_generate_v4函数（返回TEXT）", "SUCCESS")
        
        # 测试函数
        cursor.execute("SELECT uuid_generate_v4();")
        test_uuid = cursor.fetchone()[0]
        print_step(f"函数测试成功，生成UUID: {test_uuid}", "SUCCESS")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"修复UUID函数失败: {e}", "ERROR")
        return False

def check_users_table_structure():
    """检查users表结构"""
    print_header("检查users表结构")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 查询users表结构
        cursor.execute("""
            SELECT column_name, data_type, column_default, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        print_step("users表结构:", "INFO")
        for col_name, data_type, default, nullable in columns:
            default_info = f" DEFAULT: {default}" if default else ""
            nullable_info = f" NULLABLE: {nullable}" if nullable == 'YES' else " NOT NULL"
            print(f"    {col_name}: {data_type}{default_info}{nullable_info}")
        
        # 检查是否有默认值设置
        cursor.execute("""
            SELECT column_default 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'id';
        """)
        id_default = cursor.fetchone()[0]
        print_step(f"id字段默认值: {id_default}", "INFO")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"检查表结构失败: {e}", "ERROR")
        return False

def fix_users_table_default():
    """修复users表的默认值"""
    print_header("修复users表默认值")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 修改id字段的默认值
        cursor.execute("""
            ALTER TABLE users 
            ALTER COLUMN id SET DEFAULT uuid_generate_v4();
        """)
        print_step("修复users表id字段默认值", "SUCCESS")
        
        # 验证修改
        cursor.execute("""
            SELECT column_default 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'id';
        """)
        new_default = cursor.fetchone()[0]
        print_step(f"新的默认值: {new_default}", "INFO")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"修复默认值失败: {e}", "ERROR")
        return False

def test_user_creation():
    """测试用户创建"""
    print_header("测试用户创建")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 删除可能存在的测试用户
        cursor.execute("DELETE FROM users WHERE username = 'test_user';")
        
        # 创建测试用户（不指定id，使用默认值）
        cursor.execute("""
            INSERT INTO users (username, email, hashed_password, full_name)
            VALUES ('test_user', 'test@example.com', 'test_password', '测试用户')
            RETURNING id;
        """)
        user_id = cursor.fetchone()[0]
        print_step(f"测试用户创建成功，ID: {user_id}", "SUCCESS")
        
        # 删除测试用户
        cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
        print_step("测试用户已删除", "SUCCESS")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"测试用户创建失败: {e}", "ERROR")
        return False

def insert_admin_user():
    """插入管理员用户"""
    print_header("插入管理员用户")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查是否已存在admin用户
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin';")
        admin_count = cursor.fetchone()[0]
        
        if admin_count > 0:
            print_step("admin用户已存在", "INFO")
            return True
        
        # 插入管理员用户
        cursor.execute("""
            INSERT INTO users (username, email, hashed_password, full_name, is_superuser)
            VALUES ('admin', 'admin@zzdsj.com', '$2b$12$LQv3c1yqBo69SFqjfUmNnuebNZr8cCsVIIuQ1y.U9VC.ExnQd7CtO', '系统管理员', true)
            RETURNING id;
        """)
        admin_id = cursor.fetchone()[0]
        print_step(f"管理员用户创建成功，ID: {admin_id}", "SUCCESS")
        
        # 插入默认角色
        cursor.execute("""
            INSERT INTO roles (name, description, is_system)
            VALUES ('admin', '系统管理员角色', true)
            ON CONFLICT (name) DO NOTHING
            RETURNING id;
        """)
        
        role_result = cursor.fetchone()
        if role_result:
            role_id = role_result[0]
            print_step(f"管理员角色创建成功，ID: {role_id}", "SUCCESS")
            
            # 关联用户和角色
            cursor.execute("""
                INSERT INTO user_role (user_id, role_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
            """, (admin_id, role_id))
            print_step("用户角色关联成功", "SUCCESS")
        else:
            print_step("管理员角色已存在", "INFO")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"插入管理员用户失败: {e}", "ERROR")
        return False

def final_verification():
    """最终验证"""
    print_header("最终验证")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查用户数量
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        print_step(f"用户数量: {user_count}", "SUCCESS" if user_count > 0 else "WARNING")
        
        # 检查管理员用户
        cursor.execute("SELECT username, email, is_superuser FROM users WHERE username = 'admin';")
        admin_info = cursor.fetchone()
        if admin_info:
            username, email, is_super = admin_info
            print_step(f"管理员用户: {username} ({email}) - 超级用户: {is_super}", "SUCCESS")
        else:
            print_step("未找到管理员用户", "WARNING")
        
        # 检查表数量
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        table_count = cursor.fetchone()[0]
        print_step(f"数据库表数量: {table_count}", "SUCCESS")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"最终验证失败: {e}", "ERROR")
        return False

def main():
    """主修复流程"""
    print_header("UUID函数修复工具")
    
    print("🎯 此工具将修复UUID函数类型问题并创建管理员用户")
    
    # 步骤1: 修复UUID函数
    if not fix_uuid_function():
        return False
    
    # 步骤2: 检查users表结构
    if not check_users_table_structure():
        return False
    
    # 步骤3: 修复users表默认值
    if not fix_users_table_default():
        return False
    
    # 步骤4: 测试用户创建
    if not test_user_creation():
        return False
    
    # 步骤5: 插入管理员用户
    if not insert_admin_user():
        return False
    
    # 步骤6: 最终验证
    if not final_verification():
        return False
    
    print_step("🎉 数据库修复完成！", "SUCCESS")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 