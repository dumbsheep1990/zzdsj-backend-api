"""
敏感词过滤器实现
提供本地和第三方API的敏感词检测功能
"""

import os
import json
import logging
import aiohttp
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from enum import Enum
from pathlib import Path
import time

from ..core.base import SecurityComponent
from ..core.exceptions import ContentFilterError

try:
    from app.config import settings
except ImportError:
    # 提供默认配置以防导入失败
    class DefaultSettings:
        SENSITIVE_WORD_FILTER_TYPE = "local"
        SENSITIVE_WORD_FILTER_RESPONSE = "很抱歉，您的消息包含敏感内容，请调整后重新发送。"
        SENSITIVE_WORD_DICT_PATH = "./data/sensitive_words.txt"
        SENSITIVE_WORD_API_URL = ""
        SENSITIVE_WORD_API_KEY = ""
        SENSITIVE_WORD_API_TIMEOUT = 3.0
        SENSITIVE_WORD_CACHE_ENABLED = True
        SENSITIVE_WORD_CACHE_TTL = 3600
    
    settings = DefaultSettings()

logger = logging.getLogger(__name__)


class SensitiveWordFilterType(str, Enum):
    """敏感词过滤器类型"""
    LOCAL = "local"  # 本地敏感词库
    THIRD_PARTY = "third_party"  # 第三方API
    HYBRID = "hybrid"  # 混合模式（先本地后第三方）


