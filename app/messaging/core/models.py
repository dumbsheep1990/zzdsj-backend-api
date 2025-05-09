"""
消息模型定义
定义统一的消息类型、角色和结构
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
import time
import json


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"                   # 普通文本消息
    FUNCTION_CALL = "function_call"  # 函数调用
    FUNCTION_RETURN = "function_return"  # 函数返回
    THINKING = "thinking"           # 思考过程
    IMAGE = "image"                 # 图像消息
    HYBRID = "hybrid"               # 混合内容
    STATUS = "status"               # 状态更新
    ERROR = "error"                 # 错误消息
    DONE = "done"                   # 完成标记
    MCP_TOOL = "mcp_tool"           # MCP工具消息
    VOICE = "voice"                 # 语音消息
    DEEP_RESEARCH = "deep_research" # 深度研究消息
    CODE = "code"                   # 代码消息
    TABLE = "table"                 # 表格消息


class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"       # 系统消息
    USER = "user"           # 用户消息
    ASSISTANT = "assistant"  # 助手消息
    TOOL = "tool"           # 工具消息
    FUNCTION = "function"   # 函数消息


class ContentBlock(BaseModel):
    """内容块模型，用于混合内容"""
    type: str = Field(..., description="内容类型，如text、image")
    content: Any = Field(..., description="具体内容")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class Message(BaseModel):
    """统一消息模型"""
    id: str = Field(default_factory=lambda: f"msg-{int(time.time() * 1000)}", description="消息唯一标识")
    type: MessageType = Field(..., description="消息类型")
    role: Optional[MessageRole] = Field(default=MessageRole.ASSISTANT, description="消息角色")
    content: Any = Field(..., description="消息内容")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式，子类应重写此方法
        
        返回:
            OpenAI格式字典
        """
        # 默认实现
        if isinstance(self.content, str):
            return {
                "role": self.role.value,
                "content": self.content
            }
        elif isinstance(self.content, dict) or isinstance(self.content, list):
            return {
                "role": self.role.value,
                "content": json.dumps(self.content, ensure_ascii=False)
            }
        else:
            return {
                "role": self.role.value,
                "content": str(self.content)
            }
    
    class Config:
        """Pydantic配置"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.type,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_sse(self, event_name: Optional[str] = None) -> str:
        """转换为SSE格式"""
        event = event_name or self.type
        return f"event: {event}\ndata: {self.to_json()}\n\n"


class TextMessage(Message):
    """文本消息"""
    type: MessageType = MessageType.TEXT
    content: str
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        return {
            "role": self.role.value,
            "content": self.content
        }


class FunctionCallMessage(Message):
    """函数调用消息"""
    type: MessageType = MessageType.FUNCTION_CALL
    content: Dict[str, Any] = Field(..., description="函数调用内容")
    
    @property
    def function_name(self) -> str:
        """获取函数名称"""
        return self.content.get("name", "")
    
    @property
    def function_arguments(self) -> Dict[str, Any]:
        """获取函数参数"""
        return self.content.get("arguments", {})
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        return {
            "role": self.role.value,
            "content": None,
            "tool_calls": [
                {
                    "id": self.metadata.get("call_id", f"call_{self.id}"),
                    "type": "function",
                    "function": {
                        "name": self.function_name,
                        "arguments": json.dumps(self.function_arguments, ensure_ascii=False)
                    }
                }
            ]
        }


class FunctionReturnMessage(Message):
    """函数返回消息"""
    type: MessageType = MessageType.FUNCTION_RETURN
    content: Dict[str, Any] = Field(..., description="函数返回内容")
    
    @property
    def function_name(self) -> str:
        """获取函数名称"""
        return self.content.get("name", "")
    
    @property
    def function_result(self) -> Any:
        """获取函数返回结果"""
        return self.content.get("result")
    
    @property
    def call_id(self) -> Optional[str]:
        """获取调用ID"""
        return self.content.get("call_id")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        result = self.function_result
        call_id = self.call_id or self.metadata.get("call_id", f"call_{self.id}")
        
        if isinstance(result, dict) or isinstance(result, list):
            result_str = json.dumps(result, ensure_ascii=False)
        elif not isinstance(result, str):
            result_str = str(result)
        else:
            result_str = result
        
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "name": self.function_name,
            "content": result_str
        }


class ThinkingMessage(Message):
    """思考过程消息"""
    type: MessageType = MessageType.THINKING
    content: str
    step: Optional[int] = Field(None, description="思考步骤")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        # 思考过程在OpenAI格式中用系统消息表示
        step_text = f"步骤 {self.step}: " if self.step is not None else ""
        return {
            "role": "system",
            "content": f"思考过程: {step_text}{self.content}"
        }


class ImageMessage(Message):
    """图像消息"""
    type: MessageType = MessageType.IMAGE
    content: Dict[str, Any] = Field(..., description="图像内容")
    
    @property
    def image_url(self) -> str:
        """获取图像URL"""
        return self.content.get("url", "")
    
    @property
    def caption(self) -> Optional[str]:
        """获取图像说明"""
        return self.content.get("caption")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        if self.role == MessageRole.USER:
            # 用户发送的图像
            content_parts = []
            if self.caption:
                content_parts.append({
                    "type": "text",
                    "text": self.caption
                })
            
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": self.image_url
                }
            })
            
            return {
                "role": "user",
                "content": content_parts
            }
        else:
            # 助手生成的图像
            caption = self.caption or "图像"
            return {
                "role": self.role.value,
                "content": f"{caption}\n![图像]({self.image_url})"
            }


class HybridMessage(Message):
    """混合内容消息"""
    type: MessageType = MessageType.HYBRID
    content: Dict[str, List[ContentBlock]] = Field(..., description="混合内容")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        blocks = self.content.get("blocks", [])
        if not blocks:
            return {
                "role": self.role.value,
                "content": ""
            }
        
        if self.role == MessageRole.USER:
            # 用户消息使用多部分内容格式
            content_parts = []
            for block in blocks:
                if block.type == "text":
                    content_parts.append({
                        "type": "text",
                        "text": block.content
                    })
                elif block.type == "image":
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": block.content.get("url", "")
                        }
                    })
            
            return {
                "role": "user",
                "content": content_parts
            }
        else:
            # 助手消息使用markdown格式
            combined_content = ""
            for block in blocks:
                if block.type == "text":
                    combined_content += block.content + "\n\n"
                elif block.type == "image":
                    url = block.content.get("url", "")
                    caption = block.content.get("caption", "图像")
                    combined_content += f"{caption}\n![{caption}]({url})\n\n"
            
            return {
                "role": self.role.value,
                "content": combined_content.strip()
            }


class StatusMessage(Message):
    """状态消息"""
    type: MessageType = MessageType.STATUS
    content: Dict[str, Any] = Field(..., description="状态信息")
    
    @property
    def status(self) -> str:
        """获取状态"""
        return self.content.get("status", "")


class ErrorMessage(Message):
    """错误消息"""
    type: MessageType = MessageType.ERROR
    content: Dict[str, Any] = Field(..., description="错误信息")
    
    @property
    def error_message(self) -> str:
        """获取错误消息"""
        return self.content.get("message", "未知错误")
    
    @property
    def error_code(self) -> Optional[str]:
        """获取错误代码"""
        return self.content.get("code")


class DoneMessage(Message):
    """完成标记消息"""
    type: MessageType = MessageType.DONE
    content: Dict[str, bool] = Field(default_factory=lambda: {"done": True}, description="完成标记")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        # Done消息在OpenAI格式中不存在对应，使用系统消息表示
        return {
            "role": "system",
            "content": "[已完成]" 
        }


class MCPToolMessage(Message):
    """MCP工具消息"""
    type: MessageType = MessageType.MCP_TOOL
    content: Dict[str, Any] = Field(..., description="MCP工具内容")
    
    @property
    def tool_name(self) -> str:
        """获取工具名称"""
        return self.content.get("name", "")
    
    @property
    def tool_parameters(self) -> Dict[str, Any]:
        """获取工具参数"""
        return self.content.get("parameters", {})
    
    @property
    def tool_result(self) -> Optional[Any]:
        """获取工具结果"""
        return self.content.get("result")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        if self.tool_result is None:
            # 工具调用
            return {
                "role": self.role.value,
                "content": None,
                "tool_calls": [
                    {
                        "id": self.metadata.get("call_id", f"call_{self.id}"),
                        "type": "function",
                        "function": {
                            "name": f"mcp_{self.tool_name}",
                            "arguments": json.dumps(self.tool_parameters, ensure_ascii=False)
                        }
                    }
                ]
            }
        else:
            # 工具结果
            result = self.tool_result
            if isinstance(result, dict) or isinstance(result, list):
                result_str = json.dumps(result, ensure_ascii=False)
            elif not isinstance(result, str):
                result_str = str(result)
            else:
                result_str = result
                
            return {
                "role": "tool",
                "tool_call_id": self.metadata.get("call_id", f"call_{self.id}"),
                "name": f"mcp_{self.tool_name}",
                "content": result_str
            }


class VoiceMessage(Message):
    """语音消息"""
    type: MessageType = MessageType.VOICE
    content: Dict[str, Any] = Field(..., description="语音内容")
    
    @property
    def audio_url(self) -> str:
        """获取音频URL"""
        return self.content.get("url", "")
    
    @property
    def transcript(self) -> Optional[str]:
        """获取语音转录文本"""
        return self.content.get("transcript")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        if self.role == MessageRole.USER:
            # 用户发送的语音
            return {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.transcript or "[语音消息]"
                    },
                    {
                        "type": "audio_url",
                        "audio_url": {"url": self.audio_url}
                    }
                ]
            }
        else:
            # 助手生成的语音
            return {
                "role": "assistant",
                "content": self.transcript or "[语音消息]",
                "audio": {
                    "url": self.audio_url
                }
            }


class DeepResearchMessage(Message):
    """深度研究消息"""
    type: MessageType = MessageType.DEEP_RESEARCH
    content: Dict[str, Any] = Field(..., description="研究内容")
    
    @property
    def research_content(self) -> str:
        """获取研究内容"""
        return self.content.get("content", "")
    
    @property
    def sources(self) -> List[Dict[str, Any]]:
        """获取来源信息"""
        return self.content.get("sources", [])
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        # 格式化源引用
        formatted_sources = ""
        if self.sources:
            formatted_sources = "\n\n**来源:**\n"
            for i, source in enumerate(self.sources):
                url = source.get("url", "")
                title = source.get("title", f"来源 {i+1}")
                formatted_sources += f"{i+1}. [{title}]({url})\n"
        
        return {
            "role": self.role.value,
            "content": self.research_content + formatted_sources
        }


class CodeMessage(Message):
    """代码消息"""
    type: MessageType = MessageType.CODE
    content: Dict[str, Any] = Field(..., description="代码内容")
    
    @property
    def code(self) -> str:
        """获取代码"""
        return self.content.get("code", "")
    
    @property
    def language(self) -> str:
        """获取语言"""
        return self.content.get("language", "")
    
    @property
    def explanation(self) -> Optional[str]:
        """获取解释说明"""
        return self.content.get("explanation")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式
        
        返回:
            OpenAI格式字典
        """
        explanation = self.explanation or ""
        if explanation:
            explanation += "\n\n"
            
        formatted_content = f"{explanation}```{self.language}\n{self.code}\n```"
        
        return {
            "role": self.role.value,
            "content": formatted_content
        }


class TableMessage(Message):
    """表格消息"""
    type: MessageType = MessageType.TABLE
    content: Dict[str, Any] = Field(..., description="表格内容")
    
    @property
    def headers(self) -> List[str]:
        """获取表头"""
        return self.content.get("headers", [])
    
    @property
    def rows(self) -> List[List[Any]]:
        """获取行数据"""
        return self.content.get("rows", [])
    
    @property
    def caption(self) -> Optional[str]:
        """获取表格标题"""
        return self.content.get("caption")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式的markdown表格
        
        返回:
            OpenAI格式字典
        """
        # 构建markdown表格
        table = ""
        
        if self.caption:
            table += f"**{self.caption}**\n\n"
        
        if self.headers:
            table += "| " + " | ".join(self.headers) + " |\n"
            table += "| " + " | ".join(["---" for _ in self.headers]) + " |\n"
        
        for row in self.rows:
            table += "| " + " | ".join([str(cell) for cell in row]) + " |\n"
        
        return {
            "role": self.role.value,
            "content": table
        }
