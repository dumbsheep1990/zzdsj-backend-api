"""
向量数据库模板加载器
从YAML配置文件加载模板配置并转换为Pydantic模型
"""

import yaml
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.schemas.vector_store import (
    StandardCollectionDefinition,
    VectorStoreConfig,
    CollectionSchema,
    FieldSchema,
    IndexParameters,
    PartitionConfig,
    DataType,
    IndexType,
    MetricType
)


class VectorStoreTemplateLoader:
    """向量存储模板加载器"""
    
    def __init__(self, template_file: Optional[str] = None):
        """
        初始化模板加载器
        
        参数:
            template_file: 模板文件路径，如果不指定则使用默认路径
        """
        if template_file is None:
            # 使用默认模板文件路径
            current_dir = Path(__file__).parent.parent.parent.parent
            template_file = current_dir / "config" / "vector_store_templates.yaml"
        
        self.template_file = Path(template_file)
        self.templates = {}
        self.load_templates()
    
    def load_templates(self) -> None:
        """加载模板配置"""
        try:
            if not self.template_file.exists():
                raise FileNotFoundError(f"模板文件不存在: {self.template_file}")
            
            with open(self.template_file, 'r', encoding='utf-8') as f:
                self.templates = yaml.safe_load(f)
            
        except Exception as e:
            raise RuntimeError(f"加载模板文件失败: {str(e)}")
    
    def get_base_config(self, config_name: str = "default") -> VectorStoreConfig:
        """
        获取基础配置
        
        参数:
            config_name: 配置名称
            
        返回:
            向量存储配置
        """
        base_configs = self.templates.get("base_configs", {})
        config_data = base_configs.get(config_name, {})
        
        if not config_data:
            raise ValueError(f"未找到基础配置: {config_name}")
        
        # 处理环境变量
        processed_config = self._process_env_vars(config_data)
        
        return VectorStoreConfig(**processed_config)
    
    def get_index_config(self, index_name: str = "balanced") -> IndexParameters:
        """
        获取索引配置
        
        参数:
            index_name: 索引配置名称
            
        返回:
            索引参数配置
        """
        index_templates = self.templates.get("index_templates", {})
        index_data = index_templates.get(index_name, {})
        
        if not index_data:
            raise ValueError(f"未找到索引配置: {index_name}")
        
        return IndexParameters(
            index_type=IndexType(index_data["index_type"]),
            metric_type=MetricType(index_data["metric_type"]),
            params=index_data.get("params", {})
        )
    
    def get_field_template(self, template_name: str) -> List[FieldSchema]:
        """
        获取字段模板
        
        参数:
            template_name: 模板名称
            
        返回:
            字段列表
        """
        field_templates = self.templates.get("field_templates", {})
        field_data = field_templates.get(template_name, [])
        
        if not field_data:
            raise ValueError(f"未找到字段模板: {template_name}")
        
        fields = []
        for field_config in field_data:
            field = FieldSchema(
                name=field_config["name"],
                data_type=DataType(field_config["data_type"]),
                is_primary=field_config.get("is_primary", False),
                auto_id=field_config.get("auto_id", False),
                max_length=field_config.get("max_length"),
                dimension=field_config.get("dimension"),
                description=field_config.get("description"),
                nullable=field_config.get("nullable", True),
                default_value=field_config.get("default_value")
            )
            fields.append(field)
        
        return fields
    
    def get_collection_template(self, template_name: str, **kwargs) -> StandardCollectionDefinition:
        """
        获取集合模板
        
        参数:
            template_name: 模板名称
            **kwargs: 配置覆盖参数
            
        返回:
            标准集合定义
        """
        collection_templates = self.templates.get("collection_templates", {})
        template_data = collection_templates.get(template_name, {})
        
        if not template_data:
            raise ValueError(f"未找到集合模板: {template_name}")
        
        # 处理字段配置
        fields = []
        field_configs = template_data.get("fields", [])
        
        for field_config in field_configs:
            if isinstance(field_config, dict) and "template" in field_config:
                # 引用字段模板
                template_fields = self.get_field_template(field_config["template"])
                fields.extend(template_fields)
            else:
                # 直接定义的字段
                field = FieldSchema(
                    name=field_config["name"],
                    data_type=DataType(field_config["data_type"]),
                    is_primary=field_config.get("is_primary", False),
                    auto_id=field_config.get("auto_id", False),
                    max_length=field_config.get("max_length"),
                    dimension=field_config.get("dimension"),
                    description=field_config.get("description"),
                    nullable=field_config.get("nullable", True),
                    default_value=field_config.get("default_value")
                )
                fields.append(field)
        
        # 创建集合模式
        collection_schema = CollectionSchema(
            name=template_data.get("name", "default_collection"),
            description=template_data.get("description"),
            fields=fields,
            enable_dynamic_field=template_data.get("enable_dynamic_field", False),
            auto_id=template_data.get("auto_id", False)
        )
        
        # 获取索引配置
        index_name = template_data.get("index", "balanced")
        index_config = self.get_index_config(index_name)
        
        # 创建分区配置
        partition_data = template_data.get("partition", {})
        partition_config = PartitionConfig(
            enabled=partition_data.get("enabled", False),
            partition_key=partition_data.get("partition_key"),
            default_partitions=partition_data.get("default_partitions", ["_default"])
        )
        
        # 获取基础配置
        base_config = self.get_base_config("default")
        
        # 应用覆盖参数
        if kwargs:
            if "host" in kwargs:
                base_config.host = kwargs["host"]
            if "port" in kwargs:
                base_config.port = kwargs["port"]
            if "collection_name" in kwargs:
                collection_schema.name = kwargs["collection_name"]
            if "dimension" in kwargs:
                # 更新向量字段的维度
                for field in fields:
                    if field.data_type == DataType.FLOAT_VECTOR:
                        field.dimension = kwargs["dimension"]
        
        # 创建标准集合定义
        return StandardCollectionDefinition(
            base_config=base_config,
            collection_schema=collection_schema,
            index_config=index_config,
            partition_config=partition_config,
            metadata=template_data.get("metadata", {})
        )
    
    def get_environment_config(self, env_name: str = "development") -> Dict[str, Any]:
        """
        获取环境配置
        
        参数:
            env_name: 环境名称
            
        返回:
            环境配置字典
        """
        environments = self.templates.get("environments", {})
        env_config = environments.get(env_name, {})
        
        if not env_config:
            raise ValueError(f"未找到环境配置: {env_name}")
        
        return env_config
    
    def get_metadata_schema(self, schema_name: str) -> Dict[str, Any]:
        """
        获取元数据模式
        
        参数:
            schema_name: 模式名称
            
        返回:
            元数据模式字典
        """
        metadata_schemas = self.templates.get("metadata_schemas", {})
        schema_data = metadata_schemas.get(schema_name, {})
        
        if not schema_data:
            raise ValueError(f"未找到元数据模式: {schema_name}")
        
        return schema_data
    
    def get_performance_config(self, config_name: str) -> Dict[str, Any]:
        """
        获取性能配置
        
        参数:
            config_name: 配置名称
            
        返回:
            性能配置字典
        """
        performance_configs = self.templates.get("performance_configs", {})
        config_data = performance_configs.get(config_name, {})
        
        if not config_data:
            raise ValueError(f"未找到性能配置: {config_name}")
        
        return config_data
    
    def list_templates(self) -> Dict[str, List[str]]:
        """
        列出所有可用的模板
        
        返回:
            模板列表字典
        """
        return {
            "base_configs": list(self.templates.get("base_configs", {}).keys()),
            "index_templates": list(self.templates.get("index_templates", {}).keys()),
            "field_templates": list(self.templates.get("field_templates", {}).keys()),
            "collection_templates": list(self.templates.get("collection_templates", {}).keys()),
            "environments": list(self.templates.get("environments", {}).keys()),
            "metadata_schemas": list(self.templates.get("metadata_schemas", {}).keys()),
            "performance_configs": list(self.templates.get("performance_configs", {}).keys())
        }
    
    def validate_template(self, template_name: str) -> Dict[str, Any]:
        """
        验证模板配置
        
        参数:
            template_name: 模板名称
            
        返回:
            验证结果
        """
        try:
            # 尝试加载模板
            collection_def = self.get_collection_template(template_name)
            
            return {
                "valid": True,
                "message": "模板配置有效",
                "collection_name": collection_def.collection_schema.name,
                "field_count": len(collection_def.collection_schema.fields),
                "has_vector_field": any(
                    field.data_type == DataType.FLOAT_VECTOR 
                    for field in collection_def.collection_schema.fields
                ),
                "partition_enabled": collection_def.partition_config.enabled
            }
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"模板配置无效: {str(e)}",
                "error": str(e)
            }
    
    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理配置中的环境变量
        
        参数:
            config: 配置字典
            
        返回:
            处理后的配置字典
        """
        processed = {}
        
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # 提取环境变量名
                env_var = value[2:-1]
                processed[key] = os.getenv(env_var, value)
            else:
                processed[key] = value
        
        return processed


# 全局模板加载器实例
_template_loader = None


def get_template_loader() -> VectorStoreTemplateLoader:
    """获取全局模板加载器实例"""
    global _template_loader
    if _template_loader is None:
        _template_loader = VectorStoreTemplateLoader()
    return _template_loader


# 便捷函数
def load_collection_template(template_name: str, **kwargs) -> StandardCollectionDefinition:
    """
    加载集合模板
    
    参数:
        template_name: 模板名称
        **kwargs: 配置覆盖参数
        
    返回:
        标准集合定义
    """
    loader = get_template_loader()
    return loader.get_collection_template(template_name, **kwargs)


def list_available_templates() -> Dict[str, List[str]]:
    """
    列出所有可用模板
    
    返回:
        模板列表字典
    """
    loader = get_template_loader()
    return loader.list_templates() 