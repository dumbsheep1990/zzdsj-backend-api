"""
敏感词过滤器模块，提供对聊天消息的敏感词检测功能
支持本地敏感词库和第三方敏感词检测API
"""

import os
import re
import json
import logging
import aiohttp
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from enum import Enum
from pathlib import Path
import time

from app.config import settings

logger = logging.getLogger(__name__)

class SensitiveWordFilterType(str, Enum):
    """敏感词过滤器类型"""
    LOCAL = "local"  # 本地敏感词库
    THIRD_PARTY = "third_party"  # 第三方API
    HYBRID = "hybrid"  # 混合模式（先本地后第三方）


class SensitiveWordFilter:
    """敏感词过滤器"""
    
    def __init__(self):
        """初始化敏感词过滤器"""
        self.filter_type = getattr(settings, "SENSITIVE_WORD_FILTER_TYPE", SensitiveWordFilterType.LOCAL)
        self.default_response = getattr(settings, "SENSITIVE_WORD_FILTER_RESPONSE", 
                                   "很抱歉，您的消息包含敏感内容，请调整后重新发送。")
        self.local_dict_path = getattr(settings, "SENSITIVE_WORD_DICT_PATH", 
                                   os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                           "data", "sensitive_words.txt"))
        self.third_party_api_url = getattr(settings, "SENSITIVE_WORD_API_URL", "")
        self.third_party_api_key = getattr(settings, "SENSITIVE_WORD_API_KEY", "")
        self.third_party_api_timeout = getattr(settings, "SENSITIVE_WORD_API_TIMEOUT", 3.0)  # 秒
        
        # 词库相关
        self.local_words: Set[str] = set()
        self.word_tree = {}  # DFA算法的词典树
        self.is_initialized = False
        
        # 启用缓存以提高性能
        self.cache_enabled = getattr(settings, "SENSITIVE_WORD_CACHE_ENABLED", True)
        self.cache_ttl = getattr(settings, "SENSITIVE_WORD_CACHE_TTL", 3600)  # 1小时缓存有效期
        self.cache = {}  # 简单的内存缓存 {text: (timestamp, result)}
    
    async def initialize(self):
        """初始化敏感词过滤器，加载词库"""
        if self.is_initialized:
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.local_dict_path), exist_ok=True)
        
        # 加载本地敏感词库
        if self.filter_type in [SensitiveWordFilterType.LOCAL, SensitiveWordFilterType.HYBRID]:
            await self._load_local_dict()
        
        # 测试第三方API连接
        if self.filter_type in [SensitiveWordFilterType.THIRD_PARTY, SensitiveWordFilterType.HYBRID]:
            if not self.third_party_api_url:
                logger.warning("未配置第三方敏感词API URL，将回退到本地敏感词库")
                self.filter_type = SensitiveWordFilterType.LOCAL
        
        self.is_initialized = True
        logger.info(f"敏感词过滤器初始化完成，使用{self.filter_type}模式，共加载{len(self.local_words)}个本地敏感词")
    
    async def _load_local_dict(self):
        """加载本地敏感词库"""
        try:
            if not os.path.exists(self.local_dict_path):
                # 创建一个基础敏感词典
                with open(self.local_dict_path, 'w', encoding='utf-8') as f:
                    f.write("敏感词1\n敏感词2\n请替换为实际的敏感词\n")
                logger.warning(f"未找到敏感词库，已创建样例文件: {self.local_dict_path}")
            
            # 读取敏感词库
            with open(self.local_dict_path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):  # 忽略空行和注释
                        self.local_words.add(word)
            
            # 构建DFA算法的词典树
            self._build_word_tree()
            
            logger.info(f"成功加载本地敏感词库，共{len(self.local_words)}个词")
        except Exception as e:
            logger.error(f"加载本地敏感词库失败: {str(e)}")
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
    
    async def check_sensitive(self, text: str) -> Tuple[bool, List[str], str]:
        """
        检查文本是否包含敏感词
        
        参数:
            text: 待检查的文本
            
        返回:
            (是否包含敏感词, 检测到的敏感词列表, 处理建议)
        """
        if not self.is_initialized:
            await self.initialize()
        
        # 检查缓存
        if self.cache_enabled:
            cache_result = self._check_cache(text)
            if cache_result is not None:
                return cache_result
        
        result = (False, [], "")
        
        # 根据过滤器类型选择检测方法
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
                    logger.error(f"第三方敏感词检测失败，回退到本地结果: {str(e)}")
                    result = local_result
        
        # 更新缓存
        if self.cache_enabled:
            self._update_cache(text, result)
        
        return result
    
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
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.third_party_api_url,
                    json={"text": text},
                    headers=headers,
                    timeout=self.third_party_api_timeout
                ) as response:
                    if response.status != 200:
                        logger.error(f"第三方敏感词API返回错误状态码: {response.status}")
                        return False, [], ""
                    
                    data = await response.json()
                    
                    # 解析API返回结果（不同API格式可能需要调整）
                    is_sensitive = data.get("is_sensitive", False)
                    words = data.get("words", [])
                    suggestion = data.get("suggestion", self.default_response)
                    
                    return is_sensitive, words, suggestion
        
        except Exception as e:
            logger.error(f"调用第三方敏感词API出错: {str(e)}")
            # 发生错误时可以选择回退到本地检测
            if self.filter_type == SensitiveWordFilterType.HYBRID:
                return await self._check_local(text)
            return False, [], ""
    
    def _check_cache(self, text: str) -> Optional[Tuple[bool, List[str], str]]:
        """检查文本是否在缓存中"""
        if text in self.cache:
            timestamp, result = self.cache[text]
            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                # 缓存过期，删除
                del self.cache[text]
        return None
    
    def _update_cache(self, text: str, result: Tuple[bool, List[str], str]):
        """更新缓存"""
        self.cache[text] = (time.time(), result)
        
        # 简单的缓存清理，避免内存泄漏
        if len(self.cache) > 10000:  # 最多缓存10000条记录
            # 删除最旧的20%记录
            items = sorted(self.cache.items(), key=lambda x: x[1][0])
            for key, _ in items[:int(len(items) * 0.2)]:
                del self.cache[key]
    
    def add_sensitive_word(self, word: str) -> bool:
        """
        添加敏感词到本地词库
        
        参数:
            word: 要添加的敏感词
            
        返回:
            添加是否成功
        """
        if not word or word in self.local_words:
            return False
        
        try:
            # 更新内存中的词库
            self.local_words.add(word)
            self._build_word_tree()
            
            # 更新文件
            with open(self.local_dict_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{word}")
            
            # 清理可能包含此词的缓存
            if self.cache_enabled:
                keys_to_remove = []
                for key in self.cache:
                    if word in key:
                        keys_to_remove.append(key)
                for key in keys_to_remove:
                    del self.cache[key]
            
            return True
        
        except Exception as e:
            logger.error(f"添加敏感词失败: {str(e)}")
            return False
    
    def remove_sensitive_word(self, word: str) -> bool:
        """
        从本地词库中移除敏感词
        
        参数:
            word: 要移除的敏感词
            
        返回:
            移除是否成功
        """
        if not word or word not in self.local_words:
            return False
        
        try:
            # 更新内存中的词库
            self.local_words.remove(word)
            self._build_word_tree()
            
            # 更新文件
            with open(self.local_dict_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with open(self.local_dict_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    if line.strip() != word:
                        f.write(line)
            
            # 清理包含此词的缓存
            if self.cache_enabled:
                keys_to_remove = []
                for key in self.cache:
                    if word in key:
                        keys_to_remove.append(key)
                for key in keys_to_remove:
                    del self.cache[key]
            
            return True
        
        except Exception as e:
            logger.error(f"移除敏感词失败: {str(e)}")
            return False
    
    def get_sensitive_words(self) -> List[str]:
        """获取所有本地敏感词"""
        return list(self.local_words)
    
    def set_filter_type(self, filter_type: SensitiveWordFilterType) -> bool:
        """
        设置过滤器类型
        
        参数:
            filter_type: 要设置的过滤器类型
            
        返回:
            设置是否成功
        """
        if filter_type == SensitiveWordFilterType.THIRD_PARTY and not self.third_party_api_url:
            logger.warning("未配置第三方敏感词API URL，无法设置为第三方模式")
            return False
        
        self.filter_type = filter_type
        return True
    
    def clear_cache(self):
        """清空缓存"""
        self.cache = {}

# 全局单例
_filter_instance = None

def get_sensitive_word_filter() -> SensitiveWordFilter:
    """获取敏感词过滤器实例"""
    global _filter_instance
    
    if _filter_instance is None:
        _filter_instance = SensitiveWordFilter()
    
    return _filter_instance
