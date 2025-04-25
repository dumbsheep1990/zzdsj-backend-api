"""
框架工厂模块: 提供用于创建不同AI框架助手的工厂
"""

import logging
from typing import Dict, Any, Optional, Union, List

logger = logging.getLogger(__name__)

class AgentFrameworkFactory:
    """AI框架工厂类"""
    
    def __init__(self, framework_name: str):
        """
        初始化框架工厂
        
        参数:
            framework_name: 框架名称
        """
        self.framework_name = framework_name.lower()
    
    async def create_agent(self, name: str, description: Optional[str] = None,
                          knowledge_bases: Optional[List[str]] = None,
                          model: Optional[str] = None,
                          settings: Optional[Dict[str, Any]] = None) -> Any:
        """
        创建代理实例
        
        参数:
            name: 代理名称
            description: 代理描述
            knowledge_bases: 知识库ID列表
            model: 使用的模型
            settings: 其他设置
            
        返回:
            代理实例
        """
        try:
            if self.framework_name == "llamaindex":
                from app.frameworks.llamaindex.agent import create_llamaindex_agent
                return await create_llamaindex_agent(
                    name=name,
                    description=description,
                    knowledge_bases=knowledge_bases,
                    model=model,
                    settings=settings
                )
                
            elif self.framework_name == "haystack":
                from app.frameworks.haystack.agent import create_haystack_agent
                return await create_haystack_agent(
                    name=name,
                    description=description,
                    knowledge_bases=knowledge_bases,
                    model=model,
                    settings=settings
                )
                
            elif self.framework_name == "agno":
                from app.frameworks.agno.agent import create_knowledge_agent
                return await create_knowledge_agent(
                    name=name,
                    description=description,
                    knowledge_bases=knowledge_bases,
                    model=model,
                    settings=settings
                )
                
            else:
                raise ValueError(f"不支持的框架: {self.framework_name}")
        
        except Exception as e:
            logger.error(f"创建{self.framework_name}代理时出错: {str(e)}")
            raise

def get_agent_framework(framework_name: str) -> AgentFrameworkFactory:
    """
    获取框架工厂实例
    
    参数:
        framework_name: 框架名称
        
    返回:
        框架工厂实例
    """
    # 检查是否是支持的框架
    framework_name = framework_name.lower()
    supported_frameworks = ["llamaindex", "haystack", "agno"]
    
    if framework_name not in supported_frameworks:
        logger.warning(f"未知框架: {framework_name}，使用默认的llamaindex")
        framework_name = "llamaindex"
    
    return AgentFrameworkFactory(framework_name)
