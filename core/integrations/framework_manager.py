"""
核心业务逻辑层 - 通用框架集成管理
处理通用框架集成的核心业务逻辑，包括配置管理、框架协调、服务发现等
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime


class FrameworkIntegrationManager:
    """通用框架集成管理器 - 核心业务逻辑层"""
    
    def __init__(self, db: Session):
        """初始化框架集成管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def get_framework_status(self, framework_name: str) -> Dict[str, Any]:
        """获取框架状态
        
        Args:
            framework_name: 框架名称
            
        Returns:
            Dict[str, Any]: 框架状态信息
        """
        try:
            # 这里可以根据具体框架实现状态检查逻辑
            framework_configs = await self._get_framework_configs()
            
            if framework_name not in framework_configs:
                return {
                    "success": False,
                    "error": f"未知的框架: {framework_name}"
                }
            
            config = framework_configs[framework_name]
            
            return {
                "success": True,
                "data": {
                    "framework_name": framework_name,
                    "status": "active",
                    "version": config.get("version", "unknown"),
                    "description": config.get("description", ""),
                    "capabilities": config.get("capabilities", []),
                    "dependencies": config.get("dependencies", []),
                    "last_check": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取框架状态失败: {str(e)}"
            }
    
    async def list_available_frameworks(self) -> Dict[str, Any]:
        """获取可用框架列表
        
        Returns:
            Dict[str, Any]: 可用框架列表
        """
        try:
            framework_configs = await self._get_framework_configs()
            
            frameworks = []
            for name, config in framework_configs.items():
                framework_info = {
                    "name": name,
                    "version": config.get("version", "unknown"),
                    "description": config.get("description", ""),
                    "status": "available",
                    "capabilities": config.get("capabilities", [])
                }
                frameworks.append(framework_info)
            
            return {
                "success": True,
                "data": {
                    "frameworks": frameworks,
                    "total": len(frameworks)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取可用框架列表失败: {str(e)}"
            }
    
    async def validate_framework_config(
        self,
        framework_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证框架配置
        
        Args:
            framework_name: 框架名称
            config: 配置信息
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 获取框架规范
            framework_configs = await self._get_framework_configs()
            
            if framework_name not in framework_configs:
                return {
                    "success": False,
                    "error": f"不支持的框架: {framework_name}"
                }
            
            framework_spec = framework_configs[framework_name]
            required_fields = framework_spec.get("required_config_fields", [])
            
            # 检查必需字段
            missing_fields = []
            for field in required_fields:
                if field not in config:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    "success": False,
                    "error": f"缺少必需的配置字段: {', '.join(missing_fields)}"
                }
            
            # 验证字段类型
            field_types = framework_spec.get("config_field_types", {})
            type_errors = []
            
            for field, expected_type in field_types.items():
                if field in config:
                    actual_value = config[field]
                    if expected_type == "string" and not isinstance(actual_value, str):
                        type_errors.append(f"{field} 应为字符串类型")
                    elif expected_type == "dict" and not isinstance(actual_value, dict):
                        type_errors.append(f"{field} 应为字典类型")
                    elif expected_type == "list" and not isinstance(actual_value, list):
                        type_errors.append(f"{field} 应为列表类型")
                    elif expected_type == "int" and not isinstance(actual_value, int):
                        type_errors.append(f"{field} 应为整数类型")
                    elif expected_type == "bool" and not isinstance(actual_value, bool):
                        type_errors.append(f"{field} 应为布尔类型")
            
            if type_errors:
                return {
                    "success": False,
                    "error": f"配置类型错误: {'; '.join(type_errors)}"
                }
            
            return {
                "success": True,
                "data": {
                    "framework_name": framework_name,
                    "config_valid": True,
                    "validated_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"验证框架配置失败: {str(e)}"
            }
    
    async def get_framework_capabilities(self, framework_name: str) -> Dict[str, Any]:
        """获取框架能力
        
        Args:
            framework_name: 框架名称
            
        Returns:
            Dict[str, Any]: 框架能力信息
        """
        try:
            framework_configs = await self._get_framework_configs()
            
            if framework_name not in framework_configs:
                return {
                    "success": False,
                    "error": f"未知的框架: {framework_name}"
                }
            
            config = framework_configs[framework_name]
            
            return {
                "success": True,
                "data": {
                    "framework_name": framework_name,
                    "capabilities": config.get("capabilities", []),
                    "supported_operations": config.get("supported_operations", []),
                    "integration_points": config.get("integration_points", []),
                    "dependencies": config.get("dependencies", [])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取框架能力失败: {str(e)}"
            }
    
    # ============ 私有辅助方法 ============
    
    async def _get_framework_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取框架配置规范
        
        Returns:
            Dict[str, Dict[str, Any]]: 框架配置规范
        """
        # 这里定义各个框架的配置规范
        return {
            "llamaindex": {
                "version": "0.10.0",
                "description": "LlamaIndex框架集成",
                "capabilities": ["indexing", "retrieval", "embedding"],
                "required_config_fields": ["service_type", "config"],
                "config_field_types": {
                    "service_type": "string",
                    "config": "dict",
                    "description": "string",
                    "is_active": "bool"
                },
                "supported_operations": ["create_index", "query", "embed"],
                "integration_points": ["knowledge_base", "retrieval"],
                "dependencies": ["llama-index"]
            },
            "lightrag": {
                "version": "0.1.0",
                "description": "LightRAG图谱框架集成",
                "capabilities": ["graph_construction", "relation_extraction", "graph_query"],
                "required_config_fields": ["working_dir", "llm_model", "embedding_model"],
                "config_field_types": {
                    "working_dir": "string",
                    "llm_model": "dict",
                    "embedding_model": "dict",
                    "graph_config": "dict"
                },
                "supported_operations": ["build_graph", "query_graph", "extract_relations"],
                "integration_points": ["knowledge_graph", "relation_mining"],
                "dependencies": ["lightrag"]
            },
            "mcp": {
                "version": "1.0.0",
                "description": "Model Context Protocol集成",
                "capabilities": ["protocol_communication", "service_discovery", "tool_execution"],
                "required_config_fields": ["server_name", "server_type", "connection_config"],
                "config_field_types": {
                    "server_name": "string",
                    "server_type": "string",
                    "connection_config": "dict",
                    "auth_config": "dict"
                },
                "supported_operations": ["connect", "discover_tools", "execute_tool"],
                "integration_points": ["tool_execution", "service_communication"],
                "dependencies": ["mcp-client"]
            },
            "owl": {
                "version": "2.0.0",
                "description": "OWL框架集成",
                "capabilities": ["agent_framework", "workflow_engine", "plugin_system"],
                "required_config_fields": ["framework_type", "config"],
                "config_field_types": {
                    "framework_type": "string",
                    "config": "dict",
                    "description": "string"
                },
                "supported_operations": ["register_agent", "run_workflow", "load_plugin"],
                "integration_points": ["agent_execution", "workflow_management"],
                "dependencies": ["owl-framework"]
            }
        } 