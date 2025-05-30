"""
系统配置API - 提供配置管理和系统自检API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.utils.database import get_db
from app.services.async_system_config_service import AsyncSystemConfigService
from app.utils.config_validator import ConfigValidator
from app.utils.service_health import ServiceHealthChecker
from app.utils.config_state import config_state_manager
from app.utils.config_bootstrap import ConfigBootstrap
from app.api.frontend.dependencies import ResponseFormatter, get_current_user, require_permission
import asyncio

router = APIRouter(prefix="/api/frontend/system/config", tags=["系统管理"])

# ============ 输入输出模型 ============

class ConfigCategoryBase(BaseModel):
    """配置类别基础模型"""
    name: str
    description: Optional[str] = None
    order: Optional[int] = None


class ConfigCategoryCreate(ConfigCategoryBase):
    """创建配置类别请求模型"""
    pass


class ConfigCategoryUpdate(BaseModel):
    """更新配置类别请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class ConfigCategory(ConfigCategoryBase):
    """配置类别响应模型"""
    id: str
    is_system: bool

    class Config:
        orm_mode = True


class ConfigBase(BaseModel):
    """配置项基础模型"""
    key: str
    value: Any
    category_id: str
    description: Optional[str] = None
    is_sensitive: Optional[bool] = False
    validation_rules: Optional[Dict[str, Any]] = None
    visible_level: Optional[str] = "all"


class ConfigCreate(ConfigBase):
    """创建配置项请求模型"""
    value_type: str
    default_value: Optional[Any] = None
    is_system: Optional[bool] = False


class ConfigUpdate(BaseModel):
    """更新配置项请求模型"""
    value: Optional[Any] = None
    description: Optional[str] = None
    is_sensitive: Optional[bool] = None
    validation_rules: Optional[Dict[str, Any]] = None
    visible_level: Optional[str] = None
    change_notes: Optional[str] = None


class Config(ConfigBase):
    """配置项响应模型"""
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
    """配置历史记录响应模型"""
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
    """服务健康状态响应模型"""
    service_name: str
    status: bool
    check_time: str
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class ConfigStateResponse(BaseModel):
    """配置状态响应模型"""
    loaded: bool
    validated: bool
    last_updated: Optional[str] = None
    missing_configs: List[str] = []
    service_health: Dict[str, bool] = {}
    override_sources: Dict[str, List[str]] = {"env": [], "file": []}
    validation_details: Dict[str, Any] = {}


# ============ API端点 ============

@router.get("/status", response_model=ConfigStateResponse)
async def get_config_status():
    """获取系统配置状态"""
    status = config_state_manager.get_config_state()
    return ResponseFormatter.format_success(status)


@router.post("/refresh", response_model=ConfigStateResponse)
async def refresh_config():
    """刷新系统配置"""
    result = await AsyncSystemConfigService.reload_configs()
    return ResponseFormatter.format_success(result)


@router.get("/health", response_model=List[ServiceHealth])
async def health_check(
    save_to_db: bool = False, 
    db: Session = Depends(get_db)
):
    """
    检查系统健康状态
    
    - **save_to_db**: 是否将健康检查结果保存到数据库
    """
    checker = ServiceHealthChecker(db)
    services = await checker.check_all_services()
    
    if save_to_db:
        for service in services:
            await checker.save_health_record(service)
    
    return ResponseFormatter.format_success(services)


@router.get("/validate", response_model=Dict[str, Any])
async def validate_config():
    """验证当前系统配置是否正确完整"""
    validator = ConfigValidator()
    result = await validator.validate_all()
    
    # 更新配置状态
    config_state_manager.update_validation_state(result["valid"], result)
    
    return ResponseFormatter.format_success(result)


@router.post("/bootstrap")
async def run_bootstrap(db: Session = Depends(get_db)):
    """启动配置初始化流程"""
    bootstrap = ConfigBootstrap(db)
    result = await bootstrap.run()
    return ResponseFormatter.format_success({"status": "completed", "details": result})


# ============ 配置类别管理 ============

@router.get("/categories", response_model=List[ConfigCategory])
async def get_config_categories(db: Session = Depends(get_db)):
    """获取所有配置类别"""
    service = AsyncSystemConfigService(db)
    categories = await service.get_all_categories()
    return ResponseFormatter.format_success(categories)


@router.post("/categories", response_model=ConfigCategory, status_code=status.HTTP_201_CREATED)
async def create_config_category(
    category: ConfigCategoryCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:write"))
):
    """
    创建配置类别
    
    需要系统配置写入权限
    """
    service = AsyncSystemConfigService(db)
    try:
        new_category = await service.create_category(category.dict())
        return ResponseFormatter.format_success(new_category)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法创建配置类别: {str(e)}"
        )


@router.get("/categories/{category_id}", response_model=ConfigCategory)
async def get_config_category(
    category_id: str, 
    db: Session = Depends(get_db)
):
    """获取特定配置类别"""
    service = AsyncSystemConfigService(db)
    category = await service.get_category(category_id)
    return ResponseFormatter.format_success(category)


@router.put("/categories/{category_id}", response_model=ConfigCategory)
async def update_config_category(
    category_id: str, 
    category: ConfigCategoryUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:write"))
):
    """
    更新配置类别
    
    需要系统配置写入权限
    """
    service = AsyncSystemConfigService(db)
    
    # 检查类别是否存在
    existing = await service.get_category(category_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置类别 {category_id} 不存在"
        )
        
    # 检查是否为系统类别
    if existing.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统配置类别不允许修改"
        )
    
    try:
        updated = await service.update_category(category_id, category.dict(exclude_unset=True))
        return ResponseFormatter.format_success(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新配置类别失败: {str(e)}"
        )


