"""
通用验证器
"""
import re
from typing import Optional


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """验证URL格式"""
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    return bool(re.match(pattern, url))


def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    # 移除特殊字符
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # 限制长度
    return filename[:255]