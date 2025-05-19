-- 模型提供商初始化脚本 (通用)
-- 创建常用模型提供商配置

-- OpenAI
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6', 
    'OpenAI', 
    'openai', 
    'https://api.openai.com/v1', 
    'api_key', 
    true, 
    true, 
    '[
        {"id": "gpt-4", "name": "GPT-4", "type": "chat", "context_window": 8192, "is_default": false},
        {"id": "gpt-4o", "name": "GPT-4o", "type": "chat", "context_window": 128000, "is_default": true},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "type": "chat", "context_window": 128000, "is_default": false},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "type": "chat", "context_window": 16385, "is_default": false},
        {"id": "text-embedding-3-large", "name": "Embedding (Large)", "type": "embedding", "context_window": 8191, "is_default": true},
        {"id": "text-embedding-3-small", "name": "Embedding (Small)", "type": "embedding", "context_window": 8191, "is_default": false}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- 智谱AI
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7', 
    '智谱AI', 
    'zhipu', 
    'https://open.bigmodel.cn/api/paas/v4', 
    'api_key', 
    true, 
    false, 
    '[
        {"id": "glm-4", "name": "GLM-4", "type": "chat", "context_window": 128000, "is_default": true},
        {"id": "glm-3-turbo", "name": "GLM-3-Turbo", "type": "chat", "context_window": 128000, "is_default": false},
        {"id": "embedding-2", "name": "Embedding-2", "type": "embedding", "context_window": 8192, "is_default": true}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- 月之暗面
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8', 
    '月之暗面', 
    'moonshot', 
    'https://api.moonshot.cn/v1', 
    'api_key', 
    true, 
    false, 
    '[
        {"id": "moonshot-v1-128k", "name": "Moonshot 128K", "type": "chat", "context_window": 128000, "is_default": true},
        {"id": "moonshot-v1-32k", "name": "Moonshot 32K", "type": "chat", "context_window": 32000, "is_default": false}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- 百度文心一言
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9', 
    '文心一言', 
    'baidu', 
    'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop', 
    'api_secret', 
    true, 
    false, 
    '[
        {"id": "ernie-4.0", "name": "文心一言4.0", "type": "chat", "context_window": 24000, "is_default": true},
        {"id": "ernie-3.5", "name": "文心一言3.5", "type": "chat", "context_window": 9600, "is_default": false},
        {"id": "ernie-embedding-v1", "name": "文心Embedding", "type": "embedding", "context_window": 4096, "is_default": true}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- 通义千问
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0', 
    '通义千问', 
    'qwen', 
    'https://dashscope.aliyuncs.com/api/v1', 
    'api_key', 
    true, 
    false, 
    '[
        {"id": "qwen-turbo", "name": "千问Turbo", "type": "chat", "context_window": 6000, "is_default": false},
        {"id": "qwen-plus", "name": "千问Plus", "type": "chat", "context_window": 32000, "is_default": true},
        {"id": "qwen-max", "name": "千问Max", "type": "chat", "context_window": 8192, "is_default": false},
        {"id": "text-embedding-v1", "name": "千问Embedding", "type": "embedding", "context_window": 8192, "is_default": true}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- Anthropic
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1', 
    'Anthropic', 
    'anthropic', 
    'https://api.anthropic.com', 
    'api_key', 
    true, 
    false, 
    '[
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "type": "chat", "context_window": 200000, "is_default": true},
        {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "type": "chat", "context_window": 200000, "is_default": false},
        {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "type": "chat", "context_window": 200000, "is_default": false}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- 本地Ollama
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'g7h8i9j0-k1l2-m3n4-o5p6-q7r8s9t0u1v2', 
    'Ollama', 
    'ollama', 
    'http://localhost:11434', 
    'none', 
    true, 
    false, 
    '[
        {"id": "llama3", "name": "Llama3", "type": "chat", "context_window": 8192, "is_default": true},
        {"id": "qwen:7b", "name": "Qwen 7B", "type": "chat", "context_window": 8192, "is_default": false},
        {"id": "llava", "name": "LLaVA", "type": "chat", "context_window": 8192, "is_default": false, "multimodal": true}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);

-- VLLM
INSERT INTO model_providers (id, name, provider_type, base_url, auth_type, is_enabled, is_default, models, created_at, updated_at)
VALUES (
    'h8i9j0k1-l2m3-n4o5-p6q7-r8s9t0u1v2w3', 
    'VLLM', 
    'vllm', 
    'http://localhost:8000', 
    'none', 
    true, 
    false, 
    '[
        {"id": "yi:34b", "name": "Yi-34B", "type": "chat", "context_window": 16000, "is_default": true},
        {"id": "gemma:7b", "name": "Gemma 7B", "type": "chat", "context_window": 8192, "is_default": false}
    ]', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP
);
