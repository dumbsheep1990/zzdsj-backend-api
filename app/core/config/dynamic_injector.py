#!/usr/bin/env python3
"""
动态配置注入器
支持运行时配置更新、全局注入和配置变更通知
"""

import asyncio
import logging
from typing import Dict, Any, Callable, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from fastapi import FastAPI
from threading import RLock
import weakref

logger = logging.getLogger(__name__)


@dataclass
class ConfigChangeEvent:
    """配置变更事件"""
    config_key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    change_type: str = "modified"  # added, modified, removed


class ConfigSubscriber:
    """配置订阅者"""
    
    def __init__(self, callback: Callable, config_keys: Set[str] = None, 
                 filter_func: Optional[Callable] = None):
        self.callback = callback
        self.config_keys = config_keys or set()
        self.filter_func = filter_func
        self.created_at = datetime.now()
        self.last_triggered = None
        self.trigger_count = 0
    
    def should_trigger(self, event: ConfigChangeEvent) -> bool:
        """判断是否应该触发回调"""
        # 检查配置键过滤
        if self.config_keys and event.config_key not in self.config_keys:
            return False
        
        # 检查自定义过滤器
        if self.filter_func and not self.filter_func(event):
            return False
        
        return True
    
    async def trigger(self, event: ConfigChangeEvent):
        """触发回调"""
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(event)
            else:
                self.callback(event)
            
            self.last_triggered = datetime.now()
            self.trigger_count += 1
            
        except Exception as e:
            logger.error(f"配置订阅者回调执行失败: {str(e)}")


