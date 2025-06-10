"""
基础适配器实现
提供框架适配器的基础类和通用功能
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..abstractions import (
    ToolSpec, ToolResult, ToolStatus, ToolCategory, ToolExecutionContext,
    UniversalToolInterface, FrameworkInterface, FrameworkInfo, FrameworkStatus, FrameworkCapability
)


class AdapterError(Exception):
    """适配器错误"""
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        super().__init__(message)
        self.error_code = error_code
        self.original_error = original_error


class BaseToolAdapter(UniversalToolInterface):
    """基础工具适配器"""
    
    def __init__(self, provider_name: str, supported_categories: List[ToolCategory]):
        self._provider_name = provider_name
        self._supported_categories = supported_categories
        self._initialized = False
        self._tools_cache: Dict[str, ToolSpec] = {}
        self._logger = logging.getLogger(f"adapter.{provider_name}")
    
    @property
    def provider_name(self) -> str:
        return self._provider_name
    
    @property
    def supported_categories(self) -> List[ToolCategory]:
        return self._supported_categories
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize(self) -> bool:
        """初始化适配器"""
        try:
            await self._do_initialize()
            self._initialized = True
            self._logger.info(f"Adapter {self._provider_name} initialized successfully")
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize adapter {self._provider_name}: {e}")
            raise AdapterError(f"Initialization failed: {e}", "INIT_ERROR", e)
    
    async def shutdown(self) -> bool:
        """关闭适配器"""
        try:
            await self._do_shutdown()
            self._initialized = False
            self._logger.info(f"Adapter {self._provider_name} shutdown successfully")
            return True
        except Exception as e:
            self._logger.error(f"Failed to shutdown adapter {self._provider_name}: {e}")
            return False
    
    @abstractmethod
    async def _do_initialize(self):
        """子类实现具体的初始化逻辑"""
        pass
    
    @abstractmethod
    async def _do_shutdown(self):
        """子类实现具体的关闭逻辑"""
        pass
    
    async def register_tool(self, tool_spec: ToolSpec) -> Dict[str, Any]:
        """注册工具"""
        if not self._initialized:
            raise AdapterError("Adapter not initialized", "NOT_INITIALIZED")
        
        # 验证工具规范
        validation_errors = self._validate_tool_spec(tool_spec)
        if validation_errors:
            raise AdapterError(f"Tool spec validation failed: {validation_errors}", "VALIDATION_ERROR")
        
        # 缓存工具规范
        self._tools_cache[tool_spec.name] = tool_spec
        
        # 子类可以重写此方法进行特定的注册逻辑
        result = await self._do_register_tool(tool_spec)
        
        self._logger.info(f"Tool {tool_spec.name} registered successfully")
        return result
    
    async def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        if tool_name in self._tools_cache:
            del self._tools_cache[tool_name]
            await self._do_unregister_tool(tool_name)
            self._logger.info(f"Tool {tool_name} unregistered successfully")
            return True
        return False
    
    async def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """获取工具规范"""
        return self._tools_cache.get(tool_name)
    
    async def validate_params(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """验证工具参数"""
        tool_spec = await self.get_tool_spec(tool_name)
        if not tool_spec:
            return False
        
        # 基础参数验证逻辑
        return self._validate_params_against_schema(params, tool_spec.input_schema)
    
    def _validate_tool_spec(self, tool_spec: ToolSpec) -> List[str]:
        """验证工具规范"""
        errors = []
        
        if not tool_spec.name:
            errors.append("Tool name is required")
        
        if not tool_spec.version:
            errors.append("Tool version is required")
        
        if tool_spec.category not in self._supported_categories:
            errors.append(f"Unsupported tool category: {tool_spec.category}")
        
        if not tool_spec.input_schema:
            errors.append("Input schema is required")
        
        return errors
    
    def _validate_params_against_schema(self, params: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """根据schema验证参数"""
        # 简单的schema验证逻辑，子类可以重写
        required_params = schema.get("required", [])
        for param in required_params:
            if param not in params:
                return False
        return True
    
    async def _do_register_tool(self, tool_spec: ToolSpec) -> Dict[str, Any]:
        """子类实现具体的工具注册逻辑"""
        return {"status": "registered", "tool_name": tool_spec.name}
    
    async def _do_unregister_tool(self, tool_name: str):
        """子类实现具体的工具注销逻辑"""
        pass
    
    def _create_error_result(self, execution_id: str, tool_name: str, error: str, 
                           error_code: str = None) -> ToolResult:
        """创建错误结果"""
        return ToolResult(
            execution_id=execution_id,
            tool_name=tool_name,
            status=ToolStatus.FAILED,
            error=error,
            error_code=error_code,
            completed_at=datetime.now()
        )
    
    def _create_success_result(self, execution_id: str, tool_name: str, 
                             data: Any, duration_ms: int = None) -> ToolResult:
        """创建成功结果"""
        return ToolResult(
            execution_id=execution_id,
            tool_name=tool_name,
            status=ToolStatus.COMPLETED,
            data=data,
            completed_at=datetime.now(),
            duration_ms=duration_ms
        )


class BaseFrameworkAdapter(FrameworkInterface):
    """基础框架适配器"""
    
    def __init__(self, tool_adapter: BaseToolAdapter, config=None):
        super().__init__(config)
        self.tool_adapter = tool_adapter
        self._framework_info: Optional[FrameworkInfo] = None
    
    @property
    def framework_info(self) -> FrameworkInfo:
        if not self._framework_info:
            self._framework_info = self._create_framework_info()
        return self._framework_info
    
    @abstractmethod
    def _create_framework_info(self) -> FrameworkInfo:
        """子类实现创建框架信息"""
        pass
    
    async def initialize(self) -> bool:
        """初始化框架"""
        try:
            self.update_status(FrameworkStatus.INITIALIZING)
            
            # 初始化工具适配器
            await self.tool_adapter.initialize()
            
            # 创建工具接口
            self._tool_interface = self.tool_adapter
            
            # 执行框架特定的初始化
            await self._do_framework_initialize()
            
            self.update_status(FrameworkStatus.READY)
            return True
        except Exception as e:
            self.update_status(FrameworkStatus.ERROR)
            raise AdapterError(f"Framework initialization failed: {e}", "FRAMEWORK_INIT_ERROR", e)
    
    async def shutdown(self) -> bool:
        """关闭框架"""
        try:
            await self._do_framework_shutdown()
            await self.tool_adapter.shutdown()
            self.update_status(FrameworkStatus.SHUTDOWN)
            return True
        except Exception as e:
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": self.status.value,
            "tool_adapter_initialized": self.tool_adapter.is_initialized,
            "available_tools": len(self.tool_adapter._tools_cache),
            "timestamp": datetime.now().isoformat()
        }
    
    def has_capability(self, capability: FrameworkCapability) -> bool:
        """检查是否具有指定能力"""
        return capability in self.framework_info.capabilities
    
    def supports_category(self, category: ToolCategory) -> bool:
        """检查是否支持指定工具分类"""
        return category in self.framework_info.supported_categories
    
    async def create_tool_interface(self) -> UniversalToolInterface:
        """创建工具接口实例"""
        return self.tool_adapter
    
    async def _do_framework_initialize(self):
        """子类实现框架特定的初始化逻辑"""
        pass
    
    async def _do_framework_shutdown(self):
        """子类实现框架特定的关闭逻辑"""
        pass 