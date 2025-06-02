"""
Web工具模块
提供Web开发相关工具的统一接口

重构后的模块结构:
- core: 核心Web组件 
- docs: 文档生成工具
"""

import logging

# 可用模块列表
available_modules = []

# 安全导入各个模块
try:
    from .docs import *
    available_modules.append("docs")
except ImportError as e:
    logging.warning(f"Web Docs模块导入失败: {e}")

__all__ = []

# 条件性添加可选模块的导出
if "docs" in available_modules:
    __all__.extend([
        # 文档生成工具
        "save_db_schema_doc",
        "add_schema_examples",
        "generate_model_examples"
    ])
