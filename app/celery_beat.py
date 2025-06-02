"""
Celery Beat 定时任务调度配置
提供周期性任务的调度管理
"""

from celery.schedules import crontab
from app.worker import celery_app
import logging

logger = logging.getLogger(__name__)

# 定时任务配置
celery_app.conf.beat_schedule = {
    # 每日数据清理 - 每天凌晨2点执行
    'daily-cleanup': {
        'task': 'cleanup_expired_data',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'maintenance'}
    },
    
    # 每周报表生成 - 每周一早6点执行
    'weekly-report': {
        'task': 'generate_weekly_report',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),
        'options': {'queue': 'reports'}
    },
    
    # 系统健康检查 - 每5分钟执行一次
    'system-health-check': {
        'task': 'system_health_check',
        'schedule': 300.0,  # 5分钟
        'options': {'queue': 'monitoring'}
    },
    
    # 清理任务执行历史 - 每天凌晨3点执行
    'cleanup-task-history': {
        'task': 'cleanup_task_history',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'maintenance'}
    },
    
    # 缓存预热 - 每天凌晨4点执行
    'cache-warmup': {
        'task': 'cache_warmup',
        'schedule': crontab(hour=4, minute=0),
        'options': {'queue': 'cache'}
    },
    
    # 数据库连接检查 - 每分钟执行
    'db-connection-check': {
        'task': 'check_db_connections',
        'schedule': 60.0,
        'options': {'queue': 'monitoring'}
    },
    
    # 磁盘空间检查 - 每小时执行
    'disk-space-check': {
        'task': 'check_disk_space',
        'schedule': crontab(minute=0),  # 每小时的0分
        'options': {'queue': 'monitoring'}
    },
    
    # 用户活动统计 - 每天凌晨1点执行
    'daily-user-stats': {
        'task': 'calculate_daily_user_stats',
        'schedule': crontab(hour=1, minute=0),
        'options': {'queue': 'analytics'}
    }
}

# Beat调度器配置
celery_app.conf.update(
    timezone='Asia/Shanghai',
    enable_utc=True,
    beat_schedule_filename='celerybeat-schedule',
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler' if False else 'celery.beat:PersistentScheduler'
)

# 任务队列路由配置
celery_app.conf.task_routes = {
    # 维护任务队列
    'cleanup_expired_data': {'queue': 'maintenance'},
    'cleanup_task_history': {'queue': 'maintenance'},
    
    # 报表队列
    'generate_weekly_report': {'queue': 'reports'},
    'generate_report': {'queue': 'reports'},
    
    # 监控队列
    'system_health_check': {'queue': 'monitoring'},
    'check_db_connections': {'queue': 'monitoring'},
    'check_disk_space': {'queue': 'monitoring'},
    
    # 分析队列
    'calculate_daily_user_stats': {'queue': 'analytics'},
    
    # 缓存队列
    'cache_warmup': {'queue': 'cache'},
    'refresh_cache': {'queue': 'cache'},
    
    # 默认队列
    'process_document': {'queue': 'default'},
    'rebuild_vector_store': {'queue': 'default'},
    'generate_assistant_response': {'queue': 'default'},
}

logger.info("Celery Beat 调度配置已加载") 