"""
MCP服务管理和集成测试
"""
import pytest
import os
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models.mcp import MCPServiceConfig, MCPTool
from app.repositories.mcp import MCPServiceRepository, MCPToolRepository
from core.mcp_service_manager import MCPServiceManager
from app.utils.core.database import SessionLocal

client = TestClient(app)

# 测试数据
TEST_SERVICE_CONFIG = {
    "deployment_id": "test-mcp-1",
    "name": "测试MCP服务",
    "description": "用于测试的MCP服务",
    "version": "1.0.0",
    "image": "testmcp:latest",
    "port": 8000,
    "status": "running",
    "docker_config": {
        "container_name": "test-mcp-1",
        "host_port": 9001
    }
}

TEST_TOOL = {
    "deployment_id": "test-mcp-1",
    "name": "test_tool",
    "description": "测试工具",
    "category": "测试",
    "schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        "required": ["param1"]
    },
    "examples": [
        {"param1": "test", "param2": 123},
        {"param1": "example", "param2": 456}
    ]
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
def mock_docker():
    """模拟Docker容器操作"""
    with patch("app.core.mcp_service_manager.docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        # 模拟容器
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.logs.return_value = "MCP服务启动成功".encode('utf-8')
        
        # 模拟容器集合
        mock_containers = MagicMock()
        mock_containers.get.return_value = mock_container
        mock_containers.list.return_value = [mock_container]
        
        # 设置client.containers属性
        mock_client.containers = mock_containers
        
        yield mock_client


@pytest.fixture
def mock_http_client():
    """模拟HTTP客户端"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        # 模拟工具列表响应
        mock_instance.get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "测试工具"
                    }
                ]
            })
        )
        
        # 模拟工具schema响应
        mock_instance.get.return_value.json.return_value = TEST_TOOL["schema"]
        
        yield mock_instance


class TestMCPServiceAPI:
    """MCP服务API测试类"""
    
    def test_list_services(self, db_session, mock_docker):
        """测试获取MCP服务列表"""
        # 准备数据
        repo = MCPServiceRepository(db_session)
        service_config = MCPServiceConfig(**TEST_SERVICE_CONFIG)
        db_session.add(service_config)
        db_session.commit()
        
        # 发送请求
        response = client.get("/api/mcp-services")
        
        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert len(data["services"]) >= 1
        
        # 清理数据
        db_session.delete(service_config)
        db_session.commit()
    
    def test_get_service(self, db_session, mock_docker):
        """测试获取单个MCP服务详情"""
        # 准备数据
        repo = MCPServiceRepository(db_session)
        service_config = MCPServiceConfig(**TEST_SERVICE_CONFIG)
        db_session.add(service_config)
        db_session.commit()
        
        # 发送请求
        response = client.get(f"/api/mcp-services/{TEST_SERVICE_CONFIG['deployment_id']}")
        
        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["deployment_id"] == TEST_SERVICE_CONFIG["deployment_id"]
        assert data["name"] == TEST_SERVICE_CONFIG["name"]
        
        # 清理数据
        db_session.delete(service_config)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self, mock_docker):
        """测试MCP服务生命周期管理"""
        manager = MCPServiceManager()
        
        # 测试启动
        with patch.object(manager, "_get_service_config", return_value=TEST_SERVICE_CONFIG):
            result = await manager.start_service("test-mcp-1")
            assert result["status"] == "success"
        
        # 测试重启
        with patch.object(manager, "_get_service_config", return_value=TEST_SERVICE_CONFIG):
            result = await manager.restart_service("test-mcp-1")
            assert result["status"] == "success"
        
        # 测试停止
        with patch.object(manager, "_get_service_config", return_value=TEST_SERVICE_CONFIG):
            result = await manager.stop_service("test-mcp-1")
            assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_get_tool_schema(self, mock_http_client):
        """测试获取工具模式定义"""
        manager = MCPServiceManager()
        
        with patch.object(manager, "_get_service_config", return_value=TEST_SERVICE_CONFIG):
            schema = await manager.get_tool_schema("test-mcp-1", "test_tool")
            assert schema["type"] == "object"
            assert "properties" in schema
    
    @pytest.mark.asyncio
    async def test_list_mcp_tools(self, db_session, mock_http_client):
        """测试获取MCP工具列表"""
        # 准备数据
        service_config = MCPServiceConfig(**TEST_SERVICE_CONFIG)
        tool = MCPTool(**TEST_TOOL)
        db_session.add(service_config)
        db_session.add(tool)
        db_session.commit()
        
        # 发送请求
        with patch("app.api.mcp_service.mcp_service_manager"):
            response = client.get("/api/mcp-services/tools")
            
            # 验证结果
            assert response.status_code == 200
            data = response.json()
            assert len(data["tools"]) >= 1
        
        # 清理数据
        db_session.delete(tool)
        db_session.delete(service_config)
        db_session.commit()
