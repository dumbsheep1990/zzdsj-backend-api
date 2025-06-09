"""
图数据库启动时初始化和配置检查
确保图数据库配置正确并能正常连接
"""

import logging
import asyncio
from typing import Dict, Any

from app.config import settings
from app.config.graph_database_config import (
    get_graph_database_config_from_app,
    validate_graph_config,
    GraphDatabaseConfigManager
)
from app.utils.storage.graph_storage.graph_database_factory import (
    GraphDatabaseFactory,
    graph_db_manager
)

logger = logging.getLogger(__name__)

async def check_graph_database_config() -> Dict[str, Any]:
    """检查图数据库配置"""
    try:
        # 检查功能是否启用
        if not getattr(settings, 'GRAPH_DATABASE_ENABLED', True):
            return {
                "enabled": False,
                "status": "disabled",
                "message": "图数据库功能已禁用"
            }
        
        # 获取配置
        config = get_graph_database_config_from_app()
        
        # 验证配置
        validation_result = validate_graph_config(config)
        
        if not validation_result["valid"]:
            return {
                "enabled": True,
                "status": "error",
                "message": "图数据库配置错误",
                "issues": validation_result["issues"],
                "config_summary": validation_result["config_summary"]
            }
        
        return {
            "enabled": True,
            "status": "valid",
            "message": "图数据库配置正确",
            "config_summary": validation_result["config_summary"],
            "database_type": config.db_type.value,
            "storage_strategy": config.storage_strategy.value,
            "isolation_strategy": config.isolation_config.get("strategy", "unknown")
        }
        
    except Exception as e:
        logger.error(f"检查图数据库配置失败: {str(e)}")
        return {
            "enabled": True,
            "status": "error",
            "message": f"配置检查失败: {str(e)}"
        }

async def test_graph_database_connection() -> Dict[str, Any]:
    """测试图数据库连接"""
    try:
        # 获取配置
        config = get_graph_database_config_from_app()
        
        # 创建测试连接
        test_db = await GraphDatabaseFactory.create_graph_database(config)
        
        try:
            # 初始化连接
            await test_db.initialize()
            
            # 测试基本操作
            test_tenant = "test_tenant"
            await test_db.create_tenant_context(test_tenant)
            
            # 测试保存和加载
            test_triples = [
                {"subject": "测试实体1", "predicate": "关系", "object": "测试实体2", "confidence": 1.0}
            ]
            
            save_result = await test_db.save_knowledge_graph(test_tenant, "test_graph", test_triples)
            load_result = await test_db.load_knowledge_graph(test_tenant, "test_graph")
            
            # 清理测试数据
            await test_db.delete_knowledge_graph(test_tenant, "test_graph")
            
            await test_db.close()
            
            return {
                "status": "success",
                "message": "图数据库连接测试成功",
                "database_type": config.db_type.value,
                "save_success": save_result.get("success", False),
                "load_success": load_result.get("success", False),
                "triples_count": len(load_result.get("triples", []))
            }
            
        except Exception as test_error:
            await test_db.close()
            raise test_error
            
    except Exception as e:
        logger.error(f"图数据库连接测试失败: {str(e)}")
        return {
            "status": "error",
            "message": f"连接测试失败: {str(e)}"
        }

async def initialize_graph_database() -> Dict[str, Any]:
    """初始化图数据库"""
    try:
        # 检查配置
        config_check = await check_graph_database_config()
        
        if not config_check["enabled"]:
            return config_check
        
        if config_check["status"] == "error":
            return config_check
        
        # 测试连接
        connection_test = await test_graph_database_connection()
        
        if connection_test["status"] == "error":
            return {
                "status": "error",
                "message": "图数据库连接失败",
                "config_check": config_check,
                "connection_test": connection_test
            }
        
        # 初始化全局管理器
        config = get_graph_database_config_from_app()
        await graph_db_manager.initialize(config)
        
        logger.info(f"图数据库初始化成功: {config.db_type.value}")
        
        return {
            "status": "success",
            "message": "图数据库初始化成功",
            "config_check": config_check,
            "connection_test": connection_test,
            "database_type": config.db_type.value,
            "initialized": True
        }
        
    except Exception as e:
        logger.error(f"图数据库初始化失败: {str(e)}")
        return {
            "status": "error",
            "message": f"初始化失败: {str(e)}",
            "initialized": False
        }

