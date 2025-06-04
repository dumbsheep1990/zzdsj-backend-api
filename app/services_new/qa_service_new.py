"""
问答助手服务层：处理问答助手相关的业务逻辑
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.assistant_qa import QAAssistant, Question, DocumentSegment
from app.core.assistant_qa_manager import AssistantQAManager
from app.core.exceptions import NotFoundError, PermissionError, ValidationError

logger = logging.getLogger(__name__)


class QAService:
    """问答助手服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.qa_manager = AssistantQAManager(db)

    # ==================== 助手管理 ====================

    async def create_qa_assistant(self, data: Dict[str, Any], user_id: int) -> QAAssistant:
        """创建问答助手"""
        try:
            # 添加创建者信息
            data['owner_id'] = user_id
            data['created_by'] = user_id

            assistant = self.qa_manager.create_assistant(data)
            logger.info(f"Created QA assistant: {assistant.id} for user: {user_id}")
            return assistant

        except Exception as e:
            logger.error(f"Failed to create QA assistant: {str(e)}")
            raise ValidationError(f"创建问答助手失败: {str(e)}")

    async def get_qa_assistant(self, assistant_id: int, user_id: Optional[int] = None) -> QAAssistant:
        """获取问答助手详情"""
        assistant = self.qa_manager.get_assistant(assistant_id)

        if not assistant:
            raise NotFoundError("问答助手不存在")

        # 权限检查
        if user_id and hasattr(assistant, 'owner_id'):
            if assistant.owner_id != user_id and not getattr(assistant, 'is_public', False):
                raise PermissionError("无权访问该问答助手")

        return assistant

    async def get_qa_assistants(
            self,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[int] = None,
            status: Optional[str] = None
    ) -> Tuple[List[QAAssistant], int]:
        """获取问答助手列表"""
        assistants, total = await self.qa_manager.get_assistants(skip, limit)

        # 过滤用户可访问的助手
        if user_id:
            filtered = []
            for assistant in assistants:
                owner_id = getattr(assistant, 'owner_id', None)
                is_public = getattr(assistant, 'is_public', False)

                if owner_id == user_id or is_public:
                    filtered.append(assistant)

            assistants = filtered
            total = len(filtered)

        # 状态过滤
        if status:
            assistants = [a for a in assistants if a.status == status]
            total = len(assistants)

        return assistants, total

    async def update_qa_assistant(
            self,
            assistant_id: int,
            data: Dict[str, Any],
            user_id: int
    ) -> QAAssistant:
        """更新问答助手"""
        assistant = await self.get_qa_assistant(assistant_id)

        # 权限检查
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以更新问答助手")

        try:
            updated = self.qa_manager.update_assistant(assistant_id, data)
            logger.info(f"Updated QA assistant: {assistant_id}")
            return updated

        except Exception as e:
            logger.error(f"Failed to update QA assistant: {str(e)}")
            raise ValidationError(f"更新问答助手失败: {str(e)}")

    async def delete_qa_assistant(self, assistant_id: int, user_id: int) -> bool:
        """删除问答助手"""
        assistant = await self.get_qa_assistant(assistant_id)

        # 权限检查
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有所有者可以删除问答助手")

        success = self.qa_manager.delete_assistant(assistant_id)
        if success:
            logger.info(f"Deleted QA assistant: {assistant_id}")
        return success

    # ==================== 问题管理 ====================

    async def create_question(self, data: Dict[str, Any], user_id: int) -> Question:
        """创建问题"""
        # 验证助手存在和权限
        assistant = await self.get_qa_assistant(data['assistant_id'], user_id)

        try:
            data['created_by'] = user_id
            question = await self.qa_manager.create_question(data)
            logger.info(f"Created question: {question.id}")
            return question

        except Exception as e:
            logger.error(f"Failed to create question: {str(e)}")
            raise ValidationError(f"创建问题失败: {str(e)}")

    async def get_question(
            self,
            question_id: int,
            include_document_segments: bool = True,
            user_id: Optional[int] = None
    ) -> Question:
        """获取问题详情"""
        question = self.qa_manager.get_question(question_id, include_document_segments)

        if not question:
            raise NotFoundError("问题不存在")

        # 验证访问权限
        if user_id:
            assistant = await self.get_qa_assistant(question.assistant_id, user_id)

        return question

    async def get_questions(
            self,
            assistant_id: int,
            skip: int = 0,
            limit: int = 100,
            user_id: Optional[int] = None
    ) -> Tuple[List[Question], int]:
        """获取问题列表"""
        # 验证助手访问权限
        if user_id:
            assistant = await self.get_qa_assistant(assistant_id, user_id)

        questions, total = await self.qa_manager.get_questions(assistant_id, skip, limit)
        return questions, total

    async def update_question(
            self,
            question_id: int,
            data: Dict[str, Any],
            user_id: int
    ) -> Question:
        """更新问题"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以更新问题")

        try:
            updated = await self.qa_manager.update_question(question_id, data)
            logger.info(f"Updated question: {question_id}")
            return updated

        except Exception as e:
            logger.error(f"Failed to update question: {str(e)}")
            raise ValidationError(f"更新问题失败: {str(e)}")

    async def delete_question(self, question_id: int, user_id: int) -> bool:
        """删除问题"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以删除问题")

        success = self.qa_manager.delete_question(question_id)
        if success:
            logger.info(f"Deleted question: {question_id}")
        return success

    # ==================== 问答功能 ====================

    async def answer_question(self, question_id: int, user_id: Optional[int] = None) -> str:
        """回答问题"""
        # 验证问题存在和权限
        question = await self.get_question(question_id, user_id=user_id)

        # 增加浏览次数
        question.views_count = (question.views_count or 0) + 1
        self.db.commit()

        # 生成答案
        answer = await self.qa_manager.answer_question(question_id)

        # 记录回答历史
        await self._record_answer_history(question_id, answer, user_id)

        return answer

    async def _record_answer_history(
            self,
            question_id: int,
            answer: str,
            user_id: Optional[int]
    ):
        """记录回答历史"""
        try:
            # TODO: 实现回答历史记录
            pass
        except Exception as e:
            logger.error(f"记录回答历史失败: {str(e)}")

    # ==================== 设置管理 ====================

    async def update_answer_settings(
            self,
            question_id: int,
            answer_mode: Optional[str],
            use_cache: Optional[bool],
            user_id: int
    ) -> Question:
        """更新问题回答设置"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以更新设置")

        updated = await self.qa_manager.update_answer_settings(
            question_id, answer_mode, use_cache
        )
        return updated

    async def update_document_segment_settings(
            self,
            question_id: int,
            segment_ids: List[int],
            user_id: int
    ) -> Question:
        """更新问题文档分段设置"""
        question = await self.get_question(question_id)

        # 验证权限
        assistant = await self.get_qa_assistant(question.assistant_id, user_id)
        if hasattr(assistant, 'owner_id') and assistant.owner_id != user_id:
            raise PermissionError("只有助手所有者可以更新设置")

        updated = await self.qa_manager.update_document_segment_settings(
            question_id, segment_ids
        )
        return updated

    # ==================== 统计功能 ====================

    async def get_assistant_statistics(self, assistant_id: int) -> Dict[str, Any]:
        """获取助手统计信息"""
        assistant = await self.get_qa_assistant(assistant_id)

        # 问题统计
        questions = self.db.query(Question).filter(
            Question.assistant_id == assistant_id
        ).all()

        total_questions = len(questions)
        total_views = sum(q.views_count or 0 for q in questions)

        # 按类别统计
        categories = {}
        for q in questions:
            cat = q.category or "未分类"
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        return {
            "total_questions": total_questions,
            "total_views": total_views,
            "categories": categories,
            "average_views": total_views / total_questions if total_questions > 0 else 0
        }