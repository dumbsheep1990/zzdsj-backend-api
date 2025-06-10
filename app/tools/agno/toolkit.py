# ZZDSJ Agno工具包 - 统一注册所有工具
from typing import List, Any
from agno import Toolkit
from .manager import AgnoToolsManager
from .custom_tools import ZZDSJCustomTools

class ZZDSJAgnoToolkit(Toolkit):
    """ZZDSJ Agno工具包 - 统一注册所有工具"""
    
    def __init__(self):
        # 初始化Agno现成工具管理器
        self.agno_manager = AgnoToolsManager()
        
        # 初始化自定义工具
        self.custom_tools = ZZDSJCustomTools()
        
        # 合并所有工具
        self.tools = self._combine_all_tools()
    
    def _combine_all_tools(self) -> List[Any]:
        """合并Agno现成工具和自定义工具"""
        # 获取Agno现成工具
        agno_tools = self.agno_manager.get_all_agno_tools()
        
        # 获取自定义工具
        custom_tools = [self.custom_tools]
        
        # 合并返回
        return agno_tools + custom_tools
    
    def get_tools(self) -> List[Any]:
        """获取所有注册的工具"""
        return self.tools
    
    def get_agno_tools_only(self) -> List[Any]:
        """仅获取Agno现成工具"""
        return self.agno_manager.get_all_agno_tools()
    
    def get_custom_tools_only(self) -> List[Any]:
        """仅获取自定义工具"""
        return [self.custom_tools] 