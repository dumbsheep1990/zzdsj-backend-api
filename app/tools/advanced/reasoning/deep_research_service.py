"""
深度研究服务模块
提供结构化的深度研究流程，支持多阶段处理和矢量索引
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Union, Set

from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.node_parser import NodeParser
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms.base import LLM
from llama_index.core.tools import BaseTool
from llama_index.readers.web import SimpleWebPageReader

from app.tools.advanced.reasoning.cot_manager import CoTManager
from app.tools.base.search.search_tool import get_search_tool

logger = logging.getLogger(__name__)

class DeepResearchService:
    """
    深度研究服务
    提供结构化的多阶段研究流程，包括任务规划、网络搜索、内容抓取、回答子问题和报告合成
    """
    
    def __init__(
        self,
        llm: Optional[LLM] = None,
        embed_model: Optional[BaseEmbedding] = None,
        node_parser: Optional[NodeParser] = None,
        search_tool: Optional[BaseTool] = None,
        cot_manager: Optional[CoTManager] = None,
        max_sub_questions: int = 3,
        max_urls_per_query: int = 3,
        enable_cot_display: bool = True
    ):
        """
        初始化深度研究服务
        
        参数:
            llm: 语言模型实例，如果为None则使用全局设置的LLM
            embed_model: 嵌入模型实例，如果为None则使用全局设置的嵌入模型
            node_parser: 节点解析器实例，如果为None则使用全局设置的节点解析器
            search_tool: 搜索工具实例，如果为None则获取默认搜索工具
            cot_manager: CoT管理器实例，如果为None则创建新实例
            max_sub_questions: 最大子问题数量
            max_urls_per_query: 每个查询最大URL数量
            enable_cot_display: 是否默认启用CoT显示
        """
        self.llm = llm or Settings.llm
        self.embed_model = embed_model or Settings.embed_model
        self.node_parser = node_parser or Settings.node_parser
        self.search_tool = search_tool or get_search_tool()
        self.cot_manager = cot_manager or CoTManager(llm=self.llm)
        
        self.max_sub_questions = max_sub_questions
        self.max_urls_per_query = max_urls_per_query
        self.enable_cot_display = enable_cot_display
        
        # 存储每次执行的信息
        self.current_topic = ""
        self.sub_questions = []
        self.search_results = {}
        self.web_content = {}
        self.sub_answers = {}
    
    async def run(
        self,
        main_topic: str,
        num_sub_questions: int = 3,
        urls_per_query: int = 3,
        language: str = "zh-CN",
        show_cot: Optional[bool] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        执行完整的深度研究流程
        
        参数:
            main_topic: 主要研究问题
            num_sub_questions: 子问题数量，不能超过max_sub_questions
            urls_per_query: 每个查询最大URL数量，不能超过max_urls_per_query
            language: 搜索语言，默认为zh-CN
            show_cot: 是否在响应中显示CoT过程，默认为None表示使用服务的默认设置
            temperature: 温度参数，控制LLM输出随机性
            
        返回:
            包含研究结果的字典
        """
        # 确定是否显示CoT
        show_cot = self.enable_cot_display if show_cot is None else show_cot
        
        # 限制参数范围
        num_sub_questions = min(num_sub_questions, self.max_sub_questions)
        urls_per_query = min(urls_per_query, self.max_urls_per_query)
        
        # 重置执行状态
        self.current_topic = main_topic
        self.sub_questions = []
        self.search_results = {}
        self.web_content = {}
        self.sub_answers = {}
        
        try:
            # 步骤1: 将主问题分解为子问题
            logger.info(f"分解问题: {main_topic}")
            self.sub_questions = await self._decompose_question(
                main_topic, 
                num_sub_questions,
                temperature=temperature
            )
            
            # 步骤2: 对每个子问题进行网络搜索
            logger.info(f"开始搜索子问题: {len(self.sub_questions)}个")
            for i, question in enumerate(self.sub_questions):
                logger.info(f"搜索子问题 {i+1}/{len(self.sub_questions)}: {question}")
                search_results = await self._search_question(
                    question, 
                    urls_per_query,
                    language
                )
                self.search_results[question] = search_results
            
            # 步骤3: 爬取搜索结果的网页内容
            logger.info("爬取网页内容")
            await self._fetch_web_content()
            
            # 步骤4: 回答每个子问题
            logger.info("回答子问题")
            for i, question in enumerate(self.sub_questions):
                logger.info(f"回答子问题 {i+1}/{len(self.sub_questions)}: {question}")
                answer = await self._answer_sub_question(
                    question, 
                    temperature=temperature
                )
                self.sub_answers[question] = answer
            
            # 步骤5: 合成最终报告
            logger.info("合成最终报告")
            final_report = await self._synthesize_report(
                main_topic,
                temperature=temperature
            )
            
            # 整理返回结果
            return self._format_results(main_topic, final_report, show_cot)
            
        except Exception as e:
            logger.error(f"执行深度研究时出错: {str(e)}")
            return {
                "original_query": main_topic,
                "final_answer": f"执行深度研究时出错: {str(e)}",
                "show_cot": False
            }
    
    async def _decompose_question(
        self, 
        main_question: str, 
        num_questions: int,
        temperature: float = 0.3
    ) -> List[str]:
        """
        将主问题分解为子问题
        
        参数:
            main_question: 主要研究问题
            num_questions: 要生成的子问题数量
            temperature: 温度参数，控制LLM输出随机性
            
        返回:
            子问题列表
        """
        system_prompt = (
            f"你是一个专业的研究助手，负责帮助拆解复杂问题。"
            f"请将以下复杂问题拆分为{num_questions}个具体、明确的子问题，以便进行深入研究。"
            f"这些子问题应该涵盖原问题的不同方面，并且层层递进，引导向全面的答案。"
            f"输出格式应为JSON数组，每个元素是一个子问题。"
        )
        
        user_message = (
            f"请将以下复杂问题拆分为{num_questions}个明确的子问题:\n\n"
            f"{main_question}\n\n"
            f"请确保子问题:\n"
            f"1. 涵盖原问题的各个重要方面\n"
            f"2. 具体、明确、便于搜索\n"
            f"3. 层层递进，有助于构建全面答案\n\n"
            f"请以JSON数组格式输出子问题，不要包含额外解释。"
        )
        
        # 使用COT思考更好的问题分解
        cot_result = await self.cot_manager.invoke_cot(
            query=user_message,
            system_prompt=system_prompt,
            use_multi_step=True,
            temperature=temperature,
            enable_cot=True
        )
        
        # 尝试从输出中提取JSON数组
        sub_questions = []
        try:
            answer = cot_result.get("final_answer", "")
            
            # 尝试从文本中提取JSON数组
            json_start = answer.find("[")
            json_end = answer.rfind("]") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = answer[json_start:json_end]
                sub_questions = json.loads(json_str)
                
                # 确保至少有一个子问题
                if not sub_questions or not isinstance(sub_questions, list):
                    raise ValueError("未能提取到有效的子问题列表")
                
                # 限制子问题数量
                sub_questions = sub_questions[:num_questions]
                
            else:
                # 如果没有找到JSON格式，尝试直接从文本中提取问题
                import re
                # 查找类似于"1. 问题描述"的模式
                matches = re.findall(r'\d+[\.\)]\s*(.*?)(?=\d+[\.\)]|$)', answer, re.DOTALL)
                if matches:
                    sub_questions = [q.strip() for q in matches if q.strip()][:num_questions]
                
                # 如果仍然没有找到问题，则直接分割文本
                if not sub_questions:
                    lines = [line.strip() for line in answer.split('\n') if line.strip()]
                    sub_questions = [line for line in lines if '?' in line or len(line) > 10][:num_questions]
        
        except Exception as e:
            logger.error(f"解析子问题时出错: {str(e)}")
            # 如果解析失败，创建默认子问题
            sub_questions = [f"{main_question} (方面 {i+1})" for i in range(num_questions)]
        
        # 确保返回指定数量的子问题
        if len(sub_questions) < num_questions:
            additional = num_questions - len(sub_questions)
            sub_questions.extend([f"{main_question} (附加方面 {i+1})" for i in range(additional)])
        
        return sub_questions
    
    async def _search_question(
        self, 
        question: str, 
        max_results: int,
        language: str = "zh-CN"
    ) -> List[Dict[str, Any]]:
        """
        使用搜索工具搜索子问题
        
        参数:
            question: 要搜索的问题
            max_results: 最大结果数量
            language: 搜索语言
            
        返回:
            搜索结果列表
        """
        try:
            # 调用搜索工具
            search_results = await self.search_tool._arun(
                query=question,
                limit=max_results,
                language=language
            )
            
            # 提取URL和摘要
            urls_with_snippets = []
            for result in search_results:
                urls_with_snippets.append({
                    "url": result.get("link", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", "")
                })
            
            return urls_with_snippets
            
        except Exception as e:
            logger.error(f"搜索问题时出错: {str(e)}")
            return []
    
    async def _fetch_web_content(self) -> None:
        """
        抓取搜索结果中的网页内容
        
        将内容存储在self.web_content中，键为URL
        """
        # 收集所有唯一的URL
        all_urls = set()
        for results in self.search_results.values():
            for result in results:
                url = result.get("url")
                if url:
                    all_urls.add(url)
        
        # 批量抓取网页内容
        try:
            logger.info(f"开始抓取 {len(all_urls)} 个网页")
            
            # 使用asyncio并发抓取
            async def fetch_url(url):
                try:
                    # 使用SimpleWebPageReader抓取内容
                    documents = await SimpleWebPageReader(html_to_text=True).aload_data([url])
                    if documents and len(documents) > 0:
                        return url, documents[0].text
                    return url, ""
                except Exception as e:
                    logger.error(f"抓取URL {url} 时出错: {str(e)}")
                    return url, ""
            
            # 并发抓取所有URL
            tasks = [fetch_url(url) for url in all_urls]
            results = await asyncio.gather(*tasks)
            
            # 存储结果
            for url, content in results:
                if content:
                    self.web_content[url] = content
            
            logger.info(f"成功抓取 {len(self.web_content)} 个网页")
            
        except Exception as e:
            logger.error(f"批量抓取网页时出错: {str(e)}")
    
    async def _answer_sub_question(
        self, 
        question: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        使用搜索结果和网页内容回答子问题
        
        参数:
            question: 要回答的子问题
            temperature: 温度参数，控制LLM输出随机性
            
        返回:
            包含回答和思维链的字典
        """
        # 获取该问题的搜索结果
        search_results = self.search_results.get(question, [])
        
        # 构建上下文信息
        context = []
        for result in search_results:
            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            # 获取完整网页内容
            content = self.web_content.get(url, "")
            
            if content:
                context.append(f"标题: {title}\n网址: {url}\n内容: {content[:2000]}...\n")
            elif snippet:
                context.append(f"标题: {title}\n网址: {url}\n摘要: {snippet}\n")
        
        context_str = "\n===\n".join(context)
        
        # 准备提示
        system_prompt = (
            "你是一个专业的研究助手，根据提供的信息回答问题。"
            "请使用提供的上下文来回答问题，并确保答案全面、准确、有条理。"
            "如果上下文信息不足以完全回答问题，请说明信息不足的部分。"
        )
        
        user_message = (
            f"请根据以下信息回答问题:\n\n"
            f"问题: {question}\n\n"
            f"参考信息:\n{context_str}\n\n"
            f"请提供全面、准确的回答，引用相关事实和数据。如有必要，请注明信息不足的部分。"
        )
        
        # 使用COT思考来回答问题
        cot_result = await self.cot_manager.invoke_cot(
            query=user_message,
            system_prompt=system_prompt,
            use_multi_step=True,
            temperature=temperature,
            enable_cot=True
        )
        
        return cot_result
    
    async def _synthesize_report(
        self, 
        main_question: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        合成最终研究报告
        
        参数:
            main_question: 主要研究问题
            temperature: 温度参数，控制LLM输出随机性
            
        返回:
            包含报告和思维链的字典
        """
        # 准备子问题和答案的摘要
        sub_qa_summary = ""
        for i, question in enumerate(self.sub_questions):
            answer = self.sub_answers.get(question, {})
            final_answer = answer.get("final_answer", "未获取到答案")
            
            sub_qa_summary += f"子问题 {i+1}: {question}\n"
            sub_qa_summary += f"回答: {final_answer}\n\n"
        
        # 准备提示
        system_prompt = (
            "你是一个专业的研究报告撰写专家。"
            "请基于提供的子问题答案，合成一份全面、连贯的研究报告，"
            "报告应该完整回答主问题，并保持逻辑清晰、结构有序。"
            "适当使用小标题、要点和总结来增强可读性。"
        )
        
        user_message = (
            f"请基于以下子问题的答案，撰写一份完整的研究报告，回答主问题:\n\n"
            f"主问题: {main_question}\n\n"
            f"子问题和答案:\n{sub_qa_summary}\n\n"
            f"请确保报告:\n"
            f"1. 全面回答主问题\n"
            f"2. 整合所有子问题的答案\n"
            f"3. 保持逻辑清晰、结构有序\n"
            f"4. 适当使用小标题和要点增强可读性\n"
            f"5. 包含一个简短的总结段落"
        )
        
        # 使用COT思考来合成报告
        cot_result = await self.cot_manager.invoke_cot(
            query=user_message,
            system_prompt=system_prompt,
            use_multi_step=True,
            temperature=temperature,
            enable_cot=True
        )
        
        return cot_result
    
    def _format_results(
        self, 
        original_query: str, 
        final_report: Dict[str, Any],
        show_cot: bool
    ) -> Dict[str, Any]:
        """
        格式化最终结果
        
        参数:
            original_query: 原始查询
            final_report: 最终报告
            show_cot: 是否显示思维链
            
        返回:
            格式化后的结果字典
        """
        # 准备返回的数据结构
        result = {
            "original_query": original_query,
            "final_answer": final_report.get("final_answer", ""),
            "sub_questions": self.sub_questions,
            "show_cot": show_cot
        }
        
        # 如果需要显示思维链，添加相关信息
        if show_cot:
            # 添加最终报告的思维链
            result["cot_steps"] = final_report.get("cot_steps", "")
            
            # 添加每个子问题的思维链和答案
            sub_question_details = []
            for question in self.sub_questions:
                answer_data = self.sub_answers.get(question, {})
                
                sub_detail = {
                    "question": question,
                    "answer": answer_data.get("final_answer", ""),
                    "cot_steps": answer_data.get("cot_steps", "")
                }
                
                # 添加搜索结果
                search_data = self.search_results.get(question, [])
                sub_detail["search_results"] = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", "")
                    }
                    for item in search_data
                ]
                
                sub_question_details.append(sub_detail)
            
            result["sub_question_details"] = sub_question_details
        
        return result

