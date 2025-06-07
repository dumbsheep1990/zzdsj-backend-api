"""三元组提取器
基于AI知识图谱框架的三元组提取功能
"""

from typing import List, Dict, Any, Optional, Callable
import logging
import json
import re

from app.frameworks.ai_knowledge_graph.adapters.llm_adapter import get_llm_adapter
from app.frameworks.ai_knowledge_graph.utils.text_utils import chunk_text

logger = logging.getLogger(__name__)

# 主要提示词
MAIN_SYSTEM_PROMPT = """
你是一个专业的知识提取AI系统，专门从文本中识别实体和关系。
关键要求：所有关系（谓词）必须不超过3个词，最好是1-2个词。这是硬性限制。
"""

MAIN_USER_PROMPT = """
任务：阅读下面的文本（用三个反引号分隔），识别所有主语-谓语-宾语(S-P-O)关系，然后生成一个JSON数组。

遵循以下规则：

- 实体一致性：在整个文档中对实体使用一致的名称。例如，如果"John Smith"在不同地方被提到为"John"、"Mr. Smith"和"John Smith"，则在所有三元组中使用单一一致的形式（最好是最完整的）。
- 原子术语：识别不同的关键术语（例如，对象、位置、组织、缩写、人员、条件、概念、感受）。避免将多个想法合并为一个术语（它们应该尽可能"原子化"）。
- 统一引用：用实际引用的实体替换任何代词（例如，"他"、"她"、"它"、"他们"等），如果可识别。
- 成对关系：如果多个术语在同一句子中共现（或使它们在上下文中相关的短段落），请为每个具有有意义关系的对创建一个三元组。
- 关键指令：谓词必须最多3个词。绝不超过3个词。保持极其简洁。
- 确保识别文本中所有可能的关系并在S-P-O关系中捕获。
- 标准化术语：如果同一概念以轻微变化出现（例如，"人工智能"和"AI"），请始终使用最常见或规范形式。
- 使S-P-O文本的所有文本都小写，甚至是人名和地名。
- 如果提到某人的姓名，请创建与其位置、职业和他们所知的关系（发明、写作、开始、头衔等），如果已知并且符合信息的上下文。

重要考虑：
- 追求实体命名的精确性 - 使用区分相似但不同实体的特定形式
- 通过在整个文档中对相同概念使用相同的实体名称来最大化连通性
- 在识别实体引用时考虑整个上下文
- 所有谓词必须是3个词或更少 - 这是硬性要求

输出要求：

- 不要在JSON之外包含任何文本或评论。
- 仅返回JSON数组，每个三元组作为包含"subject"、"predicate"和"object"的对象。
- 确保JSON有效且格式正确。

期望输出结构的示例：

[
  {
    "subject": "术语A",
    "predicate": "关联到",  // 注意：仅2个词
    "object": "术语B"
  },
  {
    "subject": "术语C",
    "predicate": "使用",  // 注意：仅1个词
    "object": "术语D"
  }
]

重要：只输出JSON数组（带有S-P-O对象），其他什么都不要。

要分析的文本（在三个反引号之间）：
"""


