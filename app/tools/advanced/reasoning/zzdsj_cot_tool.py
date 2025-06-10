"""
Agno思维链(Chain of Thought)工具
基于Agno框架的原生实现，替代LlamaIndex版本
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

from app.tools.advanced.reasoning.cot_manager import CoTManager

logger = logging.getLogger(__name__)

class AgnoCoTRequest(BaseModel):
    """Agno CoT请求参数模型"""
    query: str = Field(..., description="用户查询内容")
    system_prompt: Optional[str] = Field(None, description="系统提示，控制模型角色和行为")
    enable_cot: bool = Field(True, description="是否启用思维链")
    use_multi_step: bool = Field(False, description="是否使用多步骤思维链格式")
    temperature: float = Field(0.3, description="温度参数，控制输出随机性")
    max_tokens: Optional[int] = Field(None, description="最大输出token数")
    show_cot: bool = Field(True, description="是否在输出中显示思维过程")

class AgnoCoTResponse(BaseModel):
    """Agno CoT响应模型"""
    final_answer: str = Field(..., description="最终答案")
    thinking_process: Optional[str] = Field(None, description="思维过程")
    reasoning_steps: Optional[List[str]] = Field(None, description="推理步骤")
    show_cot: bool = Field(True, description="是否显示思维链")
    execution_time: float = Field(0.0, description="执行时间(秒)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class AgnoCoTTool:
    """Agno思维链工具，基于Agno框架原生实现"""
    
    def __init__(self, name: str = "cot_reasoning", llm=None):
        """
        初始化Agno思维链工具
        
        参数:
            name: 工具名称
            llm: 语言模型实例，如果为None则使用全局设置的模型
        """
        self.name = name
        self.llm = llm
        self.cot_manager = CoTManager(llm=llm)
        self.description = (
            "使用思维链(Chain of Thought)进行推理，展示清晰的思考过程和最终答案。"
            "适用于需要深入分析、逐步推理或说明思考过程的复杂问题。"
        )
    
    def reason_with_cot(
        self, 
        query: str,
        system_prompt: Optional[str] = None,
        enable_cot: bool = True,
        use_multi_step: bool = False,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        show_cot: bool = True
    ) -> Dict[str, Any]:
        """
        使用思维链进行推理 - Agno工具方法
        
        参数:
            query: 用户查询内容
            system_prompt: 系统提示，控制模型角色和行为
            enable_cot: 是否启用思维链
            use_multi_step: 是否使用多步骤思维链格式
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            show_cot: 是否在输出中显示思维过程
            
        返回:
            包含思维链和最终答案的结果字典
        """
        try:
            start_time = datetime.now()
            
            # 执行同步推理
            result = self.cot_manager.call_with_cot(
                prompt_content=query,
                system_prompt=system_prompt,
                enable_cot=enable_cot,
                use_multi_step=use_multi_step,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 格式化响应
            formatted_result = self.cot_manager.format_response_for_api(
                result,
                show_cot=show_cot
            )
            
            # 构建Agno工具响应
            response = {
                "success": True,
                "final_answer": formatted_result.get("final_answer", ""),
                "thinking_process": formatted_result.get("thinking_process") if show_cot else None,
                "reasoning_steps": formatted_result.get("reasoning_steps") if show_cot else None,
                "show_cot": show_cot,
                "execution_time": execution_time,
                "metadata": {
                    "query": query,
                    "enable_cot": enable_cot,
                    "use_multi_step": use_multi_step,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timestamp": end_time.isoformat()
                },
                "raw_result": formatted_result
            }
            
            return response
            
        except Exception as e:
            logger.error(f"执行思维链推理时出错: {str(e)}")
            return {
                "success": False,
                "final_answer": f"执行推理时出错: {str(e)}",
                "thinking_process": None,
                "reasoning_steps": None,
                "show_cot": False,
                "execution_time": 0.0,
                "metadata": {
                    "query": query,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                "error": str(e)
            }
    
    async def async_reason_with_cot(
        self, 
        query: str,
        system_prompt: Optional[str] = None,
        enable_cot: bool = True,
        use_multi_step: bool = False,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        show_cot: bool = True
    ) -> Dict[str, Any]:
        """
        异步使用思维链进行推理
        
        参数:
            query: 用户查询内容
            system_prompt: 系统提示，控制模型角色和行为
            enable_cot: 是否启用思维链
            use_multi_step: 是否使用多步骤思维链格式
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            show_cot: 是否在输出中显示思维过程
            
        返回:
            包含思维链和最终答案的结果字典
        """
        try:
            start_time = datetime.now()
            
            # 执行异步推理
            result = await self.cot_manager.acall_with_cot(
                prompt_content=query,
                system_prompt=system_prompt,
                enable_cot=enable_cot,
                use_multi_step=use_multi_step,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 格式化响应
            formatted_result = self.cot_manager.format_response_for_api(
                result,
                show_cot=show_cot
            )
            
            # 构建Agno工具响应
            response = {
                "success": True,
                "final_answer": formatted_result.get("final_answer", ""),
                "thinking_process": formatted_result.get("thinking_process") if show_cot else None,
                "reasoning_steps": formatted_result.get("reasoning_steps") if show_cot else None,
                "show_cot": show_cot,
                "execution_time": execution_time,
                "metadata": {
                    "query": query,
                    "enable_cot": enable_cot,
                    "use_multi_step": use_multi_step,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timestamp": end_time.isoformat()
                },
                "raw_result": formatted_result
            }
            
            return response
            
        except Exception as e:
            logger.error(f"执行异步思维链推理时出错: {str(e)}")
            return {
                "success": False,
                "final_answer": f"执行推理时出错: {str(e)}",
                "thinking_process": None,
                "reasoning_steps": None,
                "show_cot": False,
                "execution_time": 0.0,
                "metadata": {
                    "query": query,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                "error": str(e)
            }
    
    def simple_reason(self, query: str, **kwargs) -> str:
        """
        简单推理接口，返回文本格式结果
        
        参数:
            query: 查询内容
            **kwargs: 其他参数
            
        返回:
            推理结果的文本表示
        """
        result = self.reason_with_cot(
            query=query,
            system_prompt=kwargs.get('system_prompt'),
            enable_cot=kwargs.get('enable_cot', True),
            use_multi_step=kwargs.get('use_multi_step', False),
            temperature=kwargs.get('temperature', 0.3),
            max_tokens=kwargs.get('max_tokens'),
            show_cot=kwargs.get('show_cot', True)
        )
        
        if result['success']:
            if result['show_cot'] and result['thinking_process']:
                return f"思考过程：\n{result['thinking_process']}\n\n最终答案：\n{result['final_answer']}"
            else:
                return result['final_answer']
        else:
            return result['final_answer']  # 包含错误信息
    
    def get_reasoning_capabilities(self) -> List[str]:
        """
        获取推理能力列表
        
        返回:
            推理能力列表
        """
        return [
            "chain_of_thought",
            "step_by_step_reasoning", 
            "multi_step_analysis",
            "logical_deduction",
            "problem_decomposition",
            "cause_effect_analysis"
        ]
    
    def validate_query(self, query: str) -> bool:
        """
        验证推理查询
        
        参数:
            query: 推理查询
            
        返回:
            是否有效
        """
        if not query or not query.strip():
            return False
        
        # 检查查询长度
        if len(query) > 2000:
            return False
            
        return True

class AgnoReasoningToolCollection:
    """Agno推理工具集合，包含多种推理工具"""
    
    def __init__(self, llm=None):
        """
        初始化推理工具集合
        
        参数:
            llm: 语言模型实例
        """
        self.llm = llm
        self.cot_tool = AgnoCoTTool(llm=llm)
        self.tools = {
            "cot_reasoning": self.cot_tool,
        }
    
    def get_tool(self, tool_name: str):
        """
        获取指定的推理工具
        
        参数:
            tool_name: 工具名称
            
        返回:
            推理工具实例
        """
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有可用的推理工具
        
        返回:
            工具名称列表
        """
        return list(self.tools.keys())

