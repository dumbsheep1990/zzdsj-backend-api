"""
ZZDSJ工具注册系统
统一管理和注册所有ZZDSJ自研工具
注意：这是ZZDSJ自研的工具注册系统，不是Agno框架的工具注册系统
"""

import logging
from typing import Dict, List, Any, Optional, Type, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

class ToolCategory(Enum):
    """工具分类枚举"""
    SEARCH = "search"
    REASONING = "reasoning"
    KNOWLEDGE = "knowledge"
    FILE_MANAGEMENT = "file_management"
    SYSTEM = "system"
    COMMUNICATION = "communication"
    DATA_PROCESSING = "data_processing"
    INTEGRATION = "integration"
    ADVANCED = "advanced"
    CUSTOM = "custom"

class ToolStatus(Enum):
    """工具状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: str = "ZZDSJ"
    status: ToolStatus = ToolStatus.ACTIVE
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

@dataclass
class RegisteredTool:
    """注册的工具信息"""
    tool_class: Type
    factory_function: Optional[Callable] = None
    metadata: Optional[ToolMetadata] = None
    instance: Optional[Any] = None
    is_singleton: bool = False

class ZZDSJToolRegistry:
    """ZZDSJ工具注册中心（自研）"""
    
    def __init__(self):
        """初始化工具注册中心"""
        self._tools: Dict[str, RegisteredTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            category: [] for category in ToolCategory
        }
        self._instances: Dict[str, Any] = {}
        
        # 自动注册内置工具
        self._register_builtin_tools()
    
    def register_tool(
        self,
        name: str,
        tool_class: Type,
        metadata: ToolMetadata,
        factory_function: Optional[Callable] = None,
        is_singleton: bool = False
    ) -> bool:
        """
        注册工具
        
        参数:
            name: 工具名称
            tool_class: 工具类
            metadata: 工具元数据
            factory_function: 工具工厂函数（可选）
            is_singleton: 是否为单例模式
            
        返回:
            是否注册成功
        """
        try:
            if name in self._tools:
                logger.warning(f"工具 '{name}' 已存在，将被覆盖")
            
            registered_tool = RegisteredTool(
                tool_class=tool_class,
                factory_function=factory_function,
                metadata=metadata,
                is_singleton=is_singleton
            )
            
            self._tools[name] = registered_tool
            
            # 添加到分类索引
            if metadata.category not in self._categories[metadata.category]:
                self._categories[metadata.category].append(name)
            
            logger.info(f"成功注册工具: {name} ({metadata.category.value})")
            return True
            
        except Exception as e:
            logger.error(f"注册工具 '{name}' 失败: {str(e)}")
            return False
    
    def get_tool(self, name: str, **kwargs) -> Optional[Any]:
        """
        获取工具实例
        
        参数:
            name: 工具名称
            **kwargs: 传递给工具构造函数的参数
            
        返回:
            工具实例
        """
        try:
            if name not in self._tools:
                logger.error(f"工具 '{name}' 未注册")
                return None
            
            registered_tool = self._tools[name]
            
            # 如果是单例模式且已创建实例，直接返回
            if registered_tool.is_singleton and registered_tool.instance:
                return registered_tool.instance
            
            # 使用工厂函数创建实例
            if registered_tool.factory_function:
                instance = registered_tool.factory_function(**kwargs)
            else:
                instance = registered_tool.tool_class(**kwargs)
            
            # 更新使用计数
            if registered_tool.metadata:
                registered_tool.metadata.usage_count += 1
            
            # 如果是单例模式，保存实例
            if registered_tool.is_singleton:
                registered_tool.instance = instance
            
            return instance
            
        except Exception as e:
            logger.error(f"获取工具 '{name}' 实例失败: {str(e)}")
            return None
    
    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """
        根据分类获取工具名称列表
        
        参数:
            category: 工具分类
            
        返回:
            工具名称列表
        """
        return self._categories.get(category, [])
    
    def list_all_tools(self) -> List[str]:
        """
        列出所有注册的工具
        
        返回:
            工具名称列表
        """
        return list(self._tools.keys())
    
    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        获取工具元数据
        
        参数:
            name: 工具名称
            
        返回:
            工具元数据
        """
        registered_tool = self._tools.get(name)
        return registered_tool.metadata if registered_tool else None
    
    def search_tools(
        self, 
        query: str = "",
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[str]:
        """
        搜索工具
        
        参数:
            query: 搜索查询
            category: 工具分类
            status: 工具状态
            tags: 标签列表
            
        返回:
            匹配的工具名称列表
        """
        results = []
        
        for name, registered_tool in self._tools.items():
            metadata = registered_tool.metadata
            if not metadata:
                continue
            
            # 分类过滤
            if category and metadata.category != category:
                continue
            
            # 状态过滤
            if status and metadata.status != status:
                continue
            
            # 标签过滤
            if tags and not any(tag in metadata.tags for tag in tags):
                continue
            
            # 查询过滤
            if query:
                query_lower = query.lower()
                if (query_lower not in name.lower() and 
                    query_lower not in metadata.description.lower() and
                    not any(query_lower in tag.lower() for tag in metadata.tags)):
                    continue
            
            results.append(name)
        
        return results
    
    def unregister_tool(self, name: str) -> bool:
        """
        注销工具
        
        参数:
            name: 工具名称
            
        返回:
            是否注销成功
        """
        try:
            if name not in self._tools:
                logger.warning(f"工具 '{name}' 未注册")
                return False
            
            registered_tool = self._tools[name]
            
            # 从分类索引中移除
            if registered_tool.metadata:
                category_tools = self._categories[registered_tool.metadata.category]
                if name in category_tools:
                    category_tools.remove(name)
            
            # 清理实例
            if registered_tool.instance:
                registered_tool.instance = None
            
            # 从注册表中移除
            del self._tools[name]
            
            logger.info(f"成功注销工具: {name}")
            return True
            
        except Exception as e:
            logger.error(f"注销工具 '{name}' 失败: {str(e)}")
            return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        获取注册中心统计信息
        
        返回:
            统计信息字典
        """
        total_tools = len(self._tools)
        category_stats = {}
        status_stats = {}
        
        for registered_tool in self._tools.values():
            if registered_tool.metadata:
                # 分类统计
                category = registered_tool.metadata.category.value
                category_stats[category] = category_stats.get(category, 0) + 1
                
                # 状态统计
                status = registered_tool.metadata.status.value
                status_stats[status] = status_stats.get(status, 0) + 1
        
        return {
            "total_tools": total_tools,
            "category_distribution": category_stats,
            "status_distribution": status_stats,
            "categories": [cat.value for cat in ToolCategory],
            "active_categories": len([cat for cat, tools in self._categories.items() if tools])
        }
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        try:
            # 注册搜索工具
            from app.tools.base.search.agno_search_tool import AgnoWebSearchTool, create_agno_web_search_tool
            
            search_metadata = ToolMetadata(
                name="web_search",
                description="基于SearxNG的Web搜索工具，支持多搜索引擎和实时信息获取",
                category=ToolCategory.SEARCH,
                version="1.0.0",
                capabilities=["web_search", "multi_engine", "real_time_info"],
                tags=["search", "web", "real-time", "searxng"]
            )
            
            self.register_tool(
                name="web_search",
                tool_class=AgnoWebSearchTool,
                metadata=search_metadata,
                factory_function=create_agno_web_search_tool,
                is_singleton=False
            )
            
            # 注册推理工具
            from app.tools.advanced.reasoning.agno_cot_tool import AgnoCoTTool, create_agno_cot_tool
            
            reasoning_metadata = ToolMetadata(
                name="cot_reasoning",
                description="链式思考推理工具，支持多步骤思维链和逻辑推理",
                category=ToolCategory.REASONING,
                version="1.0.0",
                capabilities=["chain_of_thought", "step_by_step", "logical_reasoning"],
                tags=["reasoning", "cot", "thinking", "analysis"]
            )
            
            self.register_tool(
                name="cot_reasoning",
                tool_class=AgnoCoTTool,
                metadata=reasoning_metadata,
                factory_function=create_agno_cot_tool,
                is_singleton=False
            )
            
            # 注册知识库工具
            from app.frameworks.agno.tools import ZZDSJKnowledgeTools, get_zzdsj_knowledge_tools
            
            knowledge_metadata = ToolMetadata(
                name="knowledge_tools",
                description="ZZDSJ知识库工具包，支持文档搜索、摘要生成和元数据提取",
                category=ToolCategory.KNOWLEDGE,
                version="1.0.0",
                capabilities=["document_search", "summarization", "metadata_extraction"],
                tags=["knowledge", "documents", "search", "summary"]
            )
            
            self.register_tool(
                name="knowledge_tools",
                tool_class=ZZDSJKnowledgeTools,
                metadata=knowledge_metadata,
                factory_function=get_zzdsj_knowledge_tools,
                is_singleton=False
            )
            
            # 注册文件管理工具
            from app.frameworks.agno.tools import ZZDSJFileManagementTools, get_zzdsj_file_tools
            
            file_metadata = ToolMetadata(
                name="file_management_tools",
                description="ZZDSJ文件管理工具包，支持文件列表、信息获取和基础操作",
                category=ToolCategory.FILE_MANAGEMENT,
                version="1.0.0",
                capabilities=["file_listing", "file_info", "directory_management"],
                tags=["files", "management", "directory", "metadata"]
            )
            
            self.register_tool(
                name="file_management_tools",
                tool_class=ZZDSJFileManagementTools,
                metadata=file_metadata,
                factory_function=get_zzdsj_file_tools,
                is_singleton=False
            )
            
            # 注册系统工具
            from app.frameworks.agno.tools import ZZDSJSystemTools, get_zzdsj_system_tools
            
            system_metadata = ToolMetadata(
                name="system_tools",
                description="ZZDSJ系统工具包，支持系统状态监控和服务健康检查",
                category=ToolCategory.SYSTEM,
                version="1.0.0",
                capabilities=["system_monitoring", "health_check", "service_status"],
                tags=["system", "monitoring", "health", "status"]
            )
            
            self.register_tool(
                name="system_tools",
                tool_class=ZZDSJSystemTools,
                metadata=system_metadata,
                factory_function=get_zzdsj_system_tools,
                is_singleton=True  # 系统工具使用单例
            )
            
            logger.info("成功注册所有内置工具")
            
        except Exception as e:
            logger.error(f"注册内置工具失败: {str(e)}")

# 全局工具注册中心实例
_tool_registry = None

def get_tool_registry() -> ZZDSJToolRegistry:
    """
    获取全局ZZDSJ工具注册中心实例
    
    返回:
        ZZDSJ工具注册中心实例
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ZZDSJToolRegistry()
    return _tool_registry

def register_tool(
    name: str,
    tool_class: Type,
    metadata: ToolMetadata,
    factory_function: Optional[Callable] = None,
    is_singleton: bool = False
) -> bool:
    """
    注册工具的便捷函数
    
    参数:
        name: 工具名称
        tool_class: 工具类
        metadata: 工具元数据
        factory_function: 工具工厂函数（可选）
        is_singleton: 是否为单例模式
        
    返回:
        是否注册成功
    """
    registry = get_tool_registry()
    return registry.register_tool(name, tool_class, metadata, factory_function, is_singleton)

def get_tool(name: str, **kwargs) -> Optional[Any]:
    """
    获取工具实例的便捷函数
    
    参数:
        name: 工具名称
        **kwargs: 传递给工具构造函数的参数
        
    返回:
        工具实例
    """
    registry = get_tool_registry()
    return registry.get_tool(name, **kwargs)

def list_tools(category: Optional[ToolCategory] = None) -> List[str]:
    """
    列出工具的便捷函数
    
    参数:
        category: 工具分类（可选）
        
    返回:
        工具名称列表
    """
    registry = get_tool_registry()
    if category:
        return registry.get_tools_by_category(category)
    else:
        return registry.list_all_tools()

def search_tools(
    query: str = "",
    category: Optional[ToolCategory] = None,
    status: Optional[ToolStatus] = None,
    tags: Optional[List[str]] = None
) -> List[str]:
    """
    搜索工具的便捷函数
    
    参数:
        query: 搜索查询
        category: 工具分类
        status: 工具状态
        tags: 标签列表
        
    返回:
        匹配的工具名称列表
    """
    registry = get_tool_registry()
    return registry.search_tools(query, category, status, tags)

def get_tools_for_agent(categories: List[ToolCategory], **tool_kwargs) -> List[Any]:
    """
    为Agno Agent获取工具实例列表
    
    参数:
        categories: 需要的工具分类列表
        **tool_kwargs: 传递给工具构造函数的参数
        
    返回:
        工具实例列表
    """
    registry = get_tool_registry()
    tools = []
    
    for category in categories:
        tool_names = registry.get_tools_by_category(category)
        for tool_name in tool_names:
            tool_instance = registry.get_tool(tool_name, **tool_kwargs)
            if tool_instance:
                tools.append(tool_instance)
    
    return tools

# 导出主要组件
__all__ = [
    "ToolCategory",
    "ToolStatus", 
    "ToolMetadata",
    "RegisteredTool",
    "AgnoToolRegistry",
    "get_tool_registry",
    "register_tool",
    "get_tool",
    "list_tools",
    "search_tools",
    "get_tools_for_agent"
] 