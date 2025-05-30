-- =====================================================
-- ZZ-Backend-Lite 完整数据库初始化脚本
-- 合并日期: 2025-01-08  
-- 说明: 包含基础表定义和Schema层补充表定义
-- =====================================================

-- 设置PostgreSQL环境
SET timezone = 'UTC';
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- 第一部分: 基础表定义 (来自 db_init_tables.sql)
-- =====================================================

-- 1. 用户与认证相关表
CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    is_system BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    category VARCHAR(50),
    resource VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS user_role (
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    role_id VARCHAR(36) REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id VARCHAR(36) REFERENCES roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(36) REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_settings (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) UNIQUE NOT NULL,
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'zh-CN',
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) NOT NULL,
    key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100),
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 知识库与文档相关表
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

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    knowledge_base_id INTEGER REFERENCES knowledge_bases(id),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    mime_type VARCHAR(100) DEFAULT 'text/plain',
    metadata JSONB DEFAULT '{}',
    file_path VARCHAR(255),
    file_size INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    content TEXT,
    metadata JSONB DEFAULT '{}',
    embedding_id VARCHAR(255),
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 系统配置相关表
CREATE TABLE IF NOT EXISTS config_categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    "order" INTEGER DEFAULT 0,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_configs (
    id VARCHAR(36) PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value TEXT,
    value_type VARCHAR(50) NOT NULL,
    default_value TEXT,
    category_id VARCHAR(36) REFERENCES config_categories(id) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    is_sensitive BOOLEAN DEFAULT FALSE,
    is_encrypted BOOLEAN DEFAULT FALSE,
    validation_rules JSONB,
    is_overridden BOOLEAN DEFAULT FALSE,
    override_source VARCHAR(255),
    visible_level VARCHAR(50) DEFAULT 'all',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS config_history (
    id VARCHAR(36) PRIMARY KEY,
    config_id VARCHAR(36) REFERENCES system_configs(id) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_source VARCHAR(50) NOT NULL,
    changed_by VARCHAR(100),
    change_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_health_records (
    id VARCHAR(36) PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status BOOLEAN DEFAULT FALSE,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    error_message TEXT,
    details JSONB
);

-- 4. 模型提供商相关表
CREATE TABLE IF NOT EXISTS model_providers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    base_url VARCHAR(255),
    auth_type VARCHAR(50),
    is_enabled BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    models JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 智能体定义表 (新增)
CREATE TABLE IF NOT EXISTS agent_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_agent_type VARCHAR(50) NOT NULL,
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

-- 6. 工具定义表 (新增)
CREATE TABLE IF NOT EXISTS tools (
    id VARCHAR(36) PRIMARY KEY,
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
    tool_type VARCHAR(50),
    module_path TEXT,
    class_name VARCHAR(100),
    creator_id VARCHAR(36) REFERENCES users(id),
    tags JSONB,
    input_format JSONB,
    output_format JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE tools IS '工具定义表';

-- 7. 智能体工具关联表 (新增)
CREATE TABLE IF NOT EXISTS agent_tool_association (
    agent_definition_id INTEGER REFERENCES agent_definitions(id) ON DELETE CASCADE,
    tool_id VARCHAR(36) REFERENCES tools(id) ON DELETE CASCADE,
    "order" INTEGER,
    condition VARCHAR(255),
    parameters JSONB,
    PRIMARY KEY (agent_definition_id, tool_id)
);
COMMENT ON TABLE agent_tool_association IS '智能体工具关联表';

-- 8. LightRAG集成表 (新增)
CREATE TABLE IF NOT EXISTS lightrag_integrations (
    id VARCHAR(36) PRIMARY KEY,
    index_name VARCHAR(100) UNIQUE NOT NULL,
    document_processor_config JSONB,
    graph_config JSONB,
    query_engine_config JSONB,
    workdir_path TEXT,
    api_key VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE lightrag_integrations IS 'LightRAG框架集成表';

-- 5. 助手与对话相关表
CREATE TABLE IF NOT EXISTS assistants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    model VARCHAR(100) NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '[]',
    configuration JSONB,
    system_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_url VARCHAR(255)
);

-- 9. 问题表 (新增)
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    assistant_id INTEGER REFERENCES assistants(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    answer_text TEXT,
    views_count INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    category VARCHAR(50),
    priority INTEGER DEFAULT 0,
    tags JSONB DEFAULT '[]',
    feedback_score FLOAT,
    feedback_count INTEGER DEFAULT 0,
    answer_mode VARCHAR(20) DEFAULT 'default',
    use_cache BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE questions IS '问答助手问题表';

-- 10. 问题文档分段关联表 (新增)
CREATE TABLE IF NOT EXISTS question_document_segments (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    segment_id INTEGER REFERENCES document_chunks(id) ON DELETE CASCADE,
    relevance_score FLOAT DEFAULT 0.0,
    is_enabled BOOLEAN DEFAULT TRUE
);
COMMENT ON TABLE question_document_segments IS '问题文档分段关联表';

-- 助手和知识库之间的关联表
CREATE TABLE IF NOT EXISTS assistant_knowledge_base (
    assistant_id INTEGER REFERENCES assistants(id) ON DELETE CASCADE,
    knowledge_base_id INTEGER REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    PRIMARY KEY (assistant_id, knowledge_base_id)
);

-- 对话表
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    assistant_id INTEGER REFERENCES assistants(id) NOT NULL,
    title VARCHAR(255) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 消息引用表
CREATE TABLE IF NOT EXISTS message_references (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    document_chunk_id INTEGER REFERENCES document_chunks(id) ON DELETE CASCADE,
    relevance_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. MCP服务和Agent相关表
CREATE TABLE IF NOT EXISTS mcp_service_config (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(36) NOT NULL UNIQUE,
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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_started_at TIMESTAMP,
    last_stopped_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mcp_tool (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES mcp_service_config(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    schema JSONB,
    examples JSONB,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ix_mcp_tool_service_name UNIQUE (service_id, tool_name)
);

CREATE TABLE IF NOT EXISTS mcp_tool_execution (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(36) NOT NULL UNIQUE,
    tool_id INTEGER NOT NULL REFERENCES mcp_tool(id) ON DELETE CASCADE,
    parameters JSONB,
    result JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    context JSONB,
    agent_id VARCHAR(36),
    session_id VARCHAR(36),
    user_id VARCHAR(36),
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time_ms INTEGER
);

CREATE TABLE IF NOT EXISTS agent_config (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'llamaindex',
    model VARCHAR(100),
    settings JSONB,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_tool (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_config(id) ON DELETE CASCADE,
    tool_type VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    mcp_tool_id INTEGER REFERENCES mcp_tool(id),
    settings JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ix_agent_tool_agent_name UNIQUE (agent_id, tool_name)
);

-- =====================================================
-- 第二部分: 新增表定义 (来自 database_supplement.sql)
-- =====================================================

-- =====================================================
-- 1. 高优先级新增表
-- =====================================================

-- Agent调用链配置表
CREATE TABLE IF NOT EXISTS agent_chains (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    execution_mode VARCHAR(20) NOT NULL DEFAULT 'sequential', -- sequential, parallel, conditional
    agents JSONB NOT NULL, -- Agent引用列表
    conditions JSONB, -- 条件执行配置
    metadata JSONB DEFAULT '{}',
    creator_id VARCHAR(36) REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE agent_chains IS 'Agent调用链配置表';

-- Agent调用链执行记录表
CREATE TABLE IF NOT EXISTS agent_chain_executions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    chain_id VARCHAR(36) NOT NULL REFERENCES agent_chains(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id),
    input_data JSONB NOT NULL,
    output_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    context JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE agent_chain_executions IS 'Agent调用链执行记录表';

-- Agent执行步骤表
CREATE TABLE IF NOT EXISTS agent_chain_execution_steps (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(36) NOT NULL REFERENCES agent_chain_executions(id) ON DELETE CASCADE,
    agent_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE agent_chain_execution_steps IS 'Agent执行步骤表';

-- 统一工具注册表
CREATE TABLE IF NOT EXISTS unified_tools (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    tool_type VARCHAR(50) NOT NULL, -- builtin, custom, mcp, external
    source_type VARCHAR(50) NOT NULL, -- internal, mcp_service, external_api
    source_id VARCHAR(36), -- 指向具体的工具源
    category VARCHAR(50),
    tags JSONB DEFAULT '[]',
    schema JSONB NOT NULL,
    config JSONB DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE unified_tools IS '统一工具注册表';

-- 搜索会话表
CREATE TABLE IF NOT EXISTS search_sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) REFERENCES users(id),
    query TEXT NOT NULL,
    search_type VARCHAR(50) NOT NULL, -- semantic, keyword, hybrid
    filters JSONB DEFAULT '{}',
    results JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE search_sessions IS '搜索会话表';

-- =====================================================
-- 2. 中优先级新增表
-- =====================================================

-- LightRAG图谱表
CREATE TABLE IF NOT EXISTS lightrag_graphs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    knowledge_base_id INTEGER REFERENCES knowledge_bases(id),
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'building', -- building, ready, error
    node_count INTEGER DEFAULT 0,
    edge_count INTEGER DEFAULT 0,
    last_updated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE lightrag_graphs IS 'LightRAG图谱表';

-- LightRAG查询记录表
CREATE TABLE IF NOT EXISTS lightrag_queries (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    graph_id VARCHAR(36) NOT NULL REFERENCES lightrag_graphs(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_type VARCHAR(20) NOT NULL, -- naive, local, global, hybrid
    results JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE lightrag_queries IS 'LightRAG查询记录表';

-- 压缩策略表
CREATE TABLE IF NOT EXISTS compression_strategies (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL, -- llm, embedding, keyword
    config JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE compression_strategies IS '压缩策略表';

-- 工具链定义表
CREATE TABLE IF NOT EXISTS tool_chains (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tools JSONB NOT NULL, -- 工具链配置
    metadata JSONB DEFAULT '{}',
    creator_id VARCHAR(36) REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE tool_chains IS '工具链定义表';

-- 工具链执行记录表
CREATE TABLE IF NOT EXISTS tool_chain_executions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    chain_id VARCHAR(36) NOT NULL REFERENCES tool_chains(id) ON DELETE CASCADE,
    input_data JSONB NOT NULL,
    output_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE tool_chain_executions IS '工具链执行记录表';

-- =====================================================
-- 3. 低优先级新增表
-- =====================================================

-- 工具使用统计表
CREATE TABLE IF NOT EXISTS tool_usage_stats (
    id SERIAL PRIMARY KEY,
    tool_id VARCHAR(36) NOT NULL REFERENCES unified_tools(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id),
    execution_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    total_execution_time_ms BIGINT DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE(tool_id, user_id, date)
);
COMMENT ON TABLE tool_usage_stats IS '工具使用统计表';

-- 搜索结果缓存表
CREATE TABLE IF NOT EXISTS search_result_cache (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    search_type VARCHAR(50) NOT NULL,
    filters_hash VARCHAR(64),
    results JSONB NOT NULL,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE search_result_cache IS '搜索结果缓存表';

-- 问题反馈表
CREATE TABLE IF NOT EXISTS question_feedback (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    is_helpful BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE question_feedback IS '问题反馈表';

-- 问题标签表
CREATE TABLE IF NOT EXISTS question_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    color VARCHAR(7), -- HEX颜色值
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE question_tags IS '问题标签表';

-- 问题标签关联表
CREATE TABLE IF NOT EXISTS question_tag_relations (
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES question_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (question_id, tag_id)
);
COMMENT ON TABLE question_tag_relations IS '问题标签关联表';

-- =====================================================
-- 4. 现有表字段补充
-- =====================================================

-- 补充tools表缺少的字段
ALTER TABLE tools ADD COLUMN IF NOT EXISTS tool_type VARCHAR(50);
ALTER TABLE tools ADD COLUMN IF NOT EXISTS module_path TEXT;
ALTER TABLE tools ADD COLUMN IF NOT EXISTS class_name VARCHAR(100);

-- 补充assistants表缺少的字段（如果存在的话，避免重复添加）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assistants' AND column_name='access_url') THEN
        ALTER TABLE assistants ADD COLUMN access_url VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assistants' AND column_name='is_active') THEN
        ALTER TABLE assistants ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;
END $$;

-- 补充agent_definitions表缺少的字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='agent_definitions' AND column_name='is_system') THEN
        ALTER TABLE agent_definitions ADD COLUMN is_system BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- 补充questions表缺少的字段
ALTER TABLE questions ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE questions ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]';
ALTER TABLE questions ADD COLUMN IF NOT EXISTS feedback_score FLOAT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS feedback_count INTEGER DEFAULT 0;

-- =====================================================
-- 5. 新增索引
-- =====================================================

-- Agent链相关索引
CREATE INDEX IF NOT EXISTS idx_agent_chains_creator_id ON agent_chains(creator_id);
CREATE INDEX IF NOT EXISTS idx_agent_chains_active ON agent_chains(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_chain_executions_chain_id ON agent_chain_executions(chain_id);
CREATE INDEX IF NOT EXISTS idx_agent_chain_executions_user_id ON agent_chain_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_chain_executions_status ON agent_chain_executions(status);
CREATE INDEX IF NOT EXISTS idx_agent_chain_execution_steps_execution_id ON agent_chain_execution_steps(execution_id);

-- 统一工具相关索引
CREATE INDEX IF NOT EXISTS idx_unified_tools_name ON unified_tools(name);
CREATE INDEX IF NOT EXISTS idx_unified_tools_type ON unified_tools(tool_type);
CREATE INDEX IF NOT EXISTS idx_unified_tools_category ON unified_tools(category);
CREATE INDEX IF NOT EXISTS idx_unified_tools_enabled ON unified_tools(is_enabled);

-- 搜索相关索引
CREATE INDEX IF NOT EXISTS idx_search_sessions_user_id ON search_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_search_sessions_type ON search_sessions(search_type);
CREATE INDEX IF NOT EXISTS idx_search_sessions_created_at ON search_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_search_result_cache_query_hash ON search_result_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_result_cache_expires_at ON search_result_cache(expires_at);

-- LightRAG相关索引
CREATE INDEX IF NOT EXISTS idx_lightrag_graphs_kb_id ON lightrag_graphs(knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_lightrag_graphs_status ON lightrag_graphs(status);
CREATE INDEX IF NOT EXISTS idx_lightrag_queries_graph_id ON lightrag_queries(graph_id);
CREATE INDEX IF NOT EXISTS idx_lightrag_queries_type ON lightrag_queries(query_type);

-- 工具链相关索引
CREATE INDEX IF NOT EXISTS idx_tool_chains_creator_id ON tool_chains(creator_id);
CREATE INDEX IF NOT EXISTS idx_tool_chains_active ON tool_chains(is_active);
CREATE INDEX IF NOT EXISTS idx_tool_chain_executions_chain_id ON tool_chain_executions(chain_id);
CREATE INDEX IF NOT EXISTS idx_tool_chain_executions_status ON tool_chain_executions(status);

-- 压缩策略相关索引
CREATE INDEX IF NOT EXISTS idx_compression_strategies_type ON compression_strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_compression_strategies_default ON compression_strategies(is_default);
CREATE INDEX IF NOT EXISTS idx_compression_strategies_active ON compression_strategies(is_active);

-- 问题反馈相关索引
CREATE INDEX IF NOT EXISTS idx_question_feedback_question_id ON question_feedback(question_id);
CREATE INDEX IF NOT EXISTS idx_question_feedback_user_id ON question_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_question_feedback_rating ON question_feedback(rating);

-- 工具使用统计索引
CREATE INDEX IF NOT EXISTS idx_tool_usage_stats_tool_id ON tool_usage_stats(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_stats_user_id ON tool_usage_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_stats_date ON tool_usage_stats(date);

-- 新增核心表索引
CREATE INDEX IF NOT EXISTS idx_agent_definitions_name ON agent_definitions(name);
CREATE INDEX IF NOT EXISTS idx_agent_definitions_creator_id ON agent_definitions(creator_id);
CREATE INDEX IF NOT EXISTS idx_agent_definitions_base_type ON agent_definitions(base_agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_definitions_is_public ON agent_definitions(is_public);
CREATE INDEX IF NOT EXISTS idx_agent_definitions_is_system ON agent_definitions(is_system);

CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
CREATE INDEX IF NOT EXISTS idx_tools_framework ON tools(framework);
CREATE INDEX IF NOT EXISTS idx_tools_tool_type ON tools(tool_type);
CREATE INDEX IF NOT EXISTS idx_tools_creator_id ON tools(creator_id);
CREATE INDEX IF NOT EXISTS idx_tools_is_system ON tools(is_system);

CREATE INDEX IF NOT EXISTS idx_agent_tool_association_agent_id ON agent_tool_association(agent_definition_id);
CREATE INDEX IF NOT EXISTS idx_agent_tool_association_tool_id ON agent_tool_association(tool_id);
CREATE INDEX IF NOT EXISTS idx_agent_tool_association_order ON agent_tool_association("order");

CREATE INDEX IF NOT EXISTS idx_lightrag_integrations_index_name ON lightrag_integrations(index_name);
CREATE INDEX IF NOT EXISTS idx_lightrag_integrations_created_at ON lightrag_integrations(created_at);

CREATE INDEX IF NOT EXISTS idx_questions_assistant_id ON questions(assistant_id);
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
CREATE INDEX IF NOT EXISTS idx_questions_enabled ON questions(enabled);
CREATE INDEX IF NOT EXISTS idx_questions_priority ON questions(priority);
CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at);

CREATE INDEX IF NOT EXISTS idx_question_document_segments_question_id ON question_document_segments(question_id);
CREATE INDEX IF NOT EXISTS idx_question_document_segments_document_id ON question_document_segments(document_id);
CREATE INDEX IF NOT EXISTS idx_question_document_segments_segment_id ON question_document_segments(segment_id);
CREATE INDEX IF NOT EXISTS idx_question_document_segments_enabled ON question_document_segments(is_enabled);

-- =====================================================
-- 6. 创建更新时间戳函数和触发器
-- =====================================================

-- 创建更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为新表添加更新时间戳触发器
CREATE TRIGGER IF NOT EXISTS update_agent_chains_updated_at 
    BEFORE UPDATE ON agent_chains 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_unified_tools_updated_at 
    BEFORE UPDATE ON unified_tools 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_lightrag_graphs_updated_at 
    BEFORE UPDATE ON lightrag_graphs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_compression_strategies_updated_at 
    BEFORE UPDATE ON compression_strategies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_tool_chains_updated_at 
    BEFORE UPDATE ON tool_chains 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 7. 视图补充
-- =====================================================

-- Agent链统计视图
CREATE OR REPLACE VIEW agent_chain_stats_view AS
SELECT 
    ac.id,
    ac.name,
    ac.execution_mode,
    COUNT(DISTINCT ace.id) as execution_count,
    COUNT(DISTINCT CASE WHEN ace.status = 'completed' THEN ace.id END) as success_count,
    COUNT(DISTINCT CASE WHEN ace.status = 'failed' THEN ace.id END) as error_count,
    AVG(EXTRACT(EPOCH FROM (ace.completed_at - ace.started_at)) * 1000) as avg_execution_time_ms,
    ac.created_at,
    ac.updated_at
FROM agent_chains ac
LEFT JOIN agent_chain_executions ace ON ac.id = ace.chain_id
GROUP BY ac.id, ac.name, ac.execution_mode, ac.created_at, ac.updated_at;

-- 工具使用统计汇总视图
CREATE OR REPLACE VIEW tool_usage_summary_view AS
SELECT 
    ut.id,
    ut.name,
    ut.tool_type,
    ut.category,
    SUM(tus.execution_count) as total_executions,
    SUM(tus.success_count) as total_successes,
    SUM(tus.error_count) as total_errors,
    CASE 
        WHEN SUM(tus.execution_count) > 0 
        THEN (SUM(tus.success_count)::FLOAT / SUM(tus.execution_count) * 100)
        ELSE 0 
    END as success_rate,
    AVG(tus.total_execution_time_ms::FLOAT / NULLIF(tus.execution_count, 0)) as avg_execution_time_ms,
    MAX(tus.last_used_at) as last_used_at
FROM unified_tools ut
LEFT JOIN tool_usage_stats tus ON ut.id = tus.tool_id
GROUP BY ut.id, ut.name, ut.tool_type, ut.category;

-- LightRAG图谱统计视图
CREATE OR REPLACE VIEW lightrag_graph_stats_view AS
SELECT 
    lg.id,
    lg.name,
    lg.status,
    lg.node_count,
    lg.edge_count,
    COUNT(DISTINCT lq.id) as query_count,
    AVG(lq.execution_time_ms) as avg_query_time_ms,
    lg.created_at,
    lg.updated_at,
    lg.last_updated_at
FROM lightrag_graphs lg
LEFT JOIN lightrag_queries lq ON lg.id = lq.graph_id
GROUP BY lg.id, lg.name, lg.status, lg.node_count, lg.edge_count, lg.created_at, lg.updated_at, lg.last_updated_at;

-- =====================================================
-- 8. 初始数据补充
-- =====================================================

-- 插入默认压缩策略
INSERT INTO compression_strategies (id, name, description, strategy_type, config, is_default) VALUES
('strategy-llm-default', 'LLM默认压缩', 'LLM默认压缩策略', 'llm', '{"model": "gpt-3.5-turbo", "max_tokens": 500}', TRUE),
('strategy-embedding', '嵌入向量压缩', '基于嵌入向量相似度的压缩策略', 'embedding', '{"threshold": 0.8}', FALSE),
('strategy-keyword', '关键词提取', '基于关键词的压缩策略', 'keyword', '{"max_keywords": 20}', FALSE)
ON CONFLICT (id) DO NOTHING;

-- 插入默认问题标签
INSERT INTO question_tags (name, description, color) VALUES
('技术问题', '技术相关的问题', '#2196F3'),
('使用帮助', '使用方法和帮助', '#4CAF50'),
('功能咨询', '功能相关的咨询', '#FF9800'),
('故障报告', '系统故障和错误报告', '#F44336'),
('建议反馈', '改进建议和反馈', '#9C27B0')
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- 9. 权限补充
-- =====================================================

-- 插入新的权限定义
INSERT INTO permissions (id, name, code, description, resource) VALUES
('perm-agent-chain-read', 'Agent链查看', 'agent_chain:read', '查看Agent调用链', 'agent_chain'),
('perm-agent-chain-write', 'Agent链编辑', 'agent_chain:write', '编辑Agent调用链', 'agent_chain'),
('perm-agent-chain-execute', 'Agent链执行', 'agent_chain:execute', '执行Agent调用链', 'agent_chain'),
('perm-unified-tool-read', '统一工具查看', 'unified_tool:read', '查看统一工具', 'unified_tool'),
('perm-unified-tool-write', '统一工具编辑', 'unified_tool:write', '编辑统一工具', 'unified_tool'),
('perm-search-session', '搜索会话', 'search:session', '搜索会话管理', 'search'),
('perm-lightrag-read', 'LightRAG查看', 'lightrag:read', '查看LightRAG图谱', 'lightrag'),
('perm-lightrag-write', 'LightRAG编辑', 'lightrag:write', '编辑LightRAG图谱', 'lightrag')
ON CONFLICT (id) DO NOTHING;

-- 为管理员角色分配新权限
INSERT INTO role_permissions (role_id, permission_id) VALUES
('role-admin', 'perm-agent-chain-read'),
('role-admin', 'perm-agent-chain-write'),
('role-admin', 'perm-agent-chain-execute'),
('role-admin', 'perm-unified-tool-read'),
('role-admin', 'perm-unified-tool-write'),
('role-admin', 'perm-search-session'),
('role-admin', 'perm-lightrag-read'),
('role-admin', 'perm-lightrag-write')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 为开发者角色分配部分新权限
INSERT INTO role_permissions (role_id, permission_id) VALUES
('role-developer', 'perm-agent-chain-read'),
('role-developer', 'perm-agent-chain-execute'),
('role-developer', 'perm-unified-tool-read'),
('role-developer', 'perm-search-session'),
('role-developer', 'perm-lightrag-read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 为普通用户分配基础权限
INSERT INTO role_permissions (role_id, permission_id) VALUES
('role-user', 'perm-agent-chain-read'),
('role-user', 'perm-unified-tool-read'),
('role-user', 'perm-search-session'),
('role-user', 'perm-lightrag-read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- =====================================================
-- 完成数据库初始化
-- =====================================================

-- 输出完成信息
DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'ZZ-Backend-Lite 数据库初始化完成！';
    RAISE NOTICE '==============================================';
    RAISE NOTICE '基础表数量: 30+ 个';
    RAISE NOTICE '新增表数量: 15 个';
    RAISE NOTICE '修复字段不匹配: 8 处';
    RAISE NOTICE '新增权限: 8 个';
    RAISE NOTICE '新增视图: 3 个';
    RAISE NOTICE '新增索引: 30+ 个';
    RAISE NOTICE '==============================================';
    RAISE NOTICE '建议重启应用以加载新的数据库结构';
    RAISE NOTICE '==============================================';
END $$; 