"""
助手API模块: 提供与AI助手交互的端点，
支持各种模式（文本、图像、语音）和不同的接口格式
[迁移桥接] - 该文件已迁移至 app/api/frontend/assistants/assistant.py
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse
import logging

# 导入新的API模块
from app.api.frontend.assistants.assistant import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/assistant.py，该文件已迁移至app/api/frontend/assistants/assistant.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
