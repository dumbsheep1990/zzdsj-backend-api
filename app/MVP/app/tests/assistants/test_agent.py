"""
智能体服务单元测试
"""
import pytest
from app.services.assistants.agent import AgentService
from app.core.assistants.exceptions import ValidationError


class TestAgentService:
    """智能体服务测试类"""

    @pytest.fixture
    def service(self, db):
        """创建服务实例"""
        return AgentService(db)

    async def test_process_task_default_framework(self, service):
        """测试使用默认框架处理任务"""
        # 执行
        result, metadata = await service.process_task(
            task="帮我分析这段代码的复杂度"
        )

        # 断言
        assert result is not None
        assert metadata["framework"] == "langchain"

    async def test_process_task_with_tools(self, service):
        """测试使用工具处理任务"""
        # 执行
        result, metadata = await service.process_task(
            task="搜索最新的Python教程",
            tools=["web_search"]
        )

        # 断言
        assert result is not None
        assert "web_search" in metadata["tools_used"]

    async def test_process_task_invalid_framework(self, service):
        """测试使用无效框架"""
        # 执行并断言
        with pytest.raises(ValidationError) as exc_info:
            await service.process_task(
                task="测试任务",
                framework="invalid_framework"
            )

        assert "不支持的框架" in str(exc_info.value)

    async def test_process_task_invalid_tool(self, service):
        """测试使用无效工具"""
        # 执行并断言
        with pytest.raises(ValidationError) as exc_info:
            await service.process_task(
                task="测试任务",
                tools=["invalid_tool"]
            )

        assert "不支持的工具" in str(exc_info.value)

    def test_list_frameworks(self, service):
        """测试列出框架"""
        # 执行
        frameworks = service.list_frameworks()

        # 断言
        assert len(frameworks) > 0
        assert any(f["name"] == "langchain" for f in frameworks)
        assert all("name" in f and "description" in f for f in frameworks)

    def test_list_tools(self, service):
        """测试列出工具"""
        # 执行
        tools = service.list_tools()

        # 断言
        assert len(tools) > 0
        assert any(t["id"] == "web_search" for t in tools)
        assert all("name" in t and "type" in t for t in tools)