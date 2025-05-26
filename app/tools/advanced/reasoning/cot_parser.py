"""
思维链(Chain of Thought)解析器模块
提供CoT解析功能，支持不同的模型输出格式
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union
from llama_index.core.output_parsers import OutputParserException
from llama_index.core.output_parsers.base import BaseOutputParser, StructuredOutput

logger = logging.getLogger(__name__)

class InducedCoTParser(BaseOutputParser):
    """
    诱导式思维链(CoT)解析器
    用于解析LLM输出中的思维过程和最终答案，支持自定义标签
    """
    
    def __init__(
        self,
        cot_start_tag: str = "<THINK>",
        cot_end_tag: str = "</THINK>",
        answer_start_tag: str = "<ANSWER>",
        answer_end_tag: str = "</ANSWER>"
    ):
        """
        初始化CoT解析器
        
        参数:
            cot_start_tag: 思维链开始标签
            cot_end_tag: 思维链结束标签
            answer_start_tag: 最终答案开始标签
            answer_end_tag: 最终答案结束标签
        """
        self.cot_start_tag = cot_start_tag
        self.cot_end_tag = cot_end_tag
        self.answer_start_tag = answer_start_tag
        self.answer_end_tag = answer_end_tag
    
    def format(self) -> str:
        """
        返回LLM需要使用的输出格式说明
        
        返回:
            格式化指令字符串
        """
        return (
            f"请先在{self.cot_start_tag}和{self.cot_end_tag}标签内详细阐述您的思考过程。\n"
            f"然后，在{self.answer_start_tag}和{self.answer_end_tag}标签内提供您的最终答案。\n"
            f"如果查询简单且不需要详细思考，您可以提供简短的思考或直接使用答案标签。"
        )
    
    def parse(self, output: str) -> Dict[str, str]:
        """
        解析LLM输出，提取思维链和最终答案
        
        参数:
            output: LLM原始输出文本
            
        返回:
            包含cot_steps和final_answer的字典
        """
        try:
            # 提取思维链部分
            cot_pattern = f"{re.escape(self.cot_start_tag)}(.*?){re.escape(self.cot_end_tag)}"
            cot_matches = re.findall(cot_pattern, output, re.DOTALL)
            cot_steps = cot_matches[0].strip() if cot_matches else ""
            
            # 提取最终答案部分
            answer_pattern = f"{re.escape(self.answer_start_tag)}(.*?){re.escape(self.answer_end_tag)}"
            answer_matches = re.findall(answer_pattern, output, re.DOTALL)
            final_answer = answer_matches[0].strip() if answer_matches else ""
            
            # 如果没有找到标签匹配，检查是否是纯文本响应
            if not cot_steps and not final_answer:
                final_answer = output.strip()
            
            # 返回解析结果
            return {
                "cot_steps": cot_steps,
                "final_answer": final_answer
            }
            
        except Exception as e:
            logger.error(f"解析CoT输出时出错: {str(e)}")
            # 出错时将原始输出作为最终答案返回
            return {
                "cot_steps": "",
                "final_answer": output.strip()
            }
    
    def parse_with_prompt(self, output: str) -> StructuredOutput:
        """
        实现BaseOutputParser接口需要的方法
        
        参数:
            output: LLM原始输出文本
            
        返回:
            结构化输出对象
        """
        parsed = self.parse(output)
        return StructuredOutput(
            raw_output=output,
            parsed_output=parsed
        )

class MultiStepCoTParser(BaseOutputParser):
    """
    多步骤思维链解析器
    用于解析包含多个步骤的复杂思维过程，每个步骤都可能包含思考和结论
    支持Deep Research等多阶段推理任务
    """
    
    def __init__(
        self,
        step_pattern: str = r"步骤 (\d+)[：:](.*?)(?=步骤 \d+[：:]|$)",
        thought_pattern: str = r"思考[：:](.*?)(?=结论[：:]|$)",
        conclusion_pattern: str = r"结论[：:](.*?)$"
    ):
        """
        初始化多步骤CoT解析器
        
        参数:
            step_pattern: 匹配步骤的正则表达式
            thought_pattern: 匹配每个步骤中思考部分的正则表达式
            conclusion_pattern: 匹配每个步骤中结论部分的正则表达式
        """
        self.step_pattern = step_pattern
        self.thought_pattern = thought_pattern
        self.conclusion_pattern = conclusion_pattern
    
    def format(self) -> str:
        """
        返回LLM需要使用的输出格式说明
        
        返回:
            格式化指令字符串
        """
        return (
            "请按照以下格式组织您的推理过程:\n\n"
            "步骤 1: [步骤描述]\n"
            "思考: [详细的思考过程]\n"
            "结论: [该步骤的结论]\n\n"
            "步骤 2: [步骤描述]\n"
            "思考: [详细的思考过程]\n"
            "结论: [该步骤的结论]\n\n"
            "... (如有必要可继续添加步骤)\n\n"
            "最终答案: [基于上述步骤得出的最终结论]"
        )
    
    def parse(self, output: str) -> Dict[str, Any]:
        """
        解析多步骤思维过程
        
        参数:
            output: LLM原始输出文本
            
        返回:
            包含steps和final_answer的字典
        """
        try:
            # 提取最终答案
            final_answer_match = re.search(r"最终答案[：:](.*?)$", output, re.DOTALL)
            final_answer = final_answer_match.group(1).strip() if final_answer_match else ""
            
            # 如果没有找到最终答案，尝试使用最后一个结论作为最终答案
            if not final_answer:
                last_conclusion_match = re.search(r"结论[：:](.*?)$", output, re.DOTALL)
                final_answer = last_conclusion_match.group(1).strip() if last_conclusion_match else ""
            
            # 提取所有步骤
            steps = []
            step_matches = re.findall(self.step_pattern, output, re.DOTALL)
            
            for step_num, step_content in step_matches:
                # 从步骤内容中提取思考和结论
                thought_match = re.search(self.thought_pattern, step_content, re.DOTALL)
                conclusion_match = re.search(self.conclusion_pattern, step_content, re.DOTALL)
                
                thought = thought_match.group(1).strip() if thought_match else ""
                conclusion = conclusion_match.group(1).strip() if conclusion_match else ""
                
                steps.append({
                    "step_number": int(step_num),
                    "thought": thought,
                    "conclusion": conclusion
                })
            
            # 如果没有找到任何步骤和最终答案，则将整个输出作为最终答案
            if not steps and not final_answer:
                final_answer = output.strip()
            
            # 返回解析结果
            return {
                "steps": steps,
                "final_answer": final_answer
            }
            
        except Exception as e:
            logger.error(f"解析多步骤CoT输出时出错: {str(e)}")
            # 出错时将原始输出作为最终答案返回
            return {
                "steps": [],
                "final_answer": output.strip()
            }
    
    def parse_with_prompt(self, output: str) -> StructuredOutput:
        """
        实现BaseOutputParser接口需要的方法
        
        参数:
            output: LLM原始输出文本
            
        返回:
            结构化输出对象
        """
        parsed = self.parse(output)
        return StructuredOutput(
            raw_output=output,
            parsed_output=parsed
        )
