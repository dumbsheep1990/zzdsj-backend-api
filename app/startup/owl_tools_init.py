"""
OWL框架工具初始化模块
系统启动时初始化OWL框架的内置工具
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.owl_tool_service import OwlToolService

logger = logging.getLogger(__name__)

async def initialize_owl_tools(db: Session) -> None:
    """初始化OWL框架工具
    
    Args:
        db: 数据库会话
    """
    try:
        # 获取OwlToolService实例
        tool_service = OwlToolService(db)
        
        # 系统用户ID (管理员)
        system_user_id = "system"
        
        # 注册内置工具包
        await _register_default_toolkits(tool_service, system_user_id)
        
        # 注册内置工具
        registered_tools = await _register_default_tools(tool_service, system_user_id)
        
        logger.info(f"成功注册 {len(registered_tools)} 个OWL框架工具")
        
    except Exception as e:
        logger.error(f"初始化OWL框架工具时出错: {str(e)}")


async def _register_default_toolkits(tool_service: OwlToolService, user_id: str) -> List[str]:
    """注册默认工具包
    
    Args:
        tool_service: OWL框架工具服务
        user_id: 用户ID (系统用户)
    
    Returns:
        List[str]: 注册的工具包名称列表
    """
    default_toolkits = [
        {
            "name": "ArxivToolkit",
            "description": "学术论文搜索和下载工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "AudioAnalysisToolkit",
            "description": "音频处理和分析工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "BrowserToolkit",
            "description": "网页浏览和交互工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "CodeExecutionToolkit",
            "description": "代码执行工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "DalleToolkit",
            "description": "图像生成工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "ExcelToolkit",
            "description": "Excel文件处理工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "FileWriteTool",
            "description": "文件创建和修改工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "GoogleMapsToolkit",
            "description": "地图服务工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "GoogleScholarToolkit",
            "description": "学术信息查询工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "ImageAnalysisToolkit",
            "description": "图像分析工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "MathToolkit",
            "description": "数学计算工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "MemoryToolkit",
            "description": "记忆管理工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "NetworkXToolkit",
            "description": "图分析工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "OpenAPIToolkit",
            "description": "API规范工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "SearchToolkit",
            "description": "网络搜索工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "TerminalToolkit",
            "description": "终端操作工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "VideoAnalysisToolkit",
            "description": "视频分析工具包",
            "is_enabled": True,
            "config": {}
        },
        {
            "name": "WeatherToolkit",
            "description": "天气数据工具包",
            "is_enabled": True,
            "config": {}
        },
    ]
    
    registered_toolkits = []
    
    for toolkit_data in default_toolkits:
        try:
            # 检查工具包是否已存在
            existing_toolkit = await tool_service.get_toolkit_by_name(toolkit_data["name"])
            
            if not existing_toolkit:
                # 注册工具包
                await tool_service.register_toolkit(toolkit_data, user_id)
                registered_toolkits.append(toolkit_data["name"])
                logger.info(f"注册工具包: {toolkit_data['name']}")
            else:
                logger.info(f"工具包已存在: {toolkit_data['name']}")
        except Exception as e:
            logger.error(f"注册工具包 {toolkit_data['name']} 时出错: {str(e)}")
    
    return registered_toolkits


async def _register_default_tools(tool_service: OwlToolService, user_id: str) -> List[str]:
    """注册默认工具
    
    Args:
        tool_service: OWL框架工具服务
        user_id: 用户ID (系统用户)
    
    Returns:
        List[str]: 注册的工具名称列表
    """
    default_tools = [
        # 搜索工具包
        {
            "name": "search_google",
            "toolkit_name": "SearchToolkit",
            "description": "使用Google搜索引擎搜索信息",
            "function_name": "search_google",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            "requires_api_key": True,
            "api_key_config": {
                "key_name": "GOOGLE_API_KEY",
                "key_type": "environment"
            }
        },
        {
            "name": "search_wiki",
            "toolkit_name": "SearchToolkit",
            "description": "在维基百科上搜索信息",
            "function_name": "search_wiki",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            "requires_api_key": False
        },
        
        # 数学工具包
        {
            "name": "calculator",
            "toolkit_name": "MathToolkit",
            "description": "计算数学表达式",
            "function_name": "calculate",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式"
                    }
                },
                "required": ["expression"]
            },
            "requires_api_key": False
        },
        
        # ArXiv工具包
        {
            "name": "search_arxiv",
            "toolkit_name": "ArxivToolkit",
            "description": "在arXiv上搜索学术论文",
            "function_name": "search",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            "requires_api_key": False
        },
        
        # 文件工具包
        {
            "name": "write_file",
            "toolkit_name": "FileWriteTool",
            "description": "写入文件内容",
            "function_name": "write",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容"
                    },
                    "append": {
                        "type": "boolean",
                        "description": "是否追加内容",
                        "default": False
                    }
                },
                "required": ["filepath", "content"]
            },
            "requires_api_key": False
        },
        
        # 图像分析工具包
        {
            "name": "analyze_image",
            "toolkit_name": "ImageAnalysisToolkit",
            "description": "分析图像内容",
            "function_name": "analyze",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图像文件路径或URL"
                    },
                    "analyze_objects": {
                        "type": "boolean",
                        "description": "是否分析对象",
                        "default": True
                    },
                    "analyze_text": {
                        "type": "boolean",
                        "description": "是否分析文本",
                        "default": True
                    }
                },
                "required": ["image_path"]
            },
            "requires_api_key": True,
            "api_key_config": {
                "key_name": "VISION_API_KEY",
                "key_type": "environment"
            }
        },
        
        # 天气工具包
        {
            "name": "get_weather",
            "toolkit_name": "WeatherToolkit",
            "description": "获取城市天气信息",
            "function_name": "get_weather",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    },
                    "country_code": {
                        "type": "string",
                        "description": "国家代码",
                        "default": "cn"
                    }
                },
                "required": ["city"]
            },
            "requires_api_key": True,
            "api_key_config": {
                "key_name": "OPENWEATHERMAP_API_KEY",
                "key_type": "environment"
            }
        },
        
        # 代码执行工具包
        {
            "name": "execute_python",
            "toolkit_name": "CodeExecutionToolkit",
            "description": "执行Python代码",
            "function_name": "execute_python",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的Python代码"
                    }
                },
                "required": ["code"]
            },
            "requires_api_key": False
        },
        
        # 终端工具包
        {
            "name": "run_shell_command",
            "toolkit_name": "TerminalToolkit",
            "description": "在系统上执行shell命令",
            "function_name": "run_command",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的shell命令"
                    }
                },
                "required": ["command"]
            },
            "requires_api_key": False
        },
        
        # 视频分析工具包
        {
            "name": "analyze_video",
            "toolkit_name": "VideoAnalysisToolkit",
            "description": "分析视频内容",
            "function_name": "analyze",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "video_path": {
                        "type": "string",
                        "description": "视频文件路径或URL"
                    },
                    "sample_rate": {
                        "type": "integer",
                        "description": "采样率（每秒帧数）",
                        "default": 1
                    }
                },
                "required": ["video_path"]
            },
            "requires_api_key": True,
            "api_key_config": {
                "key_name": "VISION_API_KEY",
                "key_type": "environment"
            }
        },
        
        # DALL-E工具包
        {
            "name": "generate_image",
            "toolkit_name": "DalleToolkit",
            "description": "使用DALL-E生成图像",
            "function_name": "generate",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "生成图像的提示"
                    },
                    "size": {
                        "type": "string",
                        "description": "图像尺寸",
                        "enum": ["256x256", "512x512", "1024x1024"],
                        "default": "512x512"
                    }
                },
                "required": ["prompt"]
            },
            "requires_api_key": True,
            "api_key_config": {
                "key_name": "OPENAI_API_KEY",
                "key_type": "environment"
            }
        },
        
        # 浏览器工具包
        {
            "name": "browse_website",
            "toolkit_name": "BrowserToolkit",
            "description": "浏览网站并提取内容",
            "function_name": "browse",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要浏览的网站URL"
                    },
                    "extract_text": {
                        "type": "boolean",
                        "description": "是否提取文本",
                        "default": True
                    },
                    "extract_links": {
                        "type": "boolean",
                        "description": "是否提取链接",
                        "default": False
                    }
                },
                "required": ["url"]
            },
            "requires_api_key": False
        },
        
        # Excel工具包
        {
            "name": "parse_excel",
            "toolkit_name": "ExcelToolkit",
            "description": "解析Excel文件内容",
            "function_name": "parse",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Excel文件路径"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "工作表名称",
                        "default": "Sheet1"
                    }
                },
                "required": ["filepath"]
            },
            "requires_api_key": False
        },
        
        # 记忆工具包
        {
            "name": "save_memory",
            "toolkit_name": "MemoryToolkit",
            "description": "保存记忆到存储",
            "function_name": "save",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "记忆的键名"
                    },
                    "value": {
                        "type": "string",
                        "description": "记忆的内容"
                    }
                },
                "required": ["key", "value"]
            },
            "requires_api_key": False
        },
        {
            "name": "load_memory",
            "toolkit_name": "MemoryToolkit",
            "description": "从存储加载记忆",
            "function_name": "load",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "记忆的键名"
                    }
                },
                "required": ["key"]
            },
            "requires_api_key": False
        }
    ]
    
    registered_tools = []
    
    for tool_data in default_tools:
        try:
            # 检查工具是否已存在
            existing_tool = await tool_service.get_tool_by_name(tool_data["name"])
            
            if not existing_tool:
                # 注册工具
                await tool_service.register_tool(tool_data, user_id)
                registered_tools.append(tool_data["name"])
                logger.info(f"注册工具: {tool_data['name']}")
            else:
                logger.info(f"工具已存在: {tool_data['name']}")
        except Exception as e:
            logger.error(f"注册工具 {tool_data['name']} 时出错: {str(e)}")
    
    return registered_tools
