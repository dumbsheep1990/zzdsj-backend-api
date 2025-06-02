"""
配置监控和告警系统
监控配置变更、异常值检测、告警通知
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ConfigAlert:
    """配置告警"""
    config_key: str
    alert_level: AlertLevel
    message: str
    timestamp: datetime
    old_value: Any = None
    new_value: Any = None
    rule_name: str = ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['alert_level'] = self.alert_level.value
        return data


class ConfigMonitor:
    """配置监控器"""
    
    def __init__(self, alert_callback: Optional[Callable[[ConfigAlert], None]] = None):
        """初始化监控器"""
        self.alert_callback = alert_callback
        self.monitoring_rules = {}
        self.config_history = []
        self.alerts = []
        self.lock = threading.RLock()
        
        # 默认监控规则
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """设置默认监控规则"""
        # 敏感配置变更告警
        self.add_rule("sensitive_config_change", self._check_sensitive_config)
        
        # 数据库连接配置告警
        self.add_rule("database_config_check", self._check_database_config)
        
        # API密钥格式检查
        self.add_rule("api_key_format_check", self._check_api_key_format)
        
        # 端口范围检查
        self.add_rule("port_range_check", self._check_port_range)
    
    def add_rule(self, rule_name: str, rule_func: Callable):
        """添加监控规则"""
        self.monitoring_rules[rule_name] = rule_func
        logger.info(f"添加监控规则: {rule_name}")
    
    def monitor_config_change(self, config_key: str, old_value: Any, new_value: Any):
        """监控配置变更"""
        with self.lock:
            # 记录变更历史
            change_record = {
                'config_key': config_key,
                'old_value': old_value,
                'new_value': new_value,
                'timestamp': datetime.now(),
                'change_type': self._get_change_type(old_value, new_value)
            }
            self.config_history.append(change_record)
            
            # 应用监控规则
            for rule_name, rule_func in self.monitoring_rules.items():
                try:
                    alert = rule_func(config_key, old_value, new_value)
                    if alert:
                        alert.rule_name = rule_name
                        self._handle_alert(alert)
                except Exception as e:
                    logger.error(f"监控规则 {rule_name} 执行失败: {str(e)}")
    
    def _get_change_type(self, old_value: Any, new_value: Any) -> str:
        """获取变更类型"""
        if old_value is None and new_value is not None:
            return "added"
        elif old_value is not None and new_value is None:
            return "removed"
        else:
            return "modified"
    
    def _handle_alert(self, alert: ConfigAlert):
        """处理告警"""
        with self.lock:
            self.alerts.append(alert)
            
            # 调用告警回调
            if self.alert_callback:
                try:
                    self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"告警回调执行失败: {str(e)}")
            
            # 记录告警日志
            level_map = {
                AlertLevel.INFO: logger.info,
                AlertLevel.WARNING: logger.warning,
                AlertLevel.ERROR: logger.error,
                AlertLevel.CRITICAL: logger.critical
            }
            log_func = level_map.get(alert.alert_level, logger.info)
            log_func(f"配置告警: {alert.config_key} - {alert.message}")
    
    def _check_sensitive_config(self, config_key: str, old_value: Any, new_value: Any) -> Optional[ConfigAlert]:
        """检查敏感配置变更"""
        sensitive_keywords = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']
        
        if any(keyword in config_key.upper() for keyword in sensitive_keywords):
            return ConfigAlert(
                config_key=config_key,
                alert_level=AlertLevel.WARNING,
                message="敏感配置发生变更",
                timestamp=datetime.now(),
                old_value="***" if old_value else None,
                new_value="***" if new_value else None
            )
        return None
    
    def _check_database_config(self, config_key: str, old_value: Any, new_value: Any) -> Optional[ConfigAlert]:
        """检查数据库配置"""
        if 'DATABASE' in config_key.upper() and new_value:
            # 检查是否使用默认密码
            if isinstance(new_value, str) and 'password=postgres' in new_value.lower():
                return ConfigAlert(
                    config_key=config_key,
                    alert_level=AlertLevel.ERROR,
                    message="检测到使用默认数据库密码，存在安全风险",
                    timestamp=datetime.now(),
                    new_value="***"
                )
        return None
    
    def _check_api_key_format(self, config_key: str, old_value: Any, new_value: Any) -> Optional[ConfigAlert]:
        """检查API密钥格式"""
        if 'API_KEY' in config_key.upper() and new_value:
            if isinstance(new_value, str) and len(new_value) < 20:
                return ConfigAlert(
                    config_key=config_key,
                    alert_level=AlertLevel.WARNING,
                    message="API密钥长度过短，可能无效",
                    timestamp=datetime.now()
                )
        return None
    
    def _check_port_range(self, config_key: str, old_value: Any, new_value: Any) -> Optional[ConfigAlert]:
        """检查端口范围"""
        if 'PORT' in config_key.upper() and new_value:
            try:
                port = int(new_value)
                if not (1 <= port <= 65535):
                    return ConfigAlert(
                        config_key=config_key,
                        alert_level=AlertLevel.ERROR,
                        message=f"端口号 {port} 超出有效范围 (1-65535)",
                        timestamp=datetime.now(),
                        new_value=new_value
                    )
                elif port < 1024 and port != 80 and port != 443:
                    return ConfigAlert(
                        config_key=config_key,
                        alert_level=AlertLevel.WARNING,
                        message=f"使用系统保留端口 {port}，可能需要管理员权限",
                        timestamp=datetime.now(),
                        new_value=new_value
                    )
            except (ValueError, TypeError):
                return ConfigAlert(
                    config_key=config_key,
                    alert_level=AlertLevel.ERROR,
                    message="端口配置格式无效",
                    timestamp=datetime.now(),
                    new_value=new_value
                )
        return None
    
    def get_recent_alerts(self, hours: int = 24) -> List[ConfigAlert]:
        """获取最近的告警"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        with self.lock:
            return [alert for alert in self.alerts if alert.timestamp > cutoff_time]
    
    def get_config_history(self, config_key: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """获取配置变更历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        with self.lock:
            history = [record for record in self.config_history if record['timestamp'] > cutoff_time]
            if config_key:
                history = [record for record in history if record['config_key'] == config_key]
            return history
    
    def export_alerts_to_json(self, file_path: str):
        """导出告警到JSON文件"""
        with self.lock:
            alerts_data = [alert.to_dict() for alert in self.alerts]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(alerts_data, f, ensure_ascii=False, indent=2)


# 全局配置监控器实例
_global_monitor: Optional[ConfigMonitor] = None


def init_config_monitor(alert_callback: Optional[Callable[[ConfigAlert], None]] = None) -> ConfigMonitor:
    """初始化全局配置监控器"""
    global _global_monitor
    _global_monitor = ConfigMonitor(alert_callback)
    return _global_monitor


def monitor_config_change(config_key: str, old_value: Any, new_value: Any):
    """监控配置变更（全局函数）"""
    if _global_monitor:
        _global_monitor.monitor_config_change(config_key, old_value, new_value)


def get_recent_alerts(hours: int = 24) -> List[ConfigAlert]:
    """获取最近告警（全局函数）"""
    if _global_monitor:
        return _global_monitor.get_recent_alerts(hours)
    return []


def default_alert_handler(alert: ConfigAlert):
    """默认告警处理器"""
    logger.warning(f"[CONFIG ALERT] {alert.config_key}: {alert.message}")
