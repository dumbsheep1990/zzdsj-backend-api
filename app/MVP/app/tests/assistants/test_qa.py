"""
问答服务单元测试
"""
import pytest
from app.services.assistants.qa import QAService
from app.schemas.assistants.qa import QAAssistantCreateRequest
from app.core.assistants.exceptions import ValidationError, PermissionDeniedError


class TestQAService:
    """问答服务测试类"""

    @pytest.fixture
    def service(self, db):
        """创建服务实例"""
        return QAService(db)

    @pytest.fixture
    async def qa_assistant(self, service, test_user):
        """创建测试用的问答助手"""
        data = QAAssistantCreateRequest(
            name="测试问答助手",
            description="用于测试的问答助手",
            type="standard"
        )
        return await service.create_qa_assistant(data, test_user.id)

    async def test_create_qa_assistant_success(self, service, test_user):
        """测试成功创建问答助手"""
        # 准备
        data = QAAssistantCreateRequest(
            name="FAQ助手",
            description="常见问题解答助手",
            type="standard",
            icon="❓"
        )

        # 执行
        assistant = await service.create_qa_assistant(data, test_user.id)

        # 断言
        assert assistant.id is not None
        assert assistant.name == "FAQ助手"
        assert assistant.owner_id == test_user.id
        assert assistant.status == "active"

    async def test_create_question_success(self, service, test_user, qa_assistant):
        """测试成功创建问题"""
        # 执行
        question = await service.create_question(
            assistant_id=qa_assistant.id,
            question="如何重置密码？",
            answer="您可以在登录页面点击'忘记密码'链接来重置密码。",
            user_id=test_user.id
        )

        # 断言
        assert question.id is not None
        assert question.question == "如何重置密码？"
        assert question.views_count == 0

    async def test_create_question_invalid_data(self, service, test_user, qa_assistant):
        """测试创建问题时数据无效"""
        # 测试空问题
        with pytest.raises(ValidationError) as exc_info:
            await service.create_question(
                assistant_id=qa_assistant.id,
                question="",
                answer="答案",
                user_id=test_user.id
            )
        assert "问题不能为空" in str(exc_info.value)

        # 测试空答案
        with pytest.raises(ValidationError) as exc_info:
            await service.create_question(
                assistant_id=qa_assistant.id,
                question="问题",
                answer="",
                user_id=test_user.id
            )
        assert "答案不能为空" in str(exc_info.value)

    async def test_answer_question_increments_views(self, service, test_user, qa_assistant):
        """测试回答问题时增加浏览次数"""
        # 准备
        question = await service.create_question(
            assistant_id=qa_assistant.id,
            question="测试问题",
            answer="测试答案",
            user_id=test_user.id
        )

        # 执行
        answer = await service.answer_question(question.id)

        # 断言
        assert answer == "测试答案"

        # 验证浏览次数增加
        updated_question = await service.get_question(question.id)
        assert updated_question.views_count == 1

    async def test_search_questions(self, service, test_user, qa_assistant):
        """测试搜索问题"""
        # 准备 - 创建多个问题
        questions = [
            ("如何登录系统？", "使用您的用户名和密码登录"),
            ("如何修改密码？", "在个人设置中修改密码"),
            ("如何联系客服？", "拨打客服电话或发送邮件")
        ]

        for q, a in questions:
            await service.create_question(qa_assistant.id, q, a, test_user.id)

        # 执行搜索
        results = await service.search_questions(qa_assistant.id, "密码")

        # 断言
        assert len(results) == 1
        assert "修改密码" in results[0].question

    async def test_get_statistics(self, service, test_user, qa_assistant):
        """测试获取统计信息"""
        # 准备 - 创建问题并模拟浏览
        question1 = await service.create_question(
            assistant_id=qa_assistant.id,
            question="问题1",
            answer="答案1",
            user_id=test_user.id
        )
        question2 = await service.create_question(
            assistant_id=qa_assistant.id,
            question="问题2",
            answer="答案2",
            user_id=test_user.id
        )

        # 模拟浏览
        await service.answer_question(question1.id)
        await service.answer_question(question1.id)
        await service.answer_question(question2.id)

        # 执行
        stats = await service.get_statistics(qa_assistant.id)

        # 断言
        assert stats.total_questions == 2
        assert stats.total_views == 3
        assert len(stats.popular_questions) <= 5
        assert len(stats.recent_questions) <= 5