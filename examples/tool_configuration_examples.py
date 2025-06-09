"""
工具配置示例
展示如何为不同类型的工具创建配置模式
"""

from typing import Dict, Any
import asyncio
from sqlalchemy.orm import Session
from core.tools.configuration_manager import ToolConfigurationManager

# ==================== 示例1: Agentic Chunk检索工具配置 ====================

AGENTIC_CHUNK_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "knowledge_base_id": {
            "type": "string",
            "title": "知识库ID",
            "description": "目标知识库的唯一标识符"
        },
        "chunk_size": {
            "type": "integer",
            "title": "块大小",
            "description": "文本块的最大字符数",
            "minimum": 100,
            "maximum": 4000,
            "default": 1000
        },
        "similarity_threshold": {
            "type": "number",
            "title": "相似度阈值",
            "description": "语义相似度的最小阈值",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 0.7
        },
        "max_results": {
            "type": "integer",
            "title": "最大结果数",
            "description": "返回的最大结果数量",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        }
    },
    "required": ["knowledge_base_id"],
    "additionalProperties": False
}

AGENTIC_CHUNK_UI_SCHEMA = {
    "knowledge_base_id": {
        "ui:widget": "knowledge_base_selector",
        "ui:placeholder": "选择知识库",
        "ui:help": "请选择要检索的知识库"
    },
    "chunk_size": {
        "ui:widget": "range",
        "ui:help": "推荐1000-2000字符"
    },
    "similarity_threshold": {
        "ui:widget": "range",
        "ui:step": 0.1,
        "ui:help": "阈值越高，结果越精确但可能更少"
    },
    "max_results": {
        "ui:widget": "updown",
        "ui:help": "建议10-20个结果以平衡质量和性能"
    }
}

AGENTIC_CHUNK_DEFAULT_CONFIG = {
    "chunk_size": 1500,
    "similarity_threshold": 0.75,
    "max_results": 15
}

AGENTIC_CHUNK_VALIDATION_RULES = {
    "custom_validations": [
        {
            "rule": "knowledge_base_exists",
            "description": "知识库必须存在且用户有访问权限",
            "validation_type": "async_api_check"
        }
    ]
}

# ==================== 示例2: 政策检索工具配置 ====================

