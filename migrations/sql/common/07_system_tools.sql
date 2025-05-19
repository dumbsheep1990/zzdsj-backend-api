-- 系统工具初始化脚本 (通用)
-- 为各种框架预配置工具

-- LlamaIndex工具: 知识库搜索
INSERT INTO tools (
    id,
    name,
    description,
    function_def,
    implementation_type,
    implementation,
    is_system,
    category,
    framework,
    permission_level,
    parameter_schema,
    version,
    created_at,
    updated_at
)
VALUES (
    'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6',
    'knowledge_search',
    '在知识库中搜索相关信息',
    '{
        "name": "knowledge_search",
        "description": "在指定知识库中搜索相关信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "knowledge_base_ids": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "要搜索的知识库ID列表"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的最大结果数量"
                },
                "similarity_threshold": {
                    "type": "number",
                    "description": "相似度阈值，低于此值的结果将被过滤"
                }
            },
            "required": ["query"]
        }
    }',
    'python',
    'from app.frameworks.llamaindex.retrieval import search_knowledge_base

async def execute(query, knowledge_base_ids=None, top_k=5, similarity_threshold=0.7):
    """在知识库中搜索相关信息"""
    results = await search_knowledge_base(
        query=query,
        knowledge_base_ids=knowledge_base_ids,
        top_k=top_k,
        similarity_threshold=similarity_threshold
    )
    return results',
    true,
    '知识库',
    'llamaindex',
    'standard',
    '{
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询"
            },
            "knowledge_base_ids": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "要搜索的知识库ID列表"
            },
            "top_k": {
                "type": "integer",
                "description": "返回的最大结果数量",
                "default": 5
            },
            "similarity_threshold": {
                "type": "number",
                "description": "相似度阈值，低于此值的结果将被过滤",
                "default": 0.7
            }
        },
        "required": ["query"]
    }',
    '1.0.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- OWL工具: 网络搜索
INSERT INTO tools (
    id,
    name,
    description,
    function_def,
    implementation_type,
    implementation,
    is_system,
    category,
    framework,
    permission_level,
    parameter_schema,
    version,
    created_at,
    updated_at
)
VALUES (
    'b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7',
    'web_search',
    '在互联网上搜索信息',
    '{
        "name": "web_search",
        "description": "在互联网上搜索信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "engine": {
                    "type": "string",
                    "description": "搜索引擎",
                    "enum": ["google", "bing", "baidu", "searx"]
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回的结果数量"
                }
            },
            "required": ["query"]
        }
    }',
    'python',
    'from app.core.searxng_manager import search_web

async def execute(query, engine="searx", num_results=5):
    """在互联网上搜索信息"""
    results = await search_web(
        query=query,
        engine=engine,
        num_results=num_results
    )
    return results',
    true,
    '搜索',
    'owl',
    'standard',
    '{
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询"
            },
            "engine": {
                "type": "string",
                "description": "搜索引擎",
                "enum": ["google", "bing", "baidu", "searx"],
                "default": "searx"
            },
            "num_results": {
                "type": "integer",
                "description": "返回的结果数量",
                "default": 5
            }
        },
        "required": ["query"]
    }',
    '1.0.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- OWL工具: 智能体社会管理器
INSERT INTO tools (
    id,
    name,
    description,
    function_def,
    implementation_type,
    implementation,
    is_system,
    category,
    framework,
    permission_level,
    parameter_schema,
    version,
    created_at,
    updated_at
)
VALUES (
    'c3d4e5f6-g7h8-i9j0-k1l2-m3n4o5p6q7r8',
    'owl_society_manager',
    '管理OWL框架中的智能体社会',
    '{
        "name": "owl_society_manager",
        "description": "管理OWL框架中的智能体社会，协调多个智能体共同完成任务",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "执行的操作",
                    "enum": ["create_society", "add_agent", "remove_agent", "run_workflow", "get_status"]
                },
                "society_name": {
                    "type": "string",
                    "description": "智能体社会名称"
                },
                "agent_configs": {
                    "type": "array",
                    "description": "智能体配置列表",
                    "items": {
                        "type": "object"
                    }
                },
                "workflow_name": {
                    "type": "string",
                    "description": "工作流名称"
                },
                "task_description": {
                    "type": "string",
                    "description": "任务描述"
                }
            },
            "required": ["action"]
        }
    }',
    'python',
    'from app.core.owl_controller import SocietyController

society_controller = SocietyController()

