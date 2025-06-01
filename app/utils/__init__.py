"""
应用工具模块
提供应用开发所需的各种工具和组件的统一接口

模块结构:
- core: 核心基础设施 (数据库、配置、缓存)
- text: 文本处理工具
- security: 安全工具
- storage: 存储系统
- monitoring: 监控指标
- messaging: 消息队列
- auth: 认证授权
- services: 服务管理
- web: Web工具
- common: 通用工具
"""

import logging

# 核心基础设施模块
from . import core

# Phase 2: 专用工具模块 - 使用安全导入
available_modules = ["core"]

try:
    from . import text
    available_modules.append("text")
except ImportError as e:
    logging.warning(f"Text模块导入失败: {e}")

try:
    from . import security
    available_modules.append("security")
except ImportError as e:
    logging.warning(f"Security模块导入失败: {e}")

try:
    from . import storage
    available_modules.append("storage")
except ImportError as e:
    logging.warning(f"Storage模块导入失败: {e}")

try:
    from . import monitoring
    available_modules.append("monitoring")
except ImportError as e:
    logging.warning(f"Monitoring模块导入失败: {e}")

# Phase 3: 服务集成模块 - 使用安全导入
try:
    from . import messaging
    available_modules.append("messaging")
except ImportError as e:
    logging.warning(f"Messaging模块导入失败: {e}")

try:
    from . import auth
    available_modules.append("auth")
except ImportError as e:
    logging.warning(f"Auth模块导入失败: {e}")

try:
    from . import services
    available_modules.append("services")
except ImportError as e:
    logging.warning(f"Services模块导入失败: {e}")

try:
    from . import web
    available_modules.append("web")
except ImportError as e:
    logging.warning(f"Web模块导入失败: {e}")

try:
    from . import common
    available_modules.append("common")
except ImportError as e:
    logging.warning(f"Common模块导入失败: {e}")

# 向后兼容的导入 - 为了保持旧代码正常工作
backward_compatible_functions = []

try:
    # Logger向后兼容
    from .common.logger import setup_logger, get_logger
    backward_compatible_functions.extend(["setup_logger", "get_logger"])
except ImportError as e:
    logging.warning(f"Logger向后兼容导入失败: {e}")

try:
    # Embedding utils向后兼容
    from .text.embedding_utils import get_embedding, batch_get_embeddings
    backward_compatible_functions.extend(["get_embedding", "batch_get_embeddings"])
except ImportError as e:
    logging.warning(f"Embedding utils向后兼容导入失败: {e}")

try:
    # Template renderer向后兼容
    from .text.template_renderer import render_assistant_page
    backward_compatible_functions.append("render_assistant_page")
except ImportError as e:
    logging.warning(f"Template renderer向后兼容导入失败: {e}")

# 动态构建__all__列表
__all__ = available_modules + backward_compatible_functions

# 记录成功加载的模块
logging.info(f"Utils模块加载完成，可用模块: {available_modules}")
if backward_compatible_functions:
    logging.info(f"向后兼容功能: {backward_compatible_functions}") 