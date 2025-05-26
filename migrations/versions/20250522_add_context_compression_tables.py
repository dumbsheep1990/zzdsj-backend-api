"""Add Context Compression tables

Revision ID: 20250522_context_compression
Revises: 20250522_owl_agent
Create Date: 2025-05-22 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250522_context_compression'
down_revision = '20250522_owl_agent'  # 使用最新的迁移版本ID作为前置版本
branch_labels = None
depends_on = None


def upgrade():
    # 创建上下文压缩工具表
    op.create_table('context_compression_tools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('compression_method', sa.String(length=50), nullable=False, server_default='tree_summarize'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_context_compression_tools_name'), 'context_compression_tools', ['name'], unique=False)
    
    # 创建Agent上下文压缩配置表
    op.create_table('agent_context_compression_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('method', sa.String(length=50), nullable=False, server_default='tree_summarize'),
        sa.Column('top_n', sa.Integer(), nullable=False, server_default=sa.text('5')),
        sa.Column('num_children', sa.Integer(), nullable=False, server_default=sa.text('2')),
        sa.Column('streaming', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('rerank_model', sa.String(length=255), nullable=True, server_default='BAAI/bge-reranker-base'),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=False, server_default=sa.text('0.1')),
        sa.Column('store_original', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('use_message_format', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('phase', sa.String(length=50), nullable=False, server_default='final'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['owl_agent_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_agent_context_compression_config_agent_id'), 'agent_context_compression_config', ['agent_id'], unique=False)
    op.create_check_constraint(
        'check_compression_method',
        'agent_context_compression_config',
        sa.text("method IN ('tree_summarize', 'compact_and_refine')")
    )
    op.create_check_constraint(
        'check_compression_phase',
        'agent_context_compression_config',
        sa.text("phase IN ('retrieval', 'final')")
    )
    
    # 创建上下文压缩执行记录表
    op.create_table('context_compression_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('compression_config_id', sa.Integer(), nullable=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('original_content_length', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('compressed_content_length', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('compression_ratio', sa.Float(), nullable=True),
        sa.Column('source_count', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='success'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['owl_agent_definitions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['compression_config_id'], ['agent_context_compression_config.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('execution_id')
    )
    op.create_index(op.f('idx_context_compression_executions_agent_id'), 'context_compression_executions', ['agent_id'], unique=False)
    op.create_index(op.f('idx_context_compression_executions_config_id'), 'context_compression_executions', ['compression_config_id'], unique=False)
    op.create_check_constraint(
        'check_compression_status',
        'context_compression_executions',
        sa.text("status IN ('success', 'failed', 'partial')")
    )
    
    # 为现有的owl_agent_tools表添加上下文压缩工具关联
    op.add_column('owl_agent_tools', 
        sa.Column('compression_config_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_agent_tools_compression_config',
        'owl_agent_tools', 'agent_context_compression_config',
        ['compression_config_id'], ['id'], ondelete='SET NULL'
    )


def downgrade():
    # 删除外键约束
    op.drop_constraint('fk_agent_tools_compression_config', 'owl_agent_tools', type_='foreignkey')
    
    # 删除列
    op.drop_column('owl_agent_tools', 'compression_config_id')
    
    # 删除表
    op.drop_table('context_compression_executions')
    op.drop_table('agent_context_compression_config')
    op.drop_table('context_compression_tools')
