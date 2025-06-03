#!/usr/bin/env python3
"""
远程PostgreSQL数据库连接测试和初始化脚本
测试连接到远程服务器并执行完整的数据库初始化
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
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            if count > 0:
                print_step(f"表 '{table}' 包含 {count} 行数据", "INFO")
                total_rows += count
        
        print_step(f"数据库总记录数: {total_rows}", "INFO")
        
        cursor.close()
        conn.close()
        
        return len(tables)
        
    except psycopg2.Error as e:
        print_step(f"检查表结构失败: {e}", "ERROR")
        return -1

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
        role_id = str(uuid.uuid4())
        role_sql = """
            INSERT INTO roles (id, name, description, is_default)
            VALUES (%s, 'admin', '系统管理员角色', false)
            ON CONFLICT (name) DO NOTHING;
        """
        cursor.execute(role_sql, (role_id,))
        
        # 创建基础权限
        permissions = [
            ('user_management', '用户管理', '管理系统用户'),
            ('knowledge_base_management', '知识库管理', '管理知识库'),
            ('system_config', '系统配置', '配置系统参数')
        ]
        
        for code, name, desc in permissions:
            perm_id = str(uuid.uuid4())
            perm_sql = """
                INSERT INTO permissions (id, code, name, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (code) DO NOTHING;
            """
            cursor.execute(perm_sql, (perm_id, code, name, desc))
        
        # 创建配置类别
        categories = [
            ('system', '系统配置', '基础系统配置'),
            ('ai_models', 'AI模型', 'AI模型相关配置'),
            ('storage', '存储配置', '文件和数据存储配置')
        ]
        
        for code, name, desc in categories:
            cat_id = str(uuid.uuid4())
            cat_sql = """
                INSERT INTO config_categories (id, name, description, is_system)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (name) DO NOTHING;
            """
            cursor.execute(cat_sql, (cat_id, name, desc))
        
        # 创建默认知识库
        kb_sql = """
            INSERT INTO knowledge_bases (name, description, type)
            VALUES ('默认知识库', '系统默认知识库', 'default')
            ON CONFLICT DO NOTHING;
        """
        cursor.execute(kb_sql)
        
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
            'users', 'roles', 'permissions', 'knowledge_bases', 
            'documents', 'assistants', 'system_configs', 'model_providers'
        ]
        
        missing_tables = []
        existing_tables = []
        
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
        
        print_step(f"关键表检查: {len(existing_tables)}/{len(required_tables)} 存在", 
                  "SUCCESS" if not missing_tables else "WARNING")
        
        if missing_tables:
            print_step(f"缺失表: {', '.join(missing_tables)}", "WARNING")
        
        # 检查数据完整性
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_superuser = true;")
        admin_count = cursor.fetchone()[0]
        print_step(f"管理员用户数: {admin_count}", "SUCCESS" if admin_count > 0 else "WARNING")
        
        cursor.execute("SELECT COUNT(*) FROM roles;")
        role_count = cursor.fetchone()[0]
        print_step(f"系统角色数: {role_count}", "INFO")
        
        cursor.execute("SELECT COUNT(*) FROM permissions;")
        perm_count = cursor.fetchone()[0]
        print_step(f"系统权限数: {perm_count}", "INFO")
        
        cursor.execute("SELECT COUNT(*) FROM knowledge_bases;")
        kb_count = cursor.fetchone()[0]
        print_step(f"知识库数: {kb_count}", "INFO")
        
        cursor.close()
        conn.close()
        
        success = len(missing_tables) == 0 and admin_count > 0
        print_step("数据库验证完成！", "SUCCESS" if success else "WARNING")
        return success
        
    except psycopg2.Error as e:
        print_step(f"验证安装失败: {e}", "ERROR")
        return False

def main():
    """主函数"""
    print_header("远程PostgreSQL数据库连接测试和初始化")
    
    print("🎯 目标服务器信息:")
    print(f"  📍 地址: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")
    print(f"  👤 用户: {REMOTE_DB_CONFIG['user']}")
    print(f"  🗄️  数据库: {REMOTE_DB_CONFIG['database']}")
    
    # 步骤1: 测试连接
    if not test_connection():
        print_step("连接测试失败，请检查网络和配置", "ERROR")
        return False
    
    # 步骤2: 检查现有表
    table_count = check_existing_tables()
    if table_count == -1:
        print_step("无法检查现有表结构", "ERROR")
        return False
    
    # 步骤3: 执行数据库初始化
    sql_file_path = "database_complete.sql"
    if not os.path.exists(sql_file_path):
        print_step(f"未找到数据库初始化文件: {sql_file_path}", "ERROR")
        print_step("请确保在项目根目录下运行此脚本", "INFO")
        return False
    
    if not execute_sql_file(sql_file_path, confirm_required=True):
        print_step("数据库初始化失败", "ERROR")
        return False
    
    # 步骤4: 创建测试数据
    if not create_test_data():
        print_step("创建测试数据失败", "WARNING")
    
    # 步骤5: 验证安装
    if not verify_installation():
        print_step("数据库验证失败", "WARNING")
        return False
    
    # 成功完成
    print_header("数据库初始化完成")
    print_step("🎉 远程PostgreSQL数据库初始化成功！", "SUCCESS")
    print_step("📋 后续步骤:", "INFO")
    print("  1. 配置应用程序的数据库连接")
    print("  2. 测试应用程序连接到远程数据库")
    print("  3. 根据需要创建更多用户和配置")
    
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