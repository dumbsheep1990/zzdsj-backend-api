from typing import Any, Dict, List, Optional
import os
import json

class MCPToolkit:
    """MCP工具包，将MCP服务器提供的工具封装为OWL可用的工具"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化MCP工具包
        
        Args:
            config_path: MCP配置文件路径
        """
        self.config_path = config_path
        self.tools = []
        self.server_name = None
        self.resources = {}
        self.connected = False
        
    async def connect(self) -> None:
        """连接到MCP服务器并加载工具"""
        if not self.config_path or not os.path.exists(self.config_path):
            raise ValueError(f"MCP配置文件不存在: {self.config_path}")
            
        try:
            # 加载MCP配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            self.server_name = config.get("server_name", "default")
            
            # TODO: 实际实现时，使用API连接MCP服务器并加载资源
            # 目前使用模拟实现
            await self._mock_load_resources()
            
            self.connected = True
        except Exception as e:
            raise ValueError(f"MCP连接失败: {str(e)}")
    
    async def _mock_load_resources(self) -> None:
        """模拟加载MCP资源"""
        # 模拟资源列表
        mock_resources = [
            {"name": "web_search", "description": "搜索网络信息", "type": "tool"},
            {"name": "file_upload", "description": "上传文件", "type": "tool"},
            {"name": "code_execution", "description": "执行代码", "type": "tool"},
            {"name": "image_analysis", "description": "分析图像", "type": "tool"}
        ]
        
        # 创建工具
        for resource in mock_resources:
            # 将资源添加到资源字典
            self.resources[resource["name"]] = resource
            
            # 创建对应的工具
            tool = MCPTool(
                server_name=self.server_name,
                name=resource["name"],
                description=resource["description"]
            )
            self.tools.append(tool)
    
    async def list_resources(self, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出MCP服务器提供的资源
        
        Args:
            resource_type: 资源类型过滤器
            
        Returns:
            List[Dict[str, Any]]: 资源列表
        """
        if not self.connected:
            await self.connect()
            
        # 按类型过滤资源
        if resource_type:
            return [r for r in self.resources.values() if r.get("type") == resource_type]
        else:
            return list(self.resources.values())
    
    def get_tools(self) -> List[Any]:
        """获取所有工具
        
        Returns:
            List[Any]: 工具列表
        """
        return self.tools


class MCPTool:
    """MCP工具，包装MCP服务器的工具为可调用对象"""
    
    def __init__(self, server_name: str, name: str, description: str):
        """初始化MCP工具
        
        Args:
            server_name: 服务器名称
            name: 工具名称
            description: 工具描述
        """
        self.server_name = server_name
        self.name = name
        self.description = description
        self.uri = None
        self.tool_params = []
        self.tool_returns = None
        self.loaded = False

    async def load_details(self) -> None:
        """加载工具详细信息"""
        if self.loaded:
            return
            
        # 在真实实现中，从MCP服务器获取工具详情
        # 例如：params，返回类型等
        try:
            from core.mcp_service_manager import MCPServiceManager
            mcp_manager = MCPServiceManager()
            
            # 获取工具详情
            tool_details = await mcp_manager.get_resource_details(self.server_name, self.name)
            
            if tool_details:
                self.uri = tool_details.get("uri")
                self.tool_params = tool_details.get("params", [])
                self.tool_returns = tool_details.get("returns")
                self.loaded = True
            else:
                # 如果获取失败，使用默认值
                self._set_default_details()
        except Exception as e:
            # 如果获取失败，使用默认值
            self._set_default_details()
    
    def _set_default_details(self) -> None:
        """设置默认工具详情"""
        # 设置通用参数
        self.tool_params = [
            {"name": "query", "type": "string", "description": "查询内容"}
        ]
        self.tool_returns = {"type": "object", "description": "工具执行结果"}
        self.uri = f"mcp://{self.server_name}/{self.name}"
        self.loaded = True
    
    async def __call__(self, **kwargs) -> Dict[str, Any]:
        """调用MCP工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            Dict[str, Any]: 工具执行结果
        """
        if not self.loaded:
            await self.load_details()
            
        # 验证参数
        if self.tool_params:
            self._validate_params(kwargs)
            
        try:
            # 实际调用MCP工具
            from core.mcp_service_manager import MCPServiceManager
            mcp_manager = MCPServiceManager()
            
            # 执行工具调用
            result = await mcp_manager.execute_resource(
                server_name=self.server_name,
                resource_name=self.name,
                params=kwargs
            )
            
            return result
        except Exception as e:
            # 如果调用失败，返回错误信息
            return {
                "error": str(e),
                "status": "failed"
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> None:
        """验证参数是否符合要求
        
        Args:
            params: 参数字典
            
        Raises:
            ValueError: 参数无效
        """
        for param_def in self.tool_params:
            param_name = param_def.get("name")
            param_required = param_def.get("required", False)
            
            if param_required and param_name not in params:
                raise ValueError(f"缺少必需参数: {param_name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """将工具转换为字典表示
        
        Returns:
            Dict[str, Any]: 工具字典表示
        """
        return {
            "name": self.name,
            "description": self.description,
            "server_name": self.server_name,
            "uri": self.uri,
            "params": self.tool_params,
            "returns": self.tool_returns
        }
    async def __call__(self, *args, **kwargs) -> Any:
        """调用MCP工具
        
        Returns:
            Any: 工具执行结果
        """
        # TODO: 实际实现时，使用API调用MCP工具
        # 目前使用模拟实现
        param_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        return f"调用MCP工具 {self.name}({param_str})"
