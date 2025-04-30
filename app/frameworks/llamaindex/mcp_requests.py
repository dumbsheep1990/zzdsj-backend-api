"""
MCP请求构造模块
提供标准化的MCP工具请求构造功能
"""

from typing import Dict, Any, Optional, List
import json
import logging

logger = logging.getLogger(__name__)

class MCPRequestBuilder:
    """MCP请求构造器"""
    
    @staticmethod
    def build_tool_request(
        tool_name: str, 
        params: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建标准MCP工具请求
        
        参数:
            tool_name: 工具名称
            params: 参数字典
            metadata: 元数据（可选）
            
        返回:
            标准化的MCP工具请求
        """
        request = {
            "tool_name": tool_name,
            "parameters": params,
            "context": {
                "source": "llamaindex_agent",
                "timestamp": None,  # 由服务端填充
                "request_id": None,  # 由服务端填充
                "metadata": metadata or {}
            }
        }
        
        logger.debug(f"构建MCP工具请求: {json.dumps(request)}")
        return request
    
    @staticmethod
    def validate_parameters(
        parameters: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证并转换参数
        
        参数:
            parameters: 用户提供的参数
            schema: 参数schema
            
        返回:
            验证后的参数
        """
        import jsonschema
        
        try:
            # 获取参数schema
            props_schema = schema.get("parameters", {}).get("properties", {})
            required = schema.get("parameters", {}).get("required", [])
            
            # 验证必填项
            for field in required:
                if field not in parameters:
                    raise ValueError(f"缺少必填参数: {field}")
            
            # 验证并转换类型
            validated_params = {}
            for name, value in parameters.items():
                if name not in props_schema:
                    logger.warning(f"未知参数: {name}")
                    validated_params[name] = value
                    continue
                
                field_schema = props_schema[name]
                field_type = field_schema.get("type")
                
                # 简单类型转换
                if field_type == "integer" and not isinstance(value, int):
                    validated_params[name] = int(value)
                elif field_type == "number" and not isinstance(value, (int, float)):
                    validated_params[name] = float(value)
                elif field_type == "boolean" and not isinstance(value, bool):
                    validated_params[name] = value.lower() in ("true", "yes", "1")
                elif field_type == "array" and not isinstance(value, list):
                    if isinstance(value, str):
                        validated_params[name] = json.loads(value)
                    else:
                        validated_params[name] = [value]
                else:
                    validated_params[name] = value
            
            # 验证整体schema
            jsonschema.validate(
                instance={"parameters": validated_params},
                schema={"type": "object", "properties": {"parameters": schema.get("parameters", {})}}
            )
            
            return validated_params
            
        except (ValueError, jsonschema.exceptions.ValidationError) as e:
            logger.error(f"参数验证失败: {str(e)}")
            raise ValueError(f"参数验证失败: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}")
            raise ValueError(f"JSON解析错误: {str(e)}")
        except Exception as e:
            logger.error(f"参数验证出现未知错误: {str(e)}")
            raise ValueError(f"参数验证出现未知错误: {str(e)}")
    
    @staticmethod
    def parse_response(
        response: Dict[str, Any]
    ) -> Any:
        """
        解析MCP工具响应
        
        参数:
            response: MCP工具响应
            
        返回:
            解析后的结果
        """
        # 从响应中提取结果
        if not isinstance(response, dict):
            return response
            
        # 检查是否有错误
        if "error" in response:
            logger.error(f"MCP工具返回错误: {response['error']}")
            error_msg = response.get("error_message", str(response["error"]))
            raise ValueError(f"MCP工具执行失败: {error_msg}")
            
        # 提取结果
        if "result" in response:
            return response["result"]
        elif "data" in response:
            return response["data"]
        
        # 如果没有标准字段，返回整个响应
        return response
