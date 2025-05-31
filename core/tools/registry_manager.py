"""
工具注册管理器
处理工具注册、发现和版本管理的核心业务逻辑
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime
from packaging import version

from app.repositories.tool_registry_repository import ToolRegistryRepository
from app.repositories.tool_repository import ToolRepository
from .tool_manager import ToolManager

logger = logging.getLogger(__name__)


class RegistryManager:
    """工具注册管理器"""
    
    def __init__(self, db: Session):
        """初始化注册管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.registry_repository = ToolRegistryRepository(db)
        self.tool_manager = ToolManager(db)
    
    async def register_tool(self,
                           tool_name: str,
                           tool_version: str,
                           tool_config: Dict[str, Any],
                           provider: str,
                           category: Optional[str] = None,
                           description: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """注册工具
        
        Args:
            tool_name: 工具名称
            tool_version: 工具版本
            tool_config: 工具配置
            provider: 提供者
            category: 工具分类
            description: 工具描述
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证版本格式
            try:
                version.parse(tool_version)
            except Exception:
                return {
                    "success": False,
                    "error": f"无效的版本格式: {tool_version}",
                    "error_code": "INVALID_VERSION_FORMAT"
                }
            
            # 检查工具是否已注册
            existing_tool = self.registry_repository.get_tool_by_name_and_version(
                tool_name, tool_version
            )
            if existing_tool:
                return {
                    "success": False,
                    "error": f"工具版本已存在: {tool_name} v{tool_version}",
                    "error_code": "TOOL_VERSION_EXISTS"
                }
            
            # 验证工具配置
            validation_result = await self._validate_tool_config(tool_config)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "工具配置验证失败",
                    "error_code": "CONFIG_VALIDATION_FAILED",
                    "validation_errors": validation_result["errors"]
                }
            
            # 生成注册ID
            registry_id = str(uuid.uuid4())
            
            # 准备注册数据
            registry_data = {
                "registry_id": registry_id,
                "tool_name": tool_name,
                "tool_version": tool_version,
                "tool_config": tool_config,
                "provider": provider,
                "category": category,
                "description": description or "",
                "metadata": metadata or {},
                "status": "active",
                "registered_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 创建注册记录
            registry_entry = self.registry_repository.create(registry_data)
            
            # 检查是否需要创建或更新工具定义
            tool_result = await self.tool_manager.get_tool_by_name(tool_name)
            if not tool_result["success"]:
                # 创建新工具定义
                await self.tool_manager.create_tool(
                    name=tool_name,
                    description=description or "",
                    tool_type=tool_config.get("type", "unknown"),
                    config=tool_config,
                    category=category,
                    metadata={
                        "registry_id": registry_id,
                        "provider": provider,
                        "version": tool_version
                    }
                )
            else:
                # 更新现有工具定义
                tool_data = tool_result["data"]
                if self._is_newer_version(tool_version, tool_data.get("metadata", {}).get("version", "0.0.0")):
                    await self.tool_manager.update_tool(
                        tool_data["id"],
                        {
                            "config": tool_config,
                            "metadata": {
                                **tool_data.get("metadata", {}),
                                "registry_id": registry_id,
                                "provider": provider,
                                "version": tool_version
                            }
                        }
                    )
            
            logger.info(f"已注册工具: {tool_name} v{tool_version} by {provider}")
            
            return {
                "success": True,
                "data": {
                    "registry_id": registry_entry.registry_id,
                    "tool_name": registry_entry.tool_name,
                    "tool_version": registry_entry.tool_version,
                    "provider": registry_entry.provider,
                    "category": registry_entry.category,
                    "status": registry_entry.status,
                    "registered_at": registry_entry.registered_at,
                    "updated_at": registry_entry.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"注册工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"注册工具失败: {str(e)}",
                "error_code": "REGISTER_TOOL_FAILED"
            }
    
    async def unregister_tool(self, registry_id: str) -> Dict[str, Any]:
        """注销工具
        
        Args:
            registry_id: 注册ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取注册信息
            registry_entry = self.registry_repository.get_by_id(registry_id)
            if not registry_entry:
                return {
                    "success": False,
                    "error": "注册记录不存在",
                    "error_code": "REGISTRY_NOT_FOUND"
                }
            
            # 更新状态为已注销
            update_data = {
                "status": "unregistered",
                "updated_at": datetime.now()
            }
            
            updated_entry = self.registry_repository.update(registry_id, update_data)
            if not updated_entry:
                return {
                    "success": False,
                    "error": "注销工具失败",
                    "error_code": "UNREGISTER_TOOL_FAILED"
                }
            
            logger.info(f"已注销工具: {registry_entry.tool_name} v{registry_entry.tool_version}")
            
            return {
                "success": True,
                "data": {
                    "registry_id": registry_id,
                    "tool_name": registry_entry.tool_name,
                    "tool_version": registry_entry.tool_version,
                    "status": "unregistered"
                }
            }
            
        except Exception as e:
            logger.error(f"注销工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"注销工具失败: {str(e)}",
                "error_code": "UNREGISTER_TOOL_FAILED"
            }
    
    async def get_registered_tool(self, registry_id: str) -> Dict[str, Any]:
        """获取注册工具详情
        
        Args:
            registry_id: 注册ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            registry_entry = self.registry_repository.get_by_id(registry_id)
            if not registry_entry:
                return {
                    "success": False,
                    "error": "注册记录不存在",
                    "error_code": "REGISTRY_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "registry_id": registry_entry.registry_id,
                    "tool_name": registry_entry.tool_name,
                    "tool_version": registry_entry.tool_version,
                    "tool_config": registry_entry.tool_config,
                    "provider": registry_entry.provider,
                    "category": registry_entry.category,
                    "description": registry_entry.description,
                    "metadata": registry_entry.metadata,
                    "status": registry_entry.status,
                    "registered_at": registry_entry.registered_at,
                    "updated_at": registry_entry.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取注册工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取注册工具失败: {str(e)}",
                "error_code": "GET_REGISTERED_TOOL_FAILED"
            }
    
    async def list_registered_tools(self,
                                   skip: int = 0,
                                   limit: int = 100,
                                   tool_name: Optional[str] = None,
                                   provider: Optional[str] = None,
                                   category: Optional[str] = None,
                                   status: Optional[str] = None) -> Dict[str, Any]:
        """获取注册工具列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            tool_name: 工具名称过滤
            provider: 提供者过滤
            category: 分类过滤
            status: 状态过滤
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if tool_name:
                filters["tool_name"] = tool_name
            if provider:
                filters["provider"] = provider
            if category:
                filters["category"] = category
            if status:
                filters["status"] = status
            
            # 获取注册工具列表
            registry_entries = self.registry_repository.list_with_filters(
                skip=skip, limit=limit, **filters
            )
            
            # 格式化注册工具列表
            tools_list = []
            for entry in registry_entries:
                tools_list.append({
                    "registry_id": entry.registry_id,
                    "tool_name": entry.tool_name,
                    "tool_version": entry.tool_version,
                    "provider": entry.provider,
                    "category": entry.category,
                    "description": entry.description,
                    "status": entry.status,
                    "registered_at": entry.registered_at,
                    "updated_at": entry.updated_at
                })
            
            return {
                "success": True,
                "data": {
                    "tools": tools_list,
                    "total": len(tools_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取注册工具列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取注册工具列表失败: {str(e)}",
                "error_code": "LIST_REGISTERED_TOOLS_FAILED"
            }
    
    async def get_tool_versions(self, tool_name: str) -> Dict[str, Any]:
        """获取工具的所有版本
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            versions = self.registry_repository.get_tool_versions(tool_name)
            
            # 按版本号排序
            sorted_versions = sorted(
                versions,
                key=lambda x: version.parse(x["tool_version"]),
                reverse=True
            )
            
            return {
                "success": True,
                "data": {
                    "tool_name": tool_name,
                    "versions": sorted_versions,
                    "total": len(sorted_versions)
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具版本时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具版本失败: {str(e)}",
                "error_code": "GET_TOOL_VERSIONS_FAILED"
            }
    
    async def get_latest_version(self, tool_name: str) -> Dict[str, Any]:
        """获取工具的最新版本
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            versions_result = await self.get_tool_versions(tool_name)
            if not versions_result["success"]:
                return versions_result
            
            versions = versions_result["data"]["versions"]
            if not versions:
                return {
                    "success": False,
                    "error": f"未找到工具: {tool_name}",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            # 第一个版本是最新版本（已排序）
            latest_version = versions[0]
            
            return {
                "success": True,
                "data": latest_version
            }
            
        except Exception as e:
            logger.error(f"获取最新版本时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取最新版本失败: {str(e)}",
                "error_code": "GET_LATEST_VERSION_FAILED"
            }
    
    async def discover_tools(self,
                            category: Optional[str] = None,
                            provider: Optional[str] = None,
                            search_query: Optional[str] = None) -> Dict[str, Any]:
        """发现工具
        
        Args:
            category: 分类过滤
            provider: 提供者过滤
            search_query: 搜索查询
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建搜索条件
            search_filters = {"status": "active"}
            if category:
                search_filters["category"] = category
            if provider:
                search_filters["provider"] = provider
            
            # 获取活跃的注册工具
            registry_entries = self.registry_repository.search_tools(
                search_query=search_query,
                **search_filters
            )
            
            # 按工具名称分组，保留最新版本
            tools_map = {}
            for entry in registry_entries:
                tool_name = entry.tool_name
                if tool_name not in tools_map:
                    tools_map[tool_name] = entry
                else:
                    # 比较版本，保留更新的版本
                    if self._is_newer_version(entry.tool_version, tools_map[tool_name].tool_version):
                        tools_map[tool_name] = entry
            
            # 格式化发现的工具
            discovered_tools = []
            for entry in tools_map.values():
                discovered_tools.append({
                    "tool_name": entry.tool_name,
                    "latest_version": entry.tool_version,
                    "provider": entry.provider,
                    "category": entry.category,
                    "description": entry.description,
                    "registry_id": entry.registry_id
                })
            
            return {
                "success": True,
                "data": {
                    "tools": discovered_tools,
                    "total": len(discovered_tools)
                }
            }
            
        except Exception as e:
            logger.error(f"发现工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"发现工具失败: {str(e)}",
                "error_code": "DISCOVER_TOOLS_FAILED"
            }
    
    async def update_tool_metadata(self,
                                  registry_id: str,
                                  metadata: Dict[str, Any]) -> Dict[str, Any]:
        """更新工具元数据
        
        Args:
            registry_id: 注册ID
            metadata: 新的元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取现有注册信息
            registry_entry = self.registry_repository.get_by_id(registry_id)
            if not registry_entry:
                return {
                    "success": False,
                    "error": "注册记录不存在",
                    "error_code": "REGISTRY_NOT_FOUND"
                }
            
            # 合并元数据
            current_metadata = registry_entry.metadata or {}
            updated_metadata = {**current_metadata, **metadata}
            
            # 更新注册记录
            update_data = {
                "metadata": updated_metadata,
                "updated_at": datetime.now()
            }
            
            updated_entry = self.registry_repository.update(registry_id, update_data)
            if not updated_entry:
                return {
                    "success": False,
                    "error": "更新元数据失败",
                    "error_code": "UPDATE_METADATA_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "registry_id": registry_id,
                    "metadata": updated_metadata
                }
            }
            
        except Exception as e:
            logger.error(f"更新工具元数据时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新工具元数据失败: {str(e)}",
                "error_code": "UPDATE_TOOL_METADATA_FAILED"
            }
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """比较版本号
        
        Args:
            version1: 版本1
            version2: 版本2
            
        Returns:
            bool: version1是否比version2新
        """
        try:
            return version.parse(version1) > version.parse(version2)
        except Exception:
            # 如果版本格式无效，使用字符串比较
            return version1 > version2
    
    async def _validate_tool_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具配置
        
        Args:
            config: 工具配置
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        errors = []
        
        # 基本验证
        if not config:
            errors.append("配置不能为空")
            return {"valid": False, "errors": errors}
        
        # 必需字段验证
        required_fields = ["type", "name"]
        for field in required_fields:
            if field not in config:
                errors.append(f"缺少必需字段: {field}")
        
        # 类型特定验证
        tool_type = config.get("type")
        if tool_type == "api":
            if not config.get("endpoint"):
                errors.append("API工具必须指定endpoint")
        elif tool_type == "script":
            if not config.get("script") and not config.get("script_path"):
                errors.append("脚本工具必须指定script或script_path")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        } 