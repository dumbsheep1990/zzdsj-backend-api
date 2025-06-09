"""
助手服务单元测试
"""
import pytest
from app.services.assistants.assistant import AssistantService
from app.schemas.assistants.assistant import AssistantCreateRequest
from app.core.assistants.exceptions import (
    ValidationError,
    QuotaExceededError,
    AssistantNotFoundError,
    PermissionDeniedError
)


class TestAssistantService:
    """助手服务测试类"""

    @pytest.fixture
    def service(self, db):
        """创建服务实例"""
        return AssistantService(db)

    @pytest.fixture
    def valid_assistant_data(self):
        """有效的助手数据"""
        return AssistantCreateRequest(
            name="测试助手",
            description="这是一个测试助手",
            model="deepseek-chat",
            system_prompt="你是一个有帮助的助手",
            capabilities=["text", "code"],
            category="通用",
            tags=["测试", "示例"],
            is_public=False
        )

    async def test_create_assistant_success(self, service, test_user, valid_assistant_data):
        """测试成功创建助手"""
        # 执行
        assistant = await service.create(valid_assistant_data, test_user.id)

        # 断言
        assert assistant.id is not None
        assert assistant.name == valid_assistant_data.name
        assert assistant.owner_id == test_user.id
        assert assistant.is_active is True

    async def test_create_assistant_invalid_name(self, service, test_user, valid_assistant_data):
        """测试创建助手时名称无效"""
        # 准备
        valid_assistant_data.name = ""

        # 执行并断言
        with pytest.raises(ValidationError) as exc_info:
            await service.create(valid_assistant_data, test_user.id)

        assert "名称不能为空" in str(exc_info.value)

    async def test_create_assistant_invalid_model(self, service, test_user, valid_assistant_data):
        """测试创建助手时模型无效"""
        # 准备
        valid_assistant_data.model = "invalid-model"

        # 执行并断言
        with pytest.raises(ValidationError) as exc_info:
            await service.create(valid_assistant_data, test_user.id)

        assert "不支持的模型" in str(exc_info.value)

    async def test_get_assistant_by_id_success(self, service, test_user, valid_assistant_data):
        """测试成功获取助手"""
        # 准备
        created = await service.create(valid_assistant_data, test_user.id)

        # 执行
        assistant = await service.get_by_id(created.id, test_user.id)

        # 断言
        assert assistant.id == created.id
        assert assistant.name == created.name

    async def test_get_assistant_not_found(self, service, test_user):
        """测试获取不存在的助手"""
        # 执行并断言
        with pytest.raises(AssistantNotFoundError):
            await service.get_by_id(99999, test_user.id)

    async def test_get_private_assistant_no_permission(self, service, test_user, valid_assistant_data):
        """测试获取私有助手时无权限"""
        # 准备
        created = await service.create(valid_assistant_data, test_user.id)
        another_user_id = test_user.id + 1

        # 执行并断言
        with pytest.raises(PermissionDeniedError):
            await service.get_by_id(created.id, another_user_id)

    async def test_update_assistant_success(self, service, test_user, valid_assistant_data):
        """测试成功更新助手"""
        # 准备
        created = await service.create(valid_assistant_data, test_user.id)
        update_data = {"name": "更新后的助手", "description": "更新后的描述"}

        # 执行
        updated = await service.update(created.id, update_data, test_user.id)

        # 断言
        assert updated.name == "更新后的助手"
        assert updated.description == "更新后的描述"

    async def test_update_assistant_no_permission(self, service, test_user, valid_assistant_data):
        """测试更新助手时无权限"""
        # 准备
        created = await service.create(valid_assistant_data, test_user.id)
        another_user_id = test_user.id + 1

        # 执行并断言
        with pytest.raises(PermissionDeniedError):
            await service.update(created.id, {"name": "新名称"}, another_user_id)

    async def test_delete_assistant_success(self, service, test_user, valid_assistant_data):
        """测试成功删除助手"""
        # 准备
        created = await service.create(valid_assistant_data, test_user.id)

        # 执行
        success = await service.delete(created.id, test_user.id)

        # 断言
        assert success is True

        # 验证软删除
        with pytest.raises(AssistantNotFoundError):
            await service.get_by_id(created.id, test_user.id)

    async def test_list_assistants_with_filters(self, service, test_user, db):
        """测试带过滤条件的助手列表"""
        # 准备 - 创建多个助手
        assistants_data = [
            {"name": "Python助手", "category": "编程", "is_public": True},
            {"name": "数学助手", "category": "教育", "is_public": True},
            {"name": "私有助手", "category": "通用", "is_public": False}
        ]

        for data in assistants_data:
            assistant_data = AssistantCreateRequest(
                name=data["name"],
                model="deepseek-chat",
                category=data["category"],
                is_public=data["is_public"]
            )
            await service.create(assistant_data, test_user.id)

        # 测试分类过滤
        result = await service.list(
            user_id=test_user.id,
            filters={"category": "编程"}
        )
        assert result.total == 1
        assert result.items[0].name == "Python助手"

        # 测试公开性过滤
        result = await service.list(
            user_id=test_user.id,
            filters={"is_public": True}
        )
        assert result.total == 2

        # 测试搜索
        result = await service.list(
            user_id=test_user.id,
            filters={"search": "数学"}
        )
        assert result.total == 1
        assert result.items[0].name == "数学助手"