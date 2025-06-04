"""
助手服务实现
"""
from typing import List, Optional, Dict, Any, Tuple
from app.services.assistants.base import BaseService
from app.repositories.assistants.assistant import AssistantRepository
from app.repositories.assistants.conversation import ConversationRepository
from app.core.assistants.interfaces import IAssistantService
from app.core.assistants.exceptions import (
    AssistantNotFoundError,
    PermissionDeniedError,
    ValidationError,
    QuotaExceededError
)
from app.core.assistants.validators import AssistantValidator
from app.schemas.assistants.assistant import (
    AssistantCreateRequest,
    AssistantUpdateRequest,
    AssistantResponse,
    AssistantListResponse
)


class AssistantService(BaseService, IAssistantService):
    """助手服务"""

    def __init__(self, db):
        super().__init__(db)
        self.repository = AssistantRepository(db)
        self.conversation_repo = ConversationRepository(db)
        self.validator = AssistantValidator()

        # 配置项
        self.max_assistants_per_user = 50
        self.allowed_models = ["gpt-3.5-turbo", "gpt-4", "claude-3-opus"]
        self.allowed_capabilities = ["text", "code", "math", "creative", "analysis"]

    async def create(self, data: AssistantCreateRequest, user_id: int) -> AssistantResponse:
        """创建助手"""
        # 检查用户配额
        user_assistant_count = await self.repository.count({"owner_id": user_id, "is_active": True})
        if user_assistant_count >= self.max_assistants_per_user:
            raise QuotaExceededError("助手", self.max_assistants_per_user)

        # 验证数据
        self.validator.validate_name(data.name)
        self.validator.validate_model(data.model, self.allowed_models)
        if data.capabilities:
            self.validator.validate_capabilities(data.capabilities, self.allowed_capabilities)
        if data.config:
            self.validator.validate_config(data.config)

        # 创建助手
        assistant = await self.repository.create(
            name=data.name,
            description=data.description,
            model=data.model,
            system_prompt=data.system_prompt,
            capabilities=data.capabilities or [],
            category=data.category,
            tags=data.tags or [],
            avatar_url=data.avatar_url,
            is_public=data.is_public,
            config=data.config or {},
            owner_id=user_id
        )

        self.logger.info(f"Created assistant {assistant.id} for user {user_id}")

        return AssistantResponse.from_orm(assistant)

    async def get_by_id(self, assistant_id: int, user_id: Optional[int] = None) -> AssistantResponse:
        """获取助手详情"""
        assistant = await self.repository.get_by_id(assistant_id)

        if not assistant or not assistant.is_active:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查：私有助手只有所有者可以访问
        if not assistant.is_public and user_id != assistant.owner_id:
            raise PermissionDeniedError("助手")

        # 获取额外信息
        response = AssistantResponse.from_orm(assistant)

        # 获取关联的知识库
        knowledge_base_ids = await self.repository.get_knowledge_bases(assistant_id)
        response.knowledge_base_ids = knowledge_base_ids

        # 获取使用统计
        if user_id and user_id == assistant.owner_id:
            stats = await self._get_assistant_stats(assistant_id)
            response.stats = stats

        return response

    async def list(
            self,
            user_id: Optional[int] = None,
            filters: Optional[Dict[str, Any]] = None,
            pagination: Optional[Dict[str, int]] = None
    ) -> AssistantListResponse:
        """获取助手列表"""
        skip = pagination.get("skip", 0) if pagination else 0
        limit = pagination.get("limit", 20) if pagination else 20

        # 搜索助手
        query = filters.get("search", "") if filters else ""
        assistants, total = await self.repository.search(
            query=query,
            user_id=user_id,
            filters=filters,
            skip=skip,
            limit=limit
        )

        # 转换为响应模型
        items = [AssistantResponse.from_orm(a) for a in assistants]

        return AssistantListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def update(self, assistant_id: int, data: AssistantUpdateRequest, user_id: int) -> AssistantResponse:
        """更新助手"""
        assistant = await self.repository.get_by_id(assistant_id)

        if not assistant or not assistant.is_active:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        self._check_permission(assistant.owner_id, user_id, "助手")

        # 验证更新数据
        if data.name:
            self.validator.validate_name(data.name)
        if data.model:
            self.validator.validate_model(data.model, self.allowed_models)
        if data.capabilities:
            self.validator.validate_capabilities(data.capabilities, self.allowed_capabilities)
        if data.config:
            self.validator.validate_config(data.config)

        # 更新助手
        update_data = data.dict(exclude_unset=True)
        updated_assistant = await self.repository.update(assistant_id, **update_data)

        self.logger.info(f"Updated assistant {assistant_id}")

        return AssistantResponse.from_orm(updated_assistant)

    async def delete(self, assistant_id: int, user_id: int) -> bool:
        """删除助手（软删除）"""
        assistant = await self.repository.get_by_id(assistant_id)

        if not assistant or not assistant.is_active:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        self._check_permission(assistant.owner_id, user_id, "助手")

        # 执行软删除
        success = await self.repository.soft_delete(assistant_id)

        if success:
            self.logger.info(f"Soft deleted assistant {assistant_id}")

        return success

    async def add_knowledge_base(self, assistant_id: int, knowledge_base_id: int, user_id: int) -> bool:
        """添加知识库到助手"""
        assistant = await self.repository.get_by_id(assistant_id)

        if not assistant or not assistant.is_active:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        self._check_permission(assistant.owner_id, user_id, "助手")

        # TODO: 验证知识库存在且用户有权限使用

        # 添加关联
        success = await self.repository.add_knowledge_base(assistant_id, knowledge_base_id)

        if success:
            self.logger.info(f"Added knowledge base {knowledge_base_id} to assistant {assistant_id}")

        return success

    async def remove_knowledge_base(self, assistant_id: int, knowledge_base_id: int, user_id: int) -> bool:
        """从助手移除知识库"""
        assistant = await self.repository.get_by_id(assistant_id)

        if not assistant or not assistant.is_active:
            raise AssistantNotFoundError(assistant_id)

        # 权限检查
        self._check_permission(assistant.owner_id, user_id, "助手")

        # 移除关联
        success = await self.repository.remove_knowledge_base(assistant_id, knowledge_base_id)

        if success:
            self.logger.info(f"Removed knowledge base {knowledge_base_id} from assistant {assistant_id}")

        return success

    async def _get_assistant_stats(self, assistant_id: int) -> Dict[str, Any]:
        """获取助手统计信息"""
        # 对话数
        conversation_count = await self.conversation_repo.count({"assistant_id": assistant_id})

        # TODO: 获取更多统计信息

        return {
            "conversation_count": conversation_count,
            "message_count": 0,  # TODO
            "unique_users": 0,  # TODO
            "last_used": None  # TODO
        }