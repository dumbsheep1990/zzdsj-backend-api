-- =====================================================
-- ZZ-Backend-Lite 数据库初始化脚本
-- 基于 app/models 层的所有模型定义
-- 数据库类型: PostgreSQL
-- 创建时间: 2024
-- =====================================================

-- 启用UUID扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 设置时区
SET timezone = 'UTC';

-- =====================================================
-- 1. 基础表（无外键依赖）
-- =====================================================

-- 用户表
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    auto_id SERIAL UNIQUE,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    disabled BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    avatar_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE users IS '用户基础信息表';

-- 角色表
CREATE TABLE roles (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE roles IS '用户角色定义表';

-- 权限表
CREATE TABLE permissions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(50) UNIQUE NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    resource VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE permissions IS '系统权限定义表';

-- 配置类别表
CREATE TABLE config_categories (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    "order" INTEGER DEFAULT 0,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE config_categories IS '系统配置类别表';

-- 知识库表
CREATE TABLE knowledge_bases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    type VARCHAR(50) DEFAULT 'default',
    agno_kb_id VARCHAR(255),
    total_documents INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE knowledge_bases IS '知识库基础信息表';

-- 模型提供商表
CREATE TABLE model_providers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    api_key VARCHAR(255),
    api_base VARCHAR(255),
    api_version VARCHAR(50),
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB
);
COMMENT ON TABLE model_providers IS '模型提供商配置表';

-- 工具定义表
CREATE TABLE tools (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    function_def JSONB NOT NULL,
    implementation_type VARCHAR(50) DEFAULT 'python',
    implementation TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    category VARCHAR(50),
    framework VARCHAR(50),
    permission_level VARCHAR(50) DEFAULT 'standard',
    parameter_schema JSONB,
    version VARCHAR(20) DEFAULT '1.0.0',
    creator_id VARCHAR(36),
    tags JSONB,
    input_format JSONB,
    output_format JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE tools IS '工具定义表';

-- =====================================================
-- 2. 一级依赖表
-- =====================================================

-- 用户设置表
CREATE TABLE user_settings (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'zh-CN',
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE user_settings IS '用户个人设置表';

-- API密钥表
CREATE TABLE api_keys (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100),
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE api_keys IS '用户API密钥表';

-- 系统配置表
CREATE TABLE system_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    value_type VARCHAR(50) NOT NULL,
    default_value TEXT,
    category_id VARCHAR(36) NOT NULL REFERENCES config_categories(id) ON DELETE CASCADE,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    is_sensitive BOOLEAN DEFAULT FALSE,
    is_encrypted BOOLEAN DEFAULT FALSE,
    validation_rules JSONB,
    is_overridden BOOLEAN DEFAULT FALSE,
    override_source VARCHAR(255),
    visible_level VARCHAR(50) DEFAULT 'all',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE system_configs IS '系统配置项表';

-- 模型信息表
CREATE TABLE model_info (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
    model_id VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    capabilities JSONB,
    is_default BOOLEAN DEFAULT FALSE,
    config JSONB
);
COMMENT ON TABLE model_info IS '模型详细信息表';

-- 文档表
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    mime_type VARCHAR(100) DEFAULT 'text/plain',
    metadata JSONB DEFAULT '{}',
    file_path VARCHAR(255),
    file_size INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE documents IS '知识库文档表';

-- 助手表（统一定义）
CREATE TABLE assistants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model VARCHAR(100) NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '[]',
    configuration JSONB,
    system_prompt TEXT,
    access_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE assistants IS 'AI助手定义表';

-- 智能体定义表
CREATE TABLE agent_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_agent_type VARCHAR(255) NOT NULL,
    creator_id VARCHAR(36) REFERENCES users(id),
    is_public BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    configuration JSONB,
    system_prompt TEXT,
    workflow_definition JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE agent_definitions IS '智能体定义表';

-- 智能体模板表
CREATE TABLE agent_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_data JSONB NOT NULL,
    category VARCHAR(100),
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE agent_templates IS '智能体模板表';

-- MCP服务配置表
CREATE TABLE mcp_service_config (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(36) UNIQUE NOT NULL DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    service_type VARCHAR(50) NOT NULL DEFAULT 'docker',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    image VARCHAR(255),
    container VARCHAR(255),
    service_port INTEGER,
    deploy_directory VARCHAR(255),
    settings JSONB,
    cpu_limit VARCHAR(20),
    memory_limit VARCHAR(20),
    disk_limit VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_started_at TIMESTAMP WITH TIME ZONE,
    last_stopped_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE mcp_service_config IS 'MCP服务配置表';

-- 语音设置表
CREATE TABLE voice_settings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    enable_voice_input BOOLEAN DEFAULT FALSE,
    enable_voice_output BOOLEAN DEFAULT FALSE,
    stt_model_name VARCHAR(255) DEFAULT 'whisper-base',
    tts_model_name VARCHAR(255) DEFAULT 'edge-tts',
    language VARCHAR(10) DEFAULT 'zh-CN',
    voice VARCHAR(255) DEFAULT 'zh-CN-XiaoxiaoNeural',
    speed FLOAT DEFAULT 1.0,
    audio_format VARCHAR(10) DEFAULT 'mp3',
    sampling_rate INTEGER DEFAULT 16000
);
COMMENT ON TABLE voice_settings IS '用户语音设置表';

-- =====================================================
-- 3. 二级依赖表
-- =====================================================

-- 文档块表
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    embedding_id VARCHAR(255),
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE document_chunks IS '文档分块表';

-- 对话表
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    assistant_id INTEGER NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id),
    title VARCHAR(255) DEFAULT '新对话',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE conversations IS '对话会话表';

-- 消息表
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE messages IS '对话消息表';

-- 消息引用表
CREATE TABLE message_references (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_chunk_id INTEGER NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    relevance_score FLOAT
);
COMMENT ON TABLE message_references IS '消息文档引用表';

-- 资源权限表
CREATE TABLE resource_permissions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(36) NOT NULL,
    access_level VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE resource_permissions IS '用户资源权限表';

-- 知识库访问权限表
CREATE TABLE knowledge_base_access (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    can_read BOOLEAN DEFAULT TRUE,
    can_write BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_share BOOLEAN DEFAULT FALSE,
    can_manage BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE knowledge_base_access IS '知识库访问权限表';

-- 助手访问权限表
CREATE TABLE assistant_access (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assistant_id INTEGER NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    can_use BOOLEAN DEFAULT TRUE,
    can_edit BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    can_share BOOLEAN DEFAULT FALSE,
    can_manage BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE assistant_access IS '助手访问权限表';

-- 模型配置访问权限表
CREATE TABLE model_config_access (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_provider_id INTEGER NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
    can_use BOOLEAN DEFAULT TRUE,
    can_edit BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    quota_limit INTEGER DEFAULT -1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE model_config_access IS '模型配置访问权限表';

-- MCP配置访问权限表
CREATE TABLE mcp_config_access (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mcp_service_id INTEGER NOT NULL REFERENCES mcp_service_config(id) ON DELETE CASCADE,
    can_use BOOLEAN DEFAULT TRUE,
    can_edit BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE mcp_config_access IS 'MCP配置访问权限表';

-- 用户资源配额表
CREATE TABLE user_resource_quotas (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    max_knowledge_bases INTEGER DEFAULT 5,
    max_knowledge_base_size_mb INTEGER DEFAULT 1024,
    max_assistants INTEGER DEFAULT 3,
    daily_model_tokens INTEGER DEFAULT 10000,
    monthly_model_tokens INTEGER DEFAULT 300000,
    max_mcp_calls_per_day INTEGER DEFAULT 100,
    max_storage_mb INTEGER DEFAULT 2048,
    rate_limit_per_minute INTEGER DEFAULT 60,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE user_resource_quotas IS '用户资源配额表';

-- MCP工具表
CREATE TABLE mcp_tool (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES mcp_service_config(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    schema JSONB,
    examples JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE mcp_tool IS 'MCP工具定义表';

-- MCP工具执行历史表
CREATE TABLE mcp_tool_execution (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(36) UNIQUE NOT NULL DEFAULT uuid_generate_v4()::text,
    tool_id INTEGER NOT NULL REFERENCES mcp_tool(id) ON DELETE CASCADE,
    parameters JSONB,
    result JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    context JSONB,
    agent_id VARCHAR(36),
    session_id VARCHAR(36),
    user_id VARCHAR(36),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_ms INTEGER
);
COMMENT ON TABLE mcp_tool_execution IS 'MCP工具执行历史表';

-- 智能体配置表
CREATE TABLE agent_config (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(36) UNIQUE NOT NULL DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'llamaindex',
    model VARCHAR(100),
    settings JSONB,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE agent_config IS '智能体配置表';

-- 智能体工具配置表
CREATE TABLE agent_tool (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_config(id) ON DELETE CASCADE,
    tool_type VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    mcp_tool_id INTEGER REFERENCES mcp_tool(id),
    settings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE agent_tool IS '智能体工具配置表';

-- 智能体运行记录表
CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    status VARCHAR(50) DEFAULT 'running',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_ms INTEGER
);
COMMENT ON TABLE agent_runs IS '智能体运行记录表';

-- 智能体记忆表
CREATE TABLE agent_memories (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE agent_memories IS '智能体记忆存储表';

-- 工具执行记录表
CREATE TABLE tool_executions (
    id SERIAL PRIMARY KEY,
    tool_id VARCHAR(36) NOT NULL REFERENCES tools(id),
    agent_id VARCHAR(36),
    session_id VARCHAR(36),
    input_parameters JSONB,
    output_result JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_ms INTEGER
);
COMMENT ON TABLE tool_executions IS '工具执行记录表';

-- 助手知识图谱关联表
CREATE TABLE assistant_knowledge_graphs (
    id SERIAL PRIMARY KEY,
    assistant_id INTEGER NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    graph_id VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE assistant_knowledge_graphs IS '助手知识图谱关联表';

-- 问题表（问答助手）
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    assistant_id INTEGER NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    answer_text TEXT,
    views_count INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    answer_mode VARCHAR(20) DEFAULT 'default',
    use_cache BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE questions IS '问答助手问题表';

-- 问题文档分段关联表
CREATE TABLE question_document_segments (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    segment_id INTEGER NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    relevance_score FLOAT DEFAULT 0.0,
    is_enabled BOOLEAN DEFAULT TRUE
);
COMMENT ON TABLE question_document_segments IS '问题文档分段关联表';

-- 配置历史表
CREATE TABLE config_history (
    id SERIAL PRIMARY KEY,
    config_id VARCHAR(36) NOT NULL REFERENCES system_configs(id) ON DELETE CASCADE,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(36) REFERENCES users(id),
    change_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE config_history IS '配置变更历史表';

-- 服务健康记录表
CREATE TABLE service_health_records (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    response_time_ms INTEGER,
    error_message TEXT,
    metadata JSONB,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE service_health_records IS '服务健康检查记录表';

-- =====================================================
-- 4. 关联表（多对多关系）
-- =====================================================

-- 用户角色关联表
CREATE TABLE user_role (
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);
COMMENT ON TABLE user_role IS '用户角色关联表';

-- 角色权限关联表
CREATE TABLE role_permission (
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(36) NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);
COMMENT ON TABLE role_permission IS '角色权限关联表';

-- 助手知识库关联表
CREATE TABLE assistant_knowledge_base (
    assistant_id INTEGER NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    PRIMARY KEY (assistant_id, knowledge_base_id)
);
COMMENT ON TABLE assistant_knowledge_base IS '助手知识库关联表';

-- 智能体工具关联表
CREATE TABLE agent_tool_association (
    agent_definition_id INTEGER NOT NULL REFERENCES agent_definitions(id) ON DELETE CASCADE,
    tool_id VARCHAR(36) NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    "order" INTEGER,
    condition VARCHAR(255),
    parameters JSONB,
    PRIMARY KEY (agent_definition_id, tool_id)
);
COMMENT ON TABLE agent_tool_association IS '智能体工具关联表';

-- =====================================================
-- 5. 索引创建
-- =====================================================

-- 用户相关索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- 知识库相关索引
CREATE INDEX idx_knowledge_bases_name ON knowledge_bases(name);
CREATE INDEX idx_knowledge_bases_type ON knowledge_bases(type);
CREATE INDEX idx_documents_kb_id ON documents(knowledge_base_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_document_chunks_doc_id ON document_chunks(document_id);

-- 助手相关索引
CREATE INDEX idx_assistants_name ON assistants(name);
CREATE INDEX idx_conversations_assistant_id ON conversations(assistant_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- 权限相关索引
CREATE INDEX idx_resource_permissions_user_id ON resource_permissions(user_id);
CREATE INDEX idx_resource_permissions_resource ON resource_permissions(resource_type, resource_id);
CREATE INDEX idx_knowledge_base_access_user_id ON knowledge_base_access(user_id);
CREATE INDEX idx_assistant_access_user_id ON assistant_access(user_id);

-- MCP相关索引
CREATE INDEX idx_mcp_service_config_status ON mcp_service_config(status);
CREATE INDEX idx_mcp_tool_service_id ON mcp_tool(service_id);
CREATE INDEX idx_mcp_tool_execution_tool_id ON mcp_tool_execution(tool_id);
CREATE INDEX idx_mcp_tool_execution_status ON mcp_tool_execution(status);
CREATE INDEX idx_mcp_tool_execution_started_at ON mcp_tool_execution(started_at);

-- 工具相关索引
CREATE INDEX idx_tools_name ON tools(name);
CREATE INDEX idx_tools_category ON tools(category);
CREATE INDEX idx_tool_executions_tool_id ON tool_executions(tool_id);
CREATE INDEX idx_tool_executions_status ON tool_executions(status);

-- 智能体相关索引
CREATE INDEX idx_agent_definitions_creator_id ON agent_definitions(creator_id);
CREATE INDEX idx_agent_runs_agent_id ON agent_runs(agent_id);
CREATE INDEX idx_agent_runs_session_id ON agent_runs(session_id);
CREATE INDEX idx_agent_memories_agent_id ON agent_memories(agent_id);

-- 系统配置相关索引
CREATE INDEX idx_system_configs_key ON system_configs(key);
CREATE INDEX idx_system_configs_category_id ON system_configs(category_id);

-- 复合索引
CREATE UNIQUE INDEX idx_mcp_tool_service_name ON mcp_tool(service_id, tool_name);
CREATE UNIQUE INDEX idx_agent_tool_agent_name ON agent_tool(agent_id, tool_name);

-- =====================================================
-- 6. 初始数据插入
-- =====================================================

-- 插入默认配置类别
INSERT INTO config_categories (id, name, description, "order", is_system) VALUES
('cat-system', '系统配置', '系统核心配置项', 1, TRUE),
('cat-model', '模型配置', '模型提供商和API配置', 2, TRUE),
('cat-security', '安全配置', '安全和权限相关配置', 3, TRUE),
('cat-feature', '功能配置', '功能开关和参数配置', 4, TRUE),
('cat-ui', '界面配置', '用户界面相关配置', 5, FALSE);

-- 插入默认角色
INSERT INTO roles (id, name, description, is_default) VALUES
('role-admin', '系统管理员', '拥有系统所有权限', FALSE),
('role-user', '普通用户', '基础用户权限', TRUE),
('role-developer', '开发者', '开发和调试权限', FALSE);

-- 插入默认权限
INSERT INTO permissions (id, name, code, description, resource) VALUES
('perm-user-read', '用户查看', 'user:read', '查看用户信息', 'user'),
('perm-user-write', '用户编辑', 'user:write', '编辑用户信息', 'user'),
('perm-user-delete', '用户删除', 'user:delete', '删除用户', 'user'),
('perm-kb-read', '知识库查看', 'knowledge_base:read', '查看知识库', 'knowledge_base'),
('perm-kb-write', '知识库编辑', 'knowledge_base:write', '编辑知识库', 'knowledge_base'),
('perm-kb-delete', '知识库删除', 'knowledge_base:delete', '删除知识库', 'knowledge_base'),
('perm-assistant-read', '助手查看', 'assistant:read', '查看助手', 'assistant'),
('perm-assistant-write', '助手编辑', 'assistant:write', '编辑助手', 'assistant'),
('perm-assistant-delete', '助手删除', 'assistant:delete', '删除助手', 'assistant'),
('perm-system-config', '系统配置', 'system:config', '系统配置管理', 'system');

-- 分配角色权限
INSERT INTO role_permission (role_id, permission_id) VALUES
-- 管理员拥有所有权限
('role-admin', 'perm-user-read'),
('role-admin', 'perm-user-write'),
('role-admin', 'perm-user-delete'),
('role-admin', 'perm-kb-read'),
('role-admin', 'perm-kb-write'),
('role-admin', 'perm-kb-delete'),
('role-admin', 'perm-assistant-read'),
('role-admin', 'perm-assistant-write'),
('role-admin', 'perm-assistant-delete'),
('role-admin', 'perm-system-config'),
-- 普通用户基础权限
('role-user', 'perm-kb-read'),
('role-user', 'perm-assistant-read'),
-- 开发者权限
('role-developer', 'perm-kb-read'),
('role-developer', 'perm-kb-write'),
('role-developer', 'perm-assistant-read'),
('role-developer', 'perm-assistant-write');

-- 插入默认系统配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system) VALUES
('cfg-app-name', 'app.name', 'ZZ-Backend-Lite', 'string', 'ZZ-Backend-Lite', 'cat-system', '应用名称', TRUE),
('cfg-app-version', 'app.version', '1.0.0', 'string', '1.0.0', 'cat-system', '应用版本', TRUE),
('cfg-debug-mode', 'app.debug', 'false', 'boolean', 'false', 'cat-system', '调试模式', TRUE),
('cfg-max-upload-size', 'upload.max_size_mb', '100', 'number', '100', 'cat-system', '最大上传文件大小(MB)', FALSE),
('cfg-session-timeout', 'security.session_timeout_hours', '24', 'number', '24', 'cat-security', '会话超时时间(小时)', FALSE),
('cfg-enable-registration', 'security.enable_registration', 'true', 'boolean', 'true', 'cat-security', '是否允许用户注册', FALSE),
('cfg-default-model', 'model.default_provider', 'openai', 'string', 'openai', 'cat-model', '默认模型提供商', FALSE),
('cfg-enable-voice', 'feature.enable_voice', 'true', 'boolean', 'true', 'cat-feature', '是否启用语音功能', FALSE),
('cfg-ui-theme', 'ui.default_theme', 'light', 'string', 'light', 'cat-ui', '默认UI主题', FALSE);

-- 创建默认管理员用户（密码: admin123）
INSERT INTO users (id, username, email, hashed_password, full_name, is_superuser) VALUES
('user-admin', 'admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJflHQrxG', '系统管理员', TRUE);

-- 分配管理员角色
INSERT INTO user_role (user_id, role_id) VALUES
('user-admin', 'role-admin');

-- 创建管理员默认设置
INSERT INTO user_settings (user_id, theme, language) VALUES
('user-admin', 'light', 'zh-CN');

-- 创建管理员资源配额
INSERT INTO user_resource_quotas (user_id, max_knowledge_bases, max_assistants, daily_model_tokens, monthly_model_tokens) VALUES
('user-admin', -1, -1, -1, -1);

-- =====================================================
-- 7. 触发器和函数
-- =====================================================

-- 创建更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表添加更新时间戳触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_permissions_updated_at BEFORE UPDATE ON permissions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_configs_updated_at BEFORE UPDATE ON system_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_knowledge_bases_updated_at BEFORE UPDATE ON knowledge_bases FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_assistants_updated_at BEFORE UPDATE ON assistants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agent_definitions_updated_at BEFORE UPDATE ON agent_definitions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tools_updated_at BEFORE UPDATE ON tools FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_mcp_service_config_updated_at BEFORE UPDATE ON mcp_service_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_mcp_tool_updated_at BEFORE UPDATE ON mcp_tool FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agent_config_updated_at BEFORE UPDATE ON agent_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agent_tool_updated_at BEFORE UPDATE ON agent_tool FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 8. 视图创建
-- =====================================================

-- 用户权限视图
CREATE VIEW user_permissions_view AS
SELECT 
    u.id as user_id,
    u.username,
    u.email,
    r.name as role_name,
    p.name as permission_name,
    p.code as permission_code,
    p.resource
FROM users u
JOIN user_role ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
JOIN role_permission rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id;

-- 助手统计视图
CREATE VIEW assistant_stats_view AS
SELECT 
    a.id,
    a.name,
    COUNT(DISTINCT c.id) as conversation_count,
    COUNT(DISTINCT m.id) as message_count,
    COUNT(DISTINCT akb.knowledge_base_id) as knowledge_base_count,
    a.created_at,
    a.updated_at
FROM assistants a
LEFT JOIN conversations c ON a.id = c.assistant_id
LEFT JOIN messages m ON c.id = m.conversation_id
LEFT JOIN assistant_knowledge_base akb ON a.id = akb.assistant_id
GROUP BY a.id, a.name, a.created_at, a.updated_at;

-- 知识库统计视图
CREATE VIEW knowledge_base_stats_view AS
SELECT 
    kb.id,
    kb.name,
    kb.type,
    COUNT(DISTINCT d.id) as document_count,
    COUNT(DISTINCT dc.id) as chunk_count,
    SUM(d.file_size) as total_size_bytes,
    kb.total_tokens,
    kb.created_at,
    kb.updated_at
FROM knowledge_bases kb
LEFT JOIN documents d ON kb.id = d.knowledge_base_id
LEFT JOIN document_chunks dc ON d.id = dc.document_id
GROUP BY kb.id, kb.name, kb.type, kb.total_tokens, kb.created_at, kb.updated_at;

-- =====================================================
-- 完成数据库初始化
-- =====================================================

-- 输出完成信息
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成！';
    RAISE NOTICE '默认管理员账户: admin / admin123';
    RAISE NOTICE '请及时修改默认密码并配置相关服务';
END $$; 