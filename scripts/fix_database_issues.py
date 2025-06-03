#!/usr/bin/env python3
"""
修复数据库初始化问题的脚本
主要解决UUID扩展和表创建问题
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

def check_extensions():
    """检查可用的UUID扩展"""
    print_header("检查UUID扩展支持")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查当前已安装的扩展
        cursor.execute("SELECT extname FROM pg_extension;")
        installed_extensions = [row[0] for row in cursor.fetchall()]
        print_step(f"已安装扩展: {', '.join(installed_extensions)}", "INFO")
        
        # 检查可用的扩展
        cursor.execute("SELECT name FROM pg_available_extensions WHERE name LIKE '%uuid%';")
        available_uuid_extensions = [row[0] for row in cursor.fetchall()]
        print_step(f"可用UUID扩展: {', '.join(available_uuid_extensions)}", "INFO")
        
        # 检查是否有gen_random_uuid函数（PostgreSQL 13+内置）
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc 
                WHERE proname = 'gen_random_uuid'
            );
        """)
        has_gen_random_uuid = cursor.fetchone()[0]
        print_step(f"gen_random_uuid函数可用: {has_gen_random_uuid}", "SUCCESS" if has_gen_random_uuid else "WARNING")
        
        cursor.close()
        conn.close()
        
        return {
            'installed': installed_extensions,
            'available_uuid': available_uuid_extensions,
            'has_gen_random_uuid': has_gen_random_uuid
        }
        
    except Exception as e:
        print_step(f"检查扩展失败: {e}", "ERROR")
        return None

def try_install_uuid_extension():
    """尝试安装UUID扩展"""
    print_header("尝试安装UUID扩展")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 尝试安装pgcrypto（通常包含gen_random_uuid）
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            print_step("pgcrypto扩展安装成功", "SUCCESS")
            conn.commit()
        except psycopg2.Error as e:
            print_step(f"pgcrypto安装失败: {e}", "WARNING")
        
        # 尝试安装uuid-ossp
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
            print_step("uuid-ossp扩展安装成功", "SUCCESS")
            conn.commit()
        except psycopg2.Error as e:
            print_step(f"uuid-ossp安装失败: {e}", "WARNING")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"安装扩展异常: {e}", "ERROR")
        return False

def create_uuid_function():
    """创建UUID生成函数"""
    print_header("创建UUID生成函数")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 检查是否已有uuid_generate_v4函数
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc 
                WHERE proname = 'uuid_generate_v4'
            );
        """)
        has_uuid_v4 = cursor.fetchone()[0]
        
        if has_uuid_v4:
            print_step("uuid_generate_v4函数已存在", "SUCCESS")
        else:
            # 检查是否有gen_random_uuid
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_proc 
                    WHERE proname = 'gen_random_uuid'
                );
            """)
            has_gen_random = cursor.fetchone()[0]
            
            if has_gen_random:
                # 创建uuid_generate_v4作为gen_random_uuid的别名
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION uuid_generate_v4() 
                    RETURNS uuid 
                    LANGUAGE sql 
                    AS $$ SELECT gen_random_uuid(); $$;
                """)
                print_step("使用gen_random_uuid创建uuid_generate_v4函数", "SUCCESS")
            else:
                # 使用纯SQL实现简单的UUID生成
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION uuid_generate_v4() 
                    RETURNS varchar(36) 
                    LANGUAGE sql 
                    AS $$
                        SELECT 
                            substr(md5(random()::text || clock_timestamp()::text), 1, 8) || '-' ||
                            substr(md5(random()::text || clock_timestamp()::text), 1, 4) || '-' ||
                            '4' || substr(md5(random()::text || clock_timestamp()::text), 1, 3) || '-' ||
                            ('89ab'::text)[floor(random() * 4 + 1)::int] || substr(md5(random()::text || clock_timestamp()::text), 1, 3) || '-' ||
                            substr(md5(random()::text || clock_timestamp()::text), 1, 12);
                    $$;
                """)
                print_step("创建自定义uuid_generate_v4函数", "SUCCESS")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print_step(f"创建UUID函数失败: {e}", "ERROR")
        return False

def check_missing_tables():
    """检查缺失的表"""
    print_header("检查缺失的关键表")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 期望的关键表列表
        expected_tables = [
            'users', 'roles', 'permissions', 'user_role', 'role_permissions',
            'knowledge_bases', 'documents', 'assistants', 'conversations', 'messages',
            'system_configs', 'config_categories', 'model_providers',
            'tools', 'agent_definitions', 'mcp_service_config'
        ]
        
        # 查询现有表
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename;
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in expected_tables if table not in existing_tables]
        
        print_step(f"现有表数量: {len(existing_tables)}", "INFO")
        print_step(f"缺失关键表数量: {len(missing_tables)}", "WARNING" if missing_tables else "SUCCESS")
        
        if missing_tables:
            print_step(f"缺失的表: {', '.join(missing_tables)}", "WARNING")
        
        cursor.close()
        conn.close()
        
        return missing_tables
        
    except Exception as e:
        print_step(f"检查表失败: {e}", "ERROR")
        return []

