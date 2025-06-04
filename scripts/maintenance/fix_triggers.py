#!/usr/bin/env python3
"""
修复数据库触发器创建的脚本
PostgreSQL不支持CREATE TRIGGER IF NOT EXISTS语法，需要单独处理
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

def check_trigger_exists(cursor, trigger_name, table_name):
    """检查触发器是否存在"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.triggers
            WHERE trigger_name = %s AND event_object_table = %s
            AND trigger_schema = 'public'
        );
    """, (trigger_name, table_name))
    return cursor.fetchone()[0]

def create_trigger(cursor, trigger_name, table_name):
    """创建单个触发器"""
    try:
        # 检查触发器是否已存在
        if check_trigger_exists(cursor, trigger_name, table_name):
            print_step(f"触发器 {trigger_name} 已存在", "INFO")
            return True
        
        # 创建触发器
        trigger_sql = f"""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
        
        cursor.execute(trigger_sql)
        print_step(f"创建触发器 {trigger_name} 成功", "SUCCESS")
        return True
        
    except Exception as e:
        print_step(f"创建触发器 {trigger_name} 失败: {str(e)[:50]}...", "ERROR")
        return False

def create_all_triggers():
    """创建所有需要的触发器"""
    print_header("创建数据库触发器")
    
    # 需要创建的触发器列表
    triggers = [
        # 新增表的触发器
        ('update_agent_chains_updated_at', 'agent_chains'),
        ('update_agent_chain_executions_updated_at', 'agent_chain_executions'),
        ('update_unified_tools_updated_at', 'unified_tools'),
        ('update_lightrag_graphs_updated_at', 'lightrag_graphs'),
        ('update_compression_strategies_updated_at', 'compression_strategies'),
        ('update_tool_chains_updated_at', 'tool_chains'),
        ('update_tool_chain_executions_updated_at', 'tool_chain_executions'),
        
        # 基础表的触发器（如果缺失）
        ('update_users_updated_at', 'users'),
        ('update_roles_updated_at', 'roles'),
        ('update_permissions_updated_at', 'permissions'),
        ('update_user_settings_updated_at', 'user_settings'),
        ('update_api_keys_updated_at', 'api_keys'),
        ('update_system_configs_updated_at', 'system_configs'),
        ('update_knowledge_bases_updated_at', 'knowledge_bases'),
        ('update_documents_updated_at', 'documents'),
        ('update_assistants_updated_at', 'assistants'),
        ('update_conversations_updated_at', 'conversations'),
        ('update_agent_definitions_updated_at', 'agent_definitions'),
        ('update_tools_updated_at', 'tools'),
        ('update_mcp_service_config_updated_at', 'mcp_service_config'),
        ('update_mcp_tool_updated_at', 'mcp_tool'),
        ('update_agent_config_updated_at', 'agent_config'),
        ('update_agent_tool_updated_at', 'agent_tool'),
        ('update_model_providers_updated_at', 'model_providers'),
        ('update_config_categories_updated_at', 'config_categories'),
        
        # OWL Agent系统触发器
        ('update_owl_agent_definitions_updated_at', 'owl_agent_definitions'),
        ('update_owl_agent_chain_definitions_updated_at', 'owl_agent_chain_definitions'),
        ('update_owl_agent_chain_steps_updated_at', 'owl_agent_chain_steps'),
        ('update_owl_agent_chain_executions_updated_at', 'owl_agent_chain_executions'),
        ('update_context_compression_tools_updated_at', 'context_compression_tools'),
        ('update_agent_context_compression_config_updated_at', 'agent_context_compression_config'),
        ('update_context_compression_executions_updated_at', 'context_compression_executions')
    ]
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 确保update_updated_at_column函数存在
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        print_step("确保update_updated_at_column函数存在", "SUCCESS")
        
        success_count = 0
        total_count = len(triggers)
        
        for trigger_name, table_name in triggers:
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                );
            """, (table_name,))
            
            if not cursor.fetchone()[0]:
                print_step(f"表 {table_name} 不存在，跳过触发器 {trigger_name}", "WARNING")
                continue
            
            # 检查表是否有updated_at字段
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' 
                    AND table_name = %s 
                    AND column_name = 'updated_at'
                );
            """, (table_name,))
            
            if not cursor.fetchone()[0]:
                print_step(f"表 {table_name} 没有updated_at字段，跳过触发器 {trigger_name}", "WARNING")
                continue
            
            if create_trigger(cursor, trigger_name, table_name):
                success_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_step(f"成功创建 {success_count}/{total_count} 个触发器", 
                   "SUCCESS" if success_count == total_count else "WARNING")
        
        return True
        
    except Exception as e:
        print_step(f"创建触发器失败: {e}", "ERROR")
        return False

