"""
工具管理器
处理工具定义、配置和基本管理的核心业务逻辑
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime

from app.repositories.tool import ToolRepository

logger = logging.getLogger(__name__)


class ToolManager:
    """工具管理器"""
    
    def __init__(self, db: Session):
        """初始化工具管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.tool_repository = ToolRepository(db)
    
    async def create_tool(self, 
                         name: str,
                         description: str,
                         tool_type: str,
                         config: Dict[str, Any],
                         category: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         is_active: bool = True,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建工具定义
        
        Args:
            name: 工具名称
            description: 工具描述
            tool_type: 工具类型
            config: 工具配置
            category: 工具分类
            tags: 工具标签
            is_active: 是否激活
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查工具名称是否已存在
            existing_tool = self.tool_repository.get_by_name(name)
            if existing_tool:
                return {
                    "success": False,
                    "error": f"工具名称已存在: {name}",
                    "error_code": "TOOL_NAME_EXISTS"
                }
            
            # 准备工具数据
            tool_data = {
                "name": name,
                "description": description,
                "tool_type": tool_type,
                "config": config,
                "category": category,
                "tags": tags or [],
                "is_active": is_active,
                "metadata": metadata or {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 创建工具
            tool = self.tool_repository.create(tool_data)
            
            logger.info(f"已创建工具: {name} (ID: {tool.id})")
            
            return {
                "success": True,
                "data": {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "config": tool.config,
                    "category": tool.category,
                    "tags": tool.tags,
                    "is_active": tool.is_active,
                    "metadata": tool.metadata,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建工具失败: {str(e)}",
                "error_code": "CREATE_TOOL_FAILED"
            }
    
    async def get_tool(self, tool_id: str) -> Dict[str, Any]:
        """获取工具定义
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            tool = self.tool_repository.get_by_id(tool_id)
            if not tool:
                return {
                    "success": False,
                    "error": "工具不存在",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "config": tool.config,
                    "category": tool.category,
                    "tags": tool.tags,
                    "is_active": tool.is_active,
                    "metadata": tool.metadata,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具失败: {str(e)}",
                "error_code": "GET_TOOL_FAILED"
            }
    
    async def get_tool_by_name(self, name: str) -> Dict[str, Any]:
        """通过名称获取工具定义
        
        Args:
            name: 工具名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            tool = self.tool_repository.get_by_name(name)
            if not tool:
                return {
                    "success": False,
                    "error": "工具不存在",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "config": tool.config,
                    "category": tool.category,
                    "tags": tool.tags,
                    "is_active": tool.is_active,
                    "metadata": tool.metadata,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"通过名称获取工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具失败: {str(e)}",
                "error_code": "GET_TOOL_BY_NAME_FAILED"
            }
    
    async def list_tools(self, 
                        skip: int = 0, 
                        limit: int = 100,
                        category: Optional[str] = None,
                        tool_type: Optional[str] = None,
                        is_active: Optional[bool] = None,
                        tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取工具列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            category: 分类过滤
            tool_type: 类型过滤
            is_active: 激活状态过滤
            tags: 标签过滤
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if category:
                filters["category"] = category
            if tool_type:
                filters["tool_type"] = tool_type
            if is_active is not None:
                filters["is_active"] = is_active
            if tags:
                filters["tags"] = tags
            
            # 获取工具列表
            tools = self.tool_repository.list_with_filters(
                skip=skip, limit=limit, **filters
            )
            
            # 格式化工具列表
            tool_list = []
            for tool in tools:
                tool_list.append({
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "config": tool.config,
                    "category": tool.category,
                    "tags": tool.tags,
                    "is_active": tool.is_active,
                    "metadata": tool.metadata,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                })
            
            return {
                "success": True,
                "data": {
                    "tools": tool_list,
                    "total": len(tool_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具列表失败: {str(e)}",
                "error_code": "LIST_TOOLS_FAILED"
            }
    
    async def update_tool(self, 
                         tool_id: str, 
                         update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新工具定义
        
        Args:
            tool_id: 工具ID
            update_data: 更新数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查工具是否存在
            tool = self.tool_repository.get_by_id(tool_id)
            if not tool:
                return {
                    "success": False,
                    "error": "工具不存在",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            # 如果更新名称，检查是否重复
            if "name" in update_data and update_data["name"] != tool.name:
                existing_tool = self.tool_repository.get_by_name(update_data["name"])
                if existing_tool:
                    return {
                        "success": False,
                        "error": f"工具名称已存在: {update_data['name']}",
                        "error_code": "TOOL_NAME_EXISTS"
                    }
            
            # 添加更新时间
            update_data["updated_at"] = datetime.now()
            
            # 更新工具
            updated_tool = self.tool_repository.update(tool_id, update_data)
            if not updated_tool:
                return {
                    "success": False,
                    "error": "更新工具失败",
                    "error_code": "UPDATE_TOOL_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "id": updated_tool.id,
                    "name": updated_tool.name,
                    "description": updated_tool.description,
                    "tool_type": updated_tool.tool_type,
                    "config": updated_tool.config,
                    "category": updated_tool.category,
                    "tags": updated_tool.tags,
                    "is_active": updated_tool.is_active,
                    "metadata": updated_tool.metadata,
                    "created_at": updated_tool.created_at,
                    "updated_at": updated_tool.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新工具失败: {str(e)}",
                "error_code": "UPDATE_TOOL_FAILED"
            }
    
    async def delete_tool(self, tool_id: str) -> Dict[str, Any]:
        """删除工具定义
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查工具是否存在
            tool = self.tool_repository.get_by_id(tool_id)
            if not tool:
                return {
                    "success": False,
                    "error": "工具不存在",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            # 检查工具是否被使用中
            # 这里应该添加检查工具是否在执行中的逻辑
            
            # 删除工具
            success = self.tool_repository.delete(tool_id)
            if not success:
                return {
                    "success": False,
                    "error": "删除工具失败",
                    "error_code": "DELETE_TOOL_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "message": "工具已成功删除",
                    "tool_id": tool_id
                }
            }
            
        except Exception as e:
            logger.error(f"删除工具时出错: {str(e)}")
            return {
                "success": False,
                "error": f"删除工具失败: {str(e)}",
                "error_code": "DELETE_TOOL_FAILED"
            }
    
    async def validate_tool_config(self, 
                                  tool_type: str, 
                                  config: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具配置
        
        Args:
            tool_type: 工具类型
            config: 工具配置
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 这里应该根据工具类型进行配置验证
            # 暂时简单验证必要字段
            validation_errors = []
            
            if not config:
                validation_errors.append("配置不能为空")
            
            # 根据工具类型进行特定验证
            if tool_type == "api":
                if not config.get("url"):
                    validation_errors.append("API工具必须指定URL")
                if not config.get("method"):
                    validation_errors.append("API工具必须指定HTTP方法")
                    
            elif tool_type == "script":
                if not config.get("script_path") and not config.get("script_content"):
                    validation_errors.append("脚本工具必须指定脚本路径或内容")
                    
            elif tool_type == "database":
                if not config.get("connection_string"):
                    validation_errors.append("数据库工具必须指定连接字符串")
            
            if validation_errors:
                return {
                    "success": False,
                    "error": "配置验证失败",
                    "error_code": "CONFIG_VALIDATION_FAILED",
                    "validation_errors": validation_errors
                }
            
            return {
                "success": True,
                "data": {
                    "message": "配置验证通过",
                    "validated_config": config
                }
            }
            
        except Exception as e:
            logger.error(f"验证工具配置时出错: {str(e)}")
            return {
                "success": False,
                "error": f"配置验证失败: {str(e)}",
                "error_code": "CONFIG_VALIDATION_ERROR"
            }
    
    async def get_tool_categories(self) -> Dict[str, Any]:
        """获取所有工具分类
        
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            categories = self.tool_repository.get_all_categories()
            
            return {
                "success": True,
                "data": {
                    "categories": categories,
                    "total": len(categories)
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具分类时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具分类失败: {str(e)}",
                "error_code": "GET_CATEGORIES_FAILED"
            }
    
    async def get_tool_types(self) -> Dict[str, Any]:
        """获取所有工具类型
        
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            tool_types = self.tool_repository.get_all_types()
            
            return {
                "success": True,
                "data": {
                    "tool_types": tool_types,
                    "total": len(tool_types)
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具类型时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具类型失败: {str(e)}",
                "error_code": "GET_TOOL_TYPES_FAILED"
            } 