"""
配置状态管理器 - 负责跟踪和管理配置状态
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.utils.config_manager import get_config_manager

logger = logging.getLogger(__name__)

class ConfigState(BaseModel):
    """配置状态模型"""
    loaded: bool = False
    validated: bool = False
    last_updated: Optional[str] = None
    missing_configs: List[str] = []
    service_health: Dict[str, bool] = {}
    override_sources: Dict[str, List[str]] = {"env": [], "file": []}
    validation_details: Dict[str, Any] = {}

class ConfigStateManager:
    """配置状态管理器，负责跟踪和管理配置状态"""
    
    def __init__(self):
        """初始化配置状态"""
        self.state = ConfigState()
        self._update_timestamp()
    
    def update_state(self, **kwargs):
        """更新配置状态"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        
        self._update_timestamp()
    
    def _update_timestamp(self):
        """更新时间戳"""
        self.state.last_updated = datetime.now().isoformat()
    
    def get_state(self) -> ConfigState:
        """获取当前配置状态"""
        return self.state
    
    def record_override(self, key: str, source: str, source_name: str):
        """记录配置覆盖来源"""
        if source == "env":
            if key not in self.state.override_sources["env"]:
                self.state.override_sources["env"].append(key)
        elif source == "file":
            source_key = f"{source_name}:{key}"
            if source_key not in self.state.override_sources["file"]:
                self.state.override_sources["file"].append(source_key)
    
    def update_validation_details(self, validation_result: Dict[str, Any]):
        """更新配置验证详情"""
        self.state.validation_details = validation_result
        self.state.validated = True
        
        # 提取缺失配置
        missing_configs = []
        for service, details in validation_result.get("configs", {}).items():
            if not details.get("valid", True):
                for msg in details.get("messages", []):
                    if "未配置" in msg or "默认值" in msg:
                        missing_configs.append(f"{service}: {msg}")
        
        self.state.missing_configs = missing_configs
    
    def update_service_health(self, health_results: Dict[str, Dict[str, Any]]):
        """更新服务健康状态"""
        service_health = {}
        for service, details in health_results.items():
            service_health[service] = details.get("status", False)
        
        self.state.service_health = service_health
    
    def export_state(self, filepath: str = "config_state.json"):
        """导出配置状态到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.state.dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"配置状态已导出到 {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出配置状态时出错: {str(e)}")
            return False
    
    def load_state(self, filepath: str = "config_state.json") -> bool:
        """从文件加载配置状态"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    self.state = ConfigState(**state_data)
                logger.info(f"配置状态已从 {filepath} 加载")
                return True
            return False
        except Exception as e:
            logger.error(f"加载配置状态时出错: {str(e)}")
            return False
    
    def refresh_config(self) -> bool:
        """刷新配置（清除缓存并重新加载）"""
        try:
            # 清除缓存的配置管理器
            get_config_manager.cache_clear()
            
            # 获取新的配置管理器实例（会重新加载配置）
            _ = get_config_manager()
            
            logger.info("配置已刷新")
            self.update_state(loaded=True)
            return True
        except Exception as e:
            logger.error(f"刷新配置时出错: {str(e)}")
            return False

# 创建全局配置状态管理器实例
config_state_manager = ConfigStateManager()
