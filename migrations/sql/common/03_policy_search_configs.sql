-- 政策检索配置数据库迁移脚本
-- 添加政策检索相关的系统配置

-- 检查并创建配置类别（如果不存在）
INSERT INTO config_categories (id, name, description, is_system, order_index, created_at, updated_at)
VALUES ('policy-search-category-id', '政策检索配置', '政府门户政策检索相关配置', true, 80, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (name) DO NOTHING;

-- 政策检索功能开关
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-search-enabled-id',
    'features.policy_search.enabled',
    'true',
    'boolean',
    'true',
    'policy-search-category-id',
    '是否启用政策检索功能',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 默认检索策略
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-search-strategy-id',
    'policy_search.default_strategy',
    'auto',
    'string',
    'auto',
    'policy-search-category-id',
    '默认政策检索策略（auto|local_only|provincial_only|search_only）',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 默认最大结果数
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-search-max-results-id',
    'policy_search.max_results',
    '10',
    'number',
    '10',
    'policy-search-category-id',
    '政策检索默认最大结果数',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 连接超时设置
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-search-timeout-id',
    'policy_search.connection_timeout',
    '30',
    'number',
    '30',
    'policy-search-category-id',
    '门户连接超时时间（秒）',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 结果质量阈值
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-search-quality-threshold-id',
    'policy_search.quality_threshold',
    '0.6',
    'number',
    '0.6',
    'policy-search-category-id',
    '检索结果质量阈值（0-1）',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 是否启用搜索引擎兜底
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-search-fallback-id',
    'policy_search.enable_search_fallback',
    'true',
    'boolean',
    'true',
    'policy-search-category-id',
    '是否启用搜索引擎兜底检索',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 六盘水市门户配置（示例）
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-portal-liupanshui-id',
    'policy_search.portal.六盘水',
    '{"name": "六盘水市人民政府", "level": "municipal", "parent_region": "贵州省", "base_url": "https://www.gzlps.gov.cn", "search_endpoint": "/so/search.shtml", "search_params": {"tenantId": "30", "tenantIds": "", "configTenantId": "", "searchWord": "{query}"}, "result_selector": ".search-result-item", "encoding": "utf-8", "max_results": 10, "region_code": "520200"}',
    'json',
    '{}',
    'policy-search-category-id',
    '六盘水市政府门户搜索配置',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 贵州省门户配置（示例）
INSERT INTO system_configs (id, key, value, value_type, default_value, category_id, description, is_system, is_sensitive, created_at, updated_at)
VALUES (
    'policy-portal-guizhou-id',
    'policy_search.portal.贵州省',
    '{"name": "贵州省人民政府", "level": "provincial", "base_url": "https://www.guizhou.gov.cn", "search_endpoint": "/so/search.shtml", "search_params": {"tenantId": "186", "tenantIds": "", "configTenantId": "", "searchWord": "{query}"}, "result_selector": ".search-result-item", "encoding": "utf-8", "max_results": 15, "region_code": "520000"}',
    'json',
    '{}',
    'policy-search-category-id',
    '贵州省政府门户搜索配置',
    false,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (key) DO NOTHING;

-- 创建门户配置索引（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_system_configs_policy_search_portal'
    ) THEN
        CREATE INDEX idx_system_configs_policy_search_portal 
        ON system_configs(key) 
        WHERE key LIKE 'policy_search.portal.%';
    END IF;
END $$;

-- 创建配置变更日志（如果表存在）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'config_history') THEN
        INSERT INTO config_history (id, config_id, old_value, new_value, changed_by, change_reason, created_at)
        SELECT 
            gen_random_uuid(),
            sc.id,
            NULL,
            sc.value,
            'system_migration',
            '政策检索配置初始化',
            CURRENT_TIMESTAMP
        FROM system_configs sc
        WHERE sc.key LIKE 'policy_search.%'
        AND NOT EXISTS (
            SELECT 1 FROM config_history ch WHERE ch.config_id = sc.id
        );
    END IF;
END $$; 