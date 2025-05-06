"""
深度研究(Deep Research)工具模块
提供多步骤思维链和Web搜索的集成，用于复杂问题的深入研究
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple

from llama_index.core import Settings
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.callbacks import CallbackManager
from llama_index.core.llms.base import LLM

from app.middleware.cot_manager import CoTManager
from app.middleware.search_tool import get_search_tool
from app.middleware.deep_research_service import get_deep_research_service, DeepResearchService

logger = logging.getLogger(__name__)

class DeepResearchTool(BaseTool):
    """
    深度研究工具
    集成Web搜索和多步骤思维链，用于复杂问题分析
    """
    
    def __init__(
        self,
        name: str = "deep_research",
        description: str = None,
        cot_manager: Optional[CoTManager] = None,
        search_tool: Optional[BaseTool] = None,
        max_research_steps: int = 3,
        enable_cot_display: bool = True,
        deep_research_service: Optional[DeepResearchService] = None
    ):
        """
        初始化深度研究工具
        
        参数:
            name: 工具名称
            description: 工具描述
            cot_manager: CoT管理器实例，如果为None则创建新实例
            search_tool: 搜索工具实例，如果为None则获取默认搜索工具
            max_research_steps: 最大研究步骤数
            enable_cot_display: 是否默认启用CoT显示
            deep_research_service: 深度研究服务实例，如果为None则创建新实例
        """
        description = description or (
            "进行深度研究，分析复杂问题并提供详细的多步骤推理过程。"
            "此工具结合了Web搜索和结构化思维链，适用于需要深入研究的复杂问题。"
        )
        
        super().__init__(name=name, metadata={"description": description})
        
        self.cot_manager = cot_manager or CoTManager()
        self.search_tool = search_tool or get_search_tool()
        self.max_research_steps = max_research_steps
        self.enable_cot_display = enable_cot_display
        
        # 初始化或使用提供的深度研究服务
        self.deep_research_service = deep_research_service or get_deep_research_service(
            cot_manager=self.cot_manager,
            search_tool=self.search_tool,
            max_sub_questions=max_research_steps,
            enable_cot_display=enable_cot_display
        )
    
    async def _arun(
        self,
        query: str,
        research_depth: int = 2,
        search_engines: Optional[List[str]] = None,
        language: str = "zh-CN",
        show_cot: Optional[bool] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        异步执行深度研究
        
        参数:
            query: 研究问题
            research_depth: 研究深度，控制研究步骤数，最大不超过max_research_steps
            search_engines: 搜索引擎列表，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            show_cot: 是否在响应中显示CoT过程，默认为None表示使用工具的默认设置
            temperature: 温度参数，控制LLM输出随机性
            
        返回:
            包含研究结果和思维链的字典
        """
        # 确定是否显示CoT
        show_cot = self.enable_cot_display if show_cot is None else show_cot
        
        # 限制研究深度
        research_depth = min(research_depth, self.max_research_steps)
        
        try:
            logger.info(f"开始深度研究: {query}")
            
            # 使用深度研究服务
            result = await self.deep_research_service.run(
                main_topic=query,
                num_sub_questions=research_depth,
                urls_per_query=3,
                language=language,
                show_cot=show_cot,
                temperature=temperature
            )
            
            return result
            
        except Exception as e:
            logger.error(f"执行深度研究时出错: {str(e)}")
            return {
                "original_query": query,
                "final_answer": f"执行深度研究时出错: {str(e)}",
                "show_cot": False
            }
    
    def _run(
        self,
        query: str,
        research_depth: int = 2,
        search_engines: Optional[List[str]] = None,
        language: str = "zh-CN",
        show_cot: Optional[bool] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        同步执行深度研究（包装异步方法）
        
        参数:
            query: 研究问题
            research_depth: 研究深度，控制研究步骤数
            search_engines: 搜索引擎列表，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            show_cot: 是否在响应中显示CoT过程，默认为None表示使用工具的默认设置
            temperature: 温度参数，控制LLM输出随机性
            
        返回:
            包含研究结果和思维链的字典
        """
        return asyncio.run(self._arun(
            query=query,
            research_depth=research_depth,
            search_engines=search_engines,
            language=language,
            show_cot=show_cot,
            temperature=temperature
        ))

def get_deep_research_tool(
    cot_manager: Optional[CoTManager] = None,
    search_tool: Optional[BaseTool] = None,
    max_research_steps: int = 3,
    enable_cot_display: bool = True
) -> DeepResearchTool:
    """
    获取深度研究工具实例
    
    参数:
        cot_manager: CoT管理器实例，如果为None则创建新实例
        search_tool: 搜索工具实例，如果为None则获取默认搜索工具
        max_research_steps: 最大研究步骤数
        enable_cot_display: 是否默认启用CoT显示
        
    返回:
        配置好的深度研究工具
    """
    return DeepResearchTool(
        cot_manager=cot_manager,
        search_tool=search_tool,
        max_research_steps=max_research_steps,
        enable_cot_display=enable_cot_display
    )

def create_deep_research_function_tool(
    cot_manager: Optional[CoTManager] = None,
    search_tool: Optional[BaseTool] = None,
    max_research_steps: int = 3,
    enable_cot_display: bool = True
) -> FunctionTool:
    """
    创建基于函数的深度研究工具
    
    参数:
        cot_manager: CoT管理器实例，如果为None则创建新实例
        search_tool: 搜索工具实例，如果为None则获取默认搜索工具
        max_research_steps: 最大研究步骤数
        enable_cot_display: 是否默认启用CoT显示
        
    返回:
        配置好的函数工具
    """
    deep_research_tool = get_deep_research_tool(
        cot_manager=cot_manager,
        search_tool=search_tool,
        max_research_steps=max_research_steps,
        enable_cot_display=enable_cot_display
    )
    
    def deep_research(
        query: str,
        research_depth: int = 2,
        search_engines: Optional[List[str]] = None,
        language: str = "zh-CN",
        show_cot: Optional[bool] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        执行深度研究，分析复杂问题并提供详细的多步骤推理过程
        
        参数:
            query: 研究问题
            research_depth: 研究深度，控制研究步骤数，最大不超过3
            search_engines: 搜索引擎列表，可选值：google, bing, baidu等，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            show_cot: 是否在响应中显示思维链过程，默认为系统设置
            temperature: 温度参数，控制输出随机性，默认为0.3
            
        返回:
            包含研究结果和思维链的响应
        """
        return deep_research_tool._run(
            query=query,
            research_depth=research_depth,
            search_engines=search_engines,
            language=language,
            show_cot=show_cot,
            temperature=temperature
        )
    
    return FunctionTool.from_defaults(
        fn=deep_research,
        name="deep_research",
        description=(
            "进行深度研究，分析复杂问题并提供详细的多步骤推理过程。"
            "此工具结合了Web搜索和结构化思维链，适用于需要深入研究的复杂问题。"
        )
    )
