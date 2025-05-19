-- 智能体模板初始化脚本 (通用)
-- 为系统创建预定义的智能体模板

-- 知识库问答智能体模板
INSERT INTO agent_templates (
    id,
    name,
    description,
    system_prompt_template,
    default_model,
    required_tools,
    optional_tools,
    parameters_schema,
    category,
    is_system,
    created_at,
    updated_at
)
VALUES (
    'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6',
    '知识库问答助手',
    '基于知识库回答用户问题的智能体，可以检索和引用文档内容',
    '你是一个专业的智能知识库问答助手，名为 {{name}}。你的任务是基于提供的知识库准确回答用户问题。\n\n当用户提问时，请首先使用knowledge_search工具在知识库中检索相关信息，然后根据检索结果进行回答。\n\n如果知识库中没有相关信息，请明确告知用户，并建议用户尝试其他相关问题。\n\n请遵循以下原则：\n1. 回答应基于检索到的知识库内容，不要编造信息\n2. 回答应简洁明了，重点突出\n3. 适当引用知识库来源，增强可信度\n4. 专业、客观、友好地回应用户',
    'gpt-4o-mini',
    '["knowledge_search"]',
    '["web_search", "file_reader", "calculator"]',
    '{
        "properties": {
            "name": {
                "type": "string",
                "description": "智能体名称"
            },
            "knowledge_base_ids": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "关联的知识库ID列表"
            },
            "search_top_k": {
                "type": "integer",
                "description": "检索结果数量",
                "default": 5
            },
            "search_threshold": {
                "type": "number",
                "description": "检索相似度阈值",
                "default": 0.7
            }
        },
        "required": ["name", "knowledge_base_ids"]
    }',
    '知识库',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 网络搜索智能体模板
INSERT INTO agent_templates (
    id,
    name,
    description,
    system_prompt_template,
    default_model,
    required_tools,
    optional_tools,
    parameters_schema,
    category,
    is_system,
    created_at,
    updated_at
)
VALUES (
    'b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7',
    '网络搜索助手',
    '可以搜索互联网获取最新信息的智能体',
    '你是一个专业的网络搜索智能助手，名为 {{name}}。你的任务是帮助用户搜索互联网获取最新、最相关的信息。\n\n当用户提问时，请使用web_search工具在互联网上搜索相关信息，然后根据搜索结果为用户提供准确、全面的回答。\n\n请遵循以下原则：\n1. 优先提供最新、最权威的信息\n2. 综合多个来源，提供全面的视角\n3. 引用信息来源，确保可追溯\n4. 客观呈现信息，避免个人偏见\n5. 对于有争议的话题，呈现不同的观点',
    'gpt-4o',
    '["web_search"]',
    '["knowledge_search", "calculator", "summarizer"]',
    '{
        "properties": {
            "name": {
                "type": "string",
                "description": "智能体名称"
            },
            "search_engine": {
                "type": "string",
                "description": "搜索引擎",
                "enum": ["google", "bing", "baidu", "searx"],
                "default": "searx"
            },
            "result_count": {
                "type": "integer",
                "description": "搜索结果数量",
                "default": 5
            }
        },
        "required": ["name"]
    }',
    '搜索',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 数据分析智能体模板
INSERT INTO agent_templates (
    id,
    name,
    description,
    system_prompt_template,
    default_model,
    required_tools,
    optional_tools,
    parameters_schema,
    category,
    is_system,
    created_at,
    updated_at
)
VALUES (
    'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8',
    '数据分析助手',
    '可以读取和分析数据文件的智能体',
    '你是一个专业的数据分析智能助手，名为 {{name}}。你的任务是帮助用户读取、分析和可视化数据。\n\n你可以使用以下工具：\n- file_reader工具读取各种格式的数据文件\n- calculator工具进行计算和分析\n- chart_generator工具创建可视化图表\n\n请遵循以下原则：\n1. 首先了解用户的分析需求和目标\n2. 根据需求选择合适的分析方法\n3. 清晰呈现分析结果，使用图表增强可理解性\n4. 提供洞察和建议，但避免过度解读数据\n5. 客观严谨，避免统计误用',
    'gpt-4o',
    '["file_reader", "calculator"]',
    '["chart_generator", "excel_processor", "data_cleaner"]',
    '{
        "properties": {
            "name": {
                "type": "string",
                "description": "智能体名称"
            },
            "support_formats": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["csv", "excel", "json", "txt"]
                },
                "description": "支持的文件格式",
                "default": ["csv", "excel", "json"]
            },
            "max_file_size_mb": {
                "type": "integer",
                "description": "最大文件大小(MB)",
                "default": 10
            }
        },
        "required": ["name"]
    }',
    '数据',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 多人协作智能体模板
