-- 框架配置初始化脚本 (通用)
-- 为各种AI框架创建默认配置

-- LlamaIndex框架配置
INSERT INTO framework_configs (
    id,
    framework_name,
    settings,
    is_enabled,
    priority,
    capabilities,
    version,
    created_at,
    updated_at
)
VALUES (
    'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6',
    'llamaindex',
    '{
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "storage_context_type": "default",
        "response_mode": "compact",
        "similarity_top_k": 5,
        "node_postprocessors": ["keyword_filter", "similarity_filter"],
        "default_index_type": "vector_store"
    }',
    true,
    100,
    '["embeddings", "retrieval", "document_processing", "agent", "chat"]',
    '0.9.48',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- OWL框架配置
INSERT INTO framework_configs (
    id,
    framework_name,
    settings,
    is_enabled,
    priority,
    capabilities,
    version,
    created_at,
    updated_at
)
VALUES (
    'b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7',
    'owl',
    '{
        "mcp_config_path": "./data/mcp/config",
        "society_config": {
            "default_agents": ["planner", "researcher", "executor"],
            "workflow_enabled": true
        },
        "toolkit_config": {
            "load_system_tools": true,
            "tool_permission_level": "standard"
        },
        "llm_model": "gpt-4o"
    }',
    true,
    200,
    '["agent", "tools", "workflow", "society"]',
    '0.5.2',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- LightRAG框架配置
INSERT INTO framework_configs (
    id,
    framework_name,
    settings,
    is_enabled,
    priority,
    capabilities,
    version,
    created_at,
    updated_at
)
VALUES (
    'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8',
    'lightrag',
    '{
        "base_dir": "./data/lightrag",
        "embedding_dim": 1536,
        "max_token_size": 8192,
        "graph_db_type": "file",
        "server_port": 9621,
        "api_url": "http://localhost:9621",
        "llm_binding": "openai",
        "llm_model": "gpt-4o-mini"
    }',
    true,
    300,
    '["document_processing", "retrieval", "graph", "query_engine"]',
    '0.3.1',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Agno框架配置
INSERT INTO framework_configs (
    id,
    framework_name,
    settings,
    is_enabled,
    priority,
    capabilities,
    version,
    created_at,
    updated_at
)
VALUES (
    'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9',
    'agno',
    '{
        "llm_model": "gpt-4o-mini",
        "enable_memory": true,
        "max_memory_items": 100,
        "default_tools": ["knowledge_search", "internet_search"]
    }',
    true,
    400,
    '["agent", "tools"]',
    '0.2.5',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Haystack框架配置 (默认禁用)
INSERT INTO framework_configs (
    id,
    framework_name,
    settings,
    is_enabled,
    priority,
    capabilities,
    version,
    created_at,
    updated_at
)
VALUES (
    'e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0',
    'haystack',
    '{
        "document_store_type": "elasticsearch",
        "retriever_type": "embedding",
        "top_k": 5,
        "reader_model": "deepset/roberta-base-squad2"
    }',
    false,
    500,
    '["retrieval", "question_answering", "document_processing"]',
    '2.0.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- FastMCP框架配置
INSERT INTO framework_configs (
    id,
    framework_name,
    settings,
    is_enabled,
    priority,
    capabilities,
    version,
    created_at,
    updated_at
)
VALUES (
    'f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1',
    'fastmcp',
    '{
        "enable_caching": true,
        "cache_ttl": 3600,
        "resource_polling_interval": 60,
        "max_concurrent_requests": 50
    }',
    true,
    150,
    '["mcp_tools", "resource_management"]',
    '0.4.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- LlamaIndex集成配置
INSERT INTO llamaindex_integrations (
    id,
    index_name,
    index_type,
    index_settings,
    storage_context,
    embedding_model,
    chunk_size,
    chunk_overlap,
    metadata,
    created_at,
    updated_at
)
VALUES (
    'a1a2a3a4-b5b6-c7c8-d9d0-e1e2e3e4e5e6',
    'default_index',
    'vector_store',
    '{
        "similarity_top_k": 5,
        "include_metadata": true,
        "service_context_config": {
            "llm_model": "gpt-4o-mini",
            "embed_model": "text-embedding-3-small"
        }
    }',
    '{
        "vector_store": {
            "type": "milvus",
            "collection_name": "document_vectors"
        },
        "docstore": {
            "type": "simple"
        }
    }',
    'text-embedding-3-small',
    1000,
    200,
    '{
        "description": "默认索引",
        "creator": "system"
    }',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- OWL框架集成配置
INSERT INTO owl_integrations (
    id,
    society_name,
    agent_configs,
    toolkit_configs,
    workflow_configs,
    mcp_config_path,
    created_at,
    updated_at
)
VALUES (
    'b1b2b3b4-c5c6-d7d8-e9e0-f1f2f3f4f5f6',
    '默认智能体社会',
    '[
        {
            "name": "planner",
            "description": "计划制定智能体",
            "role": "planner",
            "model": "gpt-4o",
            "system_prompt": "你是一个专业的计划制定者，负责分解复杂任务并制定执行计划。"
        },
        {
            "name": "researcher",
            "description": "信息收集智能体",
            "role": "researcher",
            "model": "gpt-4o",
            "system_prompt": "你是一个专业的研究员，负责收集和分析信息。"
        },
        {
            "name": "executor",
            "description": "执行智能体",
            "role": "executor",
            "model": "gpt-4o",
            "system_prompt": "你是一个执行者，负责按计划完成具体任务。"
        }
    ]',
    '{
        "default_tools": ["knowledge_search", "web_search", "calculator", "file_reader"],
        "tool_permission_level": "standard"
    }',
    '{
        "enable_workflows": true,
        "workflow_definitions_path": "./data/owl/workflows",
        "default_workflow": "research_and_report"
    }',
    './data/mcp/config',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- LightRAG集成配置
INSERT INTO lightrag_integrations (
    id,
    index_name,
    document_processor_config,
    graph_config,
    query_engine_config,
    workdir_path,
    created_at,
    updated_at
)
VALUES (
    'c1c2c3c4-d5d6-e7e8-f9f0-g1g2g3g4g5g6',
    'default_lightrag',
    '{
        "chunk_size": 512,
        "chunk_overlap": 50,
        "extractors": ["entity", "relationship", "keyword"],
        "preprocessors": ["html_cleaner", "table_extractor"]
    }',
    '{
        "graph_type": "knowledge_graph",
        "entity_extraction_model": "gpt-4o-mini",
        "relationship_threshold": 0.6
    }',
    '{
        "retrieval_mode": "hybrid",
        "semantic_weight": 0.7,
        "keyword_weight": 0.3,
        "top_k": 5,
        "reranker_enabled": true
    }',
    './data/lightrag/workdir',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- MCP服务集成配置
INSERT INTO mcp_integrations (
    id,
    server_name,
    endpoint_url,
    auth_type,
    resource_configs,
    server_capabilities,
    status,
    created_at,
    updated_at
)
VALUES (
    'd1d2d3d4-e5e6-f7f8-g9g0-h1h2h3h4h5h6',
    'default_mcp_server',
    'http://localhost:8080',
    'none',
    '{
        "resource_types": ["tool", "model", "data"],
        "polling_interval": 60
    }',
    '["tool_execution", "resource_management", "model_serving"]',
    'active',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
