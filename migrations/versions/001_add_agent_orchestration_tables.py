"""Add agent orchestration tables

Revision ID: 001_orchestration
Revises: 
Create Date: 2025-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_orchestration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库：创建智能体编排相关表"""
    
    # 创建智能体编排配置表
    op.create_table(
        'agent_orchestrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assistant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('orchestration_config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('execution_plan', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assistant_id'], ['assistants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_agent_orchestrations_id', 'agent_orchestrations', ['id'])
    op.create_index('ix_agent_orchestrations_assistant_id', 'agent_orchestrations', ['assistant_id'])
    op.create_index('ix_agent_orchestrations_is_active', 'agent_orchestrations', ['is_active'])
    
    # 创建编排执行日志表
    op.create_table(
        'orchestration_execution_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('orchestration_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('input_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_trace', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['orchestration_id'], ['agent_orchestrations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建执行日志索引
    op.create_index('ix_orchestration_execution_logs_id', 'orchestration_execution_logs', ['id'])
    op.create_index('ix_orchestration_execution_logs_session_id', 'orchestration_execution_logs', ['session_id'])
    op.create_index('ix_orchestration_execution_logs_orchestration_id', 'orchestration_execution_logs', ['orchestration_id'])
    op.create_index('ix_orchestration_execution_logs_status', 'orchestration_execution_logs', ['status'])
    op.create_index('ix_orchestration_execution_logs_start_time', 'orchestration_execution_logs', ['start_time'])


def downgrade():
    """降级数据库：删除智能体编排相关表"""
    
    # 删除索引
    op.drop_index('ix_orchestration_execution_logs_start_time', table_name='orchestration_execution_logs')
    op.drop_index('ix_orchestration_execution_logs_status', table_name='orchestration_execution_logs')
    op.drop_index('ix_orchestration_execution_logs_orchestration_id', table_name='orchestration_execution_logs')
    op.drop_index('ix_orchestration_execution_logs_session_id', table_name='orchestration_execution_logs')
    op.drop_index('ix_orchestration_execution_logs_id', table_name='orchestration_execution_logs')
    
    op.drop_index('ix_agent_orchestrations_is_active', table_name='agent_orchestrations')
    op.drop_index('ix_agent_orchestrations_assistant_id', table_name='agent_orchestrations')
    op.drop_index('ix_agent_orchestrations_id', table_name='agent_orchestrations')
    
    # 删除表
    op.drop_table('orchestration_execution_logs')
    op.drop_table('agent_orchestrations') 