async def execute(action, society_name=None, agent_configs=None, workflow_name=None, task_description=None):
    """管理OWL框架中的智能体社会"""
    if action == "create_society":
        return await society_controller.create_society(society_name, agent_configs)
    elif action == "add_agent":
        return await society_controller.add_agent(society_name, agent_configs[0])
    elif action == "remove_agent":
        return await society_controller.remove_agent(society_name, agent_configs[0]["name"])
    elif action == "run_workflow":
        return await society_controller.run_workflow(society_name, workflow_name, task_description)
    elif action == "get_status":
        return await society_controller.get_status(society_name)
    else:
        return {"error": "未知操作"}',
    true,
    'OWL',
    'owl',
    'admin',
    '{
        "properties": {
            "action": {
                "type": "string",
                "description": "执行的操作",
                "enum": ["create_society", "add_agent", "remove_agent", "run_workflow", "get_status"]
            },
            "society_name": {
                "type": "string",
                "description": "智能体社会名称"
            },
            "agent_configs": {
                "type": "array",
                "description": "智能体配置列表",
                "items": {
                    "type": "object"
                }
            },
            "workflow_name": {
                "type": "string",
                "description": "工作流名称"
            },
            "task_description": {
                "type": "string",
                "description": "任务描述"
            }
        },
        "required": ["action"]
    }',
    '1.0.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- LightRAG工具: 检索工具
INSERT INTO tools (
    id,
    name,
    description,
    function_def,
    implementation_type,
    implementation,
    is_system,
    category,
    framework,
    permission_level,
    parameter_schema,
    version,
    created_at,
    updated_at
)
VALUES (
    'd4e5f6g7-h8i9-j0k1-l2m3-n4o5p6q7r8s9',
    'lightrag_search',
    '使用LightRAG框架进行知识检索',
    '{
        "name": "lightrag_search",
        "description": "使用LightRAG框架在知识库中检索信息，支持向量检索和知识图谱增强",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "index_name": {
                    "type": "string",
                    "description": "LightRAG索引名称"
                },
                "retrieval_mode": {
                    "type": "string",
                    "description": "检索模式",
                    "enum": ["hybrid", "vector", "keyword", "graph"]
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的最大结果数量"
                }
            },
            "required": ["query"]
        }
    }',
    'python',
    'from app.frameworks.lightrag.client import LightRAGClient

async def execute(query, index_name="default_lightrag", retrieval_mode="hybrid", top_k=5):
    """使用LightRAG框架进行知识检索"""
    client = LightRAGClient()
    
    # 确保LightRAG客户端已初始化
    await client.initialize()
    
    # 执行检索
    results = await client.query(
        query=query,
        index_name=index_name,
        retrieval_mode=retrieval_mode,
        top_k=top_k
    )
    
    return results',
    true,
    'LightRAG',
    'lightrag',
    'standard',
    '{
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询"
            },
            "index_name": {
                "type": "string",
                "description": "LightRAG索引名称",
                "default": "default_lightrag"
            },
            "retrieval_mode": {
                "type": "string",
                "description": "检索模式",
                "enum": ["hybrid", "vector", "keyword", "graph"],
                "default": "hybrid"
            },
            "top_k": {
                "type": "integer",
                "description": "返回的最大结果数量",
                "default": 5
            }
        },
        "required": ["query"]
    }',
    '1.0.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 通用工具: 计算器
INSERT INTO tools (
    id,
    name,
    description,
    function_def,
    implementation_type,
    implementation,
    is_system,
    category,
    framework,
    permission_level,
    parameter_schema,
    version,
    created_at,
    updated_at
)
VALUES (
    'e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0',
    'calculator',
    '执行数学计算',
    '{
        "name": "calculator",
        "description": "执行数学计算，支持基本运算和高级数学函数",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式"
                }
            },
            "required": ["expression"]
        }
    }',
    'python',
    'import math
import re
import numpy as np
from sympy import sympify, symbols

async def execute(expression):
    """执行数学计算"""
    # 安全检查
    if not is_safe_expression(expression):
        return {"error": "不安全的表达式"}
    
    try:
        # 尝试使用sympy进行符号计算
        result = sympify(expression)
        return {"result": str(result)}
    except Exception as e:
        try:
            # 回退到eval
            # 创建安全的本地环境
            safe_locals = {"__builtins__": {}}
            # 添加安全的数学函数
            safe_locals.update({k: getattr(math, k) for k in dir(math) if not k.startswith("_")})
            safe_locals.update({
                "abs": abs,
                "round": round,
                "max": max,
                "min": min,
                "sum": sum,
                "np": np
            })
            
            # 执行计算
            result = eval(expression, {"__builtins__": {}}, safe_locals)
            return {"result": result}
        except Exception as e2:
            return {"error": f"计算错误: {str(e2)}"}

