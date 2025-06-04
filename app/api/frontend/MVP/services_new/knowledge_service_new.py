"""
统一知识库服务层
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import asyncio


class KnowledgeService:
    """统一的知识库服务"""

    def __init__(self, db: Session):
        self.db = db
        self._init_backends()

    def _init_backends(self):
        """初始化不同类型的后端"""
        self.backends = {
            KnowledgeBaseType.TRADITIONAL: TraditionalKBBackend(self.db),
            KnowledgeBaseType.LIGHTRAG: LightRAGBackend(self.db),
            KnowledgeBaseType.HYBRID: HybridKBBackend(self.db)
        }

    async def create_knowledge_base(self, request: KnowledgeBaseCreate, user_id: str) -> Dict:
        """创建知识库"""
        # 选择对应的后端
        backend = self.backends[request.type]

        # 创建知识库
        kb = await backend.create(request, user_id)

        # 记录审计日志
        await self._audit_log("create_kb", user_id, kb.id)

        return kb

    async def query(self, request: QueryRequest) -> List[Dict]:
        """统一查询接口"""
        results = []

        # 并发查询多个知识库
        tasks = []
        for kb_id in request.knowledge_base_ids:
            kb = await self.get_knowledge_base(kb_id)
            if kb:
                backend = self.backends[kb.type]
                tasks.append(backend.query(kb_id, request))

        # 等待所有查询完成
        all_results = await asyncio.gather(*tasks)

        # 合并和重排序结果
        for kb_results in all_results:
            results.extend(kb_results)

        # 根据分数重新排序
        results.sort(key=lambda x: x.get('score', 0), reverse=True)

        # 返回top_k结果
        return results[:request.top_k]

    async def check_read_permission(self, kb_id: str, user_id: str) -> bool:
        """检查读权限"""
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return False

        # 公开读或者是所有者
        return kb.public_read or kb.owner_id == user_id

    async def check_write_permission(self, kb_id: str, user_id: str) -> bool:
        """检查写权限"""
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return False

        # 公开写或者是所有者
        return kb.public_write or kb.owner_id == user_id