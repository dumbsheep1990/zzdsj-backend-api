#!/usr/bin/env python3
"""
重新创建缺失的数据库表脚本
检查database_complete.sql中定义的表，找出缺失的表并重新创建
"""

import psycopg2
import sys
import re
from datetime import datetime
from pathlib import Path

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

def get_existing_tables():
    """获取当前数据库中已存在的表"""
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename;
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return existing_tables
        
    except Exception as e:
        print_step(f"获取现有表失败: {e}", "ERROR")
        return []

def extract_table_definitions_from_sql():
    """从database_complete.sql文件中提取表定义"""
    sql_file = Path("database_complete.sql")
    if not sql_file.exists():
        print_step("database_complete.sql文件不存在", "ERROR")
        return {}
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则表达式提取CREATE TABLE语句
    table_pattern = r'CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);'
    matches = re.findall(table_pattern, content, re.DOTALL | re.IGNORECASE)
    
    table_definitions = {}
    for table_name, table_def in matches:
        # 重构完整的CREATE TABLE语句
        full_definition = f"CREATE TABLE IF NOT EXISTS {table_name} ({table_def});"
        table_definitions[table_name] = full_definition
    
    return table_definitions

def find_missing_tables():
    """找出缺失的表"""
    print_header("分析缺失的表")
    
    existing_tables = get_existing_tables()
    table_definitions = extract_table_definitions_from_sql()
    
    if not table_definitions:
        print_step("无法从SQL文件中提取表定义", "ERROR")
        return [], {}
    
    expected_tables = set(table_definitions.keys())
    existing_tables_set = set(existing_tables)
    missing_tables = expected_tables - existing_tables_set
    
    print_step(f"预期表数量: {len(expected_tables)}", "INFO")
    print_step(f"现有表数量: {len(existing_tables)}", "INFO")
    print_step(f"缺失表数量: {len(missing_tables)}", "WARNING" if missing_tables else "SUCCESS")
    
    if missing_tables:
        print_step("缺失的表:", "INFO")
        for i, table in enumerate(sorted(missing_tables), 1):
            print(f"    {i:2}. {table}")
    
    # 返回缺失的表及其定义
    missing_definitions = {table: table_definitions[table] for table in missing_tables}
    return list(missing_tables), missing_definitions