INSERT INTO agent_templates (
    id,
    name,
    description,
    system_prompt_template,
    default_model,
    required_tools,
    optional_tools,
    parameters_schema,
    category,
    is_system,
    created_at,
    updated_at
)
VALUES (
    'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9',
    '多智能体协作系统',
    '基于OWL框架的多智能体协作系统模板',
    '你是一个多智能体协作系统的控制中心，名为 {{name}}。你可以协调多个专业智能体共同完成复杂任务。\n\n系统中包含以下智能体角色：\n- 规划者(Planner): 负责分析任务并制定执行计划\n- 研究员(Researcher): 负责收集和分析相关信息\n- 执行者(Executor): 负责执行具体任务\n- 评审者(Reviewer): 负责检查和评估结果\n\n你的工作流程如下：\n1. 接收用户任务请求\n2. 调用规划者分析任务并创建计划\n3. 协调研究员获取必要信息\n4. 指导执行者完成具体任务\n5. 请评审者审核结果\n6. 向用户呈现最终结果\n\n请确保智能体之间的有效协作，并在必要时干预协调。',
    'gpt-4o',
    '["owl_society_manager"]',
    '["knowledge_search", "web_search", "file_reader", "calculator"]',
    '{
        "properties": {
            "name": {
                "type": "string",
                "description": "协作系统名称"
            },
            "agent_roles": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "启用的智能体角色",
                "default": ["planner", "researcher", "executor", "reviewer"]
            },
            "workflow_enabled": {
                "type": "boolean",
                "description": "是否启用工作流",
                "default": true
            },
            "default_workflow": {
                "type": "string",
                "description": "默认工作流名称",
                "default": "research_and_report"
            }
        },
        "required": ["name"]
    }',
    'OWL',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- LightRAG智能体模板
INSERT INTO agent_templates (
    id,
    name,
    description,
    system_prompt_template,
    default_model,
    required_tools,
    optional_tools,
    parameters_schema,
    category,
    is_system,
    created_at,
    updated_at
)
VALUES (
    'e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0',
    'LightRAG检索增强助手',
    '基于LightRAG框架的知识图谱增强检索智能体',
    '你是一个基于知识图谱增强的智能问答助手，名为 {{name}}。你使用LightRAG框架，能够结合向量检索和图谱关系提供更准确的回答。\n\n当用户提问时，你会：\n1. 使用lightrag_search工具在知识库中检索相关信息\n2. 同时利用知识图谱关系扩展检索范围，发现潜在的相关信息\n3. 根据检索结果回答问题，同时展示关键实体间的关系\n\n请遵循以下原则：\n1. 优先使用检索到的内容回答问题\n2. 利用图谱关系提供更全面的视角\n3. 在回答中自然融入实体关系\n4. 客观准确呈现信息',
    'gpt-4o-mini',
    '["lightrag_search"]',
    '["lightrag_graph", "knowledge_search"]',
    '{
        "properties": {
            "name": {
                "type": "string",
                "description": "智能体名称"
            },
            "lightrag_index": {
                "type": "string",
                "description": "LightRAG索引名称",
                "default": "default_lightrag"
            },
            "retrieval_mode": {
                "type": "string",
                "enum": ["hybrid", "vector", "keyword", "graph"],
                "description": "检索模式",
                "default": "hybrid"
            },
            "top_k": {
                "type": "integer",
                "description": "检索结果数量",
                "default": 5
            }
        },
        "required": ["name"]
    }',
    'LightRAG',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