def create_missing_core_tables():
    """创建缺失的核心表"""
    print_header("创建缺失的核心表")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 核心表创建SQL（使用uuid_generate_v4()）
        core_tables_sql = [
            # 用户表
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                auto_id SERIAL UNIQUE,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                disabled BOOLEAN DEFAULT FALSE,
                is_superuser BOOLEAN DEFAULT FALSE,
                last_login TIMESTAMP,
                avatar_url VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # 角色表
            """
            CREATE TABLE IF NOT EXISTS roles (
                id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                name VARCHAR(50) UNIQUE NOT NULL,
                description VARCHAR(255),
                is_system BOOLEAN DEFAULT FALSE,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # 权限表
            """
            CREATE TABLE IF NOT EXISTS permissions (
                id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                name VARCHAR(50) UNIQUE NOT NULL,
                code VARCHAR(50) UNIQUE NOT NULL,
                description VARCHAR(255),
                category VARCHAR(50),
                resource VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # 用户角色关联表
            """
            CREATE TABLE IF NOT EXISTS user_role (
                user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
                role_id VARCHAR(36) REFERENCES roles(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
            );
            """,
            
            # 角色权限关联表
            """
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id VARCHAR(36) REFERENCES roles(id) ON DELETE CASCADE,
                permission_id VARCHAR(36) REFERENCES permissions(id) ON DELETE CASCADE,
                PRIMARY KEY (role_id, permission_id)
            );
            """,
            
            # 知识库表
            """
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings JSONB DEFAULT '{}',
                type VARCHAR(50) DEFAULT 'default',
                agno_kb_id VARCHAR(255),
                total_documents INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002'
            );
            """
        ]
        
        success_count = 0
        for i, sql in enumerate(core_tables_sql, 1):
            try:
                cursor.execute(sql)
                table_name = sql.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
                print_step(f"创建表 {table_name} 成功", "SUCCESS")
                success_count += 1
            except psycopg2.Error as e:
                print_step(f"创建表 {i} 失败: {str(e)[:100]}...", "ERROR")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_step(f"成功创建 {success_count}/{len(core_tables_sql)} 个核心表", "SUCCESS" if success_count == len(core_tables_sql) else "WARNING")
        return success_count == len(core_tables_sql)
        
    except Exception as e:
        print_step(f"创建核心表异常: {e}", "ERROR")
        return False

def insert_default_data():
    """插入默认数据"""
    print_header("插入默认数据")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 创建默认管理员用户
        cursor.execute("""
            INSERT INTO users (username, email, hashed_password, full_name, is_superuser)
            VALUES ('admin', 'admin@zzdsj.com', '$2b$12$LQv3c1yqBo69SFqjfUmNnuebNZr8cCsVIIuQ1y.U9VC.ExnQd7CtO', '系统管理员', true)
            ON CONFLICT (username) DO NOTHING;
        """)
        print_step("创建默认管理员用户", "SUCCESS")
        
        # 创建默认角色
        cursor.execute("""
            INSERT INTO roles (name, description, is_system)
            VALUES ('admin', '系统管理员角色', true)
            ON CONFLICT (name) DO NOTHING;
        """)
        print_step("创建默认角色", "SUCCESS")
        
        # 创建基础权限
        permissions = [
            ('user_management', '用户管理', '管理系统用户'),
            ('knowledge_base_management', '知识库管理', '管理知识库'),
            ('system_config', '系统配置', '配置系统参数')
        ]
        
        for code, name, desc in permissions:
            cursor.execute("""
                INSERT INTO permissions (code, name, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO NOTHING;
            """, (code, name, desc))
        
        print_step("创建基础权限", "SUCCESS")
        
        # 创建默认知识库
        cursor.execute("""
            INSERT INTO knowledge_bases (name, description, type)
            VALUES ('默认知识库', '系统默认知识库', 'default')
            ON CONFLICT DO NOTHING;
        """)
        print_step("创建默认知识库", "SUCCESS")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print_step(f"插入默认数据失败: {e}", "ERROR")
        return False

def main():
    """主修复流程"""
    print_header("数据库问题修复工具")
    
    print("🎯 此工具将修复数据库初始化中的问题：")
    print("  • UUID扩展和函数问题")
    print("  • 缺失的核心表")
    print("  • 默认数据插入")
    
    # 步骤1: 检查扩展
    ext_info = check_extensions()
    if not ext_info:
        return False
    
    # 步骤2: 尝试安装UUID扩展
    try_install_uuid_extension()
    
    # 步骤3: 创建UUID函数
    if not create_uuid_function():
        return False
    
    # 步骤4: 检查缺失的表
    missing_tables = check_missing_tables()
    
    # 步骤5: 创建缺失的核心表
    if missing_tables:
        if not create_missing_core_tables():
            return False
    
    # 步骤6: 插入默认数据
    if not insert_default_data():
        return False
    
    # 最终验证
    print_header("修复完成验证")
    final_missing = check_missing_tables()
    
    if not final_missing:
        print_step("🎉 数据库修复完成！所有核心表已创建", "SUCCESS")
        return True
    else:
        print_step(f"修复后仍有 {len(final_missing)} 个表缺失", "WARNING")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 