@router.delete("/categories/{category_id}")
async def delete_config_category(
    category_id: str, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:write"))
):
    """
    删除配置类别
    
    需要系统配置写入权限
    """
    service = AsyncSystemConfigService(db)
    
    # 检查类别是否存在
    existing = await service.get_category(category_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置类别 {category_id} 不存在"
        )
        
    # 检查是否为系统类别
    if existing.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统配置类别不允许删除"
        )
    
    await service.delete_category(category_id)
    return ResponseFormatter.format_success({"status": "success", "message": "配置类别已删除"})


# ============ 配置项管理 ============

@router.get("/items", response_model=List[Config])
async def get_configs(
    category_id: Optional[str] = None,
    include_sensitive: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取配置项列表
    
    - **category_id**: 可选的类别ID过滤
    - **include_sensitive**: 是否包含敏感配置项
    """
    service = AsyncSystemConfigService(db)
    configs = await service.get_all_configs(category_id, include_sensitive)
    return ResponseFormatter.format_success(configs)


@router.post("/items", response_model=Config, status_code=status.HTTP_201_CREATED)
async def create_config(
    config: ConfigCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:write"))
):
    """
    创建配置项
    
    需要系统配置写入权限
    """
    service = AsyncSystemConfigService(db)
    
    # 检查键是否已存在
    existing = await service.get_config_by_key(config.key)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置键 {config.key} 已存在"
        )
    
    # 检查类别是否存在
    category = await service.get_category(config.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置类别 {config.category_id} 不存在"
        )
    
    try:
        new_config = await service.create_config(config.dict())
        return ResponseFormatter.format_success(new_config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建配置项失败: {str(e)}"
        )


@router.get("/items/{config_id}", response_model=Config)
async def get_config(
    config_id: str, 
    db: Session = Depends(get_db)
):
    """获取特定配置项"""
    service = AsyncSystemConfigService(db)
    config = await service.get_config(config_id)
    return ResponseFormatter.format_success(config)


@router.put("/items/{config_id}", response_model=Config)
async def update_config(
    config_id: str, 
    config: ConfigUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:write"))
):
    """
    更新配置项
    
    需要系统配置写入权限
    """
    service = AsyncSystemConfigService(db)
    
    # 检查配置是否存在
    existing = await service.get_config(config_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置项 {config_id} 不存在"
        )
        
    # 检查是否为系统配置
    if existing.is_system and (config.validation_rules is not None or config.is_sensitive is not None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统配置项的验证规则和敏感性不允许修改"
        )
    
    # 准备更新数据
    update_data = config.dict(exclude_unset=True)
    
    # 添加变更来源信息
    if "change_notes" in update_data:
        update_data["change_source"] = "manual"
        update_data["changed_by"] = current_user.username if current_user else "system"
    
    try:
        updated = await service.update_config(config_id, update_data)
        return ResponseFormatter.format_success(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新配置项失败: {str(e)}"
        )


@router.delete("/items/{config_id}")
async def delete_config(
    config_id: str, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:write"))
):
    """
    删除配置项
    
    需要系统配置写入权限
    """
    service = AsyncSystemConfigService(db)
    
    # 检查配置是否存在
    existing = await service.get_config(config_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置项 {config_id} 不存在"
        )
        
    # 检查是否为系统配置
    if existing.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统配置项不允许删除"
        )
    
    await service.delete_config(config_id)
    return ResponseFormatter.format_success({"status": "success", "message": "配置项已删除"})


@router.get("/items/{config_id}/history", response_model=List[ConfigHistoryItem])
async def get_config_history(
    config_id: str, 
    db: Session = Depends(get_db)
):
    """获取配置项修改历史"""
    service = AsyncSystemConfigService(db)
    history = await service.get_config_history(config_id)
    return ResponseFormatter.format_success(history)


@router.get("/by-key/{key}", response_model=Config)
async def get_config_by_key(
    key: str, 
    db: Session = Depends(get_db)
):
    """通过键获取配置值"""
    service = AsyncSystemConfigService(db)
    config = await service.get_config_by_key(key)
    return ResponseFormatter.format_success(config)


@router.get("/health-records", response_model=List[ServiceHealth])
async def get_latest_health_records(db: Session = Depends(get_db)):
    """获取最新的服务健康状态记录"""
    checker = ServiceHealthChecker(db)
    records = await checker.get_latest_records()
    return ResponseFormatter.format_success(records)


@router.post("/import")
async def import_configs(
    configs: Dict[str, Any], 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:admin"))
):
    """
    导入配置数据
    
    需要系统管理员权限
    """
    service = AsyncSystemConfigService(db)
    try:
        result = await service.import_configs(configs)
        return ResponseFormatter.format_success({
            "status": "success",
            "imported": result
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"导入配置失败: {str(e)}"
        )


@router.get("/export")
async def export_configs(
    include_sensitive: bool = False, 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("system:config:admin"))
):
    """
    导出全部配置数据
    
    需要系统管理员权限
    """
    service = AsyncSystemConfigService(db)
    configs = await service.export_configs(include_sensitive)
    return ResponseFormatter.format_success(configs)
