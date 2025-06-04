from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime


class IAssistantService(ABC):
    """助手服务接口"""
    @abstractmethod
    async def create(self, data: Dict[str, Any], user_id: int) -> Any:
        """创建助手"""
        pass

    @abstractmethod
    async def get_by_id(self, assistant_id: int, user_id: Optional[int] = None) -> Optional[Any]:
        """获取助手详情"""
        pass

    @abstractmethod
    async def list(
            self,
            user_id: Optional[int] = None,
            filters: Optional[Dict[str, Any]] = None,
            pagination: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Any], int]:
        """获取助手列表"""
        pass

    @abstractmethod
    async def update(self, assistant_id: int, data: Dict[str, Any], user_id: int) -> Any:
        """更新助手"""
        pass

    @abstractmethod
    async def delete(self, assistant_id: int, user_id: int) -> bool:
        """删除助手"""
        pass


class IConversationService(ABC):
    """对话服务接口"""

    @abstractmethod
    async def create_conversation(self, assistant_id: int, user_id: int, title: Optional[str] = None) -> Any:
        """创建对话"""
        pass

    @abstractmethod
    async def send_message(self, conversation_id: int, content: str, user_id: int) -> Any:
        """发送消息"""
        pass

    @abstractmethod
    async def get_messages(self, conversation_id: int, user_id: int, limit: int = 50) -> List[Any]:
        """获取消息历史"""
        pass


class IAgentService(ABC):
    """智能体服务接口"""

    @abstractmethod
    async def process_task(
            self,
            task: str,
            framework: Optional[str] = None,
            tools: Optional[List[str]] = None,
            parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """处理智能体任务"""
        pass

    @abstractmethod
    async def configure_tools(self, agent_id: int, tools: List[Dict[str, Any]], user_id: int) -> List[Dict[str, Any]]:
        """配置智能体工具"""
        pass


class IQAService(ABC):
    """问答服务接口"""

    @abstractmethod
    async def create_qa_assistant(self, data: Dict[str, Any], user_id: int) -> Any:
        """创建问答助手"""
        pass

    @abstractmethod
    async def create_question(self, assistant_id: int, question: str, answer: str, user_id: int) -> Any:
        """创建问题"""
        pass

    @abstractmethod
    async def answer_question(self, question_id: int) -> str:
        """回答问题"""
        pass


class IKnowledgeBaseService(ABC):
    """知识库服务接口"""

    @abstractmethod
    async def query(self, query: str, kb_ids: List[str], **kwargs) -> List[Dict]:
        pass

    @abstractmethod
    async def add_document(self, kb_id: str, document: Dict) -> Dict:
        pass