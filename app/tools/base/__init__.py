"""
基础工具包

提供系统级别的基础工具实现，包括子问题拆分和问答路由绑定等功能。
"""

from app.tools.base.subquestion_decomposer import SubQuestionDecomposer
from app.tools.base.qa_router import QARouter
from app.tools.base.register import register_base_tools
