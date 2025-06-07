"""
知识图谱数据访问层
负责知识图谱相关的数据库操作
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import logging

from app.models.knowledge_graph import KnowledgeGraph
from app.schemas.knowledge_graph import (
    KnowledgeGraphResponse, GraphStatus
)
from app.utils.core.database.connection import get_async_session
from app.utils.common.async_utils import AsyncContextManager

logger = logging.getLogger(__name__)

class KnowledgeGraphRepository(AsyncContextManager):
    """知识图谱数据访问层"""
    
    def __init__(self):
        self.session: Optional[Session] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = await get_async_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def create_graph(
        self,
        graph_id: str,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        knowledge_base_id: Optional[int] = None,
        extraction_config: Optional[Dict[str, Any]] = None,
        visualization_config: Optional[Dict[str, Any]] = None,
        is_public: bool = False,
        tags: Optional[List[str]] = None
    ) -> KnowledgeGraphResponse:
        """创建知识图谱记录"""
        try:
            knowledge_graph = KnowledgeGraph(
                id=graph_id,
                user_id=user_id,
                name=name,
                description=description,
                knowledge_base_id=knowledge_base_id,
                status=GraphStatus.CREATED,
                extraction_config=extraction_config or {},
                visualization_config=visualization_config or {},
                is_public=is_public,
                tags=tags or [],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.session.add(knowledge_graph)
            await self.session.commit()
            await self.session.refresh(knowledge_graph)
            
            return KnowledgeGraphResponse.from_orm(knowledge_graph)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建知识图谱记录失败: {str(e)}")
            raise
    
    async def get_graph_by_id(
        self, 
        graph_id: str, 
        user_id: int
    ) -> Optional[KnowledgeGraphResponse]:
        """根据ID获取知识图谱"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                and_(
                    KnowledgeGraph.id == graph_id,
                    or_(
                        KnowledgeGraph.user_id == user_id,
                        KnowledgeGraph.is_public == True
                    )
                )
            )
            
            knowledge_graph = await query.first()
            
            if knowledge_graph:
                return KnowledgeGraphResponse.from_orm(knowledge_graph)
            
            return None
            
        except Exception as e:
            logger.error(f"获取知识图谱失败: {str(e)}")
            raise
    
    async def list_user_graphs(
        self,
        user_id: int,
        knowledge_base_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 20
    ) -> List[KnowledgeGraphResponse]:
        """获取用户的知识图谱列表"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                or_(
                    KnowledgeGraph.user_id == user_id,
                    KnowledgeGraph.is_public == True
                )
            )
            
            if knowledge_base_id:
                query = query.filter(
                    KnowledgeGraph.knowledge_base_id == knowledge_base_id
                )
            
            query = query.order_by(desc(KnowledgeGraph.updated_at))
            query = query.offset(offset).limit(limit)
            
            knowledge_graphs = await query.all()
            
            return [
                KnowledgeGraphResponse.from_orm(kg) 
                for kg in knowledge_graphs
            ]
            
        except Exception as e:
            logger.error(f"获取知识图谱列表失败: {str(e)}")
            raise
    
    async def update_graph(
        self,
        graph_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        visualization_config: Optional[Dict[str, Any]] = None,
        is_public: Optional[bool] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[KnowledgeGraphResponse]:
        """更新知识图谱"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                KnowledgeGraph.id == graph_id
            )
            
            knowledge_graph = await query.first()
            if not knowledge_graph:
                return None
            
            # 更新字段
            if name is not None:
                knowledge_graph.name = name
            if description is not None:
                knowledge_graph.description = description
            if visualization_config is not None:
                knowledge_graph.visualization_config = visualization_config
            if is_public is not None:
                knowledge_graph.is_public = is_public
            if tags is not None:
                knowledge_graph.tags = tags
            
            knowledge_graph.updated_at = datetime.utcnow()
            
            await self.session.commit()
            await self.session.refresh(knowledge_graph)
            
            return KnowledgeGraphResponse.from_orm(knowledge_graph)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新知识图谱失败: {str(e)}")
            raise
    
    async def update_graph_status(
        self, 
        graph_id: str, 
        status: GraphStatus
    ) -> bool:
        """更新知识图谱状态"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                KnowledgeGraph.id == graph_id
            )
            
            result = await query.update({
                KnowledgeGraph.status: status,
                KnowledgeGraph.updated_at: datetime.utcnow()
            })
            
            await self.session.commit()
            return result > 0
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新知识图谱状态失败: {str(e)}")
            raise
    
    async def set_graph_completed_at(
        self, 
        graph_id: str, 
        completed_at: datetime
    ) -> bool:
        """设置知识图谱完成时间"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                KnowledgeGraph.id == graph_id
            )
            
            result = await query.update({
                KnowledgeGraph.completed_at: completed_at,
                KnowledgeGraph.updated_at: datetime.utcnow()
            })
            
            await self.session.commit()
            return result > 0
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"设置完成时间失败: {str(e)}")
            raise
    
    async def update_graph_files(
        self, 
        graph_id: str, 
        file_paths: List[str]
    ) -> bool:
        """更新知识图谱源文件列表"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                KnowledgeGraph.id == graph_id
            )
            
            result = await query.update({
                KnowledgeGraph.source_files: file_paths,
                KnowledgeGraph.updated_at: datetime.utcnow()
            })
            
            await self.session.commit()
            return result > 0
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"更新源文件列表失败: {str(e)}")
            raise
    
    async def delete_graph(self, graph_id: str) -> bool:
        """删除知识图谱"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                KnowledgeGraph.id == graph_id
            )
            
            result = await query.delete()
            await self.session.commit()
            
            return result > 0
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除知识图谱失败: {str(e)}")
            raise
    
    async def get_graphs_by_knowledge_base(
        self, 
        knowledge_base_id: int
    ) -> List[KnowledgeGraphResponse]:
        """根据知识库ID获取相关图谱"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                KnowledgeGraph.knowledge_base_id == knowledge_base_id
            ).order_by(desc(KnowledgeGraph.created_at))
            
            knowledge_graphs = await query.all()
            
            return [
                KnowledgeGraphResponse.from_orm(kg) 
                for kg in knowledge_graphs
            ]
            
        except Exception as e:
            logger.error(f"根据知识库获取图谱失败: {str(e)}")
            raise
    
    async def search_graphs(
        self,
        user_id: int,
        search_query: str,
        tags: Optional[List[str]] = None,
        status: Optional[GraphStatus] = None,
        offset: int = 0,
        limit: int = 20
    ) -> List[KnowledgeGraphResponse]:
        """搜索知识图谱"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                or_(
                    KnowledgeGraph.user_id == user_id,
                    KnowledgeGraph.is_public == True
                )
            )
            
            # 搜索条件
            if search_query:
                query = query.filter(
                    or_(
                        KnowledgeGraph.name.ilike(f"%{search_query}%"),
                        KnowledgeGraph.description.ilike(f"%{search_query}%")
                    )
                )
            
            # 标签过滤
            if tags:
                for tag in tags:
                    query = query.filter(
                        KnowledgeGraph.tags.any(tag)
                    )
            
            # 状态过滤
            if status:
                query = query.filter(KnowledgeGraph.status == status)
            
            query = query.order_by(desc(KnowledgeGraph.updated_at))
            query = query.offset(offset).limit(limit)
            
            knowledge_graphs = await query.all()
            
            return [
                KnowledgeGraphResponse.from_orm(kg) 
                for kg in knowledge_graphs
            ]
            
        except Exception as e:
            logger.error(f"搜索知识图谱失败: {str(e)}")
            raise
    
    async def get_user_graph_count(self, user_id: int) -> int:
        """获取用户知识图谱数量"""
        try:
            count = await self.session.query(func.count(KnowledgeGraph.id)).filter(
                KnowledgeGraph.user_id == user_id
            ).scalar()
            
            return count or 0
            
        except Exception as e:
            logger.error(f"获取用户图谱数量失败: {str(e)}")
            raise
    
    async def get_popular_graphs(
        self, 
        limit: int = 10
    ) -> List[KnowledgeGraphResponse]:
        """获取热门公开图谱"""
        try:
            query = self.session.query(KnowledgeGraph).filter(
                and_(
                    KnowledgeGraph.is_public == True,
                    KnowledgeGraph.status == GraphStatus.COMPLETED
                )
            ).order_by(desc(KnowledgeGraph.created_at)).limit(limit)
            
            knowledge_graphs = await query.all()
            
            return [
                KnowledgeGraphResponse.from_orm(kg) 
                for kg in knowledge_graphs
            ]
            
        except Exception as e:
            logger.error(f"获取热门图谱失败: {str(e)}")
            raise 