def get_deep_research_service(
    llm: Optional[LLM] = None,
    embed_model: Optional[BaseEmbedding] = None,
    node_parser: Optional[NodeParser] = None,
    search_tool: Optional[BaseTool] = None,
    cot_manager: Optional[CoTManager] = None,
    max_sub_questions: int = 3,
    max_urls_per_query: int = 3,
    enable_cot_display: bool = True
) -> DeepResearchService:
    """
    获取深度研究服务实例
    
    参数:
        llm: 语言模型实例，如果为None则使用全局设置的LLM
        embed_model: 嵌入模型实例，如果为None则使用全局设置的嵌入模型
        node_parser: 节点解析器实例，如果为None则使用全局设置的节点解析器
        search_tool: 搜索工具实例，如果为None则获取默认搜索工具
        cot_manager: CoT管理器实例，如果为None则创建新实例
        max_sub_questions: 最大子问题数量
        max_urls_per_query: 每个查询最大URL数量
        enable_cot_display: 是否默认启用CoT显示
        
    返回:
        深度研究服务实例
    """
    return DeepResearchService(
        llm=llm,
        embed_model=embed_model,
        node_parser=node_parser,
        search_tool=search_tool,
        cot_manager=cot_manager,
        max_sub_questions=max_sub_questions,
        max_urls_per_query=max_urls_per_query,
        enable_cot_display=enable_cot_display
    )
