"""
Agno动态工具模块：与ZZDSJ统一工具注册表集成
基于系统配置和权限动态获取和创建工具，去除硬编码依赖
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime

from app.services.tools.tool_service import ToolService
from app.repositories.tool_repository import ToolRepository
from app.utils.core.database import get_db

logger = logging.getLogger(__name__)

class DynamicZZDSJToolsManager:
    """ZZDSJ动态工具管理器 - 基于系统工具注册表"""
    
    def __init__(self, user_id: Optional[str] = None, db_session=None):
        """
        初始化动态工具管理器
        
        Args:
            user_id: 用户ID，用于权限检查
            db_session: 数据库会话
        """
        self.user_id = user_id
        self.db = db_session or next(get_db())
        self.tool_service = ToolService(self.db)
        self.tool_repository = ToolRepository(self.db)
        
        # 工具实例缓存
        self._tool_cache: Dict[str, Any] = {}
        
    async def get_available_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取用户可用的工具列表
        
        Args:
            category: 工具类别过滤
            
        Returns:
            可用工具列表
        """
        try:
            if self.user_id:
                # 获取用户有权限的工具
                tools = await self.tool_service.get_user_available_tools(self.user_id)
            else:
                # 系统级别，获取所有启用的工具
                tools = await self.tool_repository.get_enabled_tools()
            
            # 按类别过滤
            if category:
                tools = [tool for tool in tools if tool.category == category]
            
            # 转换为工具描述格式
            tool_list = []
            for tool in tools:
                tool_info = {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "framework": tool.framework,
                    "is_enabled": tool.is_enabled,
                    "config": tool.config
                }
                tool_list.append(tool_info)
            
            logger.info(f"获取到 {len(tool_list)} 个可用工具")
            return tool_list
            
        except Exception as e:
            logger.error(f"获取可用工具失败: {str(e)}")
            return []
    
    async def create_tool_instance(self, tool_id: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        创建工具实例
        
        Args:
            tool_id: 工具ID
            params: 工具参数
            
        Returns:
            工具实例
        """
        try:
            # 检查缓存
            cache_key = f"{tool_id}_{hash(str(params))}"
            if cache_key in self._tool_cache:
                return self._tool_cache[cache_key]
            
            # 获取工具定义
            tool_definition = await self.tool_repository.get_tool_by_id(tool_id)
            if not tool_definition:
                logger.warning(f"工具 {tool_id} 不存在")
                return None
            
            # 检查用户权限
            if self.user_id:
                has_permission = await self.tool_service.check_tool_permission(
                    self.user_id, tool_id
                )
                if not has_permission:
                    logger.warning(f"用户 {self.user_id} 没有工具 {tool_id} 的使用权限")
                    return None
            
            # 根据框架创建工具实例
            tool_instance = await self._create_framework_tool(tool_definition, params or {})
            
            if tool_instance:
                # 缓存工具实例
                self._tool_cache[cache_key] = tool_instance
                logger.info(f"成功创建工具实例: {tool_definition.name}")
            
            return tool_instance
            
        except Exception as e:
            logger.error(f"创建工具实例 {tool_id} 失败: {str(e)}")
            return None
    
    async def _create_framework_tool(self, tool_definition, params: Dict[str, Any]) -> Optional[Any]:
        """根据框架创建工具实例"""
        framework = tool_definition.framework
        
        try:
            if framework == 'agno':
                return await self._create_agno_tool(tool_definition, params)
            elif framework == 'zzdsj':
                return await self._create_zzdsj_tool(tool_definition, params)
            else:
                # 其他框架工具，创建适配器包装
                return await self._create_adapter_tool(tool_definition, params)
                
        except Exception as e:
            logger.error(f"创建 {framework} 框架工具失败: {str(e)}")
            return None
    
    async def _create_agno_tool(self, tool_definition, params: Dict[str, Any]) -> Optional[Any]:
        """创建Agno原生工具"""
        try:
            # 动态导入工具类
            import importlib
            
            module_path, class_name = tool_definition.class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            
            # 合并配置参数
            init_params = tool_definition.config.copy()
            init_params.update(params)
            
            # 创建工具实例
            return tool_class(**init_params)
            
        except Exception as e:
            logger.error(f"创建Agno工具失败: {str(e)}")
            return None
    
    async def _create_zzdsj_tool(self, tool_definition, params: Dict[str, Any]) -> Optional[Any]:
        """创建ZZDSJ自定义工具"""
        try:
            # 根据工具类别创建相应的工具
            category = tool_definition.category
            
            if category == 'knowledge':
                return await self._create_knowledge_tool(tool_definition, params)
            elif category == 'file':
                return await self._create_file_tool(tool_definition, params)
            elif category == 'system':
                return await self._create_system_tool(tool_definition, params)
            else:
                logger.warning(f"未知的ZZDSJ工具类别: {category}")
                return None
                
        except Exception as e:
            logger.error(f"创建ZZDSJ工具失败: {str(e)}")
            return None
    
    async def _create_knowledge_tool(self, tool_definition, params: Dict[str, Any]) -> Optional[Any]:
        """创建知识库工具"""
        class DynamicKnowledgeTool:
            def __init__(self, tool_def, user_params):
                self.tool_def = tool_def
                self.user_params = user_params
                self.name = tool_def.name
                self.description = tool_def.description
            
            async def search_documents(self, query: str, kb_id: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
                """在知识库中搜索文档"""
                try:
                    from app.services.knowledge.knowledge_service import KnowledgeService
                    
                    knowledge_service = KnowledgeService()
                    
                    # 使用提供的kb_id或配置中的默认值
                    target_kb_id = kb_id or self.user_params.get('kb_id') or self.tool_def.config.get('default_kb_id')
                    
                    if not target_kb_id:
                        return {"error": "未提供知识库ID", "results": [], "count": 0}
                    
                    # 执行搜索
                    results = await knowledge_service.search_documents(
                        kb_id=target_kb_id,
                        query=query,
                        top_k=top_k
                    )
                    
                    return {
                        "results": results,
                        "count": len(results),
                        "kb_id": target_kb_id,
                        "query": query
                    }
                    
                except Exception as e:
                    return {"error": f"搜索失败: {str(e)}", "results": [], "count": 0}
            
            async def __call__(self, *args, **kwargs):
                """工具调用入口"""
                if len(args) > 0:
                    query = args[0]
                    return await self.search_documents(query, **kwargs)
                elif 'query' in kwargs:
                    return await self.search_documents(**kwargs)
                else:
                    return {"error": "缺少查询参数", "results": [], "count": 0}
        
        return DynamicKnowledgeTool(tool_definition, params)
    
    async def _create_file_tool(self, tool_definition, params: Dict[str, Any]) -> Optional[Any]:
        """创建文件管理工具"""
        class DynamicFileTool:
            def __init__(self, tool_def, user_params):
                self.tool_def = tool_def
                self.user_params = user_params
                self.name = tool_def.name
                self.description = tool_def.description
                self.upload_base_path = user_params.get('upload_base_path', 'uploads/')
            
            async def list_files(self, directory: str = "", file_type: Optional[str] = None) -> Dict[str, Any]:
                """列出目录中的文件"""
                try:
                    import os
                    
                    full_path = os.path.join(self.upload_base_path, directory)
                    
                    if not os.path.exists(full_path):
                        return {"error": f"目录不存在: {full_path}", "files": []}
                    
                    files = []
                    for item in os.listdir(full_path):
                        item_path = os.path.join(full_path, item)
                        
                        if os.path.isfile(item_path):
                            file_ext = os.path.splitext(item)[1].lower()
                            
                            # 文件类型过滤
                            if file_type and file_ext != file_type.lower():
                                continue
                            
                            file_stat = os.stat(item_path)
                            files.append({
                                "name": item,
                                "path": os.path.join(directory, item),
                                "extension": file_ext,
                                "size": file_stat.st_size,
                                "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                            })
                    
                    return {
                        "files": sorted(files, key=lambda x: x["modified_at"], reverse=True),
                        "count": len(files),
                        "directory": directory
                    }
                    
                except Exception as e:
                    return {"error": f"文件列表获取失败: {str(e)}", "files": []}
            
            async def __call__(self, *args, **kwargs):
                """工具调用入口"""
                return await self.list_files(**kwargs)
        
        return DynamicFileTool(tool_definition, params)
    
    async def _create_system_tool(self, tool_definition, params: Dict[str, Any]) -> Optional[Any]:
        """创建系统工具"""
        class DynamicSystemTool:
            def __init__(self, tool_def, user_params):
                self.tool_def = tool_def
                self.user_params = user_params
                self.name = tool_def.name
                self.description = tool_def.description
            
            async def get_system_status(self) -> Dict[str, Any]:
                """获取系统状态信息"""
                try:
                    # 返回基本的系统状态
                    return {
                        "status": "healthy",
                        "timestamp": datetime.now().isoformat(),
                        "system": "ZZDSJ Backend API",
                        "version": "1.0.0"
                    }
                    
                except Exception as e:
                    return {"error": f"系统状态获取失败: {str(e)}"}
            
            async def __call__(self, *args, **kwargs):
                """工具调用入口"""
                return await self.get_system_status()
        
        return DynamicSystemTool(tool_definition, params)
    
    async def _create_adapter_tool(self, tool_definition, params: Dict[str, Any]) -> Optional[Any]:
        """创建其他框架工具的适配器"""
        try:
            from app.adapters.tool_adapter import UniversalToolAdapter
            
            adapter = UniversalToolAdapter()
            tool_instance = await adapter.create_tool_instance(
                tool_definition.id, params, tool_definition.framework
            )
            
            # 包装为Agno兼容格式
            return self._wrap_for_agno(tool_instance, tool_definition)
            
        except Exception as e:
            logger.error(f"创建适配器工具失败: {str(e)}")
            return None
    
    def _wrap_for_agno(self, tool_instance, tool_definition):
        """包装工具为Agno兼容格式"""
        class AgnoCompatibleTool:
            def __init__(self, tool_instance, tool_def):
                self.tool_instance = tool_instance
                self.tool_def = tool_def
                self.name = tool_def.name
                self.description = tool_def.description
            
            async def __call__(self, *args, **kwargs):
                """Agno工具调用接口"""
                if hasattr(self.tool_instance, 'execute'):
                    return await self.tool_instance.execute(*args, **kwargs)
                elif hasattr(self.tool_instance, '__call__'):
                    return await self.tool_instance(*args, **kwargs)
                else:
                    return {"error": "工具不支持调用"}
        
        return AgnoCompatibleTool(tool_instance, tool_definition)

class DynamicAgnoToolRegistry:
    """Agno动态工具注册表"""
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.tools_manager = DynamicZZDSJToolsManager(user_id)
        self._registered_tools: Dict[str, Any] = {}
    
    async def register_user_tools(self) -> List[Any]:
        """注册用户可用的工具"""
        try:
            available_tools = await self.tools_manager.get_available_tools()
            registered_tools = []
            
            for tool_info in available_tools:
                tool_instance = await self.tools_manager.create_tool_instance(tool_info['id'])
                if tool_instance:
                    self._registered_tools[tool_info['id']] = tool_instance
                    registered_tools.append(tool_instance)
            
            logger.info(f"成功注册 {len(registered_tools)} 个工具")
            return registered_tools
            
        except Exception as e:
            logger.error(f"注册用户工具失败: {str(e)}")
            return []
    
    async def get_tools_by_category(self, category: str) -> List[Any]:
        """按类别获取工具"""
        try:
            category_tools = await self.tools_manager.get_available_tools(category)
            tools = []
            
            for tool_info in category_tools:
                tool_instance = await self.tools_manager.create_tool_instance(tool_info['id'])
                if tool_instance:
                    tools.append(tool_instance)
            
            return tools
            
        except Exception as e:
            logger.error(f"获取类别 {category} 工具失败: {str(e)}")
            return []
    
    def get_registered_tool(self, tool_id: str) -> Optional[Any]:
        """获取已注册的工具"""
        return self._registered_tools.get(tool_id)

# 全局工具管理器实例
_global_tools_manager: Optional[DynamicZZDSJToolsManager] = None

def get_tools_manager(user_id: Optional[str] = None) -> DynamicZZDSJToolsManager:
    """获取工具管理器实例"""
    return DynamicZZDSJToolsManager(user_id)

async def get_user_tools(user_id: str) -> List[Any]:
    """获取用户可用的工具列表"""
    registry = DynamicAgnoToolRegistry(user_id)
    return await registry.register_user_tools()

async def get_tools_by_category(category: str, user_id: Optional[str] = None) -> List[Any]:
    """按类别获取工具"""
    registry = DynamicAgnoToolRegistry(user_id)
    return await registry.get_tools_by_category(category)

# 便利函数 - 兼容原有接口
async def get_zzdsj_knowledge_tools(user_id: Optional[str] = None, kb_id: Optional[str] = None) -> List[Any]:
    """获取ZZDSJ知识库工具"""
    return await get_tools_by_category("knowledge", user_id)

async def get_zzdsj_file_tools(user_id: Optional[str] = None, upload_base_path: str = "uploads/") -> List[Any]:
    """获取ZZDSJ文件管理工具"""
    return await get_tools_by_category("file", user_id)

async def get_zzdsj_system_tools(user_id: Optional[str] = None) -> List[Any]:
    """获取ZZDSJ系统工具"""
    return await get_tools_by_category("system", user_id)

async def create_zzdsj_agent_tools(user_id: Optional[str] = None) -> Dict[str, List[Any]]:
    """为Agno代理创建ZZDSJ工具集合"""
    try:
        registry = DynamicAgnoToolRegistry(user_id)
        
        tools_by_category = {
            "knowledge": await registry.get_tools_by_category("knowledge"),
            "files": await registry.get_tools_by_category("file"),
            "system": await registry.get_tools_by_category("system"),
            "search": await registry.get_tools_by_category("search"),
            "reasoning": await registry.get_tools_by_category("reasoning")
        }
        
        return tools_by_category
        
    except Exception as e:
        logger.error(f"创建Agent工具集合失败: {str(e)}")
        return {}

# 导出主要组件
__all__ = [
    "DynamicZZDSJToolsManager",
    "DynamicAgnoToolRegistry",
    "get_tools_manager",
    "get_user_tools",
    "get_tools_by_category",
    "get_zzdsj_knowledge_tools",
    "get_zzdsj_file_tools", 
    "get_zzdsj_system_tools",
    "create_zzdsj_agent_tools"
]
