"""完整数据库初始化

Revision ID: 20250108_complete_database_init
Revises: 
Create Date: 2025-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import asyncio

# revision identifiers, used by Alembic.
revision = '20250108_complete_database_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库结构"""
    
    # 1. 启用PostgreSQL扩展
    op.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
    op.execute(text("CREATE EXTENSION IF NOT EXISTS \"vector\""))  # 为pgvector做准备
    
    # 2. 创建基础表结构 - 用户与认证
    create_user_tables()
    
    # 3. 创建知识库相关表
    create_knowledge_tables()
    
    # 4. 创建系统配置表
    create_config_tables()
    
    # 5. 创建智能体相关表
    create_agent_tables()
    
    # 6. 创建工具相关表
    create_tool_tables()
    
    # 7. 创建向量数据库相关表
    create_vector_store_tables()
    
    # 8. 创建索引
    create_indexes()
    
    # 9. 创建触发器和函数
    create_triggers_and_functions()
    
    # 10. 创建视图
    create_views()


def downgrade() -> None:
    """降级数据库结构"""
    # 删除视图
    op.execute(text("DROP VIEW IF EXISTS agent_chain_stats_view CASCADE"))
    op.execute(text("DROP VIEW IF EXISTS tool_usage_summary_view CASCADE"))
    op.execute(text("DROP VIEW IF EXISTS lightrag_graph_stats_view CASCADE"))
    
    # 删除函数
    op.execute(text("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE"))
    
    # 删除表（按依赖关系倒序删除）
    tables_to_drop = [
        'tool_usage_stats', 'question_feedback', 'question_tag_relations', 'question_tags',
        'search_result_cache', 'tool_chain_executions', 'tool_chains', 'compression_strategies',
        'lightrag_queries', 'lightrag_graphs', 'search_sessions', 'unified_tools',
        'agent_chain_execution_steps', 'agent_chain_executions', 'agent_chains',
        'agent_tool', 'agent_config', 'mcp_tool_execution', 'mcp_tool', 'mcp_service_config',
        'message_references', 'messages', 'conversations', 'assistant_knowledge_base',
        'question_document_segments', 'questions', 'assistants', 'lightrag_integrations',
        'agent_tool_association', 'tools', 'agent_definitions', 'model_providers',
        'service_health_records', 'config_history', 'system_configs', 'config_categories',
        'document_chunks', 'documents', 'knowledge_bases', 'api_keys', 'user_settings',
        'role_permissions', 'user_role', 'users', 'permissions', 'roles',
        'vector_store_collections', 'vector_store_schemas', 'vector_store_configs'
    ]
    
    for table in tables_to_drop:
        op.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def create_user_tables():
    """创建用户相关表"""
    # 角色表
    op.create_table('roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 权限表
    op.create_table('permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('category', sa.String(50)),
        sa.Column('resource', sa.String(50)),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 用户表
    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('auto_id', sa.Integer, sa.Sequence('users_auto_id_seq'), unique=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100)),
        sa.Column('disabled', sa.Boolean, default=False),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('last_login', sa.TIMESTAMP),
        sa.Column('avatar_url', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 用户角色关系表
    op.create_table('user_role',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id', ondelete='CASCADE')),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    # 角色权限关系表
    op.create_table('role_permissions',
        sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id', ondelete='CASCADE')),
        sa.Column('permission_id', sa.String(36), sa.ForeignKey('permissions.id', ondelete='CASCADE')),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    
    # 用户设置表
    op.create_table('user_settings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('theme', sa.String(20), default='light'),
        sa.Column('language', sa.String(10), default='zh-CN'),
        sa.Column('notification_enabled', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # API密钥表
    op.create_table('api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('key', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(100)),
        sa.Column('description', sa.String(255)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('expires_at', sa.TIMESTAMP),
        sa.Column('last_used_at', sa.TIMESTAMP),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def create_knowledge_tables():
    """创建知识库相关表"""
    # 知识库表
    op.create_table('knowledge_bases',
        sa.Column('id', sa.Integer, sa.Sequence('knowledge_bases_id_seq'), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('settings', sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column('type', sa.String(50), default='default'),
        sa.Column('agno_kb_id', sa.String(255)),
        sa.Column('total_documents', sa.Integer, default=0),
        sa.Column('total_tokens', sa.Integer, default=0),
        sa.Column('embedding_model', sa.String(100), default='text-embedding-ada-002')
    )
    
    # 文档表
    op.create_table('documents',
        sa.Column('id', sa.Integer, sa.Sequence('documents_id_seq'), primary_key=True),
        sa.Column('knowledge_base_id', sa.Integer, sa.ForeignKey('knowledge_bases.id')),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text),
        sa.Column('mime_type', sa.String(100), default='text/plain'),
        sa.Column('metadata', sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column('file_path', sa.String(255)),
        sa.Column('file_size', sa.Integer, default=0),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 文档块表
    op.create_table('document_chunks',
        sa.Column('id', sa.Integer, sa.Sequence('document_chunks_id_seq'), primary_key=True),
        sa.Column('document_id', sa.Integer, sa.ForeignKey('documents.id')),
        sa.Column('content', sa.Text),
        sa.Column('metadata', sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column('embedding_id', sa.String(255)),
        sa.Column('token_count', sa.Integer, default=0),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def create_config_tables():
    """创建系统配置表"""
    # 配置分类表
    op.create_table('config_categories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('order', sa.Integer, default=0),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 系统配置表
    op.create_table('system_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('key', sa.String(255), unique=True, nullable=False),
        sa.Column('value', sa.Text),
        sa.Column('value_type', sa.String(50), nullable=False),
        sa.Column('default_value', sa.Text),
        sa.Column('category_id', sa.String(36), sa.ForeignKey('config_categories.id'), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('is_sensitive', sa.Boolean, default=False),
        sa.Column('is_encrypted', sa.Boolean, default=False),
        sa.Column('validation_rules', sa.JSON),
        sa.Column('is_overridden', sa.Boolean, default=False),
        sa.Column('override_source', sa.String(255)),
        sa.Column('visible_level', sa.String(50), default='all'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 配置历史表
    op.create_table('config_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('config_id', sa.String(36), sa.ForeignKey('system_configs.id'), nullable=False),
        sa.Column('old_value', sa.Text),
        sa.Column('new_value', sa.Text),
        sa.Column('change_source', sa.String(50), nullable=False),
        sa.Column('changed_by', sa.String(100)),
        sa.Column('change_notes', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 服务健康记录表
    op.create_table('service_health_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('status', sa.Boolean, default=False),
        sa.Column('check_time', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('response_time_ms', sa.Integer),
        sa.Column('error_message', sa.Text),
        sa.Column('details', sa.JSON)
    )
    
    # 模型提供商表
    op.create_table('model_providers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('base_url', sa.String(255)),
        sa.Column('auth_type', sa.String(50)),
        sa.Column('is_enabled', sa.Boolean, default=True),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('models', sa.JSON),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def create_agent_tables():
    """创建智能体相关表（简化版）"""
    # 只创建最核心的几个表
    op.create_table('agent_definitions',
        sa.Column('id', sa.Integer, sa.Sequence('agent_definitions_id_seq'), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('base_agent_type', sa.String(50), nullable=False),
        sa.Column('creator_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('agent_config', sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def create_tool_tables():
    """创建工具相关表（简化版）"""
    op.create_table('tools',
        sa.Column('id', sa.Integer, sa.Sequence('tools_id_seq'), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(100)),
        sa.Column('framework', sa.String(50)),
        sa.Column('tool_type', sa.String(50)),
        sa.Column('config', sa.JSON, server_default=sa.text("'{}'::json")),
        sa.Column('creator_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def create_vector_store_tables():
    """创建向量数据库相关表"""
    # 向量存储配置表
    op.create_table('vector_store_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('store_type', sa.String(50), nullable=False),  # milvus, pgvector, etc.
        sa.Column('connection_config', sa.JSON, nullable=False),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 向量存储模式表
    op.create_table('vector_store_schemas',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('schema_config', sa.JSON, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('version', sa.String(20), default='1.0'),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # 向量存储集合表
    op.create_table('vector_store_collections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('store_config_id', sa.String(36), sa.ForeignKey('vector_store_configs.id'), nullable=False),
        sa.Column('schema_id', sa.String(36), sa.ForeignKey('vector_store_schemas.id'), nullable=False),
        sa.Column('collection_name', sa.String(100), nullable=False),
        sa.Column('dimension', sa.Integer, nullable=False),
        sa.Column('metric_type', sa.String(20), default='COSINE'),
        sa.Column('index_config', sa.JSON),
        sa.Column('partition_config', sa.JSON),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('store_config_id', 'collection_name', name='uq_store_collection')
    )


def create_indexes():
    """创建索引"""
    # 用户相关索引
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    
    # 知识库相关索引
    op.create_index('idx_knowledge_bases_name', 'knowledge_bases', ['name'])
    op.create_index('idx_knowledge_bases_type', 'knowledge_bases', ['type'])
    op.create_index('idx_documents_kb_id', 'documents', ['knowledge_base_id'])
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_document_chunks_doc_id', 'document_chunks', ['document_id'])
    
    # 系统配置索引
    op.create_index('idx_system_configs_key', 'system_configs', ['key'])
    op.create_index('idx_system_configs_category', 'system_configs', ['category_id'])
    
    # 向量存储索引
    op.create_index('idx_vector_store_configs_type', 'vector_store_configs', ['store_type'])
    op.create_index('idx_vector_store_configs_default', 'vector_store_configs', ['is_default'])
    op.create_index('idx_vector_store_collections_store', 'vector_store_collections', ['store_config_id'])
    op.create_index('idx_vector_store_collections_schema', 'vector_store_collections', ['schema_id'])
    op.create_index('idx_vector_store_collections_status', 'vector_store_collections', ['status'])


def create_triggers_and_functions():
    """创建触发器和函数"""
    # 创建更新时间戳函数
    op.execute(text("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language plpgsql;
    """))
    
    # 为需要的表创建更新时间戳触发器
    tables_with_updated_at = [
        'users', 'roles', 'permissions', 'user_settings', 'api_keys',
        'knowledge_bases', 'documents', 'config_categories', 'system_configs',
        'model_providers', 'agent_definitions', 'tools',
        'vector_store_configs', 'vector_store_schemas', 'vector_store_collections'
    ]
    
    for table in tables_with_updated_at:
        op.execute(text(f"""
            CREATE TRIGGER update_{table}_updated_at 
            BEFORE UPDATE ON {table} 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """))


def create_views():
    """创建视图"""
    # 用户角色权限视图
    op.execute(text("""
        CREATE OR REPLACE VIEW user_permissions_view AS
        SELECT DISTINCT
            u.id as user_id,
            u.username,
            p.code as permission_code,
            p.name as permission_name,
            p.resource,
            r.name as role_name
        FROM users u
        JOIN user_role ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        JOIN role_permissions rp ON r.id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE u.disabled = false AND r.is_system = false;
    """))
    
    # 向量存储统计视图
    op.execute(text("""
        CREATE OR REPLACE VIEW vector_store_stats_view AS
        SELECT
            vsc.id as config_id,
            vsc.name as config_name,
            vsc.store_type,
            COUNT(vscol.id) as collection_count,
            COUNT(CASE WHEN vscol.status = 'active' THEN 1 END) as active_collections,
            vsc.is_default,
            vsc.is_active as config_active
        FROM vector_store_configs vsc
        LEFT JOIN vector_store_collections vscol ON vsc.id = vscol.store_config_id
        GROUP BY vsc.id, vsc.name, vsc.store_type, vsc.is_default, vsc.is_active;
    """)) 