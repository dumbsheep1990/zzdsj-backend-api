"""
OWL框架前端API模块
提供OWL（面向工作流语言）框架的RESTful API接口
"""

from fastapi import APIRouter

# 创建框架路由
router = APIRouter(prefix="/owl", tags=["OWL Framework"])

# 导入子模块将在模块扩展时添加
