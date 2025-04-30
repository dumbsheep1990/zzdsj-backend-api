"""
LlamaIndex与MCP集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.frameworks.llamaindex.mcp_client import MCPToolClient
from app.frameworks.llamaindex.mcp_requests import MCPRequestBuilder
from app.frameworks.llamaindex.tools import create_mcp_tool, get_all_mcp_tools
from app.frameworks.integration.mcp_integration import MCPIntegrationService
from app.utils.database import SessionLocal


# 测试数据
TEST_TOOL_INFO = {
    "name": "test_calculator",
    "description": "一个简单的计算器工具",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "要执行的数学运算"
            },
            "a": {
                "type": "number",
                "description": "第一个操作数"
            },
            "b": {
                "type": "number",
                "description": "第二个操作数"
            }
        },
        "required": ["operation", "a", "b"]
    }
}

TEST_PARAMS = {
    "operation": "add",
    "a": 5,
    "b": 3
}

TEST_RESULT = {
    "result": 8
}


@pytest.fixture
def db_session():
    """提供数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def mock_mcp_client():
    """模拟MCP客户端"""
    with patch("app.frameworks.llamaindex.mcp_client.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        # 模拟工具调用响应
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = TEST_RESULT
        mock_instance.post.return_value = mock_response
        
        # 模拟工具schema响应
        mock_schema_response = AsyncMock()
        mock_schema_response.status_code = 200
        mock_schema_response.json.return_value = TEST_TOOL_INFO["parameters"]
        
        # 模拟工具示例响应
        mock_examples_response = AsyncMock()
        mock_examples_response.status_code = 200
        mock_examples_response.json.return_value = [TEST_PARAMS]
        
        # 为不同URL设置不同响应
        def mock_get(url, *args, **kwargs):
            if "schema" in url:
                return mock_schema_response
            elif "examples" in url:
                return mock_examples_response
            return mock_response
        
        mock_instance.get = mock_get
        
        yield mock_instance


class TestLlamaIndexMCPIntegration:
    """LlamaIndex与MCP集成测试类"""
    
    @pytest.mark.asyncio
    async def test_mcp_request_builder(self):
        """测试MCP请求构建器"""
        # 构建请求
        request = MCPRequestBuilder.build_tool_request(
            tool_name=TEST_TOOL_INFO["name"],
            params=TEST_PARAMS
        )
        
        # 验证结果
        assert request["name"] == TEST_TOOL_INFO["name"]
        assert request["parameters"] == TEST_PARAMS
        assert "metadata" in request
    
    @pytest.mark.asyncio
    async def test_mcp_tool_client(self, mock_mcp_client):
        """测试MCP工具客户端"""
        client = MCPToolClient(base_url="http://localhost:8000")
        
        # 测试调用工具
        result = await client.call_tool(
            tool_name=TEST_TOOL_INFO["name"],
            params=TEST_PARAMS
        )
        
        # 验证结果
        assert result == TEST_RESULT
        
        # 测试获取工具schema
        schema = await client.get_tool_schema(TEST_TOOL_INFO["name"])
        assert schema["type"] == "object"
        assert "properties" in schema
        
        # 测试获取工具示例
        examples = await client.get_tool_examples(TEST_TOOL_INFO["name"])
        assert len(examples) > 0
        assert "operation" in examples[0]
    
    @pytest.mark.asyncio
    async def test_create_mcp_tool(self, mock_mcp_client):
        """测试创建MCP工具为LlamaIndex工具"""
        # 模拟集成服务
        with patch("app.frameworks.llamaindex.tools.MCPToolClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # 模拟客户端方法
            mock_client.get_tool_schema.return_value = TEST_TOOL_INFO["parameters"]
            mock_client.call_tool.return_value = TEST_RESULT
            
            # 创建工具
            tool = await create_mcp_tool(
                tool_name=TEST_TOOL_INFO["name"],
                description=TEST_TOOL_INFO["description"]
            )
            
            # 验证工具属性
            assert tool.name == TEST_TOOL_INFO["name"]
            assert tool.description == TEST_TOOL_INFO["description"]
            
            # 测试工具调用
            result = await tool(operation="add", a=5, b=3)
            assert result == TEST_RESULT
    
    @pytest.mark.asyncio
    async def test_get_all_mcp_tools(self):
        """测试获取所有MCP工具"""
        # 模拟集成服务
        with patch("app.frameworks.llamaindex.tools.MCPIntegrationService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # 模拟获取工具列表方法
            mock_service.get_all_tool_descriptions.return_value = [
                {
                    "name": TEST_TOOL_INFO["name"],
                    "description": TEST_TOOL_INFO["description"],
                    "deployment_id": "test-mcp-1"
                }
            ]
            
            # 模拟create_mcp_tool
            with patch("app.frameworks.llamaindex.tools.create_mcp_tool") as mock_create_tool:
                mock_tool = MagicMock()
                mock_tool.name = TEST_TOOL_INFO["name"]
                mock_create_tool.return_value = mock_tool
                
                # 获取所有工具
                tools = await get_all_mcp_tools()
                
                # 验证结果
                assert len(tools) > 0
                assert tools[0].name == TEST_TOOL_INFO["name"]
    
    @pytest.mark.asyncio
    async def test_mcp_integration_service(self, db_session):
        """测试MCP集成服务"""
        # 模拟MCP服务仓库
        with patch("app.frameworks.integration.mcp_integration.MCPServiceRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            # 模拟获取工具列表方法
            mock_repo.get_all_tools.return_value = [
                MagicMock(
                    name=TEST_TOOL_INFO["name"],
                    description=TEST_TOOL_INFO["description"],
                    deployment_id="test-mcp-1",
                    schema=TEST_TOOL_INFO["parameters"]
                )
            ]
            
            # 创建集成服务
            service = MCPIntegrationService()
            
            # 获取所有工具描述
            tool_descriptions = await service.get_all_tool_descriptions()
            
            # 验证结果
            assert len(tool_descriptions) > 0
            assert tool_descriptions[0]["name"] == TEST_TOOL_INFO["name"]
            
            # 模拟MCPServiceManager
            with patch("app.frameworks.integration.mcp_integration.MCPServiceManager") as mock_manager_class:
                mock_manager = AsyncMock()
                mock_manager_class.return_value = mock_manager
                
                # 模拟获取工具schema方法
                mock_manager.get_tool_schema.return_value = TEST_TOOL_INFO["parameters"]
                
                # 获取工具schema
                schema = await service.get_tool_schema("test-mcp-1", TEST_TOOL_INFO["name"])
                
                # 验证结果
                assert schema["type"] == "object"
                assert "properties" in schema