# 工厂函数
def create_agno_cot_tool(name: str = "cot_reasoning", llm=None) -> AgnoCoTTool:
    """
    创建Agno思维链工具实例
    
    参数:
        name: 工具名称
        llm: 语言模型实例
        
    返回:
        配置好的Agno思维链工具
    """
    return AgnoCoTTool(name=name, llm=llm)

def get_agno_cot_tool(llm=None) -> AgnoCoTTool:
    """
    获取Agno思维链工具实例
    
    参数:
        llm: 语言模型实例
        
    返回:
        配置好的Agno思维链工具
    """
    return AgnoCoTTool(llm=llm)

def create_agno_reasoning_collection(llm=None) -> AgnoReasoningToolCollection:
    """
    创建Agno推理工具集合
    
    参数:
        llm: 语言模型实例
        
    返回:
        推理工具集合
    """
    return AgnoReasoningToolCollection(llm=llm)

# 兼容性包装器
class AgnoCoTToolWrapper:
    """Agno思维链工具包装器，提供与LlamaIndex兼容的接口"""
    
    def __init__(self, llm=None):
        self.tool = AgnoCoTTool(llm=llm)
    
    def run(self, query: str, **kwargs) -> str:
        """
        运行推理，返回文本格式结果
        
        参数:
            query: 查询内容
            **kwargs: 其他参数
            
        返回:
            推理结果的文本表示
        """
        return self.tool.simple_reason(query, **kwargs)

# 导出主要组件
__all__ = [
    "AgnoCoTTool",
    "AgnoCoTRequest",
    "AgnoCoTResponse", 
    "AgnoReasoningToolCollection",
    "create_agno_cot_tool",
    "get_agno_cot_tool",
    "create_agno_reasoning_collection",
    "AgnoCoTToolWrapper"
] 