def is_safe_expression(expr):
    """检查表达式是否安全"""
    # 禁止使用可能导致安全问题的函数和模块
    unsafe_patterns = [
        r"__",            # 双下划线方法
        r"import",        # 导入语句
        r"exec",          # 执行代码
        r"eval",          # 评估代码
        r"open",          # 文件操作
        r"os\.",          # 操作系统模块
        r"sys\.",         # 系统模块
        r"subprocess",    # 子进程
        r"globals",       # 全局变量
        r"locals",        # 局部变量
    ]
    
    # 检查是否包含不安全模式
    for pattern in unsafe_patterns:
        if re.search(pattern, expr):
            return False
            
    return True',
    true,
    '工具',
    null,
    'standard',
    '{
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式"
            }
        },
        "required": ["expression"]
    }',
    '1.0.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 通用工具: 文件读取器
INSERT INTO tools (
    id,
    name,
    description,
    function_def,
    implementation_type,
    implementation,
    is_system,
    category,
    framework,
    permission_level,
    parameter_schema,
    version,
    created_at,
    updated_at
)
VALUES (
    'f6g7h8i9-j0k1-l2m3-n4o5-p6q7r8s9t0u1',
    'file_reader',
    '读取和解析各种格式的文件',
    '{
        "name": "file_reader",
        "description": "读取和解析各种格式的文件，包括CSV、Excel、JSON、TXT等",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "要读取的文件ID"
                },
                "format": {
                    "type": "string",
                    "description": "文件格式，如auto、csv、excel、json、txt等"
                },
                "max_rows": {
                    "type": "integer",
                    "description": "最大读取行数"
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Excel文件的工作表名称"
                }
            },
            "required": ["file_id"]
        }
    }',
    'python',
    'import os
import json
import pandas as pd
from app.utils.object_storage import get_file_path

async def execute(file_id, format="auto", max_rows=1000, sheet_name=None):
    """读取和解析各种格式的文件"""
    try:
        # 获取文件路径
        file_path = await get_file_path(file_id)
        
        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_id}"}
        
        # 自动检测格式
        if format == "auto":
            format = detect_format(file_path)
        
        # 根据格式读取文件
        if format in ["csv", "tsv"]:
            delimiter = "," if format == "csv" else "\\t"
            df = pd.read_csv(file_path, delimiter=delimiter, nrows=max_rows)
            return {
                "format": format,
                "rows": len(df),
                "columns": df.columns.tolist(),
                "data": df.head(min(100, max_rows)).to_dict(orient="records"),
                "preview": df.head(10).to_string()
            }
            
        elif format == "excel":
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=max_rows)
            sheet_names = pd.ExcelFile(file_path).sheet_names
            return {
                "format": "excel",
                "sheets": sheet_names,
                "current_sheet": sheet_name or sheet_names[0],
                "rows": len(df),
                "columns": df.columns.tolist(),
                "data": df.head(min(100, max_rows)).to_dict(orient="records"),
                "preview": df.head(10).to_string()
            }
            
        elif format == "json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "format": "json",
                "data": data,
                "preview": json.dumps(data, ensure_ascii=False, indent=2)[:1000] + "..." if len(json.dumps(data)) > 1000 else json.dumps(data, ensure_ascii=False, indent=2)
            }
            
        elif format == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(max_rows * 1000)  # 限制读取大小
            return {
                "format": "txt",
                "content": content,
                "preview": content[:1000] + "..." if len(content) > 1000 else content
            }
            
        else:
            return {"error": f"不支持的文件格式: {format}"}
            
    except Exception as e:
        return {"error": f"读取文件失败: {str(e)}"}

def detect_format(file_path):
    """检测文件格式"""
    extension = os.path.splitext(file_path)[1].lower()
    
    if extension in [".csv"]:
        return "csv"
    elif extension in [".xls", ".xlsx", ".xlsm"]:
        return "excel"
    elif extension in [".json"]:
        return "json"
    elif extension in [".txt", ".md", ".log"]:
        return "txt"
    elif extension in [".tsv"]:
        return "tsv"
    else:
        # 默认以文本方式读取
        return "txt"',
    true,
    '文件',
    null,
    'standard',
    '{
        "properties": {
            "file_id": {
                "type": "string",
                "description": "要读取的文件ID"
            },
            "format": {
                "type": "string",
                "description": "文件格式",
                "enum": ["auto", "csv", "excel", "json", "txt", "tsv"],
                "default": "auto"
            },
            "max_rows": {
                "type": "integer",
                "description": "最大读取行数",
                "default": 1000
            },
            "sheet_name": {
                "type": "string",
                "description": "Excel文件的工作表名称",
                "default": null
            }
        },
        "required": ["file_id"]
    }',
    '1.0.0',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
