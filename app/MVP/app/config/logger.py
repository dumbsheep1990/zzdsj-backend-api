"""
日志配置
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config.settings import get_settings

settings = get_settings()


def setup_logger(name: str = None) -> logging.Logger:
    """设置日志器"""
    logger = logging.getLogger(name or "app")

    # 清除现有处理器
    logger.handlers.clear()

    # 设置日志级别
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 创建格式化器
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果配置了）
    if settings.LOG_FILE:
        log_dir = Path(settings.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# 创建默认日志器
logger = setup_logger()