"""
地图MCP客户端模块
定义地图和地理位置类型MCP服务的接口
"""

from abc import abstractmethod
from typing import Dict, Any, Optional, List, Union, Tuple
from .base import BaseMCPClient, ClientCapability

class MapMCPClient(BaseMCPClient):
    """地图类型MCP客户端"""
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        return [ClientCapability.MAPS, ClientCapability.GEOCODING, ClientCapability.TOOLS]
    
    @abstractmethod
    async def geocode(
        self,
        address: str,
        region: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        地理编码（地址转坐标）
        
        参数:
            address: 地址
            region: 区域代码
            **kwargs: 其他参数
            
        返回:
            地理编码结果
        """
        pass
    
    @abstractmethod
    async def reverse_geocode(
        self,
        location: Union[str, Tuple[float, float]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        逆地理编码（坐标转地址）
        
        参数:
            location: 位置坐标（"lat,lng"字符串或(lat, lng)元组）
            **kwargs: 其他参数
            
        返回:
            逆地理编码结果
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        location: Optional[Union[str, Tuple[float, float]]] = None,
        radius: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """
        位置搜索
        
        参数:
            query: 搜索关键词
            location: 搜索中心点坐标（可选）
            radius: 搜索半径（米）
            page: 页码
            page_size: 每页结果数
            **kwargs: 其他参数
            
        返回:
            搜索结果
        """
        pass
    
    @abstractmethod
    async def get_route(
        self,
        origin: Union[str, Tuple[float, float]],
        destination: Union[str, Tuple[float, float]],
        mode: str = "driving",
        waypoints: Optional[List[Union[str, Tuple[float, float]]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取路线规划
        
        参数:
            origin: 起点坐标
            destination: 终点坐标
            mode: 出行方式（driving, walking, transit, cycling）
            waypoints: 途经点
            **kwargs: 其他参数
            
        返回:
            路线规划结果
        """
        pass