def create_missing_table(table_name, table_definition):
    """创建单个缺失的表"""
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 首先确保uuid_generate_v4函数存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc 
                WHERE proname = 'uuid_generate_v4'
            );
        """)
        has_uuid_func = cursor.fetchone()[0]
        
        if not has_uuid_func:
            # 创建UUID函数
            cursor.execute("""
                CREATE OR REPLACE FUNCTION uuid_generate_v4() 
                RETURNS TEXT 
                LANGUAGE sql 
                AS $$ SELECT gen_random_uuid()::text; $$;
            """)
            print_step("创建uuid_generate_v4函数", "SUCCESS")
        
        # 为VARCHAR(36)类型的id字段添加默认值
        if 'id VARCHAR(36) PRIMARY KEY' in table_definition and 'DEFAULT' not in table_definition:
            table_definition = table_definition.replace(
                'id VARCHAR(36) PRIMARY KEY',
                'id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()'
            )
        
        # 执行表创建
        cursor.execute(table_definition)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print_step(f"创建表 {table_name} 成功", "SUCCESS")
        return True
        
    except Exception as e:
        print_step(f"创建表 {table_name} 失败: {str(e)[:100]}...", "ERROR")
        return False

def create_all_missing_tables():
    """创建所有缺失的表"""
    print_header("创建缺失的表")
    
    missing_tables, missing_definitions = find_missing_tables()
    
    if not missing_tables:
        print_step("没有缺失的表需要创建", "SUCCESS")
        return True
    
    success_count = 0
    total_count = len(missing_tables)
    
    # 按依赖关系排序（简单处理：基础表优先）
    priority_tables = [
        'agent_chains', 'agent_chain_executions', 'agent_chain_execution_steps',
        'unified_tools', 'search_sessions', 'lightrag_graphs', 'lightrag_queries',
        'compression_strategies', 'tool_chains', 'tool_chain_executions',
        'tool_usage_stats', 'search_result_cache', 'question_feedback',
        'question_tags', 'question_tag_relations'
    ]
    
    # 先创建优先级高的表
    ordered_tables = []
    for table in priority_tables:
        if table in missing_tables:
            ordered_tables.append(table)
    
    # 添加剩余的表
    for table in missing_tables:
        if table not in ordered_tables:
            ordered_tables.append(table)
    
    for table_name in ordered_tables:
        table_definition = missing_definitions[table_name]
        if create_missing_table(table_name, table_definition):
            success_count += 1
    
    print_step(f"成功创建 {success_count}/{total_count} 个表", 
               "SUCCESS" if success_count == total_count else "WARNING")
    
    return success_count == total_count

def create_indexes_and_triggers():
    """创建索引和触发器"""
    print_header("创建索引和触发器")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 读取SQL文件中的索引和触发器
        sql_file = Path("database_complete.sql")
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取CREATE INDEX语句
        index_pattern = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+IF\s+NOT\s+EXISTS[^;]+;'
        index_statements = re.findall(index_pattern, content, re.IGNORECASE | re.DOTALL)
        
        # 提取CREATE TRIGGER语句
        trigger_pattern = r'CREATE\s+TRIGGER\s+IF\s+NOT\s+EXISTS[^;]+;'
        trigger_statements = re.findall(trigger_pattern, content, re.IGNORECASE | re.DOTALL)
        
        # 创建update_updated_at_column函数
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        print_step("创建update_updated_at_column函数", "SUCCESS")
        
        # 执行索引创建
        index_success = 0
        for index_stmt in index_statements:
            try:
                cursor.execute(index_stmt)
                index_success += 1
            except Exception as e:
                print_step(f"创建索引失败: {str(e)[:50]}...", "WARNING")
        
        print_step(f"成功创建 {index_success}/{len(index_statements)} 个索引", "INFO")
        
        # 执行触发器创建
        trigger_success = 0
        for trigger_stmt in trigger_statements:
            try:
                cursor.execute(trigger_stmt)
                trigger_success += 1
            except Exception as e:
                print_step(f"创建触发器失败: {str(e)[:50]}...", "WARNING")
        
        print_step(f"成功创建 {trigger_success}/{len(trigger_statements)} 个触发器", "INFO")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print_step(f"创建索引和触发器失败: {e}", "ERROR")
        return False

def final_verification():
    """最终验证"""
    print_header("最终验证")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 统计表数量
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        table_count = cursor.fetchone()[0]
        
        # 统计索引数量
        cursor.execute("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE schemaname = 'public';
        """)
        index_count = cursor.fetchone()[0]
        
        # 统计触发器数量
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.triggers 
            WHERE trigger_schema = 'public';
        """)
        trigger_count = cursor.fetchone()[0]
        
        # 统计记录数量
        cursor.execute("""
            SELECT 
                SUM(
                    CASE 
                        WHEN c.reltuples >= 0 THEN c.reltuples::BIGINT
                        ELSE 0
                    END
                ) as total_records
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
            AND c.relkind = 'r';
        """)
        total_records = cursor.fetchone()[0] or 0
        
        print_step("📊 数据库最终统计:", "INFO")
        print(f"    表数量: {table_count}")
        print(f"    索引数量: {index_count}")
        print(f"    触发器数量: {trigger_count}")
        print(f"    总记录数: {total_records}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print_step(f"最终验证失败: {e}", "ERROR")
        return False

def main():
    """主函数"""
    print_header("重新创建缺失数据库表工具")
    
    print("🎯 此工具将：")
    print("  • 分析database_complete.sql中定义的表")
    print("  • 找出当前数据库中缺失的表")
    print("  • 重新创建缺失的表")
    print("  • 创建相关的索引和触发器")
    print("  • 验证最终结果")
    
    # 步骤1: 创建缺失的表
    if not create_all_missing_tables():
        print_step("部分表创建失败，继续执行其他步骤", "WARNING")
    
    # 步骤2: 创建索引和触发器
    if not create_indexes_and_triggers():
        print_step("索引和触发器创建失败", "WARNING")
    
    # 步骤3: 最终验证
    if not final_verification():
        return False
    
    print_step("🎉 数据库表结构完善完成！", "SUCCESS")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 