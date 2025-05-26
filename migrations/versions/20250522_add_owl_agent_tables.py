"""Add OWL Agent tables

Revision ID: 20250522_owl_agent
Revises: 
Create Date: 2025-05-22 16:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250522_owl_agent'
down_revision = None  # 请根据实际情况替换为最新的迁移版本ID
branch_labels = None
depends_on = None


def upgrade():
    # 创建Agent定义表
    op.create_table('owl_agent_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('model_provider', sa.String(length=255), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True, default=0.7),
        sa.Column('max_tokens', sa.Integer(), nullable=True, default=1500),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('top_k', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('prompt_templates', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('behaviors', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('knowledge', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=[]),
        sa.Column('version', sa.String(length=50), nullable=True, default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_owl_agent_definitions_name'), 'owl_agent_definitions', ['name'], unique=False)

    # 创建Agent能力表
    op.create_table('owl_agent_capabilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('required', sa.Boolean(), nullable=True, default=False),
        sa.Column('category', sa.String(length=100), nullable=True, default='general'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['owl_agent_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_owl_agent_capabilities_agent_id'), 'owl_agent_capabilities', ['agent_id'], unique=False)

    # 创建Agent工具表
    op.create_table('owl_agent_tools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('tool_description', sa.Text(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('is_required', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['owl_agent_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_owl_agent_tools_agent_id'), 'owl_agent_tools', ['agent_id'], unique=False)

    # 创建Agent链定义表
    op.create_table('owl_agent_chain_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chain_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('execution_mode', sa.String(length=50), nullable=True, default='sequential'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chain_id')
    )
    op.create_index(op.f('idx_owl_agent_chain_definitions_chain_id'), 'owl_agent_chain_definitions', ['chain_id'], unique=False)
    op.create_check_constraint(
        'check_execution_mode',
        'owl_agent_chain_definitions',
        sa.text("execution_mode IN ('sequential', 'parallel', 'conditional')")
    )

    # 创建Agent链步骤表
    op.create_table('owl_agent_chain_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chain_id', sa.Integer(), nullable=True),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('agent_name', sa.String(length=255), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True, default='processor'),
        sa.Column('input_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('output_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('condition', sa.Text(), nullable=True),
        sa.Column('fallback', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['chain_id'], ['owl_agent_chain_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['owl_agent_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_owl_agent_chain_steps_chain_id'), 'owl_agent_chain_steps', ['chain_id'], unique=False)
    op.create_index(op.f('idx_owl_agent_chain_steps_agent_id'), 'owl_agent_chain_steps', ['agent_id'], unique=False)

    # 创建Agent链执行记录表
    op.create_table('owl_agent_chain_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.String(length=255), nullable=False),
        sa.Column('chain_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, default='pending'),
        sa.Column('input_message', sa.Text(), nullable=True),
        sa.Column('result_content', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['chain_id'], ['owl_agent_chain_definitions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('execution_id')
    )
    op.create_index(op.f('idx_owl_agent_chain_executions_execution_id'), 'owl_agent_chain_executions', ['execution_id'], unique=False)
    op.create_index(op.f('idx_owl_agent_chain_executions_chain_id'), 'owl_agent_chain_executions', ['chain_id'], unique=False)
    op.create_index(op.f('idx_owl_agent_chain_executions_user_id'), 'owl_agent_chain_executions', ['user_id'], unique=False)
    op.create_check_constraint(
        'check_execution_status',
        'owl_agent_chain_executions',
        sa.text("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')")
    )

    # 创建Agent链执行步骤记录表
    op.create_table('owl_agent_chain_execution_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=True),
        sa.Column('chain_step_id', sa.Integer(), nullable=True),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('agent_name', sa.String(length=255), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True, default='pending'),
        sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['owl_agent_chain_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chain_step_id'], ['owl_agent_chain_steps.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['agent_id'], ['owl_agent_definitions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_owl_agent_chain_execution_steps_execution_id'), 'owl_agent_chain_execution_steps', ['execution_id'], unique=False)
    op.create_check_constraint(
        'check_execution_step_status',
        'owl_agent_chain_execution_steps',
        sa.text("status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'fallback')")
    )

    # 创建Agent消息表
    op.create_table('owl_agent_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.String(length=255), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('agent_execution_id', sa.String(length=255), nullable=True),
        sa.Column('message_type', sa.String(length=50), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_format', sa.String(length=50), nullable=True, default='text'),
        sa.Column('raw_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('parent_message_id', sa.String(length=255), nullable=True),
        sa.Column('conversation_id', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['owl_agent_definitions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id')
    )
    op.create_index(op.f('idx_owl_agent_messages_message_id'), 'owl_agent_messages', ['message_id'], unique=False)
    op.create_index(op.f('idx_owl_agent_messages_agent_id'), 'owl_agent_messages', ['agent_id'], unique=False)
    op.create_index(op.f('idx_owl_agent_messages_agent_execution_id'), 'owl_agent_messages', ['agent_execution_id'], unique=False)
    op.create_index(op.f('idx_owl_agent_messages_conversation_id'), 'owl_agent_messages', ['conversation_id'], unique=False)

    # 创建消息映射表
    op.create_table('owl_agent_message_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('internal_message_id', sa.Integer(), nullable=True),
        sa.Column('external_message_id', sa.String(length=255), nullable=True),
        sa.Column('mapping_type', sa.String(length=50), nullable=True, default='direct'),
        sa.Column('mapping_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['internal_message_id'], ['owl_agent_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_owl_agent_message_mappings_internal_message_id'), 'owl_agent_message_mappings', ['internal_message_id'], unique=False)
    op.create_index(op.f('idx_owl_agent_message_mappings_external_message_id'), 'owl_agent_message_mappings', ['external_message_id'], unique=False)

    # 创建工具调用表
    op.create_table('owl_agent_tool_calls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('tool_arguments', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('tool_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('status', sa.String(length=50), nullable=True, default='pending'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['owl_agent_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_owl_agent_tool_calls_message_id'), 'owl_agent_tool_calls', ['message_id'], unique=False)
    op.create_check_constraint(
        'check_tool_call_status',
        'owl_agent_tool_calls',
        sa.text("status IN ('pending', 'running', 'completed', 'failed')")
    )


def downgrade():
    # 删除所有表，顺序与创建相反
    op.drop_table('owl_agent_tool_calls')
    op.drop_table('owl_agent_message_mappings')
    op.drop_table('owl_agent_messages')
    op.drop_table('owl_agent_chain_execution_steps')
    op.drop_table('owl_agent_chain_executions')
    op.drop_table('owl_agent_chain_steps')
    op.drop_table('owl_agent_chain_definitions')
    op.drop_table('owl_agent_tools')
    op.drop_table('owl_agent_capabilities')
    op.drop_table('owl_agent_definitions')