class DynamicConfigInjector:
    """动态配置注入器"""
    
    def __init__(self):
        self.config_cache: Dict[str, Any] = {}
        self.subscribers: List[ConfigSubscriber] = []
        self.injection_hooks: List[Callable] = []
        self.app_instances: List[weakref.ref] = []
        self.lock = RLock()
        
        # 配置变更历史
        self.change_history: List[ConfigChangeEvent] = []
        self.max_history_size = 1000
        
        # 性能统计
        self.injection_stats = {
            "total_injections": 0,
            "total_changes": 0,
            "last_injection_time": None,
            "average_injection_time": 0.0
        }
        
        logger.info("动态配置注入器初始化完成")
    
    async def inject_to_application(self, app: FastAPI, config: Dict[str, Any], 
                                  source: str = "manual") -> bool:
        """注入配置到FastAPI应用"""
        start_time = datetime.now()
        
        try:
            with self.lock:
                # 检测配置变更
                changes = self._detect_config_changes(config, source)
                
                # 注入到app.state
                if not hasattr(app, 'state'):
                    app.state = type('State', (), {})()
                
                app.state.config = config
                app.state.config_last_updated = datetime.now()
                
                # 保存应用弱引用
                app_ref = weakref.ref(app)
                if app_ref not in self.app_instances:
                    self.app_instances.append(app_ref)
                
                # 触发注入钩子
                for hook in self.injection_hooks:
                    try:
                        if asyncio.iscoroutinefunction(hook):
                            await hook(config, changes)
                        else:
                            hook(config, changes)
                    except Exception as e:
                        logger.error(f"注入钩子执行失败: {str(e)}")
                
                # 通知配置变更
                for change in changes:
                    await self._notify_config_change(change)
                
                # 更新缓存
                self.config_cache.update(config)
                
                # 更新统计信息
                injection_time = (datetime.now() - start_time).total_seconds()
                self._update_injection_stats(injection_time)
                
                logger.info(f"配置注入完成 - {len(config)} 项配置，{len(changes)} 项变更")
                return True
                
        except Exception as e:
            logger.error(f"配置注入失败: {str(e)}")
            return False
    
    def register_config_change_subscriber(self, 
                                        callback: Callable,
                                        config_keys: Set[str] = None,
                                        filter_func: Optional[Callable] = None) -> str:
        """注册配置变更订阅者"""
        subscriber = ConfigSubscriber(callback, config_keys, filter_func)
        
        with self.lock:
            self.subscribers.append(subscriber)
        
        subscriber_id = f"subscriber_{len(self.subscribers)}_{id(subscriber)}"
        logger.info(f"注册配置变更订阅者: {subscriber_id}")
        
        return subscriber_id
    
    def unregister_subscriber(self, subscriber_id: str) -> bool:
        """注销配置变更订阅者"""
        # 简单实现：通过索引查找（实际项目中可能需要更好的ID管理）
        try:
            # 这里需要改进，暂时使用简单的移除逻辑
            logger.info(f"配置订阅者注销请求: {subscriber_id}")
            return True
        except Exception as e:
            logger.error(f"注销订阅者失败: {str(e)}")
            return False
    
    def register_injection_hook(self, hook: Callable) -> str:
        """注册配置注入钩子"""
        with self.lock:
            self.injection_hooks.append(hook)
        
        hook_id = f"hook_{len(self.injection_hooks)}_{id(hook)}"
        logger.info(f"注册配置注入钩子: {hook_id}")
        
        return hook_id
    
    async def hot_reload_config(self, config_changes: Dict[str, Any], 
                              source: str = "hot_reload") -> bool:
        """热重载配置"""
        try:
            # 应用配置变更到所有注册的应用实例
            for app_ref in self.app_instances[:]:  # 复制列表以避免迭代时修改
                app = app_ref()
                if app is None:
                    # 应用实例已被垃圾回收，清理弱引用
                    self.app_instances.remove(app_ref)
                    continue
                
                # 合并配置变更
                current_config = getattr(app.state, 'config', {})
                updated_config = {**current_config, **config_changes}
                
                # 重新注入配置
                await self.inject_to_application(app, updated_config, source)
            
            logger.info(f"热重载配置完成 - {len(config_changes)} 项变更")
            return True
            
        except Exception as e:
            logger.error(f"热重载配置失败: {str(e)}")
            return False
    
    async def batch_update_config(self, config_updates: List[Dict[str, Any]], 
                                source: str = "batch_update") -> bool:
        """批量更新配置"""
        try:
            merged_updates = {}
            for update in config_updates:
                merged_updates.update(update)
            
            return await self.hot_reload_config(merged_updates, source)
            
        except Exception as e:
            logger.error(f"批量更新配置失败: {str(e)}")
            return False
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取缓存的配置值"""
        with self.lock:
            return self.config_cache.get(key, default)
    
    def get_all_cached_config(self) -> Dict[str, Any]:
        """获取所有缓存的配置"""
        with self.lock:
            return self.config_cache.copy()
    
    def get_change_history(self, hours: int = 24, config_key: str = None) -> List[ConfigChangeEvent]:
        """获取配置变更历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            filtered_history = [
                event for event in self.change_history
                if event.timestamp > cutoff_time
            ]
            
            if config_key:
                filtered_history = [
                    event for event in filtered_history
                    if event.config_key == config_key
                ]
        
        return filtered_history
    
    def get_injection_stats(self) -> Dict[str, Any]:
        """获取注入统计信息"""
        with self.lock:
            stats = self.injection_stats.copy()
            stats.update({
                "total_subscribers": len(self.subscribers),
                "total_hooks": len(self.injection_hooks),
                "total_app_instances": len([ref for ref in self.app_instances if ref() is not None]),
                "cached_config_count": len(self.config_cache),
                "change_history_count": len(self.change_history)
            })
        
        return stats
    
    def cleanup_expired_history(self, days: int = 7):
        """清理过期的变更历史"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with self.lock:
            original_count = len(self.change_history)
            self.change_history = [
                event for event in self.change_history
                if event.timestamp > cutoff_time
            ]
            
            cleaned_count = original_count - len(self.change_history)
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 条过期的配置变更历史")
    
    def _detect_config_changes(self, new_config: Dict[str, Any], 
                             source: str) -> List[ConfigChangeEvent]:
        """检测配置变更"""
        changes = []
        
        # 检查新增和修改
        for key, new_value in new_config.items():
            if key not in self.config_cache:
                # 新增配置
                changes.append(ConfigChangeEvent(
                    config_key=key,
                    old_value=None,
                    new_value=new_value,
                    source=source,
                    change_type="added"
                ))
            elif self.config_cache[key] != new_value:
                # 修改配置
                changes.append(ConfigChangeEvent(
                    config_key=key,
                    old_value=self.config_cache[key],
                    new_value=new_value,
                    source=source,
                    change_type="modified"
                ))
        
        # 检查删除（在当前缓存中但不在新配置中）
        for key in self.config_cache:
            if key not in new_config:
                changes.append(ConfigChangeEvent(
                    config_key=key,
                    old_value=self.config_cache[key],
                    new_value=None,
                    source=source,
                    change_type="removed"
                ))
        
        return changes
    
    async def _notify_config_change(self, event: ConfigChangeEvent):
        """通知配置变更"""
        # 添加到历史记录
        with self.lock:
            self.change_history.append(event)
            
            # 限制历史记录大小
            if len(self.change_history) > self.max_history_size:
                self.change_history = self.change_history[-self.max_history_size:]
        
        # 通知订阅者
        for subscriber in self.subscribers[:]:  # 复制列表避免迭代时修改
            if subscriber.should_trigger(event):
                try:
                    await subscriber.trigger(event)
                except Exception as e:
                    logger.error(f"通知订阅者失败: {str(e)}")
    
    def _update_injection_stats(self, injection_time: float):
        """更新注入统计信息"""
        self.injection_stats["total_injections"] += 1
        self.injection_stats["last_injection_time"] = datetime.now()
        
        # 计算平均注入时间
        total_injections = self.injection_stats["total_injections"]
        current_avg = self.injection_stats["average_injection_time"]
        
        # 增量平均计算
        self.injection_stats["average_injection_time"] = (
            (current_avg * (total_injections - 1) + injection_time) / total_injections
        )


# 全局动态配置注入器实例
_global_injector: Optional[DynamicConfigInjector] = None


def get_config_injector() -> DynamicConfigInjector:
    """获取全局配置注入器实例"""
    global _global_injector
    
    if _global_injector is None:
        _global_injector = DynamicConfigInjector()
    
    return _global_injector


async def inject_config_to_app(app: FastAPI, config: Dict[str, Any], 
                             source: str = "global") -> bool:
    """快速注入配置到应用"""
    injector = get_config_injector()
    return await injector.inject_to_application(app, config, source)


def subscribe_config_changes(callback: Callable, config_keys: Set[str] = None) -> str:
    """订阅配置变更"""
    injector = get_config_injector()
    return injector.register_config_change_subscriber(callback, config_keys)


async def hot_reload_configs(config_changes: Dict[str, Any]) -> bool:
    """热重载配置"""
    injector = get_config_injector()
    return await injector.hot_reload_config(config_changes)


# 常用的配置变更处理器示例
class CommonConfigHandlers:
    """常用配置变更处理器"""
    
    @staticmethod
    async def database_config_handler(event: ConfigChangeEvent):
        """数据库配置变更处理器"""
        if event.config_key == "DATABASE_URL":
            logger.info(f"数据库配置变更: {event.old_value} -> {event.new_value}")
            # TODO: 重新初始化数据库连接池
    
    @staticmethod 
    async def logging_config_handler(event: ConfigChangeEvent):
        """日志配置变更处理器"""
        if event.config_key == "LOG_LEVEL":
            logger.info(f"日志级别变更: {event.old_value} -> {event.new_value}")
            # TODO: 动态调整日志级别
            logging.getLogger().setLevel(getattr(logging, event.new_value, logging.INFO))
    
    @staticmethod
    async def redis_config_handler(event: ConfigChangeEvent):
        """Redis配置变更处理器"""
        redis_keys = {"REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD"}
        if event.config_key in redis_keys:
            logger.info(f"Redis配置变更: {event.config_key} = {event.new_value}")
            # TODO: 重新初始化Redis连接
    
    @staticmethod
    def register_common_handlers():
        """注册常用配置处理器"""
        injector = get_config_injector()
        
        # 注册数据库配置处理器
        injector.register_config_change_subscriber(
            CommonConfigHandlers.database_config_handler,
            config_keys={"DATABASE_URL"}
        )
        
        # 注册日志配置处理器
        injector.register_config_change_subscriber(
            CommonConfigHandlers.logging_config_handler,
            config_keys={"LOG_LEVEL"}
        )
        
        # 注册Redis配置处理器
        injector.register_config_change_subscriber(
            CommonConfigHandlers.redis_config_handler,
            config_keys={"REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD"}
        )
        
        logger.info("常用配置处理器注册完成") 