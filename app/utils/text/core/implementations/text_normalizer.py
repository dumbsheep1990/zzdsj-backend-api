"""
多级文本规范化器：提供全面的文本清理和标准化功能
支持中英文混合文本的多级规范化处理
"""

import logging
import re
import unicodedata
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass
import html

from app.utils.text.core.base import TextNormalizer, NormalizationConfig, TextProcessingError

logger = logging.getLogger(__name__)


@dataclass
class NormalizationReport:
    """规范化报告"""
    original_length: int
    normalized_length: int
    changes_made: List[str]
    encoding_issues_fixed: int
    whitespace_normalized: bool
    html_entities_decoded: int
    special_chars_handled: int


class MultiLevelTextNormalizer(TextNormalizer):
    """
    多级文本规范化器
    提供从基础清理到深度标准化的多个级别处理
    """
    
    def __init__(self, config: Optional[NormalizationConfig] = None):
        """
        初始化文本规范化器
        
        参数:
            config: 规范化配置
        """
        super().__init__(config)
        self._init_patterns()
        self._init_character_maps()
        
        logger.info(f"初始化多级文本规范化器，级别: {self.config.level}")
    
    def normalize(self, text: str) -> str:
        """
        执行文本规范化
        
        参数:
            text: 要规范化的文本
            
        返回:
            规范化后的文本
        """
        if not text:
            return ""
        
        try:
            result = self._normalize_by_level(text, self.config.level)
            logger.debug(f"文本规范化完成: {len(text)} -> {len(result)} 字符")
            return result
            
        except Exception as e:
            logger.error(f"文本规范化失败: {str(e)}")
            raise TextProcessingError(f"文本规范化失败: {str(e)}") from e
    
    def normalize_with_report(self, text: str) -> tuple[str, NormalizationReport]:
        """
        执行规范化并返回详细报告
        
        参数:
            text: 要规范化的文本
            
        返回:
            (规范化文本, 规范化报告)
        """
        if not text:
            return "", NormalizationReport(0, 0, [], 0, False, 0, 0)
        
        original_length = len(text)
        changes_made = []
        
        try:
            # 记录各步骤的处理
            normalized_text = text
            
            # 1. 编码规范化
            if self.config.level >= 1:
                normalized_text, encoding_fixes = self._fix_encoding_issues(normalized_text)
                if encoding_fixes > 0:
                    changes_made.append(f"修复编码问题: {encoding_fixes}处")
            else:
                encoding_fixes = 0
            
            # 2. HTML实体解码
            if self.config.level >= 1:
                normalized_text, html_entities = self._decode_html_entities(normalized_text)
                if html_entities > 0:
                    changes_made.append(f"解码HTML实体: {html_entities}个")
            else:
                html_entities = 0
            
            # 3. 空白字符规范化
            if self.config.level >= 1:
                old_text = normalized_text
                normalized_text = self._normalize_whitespace(normalized_text)
                whitespace_normalized = old_text != normalized_text
                if whitespace_normalized:
                    changes_made.append("规范化空白字符")
            else:
                whitespace_normalized = False
            
            # 4. 特殊字符处理
            if self.config.level >= 2:
                normalized_text, special_chars = self._handle_special_characters(normalized_text)
                if special_chars > 0:
                    changes_made.append(f"处理特殊字符: {special_chars}个")
            else:
                special_chars = 0
            
            # 5. 更高级的规范化
            if self.config.level >= 3:
                normalized_text = self._advanced_normalization(normalized_text)
                changes_made.append("应用高级规范化")
            
            report = NormalizationReport(
                original_length=original_length,
                normalized_length=len(normalized_text),
                changes_made=changes_made,
                encoding_issues_fixed=encoding_fixes,
                whitespace_normalized=whitespace_normalized,
                html_entities_decoded=html_entities,
                special_chars_handled=special_chars
            )
            
            return normalized_text, report
            
        except Exception as e:
            logger.error(f"文本规范化失败: {str(e)}")
            raise TextProcessingError(f"文本规范化失败: {str(e)}") from e
    
    def clean_text(self, text: str, aggressive: bool = False) -> str:
        """
        文本清理（移除不需要的内容）
        
        参数:
            text: 要清理的文本
            aggressive: 是否使用激进清理模式
            
        返回:
            清理后的文本
        """
        if not text:
            return ""
        
        cleaned_text = text
        
        # 基础清理
        cleaned_text = self._remove_control_characters(cleaned_text)
        cleaned_text = self._remove_excessive_punctuation(cleaned_text)
        
        if aggressive:
            # 激进清理
            cleaned_text = self._remove_urls(cleaned_text)
            cleaned_text = self._remove_emails(cleaned_text)
            cleaned_text = self._remove_phone_numbers(cleaned_text)
            cleaned_text = self._remove_dates(cleaned_text)
            cleaned_text = self._remove_numbers(cleaned_text)
        
        return cleaned_text.strip()
    
    def standardize_punctuation(self, text: str) -> str:
        """
        标准化标点符号
        
        参数:
            text: 要处理的文本
            
        返回:
            标准化后的文本
        """
        if not text:
            return ""
        
        # 中文标点规范化
        standardized = text
        
        # 统一引号
        standardized = re.sub(r'["""]', '"', standardized)
        standardized = re.sub(r'[''']', "'", standardized)
        
        # 统一破折号
        standardized = re.sub(r'[—–-]', '-', standardized)
        
        # 统一省略号
        standardized = re.sub(r'\.{3,}|…+', '...', standardized)
        
        # 中英文标点转换（根据配置）
        if hasattr(self.config, 'prefer_chinese_punctuation') and self.config.prefer_chinese_punctuation:
            standardized = self._convert_to_chinese_punctuation(standardized)
        elif hasattr(self.config, 'prefer_english_punctuation') and self.config.prefer_english_punctuation:
            standardized = self._convert_to_english_punctuation(standardized)
        
        return standardized
    
    def normalize_unicode(self, text: str, form: str = 'NFC') -> str:
        """
        Unicode规范化
        
        参数:
            text: 要规范化的文本
            form: 规范化形式 (NFC, NFD, NFKC, NFKD)
            
        返回:
            Unicode规范化后的文本
        """
        if not text:
            return ""
        
        try:
            return unicodedata.normalize(form, text)
        except Exception as e:
            logger.warning(f"Unicode规范化失败: {str(e)}")
            return text
    
    def remove_accents(self, text: str) -> str:
        """
        移除重音符号
        
        参数:
            text: 要处理的文本
            
        返回:
            移除重音后的文本
        """
        if not text:
            return ""
        
        # 分解Unicode字符
        nfd_text = unicodedata.normalize('NFD', text)
        
        # 移除重音标记
        without_accents = ''.join(
            char for char in nfd_text
            if unicodedata.category(char) != 'Mn'
        )
        
        return without_accents
    
    def _normalize_by_level(self, text: str, level: int) -> str:
        """根据级别执行规范化"""
        normalized_text = text
        
        if level >= 1:
            # 级别1：基础规范化
            normalized_text = self._basic_normalization(normalized_text)
        
        if level >= 2:
            # 级别2：中等规范化
            normalized_text = self._medium_normalization(normalized_text)
        
        if level >= 3:
            # 级别3：高级规范化
            normalized_text = self._advanced_normalization(normalized_text)
        
        return normalized_text
    
    def _basic_normalization(self, text: str) -> str:
        """基础规范化"""
        # 1. 修复编码问题
        text, _ = self._fix_encoding_issues(text)
        
        # 2. 解码HTML实体
        text, _ = self._decode_html_entities(text)
        
        # 3. 规范化空白字符
        text = self._normalize_whitespace(text)
        
        # 4. 移除控制字符
        text = self._remove_control_characters(text)
        
        return text
    
    def _medium_normalization(self, text: str) -> str:
        """中等规范化"""
        # 1. 处理特殊字符
        text, _ = self._handle_special_characters(text)
        
        # 2. 标准化标点符号
        text = self.standardize_punctuation(text)
        
        # 3. Unicode规范化
        text = self.normalize_unicode(text)
        
        # 4. 处理重复字符
        text = self._handle_repeated_characters(text)
        
        return text
    
    def _advanced_normalization(self, text: str) -> str:
        """高级规范化"""
        # 1. 智能标点处理
        text = self._smart_punctuation_handling(text)
        
        # 2. 文本结构优化
        text = self._optimize_text_structure(text)
        
        # 3. 语言特定规范化
        text = self._language_specific_normalization(text)
        
        return text
    
    def _fix_encoding_issues(self, text: str) -> tuple[str, int]:
        """修复编码问题"""
        fixes = 0
        
        # 修复常见的编码问题
        replacements = [
            ('\ufffd', ''),  # 替换字符
            ('\u200b', ''),  # 零宽空格
            ('\u200c', ''),  # 零宽非连接符
            ('\u200d', ''),  # 零宽连接符
            ('\ufeff', ''),  # 字节顺序标记
        ]
        
        for old, new in replacements:
            count = text.count(old)
            if count > 0:
                text = text.replace(old, new)
                fixes += count
        
        return text, fixes
    
    def _decode_html_entities(self, text: str) -> tuple[str, int]:
        """解码HTML实体"""
        original_text = text
        decoded_text = html.unescape(text)
        
        # 计算解码的实体数量
        entities_count = len(re.findall(r'&[a-zA-Z][a-zA-Z0-9]*;|&#\d+;|&#x[0-9a-fA-F]+;', original_text))
        
        return decoded_text, entities_count
    
    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 替换各种空白字符为普通空格
        text = re.sub(r'[\t\r\n\f\v\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+', ' ', text)
        
        # 合并多个空格
        text = re.sub(r' +', ' ', text)
        
        # 移除行首行尾空格
        text = '\n'.join(line.strip() for line in text.split('\n'))
        
        # 移除多余的空行
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _remove_control_characters(self, text: str) -> str:
        """移除控制字符"""
        # 保留必要的控制字符（如换行符、制表符）
        allowed_controls = {'\n', '\t'}
        
        cleaned_chars = []
        for char in text:
            if unicodedata.category(char)[0] == 'C' and char not in allowed_controls:
                continue
            cleaned_chars.append(char)
        
        return ''.join(cleaned_chars)
    
    def _handle_special_characters(self, text: str) -> tuple[str, int]:
        """处理特殊字符"""
        handled_count = 0
        
        # 替换常见的特殊字符
        for old_char, new_char in self.char_replacements.items():
            count = text.count(old_char)
            if count > 0:
                text = text.replace(old_char, new_char)
                handled_count += count
        
        return text, handled_count
    
    def _handle_repeated_characters(self, text: str) -> str:
        """处理重复字符"""
        # 限制连续相同字符的数量
        text = re.sub(r'(.)\1{3,}', r'\1\1\1', text)  # 最多3个重复
        
        # 特殊处理标点符号
        text = re.sub(r'([!?])\1{2,}', r'\1\1', text)  # 最多2个感叹号/问号
        text = re.sub(r'(\.)\1{4,}', r'...', text)     # 多个点号变为省略号
        
        return text
    
    def _smart_punctuation_handling(self, text: str) -> str:
        """智能标点处理"""
        # 中英文标点符号间距调整
        # 中文字符后的英文标点前加空格
        text = re.sub(r'([\u4e00-\u9fff])([.!?])', r'\1 \2', text)
        
        # 英文字符和中文标点间加空格
        text = re.sub(r'([a-zA-Z])(，|。|！|？)', r'\1 \2', text)
        
        # 移除标点前多余空格
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        
        return text
    
    def _optimize_text_structure(self, text: str) -> str:
        """优化文本结构"""
        # 段落间距标准化
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 句子间距标准化
        text = re.sub(r'([.!?])\s{2,}', r'\1 ', text)
        
        # 修复常见的格式问题
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)  # 句号后大写字母前加空格
        
        return text
    
    def _language_specific_normalization(self, text: str) -> str:
        """语言特定的规范化"""
        # 检测主要语言
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.findall(r'[^\s]', text))
        
        if total_chars > 0 and chinese_chars / total_chars > 0.5:
            # 中文文本的特殊处理
            text = self._normalize_chinese_text(text)
        else:
            # 英文文本的特殊处理
            text = self._normalize_english_text(text)
        
        return text
    
    def _normalize_chinese_text(self, text: str) -> str:
        """中文文本规范化"""
        # 中文标点规范化
        text = self._convert_to_chinese_punctuation(text)
        
        # 中英文间加空格
        text = re.sub(r'([\u4e00-\u9fff])([a-zA-Z0-9])', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z0-9])([\u4e00-\u9fff])', r'\1 \2', text)
        
        return text
    
    def _normalize_english_text(self, text: str) -> str:
        """英文文本规范化"""
        # 英文标点规范化
        text = self._convert_to_english_punctuation(text)
        
        # 单词首字母大写（句首）
        text = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
        
        return text
    
    def _convert_to_chinese_punctuation(self, text: str) -> str:
        """转换为中文标点"""
        conversions = {
            ',': '，',
            '.': '。',
            '!': '！',
            '?': '？',
            ';': '；',
            ':': '：',
            '(': '（',
            ')': '）',
            '[': '【',
            ']': '】'
        }
        
        for eng, chn in conversions.items():
            text = text.replace(eng, chn)
        
        return text
    
    def _convert_to_english_punctuation(self, text: str) -> str:
        """转换为英文标点"""
        conversions = {
            '，': ',',
            '。': '.',
            '！': '!',
            '？': '?',
            '；': ';',
            '：': ':',
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']'
        }
        
        for chn, eng in conversions.items():
            text = text.replace(chn, eng)
        
        return text
    
    def _remove_urls(self, text: str) -> str:
        """移除URL"""
        url_pattern = r'https?://[^\s]+'
        return re.sub(url_pattern, '', text)
    
    def _remove_emails(self, text: str) -> str:
        """移除邮箱地址"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.sub(email_pattern, '', text)
    
    def _remove_phone_numbers(self, text: str) -> str:
        """移除电话号码"""
        phone_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',      # 123-456-7890
            r'\b\d{3}\.\d{3}\.\d{4}\b',    # 123.456.7890
            r'\b\d{10}\b',                 # 1234567890
            r'\b\(\d{3}\)\s*\d{3}-\d{4}\b' # (123) 456-7890
        ]
        
        for pattern in phone_patterns:
            text = re.sub(pattern, '', text)
        
        return text
    
    def _remove_dates(self, text: str) -> str:
        """移除日期"""
        date_patterns = [
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',    # 2023-01-01
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b',    # 01/01/2023
            r'\b\d{4}年\d{1,2}月\d{1,2}日\b'       # 2023年1月1日
        ]
        
        for pattern in date_patterns:
            text = re.sub(pattern, '', text)
        
        return text
    
    def _remove_numbers(self, text: str) -> str:
        """移除数字"""
        return re.sub(r'\b\d+\.?\d*\b', '', text)
    
    def _remove_excessive_punctuation(self, text: str) -> str:
        """移除过度的标点符号"""
        # 移除多余的标点
        text = re.sub(r'[!]{3,}', '!!', text)
        text = re.sub(r'[?]{3,}', '??', text)
        text = re.sub(r'[.]{4,}', '...', text)
        
        return text
    
    def _init_patterns(self):
        """初始化正则表达式模式"""
        self.whitespace_pattern = re.compile(r'\s+')
        self.punctuation_pattern = re.compile(r'[^\w\s]')
        self.url_pattern = re.compile(r'https?://[^\s]+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    def _init_character_maps(self):
        """初始化字符映射表"""
        self.char_replacements = {
            # 全角转半角
            '　': ' ',      # 全角空格
            '！': '!',
            '？': '?',
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '｛': '{',
            '｝': '}',
            
            # 特殊字符替换
            '…': '...',
            '—': '-',
            '–': '-',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            
            # 数学符号
            '×': 'x',
            '÷': '/',
            '±': '+-',
            
            # 货币符号标准化
            '￥': '¥',
            '€': 'EUR',
            '£': 'GBP',
        } 