class SensitiveWordFilter(SecurityComponent):
    """
    敏感词过滤器
    支持本地敏感词库和第三方API检测
    """
    
    def __init__(self, **kwargs):
        """初始化敏感词过滤器"""
        super().__init__(kwargs)
        
        # 配置参数
        self.filter_type = getattr(settings, "SENSITIVE_WORD_FILTER_TYPE", SensitiveWordFilterType.LOCAL)
        self.default_response = getattr(settings, "SENSITIVE_WORD_FILTER_RESPONSE", 
                                   "很抱歉，您的消息包含敏感内容，请调整后重新发送。")
        self.local_dict_path = getattr(settings, "SENSITIVE_WORD_DICT_PATH", 
                                   os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                           "data", "sensitive_words.txt"))
        self.third_party_api_url = getattr(settings, "SENSITIVE_WORD_API_URL", "")
        self.third_party_api_key = getattr(settings, "SENSITIVE_WORD_API_KEY", "")
        self.third_party_api_timeout = getattr(settings, "SENSITIVE_WORD_API_TIMEOUT", 3.0)
        
        # 词库相关
        self.local_words: Set[str] = set()
        self.word_tree = {}  # DFA算法的词典树
        
        # 缓存相关
        self.cache_enabled = getattr(settings, "SENSITIVE_WORD_CACHE_ENABLED", True)
        self.cache_ttl = getattr(settings, "SENSITIVE_WORD_CACHE_TTL", 3600)
        self.cache = {}  # 简单的内存缓存 {text: (timestamp, result)}
    
    async def initialize(self) -> None:
        """初始化敏感词过滤器，加载词库"""
        if self._initialized:
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.local_dict_path), exist_ok=True)
        
        # 加载本地敏感词库
        if self.filter_type in [SensitiveWordFilterType.LOCAL, SensitiveWordFilterType.HYBRID]:
            await self._load_local_dict()
        
        # 验证第三方API配置
        if self.filter_type in [SensitiveWordFilterType.THIRD_PARTY, SensitiveWordFilterType.HYBRID]:
            if not self.third_party_api_url:
                self.logger.warning("未配置第三方敏感词API URL，将回退到本地敏感词库")
                self.filter_type = SensitiveWordFilterType.LOCAL
        
        self._initialized = True
        self.logger.info(f"敏感词过滤器初始化完成，使用{self.filter_type}模式，共加载{len(self.local_words)}个本地敏感词")
    
    async def check(self, text: str, raise_exception: bool = False) -> Tuple[bool, List[str], str]:
        """
        检查文本是否包含敏感词
        
        参数:
            text: 待检查的文本
            raise_exception: 是否在检测到敏感词时抛出异常
            
        返回:
            (是否包含敏感词, 检测到的敏感词列表, 处理建议)
            
        异常:
            ContentFilterError: 当raise_exception=True且检测到敏感词时
        """
        if not self._initialized:
            await self.initialize()
        
        # 检查缓存
        if self.cache_enabled:
            cache_result = self._check_cache(text)
            if cache_result is not None:
                if cache_result[0] and raise_exception:
                    raise ContentFilterError(
                        message=cache_result[2],
                        detected_words=cache_result[1]
                    )
                return cache_result
        
        result = (False, [], "")
        
        # 根据过滤器类型选择检测方法
        try:
            if self.filter_type == SensitiveWordFilterType.LOCAL:
                result = await self._check_local(text)
            elif self.filter_type == SensitiveWordFilterType.THIRD_PARTY:
                result = await self._check_third_party(text)
            elif self.filter_type == SensitiveWordFilterType.HYBRID:
                # 先本地检测，如果未检测到再使用第三方
                local_result = await self._check_local(text)
                if local_result[0]:  # 本地检测到敏感词
                    result = local_result
                else:
                    try:
                        result = await self._check_third_party(text)
                    except Exception as e:
                        self.logger.error(f"第三方敏感词检测失败，回退到本地结果: {str(e)}")
                        result = local_result
        except Exception as e:
            self.logger.error(f"敏感词检测失败: {str(e)}")
            result = (False, [], "")
        
        # 更新缓存
        if self.cache_enabled:
            self._update_cache(text, result)
        
        # 根据需要抛出异常
        if result[0] and raise_exception:
            raise ContentFilterError(
                message=result[2],
                detected_words=result[1]
            )
        
        return result
    
    async def _load_local_dict(self):
        """加载本地敏感词库"""
        try:
            if not os.path.exists(self.local_dict_path):
                # 创建一个基础敏感词典
                with open(self.local_dict_path, 'w', encoding='utf-8') as f:
                    f.write("敏感词1\n敏感词2\n请替换为实际的敏感词\n")
                self.logger.warning(f"未找到敏感词库，已创建样例文件: {self.local_dict_path}")
            
            # 读取敏感词库
            with open(self.local_dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):  # 忽略空行和注释
                        self.local_words.add(word)
            
            # 构建DFA算法的词典树
            self._build_word_tree()
            
            self.logger.info(f"成功加载本地敏感词库，共{len(self.local_words)}个词")
        except Exception as e:
            self.logger.error(f"加载本地敏感词库失败: {str(e)}")
            # 确保至少有一个空的词典树
            self.local_words = set()
            self.word_tree = {}
    
    def _build_word_tree(self):
        """构建DFA算法的词典树"""
        self.word_tree = {}
        for word in self.local_words:
            current = self.word_tree
            for char in word:
                if char not in current:
                    current[char] = {}
                current = current[char]
            current['is_end'] = True
    
    async def _check_local(self, text: str) -> Tuple[bool, List[str], str]:
        """使用本地敏感词库检测"""
        if not text:
            return False, [], ""
        
        detected_words = []
        
        # 使用DFA算法进行敏感词检测
        i = 0
        while i < len(text):
            j = i
            current = self.word_tree
            found_word = ""
            
            while j < len(text) and text[j] in current:
                found_word += text[j]
                current = current[text[j]]
                
                if 'is_end' in current:
                    detected_words.append(found_word)
                    break
                
                j += 1
            
            i += 1
        
        detected_words = list(set(detected_words))  # 去重
        
        if detected_words:
            return True, detected_words, self.default_response
        else:
            return False, [], ""
    
    async def _check_third_party(self, text: str) -> Tuple[bool, List[str], str]:
        """使用第三方API检测敏感词"""
        if not self.third_party_api_url or not text:
            return False, [], ""
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.third_party_api_key}" if self.third_party_api_key else ""
            }
            
            payload = {"text": text}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.third_party_api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.third_party_api_timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # 根据API响应格式解析结果
                        # 这里需要根据实际使用的第三方API调整
                        is_sensitive = result.get("sensitive", False)
                        detected_words = result.get("words", [])
                        suggestion = result.get("suggestion", self.default_response)
                        
                        return is_sensitive, detected_words, suggestion
                    else:
                        self.logger.error(f"第三方API调用失败: HTTP {response.status}")
                        return False, [], ""
        
        except Exception as e:
            self.logger.error(f"第三方敏感词检测异常: {str(e)}")
            return False, [], ""
    
    def _check_cache(self, text: str) -> Optional[Tuple[bool, List[str], str]]:
        """检查缓存"""
        if not self.cache_enabled or text not in self.cache:
            return None
        
        timestamp, result = self.cache[text]
        
        # 检查缓存是否过期
        if time.time() - timestamp > self.cache_ttl:
            del self.cache[text]
            return None
        
        return result
    
    def _update_cache(self, text: str, result: Tuple[bool, List[str], str]):
        """更新缓存"""
        if self.cache_enabled:
            self.cache[text] = (time.time(), result)
            
            # 简单的缓存清理（保持缓存大小在合理范围内）
            if len(self.cache) > 1000:
                # 删除最旧的一半缓存
                sorted_items = sorted(self.cache.items(), key=lambda x: x[1][0])
                for key, _ in sorted_items[:500]:
                    del self.cache[key]
    
    def add_sensitive_word(self, word: str) -> bool:
        """
        添加敏感词到本地词库
        
        参数:
            word: 要添加的敏感词
            
        返回:
            是否添加成功
        """
        if not word.strip():
            return False
        
        word = word.strip()
        if word in self.local_words:
            return True  # 已存在
        
        try:
            # 添加到内存中的词库
            self.local_words.add(word)
            
            # 重建词典树
            self._build_word_tree()
            
            # 写入文件
            with open(self.local_dict_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{word}")
            
            self.logger.info(f"成功添加敏感词: {word}")
            return True
        except Exception as e:
            self.logger.error(f"添加敏感词失败: {str(e)}")
            return False
    
    def remove_sensitive_word(self, word: str) -> bool:
        """
        从本地词库中移除敏感词
        
        参数:
            word: 要移除的敏感词
            
        返回:
            是否移除成功
        """
        if word not in self.local_words:
            return True  # 本来就不存在
        
        try:
            # 从内存中移除
            self.local_words.remove(word)
            
            # 重建词典树
            self._build_word_tree()
            
            # 重写文件
            with open(self.local_dict_path, 'w', encoding='utf-8') as f:
                for w in sorted(self.local_words):
                    f.write(f"{w}\n")
            
            self.logger.info(f"成功移除敏感词: {word}")
            return True
        except Exception as e:
            self.logger.error(f"移除敏感词失败: {str(e)}")
            return False
    
    def get_sensitive_words(self) -> List[str]:
        """获取所有敏感词列表"""
        return list(self.local_words)
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.logger.info("敏感词检测缓存已清空")


# 全局敏感词过滤器实例
_global_filter: Optional[SensitiveWordFilter] = None


def get_sensitive_word_filter() -> SensitiveWordFilter:
    """
    获取全局敏感词过滤器实例
    
    返回:
        敏感词过滤器实例
    """
    global _global_filter
    if _global_filter is None:
        _global_filter = SensitiveWordFilter()
    return _global_filter


async def filter_sensitive_words(text: str) -> Tuple[bool, List[str], str]:
    """
    过滤敏感词的便捷函数
    
    参数:
        text: 待检查的文本
        
    返回:
        (是否包含敏感词, 检测到的敏感词列表, 处理建议)
    """
    filter_instance = get_sensitive_word_filter()
    if not filter_instance.is_initialized():
        await filter_instance.initialize()
    
    return await filter_instance.check(text)


async def detect_sensitive_content(text: str) -> bool:
    """
    检测文本是否包含敏感内容的便捷函数
    
    参数:
        text: 待检查的文本
        
    返回:
        是否包含敏感内容
    """
    result = await filter_sensitive_words(text)
    return result[0]


def load_sensitive_words(file_path: str) -> bool:
    """
    从指定文件加载敏感词
    
    参数:
        file_path: 敏感词文件路径
        
    返回:
        是否加载成功
    """
    try:
        filter_instance = get_sensitive_word_filter()
        filter_instance.local_dict_path = file_path
        # 需要重新初始化以加载新的词库
        filter_instance._initialized = False
        return True
    except Exception as e:
        logger.error(f"加载敏感词文件失败: {str(e)}")
        return False 