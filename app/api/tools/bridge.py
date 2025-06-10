"""
API工具桥接器
连接API层和统一注册中心，提供框架无关的工具访问接口
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...abstractions import (
    ToolSpec, ToolResult, ToolStatus, ToolCategory, ToolExecutionContext
)
from ...registry import RegistryManager


class APIToolBridge:
    """API工具桥接器 - 连接API层和注册中心"""
    
    def __init__(self, registry_manager: RegistryManager):
        self._registry_manager = registry_manager
        self._logger = logging.getLogger(__name__)
    
    @property
    def registry(self):
        """获取注册中心实例"""
        return self._registry_manager.registry
    
    async def get_overview(self) -> Dict[str, Any]:
        """获取工具系统概览"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        stats = self.registry.get_registry_stats()
        manager_status = self._registry_manager.get_comprehensive_status()
        
        return {
            "name": "ZZDSJ统一工具系统",
            "version": "1.0.0",
            "description": "框架无关的统一工具注册、发现和执行平台",
            "status": "operational" if manager_status["manager_status"] == "ready" else "degraded",
            "overview": {
                "total_tools": stats["total_tools"],
                "total_frameworks": stats["frameworks_count"],
                "total_executions": stats["total_executions"],
                "success_rate": self._calculate_success_rate(stats),
                "available_providers": stats["available_providers"],
                "supported_categories": list(stats["tools_by_category"].keys())
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_success_rate(self, stats: Dict[str, Any]) -> float:
        """计算成功率"""
        total = stats.get("total_executions", 0)
        if total == 0:
            return 1.0
        
        successful = stats.get("successful_executions", 0)
        return round(successful / total, 3)
    
    async def discover_tools(self, 
                           filters: Optional[Dict[str, Any]] = None,
                           categories: Optional[List[ToolCategory]] = None,
                           providers: Optional[List[str]] = None) -> List[ToolSpec]:
        """发现可用工具"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        return await self.registry.discover_tools(
            filters=filters,
            categories=categories,
            providers=providers
        )
    
    async def get_providers(self) -> List[Dict[str, Any]]:
        """获取所有提供方信息"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        stats = self.registry.get_registry_stats()
        providers_info = []
        
        for provider_name in stats["available_providers"]:
            provider_tools = stats["tools_by_provider"].get(provider_name, 0)
            
            # 获取提供方的工具分类统计
            tools = await self.registry.discover_tools(providers=[provider_name])
            categories = {}
            for tool in tools:
                category = tool.category.value
                categories[category] = categories.get(category, 0) + 1
            
            providers_info.append({
                "name": provider_name,
                "tool_count": provider_tools,
                "categories": categories,
                "status": "active"  # 简化的状态
            })
        
        return providers_info
    
    async def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """获取工具规范"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        return await self.registry.get_tool_spec(tool_name)
    
    async def execute_tool(self, 
                          tool_name: str,
                          params: Dict[str, Any],
                          context: Optional[ToolExecutionContext] = None) -> ToolResult:
        """执行工具"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        self._logger.info(f"Executing tool {tool_name} via API bridge")
        
        try:
            result = await self.registry.execute_tool(
                tool_name=tool_name,
                params=params,
                context=context
            )
            
            self._logger.info(f"Tool {tool_name} execution completed with status {result.status}")
            return result
            
        except Exception as e:
            self._logger.error(f"Tool {tool_name} execution failed: {e}")
            raise
    
    async def get_execution_status(self, execution_id: str) -> Optional[ToolStatus]:
        """获取执行状态"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        return self.registry.get_execution_status(execution_id)
    
    async def get_execution_result(self, execution_id: str) -> Optional[ToolResult]:
        """获取执行结果"""
        # 注意：这里需要根据实际的注册中心实现来获取结果
        # 目前的UnifiedToolRegistry没有直接提供这个方法
        # 这里提供一个基础实现
        
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        # 如果注册中心有存储执行结果的功能，这里调用相应方法
        # 暂时返回None，表示结果不可用或已过期
        return None
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        # 获取注册中心统计
        registry_stats = self.registry.get_registry_stats()
        
        # 获取管理器状态
        manager_status = self._registry_manager.get_comprehensive_status()
        
        # 组合统计信息
        return {
            "registry_stats": registry_stats,
            "manager_status": manager_status,
            "api_bridge": {
                "bridge_version": "1.0.0",
                "active": True,
                "last_activity": datetime.now().isoformat()
            },
            "system_health": {
                "overall_status": "healthy" if manager_status.get("health_status", {}).get("healthy", False) else "degraded",
                "uptime_seconds": manager_status.get("manager_uptime"),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查注册管理器状态
            manager_health = self._registry_manager.get_health_status()
            
            # 检查注册中心状态
            registry_available = self.registry is not None and self.registry._initialized
            
            # 简单的工具发现测试
            tools_discoverable = False
            try:
                tools = await self.registry.discover_tools() if self.registry else []
                tools_discoverable = len(tools) > 0
            except Exception:
                tools_discoverable = False
            
            # 综合健康状态
            overall_healthy = (
                manager_health.get("healthy", False) and
                registry_available and
                tools_discoverable
            )
            
            return {
                "healthy": overall_healthy,
                "manager_health": manager_health,
                "registry_available": registry_available,
                "tools_discoverable": tools_discoverable,
                "timestamp": datetime.now().isoformat(),
                "bridge_status": "operational"
            }
            
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "bridge_status": "error"
            }
    
    async def validate_tool_params(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具参数"""
        if not self.registry:
            raise RuntimeError("Registry not available")
        
        tool_spec = await self.get_tool_spec(tool_name)
        if not tool_spec:
            return {
                "valid": False,
                "error": f"Tool {tool_name} not found"
            }
        
        # 基础参数验证
        input_schema = tool_spec.input_schema
        required_params = input_schema.get("required", [])
        
        missing_params = []
        for param in required_params:
            if param not in params:
                missing_params.append(param)
        
        if missing_params:
            return {
                "valid": False,
                "error": f"Missing required parameters: {missing_params}"
            }
        
        return {
            "valid": True,
            "message": "Parameters are valid"
        } 