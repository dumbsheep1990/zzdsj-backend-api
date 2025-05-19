-- 系统配置初始化脚本 (通用)
-- 创建配置类别

-- 服务类别
INSERT INTO config_categories (id, name, description, order, is_system, created_at, updated_at)
VALUES ('a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6', '服务配置', '基础服务配置项', 100, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 数据库类别
INSERT INTO config_categories (id, name, description, order, is_system, created_at, updated_at)
VALUES ('b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7', '数据库配置', '数据库连接和存储配置', 200, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 模型类别
INSERT INTO config_categories (id, name, description, order, is_system, created_at, updated_at)
VALUES ('c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', '模型配置', 'AI模型及提供商配置', 300, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 框架类别
INSERT INTO config_categories (id, name, description, order, is_system, created_at, updated_at)
VALUES ('d4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', 'AI框架配置', '各种AI框架集成配置', 400, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 知识库类别
INSERT INTO config_categories (id, name, description, order, is_system, created_at, updated_at)
VALUES ('e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0', '知识库配置', '知识库处理和检索配置', 500, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 安全类别
INSERT INTO config_categories (id, name, description, order, is_system, created_at, updated_at)
VALUES ('f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1', '安全配置', '认证和授权配置', 600, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 语音类别
INSERT INTO config_categories (id, name, description, order, is_system, created_at, updated_at)
VALUES ('g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2', '语音配置', '语音转文本及文本转语音配置', 700, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 创建系统配置项

-- 服务配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('a1a2a3a4-b5b6-c7c8-d9d0-e1e2e3e4e5e6', 'service.name', '智政知识库问答系统', 'string', '智政知识库问答系统', 'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6', '服务名称', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('b2b3b4b5-c6c7-d8d9-e0e1-f2f3f4f5f6f7', 'service.port', '8000', 'number', '8000', 'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6', '服务端口', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 数据库配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('c3c4c5c6-d7d8-e9e0-f1f2-g3g4g5g6g7g8', 'database.type', 'postgresql', 'string', 'postgresql', 'b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7', '数据库类型', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('d4d5d6d7-e8e9-f0f1-g2g3-h4h5h6h7h8h9', 'vector_store.type', 'milvus', 'string', 'milvus', 'b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7', '向量存储类型', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 模型配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('e5e6e7e8-f9f0-g1g2-h3h4-i5i6i7i8i9i0', 'llm.default_model', 'gpt-4', 'string', 'gpt-4', 'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', '默认大语言模型', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('f6f7f8f9-g0g1-h2h3-i4i5-j6j7j8j9j0j1', 'embedding.model', 'text-embedding-3-large', 'string', 'text-embedding-3-large', 'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', '默认嵌入模型', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 框架配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('g7g8g9g0-h1h2-i3i4-j5j6-k7k8k9k0k1k2', 'frameworks.llamaindex.enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '启用LlamaIndex框架', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('h8h9h0h1-i2i3-j4j5-k6k7-l8l9l0l1l2l3', 'frameworks.owl.enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '启用OWL框架', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('i9i0i1i2-j3j4-k5k6-l7l8-m9m0m1m2m3m4', 'frameworks.lightrag.enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '启用LightRAG框架', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('j0j1j2j3-k4k5-l6l7-m8m9-n0n1n2n3n4n5', 'frameworks.haystack.enabled', 'false', 'boolean', 'false', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '启用Haystack框架', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('k1k2k3k4-l5l6-m7m8-n9n0-o1o2o3o4o5o6', 'frameworks.agno.enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '启用Agno框架', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 知识库配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('l2l3l4l5-m6m7-n8n9-o0o1-p2p3p4p5p6p7', 'document_processing.chunk_size', '1000', 'number', '1000', 'e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0', '文档分块大小', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('m3m4m5m6-n7n8-o9o0-p1p2-q3q4q5q6q7q8', 'document_processing.chunk_overlap', '200', 'number', '200', 'e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0', '文档分块重叠大小', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 安全配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('n4n5n6n7-o8o9-p0p1-q2q3-r4r5r6r7r8r9', 'security.jwt_access_token_expire_minutes', '30', 'number', '30', 'f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1', 'JWT访问令牌过期时间(分钟)', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('o5o6o7o8-p9p0-q1q2-r3r4-s5s6s7s8s9s0', 'security.jwt_refresh_token_expire_days', '7', 'number', '7', 'f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1', 'JWT刷新令牌过期时间(天)', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 语音配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('p6p7p8p9-q0q1-r2r3-s4s5-t6t7t8t9t0t1', 'voice.enabled', 'false', 'boolean', 'false', 'g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2', '启用语音功能', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('q7q8q9q0-r1r2-s3s4-t5t6-u7u8u9u0u1u2', 'voice.tts.model_name', 'xunfei-tts', 'string', 'xunfei-tts', 'g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2', '文本转语音模型', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
