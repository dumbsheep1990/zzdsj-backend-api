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

from app.middleware.cot_manager import CoTManager
from app.middleware.search_tool import get_search_tool

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
        # 使用传入的实例或全局设置
        self.llm = llm or Settings.llm
        self.embed_model = embed_model or Settings.embed_model
        self.node_parser = node_parser or Settings.node_parser
        
        # 初始化工具和管理器
        self.search_tool = search_tool or get_search_tool()
        self.cot_manager = cot_manager or CoTManager(llm=self.llm)
        self.web_reader = SimpleWebPageReader()
        
        # 配置参数
        self.max_sub_questions = max_sub_questions
        self.max_urls_per_query = max_urls_per_query
        self.enable_cot_display = enable_cot_display
    
    async def _execute_web_search(self, query: str, language: str = "zh-CN") -> List[Dict[str, Any]]:
        """
        执行Web搜索
        
        参数:
            query: 搜索查询
            language: 搜索语言，默认为zh-CN
            
        返回:
            搜索结果列表
        """
        try:
            # 使用search_tool进行搜索
            if hasattr(self.search_tool, "_arun"):
                search_results_text = await self.search_tool._arun(
                    query=query,
                    language=language,
                    max_results=self.max_urls_per_query
                )
            else:
                search_results_text = self.search_tool._run(
                    query=query,
                    language=language,
                    max_results=self.max_urls_per_query
                )
            
            # 解析搜索结果文本
            # 假设结果格式类似于"1. 标题\n   URL: http://example.com\n   摘要: ..."
            results = []
            current_result = {}
            
            for line in search_results_text.split('\n'):
                line = line.strip()
                
                # 新结果开始
                if line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or \
                   line.startswith("4.") or line.startswith("5."):
                    if current_result and "title" in current_result and "url" in current_result:
                        results.append(current_result)
                    current_result = {"title": line.split(".", 1)[1].strip()}
                
                # URL行
                elif line.startswith("URL:") or line.startswith("   URL:"):
                    current_result["url"] = line.split(":", 1)[1].strip()
                
                # 摘要行
                elif line.startswith("摘要:") or line.startswith("   摘要:"):
                    current_result["content"] = line.split(":", 1)[1].strip()
                
                # 来源行
                elif line.startswith("来源:") or line.startswith("   来源:"):
                    current_result["source"] = line.split(":", 1)[1].strip()
            
            # 添加最后一个结果
            if current_result and "title" in current_result and "url" in current_result:
                results.append(current_result)
            
            return results
            
        except Exception as e:
            logger.error(f"执行Web搜索时出错: {str(e)}")
            return []
    
    async def _fetch_web_content(self, urls: List[str]) -> List[Document]:
        """
        抓取网页内容
        
        参数:
            urls: URL列表
            
        返回:
            Document列表
        """
        try:
            # 使用SimpleWebPageReader抓取内容
            documents = self.web_reader.load_data(urls)
            return documents
            
        except Exception as e:
            logger.error(f"抓取网页内容时出错: {str(e)}")
            # 如果出错，尝试一个一个抓取
            documents = []
            for url in urls:
                try:
                    docs = self.web_reader.load_data([url])
                    documents.extend(docs)
                except Exception as url_e:
                    logger.error(f"抓取URL '{url}'时出错: {str(url_e)}")
            
            return documents
    
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
        执行深度研究
        
        参数:
            main_topic: 主研究主题
            num_sub_questions: 子问题数量，最大不超过max_sub_questions
            urls_per_query: 每个查询的URL数量，最大不超过max_urls_per_query
            language: 搜索语言，默认为zh-CN
            show_cot: 是否在响应中显示CoT过程，默认为None表示使用服务的默认设置
            temperature: 温度参数，控制LLM输出随机性
            
        返回:
            包含研究结果和思维链的字典
        """
        # 确定是否显示CoT
        show_cot = self.enable_cot_display if show_cot is None else show_cot
        
        # 限制参数
        num_sub_questions = min(num_sub_questions, self.max_sub_questions)
        urls_per_query = min(urls_per_query, self.max_urls_per_query)
        
        # 初始化研究输出结构
        research_output = {
            "main_topic": main_topic,
            "status": "In Progress",
            "planning": None,
            "search_results_summary": None,
            "session_knowledge_summary": None,
            "answered_sub_questions": [],
            "final_report": None,
            "final_report_cot": None,
            "show_cot": show_cot,
            "error_message": None
        }
        
        try:
            logger.info(f"开始深度研究: {main_topic}")
            
            # === 阶段1: 任务规划 ===
            logger.info("阶段1: 任务规划...")
            
            planning_prompt = (
                f"你是一位AI研究规划专家，需要为以下主题设计一个结构化的研究计划：\n\n"
                f"研究主题: \"{main_topic}\"\n\n"
                f"请设计一个包含{num_sub_questions}个子问题的研究计划，每个子问题都应该探索主题的不同方面。"
                f"对于每个子问题，还需要提供一个更具体的搜索查询，用于获取相关信息。\n\n"
                f"请以JSON格式输出，包含以下字段:\n"
                f"{{\"sub_tasks\": [{{\"sub_question\": \"子问题1\", \"search_query\": \"搜索查询1\"}}, ...]}}\n\n"
                f"确保你的输出是有效的JSON格式，只包含上述结构，没有额外的文本。"
            )
            
            planning_system_prompt = (
                "你是一位精通研究方法的AI助手。你的任务是分析复杂研究主题，并将其分解为有针对性的子问题。"
                "你需要为每个子问题提供专门设计的搜索查询，以获取最相关的信息。"
            )
            
            planning_result = await self.cot_manager.acall_with_cot(
                prompt_content=planning_prompt,
                system_prompt=planning_system_prompt,
                enable_cot=True,
                use_multi_step=False,
                temperature=temperature
            )
            
            planning_cot = planning_result.get("cot_steps", "")
            plan_json_str = planning_result.get("final_answer", "")
            
            try:
                plan_data = json.loads(plan_json_str)
                sub_tasks = plan_data.get("sub_tasks", [])
                
                if not sub_tasks:
                    raise ValueError("未找到子任务")
                
                # 限制子任务数量
                sub_tasks = sub_tasks[:num_sub_questions]
                
                research_output["planning"] = {
                    "plan": sub_tasks,
                    "cot_steps": planning_cot
                }
                
                logger.info(f"生成了包含{len(sub_tasks)}个子任务的计划")
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"解析规划JSON时出错: {str(e)}")
                # 尝试使用多步骤格式重新获取计划
                retry_planning_result = await self.cot_manager.acall_with_cot(
                    prompt_content=planning_prompt,
                    system_prompt=planning_system_prompt,
                    enable_cot=True,
                    use_multi_step=True,  # 使用多步骤格式
                    temperature=temperature
                )
                
                # 从多步骤结果中提取最终答案
                retry_plan_str = retry_planning_result.get("final_answer", "")
                
                try:
                    # 尝试匹配JSON格式
                    import re
                    json_pattern = r'\{[\s\S]*\}'
                    json_match = re.search(json_pattern, retry_plan_str)
                    
                    if json_match:
                        retry_plan_json_str = json_match.group(0)
                        plan_data = json.loads(retry_plan_json_str)
                        sub_tasks = plan_data.get("sub_tasks", [])
                        
                        if not sub_tasks:
                            raise ValueError("未找到子任务")
                        
                        # 限制子任务数量
                        sub_tasks = sub_tasks[:num_sub_questions]
                        
                        research_output["planning"] = {
                            "plan": sub_tasks,
                            "cot_steps": retry_planning_result.get("cot_steps", "")
                        }
                        
                        logger.info(f"重试后生成了包含{len(sub_tasks)}个子任务的计划")
                        
                    else:
                        # 如果仍然无法匹配JSON，手动创建子任务
                        sub_tasks = []
                        for i in range(num_sub_questions):
                            sub_tasks.append({
                                "sub_question": f"{main_topic}的第{i+1}个关键方面是什么?",
                                "search_query": f"{main_topic} 关键方面 重点 第{i+1}"
                            })
                        
                        research_output["planning"] = {
                            "plan": sub_tasks,
                            "cot_steps": "无法从LLM获取有效的计划，使用了默认计划",
                            "is_fallback": True
                        }
                        
                        logger.warning(f"使用了默认计划代替")
                        
                except Exception as retry_e:
                    logger.error(f"重试规划也失败了: {str(retry_e)}")
                    # 使用默认计划
                    sub_tasks = []
                    for i in range(num_sub_questions):
                        sub_tasks.append({
                            "sub_question": f"{main_topic}的第{i+1}个关键方面是什么?",
                            "search_query": f"{main_topic} 关键方面 重点 第{i+1}"
                        })
                    
                    research_output["planning"] = {
                        "plan": sub_tasks,
                        "cot_steps": "无法从LLM获取有效的计划，使用了默认计划",
                        "is_fallback": True
                    }
                    
                    logger.warning(f"使用了默认计划代替")
            
            # === 阶段2: Web搜索 ===
            logger.info("阶段2: Web搜索...")
            all_urls_to_process = set()
            all_search_results = []
            
            for task in sub_tasks:
                search_query = task.get("search_query", main_topic)
                logger.info(f"搜索查询: {search_query}")
                
                # 执行搜索
                search_results = await self._execute_web_search(
                    query=search_query,
                    language=language
                )
                
                task["search_results"] = search_results
                all_search_results.extend(search_results)
                
                # 收集URL
                for result in search_results:
                    if "url" in result:
                        all_urls_to_process.add(result["url"])
            
            if not all_urls_to_process:
                research_output["status"] = "Failed at Web Search"
                research_output["error_message"] = "Web搜索未返回任何URL"
                return research_output
            
            research_output["search_results_summary"] = {
                "collected_urls_count": len(all_urls_to_process),
                "urls": list(all_urls_to_process),
                "search_results": all_search_results
            }
            
            logger.info(f"收集了{len(all_urls_to_process)}个唯一URL")
            
            # === 阶段3: 内容抓取和会话索引 ===
            logger.info("阶段3: 内容抓取和会话索引...")
            
            # 抓取网页内容
            web_documents = await self._fetch_web_content(list(all_urls_to_process))
            
            if not web_documents:
                research_output["status"] = "Failed at Content Fetching"
                research_output["error_message"] = "无法从网页获取内容"
                return research_output
            
            # 创建向量索引
            session_index = VectorStoreIndex.from_documents(
                web_documents,
                embed_model=self.embed_model,
                transformations=[self.node_parser] if self.node_parser else None,
                show_progress=True
            )
            
            session_query_engine = session_index.as_query_engine(
                llm=self.llm,
                similarity_top_k=3
            )
            
            research_output["session_knowledge_summary"] = {
                "indexed_document_count": len(web_documents),
                "document_sources": [doc.metadata.get("source", "N/A") for doc in web_documents[:5]]  # 只显示前5个
            }
            
            logger.info(f"创建了包含{len(web_documents)}个文档的会话知识库")
            
            # === 阶段4: 回答子问题 ===
            logger.info("阶段4: 回答子问题...")
            
            for task in sub_tasks:
                sub_question = task.get("sub_question", "")
                logger.info(f"处理子问题: {sub_question}")
                
                # 检索相关节点
                retrieved_nodes = session_index.as_retriever(similarity_top_k=3).retrieve(sub_question)
                context_str = "\n\n".join([node.get_content() for node in retrieved_nodes])
                
                # 构建prompt
                prompt_for_sub_answer = (
                    f"基于以下提供的上下文信息，回答子问题。\n\n"
                    f"上下文信息:\n{context_str}\n\n"
                    f"子问题: {sub_question}"
                )
                
                # 调用LLM获取CoT回答
                sub_answer_result = await self.cot_manager.acall_with_cot(
                    prompt_content=prompt_for_sub_answer,
                    enable_cot=True,
                    use_multi_step=False,
                    temperature=temperature
                )
                
                # 保存回答
                research_output["answered_sub_questions"].append({
                    "sub_question": sub_question,
                    "answer": sub_answer_result.get("final_answer", ""),
                    "cot_steps": sub_answer_result.get("cot_steps", ""),
                    "sources": [node.metadata.get("source", "N/A") for node in retrieved_nodes]
                })
            
            logger.info("所有子问题已处理")
            
            # === 阶段5: 报告合成 ===
            logger.info("阶段5: 报告合成...")
            
            # 构建综合上下文
            synthesis_context = f"主研究主题: \"{main_topic}\"\n\n"
            synthesis_context += "基于子问题收集的信息:\n\n"
            
            for item in research_output["answered_sub_questions"]:
                synthesis_context += f"子问题: {item['sub_question']}\n"
                synthesis_context += f"回答: {item['answer']}\n"
                
                if item.get("sources"):
                    synthesis_context += f"支持来源: {', '.join(item['sources'][:2])}\n"  # 只显示前2个来源
                
                synthesis_context += "---\n\n"
            
            # 构建报告提示
            report_prompt = (
                f"你是一位AI研究报告撰写专家。基于以下主研究主题和收集的信息，生成一份全面的研究报告。\n\n"
                f"报告应该结构清晰，包含引言、主要发现、详细分析和结论等部分。\n\n"
                f"提供的信息:\n{synthesis_context}"
            )
            
            # 生成最终报告
            final_report_result = await self.cot_manager.acall_with_cot(
                prompt_content=report_prompt,
                enable_cot=True,
                use_multi_step=False,
                temperature=temperature
            )
            
            # 保存最终报告
            research_output["final_report"] = final_report_result.get("final_answer", "")
            research_output["final_report_cot"] = final_report_result.get("cot_steps", "")
            research_output["status"] = "Completed"
            
            logger.info("最终报告已生成")
            
            # 格式化结果用于API响应
            formatted_result = self._format_response_for_api(research_output, show_cot)
            return formatted_result
            
        except Exception as e:
            logger.error(f"执行深度研究时出错: {str(e)}")
            research_output["status"] = "Failed"
            research_output["error_message"] = f"执行深度研究时出错: {str(e)}"
            return research_output
    
    def _format_response_for_api(self, research_output: Dict[str, Any], show_cot: bool) -> Dict[str, Any]:
        """
        将内部研究输出格式化为API响应格式
        
        参数:
            research_output: 内部研究输出
            show_cot: 是否显示CoT
            
        返回:
            格式化的API响应
        """
        # 基本响应结构
        formatted_response = {
            "main_topic": research_output.get("main_topic", ""),
            "status": research_output.get("status", ""),
            "final_answer": research_output.get("final_report", ""),
            "show_cot": show_cot
        }
        
        # 如果出错，添加错误信息
        if research_output.get("error_message"):
            formatted_response["error_message"] = research_output["error_message"]
        
        # 如果启用CoT显示，添加CoT数据
        if show_cot:
            cot_data = {
                "type": "deep_research",
                "planning": research_output.get("planning", {}),
                "sub_questions": research_output.get("answered_sub_questions", []),
                "search_results_summary": research_output.get("search_results_summary", {}),
                "final_report_cot": research_output.get("final_report_cot", "")
            }
            
            formatted_response["cot_data"] = cot_data
        
        return formatted_response

# 获取深度研究服务实例
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
