"""
OWL框架消息系统适配器
实现Agent数据格式与消息系统的集成
"""

from typing import Any, Dict, List, Optional, Union, AsyncGenerator
import json
import logging
from datetime import datetime

from app.frameworks.owl.utils.decorators import AgentInput, AgentOutput
from app.frameworks.owl.agents.interfaces import AgentInputSchema, AgentOutputSchema

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    FunctionCallMessage, FunctionReturnMessage, ThinkingMessage, 
    ImageMessage, HybridMessage, StatusMessage, ErrorMessage, DoneMessage,
    MCPToolMessage, CodeMessage, DeepResearchMessage
)

logger = logging.getLogger(__name__)


class AgentMessageAdapter:
    """Agent消息适配器
    
    负责在OWL框架的Agent数据格式和应用消息系统之间进行转换
    """
    
    @staticmethod
    def agent_output_to_messages(output: Union[AgentOutput, AgentOutputSchema]) -> List[Message]:
        """将Agent输出转换为消息系统的消息列表
        
        Args:
            output: Agent输出对象
            
        Returns:
            List[Message]: 消息列表
        """
        messages = []
        
        # 处理错误情况
        if hasattr(output, 'error') and output.error:
            messages.append(ErrorMessage(
                content={"message": output.error},
                metadata={"source": "agent", "error_type": output.metadata.get("error_type", "general_error")}
            ))
            return messages
        
        # 处理思考过程
        thinking = None
        if hasattr(output, 'metadata') and output.metadata:
            if 'thinking' in output.metadata:
                thinking = output.metadata['thinking']
            elif 'reasoning' in output.metadata:
                thinking = output.metadata['reasoning']
                
        if thinking:
            messages.append(ThinkingMessage(
                content=thinking,
                role=MessageRole.SYSTEM,
                metadata={"source": "agent_thinking"}
            ))
        
        # 处理工具调用
        if hasattr(output, 'tool_calls') and output.tool_calls:
            for tool_call in output.tool_calls:
                # 工具调用消息
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {}) or tool_call.get("arguments", {})
                tool_result = tool_call.get("result", None)
                
                if tool_name:
                    # 添加工具调用消息
                    messages.append(FunctionCallMessage(
                        content={"name": tool_name, "arguments": tool_args},
                        role=MessageRole.ASSISTANT,
                        metadata={"source": "agent_tool"}
                    ))
                    
                    # 如果有工具结果，添加工具结果消息
                    if tool_result is not None:
                        messages.append(FunctionReturnMessage(
                            content={"name": tool_name, "result": tool_result},
                            role=MessageRole.FUNCTION,
                            metadata={"source": "agent_tool"}
                        ))
        
        # 处理MCP工具调用
        if hasattr(output, 'metadata') and output.metadata and 'mcp_tools' in output.metadata:
            for mcp_tool in output.metadata['mcp_tools']:
                messages.append(MCPToolMessage(
                    content=mcp_tool,
                    role=MessageRole.TOOL,
                    metadata={"source": "agent_mcp"}
                ))
        
        # 处理源文档
        if hasattr(output, 'source_documents') and output.source_documents:
            source_info = {
                "sources": output.source_documents,
                "content": "来源文档信息"
            }
            messages.append(DeepResearchMessage(
                content=source_info,
                role=MessageRole.SYSTEM,
                metadata={"source": "agent_research"}
            ))
        
        # 处理代码内容
        if hasattr(output, 'content') and output.content:
            content = output.content
            is_code = False
            
            # 检测内容是否为代码
            if hasattr(output, 'metadata') and output.metadata:
                if output.metadata.get("content_type") == "code":
                    is_code = True
                    code_lang = output.metadata.get("language", "")
                    code_content = content
                    explanation = output.metadata.get("explanation", "")
                    
                    messages.append(CodeMessage(
                        content={
                            "code": code_content,
                            "language": code_lang,
                            "explanation": explanation
                        },
                        role=MessageRole.ASSISTANT,
                        metadata={"source": "agent_code"}
                    ))
            
            # 如果不是代码，则作为普通文本处理
            if not is_code:
                messages.append(TextMessage(
                    content=content,
                    role=MessageRole.ASSISTANT,
                    metadata={"source": "agent"}
                ))
        
        # 如果没有添加任何消息（这种情况不应该发生），添加一个空消息
        if not messages:
            messages.append(TextMessage(
                content="没有生成内容",
                role=MessageRole.ASSISTANT,
                metadata={"source": "agent", "error": "no_content_generated"}
            ))
        
        return messages
    
    @staticmethod
    def messages_to_agent_input(messages: List[Message]) -> AgentInput:
        """将消息系统的消息列表转换为Agent输入
        
        Args:
            messages: 消息列表
            
        Returns:
            AgentInput: Agent输入对象
        """
        # 提取用户查询
        query = ""
        history = []
        metadata = {}
        context = {}
        
        # 处理消息历史
        for msg in messages:
            # 转换为字典格式以添加到历史记录
            msg_dict = {
                "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                "type": msg.type.value if hasattr(msg.type, 'value') else str(msg.type),
                "content": msg.content
            }
            
            # 添加到历史
            history.append(msg_dict)
            
            # 提取最后一个用户消息作为查询
            if msg.role == MessageRole.USER:
                if isinstance(msg.content, str):
                    query = msg.content
                elif isinstance(msg.content, dict) and "text" in msg.content:
                    query = msg.content["text"]
                elif isinstance(msg.content, dict):
                    query = json.dumps(msg.content, ensure_ascii=False)
                else:
                    query = str(msg.content)
        
        # 创建Agent输入
        return AgentInput(
            query=query,
            history=history,
            context=context,
            metadata=metadata
        )
    
    @staticmethod
    def convert_to_stream_response(output: Union[AgentOutput, AgentOutputSchema]) -> Dict[str, Any]:
        """将Agent输出转换为适合流式响应的格式
        
        Args:
            output: Agent输出对象
            
        Returns:
            Dict[str, Any]: 流响应格式
        """
        # 转换为消息列表
        messages = AgentMessageAdapter.agent_output_to_messages(output)
        
        # 处理流式响应格式
        response = {
            "messages": [msg.to_dict() for msg in messages],
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加主要内容字段
        for msg in messages:
            if msg.type == MessageType.TEXT:
                response["content"] = msg.content
                break
        
        # 如果没有文本内容，尝试使用其他类型
        if "content" not in response:
            for msg in messages:
                if msg.type not in [MessageType.THINKING, MessageType.STATUS]:
                    if isinstance(msg.content, str):
                        response["content"] = msg.content
                    elif isinstance(msg.content, dict) and "message" in msg.content:
                        response["content"] = msg.content["message"]
                    else:
                        response["content"] = str(msg.content)
                    break
        
        return response


class AgentChainMessageAdapter:
    """Agent链消息适配器
    
    负责在Agent链数据和消息系统之间进行转换
    """
    
    @staticmethod
    def chain_result_to_messages(
        chain_result: Dict[str, Any],
        include_intermediate: bool = False
    ) -> List[Message]:
        """将Agent链结果转换为消息列表
        
        Args:
            chain_result: Agent链执行结果
            include_intermediate: 是否包含中间结果
            
        Returns:
            List[Message]: 消息列表
        """
        messages = []
        
        # 处理错误情况
        if "error" in chain_result:
            messages.append(ErrorMessage(
                content={"message": chain_result["error"]},
                metadata={"source": "agent_chain"}
            ))
            return messages
        
        # 处理中间步骤
        if include_intermediate and "steps" in chain_result:
            for step in chain_result["steps"]:
                # 添加步骤状态消息
                messages.append(StatusMessage(
                    content={
                        "step": step.get("name", "未命名步骤"),
                        "agent": step.get("agent_name", "未知代理"),
                        "status": step.get("status", "completed")
                    },
                    role=MessageRole.SYSTEM,
                    metadata={"source": "agent_chain_step"}
                ))
                
                # 如果步骤有输出并且成功完成，添加输出消息
                if step.get("status") == "completed" and "output" in step:
                    # 将步骤输出转换为消息
                    step_output = step["output"]
                    if isinstance(step_output, (AgentOutput, AgentOutputSchema)):
                        step_messages = AgentMessageAdapter.agent_output_to_messages(step_output)
                        messages.extend(step_messages)
                    elif isinstance(step_output, str):
                        messages.append(TextMessage(
                            content=step_output,
                            role=MessageRole.ASSISTANT,
                            metadata={"source": f"agent_chain_step_{step.get('agent_name', 'unknown')}"}
                        ))
                    elif isinstance(step_output, dict):
                        if "content" in step_output:
                            messages.append(TextMessage(
                                content=step_output["content"],
                                role=MessageRole.ASSISTANT,
                                metadata={"source": f"agent_chain_step_{step.get('agent_name', 'unknown')}"}
                            ))
                        else:
                            messages.append(TextMessage(
                                content=json.dumps(step_output, ensure_ascii=False),
                                role=MessageRole.ASSISTANT,
                                metadata={"source": f"agent_chain_step_{step.get('agent_name', 'unknown')}"}
                            ))
        
        # 处理最终结果
        if "result" in chain_result:
            result = chain_result["result"]
            if isinstance(result, (AgentOutput, AgentOutputSchema)):
                # 如果是AgentOutput格式，转换为消息
                final_messages = AgentMessageAdapter.agent_output_to_messages(result)
                messages.extend(final_messages)
            elif isinstance(result, str):
                # 如果是字符串，创建文本消息
                messages.append(TextMessage(
                    content=result,
                    role=MessageRole.ASSISTANT,
                    metadata={"source": "agent_chain_result"}
                ))
            elif isinstance(result, dict):
                # 如果是字典，检查是否有标准格式
                if "content" in result:
                    messages.append(TextMessage(
                        content=result["content"],
                        role=MessageRole.ASSISTANT,
                        metadata={"source": "agent_chain_result"}
                    ))
                else:
                    # 默认转换为JSON字符串
                    messages.append(TextMessage(
                        content=json.dumps(result, ensure_ascii=False),
                        role=MessageRole.ASSISTANT,
                        metadata={"source": "agent_chain_result"}
                    ))
            else:
                # 其他类型，转换为字符串
                messages.append(TextMessage(
                    content=str(result),
                    role=MessageRole.ASSISTANT,
                    metadata={"source": "agent_chain_result"}
                ))
        
        # 添加完成标记
        messages.append(DoneMessage(
            metadata={"source": "agent_chain"}
        ))
        
        return messages
