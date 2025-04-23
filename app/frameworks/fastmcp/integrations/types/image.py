"""
图像MCP客户端模块
定义图像生成类型MCP服务的接口
"""

from abc import abstractmethod
from typing import Dict, Any, Optional, List, Union
from .base import BaseMCPClient, ClientCapability

class ImageMCPClient(BaseMCPClient):
    """图像生成类型MCP客户端"""
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        return [ClientCapability.IMAGE_GENERATION, ClientCapability.TOOLS]
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        num_images: int = 1,
        **kwargs
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        生成图像
        
        参数:
            prompt: 图像生成提示
            model: 使用的模型
            size: 图像尺寸
            quality: 图像质量
            style: 图像风格
            num_images: 生成图像数量
            **kwargs: 其他参数
            
        返回:
            生成的图像信息
        """
        pass
    
    @abstractmethod
    async def edit_image(
        self,
        image: Union[str, bytes],
        prompt: str,
        mask: Optional[Union[str, bytes]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        编辑图像
        
        参数:
            image: 原始图像（URL或二进制数据）
            prompt: 编辑提示
            mask: 编辑区域掩码（可选）
            **kwargs: 其他参数
            
        返回:
            编辑后的图像信息
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用的图像生成模型列表
        
        返回:
            模型信息列表
        """
        pass
