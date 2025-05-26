-- 智能体记忆系统数据库初始化脚本
-- 此脚本包含创建记忆系统所需的所有表、索引和约束

-- 确保pgvector扩展已安装
CREATE EXTENSION IF NOT EXISTS vector;

-- 智能体记忆绑定关系表
CREATE TABLE IF NOT EXISTS agent_memories (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL UNIQUE,
    memory_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_agent_memories_agent_id UNIQUE (agent_id)
);

COMMENT ON TABLE agent_memories IS '智能体记忆绑定关系表';
COMMENT ON COLUMN agent_memories.agent_id IS '智能体ID';
COMMENT ON COLUMN agent_memories.memory_id IS '记忆ID';
COMMENT ON COLUMN agent_memories.created_at IS '创建时间';
COMMENT ON COLUMN agent_memories.updated_at IS '更新时间';

-- 记忆向量存储表
CREATE TABLE IF NOT EXISTS memory_vectors (
    id SERIAL PRIMARY KEY,
    memory_id VARCHAR(255) NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_memory_vectors_memory_id_key UNIQUE (memory_id, key)
);

CREATE INDEX IF NOT EXISTS idx_memory_vectors_memory_id ON memory_vectors(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_vectors_owner_id ON memory_vectors(owner_id);

-- 为向量列创建索引以支持相似度搜索
CREATE INDEX IF NOT EXISTS idx_memory_vectors_embedding ON memory_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE memory_vectors IS '记忆向量存储表';
COMMENT ON COLUMN memory_vectors.memory_id IS '记忆ID';
COMMENT ON COLUMN memory_vectors.owner_id IS '所有者ID';
COMMENT ON COLUMN memory_vectors.key IS '记忆键名';
COMMENT ON COLUMN memory_vectors.content IS '记忆内容';
COMMENT ON COLUMN memory_vectors.metadata IS '记忆元数据';
COMMENT ON COLUMN memory_vectors.embedding IS '内容向量嵌入';
COMMENT ON COLUMN memory_vectors.created_at IS '创建时间';
COMMENT ON COLUMN memory_vectors.updated_at IS '更新时间';

-- 记忆配置表
CREATE TABLE IF NOT EXISTS memory_configs (
    id SERIAL PRIMARY KEY,
    memory_id VARCHAR(255) NOT NULL UNIQUE,
    memory_type VARCHAR(50) NOT NULL,
    ttl INTEGER,
    max_tokens INTEGER,
    max_items INTEGER,
    retrieval_strategy VARCHAR(50) DEFAULT 'recency',
    storage_backend VARCHAR(50) DEFAULT 'in_memory',
    vector_backend VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_memory_configs_memory_id UNIQUE (memory_id)
);

COMMENT ON TABLE memory_configs IS '记忆配置表';
COMMENT ON COLUMN memory_configs.memory_id IS '记忆ID';
COMMENT ON COLUMN memory_configs.memory_type IS '记忆类型(SHORT_TERM, SEMANTIC, WORKING, EPISODIC, PROCEDURAL, NONE)';
COMMENT ON COLUMN memory_configs.ttl IS '记忆生存时间(秒)';
COMMENT ON COLUMN memory_configs.max_tokens IS '最大记忆token数';
COMMENT ON COLUMN memory_configs.max_items IS '最大记忆项数';
COMMENT ON COLUMN memory_configs.retrieval_strategy IS '检索策略(recency, relevance)';
COMMENT ON COLUMN memory_configs.storage_backend IS '存储后端(in_memory, redis, postgres)';
COMMENT ON COLUMN memory_configs.vector_backend IS '向量后端(milvus, elasticsearch, pgvector)';

-- 记忆操作日志表
CREATE TABLE IF NOT EXISTS memory_operations (
    id SERIAL PRIMARY KEY,
    memory_id VARCHAR(255) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    key VARCHAR(255),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    duration_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_memory_operations_memory_id FOREIGN KEY (memory_id)
        REFERENCES memory_configs(memory_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_operations_memory_id ON memory_operations(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_operations_created_at ON memory_operations(created_at);

COMMENT ON TABLE memory_operations IS '记忆操作日志表';
COMMENT ON COLUMN memory_operations.memory_id IS '记忆ID';
COMMENT ON COLUMN memory_operations.operation_type IS '操作类型(add, get, update, delete, query, clear)';
COMMENT ON COLUMN memory_operations.key IS '记忆键名';
COMMENT ON COLUMN memory_operations.success IS '操作是否成功';
COMMENT ON COLUMN memory_operations.error_message IS '错误信息';
COMMENT ON COLUMN memory_operations.duration_ms IS '操作耗时(毫秒)';
COMMENT ON COLUMN memory_operations.metadata IS '操作元数据';
COMMENT ON COLUMN memory_operations.created_at IS '操作时间';

-- 默认配置插入
INSERT INTO memory_configs (memory_id, memory_type, ttl, max_items, retrieval_strategy, storage_backend)
VALUES 
    ('default:short_term', 'SHORT_TERM', 3600, 50, 'recency', 'redis'),
    ('default:semantic', 'SEMANTIC', 86400, 1000, 'relevance', 'postgres'),
    ('default:null', 'NONE', NULL, NULL, 'recency', 'in_memory')
ON CONFLICT (memory_id) DO NOTHING;
