"""
OWL框架Agent链数据转换工具
负责处理Agent链中的数据格式转换和映射
"""

from typing import Any, Dict, List, Optional, Union
import logging
import json
from datetime import datetime

from app.frameworks.owl.agents.interfaces import (
    AgentInputSchema, AgentOutputSchema, AgentChainStep
)

logger = logging.getLogger(__name__)


class ChainDataTransformer:
    """Agent链数据转换器
    
    负责在Agent链的执行过程中处理数据的格式转换和字段映射，
    确保每个Agent接收到正确格式的输入，并将输出转换为下一个Agent可接受的格式。
    """
    
    def __init__(self):
        """初始化数据转换器"""
        self.context_store = {}  # 存储链执行上下文
    
    def set_context(self, trace_id: str, context: Dict[str, Any]) -> None:
        """设置链执行上下文
        
        Args:
            trace_id: 链执行追踪ID
            context: 上下文数据
        """
        self.context_store[trace_id] = context
    
    def get_context(self, trace_id: str) -> Dict[str, Any]:
        """获取链执行上下文
        
        Args:
            trace_id: 链执行追踪ID
            
        Returns:
            Dict[str, Any]: 上下文数据
        """
        return self.context_store.get(trace_id, {})
    
    def clear_context(self, trace_id: str) -> None:
        """清除链执行上下文
        
        Args:
            trace_id: 链执行追踪ID
        """
        if trace_id in self.context_store:
            del self.context_store[trace_id]
    
    def transform_to_agent_input(
        self, 
        data: Dict[str, Any], 
        step: AgentChainStep,
        prev_output: Optional[AgentOutputSchema] = None,
        trace_id: Optional[str] = None
    ) -> AgentInputSchema:
        """将数据转换为Agent输入格式
        
        根据链步骤定义的输入映射，将数据转换为Agent可接受的输入格式
        
        Args:
            data: 原始数据
            step: 链步骤定义
            prev_output: 上一个Agent的输出
            trace_id: 链执行追踪ID
            
        Returns:
            AgentInputSchema: 转换后的Agent输入
        """
        # 获取上下文
        context = self.get_context(trace_id) if trace_id else {}
        
        # 准备基础输入
        input_data = {
            "query": "",
            "context": context,
            "metadata": {
                "chain_step": step.dict(),
                "timestamp": datetime.now().isoformat()
            },
            "parameters": {},
            "source_agent_id": None
        }
        
        # 如果有上一个Agent的输出，合并其元数据
        if prev_output:
            input_data["source_agent_id"] = context.get("last_agent_id")
            input_data["metadata"]["prev_agent_output"] = {
                "content": prev_output.content,
                "metadata": prev_output.metadata
            }
        
        # 应用输入映射
        for target_field, source_expr in step.input_mapping.items():
            try:
                # 处理特殊映射表达式
                if source_expr.startswith("${") and source_expr.endswith("}"):
                    # 从上下文中获取值
                    field_path = source_expr[2:-1].strip()
                    value = self._get_value_by_path(data, field_path)
                    if value is not None:
                        # 根据目标字段类型设置值
                        if target_field == "query":
                            input_data["query"] = str(value)
                        elif target_field.startswith("context."):
                            context_field = target_field[8:]
                            input_data["context"][context_field] = value
                        elif target_field.startswith("metadata."):
                            metadata_field = target_field[9:]
                            input_data["metadata"][metadata_field] = value
                        elif target_field.startswith("parameters."):
                            param_field = target_field[11:]
                            input_data["parameters"][param_field] = value
                        else:
                            # 默认设置到parameters
                            input_data["parameters"][target_field] = value
                else:
                    # 直接使用表达式值
                    if target_field == "query":
                        input_data["query"] = source_expr
                    elif target_field.startswith("context."):
                        context_field = target_field[8:]
                        input_data["context"][context_field] = source_expr
                    elif target_field.startswith("metadata."):
                        metadata_field = target_field[9:]
                        input_data["metadata"][metadata_field] = source_expr
                    elif target_field.startswith("parameters."):
                        param_field = target_field[11:]
                        input_data["parameters"][param_field] = source_expr
                    else:
                        # 默认设置到parameters
                        input_data["parameters"][target_field] = source_expr
            except Exception as e:
                logger.warning(f"应用输入映射时出错: {str(e)}")
        
        # 如果没有设置查询，使用默认值
        if not input_data["query"] and prev_output:
            input_data["query"] = prev_output.content
        
        # 添加追踪ID
        if trace_id:
            input_data["trace_id"] = trace_id
        
        # 创建规范的输入模型
        return AgentInputSchema(**input_data)
    
    def transform_agent_output(
        self, 
        output: AgentOutputSchema, 
        step: AgentChainStep,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """转换Agent输出
        
        根据链步骤定义的输出映射，转换Agent输出为通用格式
        
        Args:
            output: Agent输出
            step: 链步骤定义
            trace_id: 链执行追踪ID
            
        Returns:
            Dict[str, Any]: 转换后的输出
        """
        # 获取上下文
        context = self.get_context(trace_id) if trace_id else {}
        
        # 准备输出数据
        result = {
            "content": output.content,
            "agent_id": step.agent_id,
            "agent_name": step.agent_name,
            "position": step.position,
            "timestamp": output.timestamp or datetime.now().isoformat(),
            "metadata": dict(output.metadata),
            "tool_calls": output.tool_calls,
            "source_documents": output.source_documents,
            "error": output.error
        }
        
        # 应用输出映射
        transformed_data = {}
        for target_field, source_expr in step.output_mapping.items():
            try:
                if source_expr == "content":
                    transformed_data[target_field] = output.content
                elif source_expr.startswith("metadata."):
                    field_path = source_expr[9:]
                    value = self._get_value_by_path(output.metadata, field_path)
                    if value is not None:
                        transformed_data[target_field] = value
                elif source_expr.startswith("tool_calls."):
                    # 处理工具调用结果
                    field_path = source_expr[11:]
                    parts = field_path.split(".")
                    if len(parts) > 1 and parts[0].isdigit():
                        # 获取特定索引的工具调用
                        idx = int(parts[0])
                        if idx < len(output.tool_calls):
                            tool_call = output.tool_calls[idx]
                            value = self._get_value_by_path(tool_call, ".".join(parts[1:]))
                            if value is not None:
                                transformed_data[target_field] = value
                else:
                    # 尝试从整个输出对象获取值
                    value = self._get_value_by_path(output.dict(), source_expr)
                    if value is not None:
                        transformed_data[target_field] = value
            except Exception as e:
                logger.warning(f"应用输出映射时出错: {str(e)}")
        
        # 如果没有映射规则，使用默认映射
        if not step.output_mapping:
            transformed_data = {
                "result": output.content,
                "metadata": output.metadata
            }
        
        # 更新上下文
        if trace_id:
            # 保存当前Agent信息
            context["last_agent_id"] = step.agent_id
            context["last_agent_name"] = step.agent_name
            context["last_agent_position"] = step.position
            
            # 保存输出结果到上下文
            context[f"step_{step.position}_result"] = output.content
            context[f"step_{step.position}_metadata"] = output.metadata
            
            # 如果有命名，也使用名称作为键
            if step.agent_name:
                context[f"{step.agent_name}_result"] = output.content
                
            # 更新上下文
            self.set_context(trace_id, context)
        
        # 合并结果
        result.update({"transformed": transformed_data})
        
        return result
    
    def _get_value_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """通过路径获取嵌套字典中的值
        
        Args:
            data: 数据字典
            path: 点分隔的路径
            
        Returns:
            Any: 找到的值，如果路径无效则返回None
        """
        if not path:
            return None
            
        parts = path.split(".")
        current = data
        
        try:
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    return None
                    
                if current is None:
                    return None
            
            return current
        except Exception:
            return None


# 创建全局转换器实例
chain_transformer = ChainDataTransformer()
