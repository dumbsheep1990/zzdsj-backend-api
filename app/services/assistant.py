"""
助手服务模块: 提供助手相关的业务逻辑处理
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.repositories.assistant import AssistantRepository
from app.repositories.knowledge import KnowledgeBaseRepository
from app.models.assistant import Assistant
from app.models.knowledge import KnowledgeBase
from app.frameworks.factory import get_agent_framework
from app.config import settings

logger = logging.getLogger(__name__)

class AssistantService:
    """助手服务类"""
    
    def __init__(self, db: Session):
        """初始化服务"""
        self.db = db
        self.assistant_repo = AssistantRepository(db)
        self.kb_repo = KnowledgeBaseRepository(db)
    
    async def create_assistant(self, name: str, description: Optional[str] = None,
                             framework: str = "llamaindex", model: Optional[str] = None,
                             knowledge_base_ids: Optional[List[str]] = None,
                             settings_data: Optional[Dict[str, Any]] = None) -> Assistant:
        """
        创建新助手
        
        参数:
            name: 助手名称
            description: 助手描述
            framework: 框架名称 (llamaindex, haystack, langchain, agno)
            model: 使用的模型
            knowledge_base_ids: 知识库ID列表
            settings_data: 其他设置
            
        返回:
            新建的助手
        """
        try:
            # 设置默认模型（如果未指定）
            if not model:
                model = settings.DEFAULT_LLM_MODEL
                
            # 准备助手数据
            assistant_data = {
                "id": str(uuid.uuid4()),
                "name": name,
                "description": description,
                "framework": framework,
                "model": model,
                "settings": settings_data or {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 创建助手
            assistant = self.assistant_repo.create(assistant_data)
            logger.info(f"已创建助手: {assistant.name} (ID: {assistant.id})")
            
            # 关联知识库（如果有）
            if knowledge_base_ids:
                for kb_id in knowledge_base_ids:
                    # 验证知识库是否存在
                    kb = self.kb_repo.get_by_id(kb_id)
                    if kb:
                        self.assistant_repo.add_knowledge_base(assistant.id, kb_id)
                        logger.info(f"已将知识库 {kb.name} 关联到助手 {assistant.name}")
                    else:
                        logger.warning(f"知识库不存在，无法关联: {kb_id}")
            
            return assistant
            
        except Exception as e:
            logger.error(f"创建助手时出错: {str(e)}")
            raise
    
    async def get_assistant(self, assistant_id: str) -> Optional[Assistant]:
        """获取助手"""
        return self.assistant_repo.get_by_id(assistant_id)
    
    async def get_assistant_with_knowledge_bases(self, assistant_id: str) -> Optional[Assistant]:
        """获取助手及其关联的知识库"""
        return self.assistant_repo.get_with_knowledge_bases(assistant_id)
    
    async def update_assistant(self, assistant_id: str, 
                             data: Dict[str, Any]) -> Optional[Assistant]:
        """更新助手信息"""
        return self.assistant_repo.update(assistant_id, data)
    
    async def delete_assistant(self, assistant_id: str) -> bool:
        """删除助手"""
        return self.assistant_repo.delete(assistant_id)
    
    async def add_knowledge_base(self, assistant_id: str, kb_id: str) -> bool:
        """
        为助手添加知识库
        
        参数:
            assistant_id: 助手ID
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            # 验证助手是否存在
            assistant = await self.get_assistant(assistant_id)
            if not assistant:
                raise ValueError(f"助手不存在: {assistant_id}")
                
            # 验证知识库是否存在
            kb = self.kb_repo.get_by_id(kb_id)
            if not kb:
                raise ValueError(f"知识库不存在: {kb_id}")
            
            # 添加关联
            return self.assistant_repo.add_knowledge_base(assistant_id, kb_id)
            
        except Exception as e:
            logger.error(f"为助手添加知识库时出错: {str(e)}")
            raise
    
    async def remove_knowledge_base(self, assistant_id: str, kb_id: str) -> bool:
        """移除助手的知识库"""
        return self.assistant_repo.remove_knowledge_base(assistant_id, kb_id)
    
    async def get_knowledge_bases(self, assistant_id: str) -> List[KnowledgeBase]:
        """获取助手关联的所有知识库"""
        return self.assistant_repo.get_knowledge_bases(assistant_id)
    
    async def create_agent(self, assistant_id: str) -> Any:
        """
        根据助手配置创建代理实例
        
        参数:
            assistant_id: 助手ID
            
        返回:
            创建的代理实例
        """
        try:
            # 获取助手及其知识库
            assistant = await self.get_assistant_with_knowledge_bases(assistant_id)
            if not assistant:
                raise ValueError(f"助手不存在: {assistant_id}")
            
            # 获取知识库ID列表
            kb_ids = [kb.id for kb in assistant.knowledge_bases]
            
            # 获取框架工厂
            framework_factory = get_agent_framework(assistant.framework)
            if not framework_factory:
                raise ValueError(f"不支持的框架: {assistant.framework}")
            
            # 创建代理
            agent = await framework_factory.create_agent(
                name=assistant.name,
                description=assistant.description,
                knowledge_bases=kb_ids,
                model=assistant.model,
                settings=assistant.settings
            )
            
            logger.info(f"已为助手 {assistant.name} 创建框架代理: {assistant.framework}")
            return agent
            
        except Exception as e:
            logger.error(f"创建代理时出错: {str(e)}")
            raise
    
    async def query(self, assistant_id: str, query: str, 
                  conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        查询助手
        
        参数:
            assistant_id: 助手ID
            query: 查询内容
            conversation_id: 对话ID
            
        返回:
            助手响应
        """
        try:
            # 创建代理
            agent = await self.create_agent(assistant_id)
            
            # 执行查询
            result = await agent.query(query, conversation_id=conversation_id)
            
            return result
            
        except Exception as e:
            logger.error(f"查询助手时出错: {str(e)}")
            # 返回错误响应
            return {
                "response": f"查询处理出错: {str(e)}",
                "error": str(e),
                "conversation_id": conversation_id
            }
