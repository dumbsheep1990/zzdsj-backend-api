"""LLM适配器
将AI知识图谱框架与现有的LlamaIndex LLM服务集成
"""

from typing import Optional, Dict, Any
import logging

from app.frameworks.llamaindex.core import get_llm

logger = logging.getLogger(__name__)


class LLMAdapter:
    """LLM适配器类，封装LlamaIndex LLM调用"""
    
    def __init__(self):
        """初始化LLM适配器"""
        self.llm = get_llm()
        logger.info("LLM适配器初始化完成")
    
    def call_llm(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.8,
        **kwargs
    ) -> str:
        """调用LLM生成响应
        
        Args:
            user_prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            LLM响应文本
        """
        try:
            # 构造消息
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system", 
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": user_prompt
            })
            
            # 调用LlamaIndex LLM
            response = self.llm.chat(messages, max_tokens=max_tokens, temperature=temperature)
            
            # 提取响应内容
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                return response.message.content
            elif hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            raise RuntimeError(f"LLM调用失败: {str(e)}")
    
    def is_available(self) -> bool:
        """检查LLM是否可用
        
        Returns:
            是否可用
        """
        try:
            return self.llm is not None
        except:
            return False


# 全局实例
_llm_adapter = None


def get_llm_adapter() -> LLMAdapter:
    """获取LLM适配器实例
    
    Returns:
        LLM适配器实例
    """
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter()
    return _llm_adapter


def reset_llm_adapter():
    """重置LLM适配器实例"""
    global _llm_adapter
    _llm_adapter = None 