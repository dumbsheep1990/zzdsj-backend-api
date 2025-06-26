"""
Agno工具注册中心
自动发现、注册和管理所有可用工具，实现完全解耦合
"""

import os
import importlib
import inspect
import logging
from typing import Any, Dict, List, Optional, Type, Set
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from .types import (
    IToolRegistry, ToolMetadata, ToolInstance, ToolCategory, 
    ToolFramework, DEFAULT_TOOL_TIMEOUT
)

logger = logging.getLogger(__name__)

class AgnoToolRegistry(IToolRegistry):
    """Agno工具注册中心
    
    自动发现和注册工具，提供统一的工具管理接口
    """
    
    def __init__(self):
        """初始化注册中心"""
        self._tools: Dict[str, ToolMetadata] = {}
        self._tool_classes: Dict[str, Type] = {}
        self._tool_instances: Dict[str, ToolInstance] = {}
        self._discovery_paths: List[str] = []
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = False
        
    async def initialize(self):
        """初始化注册中心"""
        if self._initialized:
            return
            
        try:
            # 设置工具发现路径
            await self._setup_discovery_paths()
            
            # 自动发现工具
            await self._discover_all_tools()
            
            self._initialized = True
            logger.info(f"工具注册中心初始化完成，发现 {len(self._tools)} 个工具")
            
        except Exception as e:
            logger.error(f"工具注册中心初始化失败: {str(e)}", exc_info=True)
            
    async def _setup_discovery_paths(self):
        """设置工具发现路径"""
        # 主要工具路径
        base_path = "app.tools.agno"
        self._discovery_paths = [
            f"{base_path}.reasoning",
            f"{base_path}.search", 
            f"{base_path}.knowledge",
            f"{base_path}.chunking",
            f"{base_path}.custom_tools",
        ]
        
        # 动态发现所有子模块
        try:
            tools_path = Path(__file__).parent.parent.parent.parent / "tools" / "agno"
            if tools_path.exists():
                for item in tools_path.iterdir():
                    if item.is_dir() and not item.name.startswith('__'):
                        module_path = f"{base_path}.{item.name}"
                        if module_path not in self._discovery_paths:
                            self._discovery_paths.append(module_path)
        except Exception as e:
            logger.warning(f"动态发现工具路径失败: {str(e)}")
    
    async def _discover_all_tools(self):
        """发现所有工具"""
        discovered_count = 0
        
        for module_path in self._discovery_paths:
            try:
                count = await self._discover_tools_in_module(module_path)
                discovered_count += count
                logger.debug(f"在模块 {module_path} 中发现 {count} 个工具")
            except Exception as e:
                logger.warning(f"发现模块 {module_path} 中的工具失败: {str(e)}")
                
        logger.info(f"工具发现完成，总共发现 {discovered_count} 个工具")
    
    async def _discover_tools_in_module(self, module_path: str) -> int:
        """在指定模块中发现工具"""
        try:
            # 动态导入模块
            module = importlib.import_module(module_path)
            discovered_count = 0
            
            # 检查模块中的所有类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if await self._is_valid_tool(obj, module_path):
                    tool_metadata = await self._extract_tool_metadata(obj, module_path)
                    if tool_metadata:
                        await self.register_tool(tool_metadata, obj)
                        discovered_count += 1
                        
            # 检查是否有管理器类（如AgnoReasoningManager）
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.endswith('Manager') and await self._is_valid_manager(obj):
                    tool_metadata = await self._extract_manager_metadata(obj, module_path)
                    if tool_metadata:
                        await self.register_tool(tool_metadata, obj)
                        discovered_count += 1
                        
            return discovered_count
            
        except ImportError as e:
            logger.debug(f"无法导入模块 {module_path}: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"在模块 {module_path} 中发现工具失败: {str(e)}")
            return 0
    
    async def _is_valid_tool(self, tool_class: Type, module_path: str) -> bool:
        """检查是否为有效工具"""
        try:
            # 检查类名模式
            class_name = tool_class.__name__
            if not (class_name.endswith('Tool') or class_name.endswith('Tools')):
                return False
                
            # 检查是否在正确的模块中定义
            if tool_class.__module__ != module_path:
                return False
                
            # 检查是否有必要的方法（异步调用或同步调用）
            has_call_method = (
                hasattr(tool_class, '__call__') or
                hasattr(tool_class, 'acall') or 
                hasattr(tool_class, 'call') or
                hasattr(tool_class, 'execute') or
                hasattr(tool_class, 'run')
            )
            
            return has_call_method
            
        except Exception:
            return False
    
    async def _is_valid_manager(self, manager_class: Type) -> bool:
        """检查是否为有效的管理器"""
        try:
            # 检查管理器特征
            class_name = manager_class.__name__
            if not class_name.endswith('Manager'):
                return False
                
            # 检查是否有工具实例属性
            signature = inspect.signature(manager_class.__init__)
            
            # 尝试创建实例来检查工具属性
            try:
                # 检查类是否有工具相关的属性或方法
                for attr_name in dir(manager_class):
                    if 'tool' in attr_name.lower() and not attr_name.startswith('_'):
                        return True
            except:
                pass
                
            return False
            
        except Exception:
            return False
    
    async def _extract_tool_metadata(self, tool_class: Type, module_path: str) -> Optional[ToolMetadata]:
        """提取工具元数据"""
        try:
            class_name = tool_class.__name__
            
            # 提取类别
            category = self._extract_category_from_path(module_path)
            
            # 提取描述
            description = tool_class.__doc__ or f"Agno {class_name} 工具"
            description = description.strip().split('\n')[0]  # 取第一行
            
            # 生成工具ID
            tool_id = f"agno_{category.value}_{class_name.lower()}"
            
            # 提取能力列表
            capabilities = await self._extract_capabilities(tool_class)
            
            # 提取配置模式
            config_schema = await self._extract_config_schema(tool_class)
            
            return ToolMetadata(
                id=tool_id,
                name=class_name,
                description=description,
                category=category,
                framework=ToolFramework.AGNO,
                capabilities=capabilities,
                config_schema=config_schema,
                is_async=self._is_async_tool(tool_class)
            )
            
        except Exception as e:
            logger.error(f"提取工具元数据失败 {tool_class.__name__}: {str(e)}")
            return None
    
    async def _extract_manager_metadata(self, manager_class: Type, module_path: str) -> Optional[ToolMetadata]:
        """提取管理器元数据"""
        try:
            class_name = manager_class.__name__
            
            # 提取类别
            category = self._extract_category_from_path(module_path)
            
            # 提取描述
            description = manager_class.__doc__ or f"Agno {class_name} 管理器"
            description = description.strip().split('\n')[0]
            
            # 生成工具ID
            tool_id = f"agno_{category.value}_manager"
            
            # 管理器的能力通常包含其管理的工具能力
            capabilities = [
                f"{category.value}_management",
                f"{category.value}_tools",
                "tool_aggregation"
            ]
            
            return ToolMetadata(
                id=tool_id,
                name=class_name,
                description=description,
                category=category,
                framework=ToolFramework.AGNO,
                capabilities=capabilities,
                is_async=True  # 管理器通常支持异步
            )
            
        except Exception as e:
            logger.error(f"提取管理器元数据失败 {manager_class.__name__}: {str(e)}")
            return None
    
    def _extract_category_from_path(self, module_path: str) -> ToolCategory:
        """从模块路径提取类别"""
        path_parts = module_path.split('.')
        
        for part in reversed(path_parts):
            if part == 'reasoning':
                return ToolCategory.REASONING
            elif part == 'search':
                return ToolCategory.SEARCH
            elif part == 'knowledge':
                return ToolCategory.KNOWLEDGE
            elif part == 'chunking':
                return ToolCategory.CHUNKING
            elif part in ['file', 'files']:
                return ToolCategory.FILE_MANAGEMENT
            elif part == 'system':
                return ToolCategory.SYSTEM
                
        return ToolCategory.CUSTOM
    
    async def _extract_capabilities(self, tool_class: Type) -> List[str]:
        """提取工具能力"""
        capabilities = []
        
        try:
            # 从方法名推断能力
            for method_name in dir(tool_class):
                if not method_name.startswith('_') and callable(getattr(tool_class, method_name, None)):
                    capabilities.append(method_name)
            
            # 从类名推断能力
            class_name = tool_class.__name__.lower()
            if 'reasoning' in class_name:
                capabilities.extend(['reasoning', 'analysis', 'logic'])
            elif 'search' in class_name:
                capabilities.extend(['search', 'retrieval', 'query'])
            elif 'knowledge' in class_name:
                capabilities.extend(['knowledge', 'qa', 'information'])
            elif 'chunking' in class_name:
                capabilities.extend(['chunking', 'splitting', 'processing'])
                
        except Exception as e:
            logger.warning(f"提取能力失败 {tool_class.__name__}: {str(e)}")
            
        return list(set(capabilities))  # 去重
    
    async def _extract_config_schema(self, tool_class: Type) -> Dict[str, Any]:
        """提取配置模式"""
        try:
            # 检查__init__方法的参数
            signature = inspect.signature(tool_class.__init__)
            schema = {}
            
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue
                    
                param_info = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'required': param.default == inspect.Parameter.empty,
                    'default': param.default if param.default != inspect.Parameter.empty else None
                }
                schema[param_name] = param_info
                
            return schema
            
        except Exception as e:
            logger.warning(f"提取配置模式失败 {tool_class.__name__}: {str(e)}")
            return {}
    
    def _is_async_tool(self, tool_class: Type) -> bool:
        """检查是否为异步工具"""
        try:
            # 检查常见异步方法
            async_methods = ['acall', 'arun', 'aexecute', '__acall__']
            
            for method_name in async_methods:
                if hasattr(tool_class, method_name):
                    method = getattr(tool_class, method_name)
                    if asyncio.iscoroutinefunction(method):
                        return True
            
            # 检查__call__方法
            if hasattr(tool_class, '__call__'):
                return asyncio.iscoroutinefunction(tool_class.__call__)
                
            return False
            
        except Exception:
            return True  # 默认假设支持异步
    
    # 实现IToolRegistry接口
    async def register_tool(self, tool_metadata: ToolMetadata, tool_class: Type) -> bool:
        """注册工具"""
        try:
            self._tools[tool_metadata.id] = tool_metadata
            self._tool_classes[tool_metadata.id] = tool_class
            
            logger.debug(f"成功注册工具: {tool_metadata.name} ({tool_metadata.id})")
            return True
            
        except Exception as e:
            logger.error(f"注册工具失败 {tool_metadata.id}: {str(e)}")
            return False
    
    async def unregister_tool(self, tool_id: str) -> bool:
        """注销工具"""
        try:
            if tool_id in self._tools:
                del self._tools[tool_id]
            if tool_id in self._tool_classes:
                del self._tool_classes[tool_id]
            if tool_id in self._tool_instances:
                del self._tool_instances[tool_id]
                
            logger.debug(f"成功注销工具: {tool_id}")
            return True
            
        except Exception as e:
            logger.error(f"注销工具失败 {tool_id}: {str(e)}")
            return False
    
    async def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        return self._tools.get(tool_id)
    
    async def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolMetadata]:
        """列出工具"""
        tools = list(self._tools.values())
        
        if category:
            tools = [tool for tool in tools if tool.category == category]
            
        return sorted(tools, key=lambda x: x.name)
    
    async def create_tool_instance(self, tool_id: str, config: Dict[str, Any]) -> Optional[ToolInstance]:
        """创建工具实例"""
        try:
            # 检查缓存
            cache_key = f"{tool_id}_{hash(str(sorted(config.items())))}"
            if cache_key in self._tool_instances:
                instance = self._tool_instances[cache_key]
                instance.usage_count += 1
                instance.last_used = datetime.now()
                return instance
            
            # 获取工具类
            tool_class = self._tool_classes.get(tool_id)
            tool_metadata = self._tools.get(tool_id)
            
            if not tool_class or not tool_metadata:
                logger.error(f"工具 {tool_id} 未找到")
                return None
            
            # 创建实例
            try:
                tool_instance = tool_class(**config) if config else tool_class()
            except TypeError as e:
                # 处理参数不匹配的情况
                logger.warning(f"创建工具实例时参数不匹配，尝试无参数创建: {str(e)}")
                tool_instance = tool_class()
            
            # 包装为ToolInstance
            instance = ToolInstance(
                metadata=tool_metadata,
                instance=tool_instance,
                config=config,
                is_initialized=True,
                usage_count=1
            )
            
            # 缓存实例
            self._tool_instances[cache_key] = instance
            
            logger.debug(f"成功创建工具实例: {tool_metadata.name}")
            return instance
            
        except Exception as e:
            logger.error(f"创建工具实例失败 {tool_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_tools_by_capability(self, capability: str) -> List[ToolMetadata]:
        """根据能力获取工具"""
        return [
            tool for tool in self._tools.values()
            if capability.lower() in [cap.lower() for cap in tool.capabilities]
        ]
    
    async def search_tools(self, query: str) -> List[ToolMetadata]:
        """搜索工具"""
        query_lower = query.lower()
        matches = []
        
        for tool in self._tools.values():
            score = 0
            
            # 名称匹配
            if query_lower in tool.name.lower():
                score += 10
            
            # 描述匹配  
            if query_lower in tool.description.lower():
                score += 5
                
            # 能力匹配
            for capability in tool.capabilities:
                if query_lower in capability.lower():
                    score += 3
                    
            if score > 0:
                matches.append((tool, score))
        
        # 按得分排序
        matches.sort(key=lambda x: x[1], reverse=True)
        return [tool for tool, _ in matches]
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """获取注册中心统计信息"""
        category_counts = {}
        framework_counts = {}
        
        for tool in self._tools.values():
            category_counts[tool.category.value] = category_counts.get(tool.category.value, 0) + 1
            framework_counts[tool.framework.value] = framework_counts.get(tool.framework.value, 0) + 1
        
        return {
            'total_tools': len(self._tools),
            'total_instances': len(self._tool_instances),
            'category_distribution': category_counts,
            'framework_distribution': framework_counts,
            'discovery_paths': self._discovery_paths,
            'initialized': self._initialized
        }

# 全局注册中心实例
_registry: Optional[AgnoToolRegistry] = None

async def get_tool_registry() -> AgnoToolRegistry:
    """获取工具注册中心实例"""
    global _registry
    
    if _registry is None:
        _registry = AgnoToolRegistry()
        await _registry.initialize()
    
    return _registry

async def initialize_registry() -> AgnoToolRegistry:
    """初始化工具注册中心"""
    return await get_tool_registry()

async def cleanup_registry():
    """清理注册中心"""
    global _registry
    if _registry:
        _registry = None 