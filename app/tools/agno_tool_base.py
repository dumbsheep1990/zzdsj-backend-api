"""
AGNO工具基础类
为所有AGNO工具提供统一的基础接口和功能
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field


class AgnoToolResult(BaseModel):
    """AGNO工具执行结果"""
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class AgnoToolConfig(BaseModel):
    """AGNO工具配置"""
    tool_name: str
    version: str = "1.0.0"
    enabled: bool = True
    max_concurrent: int = 10
    timeout: float = 30.0
    retry_count: int = 3
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class AgnoToolBase(ABC):
    """AGNO工具基础抽象类"""
    
    def __init__(self, config: AgnoToolConfig):
        self.config = config
        self.logger = logging.getLogger(f"agno.tools.{config.tool_name}")
        self._execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0.0
        }
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """初始化工具"""
        if self._is_initialized:
            return
        
        try:
            await self._do_initialize()
            self._is_initialized = True
            self.logger.info(f"Tool {self.config.tool_name} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize tool {self.config.tool_name}: {e}")
            raise
    
    async def shutdown(self) -> None:
        """关闭工具"""
        if not self._is_initialized:
            return
        
        try:
            await self._do_shutdown()
            self._is_initialized = False
            self.logger.info(f"Tool {self.config.tool_name} shutdown successfully")
        except Exception as e:
            self.logger.error(f"Failed to shutdown tool {self.config.tool_name}: {e}")
    
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgnoToolResult:
        """执行工具"""
        if not self._is_initialized:
            await self.initialize()
        
        execution_id = str(uuid4())
        start_time = datetime.now()
        
        try:
            # 参数验证
            validated_params = await self._validate_params(params)
            
            # 执行工具逻辑
            result = await asyncio.wait_for(
                self._do_execute(validated_params, context),
                timeout=self.config.timeout
            )
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 更新统计信息
            self._update_stats(execution_time, True)
            
            return AgnoToolResult(
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={
                    "execution_id": execution_id,
                    "tool_name": self.config.tool_name,
                    "version": self.config.version
                }
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(execution_time, False)
            
            return AgnoToolResult(
                success=False,
                error=f"Tool execution timeout after {self.config.timeout}s",
                execution_time=execution_time,
                metadata={"execution_id": execution_id}
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(execution_time, False)
            
            self.logger.error(f"Tool execution failed: {e}")
            
            return AgnoToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                metadata={"execution_id": execution_id}
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工具统计信息"""
        return {
            "tool_name": self.config.tool_name,
            "version": self.config.version,
            "enabled": self.config.enabled,
            "initialized": self._is_initialized,
            "stats": self._execution_stats.copy()
        }
    
    @abstractmethod
    async def _do_initialize(self) -> None:
        """子类实现具体的初始化逻辑"""
        pass
    
    @abstractmethod
    async def _do_shutdown(self) -> None:
        """子类实现具体的关闭逻辑"""
        pass
    
    @abstractmethod
    async def _do_execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """子类实现具体的执行逻辑"""
        pass
    
    @abstractmethod
    async def _validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """子类实现参数验证逻辑"""
        pass
    
    def _update_stats(self, execution_time: float, success: bool) -> None:
        """更新执行统计信息"""
        self._execution_stats["total_executions"] += 1
        
        if success:
            self._execution_stats["successful_executions"] += 1
        else:
            self._execution_stats["failed_executions"] += 1
        
        # 更新平均执行时间
        total = self._execution_stats["total_executions"]
        current_avg = self._execution_stats["avg_execution_time"]
        self._execution_stats["avg_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )


class AgnoToolManager:
    """AGNO工具管理器 - 管理所有AGNO工具实例"""
    
    def __init__(self):
        self.tools: Dict[str, AgnoToolBase] = {}
        self.logger = logging.getLogger("agno.tools.manager")
    
    async def register_tool(self, tool: AgnoToolBase) -> None:
        """注册工具"""
        tool_name = tool.config.tool_name
        
        if tool_name in self.tools:
            self.logger.warning(f"Tool {tool_name} already registered, replacing...")
        
        self.tools[tool_name] = tool
        await tool.initialize()
        
        self.logger.info(f"Tool {tool_name} registered successfully")
    
    async def unregister_tool(self, tool_name: str) -> None:
        """注销工具"""
        if tool_name not in self.tools:
            self.logger.warning(f"Tool {tool_name} not found")
            return
        
        tool = self.tools.pop(tool_name)
        await tool.shutdown()
        
        self.logger.info(f"Tool {tool_name} unregistered successfully")
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgnoToolResult:
        """执行指定工具"""
        if tool_name not in self.tools:
            return AgnoToolResult(
                success=False,
                error=f"Tool {tool_name} not found"
            )
        
        tool = self.tools[tool_name]
        
        if not tool.config.enabled:
            return AgnoToolResult(
                success=False,
                error=f"Tool {tool_name} is disabled"
            )
        
        return await tool.execute(params, context)
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [
            name for name, tool in self.tools.items()
            if tool.config.enabled
        ]
    
    def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具统计信息"""
        if tool_name:
            if tool_name not in self.tools:
                return {"error": f"Tool {tool_name} not found"}
            return self.tools[tool_name].get_stats()
        
        # 返回所有工具的统计信息
        return {
            name: tool.get_stats()
            for name, tool in self.tools.items()
        }
    
    async def shutdown_all(self) -> None:
        """关闭所有工具"""
        for tool_name in list(self.tools.keys()):
            await self.unregister_tool(tool_name)


# 全局工具管理器实例
agno_tool_manager = AgnoToolManager()


class AgnoAsyncTool(AgnoToolBase):
    """异步AGNO工具基础类"""
    
    def __init__(self, config: AgnoToolConfig):
        super().__init__(config)
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
    
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgnoToolResult:
        """使用信号量控制并发执行"""
        async with self._semaphore:
            return await super().execute(params, context)


class AgnoRetryTool(AgnoToolBase):
    """支持重试的AGNO工具基础类"""
    
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgnoToolResult:
        """带重试机制的执行"""
        last_error = None
        
        for attempt in range(self.config.retry_count + 1):
            try:
                result = await super().execute(params, context)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
                
            if attempt < self.config.retry_count:
                # 指数退避
                await asyncio.sleep(2 ** attempt)
        
        return AgnoToolResult(
            success=False,
            error=f"Failed after {self.config.retry_count + 1} attempts. Last error: {last_error}"
        ) 