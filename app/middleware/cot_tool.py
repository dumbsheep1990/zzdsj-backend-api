"""
思维链(Chain of Thought)工具中间件
提供统一的CoT工具接口，支持模型的思维链功能
"""

import logging
from typing import List, Dict, Any, Optional, Union, Callable
from pydantic import BaseModel, Field

from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.llms import LLM

from app.middleware.cot_manager import CoTManager
from app.middleware.deep_research import get_deep_research_tool

logger = logging.getLogger(__name__)

class CoTRequest(BaseModel):
    """CoT请求参数模型"""
    query: str = Field(..., description="用户查询内容")
    system_prompt: Optional[str] = Field(None, description="系统提示，控制模型角色和行为")
    enable_cot: bool = Field(True, description="是否启用思维链")
    use_multi_step: bool = Field(False, description="是否使用多步骤思维链格式")
    temperature: float = Field(0.3, description="温度参数，控制输出随机性")
    max_tokens: Optional[int] = Field(None, description="最大输出token数")

class CoTTool(BaseTool):
    """思维链工具，基于LlamaIndex实现"""
    
    def __init__(self, name: str = "cot_reasoning", llm: Optional[LLM] = None):
        """
        初始化思维链工具
        
        参数:
            name: 工具名称
            llm: 语言模型实例，如果为None则使用全局设置的模型
        """
        super().__init__(name=name)
        self.cot_manager = CoTManager(llm=llm)
        self.description = (
            "使用思维链(Chain of Thought)进行推理，展示清晰的思考过程和最终答案。"
            "适用于需要深入分析、逐步推理或说明思考过程的复杂问题。"
        )
    
    async def _arun(
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
        异步执行思维链推理
        
        参数:
            query: 用户查询内容
            system_prompt: 系统提示，控制模型角色和行为
            enable_cot: 是否启用思维链
            use_multi_step: 是否使用多步骤思维链格式
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            show_cot: 是否在输出中显示思维过程
            
        返回:
            包含思维链和最终答案的结果
        """
        try:
            result = await self.cot_manager.acall_with_cot(
                prompt_content=query,
                system_prompt=system_prompt,
                enable_cot=enable_cot,
                use_multi_step=use_multi_step,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 格式化响应
            formatted_result = self.cot_manager.format_response_for_api(
                result,
                show_cot=show_cot
            )
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"执行思维链推理时出错: {str(e)}")
            return {
                "final_answer": f"执行推理时出错: {str(e)}",
                "show_cot": False
            }
    
    def _run(
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
        同步执行思维链推理
        
        参数:
            query: 用户查询内容
            system_prompt: 系统提示，控制模型角色和行为
            enable_cot: 是否启用思维链
            use_multi_step: 是否使用多步骤思维链格式
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            show_cot: 是否在输出中显示思维过程
            
        返回:
            包含思维链和最终答案的结果
        """
        try:
            result = self.cot_manager.call_with_cot(
                prompt_content=query,
                system_prompt=system_prompt,
                enable_cot=enable_cot,
                use_multi_step=use_multi_step,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 格式化响应
            formatted_result = self.cot_manager.format_response_for_api(
                result,
                show_cot=show_cot
            )
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"执行思维链推理时出错: {str(e)}")
            return {
                "final_answer": f"执行推理时出错: {str(e)}",
                "show_cot": False
            }

def get_cot_tool(llm: Optional[LLM] = None) -> BaseTool:
    """
    获取思维链工具实例
    
    参数:
        llm: 语言模型实例，如果为None则使用全局设置的模型
        
    返回:
        配置好的思维链工具
    """
    return CoTTool(llm=llm)

def create_cot_function_tool(llm: Optional[LLM] = None) -> FunctionTool:
    """
    创建基于函数的思维链工具
    
    参数:
        llm: 语言模型实例，如果为None则使用全局设置的模型
        
    返回:
        配置好的函数工具
    """
    cot_tool = CoTTool(llm=llm)
    
    def cot_reasoning(
        query: str,
        system_prompt: Optional[str] = None,
        enable_cot: bool = True,
        use_multi_step: bool = False,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        show_cot: bool = True
    ) -> Dict[str, Any]:
        """
        使用思维链进行推理，展示清晰的思考过程和最终答案
        
        参数:
            query: 用户查询内容
            system_prompt: 系统提示，控制模型角色和行为
            enable_cot: 是否启用思维链
            use_multi_step: 是否使用多步骤思维链格式
            temperature: 温度参数，控制输出随机性
            max_tokens: 最大输出token数
            show_cot: 是否在输出中显示思维过程
            
        返回:
            包含思维链和最终答案的结果
        """
        return cot_tool._run(
            query=query,
            system_prompt=system_prompt,
            enable_cot=enable_cot,
            use_multi_step=use_multi_step,
            temperature=temperature,
            max_tokens=max_tokens,
            show_cot=show_cot
        )
    
    return FunctionTool.from_defaults(
        fn=cot_reasoning,
        name="cot_reasoning",
        description=(
            "使用思维链(Chain of Thought)进行推理，展示清晰的思考过程和最终答案。"
            "适用于需要深入分析、逐步推理或说明思考过程的复杂问题。"
        )
    )

def get_all_cot_tools(llm: Optional[LLM] = None) -> List[BaseTool]:
    """
    获取所有CoT相关工具
    
    参数:
        llm: 语言模型实例，如果为None则使用全局设置的模型
        
    返回:
        CoT工具列表
    """
    cot_manager = CoTManager(llm=llm)
    
    tools = [
        # 基础思维链工具
        CoTTool(llm=llm),
        
        # 深度研究工具
        get_deep_research_tool(cot_manager=cot_manager)
    ]
    
    return tools
