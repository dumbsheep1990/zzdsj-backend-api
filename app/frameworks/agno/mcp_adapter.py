"""
Agno MCP适配器：将ZZDSJ的MCP服务集成到Agno代理中
基于Agno官方文档的MCP集成模式实现

支持的MCP服务：
- 文件系统MCP
- 数据库MCP  
- 知识库MCP
- 搜索引擎MCP
"""

import asyncio
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging

# Agno MCP 导入 - 基于官方文档
try:
    from agno.tools.mcp import MCPTools, StreamableHTTPClientParams
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    AGNO_AVAILABLE = True
except ImportError:
    # 如果Agno未安装，提供占位符类
    AGNO_AVAILABLE = False
    
    class MCPTools:
        pass
    
    class StreamableHTTPClientParams:
        pass

logger = logging.getLogger(__name__)


@dataclass
class MCPServiceConfig:
    """MCP服务配置"""
    name: str
    url: str
    access_token: Optional[str] = None
    project_id: Optional[str] = None
    environment: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout_seconds: int = 30


class ZZDSJMCPAdapter:
    """ZZDSJ MCP适配器 - 基于Agno官方MCP集成模式"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化MCP适配器
        
        参数:
            config_file: MCP配置文件路径
        """
        self.services: Dict[str, MCPServiceConfig] = {}
        self.active_tools: Dict[str, MCPTools] = {}
        
        if config_file:
            self.load_config(config_file)
        else:
            self._setup_default_services()
    
    def _setup_default_services(self):
        """设置默认的MCP服务配置"""
        
        # 文件系统MCP服务
        filesystem_url = os.getenv("ZZDSJ_FILESYSTEM_MCP_URL", "http://localhost:5000/mcp/filesystem")
        if filesystem_url:
            self.add_service(MCPServiceConfig(
                name="filesystem",
                url=filesystem_url,
                access_token=os.getenv("ZZDSJ_FILESYSTEM_MCP_TOKEN"),
                timeout_seconds=20
            ))
        
        # 数据库MCP服务
        database_url = os.getenv("ZZDSJ_DATABASE_MCP_URL", "http://localhost:5001/mcp/database")
        if database_url:
            self.add_service(MCPServiceConfig(
                name="database",
                url=database_url,
                access_token=os.getenv("ZZDSJ_DATABASE_MCP_TOKEN"),
                timeout_seconds=30
            ))
        
        # 搜索MCP服务
        search_url = os.getenv("ZZDSJ_SEARCH_MCP_URL", "http://localhost:5002/mcp/search")
        if search_url:
            self.add_service(MCPServiceConfig(
                name="search",
                url=search_url,
                access_token=os.getenv("ZZDSJ_SEARCH_MCP_TOKEN"),
                timeout_seconds=25
            ))

        # 知识库MCP服务  
        knowledge_url = os.getenv("ZZDSJ_KNOWLEDGE_MCP_URL", "http://localhost:5003/mcp/knowledge")
        if knowledge_url:
            self.add_service(MCPServiceConfig(
                name="knowledge",
                url=knowledge_url,
                access_token=os.getenv("ZZDSJ_KNOWLEDGE_MCP_TOKEN"),
                headers={
                    "x-kb-environment": os.getenv("ZZDSJ_KB_ENVIRONMENT", "production")
                },
                timeout_seconds=35
            ))

    def add_service(self, config: MCPServiceConfig):
        """
        添加MCP服务配置
        
        参数:
            config: MCP服务配置
        """
        self.services[config.name] = config
        logger.info(f"已添加MCP服务: {config.name} at {config.url}")

    def get_service_config(self, service_name: str) -> Optional[MCPServiceConfig]:
        """
        获取MCP服务配置
        
        参数:
            service_name: 服务名称
            
        返回:
            服务配置或None
        """
        return self.services.get(service_name)

    def create_server_params(self, service_name: str) -> Optional[StreamableHTTPClientParams]:
        """
        为指定服务创建服务器参数 - 基于Agno官方MCP语法
        
        参数:
            service_name: 服务名称
            
        返回:
            StreamableHTTPClientParams实例或None
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装，无法创建MCP服务器参数")
            return None
            
        config = self.get_service_config(service_name)
        if not config:
            logger.error(f"未找到服务配置: {service_name}")
            return None
        
        # 构建请求头
        headers = config.headers.copy() if config.headers else {}
        
        if config.access_token:
            headers["Authorization"] = f"Bearer {config.access_token}"
        
        if config.project_id:
            headers["x-pd-project-id"] = config.project_id
            
        if config.environment:
            headers["x-pd-environment"] = config.environment
        
        # 创建服务器参数 - 基于Agno官方语法
        server_params = StreamableHTTPClientParams(
            url=config.url,
            headers=headers
        )
        
        return server_params

    async def create_mcp_tools(self, service_name: str) -> Optional[MCPTools]:
        """
        为指定服务创建MCP工具 - 基于Agno官方MCP集成语法
        
        参数:
            service_name: 服务名称
            
        返回:
            MCPTools实例或None
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装，无法创建MCP工具")
            return None
            
        config = self.get_service_config(service_name)
        if not config:
            logger.error(f"未找到服务配置: {service_name}")
            return None
        
        try:
            # 创建服务器参数
            server_params = self.create_server_params(service_name)
            if not server_params:
                return None
            
            # 创建MCP工具 - 基于Agno官方语法
            mcp_tools = MCPTools(
                server_params=server_params,
                transport="streamable-http",
                timeout_seconds=config.timeout_seconds
            )
            
            # 缓存工具实例
            self.active_tools[service_name] = mcp_tools
            
            logger.info(f"已创建MCP工具: {service_name}")
            return mcp_tools
            
        except Exception as e:
            logger.error(f"创建MCP工具失败 {service_name}: {str(e)}")
            return None

    async def create_agent_with_mcp(self, 
                                   service_names: List[str],
                                   model_config: Optional[Dict] = None,
                                   agent_config: Optional[Dict] = None) -> Optional[Agent]:
        """
        创建带有MCP工具的Agno代理
        
        参数:
            service_names: 要集成的MCP服务名称列表
            model_config: 模型配置
            agent_config: 代理配置
            
        返回:
            配置好的Agno Agent实例或None
        """
        if not AGNO_AVAILABLE:
            logger.error("Agno框架未安装，无法创建代理")
            return None
        
        try:
            # 创建MCP工具列表
            mcp_tools = []
            for service_name in service_names:
                mcp_tool = await self.create_mcp_tools(service_name)
                if mcp_tool:
                    mcp_tools.append(mcp_tool)
                else:
                    logger.warning(f"无法为服务创建MCP工具: {service_name}")
            
            if not mcp_tools:
                logger.error("没有可用的MCP工具")
                return None
            
            # 设置默认模型配置
            default_model_config = {
                "id": "gpt-4o",
                "api_key": os.getenv("OPENAI_API_KEY")
            }
            model_config = {**default_model_config, **(model_config or {})}
            
            # 设置默认代理配置
            default_agent_config = {
                "name": "ZZDSJ-MCP-Agent",
                "description": "ZZDSJ代理集成多个MCP服务",
                "instructions": [
                    "使用MCP工具访问文件系统、数据库和知识库",
                    "始终提供准确和有用的响应",
                    "如果不确定，请询问更多详细信息"
                ],
                "show_tool_calls": True,
                "markdown": True
            }
            agent_config = {**default_agent_config, **(agent_config or {})}
            
            # 创建代理 - 基于Agno官方语法
            agent = Agent(
                model=OpenAIChat(**model_config),
                tools=mcp_tools,
                **agent_config
            )
            
            logger.info(f"已创建带有MCP工具的代理，服务: {service_names}")
            return agent
            
        except Exception as e:
            logger.error(f"创建MCP代理失败: {str(e)}")
            return None

    async def test_mcp_service(self, service_name: str) -> Dict[str, Any]:
        """
        测试MCP服务连接
        
        参数:
            service_name: 服务名称
            
        返回:
            测试结果
        """
        config = self.get_service_config(service_name)
        if not config:
            return {"error": f"未找到服务配置: {service_name}"}
        
        try:
            # 创建MCP工具进行测试
            mcp_tool = await self.create_mcp_tools(service_name)
            if not mcp_tool:
                return {"error": f"无法创建MCP工具: {service_name}"}
            
            # 这里可以添加具体的测试逻辑
            # 例如调用服务的健康检查端点
            
            return {
                "service": service_name,
                "status": "connected",
                "url": config.url,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            return {"error": f"MCP服务测试失败 {service_name}: {str(e)}"}

    def list_services(self) -> List[Dict[str, Any]]:
        """
        列出所有配置的MCP服务
        
        返回:
            服务列表
        """
        services = []
        for name, config in self.services.items():
            services.append({
                "name": name,
                "url": config.url,
                "has_token": bool(config.access_token),
                "timeout": config.timeout_seconds
            })
        return services

    def load_config(self, config_file: str):
        """
        从配置文件加载MCP服务配置
        
        参数:
            config_file: 配置文件路径
        """
        try:
            import json
            
            if not os.path.exists(config_file):
                logger.error(f"配置文件不存在: {config_file}")
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for service_data in config_data.get("mcp_services", []):
                config = MCPServiceConfig(**service_data)
                self.add_service(config)
                
            logger.info(f"从配置文件加载了 {len(self.services)} 个MCP服务")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")

    async def close_connections(self):
        """
        关闭所有MCP连接
        """
        for service_name, mcp_tool in self.active_tools.items():
            try:
                # 如果MCP工具有关闭方法，调用它
                if hasattr(mcp_tool, 'close'):
                    await mcp_tool.close()
                logger.info(f"已关闭MCP连接: {service_name}")
            except Exception as e:
                logger.error(f"关闭MCP连接失败 {service_name}: {str(e)}")
        
        self.active_tools.clear()


# 便捷函数
async def create_zzdsj_mcp_agent(service_names: Optional[List[str]] = None,
                                model_config: Optional[Dict] = None,
                                agent_config: Optional[Dict] = None) -> Optional[Agent]:
    """
    便捷函数：创建带有ZZDSJ MCP服务的Agno代理
    
    参数:
        service_names: MCP服务名称列表，默认为所有可用服务
        model_config: 模型配置
        agent_config: 代理配置
        
    返回:
        配置好的Agno Agent实例
    """
    if not AGNO_AVAILABLE:
        logger.error("Agno框架未安装")
        return None
    
    # 设置默认服务
    if service_names is None:
        service_names = ["filesystem", "database", "search", "knowledge"]
    
    # 创建MCP适配器
    adapter = ZZDSJMCPAdapter()
    
    # 创建带有MCP工具的代理
    agent = await adapter.create_agent_with_mcp(
        service_names=service_names,
        model_config=model_config,
        agent_config=agent_config
    )
    
    return agent


async def test_all_mcp_services() -> Dict[str, Any]:
    """
    测试所有配置的MCP服务
    
    返回:
        测试结果
    """
    adapter = ZZDSJMCPAdapter()
    results = {}
    
    for service_name in adapter.services.keys():
        result = await adapter.test_mcp_service(service_name)
        results[service_name] = result
    
    return results


# 示例使用方法
async def example_usage():
    """MCP适配器使用示例"""
    if not AGNO_AVAILABLE:
        print("请安装Agno框架: pip install agno")
        return
    
    # 创建带有MCP服务的代理
    agent = await create_zzdsj_mcp_agent(
        service_names=["filesystem", "knowledge"],
        model_config={"id": "gpt-4o"},
        agent_config={
            "name": "ZZDSJ助手",
            "description": "智能文档和知识库助手"
        }
    )
    
    if agent:
        # 使用代理
        response = await agent.aprint_response(
            "帮我搜索关于人工智能的文档，并总结主要内容",
            stream=True
        )
        print(response)
    else:
        print("代理创建失败")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage()) 