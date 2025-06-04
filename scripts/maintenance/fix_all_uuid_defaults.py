#!/usr/bin/env python3
"""
修复所有表的UUID默认值问题
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

def find_uuid_columns():
    """查找所有需要UUID默认值的列"""
    print_header("查找需要UUID默认值的列")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 查找所有VARCHAR(36)类型且名为id的主键列（通常是UUID列）
        cursor.execute("""
            SELECT 
                t.table_name,
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.column_default,
                c.is_nullable
            FROM information_schema.tables t
            JOIN information_schema.columns c ON t.table_name = c.table_name
            WHERE t.table_schema = 'public'
            AND c.column_name = 'id'
            AND c.data_type = 'character varying'
            AND c.character_maximum_length = 36
            ORDER BY t.table_name;
        """)
        
        uuid_columns = cursor.fetchall()
        
        print_step(f"找到 {len(uuid_columns)} 个潜在的UUID列:", "INFO")
        for table, column, dtype, length, default, nullable in uuid_columns:
            default_info = f" DEFAULT: {default}" if default else " NO DEFAULT"
            print(f"    {table}.{column} ({dtype}({length})){default_info}")
        
        cursor.close()
        conn.close()
        return uuid_columns
        
    except Exception as e:
        print_step(f"查找UUID列失败: {e}", "ERROR")
        return []

def fix_table_uuid_default(table_name, column_name):
    """修复单个表的UUID默认值"""
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 修改列的默认值
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ALTER COLUMN {column_name} SET DEFAULT uuid_generate_v4();
        """)
        
        print_step(f"修复 {table_name}.{column_name} 默认值", "SUCCESS")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"修复 {table_name}.{column_name} 失败: {e}", "ERROR")
        return False

def fix_all_uuid_defaults():
    """修复所有UUID默认值"""
    print_header("修复所有UUID默认值")
    
    uuid_columns = find_uuid_columns()
    if not uuid_columns:
        print_step("没有找到需要修复的UUID列", "WARNING")
        return True
    
    success_count = 0
    total_count = len(uuid_columns)
    
    for table, column, dtype, length, default, nullable in uuid_columns:
        if default and 'uuid_generate_v4' in default:
            print_step(f"{table}.{column} 已有正确默认值", "INFO")
            success_count += 1
        else:
            if fix_table_uuid_default(table, column):
                success_count += 1
    
    print_step(f"成功修复 {success_count}/{total_count} 个UUID列", 
               "SUCCESS" if success_count == total_count else "WARNING")
    
    return success_count == total_count

def test_uuid_generation():
    """测试UUID生成功能"""
    print_header("测试UUID生成功能")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 测试users表
        cursor.execute("DELETE FROM users WHERE username = 'test_uuid_user';")
        cursor.execute("""
            INSERT INTO users (username, email, hashed_password, full_name)
            VALUES ('test_uuid_user', 'test_uuid@example.com', 'test_password', '测试UUID用户')
            RETURNING id;
        """)
        user_id = cursor.fetchone()[0]
        print_step(f"users表UUID生成测试成功: {user_id}", "SUCCESS")
        
        # 测试roles表
        cursor.execute("DELETE FROM roles WHERE name = 'test_uuid_role';")
        cursor.execute("""
            INSERT INTO roles (name, description)
            VALUES ('test_uuid_role', '测试UUID角色')
            RETURNING id;
        """)
        role_id = cursor.fetchone()[0]
        print_step(f"roles表UUID生成测试成功: {role_id}", "SUCCESS")
        
        # 清理测试数据
        cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
        cursor.execute("DELETE FROM roles WHERE id = %s;", (role_id,))
        print_step("测试数据已清理", "SUCCESS")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"UUID生成测试失败: {e}", "ERROR")
        return False

