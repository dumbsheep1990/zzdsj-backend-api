#!/usr/bin/env python3
"""
Agno框架系统配置初始化脚本
预设合理的默认配置，确保系统开箱即用
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.utils.core.database import get_db
from core.system_config.config_manager import SystemConfigManager

logger = logging.getLogger(__name__)

# Agno框架默认配置
AGNO_DEFAULT_CONFIGS = {
    # 模型配置
    "agno.models.default_chat_model": {
        "value": "gpt-4o-mini",
        "value_type": "string",
        "description": "Agno框架默认聊天模型",
        "category": "agno_models"
    },
    "agno.models.default_embedding_model": {
        "value": "text-embedding-3-small",
        "value_type": "string",
        "description": "Agno框架默认嵌入模型",
        "category": "agno_models"
    },
    "agno.models.default_rerank_model": {
        "value": None,
        "value_type": "string",
        "description": "Agno框架默认重排序模型",
        "category": "agno_models"
    },
    "agno.models.temperature": {
        "value": 0.7,
        "value_type": "float",
        "description": "模型温度参数",
        "category": "agno_models",
        "validation_rules": {"min": 0.0, "max": 2.0}
    },
    "agno.models.max_tokens": {
        "value": 4096,
        "value_type": "integer",
        "description": "最大生成token数",
        "category": "agno_models",
        "validation_rules": {"min": 100, "max": 32000}
    },
    "agno.models.timeout": {
        "value": 60,
        "value_type": "integer",
        "description": "模型请求超时时间(秒)",
        "category": "agno_models",
        "validation_rules": {"min": 10, "max": 300}
    },
    "agno.models.max_retries": {
        "value": 3,
        "value_type": "integer",
        "description": "模型请求最大重试次数",
        "category": "agno_models",
        "validation_rules": {"min": 0, "max": 10}
    },
    
    # 工具配置
    "agno.tools.enabled_tools": {
        "value": json.dumps([
            "web_search", "file_read", "file_write", 
            "calculator", "date_time", "weather"
        ]),
        "value_type": "json",
        "description": "默认启用的工具列表",
        "category": "agno_tools"
    },
    "agno.tools.tool_timeout": {
        "value": 30,
        "value_type": "integer",
        "description": "工具执行超时时间(秒)",
        "category": "agno_tools",
        "validation_rules": {"min": 5, "max": 300}
    },
    "agno.tools.max_tool_calls": {
        "value": 10,
        "value_type": "integer",
        "description": "单次对话最大工具调用次数",
        "category": "agno_tools",
        "validation_rules": {"min": 1, "max": 50}
    },
    "agno.tools.allow_dangerous_tools": {
        "value": False,
        "value_type": "boolean",
        "description": "是否允许使用危险工具",
        "category": "agno_tools"
    },
    "agno.tools.tool_call_logging": {
        "value": True,
        "value_type": "boolean",
        "description": "是否记录工具调用日志",
        "category": "agno_tools"
    },
    
    # 内存配置
    "agno.memory.memory_type": {
        "value": "simple",
        "value_type": "string",
        "description": "内存类型 (simple/persistent/redis)",
        "category": "agno_memory",
        "validation_rules": {"choices": ["simple", "persistent", "redis"]}
    },
    "agno.memory.max_memory_size": {
        "value": 1000,
        "value_type": "integer",
        "description": "最大内存大小",
        "category": "agno_memory",
        "validation_rules": {"min": 100, "max": 10000}
    },
    "agno.memory.memory_ttl": {
        "value": 3600,
        "value_type": "integer",
        "description": "内存生存时间(秒)",
        "category": "agno_memory",
        "validation_rules": {"min": 300, "max": 86400}
    },
    "agno.memory.persist_to_db": {
        "value": True,
        "value_type": "boolean",
        "description": "是否持久化内存到数据库",
        "category": "agno_memory"
    },
    "agno.memory.redis_url": {
        "value": None,
        "value_type": "string",
        "description": "Redis连接URL (内存类型为redis时使用)",
        "category": "agno_memory"
    },
    
    # 存储配置
    "agno.storage.storage_type": {
        "value": "postgresql",
        "value_type": "string",
        "description": "存储类型 (sqlite/postgresql/memory)",
        "category": "agno_storage",
        "validation_rules": {"choices": ["sqlite", "postgresql", "memory"]}
    },
    "agno.storage.storage_path": {
        "value": None,
        "value_type": "string",
        "description": "SQLite存储路径",
        "category": "agno_storage"
    },
    "agno.storage.connection_string": {
        "value": None,
        "value_type": "string",
        "description": "数据库连接字符串 (自动从系统配置获取)",
        "category": "agno_storage"
    },
    "agno.storage.table_prefix": {
        "value": "agno_",
        "value_type": "string",
        "description": "数据库表前缀",
        "category": "agno_storage"
    },
    "agno.storage.auto_create_tables": {
        "value": True,
        "value_type": "boolean",
        "description": "是否自动创建表",
        "category": "agno_storage"
    },
    
    # 性能配置
    "agno.performance.chunk_size": {
        "value": 1024,
        "value_type": "integer",
        "description": "文本分块大小",
        "category": "agno_performance",
        "validation_rules": {"min": 256, "max": 4096}
    },
    "agno.performance.chunk_overlap": {
        "value": 200,
        "value_type": "integer",
        "description": "分块重叠大小",
        "category": "agno_performance",
        "validation_rules": {"min": 0, "max": 1000}
    },
    "agno.performance.similarity_top_k": {
        "value": 5,
        "value_type": "integer",
        "description": "相似性搜索返回结果数",
        "category": "agno_performance",
        "validation_rules": {"min": 1, "max": 20}
    },
    "agno.performance.response_mode": {
        "value": "compact",
        "value_type": "string",
        "description": "响应模式 (compact/tree_summarize/accumulate)",
        "category": "agno_performance",
        "validation_rules": {"choices": ["compact", "tree_summarize", "accumulate"]}
    },
    "agno.performance.enable_streaming": {
        "value": True,
        "value_type": "boolean",
        "description": "是否启用流式响应",
        "category": "agno_performance"
    },
    "agno.performance.concurrent_requests": {
        "value": 10,
        "value_type": "integer",
        "description": "并发请求数限制",
        "category": "agno_performance",
        "validation_rules": {"min": 1, "max": 100}
    },
    
    # 功能配置
    "agno.features.show_tool_calls": {
        "value": True,
        "value_type": "boolean",
        "description": "是否显示工具调用",
        "category": "agno_features"
    },
    "agno.features.markdown": {
        "value": True,
        "value_type": "boolean",
        "description": "是否启用Markdown格式",
        "category": "agno_features"
    },
    "agno.features.reasoning_enabled": {
        "value": True,
        "value_type": "boolean",
        "description": "是否启用推理功能",
        "category": "agno_features"
    },
    "agno.features.debug_mode": {
        "value": False,
        "value_type": "boolean",
        "description": "是否启用调试模式",
        "category": "agno_features"
    },
    "agno.features.logging_level": {
        "value": "INFO",
        "value_type": "string",
        "description": "日志级别",
        "category": "agno_features",
        "validation_rules": {"choices": ["DEBUG", "INFO", "WARNING", "ERROR"]}
    }
}

# 配置类别定义
AGNO_CATEGORIES = {
    "agno_models": {
        "name": "agno_models",
        "description": "Agno框架模型配置",
        "is_system": True,
        "order": 100
    },
    "agno_tools": {
        "name": "agno_tools",
        "description": "Agno框架工具配置",
        "is_system": True,
        "order": 101
    },
    "agno_memory": {
        "name": "agno_memory",
        "description": "Agno框架内存配置",
        "is_system": True,
        "order": 102
    },
    "agno_storage": {
        "name": "agno_storage",
        "description": "Agno框架存储配置",
        "is_system": True,
        "order": 103
    },
    "agno_performance": {
        "name": "agno_performance",
        "description": "Agno框架性能配置",
        "is_system": True,
        "order": 104
    },
    "agno_features": {
        "name": "agno_features",
        "description": "Agno框架功能配置",
        "is_system": True,
        "order": 105
    }
}


async def init_agno_categories(config_manager: SystemConfigManager):
    """初始化Agno配置类别"""
    logger.info("初始化Agno配置类别...")
    
    for category_id, category_info in AGNO_CATEGORIES.items():
        result = await config_manager.create_category(
            name=category_info["name"],
            description=category_info["description"],
            is_system=category_info["is_system"],
            order=category_info["order"]
        )
        
        if result["success"]:
            logger.info(f"成功创建类别: {category_info['name']}")
        else:
            if "已存在" in result["error"]:
                logger.info(f"类别已存在，跳过: {category_info['name']}")
            else:
                logger.error(f"创建类别失败: {category_info['name']} - {result['error']}")


async def init_agno_configs(config_manager: SystemConfigManager):
    """初始化Agno配置项"""
    logger.info("初始化Agno配置项...")
    
    # 确保类别存在
    categories = await config_manager.get_categories()
    category_map = {cat["name"]: cat["id"] for cat in categories["data"]}
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for config_key, config_info in AGNO_DEFAULT_CONFIGS.items():
        try:
            category_name = config_info["category"]
            if category_name not in category_map:
                logger.error(f"配置类别不存在: {category_name}")
                error_count += 1
                continue
            
            result = await config_manager.create_config(
                key=config_key,
                value=config_info["value"],
                value_type=config_info["value_type"],
                category_id=category_map[category_name],
                description=config_info["description"],
                default_value=config_info["value"],
                is_system=True,
                validation_rules=config_info.get("validation_rules")
            )
            
            if result["success"]:
                logger.info(f"成功创建配置: {config_key}")
                success_count += 1
            else:
                if "已存在" in result["error"]:
                    logger.info(f"配置已存在，跳过: {config_key}")
                    skip_count += 1
                else:
                    logger.error(f"创建配置失败: {config_key} - {result['error']}")
                    error_count += 1
                    
        except Exception as e:
            logger.error(f"处理配置项失败: {config_key} - {str(e)}")
            error_count += 1
    
    logger.info(f"配置初始化完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {error_count}")


async def verify_agno_configs(config_manager: SystemConfigManager):
    """验证Agno配置的完整性"""
    logger.info("验证Agno配置完整性...")
    
    missing_configs = []
    invalid_configs = []
    
    for config_key in AGNO_DEFAULT_CONFIGS.keys():
        try:
            value = await config_manager.get_config_value(config_key)
            if value is None:
                missing_configs.append(config_key)
            else:
                logger.debug(f"配置验证通过: {config_key} = {value}")
        except Exception as e:
            logger.error(f"验证配置失败: {config_key} - {str(e)}")
            invalid_configs.append(config_key)
    
    if missing_configs:
        logger.warning(f"缺失的配置项: {missing_configs}")
    
    if invalid_configs:
        logger.error(f"无效的配置项: {invalid_configs}")
    
    if not missing_configs and not invalid_configs:
        logger.info("所有Agno配置验证通过!")
    
    return len(missing_configs) == 0 and len(invalid_configs) == 0


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("开始初始化Agno框架系统配置...")
    
    try:
        # 获取数据库连接
        db = next(get_db())
        config_manager = SystemConfigManager(db)
        
        # 1. 初始化配置类别
        await init_agno_categories(config_manager)
        
        # 2. 初始化配置项
        await init_agno_configs(config_manager)
        
        # 3. 验证配置完整性
        is_valid = await verify_agno_configs(config_manager)
        
        if is_valid:
            logger.info("✅ Agno框架系统配置初始化成功!")
        else:
            logger.error("❌ Agno框架系统配置初始化存在问题，请检查日志")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main()) 