POLICY_SEARCH_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "search_portals": {
            "type": "object",
            "title": "检索门户配置",
            "description": "配置政策检索的门户网站入口",
            "properties": {
                "primary_portal": {
                    "type": "object",
                    "title": "主要门户",
                    "properties": {
                        "name": {
                            "type": "string",
                            "title": "门户名称",
                            "description": "政府门户网站名称",
                            "default": "六盘水市人民政府"
                        },
                        "base_url": {
                            "type": "string",
                            "title": "门户基础地址",
                            "description": "政府门户网站的基础URL",
                            "format": "uri",
                            "default": "https://www.gzlps.gov.cn"
                        },
                        "search_endpoint": {
                            "type": "string",
                            "title": "搜索接口路径",
                            "description": "门户网站的搜索接口路径",
                            "default": "/so/search.shtml"
                        },
                        "enabled": {
                            "type": "boolean",
                            "title": "启用此门户",
                            "default": true
                        }
                    },
                    "required": ["name", "base_url", "search_endpoint"]
                },
                "backup_portals": {
                    "type": "array",
                    "title": "备用门户",
                    "description": "备用政府门户列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "title": "门户名称"},
                            "base_url": {"type": "string", "title": "门户地址", "format": "uri"},
                            "search_endpoint": {"type": "string", "title": "搜索路径"},
                            "enabled": {"type": "boolean", "title": "启用", "default": true}
                        },
                        "required": ["name", "base_url", "search_endpoint"]
                    },
                    "default": [
                        {
                            "name": "贵州省人民政府",
                            "base_url": "https://www.guizhou.gov.cn",
                            "search_endpoint": "/so/search.shtml",
                            "enabled": true
                        }
                    ]
                }
            },
            "required": ["primary_portal"]
        },
        "search_keywords": {
            "type": "object",
            "title": "搜索关键字配置",
            "description": "配置政策检索的关键字设置",
            "properties": {
                "default_keywords": {
                    "type": "array",
                    "title": "默认关键字",
                    "description": "预设的常用搜索关键字",
                    "items": {
                        "type": "string"
                    },
                    "default": ["惠民政策", "扶持政策", "补贴政策", "服务指南"],
                    "minItems": 1,
                    "maxItems": 20
                },
                "auto_expand_keywords": {
                    "type": "boolean",
                    "title": "自动扩展关键字",
                    "description": "是否基于意图识别自动扩展关键字",
                    "default": true
                },
                "keyword_categories": {
                    "type": "object",
                    "title": "关键字分类",
                    "description": "按类别组织的关键字",
                    "properties": {
                        "social_welfare": {
                            "type": "array",
                            "title": "社会福利",
                            "items": {"type": "string"},
                            "default": ["养老保险", "医疗保障", "低保政策", "残疾人补贴"]
                        },
                        "business_support": {
                            "type": "array", 
                            "title": "企业扶持",
                            "items": {"type": "string"},
                            "default": ["创业补贴", "税收优惠", "融资政策", "人才引进"]
                        },
                        "education": {
                            "type": "array",
                            "title": "教育相关",
                            "items": {"type": "string"},
                            "default": ["教育补贴", "学费减免", "助学贷款", "技能培训"]
                        },
                        "housing": {
                            "type": "array",
                            "title": "住房保障",
                            "items": {"type": "string"},
                            "default": ["公租房", "住房补贴", "购房优惠", "棚户区改造"]
                        }
                    }
                },
                "search_filters": {
                    "type": "object",
                    "title": "搜索过滤器",
                    "properties": {
                        "policy_types": {
                            "type": "array",
                            "title": "政策类型过滤",
                            "items": {
                                "type": "string",
                                "enum": ["通知", "办法", "意见", "法规", "标准", "指南"]
                            },
                            "default": ["通知", "办法", "意见"]
                        },
                        "date_range": {
                            "type": "object",
                            "title": "发布日期范围",
                            "properties": {
                                "enabled": {"type": "boolean", "default": false},
                                "start_date": {"type": "string", "format": "date"},
                                "end_date": {"type": "string", "format": "date"}
                            }
                        }
                    }
                }
            },
            "required": ["default_keywords"]
        },
        "search_strategy": {
            "type": "object", 
            "title": "检索策略配置",
            "description": "配置政策检索的策略和参数",
            "properties": {
                "strategy": {
                    "type": "string",
                    "title": "检索策略",
                    "description": "选择检索策略类型",
                    "enum": ["auto", "local_only", "provincial_only", "search_only"],
                    "enumNames": ["自动策略", "仅地方门户", "仅省级门户", "仅搜索引擎"],
                    "default": "auto"
                },
                "max_results": {
                    "type": "integer",
                    "title": "最大结果数",
                    "description": "单次检索返回的最大结果数量",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10
                },
                "quality_threshold": {
                    "type": "number",
                    "title": "质量阈值",
                    "description": "结果质量评分的最低阈值",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.6
                },
                "enable_intelligent_crawling": {
                    "type": "boolean",
                    "title": "启用智能爬取",
                    "description": "是否使用智能爬取增强检索结果",
                    "default": true
                },
                "region_priority": {
                    "type": "array",
                    "title": "地区优先级",
                    "description": "设置检索的地区优先级顺序",
                    "items": {"type": "string"},
                    "default": ["六盘水", "贵州", "全国"],
                    "minItems": 1
                }
            },
            "required": ["strategy", "max_results"]
        },
        "intent_recognition": {
            "type": "object",
            "title": "意图识别配置",
            "description": "配置基于用户意图的智能关键字识别",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "title": "启用意图识别",
                    "description": "是否启用基于用户查询意图的关键字自动识别",
                    "default": true
                },
                "intent_mapping": {
                    "type": "object",
                    "title": "意图映射规则",
                    "description": "用户意图到关键字的映射规则",
                    "properties": {
                        "welfare_inquiry": {
                            "type": "array",
                            "title": "福利咨询",
                            "items": {"type": "string"},
                            "default": ["社会保障", "福利政策", "补贴申请"]
                        },
                        "business_inquiry": {
                            "type": "array",
                            "title": "企业咨询", 
                            "items": {"type": "string"},
                            "default": ["企业扶持", "营商环境", "优惠政策"]
                        },
                        "procedure_inquiry": {
                            "type": "array",
                            "title": "办事咨询",
                            "items": {"type": "string"},
                            "default": ["办事指南", "申请流程", "所需材料"]
                        }
                    }
                },
                "confidence_threshold": {
                    "type": "number",
                    "title": "置信度阈值",
                    "description": "意图识别的最低置信度要求",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.7
                }
            }
        },
        "configuration_template": {
            "search_portals": {
                "primary_portal": {
                    "name": "六盘水市人民政府",
                    "base_url": "https://www.gzlps.gov.cn",
                    "search_endpoint": "/so/search.shtml",
                    "enabled": True
                },
                "backup_portals": [
                    {
                        "name": "贵州省人民政府",
                        "base_url": "https://www.guizhou.gov.cn", 
                        "search_endpoint": "/so/search.shtml",
                        "enabled": True
                    }
                ]
            },
            "search_keywords": {
                "default_keywords": ["惠民政策", "扶持政策", "补贴政策", "服务指南"],
                "auto_expand_keywords": True,
                "keyword_categories": {
                    "social_welfare": ["养老保险", "医疗保障", "低保政策"],
                    "business_support": ["创业补贴", "税收优惠", "融资政策"],
                    "education": ["教育补贴", "学费减免", "助学贷款"],
                    "housing": ["公租房", "住房补贴", "购房优惠"]
                },
                "search_filters": {
                    "policy_types": ["通知", "办法", "意见"],
                    "date_range": {"enabled": False}
                }
            },
            "search_strategy": {
                "strategy": "auto",
                "max_results": 10,
                "quality_threshold": 0.6,
                "enable_intelligent_crawling": True,
                "region_priority": ["六盘水", "贵州", "全国"]
            },
            "intent_recognition": {
                "enabled": True,
                "intent_mapping": {
                    "welfare_inquiry": ["社会保障", "福利政策", "补贴申请"],
                    "business_inquiry": ["企业扶持", "营商环境", "优惠政策"],
                    "procedure_inquiry": ["办事指南", "申请流程", "所需材料"]
                },
                "confidence_threshold": 0.7
            }
        },
        "validation_rules": {
            "search_portals.primary_portal.base_url": {
                "required": True,
                "format": "uri",
                "message": "主要门户的基础地址必须是有效的URL"
            },
            "search_keywords.default_keywords": {
                "required": True,
                "min_items": 1,
                "max_items": 20,
                "message": "至少需要1个默认关键字，最多20个"
            },
            "search_strategy.max_results": {
                "required": True,
                "minimum": 1,
                "maximum": 50,
                "message": "最大结果数必须在1-50之间"
            }
        }
    },
    "required": ["search_portals", "search_keywords", "search_strategy"]
}

