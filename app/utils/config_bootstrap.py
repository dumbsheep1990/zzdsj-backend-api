"""
配置引导程序 - 负责配置验证、服务检查和初始化
"""
import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.utils.config_validator import ConfigValidator
from app.utils.service_health import ServiceHealthChecker
from app.utils.config_state import config_state_manager
from app.utils.database import db_manager

logger = logging.getLogger(__name__)

class ConfigBootstrap:
    """配置引导程序，负责配置验证、服务检查和初始化"""
    
    @staticmethod
    async def validate_and_check(validate_config=True, check_services=True) -> Dict[str, Any]:
        """验证配置并检查服务"""
        result = {
            "config_valid": True,
            "missing_configs": [],
            "services_healthy": {},
            "all_services_healthy": True,
            "validation_details": {},
            "service_details": {}
        }
        
        # 配置验证
        if validate_config:
            logger.info("正在验证配置...")
            validation_result = ConfigValidator.validate_all_configs()
            result["config_valid"] = validation_result.get("all_valid", False)
            result["validation_details"] = validation_result
            
            # 更新配置状态
            config_state_manager.update_validation_details(validation_result)
            
            # 检查是否有错误消息
            for service, details in validation_result.get("configs", {}).items():
                if not details.get("valid", True) and details.get("messages"):
                    for msg in details.get("messages", []):
                        result["missing_configs"].append(f"{service}: {msg}")
        
        # 服务健康检查
        if check_services:
            logger.info("正在检查服务健康状态...")
            service_health = await ServiceHealthChecker.check_all_services()
            result["service_details"] = service_health
            
            # 构建简化的健康状态字典
            health_status = {}
            all_healthy = True
            for service, details in service_health.items():
                status = details.get("status", False)
                health_status[service] = status
                if not status:
                    all_healthy = False
                    
                    # 打印错误信息
                    error = details.get("error")
                    if error:
                        logger.warning(f"服务 {service} 不可用: {error}")
            
            result["services_healthy"] = health_status
            result["all_services_healthy"] = all_healthy
            
            # 更新配置状态
            config_state_manager.update_service_health(service_health)
        
        # 导出配置状态
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_state_manager.export_state(f"{logs_dir}/config_state_{timestamp}.json")
        
        return result
    
    @staticmethod
    async def sync_configs_to_db(db: Session) -> Dict[str, Any]:
        """将配置同步到数据库"""
        from app.services.system_config_service import SystemConfigService
        from app.config import settings
        
        logger.info("正在同步配置到数据库...")
        
        try:
            # 创建配置服务
            config_service = SystemConfigService(db)
            
            # 初始化默认类别
            categories = config_service.initialize_default_categories()
            logger.info(f"已初始化 {len(categories)} 个默认配置类别")
            
            # 从设置同步配置
            created, updated = config_service.sync_from_settings(settings)
            logger.info(f"已同步配置: 创建 {created} 项, 更新 {updated} 项")
            
            # 记录被环境变量覆盖的配置
            for env_key in config_state_manager.state.override_sources.get("env", []):
                config = config_service.get_config_by_key(env_key)
                if config:
                    config_service.mark_config_overridden(env_key, "env")
            
            # 记录被文件覆盖的配置
            for file_override in config_state_manager.state.override_sources.get("file", []):
                if ":" in file_override:
                    file_name, key = file_override.split(":", 1)
                    config = config_service.get_config_by_key(key)
                    if config:
                        config_service.mark_config_overridden(key, f"file:{file_name}")
            
            return {
                "success": True,
                "created": created,
                "updated": updated,
                "categories": len(categories)
            }
        except Exception as e:
            logger.error(f"同步配置到数据库时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def save_service_health_to_db(db: Session, health_results: Dict[str, Dict[str, Any]]) -> bool:
        """将服务健康状态保存到数据库"""
        from app.services.system_config_service import SystemConfigService
        
        logger.info("正在保存服务健康状态到数据库...")
        
        try:
            # 创建配置服务
            config_service = SystemConfigService(db)
            
            # 保存每个服务的健康状态
            for service_name, details in health_results.items():
                config_service.save_health_record(
                    service_name=service_name,
                    status=details.get("status", False),
                    response_time_ms=details.get("response_time_ms"),
                    error_message=details.get("error"),
                    details=details.get("details")
                )
            
            return True
        except Exception as e:
            logger.error(f"保存服务健康状态到数据库时出错: {str(e)}")
            return False
    
    @classmethod
    async def run_bootstrap(cls) -> Dict[str, Any]:
        """运行完整的启动引导流程"""
        result = {
            "config_validation": {},
            "service_health": {},
            "db_sync": {},
            "health_record": False
        }
        
        # 第1步: 配置验证和服务检查
        logger.info("开始配置引导流程...")
        bootstrap_result = await cls.validate_and_check()
        result["config_validation"] = bootstrap_result
        
        # 检查数据库服务是否可用
        db_available = bootstrap_result.get("services_healthy", {}).get("database", False)
        
        # 第2步: 如果数据库可用，同步配置到数据库
        if db_available:
            try:
                db_result = db_manager.execute_with_session(
                    lambda db: asyncio.run(cls.sync_configs_to_db(db))
                )
                result["db_sync"] = db_result
                
                # 第3步: 保存服务健康状态到数据库
                health_results = bootstrap_result.get("service_details", {})
                health_record = db_manager.execute_with_session(
                    lambda db: asyncio.run(cls.save_service_health_to_db(db, health_results))
                )
                result["health_record"] = health_record
            except Exception as e:
                logger.error(f"数据库操作过程中出错: {str(e)}")
                result["db_sync"] = {"success": False, "error": str(e)}
        else:
            logger.warning("数据库服务不可用，跳过配置同步")
            result["db_sync"] = {"success": False, "error": "数据库服务不可用"}
        
        return result
