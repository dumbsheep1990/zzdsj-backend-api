"""
子问题拆分工具

提供两种子问题拆分模式：
1. 基础模式：使用系统提示词引导模型进行step by step拆分
2. 工具模式：使用MCP工具进行更结构化的拆分
"""

from typing import List, Dict, Any, Optional, Union
import logging
import json
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SubQuestion(BaseModel):
    """子问题模型"""
    id: str = Field(..., description="子问题ID")
    content: str = Field(..., description="子问题内容")
    purpose: str = Field(..., description="子问题目的")
    depends_on: List[str] = Field(default_factory=list, description="依赖的其他子问题ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="子问题元数据")
    answer: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)

class DecompositionResult(BaseModel):
    """拆分结果"""
    original_question: str
    subquestions: List[SubQuestion]
    reasoning: str
    execution_order: List[str]

class SubQuestionDecomposer:
    """子问题拆分器"""
    
    def __init__(self, 
                 llm_service=None, 
                 mcp_service=None,
                 mode: str = "basic",
                 max_subquestions: int = 5,
                 structured_output: bool = True,
                 prompts: Dict[str, str] = None):
        """初始化子问题拆分器
        
        Args:
            llm_service: LLM服务实例
            mcp_service: MCP服务实例
            mode: 拆分模式，'basic'或'tool'
            max_subquestions: 最大子问题数量
            structured_output: 是否输出结构化结果
            prompts: 提示词配置
        """
        self.llm_service = llm_service
        self.mcp_service = mcp_service
        self.mode = mode
        self.max_subquestions = max_subquestions
        self.structured_output = structured_output
        
        # 默认提示词配置
        self.default_prompts = {
            "basic_system": """你是一个专业的问题分析专家。你的任务是将复杂问题分解为更小、更容易回答的子问题。
遵循以下步骤：
1. 分析原始问题的复杂性和需求
2. 将问题拆分为2-5个逻辑子问题
3. 确保子问题涵盖原始问题的所有方面
4. 标明子问题之间的依赖关系
5. 提供子问题的执行顺序

对于每个子问题，提供以下信息：
- 子问题ID：简短标识符，如"SQ1"
- 子问题内容：明确的问题表述
- 子问题目的：回答该子问题的目的
- 依赖关系：该子问题依赖哪些其他子问题（如有）

最后，提供解释你的拆分逻辑和推荐的执行顺序。""",
            
            "basic_user": """原始问题：{question}

请将这个问题分解为多个子问题，便于逐步解答。""",
        }
        
        # 使用自定义提示词覆盖默认提示词
        if prompts:
            self.prompts = {**self.default_prompts, **prompts}
        else:
            self.prompts = self.default_prompts
            
    async def decompose(self, question: str) -> DecompositionResult:
        """拆分问题为子问题
        
        Args:
            question: 原始问题
            
        Returns:
            拆分结果
        """
        if self.mode == "basic":
            return await self._basic_decompose(question)
        elif self.mode == "tool":
            return await self._tool_decompose(question)
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
    
    async def _basic_decompose(self, question: str) -> DecompositionResult:
        """基础模式：使用系统提示词引导模型进行拆分
        
        Args:
            question: 原始问题
            
        Returns:
            拆分结果
        """
        try:
            # 准备提示词
            system_prompt = self.prompts["basic_system"]
            user_prompt = self.prompts["basic_user"].format(question=question)
            
            # 调用LLM服务
            response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response["choices"][0]["message"]["content"]
            
            # 如果需要结构化输出，解析LLM响应
            if self.structured_output:
                return self._parse_basic_response(question, content)
            else:
                # 简单解析，创建一个仅包含原始内容的结果
                return DecompositionResult(
                    original_question=question,
                    subquestions=[],
                    reasoning=content,
                    execution_order=[]
                )
                
        except Exception as e:
            logger.error(f"Error in basic decomposition: {str(e)}")
            # 返回一个简单的回退结果
            return DecompositionResult(
                original_question=question,
                subquestions=[
                    SubQuestion(
                        id="SQ1",
                        content=question,
                        purpose="回答原始问题",
                        depends_on=[]
                    )
                ],
                reasoning=f"无法执行子问题拆分: {str(e)}",
                execution_order=["SQ1"]
            )
    
    async def _tool_decompose(self, question: str) -> DecompositionResult:
        """工具模式：使用MCP工具进行拆分
        
        Args:
            question: 原始问题
            
        Returns:
            拆分结果
        """
        try:
            # 调用MCP服务中的sequentialthinking工具
            result = await self.mcp_service.invoke_tool(
                "sequentialthinking",
                {
                    "thoughtNumber": 1,
                    "totalThoughts": 5,
                    "thought": f"我需要将这个问题拆分成多个子问题：\"{question}\"",
                    "nextThoughtNeeded": True
                }
            )
            
            # 继续调用直到完成思考
            thoughts = [result]
            
            while result.get("nextThoughtNeeded", False):
                result = await self.mcp_service.invoke_tool(
                    "sequentialthinking",
                    {
                        "thoughtNumber": len(thoughts) + 1,
                        "totalThoughts": 5,
                        "thought": result.get("nextThought", "继续思考如何拆分这个问题"),
                        "nextThoughtNeeded": True
                    }
                )
                thoughts.append(result)
                
                # 防止无限循环
                if len(thoughts) >= 10:
                    break
            
            # 解析MCP工具的响应
            return self._parse_tool_response(question, thoughts)
            
        except Exception as e:
            logger.error(f"Error in tool decomposition: {str(e)}")
            # 返回一个简单的回退结果
            return DecompositionResult(
                original_question=question,
                subquestions=[
                    SubQuestion(
                        id="SQ1",
                        content=question,
                        purpose="回答原始问题",
                        depends_on=[]
                    )
                ],
                reasoning=f"无法执行子问题拆分: {str(e)}",
                execution_order=["SQ1"]
            )
    
    def _parse_basic_response(self, original_question: str, content: str) -> DecompositionResult:
        """解析基础模式的LLM响应
        
        Args:
            original_question: 原始问题
            content: LLM响应内容
            
        Returns:
            结构化的拆分结果
        """
        try:
            # 尝试直接将内容解析为JSON
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "subquestions" in data:
                    subquestions = []
                    for sq in data["subquestions"]:
                        subquestions.append(SubQuestion(**sq))
                    
                    return DecompositionResult(
                        original_question=original_question,
                        subquestions=subquestions,
                        reasoning=data.get("reasoning", ""),
                        execution_order=data.get("execution_order", [sq.id for sq in subquestions])
                    )
            except (json.JSONDecodeError, TypeError):
                pass
                
            # 手动解析文本内容
            subquestions = []
            reasoning = ""
            execution_order = []
            
            # 查找子问题部分
            lines = content.split('\n')
            current_sq = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否是子问题ID行
                if line.startswith("子问题ID") or line.startswith("SQ") or ":" in line and ("问题" in line.split(":")[0] or "ID" in line.split(":")[0]):
                    # 保存之前的子问题
                    if current_sq:
                        subquestions.append(current_sq)
                    
                    # 创建新的子问题
                    parts = line.split(":", 1)
                    sq_id = parts[1].strip() if len(parts) > 1 else f"SQ{len(subquestions) + 1}"
                    current_sq = {
                        "id": sq_id,
                        "content": "",
                        "purpose": "",
                        "depends_on": []
                    }
                
                # 内容行
                elif current_sq and (line.startswith("子问题内容") or line.startswith("内容") or "内容" in line):
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        current_sq["content"] = parts[1].strip()
                
                # 目的行
                elif current_sq and (line.startswith("子问题目的") or line.startswith("目的") or "目的" in line):
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        current_sq["purpose"] = parts[1].strip()
                
                # 依赖行
                elif current_sq and (line.startswith("依赖") or "依赖" in line):
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        deps = parts[1].strip()
                        if deps and deps.lower() not in ["无", "none", "无依赖"]:
                            current_sq["depends_on"] = [d.strip() for d in deps.split(",")]
                
                # 执行顺序
                elif "执行顺序" in line or "顺序" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        order_text = parts[1].strip()
                        # 提取所有可能的SQ标识符
                        import re
                        execution_order = re.findall(r'SQ\d+|子问题\d+', order_text)
                        if not execution_order:
                            # 尝试按逗号分隔
                            execution_order = [o.strip() for o in order_text.split(",")]
                
                # 推理解释部分
                elif "解释" in line or "逻辑" in line or "推理" in line:
                    reasoning_start = lines.index(line)
                    reasoning = "\n".join(lines[reasoning_start:]).strip()
                    break
            
            # 添加最后一个子问题
            if current_sq:
                subquestions.append(current_sq)
                
            # 如果没有找到执行顺序，使用子问题的顺序
            if not execution_order:
                execution_order = [sq["id"] for sq in subquestions]
                
            # 转换为Pydantic模型
            pydantic_subquestions = []
            for sq in subquestions:
                # 确保至少有内容
                if not sq.get("content"):
                    sq["content"] = f"关于{original_question}的子问题"
                
                # 确保至少有目的
                if not sq.get("purpose"):
                    sq["purpose"] = "帮助回答原始问题"
                    
                pydantic_subquestions.append(SubQuestion(**sq))
                
            return DecompositionResult(
                original_question=original_question,
                subquestions=pydantic_subquestions,
                reasoning=reasoning,
                execution_order=execution_order
            )
                
        except Exception as e:
            logger.error(f"Error parsing basic response: {str(e)}")
            # 创建一个简单的回退结果
            return DecompositionResult(
                original_question=original_question,
                subquestions=[
                    SubQuestion(
                        id="SQ1",
                        content=original_question,
                        purpose="回答原始问题",
                        depends_on=[]
                    )
                ],
                reasoning=f"无法解析子问题拆分结果: {str(e)}",
                execution_order=["SQ1"]
            )
            
    def _parse_tool_response(self, original_question: str, thoughts: List[Dict[str, Any]]) -> DecompositionResult:
        """解析工具模式的MCP响应
        
        Args:
            original_question: 原始问题
            thoughts: MCP思考步骤列表
            
        Returns:
            结构化的拆分结果
        """
        try:
            # 合并所有思考步骤，形成一个完整的推理过程
            reasoning = "\n".join([t.get("thought", "") for t in thoughts])
            
            # 查找最后一个思考步骤中的子问题
            subquestions = []
            execution_order = []
            
            # 逐步分析思考内容，提取子问题
            for i, thought in enumerate(thoughts):
                content = thought.get("thought", "")
                
                # 查找子问题定义
                if "子问题" in content and (":" in content or "：" in content):
                    # 通过正则表达式提取子问题
                    import re
                    # 寻找形如"子问题1: 内容"或"SQ1: 内容"的模式
                    sq_matches = re.findall(r'(子问题\s*\d+|SQ\d+)\s*[:：]\s*(.+?)(?=$|\n|(?=子问题\s*\d+|SQ\d+\s*[:：]))', content, re.DOTALL)
                    
                    for sq_id, sq_content in sq_matches:
                        sq_id = sq_id.strip().replace("子问题", "SQ")
                        sq_content = sq_content.strip()
                        
                        # 检查是否已经有这个ID的子问题
                        existing_ids = [sq.id for sq in subquestions]
                        if sq_id not in existing_ids:
                            # 创建新的子问题
                            subquestions.append(SubQuestion(
                                id=sq_id,
                                content=sq_content,
                                purpose=f"回答关于'{sq_content}'的子问题",
                                depends_on=[]
                            ))
                
                # 查找执行顺序
                if "执行顺序" in content or "处理顺序" in content:
                    # 通过正则表达式提取执行顺序
                    import re
                    order_matches = re.findall(r'(子问题\s*\d+|SQ\d+)', content)
                    if order_matches:
                        execution_order = [om.strip().replace("子问题", "SQ") for om in order_matches]
            
            # 如果没有找到执行顺序，使用子问题的顺序
            if not execution_order:
                execution_order = [sq.id for sq in subquestions]
                
            # 如果没有提取到子问题，回退到一个简单的子问题
            if not subquestions:
                subquestions = [
                    SubQuestion(
                        id="SQ1",
                        content=original_question,
                        purpose="回答原始问题",
                        depends_on=[]
                    )
                ]
                execution_order = ["SQ1"]
                
            return DecompositionResult(
                original_question=original_question,
                subquestions=subquestions,
                reasoning=reasoning,
                execution_order=execution_order
            )
                
        except Exception as e:
            logger.error(f"Error parsing tool response: {str(e)}")
            # 创建一个简单的回退结果
            return DecompositionResult(
                original_question=original_question,
                subquestions=[
                    SubQuestion(
                        id="SQ1",
                        content=original_question,
                        purpose="回答原始问题",
                        depends_on=[]
                    )
                ],
                reasoning=f"无法解析子问题拆分结果: {str(e)}",
                execution_order=["SQ1"]
            )
            
    async def answer_subquestions(self, 
                                 decomposition_result: DecompositionResult,
                                 search_service=None,
                                 knowledge_base_ids: List[str] = None) -> DecompositionResult:
        """回答拆分后的子问题
        
        Args:
            decomposition_result: 拆分结果
            search_service: 搜索服务实例
            knowledge_base_ids: 知识库ID列表
            
        Returns:
            带有答案的拆分结果
        """
        if not search_service:
            logger.warning("No search service provided, skipping subquestion answering")
            return decomposition_result
            
        # 按照执行顺序处理子问题
        for sq_id in decomposition_result.execution_order:
            # 查找对应的子问题
            subquestion = next((sq for sq in decomposition_result.subquestions if sq.id == sq_id), None)
            if not subquestion:
                continue
                
            # 检查依赖的子问题是否已回答
            all_deps_answered = True
            deps_answers = []
            
            for dep_id in subquestion.depends_on:
                dep_sq = next((sq for sq in decomposition_result.subquestions if sq.id == dep_id), None)
                if not dep_sq or not dep_sq.answer:
                    all_deps_answered = False
                    break
                deps_answers.append(f"{dep_id}: {dep_sq.answer}")
                
            if not all_deps_answered:
                logger.warning(f"Dependencies for subquestion {sq_id} not all answered, skipping")
                continue
                
            # 准备搜索查询
            query = subquestion.content
            if deps_answers:
                query += "\n上下文信息:\n" + "\n".join(deps_answers)
                
            # 执行搜索
            try:
                search_results = await search_service.search(
                    query=query,
                    knowledge_base_ids=knowledge_base_ids,
                    limit=5
                )
                
                # 保存搜索结果
                subquestion.search_results = search_results
                
                # 生成答案
                context = "\n\n".join([r.get("content", "") for r in search_results])
                answer = await self.llm_service.chat_completion(
                    messages=[
                        {"role": "system", "content": "你是一个专业的问答助手。请基于提供的上下文回答问题。如果上下文中没有相关信息，请说明无法回答。"},
                        {"role": "user", "content": f"问题：{query}\n\n上下文：{context}"}
                    ]
                )
                
                subquestion.answer = answer["choices"][0]["message"]["content"]
                
            except Exception as e:
                logger.error(f"Error answering subquestion {sq_id}: {str(e)}")
                subquestion.answer = f"无法回答此子问题: {str(e)}"
                
        return decomposition_result
        
    async def synthesize_final_answer(self, decomposition_result: DecompositionResult) -> str:
        """合成最终答案
        
        Args:
            decomposition_result: 带有子问题答案的拆分结果
            
        Returns:
            最终答案
        """
        # 准备子问题和答案的摘要
        subquestion_answers = []
        for sq in decomposition_result.subquestions:
            if sq.answer:
                subquestion_answers.append(f"{sq.id} ({sq.content}): {sq.answer}")
            else:
                subquestion_answers.append(f"{sq.id} ({sq.content}): [未回答]")
                
        # 调用LLM合成最终答案
        try:
            response = await self.llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个专业的问答助手。请基于提供的子问题答案合成一个完整、连贯的最终答案。确保最终答案直接回应原始问题，并整合所有相关子问题的信息。"},
                    {"role": "user", "content": f"原始问题：{decomposition_result.original_question}\n\n子问题答案：\n" + "\n\n".join(subquestion_answers)}
                ]
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error synthesizing final answer: {str(e)}")
            # 返回一个简单的回退答案
            return "无法合成最终答案，请查看各子问题的回答。\n\n" + "\n\n".join(subquestion_answers)