POLICY_SEARCH_UI_SCHEMA = {
    "policy_database": {
        "ui:widget": "radio",
        "ui:options": {
            "inline": True
        }
    },
    "policy_types": {
        "ui:widget": "checkboxes",
        "ui:options": {
            "inline": False
        }
    },
    "date_range": {
        "ui:field": "date_range_picker",
        "start_date": {
            "ui:widget": "date"
        },
        "end_date": {
            "ui:widget": "date"
        }
    },
    "departments": {
        "ui:widget": "department_multi_select",
        "ui:placeholder": "选择发布部门"
    },
    "keywords_mode": {
        "ui:widget": "radio",
        "ui:options": {
            "inline": True
        }
    },
    "result_format": {
        "ui:widget": "select"
    },
    "api_credentials": {
        "api_key": {
            "ui:widget": "password",
            "ui:placeholder": "输入API密钥"
        },
        "endpoint": {
            "ui:placeholder": "https://api.policy.gov.cn"
        }
    }
}

POLICY_SEARCH_DEFAULT_CONFIG = {
    "policy_database": "all",
    "keywords_mode": "semantic",
    "result_format": "summary",
    "api_credentials": {
        "endpoint": "https://api.policy.gov.cn"
    }
}

# ==================== 示例3: 天气查询工具配置 ====================

