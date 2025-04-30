"""
问答助手管理器: 统一管理问答助手系统的核心逻辑
集成各个框架的能力，提供问答、文档检索和关联度计算功能
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.assistant_qa import Assistant, Question, QuestionDocumentSegment
from app.models.knowledge import Document, DocumentSegment, KnowledgeBase
from app.schemas.assistant_qa import AnswerModeEnum

# 框架集成
from app.frameworks.llamaindex.chat import generate_response
from app.frameworks.haystack.reader import extract_answers
from app.frameworks.llamaindex.retrieval import query_index
from app.frameworks.agno.agent import AgnoAgent
from app.config import settings

logger = logging.getLogger(__name__)


class AssistantQAManager:
    """
    问答助手管理器
    
    集成LlamaIndex、Haystack、LlamaIndex和Agno框架，
    提供统一的问答助手管理、问题回答和文档检索功能
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_assistants(self, skip: int = 0, limit: int = 100) -> Tuple[List[Dict], int]:
        """
        获取助手列表
        
        参数:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        返回:
            助手列表和总记录数的元组
        """
        assistants = self.db.query(Assistant).offset(skip).limit(limit).all()
        total = self.db.query(Assistant).count()
        
        # 添加问题统计信息
        result = []
        for assistant in assistants:
            assistant_dict = {
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description,
                "type": assistant.type,
                "icon": assistant.icon,
                "status": assistant.status,
                "created_at": assistant.created_at,
                "updated_at": assistant.updated_at,
                "config": assistant.config,
                "knowledge_base_id": assistant.knowledge_base_id,
                "stats": {
                    "total_questions": len(assistant.questions),
                    "total_views": sum(q.views_count for q in assistant.questions)
                }
            }
            result.append(assistant_dict)
        
        return result, total
    
    def get_assistant(self, assistant_id: int) -> Optional[Assistant]:
        """获取助手详情"""
        assistant = self.db.query(Assistant).filter(Assistant.id == assistant_id).first()
        if not assistant:
            raise HTTPException(status_code=404, detail="助手未找到")
        return assistant
    
    def create_assistant(self, assistant_data: Dict[str, Any]) -> Assistant:
        """创建新助手"""
        # 检查知识库是否存在
        if assistant_data.get("knowledge_base_id"):
            kb = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == assistant_data["knowledge_base_id"]
            ).first()
            if not kb:
                raise HTTPException(status_code=404, detail="知识库未找到")
        
        assistant = Assistant(**assistant_data)
        self.db.add(assistant)
        self.db.commit()
        self.db.refresh(assistant)
        return assistant
    
    def update_assistant(self, assistant_id: int, assistant_data: Dict[str, Any]) -> Assistant:
        """更新助手信息"""
        assistant = self.get_assistant(assistant_id)
        
        # 检查知识库是否存在
        if assistant_data.get("knowledge_base_id"):
            kb = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == assistant_data["knowledge_base_id"]
            ).first()
            if not kb:
                raise HTTPException(status_code=404, detail="知识库未找到")
        
        # 更新字段
        for key, value in assistant_data.items():
            if hasattr(assistant, key) and value is not None:
                setattr(assistant, key, value)
        
        self.db.commit()
        self.db.refresh(assistant)
        return assistant
    
    def delete_assistant(self, assistant_id: int) -> bool:
        """删除助手"""
        assistant = self.get_assistant(assistant_id)
        self.db.delete(assistant)
        self.db.commit()
        return True
    
    async def get_questions(self, assistant_id: int, skip: int = 0, limit: int = 100) -> Tuple[List[Dict], int]:
        """获取助手下的问题列表"""
        questions = self.db.query(Question).filter(
            Question.assistant_id == assistant_id
        ).offset(skip).limit(limit).all()
        
        total = self.db.query(Question).filter(Question.assistant_id == assistant_id).count()
        
        # 格式化问题列表，但不包括文档分段
        result = []
        for question in questions:
            question_dict = {
                "id": question.id,
                "assistant_id": question.assistant_id,
                "question_text": question.question_text,
                "answer_text": question.answer_text,
                "created_at": question.created_at,
                "updated_at": question.updated_at,
                "views_count": question.views_count,
                "enabled": question.enabled,
                "answer_mode": question.answer_mode,
                "use_cache": question.use_cache
            }
            result.append(question_dict)
        
        return result, total
    
    def get_question(self, question_id: int, include_document_segments: bool = False) -> Dict[str, Any]:
        """获取问题详情"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="问题未找到")
        
        # 增加浏览计数
        question.views_count += 1
        self.db.commit()
        
        result = {
            "id": question.id,
            "assistant_id": question.assistant_id,
            "question_text": question.question_text,
            "answer_text": question.answer_text,
            "created_at": question.created_at,
            "updated_at": question.updated_at,
            "views_count": question.views_count,
            "enabled": question.enabled,
            "answer_mode": question.answer_mode,
            "use_cache": question.use_cache
        }
        
        # 包含文档分段数据
        if include_document_segments:
            document_segments = []
            for dseg in question.document_segments:
                # 获取文档和分段信息
                document = dseg.document
                segment = dseg.segment
                
                segment_data = {
                    "id": dseg.id,
                    "document_id": dseg.document_id,
                    "segment_id": dseg.segment_id,
                    "relevance_score": dseg.relevance_score,
                    "is_enabled": dseg.is_enabled,
                    "document_title": document.title if document else None,
                    "segment_content": segment.content if segment else None,
                    "file_type": document.file_type if document else None,
                    "file_size": f"{document.file_size / 1024:.1f}KB" if document and document.file_size else None
                }
                document_segments.append(segment_data)
            
            # 按相关度排序
            document_segments.sort(key=lambda x: x["relevance_score"], reverse=True)
            result["document_segments"] = document_segments
        
        return result
    
    async def create_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建问题并自动检索文档"""
        assistant_id = question_data["assistant_id"]
        assistant = self.get_assistant(assistant_id)
        
        # 创建问题记录
        question = Question(**question_data)
        self.db.add(question)
        self.db.flush()  # 获取ID但不提交事务
        
        # 如果助手关联了知识库，自动检索相关文档
        if assistant.knowledge_base_id:
            await self._retrieve_and_link_document_segments(
                question=question, 
                knowledge_base_id=assistant.knowledge_base_id
            )
        
        # 生成回答(如果没有提供)
        if not question.answer_text:
            question.answer_text = await self._generate_answer(question)
        
        self.db.commit()
        self.db.refresh(question)
        
        return self.get_question(question.id, include_document_segments=True)
    
    async def update_question(self, question_id: int, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新问题信息"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="问题未找到")
        
        # 更新字段
        for key, value in question_data.items():
            if hasattr(question, key) and value is not None:
                setattr(question, key, value)
        
        question.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(question)
        
        return self.get_question(question.id, include_document_segments=True)
    
    def delete_question(self, question_id: int) -> bool:
        """删除问题"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="问题未找到")
        
        self.db.delete(question)
        self.db.commit()
        return True
    
    async def update_answer_settings(
        self, question_id: int, answer_mode: str, use_cache: bool
    ) -> Dict[str, Any]:
        """更新回答设置"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="问题未找到")
        
        # 更新设置
        question.answer_mode = answer_mode
        question.use_cache = use_cache
        
        # 如果更改了回答模式，重新生成回答
        if answer_mode != question.answer_mode:
            question.answer_text = await self._generate_answer(question)
        
        question.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(question)
        
        return self.get_question(question.id, include_document_segments=True)
    
    async def update_document_segment_settings(
        self, question_id: int, segment_ids: List[int]
    ) -> Dict[str, Any]:
        """更新文档分段设置"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="问题未找到")
        
        # 更新所有分段的启用状态
        for doc_seg in question.document_segments:
            doc_seg.is_enabled = doc_seg.segment_id in segment_ids
        
        # 重新生成回答
        question.answer_text = await self._generate_answer(question)
        question.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(question)
        
        return self.get_question(question.id, include_document_segments=True)
    
    async def answer_question(self, question_id: int) -> str:
        """根据问题ID回答问题"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="问题未找到")
        
        # 如果使用缓存且已有回答，直接返回
        if question.use_cache and question.answer_text:
            return question.answer_text
        
        # 生成新回答
        answer = await self._generate_answer(question)
        
        # 如果使用缓存，保存回答
        if question.use_cache:
            question.answer_text = answer
            self.db.commit()
        
        return answer
    
    async def _retrieve_and_link_document_segments(
        self, question: Question, knowledge_base_id: int, top_k: int = 4
    ) -> None:
        """检索并关联相关的文档分段"""
        try:
            # 使用LlamaIndex检索
            query_results = await query_index(
                query=question.question_text,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k
            )
            
            # 关联文档分段
            for result in query_results:
                # 获取文档和分段
                document = self.db.query(Document).filter(
                    Document.knowledge_base_id == knowledge_base_id,
                    Document.id == result["document_id"]
                ).first()
                
                segment = self.db.query(DocumentSegment).filter(
                    DocumentSegment.document_id == result["document_id"],
                    DocumentSegment.id == result["segment_id"]
                ).first()
                
                if document and segment:
                    # 创建关联记录
                    doc_segment = QuestionDocumentSegment(
                        question_id=question.id,
                        document_id=document.id,
                        segment_id=segment.id,
                        relevance_score=result["score"],
                        is_enabled=True
                    )
                    self.db.add(doc_segment)
        
        except Exception as e:
            logger.error(f"文档检索错误: {str(e)}")
            # 继续处理，即使检索失败
    
    async def _generate_answer(self, question: Question) -> str:
        """根据问题和回答模式生成回答"""
        try:
            # 获取助手信息
            assistant = self.db.query(Assistant).filter(Assistant.id == question.assistant_id).first()
            if not assistant:
                return "无法找到关联的助手信息"
            
            # 获取启用的文档分段内容
            document_segments = []
            for doc_seg in question.document_segments:
                if doc_seg.is_enabled:
                    segment = self.db.query(DocumentSegment).filter(
                        DocumentSegment.id == doc_seg.segment_id
                    ).first()
                    
                    if segment:
                        document_segments.append({
                            "content": segment.content,
                            "metadata": {
                                "document_id": doc_seg.document_id,
                                "segment_id": doc_seg.segment_id,
                                "score": doc_seg.relevance_score
                            }
                        })
            
            # 按照回答模式生成回答
            if question.answer_mode == AnswerModeEnum.DOCS_ONLY:
                # 仅使用文档内容回答
                if not document_segments:
                    return "未找到相关文档内容"
                
                # 使用Haystack提取答案
                answers = extract_answers(
                    question=question.question_text,
                    contexts=document_segments
                )
                
                if answers:
                    return answers[0]["answer"]
                else:
                    return "无法从文档中提取相关答案"
                
            elif question.answer_mode == AnswerModeEnum.MODEL_ONLY:
                # 仅使用模型回答，不使用文档
                system_prompt = f"你是一个{assistant.name}，需要回答关于{assistant.description or '相关主题'}的问题。"
                
                response = await generate_response(
                    system_prompt=system_prompt,
                    conversation_history=[{"role": "user", "content": question.question_text}]
                )
                
                return response
                
            elif question.answer_mode == AnswerModeEnum.HYBRID:
                # 使用Agno代理，集成Haystack和LlamaIndex能力
                agent = AgnoAgent(
                    name=assistant.name,
                    description=assistant.description or "问答助手",
                    knowledge_bases=[str(assistant.knowledge_base_id)] if assistant.knowledge_base_id else []
                )
                
                # 使用Agno代理回答
                agent_response = await agent.query(question.question_text)
                return agent_response.get("answer", "无法生成回答")
                
            else:
                # 默认模式：LlamaIndex统一入口，使用文档增强回答
                system_prompt = f"你是一个{assistant.name}，需要回答关于{assistant.description or '相关主题'}的问题。"
                
                # 创建上下文
                conversation_history = [{"role": "user", "content": question.question_text}]
                
                # 使用LlamaIndex生成回答
                response = await generate_response(
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                    references=document_segments
                )
                
                return response
                
        except Exception as e:
            logger.error(f"生成回答错误: {str(e)}")
            return f"生成回答时出错: {str(e)}"

    def get_assistant_tools(self, assistant_id: int) -> List[Dict[str, Any]]:
        """
        获取助手的工具配置
        
        参数:
            assistant_id: 助手ID
            
        返回:
            工具配置列表
        """
        assistant = self.get_assistant(assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail=f"未找到助手: {assistant_id}")
        
        # 从assistant.settings获取工具配置
        settings = assistant.settings or {}
        return settings.get("tools", [])
    
    def update_assistant_tools(self, assistant_id: int, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        更新助手的工具配置
        
        参数:
            assistant_id: 助手ID
            tools: 工具配置列表
            
        返回:
            更新后的工具配置列表
        """
        assistant = self.get_assistant(assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail=f"未找到助手: {assistant_id}")
        
        # 更新assistant.settings中的工具配置
        settings = assistant.settings or {}
        settings["tools"] = tools
        
        # 更新assistant
        assistant.settings = settings
        assistant.updated_at = datetime.utcnow()
        self.db.commit()
        
        return tools