def verify_triggers():
    """验证触发器创建结果"""
    print_header("验证触发器状态")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 统计触发器数量
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.triggers 
            WHERE trigger_schema = 'public';
        """)
        trigger_count = cursor.fetchone()[0]
        
        # 列出所有触发器
        cursor.execute("""
            SELECT trigger_name, event_object_table, action_timing, event_manipulation
            FROM information_schema.triggers 
            WHERE trigger_schema = 'public'
            ORDER BY event_object_table, trigger_name;
        """)
        triggers = cursor.fetchall()
        
        print_step(f"📊 触发器统计: 共 {trigger_count} 个", "INFO")
        
        if triggers:
            print_step("触发器列表:", "INFO")
            for trigger_name, table_name, timing, event in triggers:
                print(f"    {table_name}.{trigger_name} ({timing} {event})")
        
        # 检查update_updated_at_column函数
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc 
                WHERE proname = 'update_updated_at_column'
            );
        """)
        has_function = cursor.fetchone()[0]
        print_step(f"update_updated_at_column函数存在: {has_function}", "SUCCESS" if has_function else "ERROR")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print_step(f"验证触发器失败: {e}", "ERROR")
        return False

def test_trigger():
    """测试触发器功能"""
    print_header("测试触发器功能")
    
    try:
        conn = psycopg2.connect(**REMOTE_DB_CONFIG)
        cursor = conn.cursor()
        
        # 测试users表的触发器
        cursor.execute("SELECT id, updated_at FROM users WHERE username = 'admin';")
        user_data = cursor.fetchone()
        
        if user_data:
            user_id, old_updated_at = user_data
            
            # 更新用户记录触发updated_at更新
            cursor.execute("""
                UPDATE users SET full_name = full_name WHERE id = %s;
            """, (user_id,))
            
            # 检查updated_at是否更新
            cursor.execute("SELECT updated_at FROM users WHERE id = %s;", (user_id,))
            new_updated_at = cursor.fetchone()[0]
            
            if new_updated_at > old_updated_at:
                print_step("触发器功能测试成功 - updated_at已自动更新", "SUCCESS")
            else:
                print_step("触发器功能测试失败 - updated_at未更新", "ERROR")
            
            conn.rollback()  # 回滚测试更改
        else:
            print_step("未找到测试用户", "WARNING")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print_step(f"测试触发器功能失败: {e}", "ERROR")
        return False

def main():
    """主函数"""
    print_header("数据库触发器修复工具")
    
    print("🎯 此工具将：")
    print("  • 创建所有缺失的updated_at触发器")
    print("  • 验证触发器创建状态")
    print("  • 测试触发器功能")
    
    # 步骤1: 创建所有触发器
    if not create_all_triggers():
        print_step("触发器创建失败", "ERROR")
        return False
    
    # 步骤2: 验证触发器
    if not verify_triggers():
        print_step("触发器验证失败", "ERROR")
        return False
    
    # 步骤3: 测试触发器功能
    if not test_trigger():
        print_step("触发器功能测试失败", "WARNING")
    
    print_step("🎉 触发器修复完成！", "SUCCESS")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 