WEATHER_API_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "api_provider": {
            "type": "string",
            "title": "天气API提供商",
            "enum": ["openweather", "weatherapi", "qweather"],
            "enumNames": ["OpenWeather", "WeatherAPI", "和风天气"],
            "description": "选择天气数据提供商"
        },
        "api_key": {
            "type": "string",
            "title": "API密钥",
            "format": "password",
            "description": "天气API的访问密钥"
        },
        "default_location": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "title": "默认城市"
                },
                "latitude": {
                    "type": "number",
                    "title": "纬度",
                    "minimum": -90,
                    "maximum": 90
                },
                "longitude": {
                    "type": "number", 
                    "title": "经度",
                    "minimum": -180,
                    "maximum": 180
                }
            },
            "required": ["city"],
            "title": "默认位置"
        },
        "units": {
            "type": "string",
            "title": "温度单位",
            "enum": ["celsius", "fahrenheit"],
            "enumNames": ["摄氏度", "华氏度"],
            "default": "celsius"
        },
        "language": {
            "type": "string",
            "title": "语言",
            "enum": ["zh", "en"],
            "enumNames": ["中文", "English"],
            "default": "zh"
        },
        "cache_duration": {
            "type": "integer",
            "title": "缓存时长(分钟)",
            "minimum": 5,
            "maximum": 120,
            "default": 15,
            "description": "天气数据缓存的有效时长"
        }
    },
    "required": ["api_provider", "api_key", "default_location"],
    "additionalProperties": False
}

# ==================== 配置创建示例函数 ====================

async def create_agentic_chunk_configuration(db: Session, tool_id: str):
    """创建Agentic Chunk工具配置示例"""
    manager = ToolConfigurationManager(db)
    
    result = await manager.create_configuration_schema(
        tool_id=tool_id,
        config_schema=AGENTIC_CHUNK_CONFIG_SCHEMA,
        display_name="智能分块检索配置",
        description="配置智能分块检索工具的参数"
    )
    
    return result

async def create_policy_search_configuration(db: Session, tool_id: str):
    """创建政策检索工具配置示例"""
    manager = ToolConfigurationManager(db)
    
    result = await manager.create_configuration_schema(
        tool_id=tool_id,
        config_schema=POLICY_SEARCH_CONFIG_SCHEMA,
        display_name="政策检索配置",
        description="配置政策检索工具的参数，包括数据库范围、API凭据等",
        default_config=POLICY_SEARCH_DEFAULT_CONFIG,
        ui_schema=POLICY_SEARCH_UI_SCHEMA
    )
    
    return result

async def create_weather_api_configuration(db: Session, tool_id: str):
    """创建天气API工具配置示例"""
    manager = ToolConfigurationManager(db)
    
    result = await manager.create_configuration_schema(
        tool_id=tool_id,
        config_schema=WEATHER_API_CONFIG_SCHEMA,
        display_name="天气API配置",
        description="配置天气查询工具的API提供商和访问凭据",
        default_config={
            "units": "celsius",
            "language": "zh",
            "cache_duration": 15
        },
        ui_schema={
            "api_provider": {
                "ui:widget": "select",
                "ui:placeholder": "选择天气API提供商"
            },
            "api_key": {
                "ui:widget": "password",
                "ui:placeholder": "输入API密钥",
                "ui:help": "请到对应API提供商官网申请密钥"
            },
            "default_location": {
                "city": {
                    "ui:placeholder": "如：北京市"
                }
            },
            "cache_duration": {
                "ui:widget": "range"
            }
        }
    )
    
    return result

# ==================== 批量创建示例 ====================

async def setup_example_configurations(db: Session):
    """批量创建示例配置"""
    # 注意：这里的tool_id需要替换为实际的工具ID
    configurations = [
        ("agentic_chunk_tool_id", create_agentic_chunk_configuration),
        ("policy_search_tool_id", create_policy_search_configuration),
        ("weather_api_tool_id", create_weather_api_configuration)
    ]
    
    results = []
    for tool_id, create_func in configurations:
        try:
            result = await create_func(db, tool_id)
            results.append({
                "tool_id": tool_id,
                "success": result["success"],
                "schema_id": result.get("data", {}).get("schema_id") if result["success"] else None,
                "error": result.get("error") if not result["success"] else None
            })
        except Exception as e:
            results.append({
                "tool_id": tool_id,
                "success": False,
                "error": str(e)
            })
    
    return results

if __name__ == "__main__":
    print("工具配置示例已创建")
    print("使用方法：")
    print("1. 调用相应的创建函数为工具设置配置模式")
    print("2. 用户通过前端界面配置工具参数")
    print("3. 工具执行前会自动验证配置的有效性") 