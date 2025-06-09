"""
助手模块业务验证器
"""
from typing import Dict, Any, Optional
import re
from .exceptions import ValidationError


class AssistantValidator:
    """助手验证器"""

    @staticmethod
    def validate_name(name: str) -> None:
        """验证助手名称"""
        if not name or len(name.strip()) == 0:
            raise ValidationError("name", "名称不能为空")

        if len(name) > 100:
            raise ValidationError("name", "名称长度不能超过100个字符")

        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_\-\s]+$', name):
            raise ValidationError("name", "名称只能包含中文、英文、数字、下划线、连字符和空格")

    @staticmethod
    def validate_model(model: str, allowed_models: list) -> None:
        """验证模型"""
        if model not in allowed_models:
            raise ValidationError("model", f"不支持的模型: {model}")

    @staticmethod
    def validate_capabilities(capabilities: list, allowed_capabilities: list) -> None:
        """验证能力列表"""
        for cap in capabilities:
            if cap not in allowed_capabilities:
                raise ValidationError("capabilities", f"不支持的能力: {cap}")

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> None:
        """验证配置"""
        # 温度参数
        if "temperature" in config:
            temp = config["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                raise ValidationError("config.temperature", "温度参数必须在0-2之间")

        # 最大令牌数
        if "max_tokens" in config:
            tokens = config["max_tokens"]
            if not isinstance(tokens, int) or tokens < 1 or tokens > 100000:
                raise ValidationError("config.max_tokens", "最大令牌数必须在1-100000之间")


class ConversationValidator:
    """对话验证器"""

    @staticmethod
    def validate_title(title: Optional[str]) -> None:
        """验证对话标题"""
        if title and len(title) > 200:
            raise ValidationError("title", "标题长度不能超过200个字符")

    @staticmethod
    def validate_message_content(content: str) -> None:
        """验证消息内容"""
        if not content or len(content.strip()) == 0:
            raise ValidationError("content", "消息内容不能为空")

        if len(content) > 10000:
            raise ValidationError("content", "消息内容不能超过10000个字符")


class QAValidator:
    """问答验证器"""

    @staticmethod
    def validate_question(question: str) -> None:
        """验证问题"""
        if not question or len(question.strip()) == 0:
            raise ValidationError("question", "问题不能为空")

        if len(question) > 500:
            raise ValidationError("question", "问题长度不能超过500个字符")

    @staticmethod
    def validate_answer(answer: str) -> None:
        """验证答案"""
        if not answer or len(answer.strip()) == 0:
            raise ValidationError("answer", "答案不能为空")

        if len(answer) > 5000:
            raise ValidationError("answer", "答案长度不能超过5000个字符")

    @staticmethod
    def validate_category(category: str, allowed_categories: list) -> None:
        """验证分类"""
        if category and category not in allowed_categories:
            raise ValidationError("category", f"不支持的分类: {category}")

    @staticmethod
    def validate_name(name: str) -> None:
        """验证名称（QA助手名称）"""
        if not name or len(name.strip()) == 0:
            raise ValidationError("name", "名称不能为空")

        if len(name) > 100:
            raise ValidationError("name", "名称长度不能超过100个字符")