-- 智能爬取工具配置项
-- 在系统配置表中添加爬取工具相关配置

-- 插入爬取功能开关
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('k0k1k2k3-l4l5-m6m7-n8n9-o0o1o2o3o4o5', 'crawling.enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '是否启用智能爬取功能', true, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 插入爬取模型配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('l1l2l3l4-m5m6-n7n8-o9o0-p1p2p3p4p5p6', 'crawling.model.provider', 'openai', 'string', 'openai', 'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', '爬取工具使用的模型提供商', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('m2m3m4m5-n6n7-o8o9-p0p1-q2q3q4q5q6q7', 'crawling.model.name', 'gpt-4o', 'string', 'gpt-4o', 'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', '爬取工具使用的具体模型名称', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('n3n4n5n6-o7o8-p9p0-q1q2-r3r4r5r6r7r8', 'crawling.model.temperature', '0.1', 'number', '0.1', 'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', '爬取工具模型的温度参数', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 插入爬取器配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('o4o5o6o7-p8p9-q0q1-r2r3-s4s5s6s7s8s9', 'crawling.default_crawler', 'auto', 'string', 'auto', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '默认爬取工具选择策略', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('p5p6p7p8-q9q0-r1r2-s3s4-t5t6t7t8t9t0', 'crawling.max_concurrent', '3', 'number', '3', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '最大并发爬取任务数', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('q6q7q8q9-r0r1-s2s3-t4t5-u6u7u8u9u0u1', 'crawling.timeout', '60', 'number', '60', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '单个爬取任务超时时间（秒）', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 插入政策检索增强配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('r7r8r9r0-s1s2-t3t4-u5u6-v7v8v9v0v1v2', 'policy_search.enable_intelligent_crawling', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '政策检索是否启用智能爬取', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('s8s9s0s1-t2t3-u4u5-v6v7-w8w9w0w1w2w3', 'policy_search.crawl_detail_pages', 'false', 'boolean', 'false', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '政策检索是否爬取详情页面', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('t9t0t1t2-u3u4-v5v6-w7w8-x9x0x1x2x3x4', 'policy_search.max_crawl_pages', '5', 'number', '5', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '政策检索最大爬取页面数', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 插入Crawl4AI配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('u0u1u2u3-v4v5-w6w7-x8x9-y0y1y2y3y4y5', 'crawl4ai.enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '是否启用Crawl4AI工具', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('v1v2v3v4-w5w6-x7x8-y9y0-z1z2z3z4z5z6', 'crawl4ai.max_pages', '10', 'number', '10', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', 'Crawl4AI最大爬取页面数', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('w2w3w4w5-x6x7-y8y9-z0z1-a2a3a4a5a6a7', 'crawl4ai.parallel_mode', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', 'Crawl4AI是否启用并行模式', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 插入Browser Use配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('x3x4x5x6-y7y8-z9z0-a1a2-b3b4b5b6b7b8', 'browser_use.enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '是否启用Browser Use工具', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('y4y5y6y7-z8z9-a0a1-b2b3-c4c5c6c7c8c9', 'browser_use.headless', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', 'Browser Use是否使用无头模式', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('z5z6z7z8-a9a0-b1b2-c3c4-d5d6d7d8d9d0', 'browser_use.max_tabs', '3', 'number', '3', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', 'Browser Use最大标签页数', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 插入质量控制配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('a6a7a8a9-b0b1-c2c3-d4d5-e6e7e8e9e0e1', 'crawling.quality_threshold', '0.6', 'number', '0.6', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '爬取内容质量阈值', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('b7b8b9b0-c1c2-d3d4-e5e6-f7f8f9f0f1f2', 'crawling.retry_enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '是否启用智能重试机制', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('c8c9c0c1-d2d3-e4e5-f6f7-g8g9g0g1g2g3', 'crawling.max_retries', '2', 'number', '2', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '最大重试次数', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 插入缓存配置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('d9d0d1d2-e3e4-f5f6-g7g8-h9h0h1h2h3h4', 'crawling.cache_enabled', 'true', 'boolean', 'true', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '是否启用爬取结果缓存', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES ('e0e1e2e3-f4f5-g6g7-h8h9-i0i1i2i3i4i5', 'crawling.cache_ttl', '3600', 'number', '3600', 'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', '爬取结果缓存时间（秒）', false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- 验证配置项插入
SELECT 
    key,
    value,
    value_type,
    description,
    category_id
FROM system_configs 
WHERE key LIKE 'crawling.%' OR key LIKE 'policy_search.%' OR key LIKE 'crawl4ai.%' OR key LIKE 'browser_use.%'
ORDER BY key; 