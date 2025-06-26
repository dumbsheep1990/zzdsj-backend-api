"""添加Agno框架支持

Revision ID: add_agno_support
Revises: 
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_agno_support'
down_revision = None  # 设置为实际的上一个revision
branch_labels = None
depends_on = None


def upgrade():
    """添加Agno框架支持的数据库结构"""
    
    # 1. 扩展assistants表
    op.add_column('assistants', 
                  sa.Column('framework', sa.String(50), nullable=False, server_default='general'))
    op.add_column('assistants', 
                  sa.Column('agno_config', sa.JSON(), nullable=True))
    op.add_column('assistants', 
                  sa.Column('agno_agent_id', sa.String(255), nullable=True))
    op.add_column('assistants', 
                  sa.Column('is_agno_managed', sa.Boolean(), nullable=False, server_default='false'))
    
    # 2. 创建用户Agno配置表
    op.create_table('user_agno_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('config_data', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 添加索引
    op.create_index('ix_user_agno_configs_user_id', 'user_agno_configs', ['user_id'], unique=True)
    
    # 3. 创建Agno会话表
    op.create_table('agno_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('assistant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('agent_name', sa.String(255), nullable=False),
        sa.Column('memory_data', sa.JSON(), nullable=True),
        sa.Column('tool_states', sa.JSON(), nullable=True),
        sa.Column('session_metadata', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['assistant_id'], ['assistants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 添加索引
    op.create_index('ix_agno_sessions_session_id', 'agno_sessions', ['session_id'], unique=True)
    op.create_index('ix_agno_sessions_user_id', 'agno_sessions', ['user_id'])
    
    # 4. 创建Agno工具执行记录表
    op.create_table('agno_tool_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('tool_name', sa.String(255), nullable=False),
        sa.Column('tool_id', sa.String(255), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['agno_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 添加索引
    op.create_index('ix_agno_tool_executions_session_id', 'agno_tool_executions', ['session_id'])
    op.create_index('ix_agno_tool_executions_tool_name', 'agno_tool_executions', ['tool_name'])


def downgrade():
    """移除Agno框架支持的数据库结构"""
    
    # 1. 删除表（按依赖关系逆序）
    op.drop_table('agno_tool_executions')
    op.drop_table('agno_sessions')
    op.drop_table('user_agno_configs')
    
    # 2. 移除assistants表的扩展字段
    op.drop_column('assistants', 'is_agno_managed')
    op.drop_column('assistants', 'agno_agent_id')
    op.drop_column('assistants', 'agno_config')
    op.drop_column('assistants', 'framework') 