async def get_graph_database_status() -> Dict[str, Any]:
    """获取图数据库状态"""
    try:
        config_check = await check_graph_database_config()
        
        if not config_check["enabled"]:
            return config_check
        
        # 检查是否已初始化
        try:
            db = await graph_db_manager.get_database()
            initialized = True
        except:
            initialized = False
        
        return {
            "enabled": config_check["enabled"],
            "status": config_check["status"],
            "initialized": initialized,
            "config_summary": config_check.get("config_summary", {}),
            "database_type": config_check.get("database_type"),
            "storage_strategy": config_check.get("storage_strategy"),
            "isolation_strategy": config_check.get("isolation_strategy")
        }
        
    except Exception as e:
        logger.error(f"获取图数据库状态失败: {str(e)}")
        return {
            "enabled": False,
            "status": "error",
            "message": str(e)
        }

def get_graph_database_config_summary() -> Dict[str, Any]:
    """获取图数据库配置摘要"""
    try:
        config = get_graph_database_config_from_app()
        
        summary = {
            "enabled": getattr(settings, 'GRAPH_DATABASE_ENABLED', True),
            "database_type": config.db_type.value,
            "storage_strategy": config.storage_strategy.value,
            "isolation_strategy": config.isolation_config.get("strategy", "unknown"),
            "tenant_sharding": config.isolation_config.get("tenant_sharding", "user_group")
        }
        
        # 添加特定数据库的配置信息
        if config.db_type.value == "arangodb":
            summary.update({
                "arango_hosts": config.connection_config.get("hosts"),
                "arango_enable_networkx": config.arangodb_config.get("enable_networkx", True),
                "arango_batch_size": config.performance_config.get("batch_size", 1000)
            })
        elif config.db_type.value == "postgresql_age":
            summary.update({
                "postgresql_url": config.connection_config.get("database_url", "").replace("://.*@", "://***@"),  # 隐藏密码
                "networkx_cache": config.networkx_config.get("enable_caching", True),
                "networkx_algorithms": config.networkx_config.get("algorithms", [])
            })
        
        return summary
        
    except Exception as e:
        logger.error(f"获取配置摘要失败: {str(e)}")
        return {
            "enabled": False,
            "error": str(e)
        }

# 启动时检查函数
async def startup_graph_database_check():
    """应用启动时的图数据库检查"""
    logger.info("开始图数据库启动检查...")
    
    try:
        # 获取状态
        status = await get_graph_database_status()
        
        if not status["enabled"]:
            logger.info("图数据库功能已禁用")
            return
        
        if status["status"] == "error":
            logger.warning(f"图数据库配置错误: {status.get('message', '未知错误')}")
            return
        
        # 如果未初始化，尝试初始化
        if not status["initialized"]:
            logger.info("图数据库未初始化，正在初始化...")
            init_result = await initialize_graph_database()
            
            if init_result["status"] == "success":
                logger.info("图数据库初始化成功")
            else:
                logger.error(f"图数据库初始化失败: {init_result['message']}")
        else:
            logger.info("图数据库已初始化")
        
        # 输出配置摘要
        config_summary = get_graph_database_config_summary()
        logger.info(f"图数据库配置: {config_summary}")
        
    except Exception as e:
        logger.error(f"图数据库启动检查失败: {str(e)}")

if __name__ == "__main__":
    # 独立测试
    async def main():
        print("图数据库配置检查...")
        result = await check_graph_database_config()
        print(f"配置检查结果: {result}")
        
        if result["enabled"] and result["status"] == "valid":
            print("\n连接测试...")
            test_result = await test_graph_database_connection()
            print(f"连接测试结果: {test_result}")
    
    asyncio.run(main()) 