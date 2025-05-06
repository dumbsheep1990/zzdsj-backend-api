"""
系统配置API - 提供配置管理和系统自检API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.utils.database import get_db
from app.services.system_config_service import SystemConfigService
from app.utils.config_validator import ConfigValidator
from app.utils.service_health import ServiceHealthChecker
from app.utils.config_state import config_state_manager
from app.utils.config_bootstrap import ConfigBootstrap
import asyncio

router = APIRouter(prefix="/api/system", tags=["系统管理"])

# ============ 输入输出模型 ============

class ConfigCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    order: Optional[int] = 0


class ConfigCategoryCreate(ConfigCategoryBase):
    pass


class ConfigCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class ConfigCategory(ConfigCategoryBase):
    id: str
    is_system: bool
    
    class Config:
        orm_mode = True


class ConfigBase(BaseModel):
    key: str
    value: Any
    category_id: str
    description: Optional[str] = None
    is_sensitive: Optional[bool] = False
    validation_rules: Optional[Dict[str, Any]] = None
    visible_level: Optional[str] = "all"


class ConfigCreate(ConfigBase):
    value_type: str
    default_value: Optional[Any] = None
    is_system: Optional[bool] = False


class ConfigUpdate(BaseModel):
    value: Optional[Any] = None
    description: Optional[str] = None
    is_sensitive: Optional[bool] = None
    validation_rules: Optional[Dict[str, Any]] = None
    visible_level: Optional[str] = None
    change_notes: Optional[str] = None


class Config(ConfigBase):
    id: str
    value_type: str
    default_value: Optional[Any] = None
    is_system: bool
    is_encrypted: bool
    is_overridden: bool
    override_source: Optional[str] = None
    
    class Config:
        orm_mode = True


class ConfigHistoryItem(BaseModel):
    id: str
    old_value: Optional[Any] = None
    new_value: Any
    change_source: str
    changed_by: Optional[str] = None
    change_notes: Optional[str] = None
    created_at: str
    
    class Config:
        orm_mode = True


class ServiceHealth(BaseModel):
    service_name: str
    status: bool
    check_time: str
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


class ConfigStateResponse(BaseModel):
    loaded: bool
    validated: bool
    last_updated: Optional[str] = None
    missing_configs: List[str] = []
    service_health: Dict[str, bool] = {}
    override_sources: Dict[str, List[str]] = {"env": [], "file": []}
    validation_details: Dict[str, Any] = {}


# ============ API端点 ============

@router.get("/config-status", response_model=ConfigStateResponse)
async def get_config_status():
    """获取系统配置状态"""
    return config_state_manager.get_state()


@router.post("/refresh-config")
async def refresh_config():
    """刷新系统配置"""
    success = config_state_manager.refresh_config()
    return {"success": success, "message": "配置已刷新" if success else "刷新配置失败"}


@router.get("/health-check")
async def health_check(save_to_db: bool = False, db: Session = Depends(get_db)):
    """检查系统健康状态"""
    # 执行健康检查
    health_results = await ServiceHealthChecker.check_all_services()
    
    # 保存到数据库
    if save_to_db:
        await ConfigBootstrap.save_service_health_to_db(db, health_results)
    
    # 更新配置状态
    config_state_manager.update_service_health(health_results)
    
    # 构建结果
    all_healthy = all(details.get("status", False) for details in health_results.values())
    
    return {
        "all_healthy": all_healthy,
        "services": health_results,
        "timestamp": config_state_manager.state.last_updated
    }


@router.post("/validate-config")
async def validate_config():
    """验证系统配置"""
    validation_result = ConfigValidator.validate_all_configs()
    
    # 更新配置状态
    config_state_manager.update_validation_details(validation_result)
    
    return validation_result


@router.post("/bootstrap")
async def run_bootstrap(db: Session = Depends(get_db)):
    """运行完整的配置引导流程"""
    result = await ConfigBootstrap.run_bootstrap()
    return result


# ============ 配置类别管理 ============

@router.get("/config-categories", response_model=List[ConfigCategory])
def get_config_categories(db: Session = Depends(get_db)):
    """获取所有配置类别"""
    config_service = SystemConfigService(db)
    return config_service.get_categories()


@router.post("/config-categories", response_model=ConfigCategory)
def create_config_category(category: ConfigCategoryCreate, db: Session = Depends(get_db)):
    """创建配置类别"""
    config_service = SystemConfigService(db)
    
    # 检查名称是否已存在
    existing = config_service.get_category_by_name(category.name)
    if existing:
        raise HTTPException(status_code=400, detail="类别名称已存在")
    
    return config_service.create_category(
        name=category.name,
        description=category.description,
        order=category.order
    )


@router.get("/config-categories/{category_id}", response_model=ConfigCategory)
def get_config_category(category_id: str, db: Session = Depends(get_db)):
    """获取特定配置类别"""
    config_service = SystemConfigService(db)
    category = config_service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="配置类别不存在")
    return category


@router.put("/config-categories/{category_id}", response_model=ConfigCategory)
def update_config_category(
    category_id: str, 
    category: ConfigCategoryUpdate, 
    db: Session = Depends(get_db)
):
    """更新配置类别"""
    config_service = SystemConfigService(db)
    
    # 检查是否存在
    if not config_service.get_category(category_id):
        raise HTTPException(status_code=404, detail="配置类别不存在")
    
    # 检查名称是否重复
    if category.name:
        existing = config_service.get_category_by_name(category.name)
        if existing and existing.id != category_id:
            raise HTTPException(status_code=400, detail="类别名称已存在")
    
    updated = config_service.update_category(
        id=category_id,
        name=category.name,
        description=category.description,
        order=category.order
    )
    
    if not updated:
        raise HTTPException(status_code=400, detail="更新失败，可能是系统类别禁止修改")
    
    return updated


@router.delete("/config-categories/{category_id}")
def delete_config_category(category_id: str, db: Session = Depends(get_db)):
    """删除配置类别"""
    config_service = SystemConfigService(db)
    
    # 检查是否存在
    if not config_service.get_category(category_id):
        raise HTTPException(status_code=404, detail="配置类别不存在")
    
    success = config_service.delete_category(category_id)
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="删除失败，该类别可能是系统类别或包含配置项"
        )
    
    return {"success": True}


# ============ 配置项管理 ============

@router.get("/configs", response_model=List[Config])
def get_configs(
    category_id: Optional[str] = None,
    include_sensitive: bool = False,
    db: Session = Depends(get_db)
):
    """获取配置项列表"""
    config_service = SystemConfigService(db)
    return config_service.get_configs(category_id, include_sensitive)


@router.post("/configs", response_model=Config)
def create_config(config: ConfigCreate, db: Session = Depends(get_db)):
    """创建配置项"""
    config_service = SystemConfigService(db)
    
    # 检查键是否已存在
    existing = config_service.get_config_by_key(config.key)
    if existing:
        raise HTTPException(status_code=400, detail="配置键已存在")
    
    # 检查类别是否存在
    if not config_service.get_category(config.category_id):
        raise HTTPException(status_code=400, detail="配置类别不存在")
    
    return config_service.create_config(
        key=config.key,
        value=config.value,
        value_type=config.value_type,
        category_id=config.category_id,
        description=config.description,
        default_value=config.default_value,
        is_system=config.is_system,
        is_sensitive=config.is_sensitive,
        validation_rules=config.validation_rules,
        visible_level=config.visible_level
    )


@router.get("/configs/{config_id}", response_model=Config)
def get_config(config_id: str, db: Session = Depends(get_db)):
    """获取特定配置项"""
    config_service = SystemConfigService(db)
    config = config_service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")
    return config


@router.put("/configs/{config_id}", response_model=Config)
def update_config(
    config_id: str, 
    config: ConfigUpdate, 
    db: Session = Depends(get_db)
):
    """更新配置项"""
    config_service = SystemConfigService(db)
    
    # 检查是否存在
    if not config_service.get_config(config_id):
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    updated = config_service.update_config(
        id=config_id,
        value=config.value,
        description=config.description,
        is_sensitive=config.is_sensitive,
        validation_rules=config.validation_rules,
        visible_level=config.visible_level,
        change_source="user",
        change_notes=config.change_notes
    )
    
    if not updated:
        raise HTTPException(status_code=400, detail="更新失败")
    
    return updated


@router.delete("/configs/{config_id}")
def delete_config(config_id: str, db: Session = Depends(get_db)):
    """删除配置项"""
    config_service = SystemConfigService(db)
    
    # 检查是否存在
    if not config_service.get_config(config_id):
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    success = config_service.delete_config(config_id)
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="删除失败，该配置可能是系统配置"
        )
    
    return {"success": True}


@router.get("/configs/{config_id}/history", response_model=List[ConfigHistoryItem])
def get_config_history(config_id: str, db: Session = Depends(get_db)):
    """获取配置项历史记录"""
    config_service = SystemConfigService(db)
    
    # 检查是否存在
    if not config_service.get_config(config_id):
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    return config_service.get_config_history(config_id)


@router.get("/configs/by-key/{key}")
def get_config_by_key(key: str, db: Session = Depends(get_db)):
    """通过键获取配置值"""
    config_service = SystemConfigService(db)
    value = config_service.get_config_value(key)
    if value is None:
        raise HTTPException(status_code=404, detail="配置键不存在")
    return {"key": key, "value": value}


@router.get("/service-health-records", response_model=Dict[str, ServiceHealth])
def get_latest_health_records(db: Session = Depends(get_db)):
    """获取最新的服务健康记录"""
    config_service = SystemConfigService(db)
    return config_service.get_latest_health_records()


@router.post("/import-configs")
def import_configs(configs: Dict[str, Any], db: Session = Depends(get_db)):
    """从字典导入配置"""
    config_service = SystemConfigService(db)
    created, updated, errors = config_service.import_configs_from_dict(configs)
    return {
        "created": created,
        "updated": updated,
        "errors": errors
    }


@router.get("/export-configs")
def export_configs(include_sensitive: bool = False, db: Session = Depends(get_db)):
    """导出配置到字典"""
    config_service = SystemConfigService(db)
    return config_service.export_configs_to_dict(include_sensitive)
