"""
问答服务实现
"""
from typing import List, Optional, Dict, Any, Tuple
from app.services.assistants.base import BaseService
from app.repositories.assistants.qa import QAAssistantRepository, QuestionRepository
from app.core.assistants.interfaces import IQAService
from app.core.assistants.exceptions import (
    AssistantNotFoundError,
    PermissionDeniedError,
    ValidationError
)
from app.core.assistants.validators import QAValidator
from app.schemas.assistants.qa import (
    QAAssistantCreateRequest,
    QAAssistantUpdateRequest,
    QAAssistantResponse,
    QuestionCreateRequest,
    QuestionUpdateRequest,
    QuestionResponse,
    QAStatisticsResponse
)
import logging

logger = logging.getLogger(__name__)


class QAService(BaseService, IQAService):
    """问答服务"""

    def __init__(self, db):
        super().__init__(db)
        self.qa_repo = QAAssistantRepository(db)
        self.question_repo = QuestionRepository(db)
        self.validator = QAValidator()

        # 配置
        self.allowed_categories = [
            "常见问题", "技术支持", "产品介绍",
            "使用指南", "账户相关", "其他"
        ]

    async def create_qa_assistant(
            self,
            data: QAAssistantCreateRequest,
            user_id: int
    ) -> QAAssistantResponse:
        """创建问答助手"""
        # 验证数据
        self.validator.validate_name(data.name)

        # 创建助手
        assistant = await self.qa_repo.create(
            name=data.name,
            description=data.description,
            type=data.type,
            icon=data.icon,
            status=data.status,
            config=data.config or {},
            knowledge_base_id=data.knowledge_base_id,
            owner_id=user_id
        )

        logger.info(f"Created QA assistant {assistant.id} for user {user_id}")

        return QAAssistantResponse.from_orm(assistant)

    async def get_qa_assistant(
            self,
            assistant_id: int,
            user_id: Optional[int] = None
    ) -> QAAssistantResponse:
        """获取问答助手详情"""
        assistant = await self.qa_repo.get_by_id(assistant_id)

        if not assistant:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        if not assistant.is_public and user_id != assistant.owner_id:
            raise PermissionDeniedError("问答助手")

        # 获取统计信息
        response = QAAssistantResponse.from_orm(assistant)

        # 获取问题统计
        questions, total = await self.question_repo.get_by_assistant(assistant_id)
        response.question_count = total
        response.total_views = sum(q.views_count for q in questions)

        return response

    async def list_qa_assistants(
            self,
            user_id: Optional[int] = None,
            status: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[QAAssistantResponse], int]:
        """获取问答助手列表"""
        if user_id:
            assistants, total = await self.qa_repo.get_user_qa_assistants(
                user_id=user_id,
                skip=skip,
                limit=limit
            )
        else:
            # 只返回公开的助手
            assistants = await self.qa_repo.get_all(skip=skip, limit=limit)
            assistants = [a for a in assistants if a.is_public]
            total = len(assistants)

        # 根据状态过滤
        if status:
            assistants = [a for a in assistants if a.status == status]
            total = len(assistants)

        # 转换为响应模型
        responses = []
        for assistant in assistants:
            response = QAAssistantResponse.from_orm(assistant)
            # 添加统计信息
            questions, _ = await self.question_repo.get_by_assistant(assistant.id)
            response.question_count = len(questions)
            response.total_views = sum(q.views_count for q in questions)
            responses.append(response)

        return responses, total

    async def update_qa_assistant(
            self,
            assistant_id: int,
            data: QAAssistantUpdateRequest,
            user_id: int
    ) -> QAAssistantResponse:
        """更新问答助手"""
        assistant = await self.qa_repo.get_by_id(assistant_id)

        if not assistant:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        self._check_permission(assistant.owner_id, user_id, "问答助手")

        # 验证更新数据
        if data.name:
            self.validator.validate_name(data.name)

        # 更新助手
        update_data = data.dict(exclude_unset=True)
        updated_assistant = await self.qa_repo.update(assistant_id, **update_data)

        logger.info(f"Updated QA assistant {assistant_id}")

        return QAAssistantResponse.from_orm(updated_assistant)

    async def delete_qa_assistant(self, assistant_id: int, user_id: int) -> bool:
        """删除问答助手"""
        assistant = await self.qa_repo.get_by_id(assistant_id)

        if not assistant:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        self._check_permission(assistant.owner_id, user_id, "问答助手")

        # 删除助手（会级联删除问题）
        success = await self.qa_repo.delete(assistant_id)

        if success:
            logger.info(f"Deleted QA assistant {assistant_id}")

        return success

    async def create_question(
            self,
            assistant_id: int,
            question: str,
            answer: str,
            user_id: int
    ) -> QuestionResponse:
        """创建问题"""
        # 验证助手
        assistant = await self.qa_repo.get_by_id(assistant_id)
        if not assistant:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        self._check_permission(assistant.owner_id, user_id, "问答助手")

        # 验证数据
        self.validator.validate_question(question)
        self.validator.validate_answer(answer)

        # 创建问题
        created_question = await self.question_repo.create(
            assistant_id=assistant_id,
            question=question,
            answer=answer,
            created_by=user_id
        )

        logger.info(f"Created question {created_question.id}")

        return QuestionResponse.from_orm(created_question)

    async def answer_question(self, question_id: int) -> str:
        """回答问题"""
        question = await self.question_repo.get_by_id(question_id)

        if not question:
            raise ValidationError("question_id", "问题不存在")

        # 增加浏览次数
        await self.question_repo.increment_views(question_id)

        # TODO: 实现智能回答逻辑
        # 1. 检查是否需要使用AI生成答案
        # 2. 检查是否有相关文档
        # 3. 使用缓存等

        return question.answer

    async def get_question(
            self,
            question_id: int,
            include_segments: bool = False
    ) -> QuestionResponse:
        """获取问题详情"""
        question = await self.question_repo.get_by_id(question_id)

        if not question:
            raise ValidationError("question_id", "问题不存在")

        response = QuestionResponse.from_orm(question)

        # 获取文档分段
        if include_segments and hasattr(question, 'document_segments'):
            response.document_segments = [
                {
                    "id": seg.id,
                    "content": seg.content,
                    "metadata": seg.metadata
                }
                for seg in question.document_segments
            ]

        return response

    async def update_question(
            self,
            question_id: int,
            data: QuestionUpdateRequest,
            user_id: int
    ) -> QuestionResponse:
        """更新问题"""
        question = await self.question_repo.get_by_id(question_id)

        if not question:
            raise ValidationError("question_id", "问题不存在")

        # 验证助手权限
        assistant = await self.qa_repo.get_by_id(question.assistant_id)
        self._check_permission(assistant.owner_id, user_id, "问答助手")

        # 验证更新数据
        if data.question:
            self.validator.validate_question(data.question)
        if data.answer:
            self.validator.validate_answer(data.answer)
        if data.category:
            self.validator.validate_category(data.category, self.allowed_categories)

        # 更新问题
        update_data = data.dict(exclude_unset=True)
        updated_question = await self.question_repo.update(question_id, **update_data)

        logger.info(f"Updated question {question_id}")

        return QuestionResponse.from_orm(updated_question)

    async def delete_question(self, question_id: int, user_id: int) -> bool:
        """删除问题"""
        question = await self.question_repo.get_by_id(question_id)

        if not question:
            raise ValidationError("question_id", "问题不存在")

        # 验证助手权限
        assistant = await self.qa_repo.get_by_id(question.assistant_id)
        self._check_permission(assistant.owner_id, user_id, "问答助手")

        # 删除问题
        success = await self.question_repo.delete(question_id)

        if success:
            logger.info(f"Deleted question {question_id}")

        return success

    async def search_questions(
            self,
            assistant_id: int,
            query: str,
            skip: int = 0,
            limit: int = 20
    ) -> List[QuestionResponse]:
        """搜索问题"""
        questions = await self.question_repo.search_questions(
            assistant_id=assistant_id,
            query=query,
            skip=skip,
            limit=limit
        )

        return [QuestionResponse.from_orm(q) for q in questions]

    async def get_popular_questions(
            self,
            assistant_id: int,
            limit: int = 10
    ) -> List[QuestionResponse]:
        """获取热门问题"""
        questions = await self.question_repo.get_popular_questions(
            assistant_id=assistant_id,
            limit=limit
        )

        return [QuestionResponse.from_orm(q) for q in questions]

    async def get_statistics(self, assistant_id: int) -> QAStatisticsResponse:
        """获取统计信息"""
        # 获取所有问题
        questions, total = await self.question_repo.get_by_assistant(assistant_id)

        # 统计总浏览量
        total_views = sum(q.views_count for q in questions)

        # 按分类统计
        categories = {}
        for q in questions:
            cat = q.category or "未分类"
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        # 获取热门问题
        popular = await self.get_popular_questions(assistant_id, 5)

        # 获取最新问题
        recent = sorted(questions, key=lambda x: x.created_at, reverse=True)[:5]
        recent_responses = [QuestionResponse.from_orm(q) for q in recent]

        return QAStatisticsResponse(
            total_questions=total,
            total_views=total_views,
            categories=categories,
            popular_questions=popular,
            recent_questions=recent_responses
        )