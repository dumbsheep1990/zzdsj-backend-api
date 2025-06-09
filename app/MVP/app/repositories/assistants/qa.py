"""
问答仓储实现
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import desc, select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncBaseRepository
from app.models.assistants.qa import QAAssistant, Question, QuestionDocumentSegment


class AsyncQAAssistantRepository(AsyncBaseRepository[QAAssistant]):
    """异步问答助手仓储"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, QAAssistant)

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[QAAssistant]:
        """根据状态获取助手列表"""
        stmt = select(QAAssistant).where(
            QAAssistant.status == status
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_qa_assistants(
            self,
            user_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[QAAssistant], int]:
        """获取用户的问答助手"""
        stmt = select(QAAssistant).where(
            or_(
                QAAssistant.owner_id == user_id,
                QAAssistant.is_public == True
            )
        )

        # 获取总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        # 获取分页结果
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        assistants = result.scalars().all()

        return assistants, total


class AsyncQuestionRepository(AsyncBaseRepository[Question]):
    """异步问题仓储"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Question)

    async def get_by_assistant(
            self,
            assistant_id: int,
            category: Optional[str] = None,
            skip: int = 0,
            limit: int = 100
    ) -> Tuple[List[Question], int]:
        """获取助手的问题列表"""
        stmt = select(Question).where(Question.assistant_id == assistant_id)

        if category:
            stmt = stmt.where(Question.category == category)

        # 获取总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        # 获取分页结果
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        questions = result.scalars().all()

        return questions, total

    async def increment_views(self, question_id: int) -> None:
        """增加浏览次数"""
        stmt = update(Question).where(
            Question.id == question_id
        ).values(views_count=Question.views_count + 1)
        
        await self.db.execute(stmt)
        await self.db.commit()

    async def search_questions(
            self,
            assistant_id: int,
            query: str,
            skip: int = 0,
            limit: int = 20
    ) -> List[Question]:
        """搜索问题"""
        search_pattern = f"%{query}%"
        stmt = select(Question).where(
            and_(
                Question.assistant_id == assistant_id,
                or_(
                    Question.question.ilike(search_pattern),
                    Question.answer.ilike(search_pattern)
                )
            )
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_popular_questions(
            self,
            assistant_id: int,
            limit: int = 10
    ) -> List[Question]:
        """获取热门问题"""
        stmt = select(Question).where(
            Question.assistant_id == assistant_id
        ).order_by(desc(Question.views_count)).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_document_segments(
            self,
            question_id: int,
            segment_ids: List[int]
    ) -> bool:
        """更新问题的文档分段"""
        try:
            # 删除现有关联
            delete_stmt = delete(QuestionDocumentSegment).where(
                QuestionDocumentSegment.question_id == question_id
            )
            await self.db.execute(delete_stmt)

            # 添加新关联
            for segment_id in segment_ids:
                link = QuestionDocumentSegment(
                    question_id=question_id,
                    document_segment_id=segment_id
                )
                self.db.add(link)

            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Failed to update document segments: {str(e)}")
            return False