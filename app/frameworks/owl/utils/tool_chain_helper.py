from typing import Any, Dict, List, Optional, Tuple
import json

from app.frameworks.owl.utils.tool_orchestrator import ToolOrchestrator

class ToolChainHelper:
    """工具链助手，帮助用户以自然语言方式创建和配置工具链"""
    
    def __init__(self, toolkit_manager: Any = None):
        """初始化工具链助手
        
        Args:
            toolkit_manager: 工具包管理器实例
        """
        self.toolkit_manager = toolkit_manager
        self.orchestrator = ToolOrchestrator()
        self.available_tools = {}
        self.workflows = {}
        
    async def initialize(self) -> None:
        """初始化助手，加载所有可用工具"""
        if self.toolkit_manager:
            tools = await self.toolkit_manager.get_tools()
            for tool in tools:
                if hasattr(tool, 'name') and hasattr(tool, 'description'):
                    self.available_tools[tool.name] = {
                        "instance": tool,
                        "description": tool.description
                    }
                    # 注册到编排器
                    self.orchestrator.register_tool(tool.name, tool, tool.description)
        
    async def parse_natural_language_workflow(self, description: str) -> Dict[str, Any]:
        """从自然语言描述中解析工作流定义
        
        Args:
            description: 工作流的自然语言描述
            
        Returns:
            Dict[str, Any]: 结构化的工作流定义
        """
        # 在实际实现中，这里会调用LLM来解析自然语言
        # 框架搭建阶段，我们使用模拟实现
        
        # 构建简单的默认工作流
        workflow = {
            "name": "自然语言生成的工作流",
            "description": description,
            "steps": []
        }
        
        # 根据描述中的关键词添加步骤
        if "搜索" in description or "查询" in description:
            workflow["steps"].append({
                "name": "搜索信息",
                "tool": "web_search" if "web_search" in self.available_tools else None,
                "input": {"query": "${query}"},
                "output": {"search_results": "$result"}
            })
            
        if "文档" in description or "处理文件" in description:
            workflow["steps"].append({
                "name": "处理文档",
                "tool": "process_document" if "process_document" in self.available_tools else None,
                "input": {"file_path": "${file_path}"},
                "output": {"document_content": "$result"}
            })
            
        if "分析" in description or "总结" in description:
            workflow["steps"].append({
                "name": "分析内容",
                "tool": "analyze_content" if "analyze_content" in self.available_tools else None,
                "input": {"content": "${content or search_results or document_content}"},
                "output": {"analysis": "$result"}
            })
            
        # 添加默认的结果汇总步骤
        workflow["steps"].append({
            "name": "汇总结果",
            "tool": "summarize" if "summarize" in self.available_tools else None,
            "input": {"content": "${analysis or search_results or document_content or content}"},
            "output": {"result": "$result"}
        })
        
        return workflow
    
    async def create_workflow_from_description(self, name: str, description: str) -> str:
        """从自然语言描述创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            
        Returns:
            str: 工作流创建结果
        """
        # 解析描述
        workflow = await self.parse_natural_language_workflow(description)
        
        # 添加名称
        workflow["name"] = name
        
        # 注册工作流
        self.workflows[name] = workflow
        self.orchestrator.register_workflow(name, workflow)
        
        # 返回工作流预览
        return json.dumps(workflow, ensure_ascii=False, indent=2)
    
    async def execute_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流
        
        Args:
            workflow_name: 工作流名称
            inputs: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        if workflow_name not in self.workflows:
            raise ValueError(f"工作流 '{workflow_name}' 不存在")
            
        # 设置当前工作流
        self.orchestrator.set_current_workflow(workflow_name)
        
        # 执行工作流
        return await self.orchestrator.execute_workflow(inputs)
    
    def get_tools_description(self) -> str:
        """获取所有可用工具的描述
        
        Returns:
            str: 工具描述列表
        """
        descriptions = []
        for name, tool_info in self.available_tools.items():
            descriptions.append(f"- {name}: {tool_info['description']}")
            
        return "\n".join(descriptions)
    
    def preview_workflows(self) -> str:
        """预览所有已创建的工作流
        
        Returns:
            str: 工作流预览
        """
        if not self.workflows:
            return "尚未创建任何工作流"
            
        previews = []
        for name, workflow in self.workflows.items():
            steps = [f"  {i+1}. {step.get('name', f'步骤{i+1}')} (使用工具: {step.get('tool', '无')})" 
                    for i, step in enumerate(workflow.get("steps", []))]
            
            preview = f"工作流: {name}\n"
            preview += f"描述: {workflow.get('description', '无')}\n"
            preview += "步骤:\n" + "\n".join(steps)
            previews.append(preview)
            
        return "\n\n".join(previews)