class TripleExtractor:
    """三元组提取器类"""
    
    def __init__(self, config):
        """初始化提取器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.llm_adapter = get_llm_adapter()
        
        logger.info("三元组提取器初始化完成")
    
    def extract_triples(
        self,
        text: str,
        callback: Optional[Callable] = None,
        task_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """从文本中提取三元组
        
        Args:
            text: 输入文本
            callback: 进度回调函数
            task_id: 任务ID
            
        Returns:
            三元组列表
        """
        if not text or not text.strip():
            logger.warning("输入文本为空")
            return []
        
        # 获取分块参数
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        # 分块处理
        text_chunks = chunk_text(text, chunk_size, overlap)
        
        logger.info(f"将文本分为 {len(text_chunks)} 块进行处理 (大小: {chunk_size} 词, 重叠: {overlap} 词)")
        
        all_results = []
        for i, chunk in enumerate(text_chunks):
            if callback:
                progress = 0.1 + (i / len(text_chunks)) * 0.3  # 在0.1-0.4之间
                callback(task_id or "", f"处理第 {i+1}/{len(text_chunks)} 块", progress, None)
            
            logger.info(f"处理第 {i+1}/{len(text_chunks)} 块 ({len(chunk.split())} 词)")
            
            # 处理单个块
            chunk_results = self._process_chunk(chunk, i+1)
            
            if chunk_results:
                # 添加块信息
                for item in chunk_results:
                    item["chunk"] = i + 1
                
                all_results.extend(chunk_results)
            else:
                logger.warning(f"第 {i+1} 块未提取到三元组")
        
        logger.info(f"从所有块中提取到总共 {len(all_results)} 个三元组")
        return all_results
    
    def _process_chunk(self, chunk_text: str, chunk_num: int) -> List[Dict[str, Any]]:
        """处理单个文本块
        
        Args:
            chunk_text: 文本块
            chunk_num: 块编号
            
        Returns:
            三元组列表
        """
        # 构造提示词
        system_prompt = MAIN_SYSTEM_PROMPT
        user_prompt = MAIN_USER_PROMPT + f"```\n{chunk_text}```\n"
        
        try:
            # 调用LLM
            response = self.llm_adapter.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            # 提取JSON
            result = self._extract_json_from_response(response)
            
            if result:
                # 验证和过滤三元组
                valid_triples = []
                invalid_count = 0
                
                for item in result:
                    if isinstance(item, dict) and "subject" in item and "predicate" in item and "object" in item:
                        # 限制谓词长度
                        item["predicate"] = self._limit_predicate_length(item["predicate"])
                        valid_triples.append(item)
                    else:
                        invalid_count += 1
                
                if invalid_count > 0:
                    logger.warning(f"第 {chunk_num} 块：过滤掉 {invalid_count} 个无效三元组")
                
                if not valid_triples:
                    logger.warning(f"第 {chunk_num} 块：未找到有效三元组")
                    return []
                
                return valid_triples
            else:
                logger.error(f"第 {chunk_num} 块：无法从响应中提取有效JSON")
                return []
                
        except Exception as e:
            logger.error(f"处理第 {chunk_num} 块时出错: {str(e)}")
            return []
    
    def _extract_json_from_response(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """从LLM响应中提取JSON
        
        Args:
            response: LLM响应文本
            
        Returns:
            解析的JSON列表或None
        """
        if not response:
            return None
        
        # 首先检查是否包装在代码块中
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        code_match = re.search(code_block_pattern, response)
        if code_match:
            response = code_match.group(1).strip()
            logger.debug("在代码块中找到JSON，提取内容...")
        
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 查找JSON数组的开始和结束
            start_idx = response.find('[')
            if start_idx == -1:
                logger.warning("响应中未找到JSON数组开始")
                return None
            
            # 简单的括号计数来找到匹配的结束括号
            bracket_count = 0
            complete_json = False
            for i in range(start_idx, len(response)):
                if response[i] == '[':
                    bracket_count += 1
                elif response[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        # 找到匹配的结束括号
                        json_str = response[start_idx:i+1]
                        complete_json = True
                        break
            
            # 处理完整的JSON数组
            if complete_json:
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    logger.warning("找到JSON结构但无法解析，尝试修复格式问题...")
                    # 尝试修复常见格式问题
                    fixed_json = self._fix_json_format(json_str)
                    try:
                        return json.loads(fixed_json)
                    except:
                        logger.error("无法修复JSON格式问题")
            else:
                # 处理不完整的JSON
                logger.warning("找到不完整的JSON数组，尝试完成它...")
                return self._complete_incomplete_json(response, start_idx)
        
        return None
    
    def _fix_json_format(self, json_str: str) -> str:
        """修复常见的JSON格式问题
        
        Args:
            json_str: JSON字符串
            
        Returns:
            修复后的JSON字符串
        """
        # 修复缺少引号的键
        fixed_json = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', json_str)
        # 修复尾随逗号
        fixed_json = re.sub(r',(\s*[\]}])', r'\1', fixed_json)
        return fixed_json
    
    def _complete_incomplete_json(self, text: str, start_idx: int) -> Optional[List[Dict[str, Any]]]:
        """完成不完整的JSON数组
        
        Args:
            text: 响应文本
            start_idx: JSON开始位置
            
        Returns:
            解析的JSON列表或None
        """
        # 获取所有完整的对象
        objects = []
        obj_start = -1
        brace_count = 0
        
        # 找到所有完整的对象
        for i in range(start_idx + 1, len(text)):
            if text[i] == '{':
                if brace_count == 0:
                    obj_start = i
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    obj_end = i
                    objects.append(text[obj_start:obj_end+1])
        
        if objects:
            # 重构有效的JSON数组
            reconstructed_json = "[\n" + ",\n".join(objects) + "\n]"
            try:
                return json.loads(reconstructed_json)
            except json.JSONDecodeError:
                logger.warning("无法解析重构的JSON数组，尝试修复格式问题...")
                fixed_json = self._fix_json_format(reconstructed_json)
                try:
                    return json.loads(fixed_json)
                except:
                    logger.error("无法修复重构JSON数组中的格式问题")
        
        return None
    
    def _limit_predicate_length(self, predicate: str, max_words: int = 3) -> str:
        """限制谓词长度
        
        Args:
            predicate: 原始谓词
            max_words: 最大词数
            
        Returns:
            限制长度后的谓词
        """
        words = predicate.split()
        if len(words) <= max_words:
            return predicate
        
        # 如果太长，只使用前max_words个词
        shortened = ' '.join(words[:max_words])
        
        # 如果最后一个词是停用词，则移除
        stop_words = {'a', 'an', 'the', 'of', 'with', 'by', 'to', 'from', 'in', 'on', 'for'}
        if len(words) > 1:
            last_word = shortened.split()[-1].lower()
            if last_word in stop_words:
                shortened = ' '.join(shortened.split()[:-1])
        
        return shortened 