def create_admin_data():
    """创建管理员数据（用户、角色、权限）"""
    print_header("创建管理员数据")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. 创建管理员用户（如果不存在）
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin';")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO users (username, email, hashed_password, full_name, is_superuser)
                VALUES ('admin', 'admin@zzdsj.com', '$2b$12$LQv3c1yqBo69SFqjfUmNnuebNZr8cCsVIIuQ1y.U9VC.ExnQd7CtO', '系统管理员', true)
                RETURNING id;
            """)
            admin_user_id = cursor.fetchone()[0]
            print_step(f"创建管理员用户成功: {admin_user_id}", "SUCCESS")
        else:
            cursor.execute("SELECT id FROM users WHERE username = 'admin';")
            admin_user_id = cursor.fetchone()[0]
            print_step(f"管理员用户已存在: {admin_user_id}", "INFO")
        
        # 2. 创建管理员角色（如果不存在）
        cursor.execute("SELECT COUNT(*) FROM roles WHERE name = 'admin';")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO roles (name, description, is_system)
                VALUES ('admin', '系统管理员角色', true)
                RETURNING id;
            """)
            admin_role_id = cursor.fetchone()[0]
            print_step(f"创建管理员角色成功: {admin_role_id}", "SUCCESS")
        else:
            cursor.execute("SELECT id FROM roles WHERE name = 'admin';")
            admin_role_id = cursor.fetchone()[0]
            print_step(f"管理员角色已存在: {admin_role_id}", "INFO")
        
        # 3. 创建基础权限
        permissions = [
            ('user_management', '用户管理', '管理系统用户'),
            ('role_management', '角色管理', '管理系统角色'),
            ('permission_management', '权限管理', '管理系统权限'),
            ('knowledge_base_management', '知识库管理', '管理知识库'),
            ('system_config', '系统配置', '配置系统参数'),
            ('assistant_management', '助手管理', '管理AI助手'),
            ('tool_management', '工具管理', '管理系统工具')
        ]
        
        permission_ids = []
        for code, name, desc in permissions:
            cursor.execute("SELECT COUNT(*) FROM permissions WHERE code = %s;", (code,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO permissions (code, name, description, category)
                    VALUES (%s, %s, %s, 'system')
                    RETURNING id;
                """, (code, name, desc))
                perm_id = cursor.fetchone()[0]
                permission_ids.append(perm_id)
                print_step(f"创建权限 {name} 成功", "SUCCESS")
            else:
                cursor.execute("SELECT id FROM permissions WHERE code = %s;", (code,))
                perm_id = cursor.fetchone()[0]
                permission_ids.append(perm_id)
        
        # 4. 关联用户和角色
        cursor.execute("""
            INSERT INTO user_role (user_id, role_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """, (admin_user_id, admin_role_id))
        print_step("用户角色关联成功", "SUCCESS")
        
        # 5. 关联角色和权限
        for perm_id in permission_ids:
            cursor.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
            """, (admin_role_id, perm_id))
        print_step(f"角色权限关联成功 ({len(permission_ids)}个权限)", "SUCCESS")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"创建管理员数据失败: {e}", "ERROR")
        return False

def final_database_status():
    """最终数据库状态检查"""
    print_header("最终数据库状态检查")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 统计信息
        stats = {}
        
        # 表数量
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        stats['tables'] = cursor.fetchone()[0]
        
        # 用户数量
        cursor.execute("SELECT COUNT(*) FROM users;")
        stats['users'] = cursor.fetchone()[0]
        
        # 角色数量
        cursor.execute("SELECT COUNT(*) FROM roles;")
        stats['roles'] = cursor.fetchone()[0]
        
        # 权限数量
        cursor.execute("SELECT COUNT(*) FROM permissions;")
        stats['permissions'] = cursor.fetchone()[0]
        
        # 知识库数量
        cursor.execute("SELECT COUNT(*) FROM knowledge_bases;")
        stats['knowledge_bases'] = cursor.fetchone()[0]
        
        print_step("📊 数据库统计:", "INFO")
        for key, value in stats.items():
            print(f"    {key}: {value}")
        
        # 检查管理员用户
        cursor.execute("""
            SELECT u.username, u.email, u.is_superuser, r.name as role_name
            FROM users u
            LEFT JOIN user_role ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.username = 'admin';
        """)
        admin_info = cursor.fetchone()
        if admin_info:
            username, email, is_super, role_name = admin_info
            print_step(f"✅ 管理员用户: {username} ({email})", "SUCCESS")
            print_step(f"  超级用户: {is_super}, 角色: {role_name}", "INFO")
        else:
            print_step("❌ 未找到管理员用户", "ERROR")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"状态检查失败: {e}", "ERROR")
        return False

def main():
    """主修复流程"""
    print_header("完整的UUID默认值修复工具")
    
    print("🎯 此工具将：")
    print("  • 修复所有表的UUID默认值")
    print("  • 测试UUID生成功能")
    print("  • 创建完整的管理员数据")
    print("  • 验证数据库状态")
    
    # 步骤1: 修复所有UUID默认值
    if not fix_all_uuid_defaults():
        print_step("UUID默认值修复失败，继续尝试其他步骤", "WARNING")
    
    # 步骤2: 测试UUID生成
    if not test_uuid_generation():
        print_step("UUID生成测试失败", "ERROR")
        return False
    
    # 步骤3: 创建管理员数据
    if not create_admin_data():
        print_step("管理员数据创建失败", "ERROR")
        return False
    
    # 步骤4: 最终状态检查
    if not final_database_status():
        return False
    
    print_step("🎉 数据库完整初始化成功！", "SUCCESS")
    print_step("默认管理员账号: admin / admin123", "INFO")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 