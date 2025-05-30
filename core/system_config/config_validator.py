"""
配置验证器
提供配置项的验证业务逻辑
"""

import re
import json
from typing import Dict, Any, List


class ConfigValidator:
    """配置验证器"""
    
    # 配置键的正则表达式模式
    CONFIG_KEY_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$')
    
    # 类别名称的正则表达式模式
    CATEGORY_NAME_PATTERN = re.compile(r'^[\u4e00-\u9fa5a-zA-Z][^\s]{0,49}$')
    
    # 服务名称的正则表达式模式
    SERVICE_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
    
    def validate_config_key(self, key: str) -> bool:
        """验证配置键格式"""
        if not key or len(key) > 100:
            return False
        return bool(self.CONFIG_KEY_PATTERN.match(key))
    
    def validate_category_name(self, name: str) -> bool:
        """验证类别名称格式"""
        if not name or len(name) > 50:
            return False
        return bool(self.CATEGORY_NAME_PATTERN.match(name))
    
    def validate_service_name(self, name: str) -> bool:
        """验证服务名称格式"""
        if not name or len(name) > 50:
            return False
        return bool(self.SERVICE_NAME_PATTERN.match(name))
    
    def validate_value_type(self, value: Any, value_type: str) -> bool:
        """验证值是否符合指定类型"""
        try:
            if value_type == "string":
                return isinstance(value, str)
            elif value_type == "number":
                if isinstance(value, (int, float)):
                    return True
                if isinstance(value, str):
                    try:
                        float(value)
                        return True
                    except ValueError:
                        return False
                return False
            elif value_type == "boolean":
                if isinstance(value, bool):
                    return True
                if isinstance(value, str):
                    return value.lower() in ["true", "false", "yes", "no", "1", "0"]
                return False
            elif value_type == "json":
                if isinstance(value, (dict, list)):
                    return True
                if isinstance(value, str):
                    try:
                        json.loads(value)
                        return True
                    except json.JSONDecodeError:
                        return False
                return False
            else:
                return False
        except Exception:
            return False
    
    def validate_config_value(self, value: Any, validation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """根据验证规则验证配置值"""
        try:
            # 必填验证
            if validation_rules.get("required", False) and not value:
                return {
                    "valid": False,
                    "error": "配置值不能为空"
                }
            
            # 长度验证
            if "min_length" in validation_rules or "max_length" in validation_rules:
                str_value = str(value)
                
                if "min_length" in validation_rules:
                    min_len = validation_rules["min_length"]
                    if len(str_value) < min_len:
                        return {
                            "valid": False,
                            "error": f"配置值长度不能少于 {min_len} 个字符"
                        }
                
                if "max_length" in validation_rules:
                    max_len = validation_rules["max_length"]
                    if len(str_value) > max_len:
                        return {
                            "valid": False,
                            "error": f"配置值长度不能超过 {max_len} 个字符"
                        }
            
            # 数值范围验证
            if "min_value" in validation_rules or "max_value" in validation_rules:
                try:
                    num_value = float(value)
                    
                    if "min_value" in validation_rules:
                        min_val = validation_rules["min_value"]
                        if num_value < min_val:
                            return {
                                "valid": False,
                                "error": f"配置值不能小于 {min_val}"
                            }
                    
                    if "max_value" in validation_rules:
                        max_val = validation_rules["max_value"]
                        if num_value > max_val:
                            return {
                                "valid": False,
                                "error": f"配置值不能大于 {max_val}"
                            }
                            
                except ValueError:
                    return {
                        "valid": False,
                        "error": "配置值必须是有效数值"
                    }
            
            # 正则表达式验证
            if "pattern" in validation_rules:
                pattern = validation_rules["pattern"]
                if not re.match(pattern, str(value)):
                    error_msg = validation_rules.get("pattern_error", f"配置值不符合格式要求: {pattern}")
                    return {
                        "valid": False,
                        "error": error_msg
                    }
            
            # 枚举值验证
            if "enum" in validation_rules:
                valid_values = validation_rules["enum"]
                if value not in valid_values:
                    return {
                        "valid": False,
                        "error": f"配置值必须是以下值之一: {', '.join(map(str, valid_values))}"
                    }
            
            # 自定义验证函数
            if "custom_validator" in validation_rules:
                validator_func = validation_rules["custom_validator"]
                if callable(validator_func):
                    result = validator_func(value)
                    if not result.get("valid", True):
                        return result
            
            return {
                "valid": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"验证过程中发生错误: {str(e)}"
            }
    
    def get_validation_rules_schema(self) -> Dict[str, Any]:
        """获取验证规则的Schema定义"""
        return {
            "type": "object",
            "properties": {
                "required": {
                    "type": "boolean",
                    "description": "是否必填"
                },
                "min_length": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "最小长度"
                },
                "max_length": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "最大长度"
                },
                "min_value": {
                    "type": "number",
                    "description": "最小值"
                },
                "max_value": {
                    "type": "number", 
                    "description": "最大值"
                },
                "pattern": {
                    "type": "string",
                    "description": "正则表达式模式"
                },
                "pattern_error": {
                    "type": "string",
                    "description": "正则验证失败时的错误消息"
                },
                "enum": {
                    "type": "array",
                    "description": "枚举值列表"
                }
            },
            "additionalProperties": False
        }
    
    def create_common_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """创建常用的验证规则模板"""
        return {
            "url": {
                "pattern": r"^https?://[^\s/$.?#].[^\s]*$",
                "pattern_error": "必须是有效的URL地址"
            },
            "email": {
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "pattern_error": "必须是有效的邮箱地址"
            },
            "port": {
                "min_value": 1,
                "max_value": 65535
            },
            "percentage": {
                "min_value": 0,
                "max_value": 100
            },
            "api_key": {
                "required": True,
                "min_length": 10,
                "max_length": 256
            },
            "password": {
                "required": True,
                "min_length": 8,
                "max_length": 128
            },
            "timeout": {
                "min_value": 1,
                "max_value": 3600
            },
            "boolean_string": {
                "enum": ["true", "false", "yes", "no", "1", "0"]
            }
        } 