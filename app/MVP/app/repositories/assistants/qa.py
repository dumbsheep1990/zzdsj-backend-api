"""
问答仓储实现
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import and_, or_, func
from app.repositories.assistants.base import BaseRepository
from app.models.assistants.qa import QAAssistant, Question, QuestionDocumentSegment


class QAAssistantRepository(BaseRepository[QAAssistant]):
    """问答助手仓储"""

    def __init__(self, db):
        super().__init__(db, QAAssistant)

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[QAAssistant]:
        """根据状态获取助手列表"""
        return self.db.query(QAAssistant).filter(
            QAAssistant.status == status
        ).offset(skip).limit(limit).all()

    async def get_user_qa_assistants(
            self,
            user_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[QAAssistant], int]:
        """获取用户的问答助手"""
        query = self.db.query(QAAssistant).filter(
            or_(
                QAAssistant.owner_id == user_id,
                QAAssistant.is_public == True
            )
        )

        total = query.count()
        assistants = query.offset(skip).limit(limit).all()

        return assistants, total


class QuestionRepository(BaseRepository[Question]):
    """问题仓储"""

    def __init__(self, db):
        super().__init__(db, Question)

    async def get_by_assistant(
            self,
            assistant_id: int,
            category: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[Question], int]:
        """获取助手的问题列表"""
        query = self.db.query(Question).filter(
            Question.assistant_id == assistant_id
        )

        if category:
            query = query.filter(Question.category == category)

        total = query.count()
        questions = query.offset(skip).limit(limit).all()

        return questions, total

    async def increment_views(self, question_id: int) -> None:
        """增加浏览次数"""
        self.db.query(Question).filter(
            Question.id == question_id
        ).update(
            {Question.views_count: Question.views_count + 1}
        )
        self.db.commit()

    async def search_questions(
            self,
            assistant_id: int,
            query: str,
            skip: int = 0,
            limit: int = 20
    ) -> List[Question]:
        """搜索问题"""
        search_pattern = f"%{query}%"
        return self.db.query(Question).filter(
            Question.assistant_id == assistant_id,
            or_(
                Question.question.ilike(search_pattern),
                Question.answer.ilike(search_pattern)
            )
        ).offset(skip).limit(limit).all()

    async def get_popular_questions(
            self,
            assistant_id: int,
            limit: int = 10
    ) -> List[Question]:
        """获取热门问题"""
        return self.db.query(Question).filter(
            Question.assistant_id == assistant_id
        ).order_by(desc(Question.views_count)).limit(limit).all()

    async def update_document_segments(
            self,
            question_id: int,
            segment_ids: List[int]
    ) -> bool:
        """更新问题的文档分段"""
        try:
            # 删除现有关联
            self.db.query(QuestionDocumentSegment).filter(
                QuestionDocumentSegment.question_id == question_id
            ).delete()

            # 添加新关联
            for segment_id in segment_ids:
                link = QuestionDocumentSegment(
                    question_id=question_id,
                    document_segment_id=segment_id
                )
                self.db.add(link)

            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update document segments: {str(e)}")
            return False