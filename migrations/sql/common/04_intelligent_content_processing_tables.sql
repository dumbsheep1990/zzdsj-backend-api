-- =====================================================
-- 智能内容处理功能数据库表结构
-- 创建日期: 2024-12-05
-- 说明: 支持MarkItDown、智能爬虫、内容质量分析等功能
-- =====================================================

-- 1. 网页爬取结果表
CREATE TABLE IF NOT EXISTS web_crawl_results (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    original_url TEXT,
    title VARCHAR(500),
    content TEXT,
    raw_html TEXT,
    content_type VARCHAR(100) DEFAULT 'text/html',
    metadata JSONB DEFAULT '{}',
    
    -- 爬取配置和结果
    crawler_type VARCHAR(50) NOT NULL, -- 'crawl4ai', 'browser_use', 'simple_crawler'
    crawler_config JSONB DEFAULT '{}',
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    
    -- 质量评估
    quality_score DECIMAL(3,2) DEFAULT 0.0,
    quality_metrics JSONB DEFAULT '{}',
    content_length INTEGER DEFAULT 0,
    
    -- 处理状态
    processing_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,
    
    -- 缓存控制
    cache_key VARCHAR(255),
    expires_at TIMESTAMP,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 内容处理任务表
CREATE TABLE IF NOT EXISTS content_processing_tasks (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type VARCHAR(50) NOT NULL, -- 'markitdown', 'quality_analysis', 'content_extraction', 'structure_analysis'
    
    -- 输入数据
    source_type VARCHAR(50) NOT NULL, -- 'url', 'file', 'text', 'crawl_result'
    source_reference VARCHAR(500), -- URL、文件路径或crawl_result的ID
    input_data JSONB DEFAULT '{}',
    input_format VARCHAR(50), -- 'html', 'pdf', 'docx', 'text'
    
    -- 处理配置
    processor_config JSONB DEFAULT '{}',
    processing_options JSONB DEFAULT '{}',
    
    -- 输出数据
    output_data JSONB DEFAULT '{}',
    output_format VARCHAR(50), -- 'markdown', 'json', 'text'
    
    -- 执行状态
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'cancelled'
    progress INTEGER DEFAULT 0, -- 0-100
    
    -- 错误处理
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- 性能指标
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_ms INTEGER,
    
    -- 关联
    user_id VARCHAR(36) REFERENCES users(id),
    parent_task_id VARCHAR(36) REFERENCES content_processing_tasks(id),
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 内容质量分析结果表
CREATE TABLE IF NOT EXISTS content_quality_analysis (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 关联内容
    content_source_type VARCHAR(50) NOT NULL, -- 'crawl_result', 'document', 'task_output'
    content_source_id VARCHAR(36) NOT NULL,
    content_hash VARCHAR(64), -- 内容的SHA256哈希，用于去重
    
    -- 分析类型和配置
    analysis_type VARCHAR(50) NOT NULL, -- 'comprehensive', 'basic', 'policy_specific'
    analyzer_version VARCHAR(20) DEFAULT '1.0',
    analysis_config JSONB DEFAULT '{}',
    
    -- 质量指标
    overall_score DECIMAL(3,2) NOT NULL,
    text_density_score DECIMAL(3,2),
    structure_quality_score DECIMAL(3,2),
    content_relevance_score DECIMAL(3,2),
    language_quality_score DECIMAL(3,2),
    
    -- 详细指标
    metrics JSONB DEFAULT '{}', -- 详细的各项指标数据
    statistics JSONB DEFAULT '{}', -- 统计信息（字数、段落数等）
    
    -- 分析结果
    content_type_detected VARCHAR(100),
    language_detected VARCHAR(10),
    readability_score DECIMAL(3,2),
    
    -- 改进建议
    suggestions JSONB DEFAULT '[]',
    issues_found JSONB DEFAULT '[]',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 爬虫调度日志表  
CREATE TABLE IF NOT EXISTS crawler_scheduling_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 调度请求
    url TEXT NOT NULL,
    request_config JSONB DEFAULT '{}',
    scheduling_strategy VARCHAR(50) DEFAULT 'auto', -- 'auto', 'crawl4ai_priority', 'browser_use_priority', 'simple_only'
    
    -- 决策过程
    page_analysis JSONB DEFAULT '{}', -- 页面复杂度分析结果
    strategy_chosen VARCHAR(50) NOT NULL, -- 最终选择的策略
    decision_factors JSONB DEFAULT '{}', -- 决策因素详情
    decision_confidence DECIMAL(3,2), -- 决策置信度
    
    -- 执行结果
    execution_status VARCHAR(50) NOT NULL, -- 'success', 'partial_success', 'failed'
    crawlers_attempted JSONB DEFAULT '[]', -- 尝试的爬虫列表
    final_crawler VARCHAR(50), -- 最终成功的爬虫
    fallback_used BOOLEAN DEFAULT FALSE,
    
    -- 性能指标
    total_duration_ms INTEGER,
    analysis_duration_ms INTEGER,
    crawling_duration_ms INTEGER,
    
    -- 质量结果
    content_quality_score DECIMAL(3,2),
    success_rate DECIMAL(3,2),
    
    -- 关联
    crawl_result_id VARCHAR(36) REFERENCES web_crawl_results(id),
    user_id VARCHAR(36) REFERENCES users(id),
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 政策门户配置表
CREATE TABLE IF NOT EXISTS policy_portal_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 基本信息
    region_name VARCHAR(100) NOT NULL, -- '六盘水市', '贵州省', '国家'
    region_level VARCHAR(20) NOT NULL, -- 'city', 'province', 'national'
    portal_name VARCHAR(200) NOT NULL,
    portal_description TEXT,
    
    -- 搜索配置
    base_url VARCHAR(500) NOT NULL,
    search_url VARCHAR(500) NOT NULL,
    search_method VARCHAR(10) DEFAULT 'GET', -- 'GET', 'POST'
    
    -- 表单配置
    form_config JSONB DEFAULT '{}', -- 表单字段配置
    search_params JSONB DEFAULT '{}', -- 默认搜索参数
    headers JSONB DEFAULT '{}', -- 请求头配置
    
    -- 解析配置
    result_selectors JSONB DEFAULT '{}', -- CSS选择器配置
    pagination_config JSONB DEFAULT '{}', -- 分页配置
    content_extraction_rules JSONB DEFAULT '{}', -- 内容提取规则
    
    -- 状态控制
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE, -- 是否已验证可用
    priority INTEGER DEFAULT 10, -- 优先级，数字越小优先级越高
    
    -- 性能配置
    timeout_seconds INTEGER DEFAULT 30,
    max_retries INTEGER DEFAULT 2,
    rate_limit_delay_ms INTEGER DEFAULT 1000,
    
    -- 验证信息
    last_verified_at TIMESTAMP,
    verification_status VARCHAR(50), -- 'pending', 'success', 'failed'
    verification_error TEXT,
    
    -- 统计信息
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- 创建者
    created_by VARCHAR(36) REFERENCES users(id),
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 创建索引
-- =====================================================

-- web_crawl_results表索引
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_url ON web_crawl_results(url);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_crawler_type ON web_crawl_results(crawler_type);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_status ON web_crawl_results(processing_status);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_created_at ON web_crawl_results(created_at);
CREATE INDEX IF NOT EXISTS idx_web_crawl_results_cache_key ON web_crawl_results(cache_key);

-- content_processing_tasks表索引
CREATE INDEX IF NOT EXISTS idx_content_processing_tasks_type ON content_processing_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_content_processing_tasks_status ON content_processing_tasks(status);
CREATE INDEX IF NOT EXISTS idx_content_processing_tasks_user_id ON content_processing_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_content_processing_tasks_created_at ON content_processing_tasks(created_at);

-- content_quality_analysis表索引
CREATE INDEX IF NOT EXISTS idx_content_quality_analysis_source ON content_quality_analysis(content_source_type, content_source_id);
CREATE INDEX IF NOT EXISTS idx_content_quality_analysis_hash ON content_quality_analysis(content_hash);
CREATE INDEX IF NOT EXISTS idx_content_quality_analysis_type ON content_quality_analysis(analysis_type);
CREATE INDEX IF NOT EXISTS idx_content_quality_analysis_score ON content_quality_analysis(overall_score);

-- crawler_scheduling_logs表索引
CREATE INDEX IF NOT EXISTS idx_crawler_scheduling_logs_url ON crawler_scheduling_logs(url);
CREATE INDEX IF NOT EXISTS idx_crawler_scheduling_logs_strategy ON crawler_scheduling_logs(strategy_chosen);
CREATE INDEX IF NOT EXISTS idx_crawler_scheduling_logs_status ON crawler_scheduling_logs(execution_status);
CREATE INDEX IF NOT EXISTS idx_crawler_scheduling_logs_created_at ON crawler_scheduling_logs(created_at);

-- policy_portal_configs表索引
CREATE INDEX IF NOT EXISTS idx_policy_portal_configs_region ON policy_portal_configs(region_name, region_level);
CREATE INDEX IF NOT EXISTS idx_policy_portal_configs_active ON policy_portal_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_policy_portal_configs_priority ON policy_portal_configs(priority);
CREATE INDEX IF NOT EXISTS idx_policy_portal_configs_verified ON policy_portal_configs(is_verified);

-- =====================================================
-- 插入默认政策门户配置
-- =====================================================

-- 插入六盘水市政府门户配置
INSERT INTO policy_portal_configs (
    id, region_name, region_level, portal_name, portal_description,
    base_url, search_url, search_method,
    form_config, search_params,
    result_selectors, pagination_config,
    is_active, priority, created_at
) VALUES (
    uuid_generate_v4(),
    '六盘水市', 'city', '六盘水市人民政府',
    '六盘水市人民政府官方门户网站政策文件搜索',
    'https://www.gzlps.gov.cn',
    'https://www.gzlps.gov.cn/so/search.shtml',
    'GET',
    '{"search_field": "q", "category_field": "type", "date_field": "daterange"}',
    '{"type": "policy", "site": "www.gzlps.gov.cn"}',
    '{"title": ".result-title a", "url": ".result-title a", "snippet": ".result-snippet", "date": ".result-date"}',
    '{"next_page": ".pagination .next", "page_param": "page"}',
    true, 1, CURRENT_TIMESTAMP
);

-- 插入贵州省政府门户配置
INSERT INTO policy_portal_configs (
    id, region_name, region_level, portal_name, portal_description,
    base_url, search_url, search_method,
    form_config, search_params,
    result_selectors, pagination_config,
    is_active, priority, created_at
) VALUES (
    uuid_generate_v4(),
    '贵州省', 'province', '贵州省人民政府',
    '贵州省人民政府官方门户网站政策文件搜索',
    'https://www.guizhou.gov.cn',
    'https://www.guizhou.gov.cn/so/search.shtml',
    'GET',
    '{"search_field": "q", "category_field": "column", "date_field": "daterange"}',
    '{"column": "policy", "site": "www.guizhou.gov.cn"}',
    '{"title": ".search-result-title a", "url": ".search-result-title a", "snippet": ".search-result-content", "date": ".search-result-time"}',
    '{"next_page": ".page-next", "page_param": "p"}',
    true, 2, CURRENT_TIMESTAMP
);

-- 插入国家级门户配置
INSERT INTO policy_portal_configs (
    id, region_name, region_level, portal_name, portal_description,
    base_url, search_url, search_method,
    form_config, search_params,
    result_selectors, pagination_config,
    is_active, priority, created_at
) VALUES (
    uuid_generate_v4(),
    '中华人民共和国', 'national', '中国政府网',
    '中华人民共和国中央人民政府门户网站政策搜索',
    'https://www.gov.cn',
    'https://www.gov.cn/zhengce/',
    'GET',
    '{"search_field": "q", "category_field": "type"}',
    '{"type": "zhengce"}',
    '{"title": ".item-title a", "url": ".item-title a", "snippet": ".item-content", "date": ".item-time"}',
    '{"next_page": ".next", "page_param": "page"}',
    true, 3, CURRENT_TIMESTAMP
);

-- =====================================================
-- 创建触发器
-- =====================================================

-- 更新时间戳触发器
CREATE TRIGGER IF NOT EXISTS update_web_crawl_results_updated_at 
    BEFORE UPDATE ON web_crawl_results 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_content_processing_tasks_updated_at 
    BEFORE UPDATE ON content_processing_tasks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_policy_portal_configs_updated_at 
    BEFORE UPDATE ON policy_portal_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 验证表创建
-- =====================================================

-- 检查表是否成功创建
SELECT 
    tablename,
    schemaname
FROM pg_tables 
WHERE tablename IN (
    'web_crawl_results',
    'content_processing_tasks', 
    'content_quality_analysis',
    'crawler_scheduling_logs',
    'policy_portal_configs'
)
ORDER BY tablename;
