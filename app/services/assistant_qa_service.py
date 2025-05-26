"""
问答助手服务模块
处理问答助手管理和操作相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.assistant_qa import AssistantQA
from app.repositories.assistant_qa_repository import AssistantQARepository
from app.services.resource_permission_service import ResourcePermissionService
from app.services.unified_knowledge_service import UnifiedKnowledgeService

@register_service(service_type="assistant-qa", priority="high", description="问答助手服务")
class AssistantQAService:
    """问答助手服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends(),
                 knowledge_service: UnifiedKnowledgeService = Depends()):
        """初始化问答助手服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
            knowledge_service: 统一知识库服务
        """
        self.db = db
        self.repository = AssistantQARepository()
        self.permission_service = permission_service
        self.knowledge_service = knowledge_service
    
    async def create_assistant_qa(self, assistant_data: Dict[str, Any], user_id: str) -> AssistantQA:
        """创建问答助手
        
        Args:
            assistant_data: 问答助手数据
            user_id: 用户ID
            
        Returns:
            AssistantQA: 创建的问答助手实例
            
        Raises:
            HTTPException: 如果问答助手名称已存在或没有权限
        """
        # 检查问答助手名称是否已存在
        existing_assistant = await self.repository.get_by_name(
            assistant_data.get("name"), self.db
        )
        if existing_assistant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"问答助手名称 '{assistant_data.get('name')}' 已存在"
            )
        
        # 检查知识库权限（如果指定了知识库）
        if knowledge_base_id := assistant_data.get("knowledge_base_id"):
            knowledge_base = await self.knowledge_service.get_knowledge_base(knowledge_base_id, user_id)
            if not knowledge_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"知识库不存在或没有访问权限"
                )
        
        # 创建问答助手
        assistant = await self.repository.create(assistant_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "assistant_qa", assistant.id, user_id
        )
        
        return assistant
    
    async def get_assistant_qa(self, assistant_id: str, user_id: str) -> Optional[AssistantQA]:
        """获取问答助手
        
        Args:
            assistant_id: 问答助手ID
            user_id: 用户ID
            
        Returns:
            Optional[AssistantQA]: 获取的问答助手实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此问答助手"
            )
        
        return assistant
    
    async def get_assistant_qa_by_name(self, name: str, user_id: str) -> Optional[AssistantQA]:
        """通过名称获取问答助手
        
        Args:
            name: 问答助手名称
            user_id: 用户ID
            
        Returns:
            Optional[AssistantQA]: 获取的问答助手实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取问答助手
        assistant = await self.repository.get_by_name(name, self.db)
        if not assistant:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant.id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此问答助手"
            )
        
        return assistant
    
    async def list_assistant_qas(self, user_id: str, skip: int = 0, limit: int = 100) -> List[AssistantQA]:
        """获取问答助手列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[AssistantQA]: 问答助手列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有问答助手
        if is_admin:
            return await self.repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的问答助手
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        assistant_permissions = [p for p in user_permissions if p.resource_type == "assistant_qa"]
        
        # 获取有权限的问答助手ID
        assistant_ids = [p.resource_id for p in assistant_permissions]
        
        # 获取公共问答助手
        public_assistants = await self.repository.list_public_assistants(self.db)
        
        # 合并结果
        result = []
        
        # 添加有权限的问答助手
        for assistant_id in assistant_ids:
            assistant = await self.repository.get_by_id(assistant_id, self.db)
            if assistant and assistant not in result:
                result.append(assistant)
        
        # 添加公共问答助手
        for assistant in public_assistants:
            if assistant not in result:
                result.append(assistant)
        
        return result
    
    async def list_assistant_qas_by_knowledge_base(self, knowledge_base_id: str, user_id: str) -> List[AssistantQA]:
        """获取与指定知识库关联的问答助手列表
        
        Args:
            knowledge_base_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            List[AssistantQA]: 问答助手列表
            
        Raises:
            HTTPException: 如果知识库不存在或没有权限
        """
        # 检查知识库是否存在并且用户有权限访问
        knowledge_base = await self.knowledge_service.get_knowledge_base(knowledge_base_id, user_id)
        if not knowledge_base:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在或没有访问权限"
            )
        
        # 获取与知识库关联的问答助手
        assistants = await self.repository.list_by_knowledge_base(knowledge_base_id, self.db)
        
        # 过滤掉没有权限访问的问答助手
        result = []
        for assistant in assistants:
            has_permission = await self.permission_service.check_permission(
                "assistant_qa", assistant.id, user_id, "read"
            ) or assistant.is_public or await self._check_admin_permission(user_id)
            
            if has_permission:
                result.append(assistant)
        
        return result
    
    async def update_assistant_qa(self, assistant_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[AssistantQA]:
        """更新问答助手
        
        Args:
            assistant_id: 问答助手ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[AssistantQA]: 更新后的问答助手实例或None
            
        Raises:
            HTTPException: 如果没有权限或问答助手不存在
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答助手不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此问答助手"
            )
        
        # 检查知识库权限（如果更新数据中包含知识库ID）
        if knowledge_base_id := update_data.get("knowledge_base_id"):
            knowledge_base = await self.knowledge_service.get_knowledge_base(knowledge_base_id, user_id)
            if not knowledge_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"知识库不存在或没有访问权限"
                )
        
        # 更新问答助手
        return await self.repository.update(assistant_id, update_data, self.db)
    
    async def update_prompt_template(self, assistant_id: str, prompt_template: str, user_id: str) -> Optional[AssistantQA]:
        """更新提示模板
        
        Args:
            assistant_id: 问答助手ID
            prompt_template: 提示模板
            user_id: 用户ID
            
        Returns:
            Optional[AssistantQA]: 更新后的问答助手实例或None
            
        Raises:
            HTTPException: 如果没有权限或问答助手不存在
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答助手不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此问答助手的提示模板"
            )
        
        # 更新提示模板
        update_data = {"prompt_template": prompt_template}
        return await self.repository.update(assistant_id, update_data, self.db)
    
    async def update_model_config(self, assistant_id: str, model_config: Dict[str, Any], user_id: str) -> Optional[AssistantQA]:
        """更新模型配置
        
        Args:
            assistant_id: 问答助手ID
            model_config: 模型配置
            user_id: 用户ID
            
        Returns:
            Optional[AssistantQA]: 更新后的问答助手实例或None
            
        Raises:
            HTTPException: 如果没有权限或问答助手不存在
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答助手不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此问答助手的模型配置"
            )
        
        # 更新模型配置
        update_data = {"model_config": model_config}
        return await self.repository.update(assistant_id, update_data, self.db)
    
    async def delete_assistant_qa(self, assistant_id: str, user_id: str) -> bool:
        """删除问答助手
        
        Args:
            assistant_id: 问答助手ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或问答助手不存在
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答助手不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此问答助手"
            )
        
        # 删除问答助手
        return await self.repository.delete(assistant_id, self.db)
    
    async def process_question(self, assistant_id: str, question: str, user_id: str) -> Dict[str, Any]:
        """处理问题
        
        Args:
            assistant_id: 问答助手ID
            question: 问题内容
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 问题处理结果
            
        Raises:
            HTTPException: 如果没有权限或问答助手不存在
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答助手不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "use"
        ) or assistant.is_public or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限使用此问答助手"
            )
        
        # 如果问答助手关联了知识库，检查知识库权限
        if assistant.knowledge_base_id:
            knowledge_base = await self.knowledge_service.get_knowledge_base(assistant.knowledge_base_id, user_id)
            if not knowledge_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="关联的知识库不存在或没有访问权限"
                )
        
        # 处理问题
        # 这里应该实现具体的问答处理逻辑，可能需要调用其他服务
        # 简化示例
        try:
            # 获取模型配置
            model_config = assistant.model_config or {}
            
            # 获取提示模板
            prompt_template = assistant.prompt_template or "请回答以下问题：{question}"
            
            # 格式化提示
            formatted_prompt = prompt_template.format(question=question)
            
            # 如果关联了知识库，使用知识库处理问题
            if assistant.knowledge_base_id:
                # 调用知识库服务处理问题
                result = await self.knowledge_service.query_knowledge_base(
                    assistant.knowledge_base_id,
                    question,
                    model_config,
                    user_id
                )
            else:
                # 使用普通LLM处理问题
                # 这里需要实现LLM调用逻辑
                result = {
                    "answer": "这是一个示例回答，实际实现需要调用LLM服务。",
                    "sources": [],
                    "metadata": {
                        "model": model_config.get("model", "default"),
                        "prompt": formatted_prompt
                    }
                }
            
            # 记录问答历史
            await self._record_qa_history(assistant_id, user_id, question, result)
            
            return result
            
        except Exception as e:
            # 记录错误
            error_message = str(e)
            
            # 返回处理失败结果
            return {
                "error": True,
                "message": f"处理问题失败: {error_message}",
                "assistant_id": assistant_id
            }
    
    async def _record_qa_history(self, assistant_id: str, user_id: str, question: str, result: Dict[str, Any]) -> None:
        """记录问答历史
        
        Args:
            assistant_id: 问答助手ID
            user_id: 用户ID
            question: 问题内容
            result: 处理结果
        """
        # 这里应该实现记录问答历史的逻辑
        # 简化示例，实际实现可能需要创建新的模型和存储逻辑
        try:
            # 创建历史记录
            history_data = {
                "assistant_id": assistant_id,
                "user_id": user_id,
                "question": question,
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "metadata": result.get("metadata", {}),
                "timestamp": str(datetime.utcnow())
            }
            
            # 将历史记录添加到问答助手的历史列表中
            assistant = await self.repository.get_by_id(assistant_id, self.db)
            if assistant:
                history = assistant.history or []
                history.append(history_data)
                
                # 限制历史记录数量
                max_history = 100
                if len(history) > max_history:
                    history = history[-max_history:]
                
                # 更新问答助手
                await self.repository.update(assistant_id, {"history": history}, self.db)
                
        except Exception as e:
            # 记录错误，但不影响主流程
            print(f"记录问答历史失败: {str(e)}")
    
    async def get_qa_history(self, assistant_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取问答历史
        
        Args:
            assistant_id: 问答助手ID
            user_id: 用户ID
            limit: 返回的最大记录数
            
        Returns:
            List[Dict[str, Any]]: 问答历史记录列表
            
        Raises:
            HTTPException: 如果没有权限或问答助手不存在
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答助手不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此问答助手的历史记录"
            )
        
        # 获取历史记录
        history = assistant.history or []
        
        # 过滤用户自己的记录
        user_history = [
            record for record in history
            if record.get("user_id") == user_id or await self._check_admin_permission(user_id)
        ]
        
        # 限制返回数量
        return user_history[-limit:] if user_history else []
    
    async def clear_qa_history(self, assistant_id: str, user_id: str) -> bool:
        """清除问答历史
        
        Args:
            assistant_id: 问答助手ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功清除
            
        Raises:
            HTTPException: 如果没有权限或问答助手不存在
        """
        # 获取问答助手
        assistant = await self.repository.get_by_id(assistant_id, self.db)
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="问答助手不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "assistant_qa", assistant_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限清除此问答助手的历史记录"
            )
        
        # 清除历史记录
        success = await self.repository.update(assistant_id, {"history": []}, self.db)
        return bool(success)
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        user = await user_service.get_by_id(user_id)
        return user and user.role == "admin"
