"""
配置热重载系统
支持运行时动态更新配置而无需重启服务
"""

import os
import json
import threading
import time
from typing import Dict, Any, Callable, Optional
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

logger = logging.getLogger(__name__)


class ConfigHotReloader:
    """配置热重载器"""
    
    def __init__(self, config_file_path: str, update_callback: Optional[Callable] = None):
        """初始化热重载器"""
        self.config_file_path = Path(config_file_path)
        self.update_callback = update_callback
        self.observer = Observer()
        self.current_config = {}
        self.lock = threading.RLock()
        
        # 加载初始配置
        self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with self.lock:
                if self.config_file_path.suffix == '.json':
                    with open(self.config_file_path, 'r', encoding='utf-8') as f:
                        self.current_config = json.load(f)
                elif self.config_file_path.suffix == '.env':
                    self.current_config = self._parse_env_file()
                
                logger.info(f"配置已加载: {len(self.current_config)} 项")
                return self.current_config.copy()
                
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            return {}
    
    def _parse_env_file(self) -> Dict[str, str]:
        """解析.env文件"""
        config = {}
        with open(self.config_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        return config
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        with self.lock:
            return self.current_config.get(key, default)
    
    def start_watching(self):
        """开始监控配置文件变化"""
        event_handler = ConfigFileHandler(self)
        self.observer.schedule(
            event_handler, 
            str(self.config_file_path.parent), 
            recursive=False
        )
        self.observer.start()
        logger.info(f"开始监控配置文件: {self.config_file_path}")
    
    def stop_watching(self):
        """停止监控"""
        self.observer.stop()
        self.observer.join()
        logger.info("配置文件监控已停止")
    
    def reload_config(self):
        """重新加载配置"""
        old_config = self.current_config.copy()
        new_config = self.load_config()
        
        # 检查变化
        changes = self._detect_changes(old_config, new_config)
        if changes:
            logger.info(f"检测到配置变化: {changes}")
            
            # 调用更新回调
            if self.update_callback:
                try:
                    self.update_callback(changes, new_config)
                except Exception as e:
                    logger.error(f"配置更新回调失败: {str(e)}")
    
    def _detect_changes(self, old_config: Dict, new_config: Dict) -> Dict[str, Any]:
        """检测配置变化"""
        changes = {
            'added': {},
            'modified': {},
            'removed': {}
        }
        
        # 检查新增和修改
        for key, value in new_config.items():
            if key not in old_config:
                changes['added'][key] = value
            elif old_config[key] != value:
                changes['modified'][key] = {'old': old_config[key], 'new': value}
        
        # 检查删除
        for key in old_config:
            if key not in new_config:
                changes['removed'][key] = old_config[key]
        
        return changes


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变化处理器"""
    
    def __init__(self, reloader: ConfigHotReloader):
        self.reloader = reloader
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path == str(self.reloader.config_file_path):
            # 延迟一小段时间，避免文件写入过程中的重复触发
            time.sleep(0.1)
            self.reloader.reload_config()


# 全局配置热重载器实例
_global_reloader: Optional[ConfigHotReloader] = None


def init_config_hot_reload(config_file_path: str, update_callback: Optional[Callable] = None):
    """初始化全局配置热重载器"""
    global _global_reloader
    _global_reloader = ConfigHotReloader(config_file_path, update_callback)
    _global_reloader.start_watching()
    return _global_reloader


def get_hot_config(key: str, default: Any = None) -> Any:
    """获取热重载配置值"""
    if _global_reloader:
        return _global_reloader.get_config(key, default)
    return default


def stop_hot_reload():
    """停止热重载"""
    global _global_reloader
    if _global_reloader:
        _global_reloader.stop_watching()
        _global_reloader = None
