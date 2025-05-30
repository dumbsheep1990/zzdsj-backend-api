"""
API桥接模块入口
提供统一的API桥接管理和访问接口
"""

from app.api.bridge.bridge_implementation import get_bridge_router, bridge_manager

__all__ = ["get_bridge_router", "bridge_manager"]
