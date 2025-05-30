"""
系统配置API - 提供配置管理和系统自检API
[迁移桥接] - 该文件已迁移至 app/api/frontend/system/config.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.system.config import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/system_config.py，该文件已迁移至app/api/frontend/system/config.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
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


@router.post("/validate")
async def validate_config():
    """验证当前系统配置是否正确完整"""
    validator = ConfigValidator()
    result = await validator.validate_all()
    
    # 更新配置状态
    config_state_manager.set_validation_status(result["is_valid"], result)
    
    return result


@router.post("/bootstrap")
async def run_bootstrap(db: Session = Depends(get_db)):
    """启动配置初始化流程"""
    bootstrap = ConfigBootstrap(db)
    result = await bootstrap.run()
    return {"success": result, "message": "Bootstrap process completed"}


# ============ 配置类别管理 ============

@router.get("/config-categories", response_model=List[ConfigCategory])
async def get_config_categories(db: Session = Depends(get_db)):
    """获取所有配置类别"""
    config_service = AsyncSystemConfigService(db)
    return await config_service.get_categories()


@router.post("/config-categories", response_model=ConfigCategory)
async def create_config_category(category: ConfigCategoryCreate, db: Session = Depends(get_db)):
    """创建配置类别"""
    config_service = AsyncSystemConfigService(db)
    
    # 检查名称是否已存在
    existing = await config_service.get_category_by_name(category.name)
    if existing:
        raise HTTPException(status_code=400, detail="类别名称已存在")
    
    return await config_service.create_category(
        name=category.name,
        description=category.description,
        order=category.order
    )


@router.get("/config-categories/{category_id}", response_model=ConfigCategory)
async def get_config_category(category_id: str, db: Session = Depends(get_db)):
    """获取特定配置类别"""
    config_service = AsyncSystemConfigService(db)
    category = await config_service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="配置类别不存在")
    return category


@router.put("/config-categories/{category_id}", response_model=ConfigCategory)
async def update_config_category(
    category_id: str, 
    category: ConfigCategoryUpdate, 
    db: Session = Depends(get_db)
):
    """更新配置类别"""
    config_service = AsyncSystemConfigService(db)
    
    # 检查是否存在
    if not await config_service.get_category(category_id):
        raise HTTPException(status_code=404, detail="配置类别不存在")
    
    # 检查名称是否重复
    if category.name:
        existing = await config_service.get_category_by_name(category.name)
        if existing and existing.id != category_id:
            raise HTTPException(status_code=400, detail="类别名称已存在")
    
    updated = await config_service.update_category(
        id=category_id,
        name=category.name,
        description=category.description,
        order=category.order
    )
    
    if not updated:
        raise HTTPException(status_code=400, detail="更新失败，可能是系统类别禁止修改")
    
    return updated


@router.delete("/config-categories/{category_id}")
async def delete_config_category(category_id: str, db: Session = Depends(get_db)):
    """删除配置类别"""
    config_service = AsyncSystemConfigService(db)
    
    # 检查是否存在
    if not await config_service.get_category(category_id):
        raise HTTPException(status_code=404, detail="配置类别不存在")
    
    success = await config_service.delete_category(category_id)
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="删除失败，该类别可能是系统类别或存在关联配置项"
        )
    
    return {"success": True}


# ============ 配置项管理 ============

@router.get("/configs", response_model=List[Config])
async def get_configs(
    category_id: Optional[str] = None,
    include_sensitive: bool = False,
    db: Session = Depends(get_db)
):
    """获取配置项列表"""
    config_service = AsyncSystemConfigService(db)
    return await config_service.get_configs(category_id, include_sensitive)


@router.post("/configs", response_model=Config)
async def create_config(config: ConfigCreate, db: Session = Depends(get_db)):
    """创建配置项"""
    config_service = AsyncSystemConfigService(db)
    
    # 检查键是否已存在
    existing = await config_service.get_config_by_key(config.key)
    if existing:
        raise HTTPException(status_code=400, detail="配置键已存在")
    
    # 检查类别是否存在
    if not await config_service.get_category(config.category_id):
        raise HTTPException(status_code=400, detail="配置类别不存在")
    
    return await config_service.create_config(
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
async def get_config(config_id: str, db: Session = Depends(get_db)):
    """获取特定配置项"""
    config_service = AsyncSystemConfigService(db)
    config = await config_service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")
    return config


@router.put("/configs/{config_id}", response_model=Config)
async def update_config(
    config_id: str, 
    config: ConfigUpdate, 
    db: Session = Depends(get_db)
):
    """更新配置项"""
    config_service = AsyncSystemConfigService(db)
    
    # 检查配置项是否存在
    existing = await config_service.get_config(config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    # 验证新值
    validator = ConfigValidator()
    if config.value is not None:
        valid, error = validator.validate(config.value, existing.value_type, config.validation_rules or existing.validation_rules)
        if not valid:
            raise HTTPException(status_code=400, detail=f"参数验证失败: {error}")
    
    # 构建更新数据
    update_data = {}
    if config.value is not None:
        update_data['value'] = config.value
    if config.description is not None:
        update_data['description'] = config.description
    if config.is_sensitive is not None:
        update_data['is_sensitive'] = config.is_sensitive
    if config.validation_rules is not None:
        update_data['validation_rules'] = config.validation_rules
    if config.visible_level is not None:
        update_data['visible_level'] = config.visible_level
        
    return await config_service.update_config(config_id, update_data, config.change_notes)


@router.delete("/configs/{config_id}")
async def delete_config(config_id: str, db: Session = Depends(get_db)):
    """删除配置项"""
    config_service = AsyncSystemConfigService(db)
    
    # 检查配置项是否存在
    existing = await config_service.get_config(config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    # 系统配置不允许删除
    if existing.is_system:
        raise HTTPException(status_code=403, detail="系统配置项不允许删除")
    
    await config_service.delete_config(config_id)
    
    return {"status": "success", "message": "配置项已删除"}


@router.get("/configs/{config_id}/history", response_model=List[ConfigHistoryItem])
async def get_config_history(config_id: str, db: Session = Depends(get_db)):
    """获取配置项修改历史"""
    config_service = AsyncSystemConfigService(db)
    
    # 检查配置项是否存在
    existing = await config_service.get_config(config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    return await config_service.get_config_history(config_id)


@router.get("/configs/by-key/{key}")
async def get_config_by_key(key: str, db: Session = Depends(get_db)):
    """通过键获取配置值"""
    config_service = AsyncSystemConfigService(db)
    value = await config_service.get_config_value(key)
    if value is None:
        raise HTTPException(status_code=404, detail="配置键不存在")
    return {"key": key, "value": value}


@router.get("/health/latest", response_model=Dict[str, ServiceHealth])
async def get_latest_health_records(db: Session = Depends(get_db)):
    """获取最新的服务健康状态记录"""
    config_service = AsyncSystemConfigService(db)
    return await config_service.get_latest_health_records()


@router.post("/import", status_code=201)
async def import_configs(configs: Dict[str, Any], db: Session = Depends(get_db)):
    """导入配置数据"""
    config_service = AsyncSystemConfigService(db)
    result = await config_service.import_configs(configs)
    return {
        "success": True,
        "imported_count": result["imported"],
        "updated_count": result["updated"],
        "failed_count": result["failed"]
    }


@router.get("/export")
async def export_configs(include_sensitive: bool = False, db: Session = Depends(get_db)):
    """导出全部配置数据"""
    config_service = AsyncSystemConfigService(db)
    return await config_service.export_configs(include_sensitive)
