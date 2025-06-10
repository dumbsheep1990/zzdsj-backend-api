# ZZDSJ Agno Agent使用示例
from agno import Agent
from .toolkit import ZZDSJAgnoToolkit

class ZZDSJAgnoAgent:
    """集成所有工具的ZZDSJ Agno Agent"""
    
    def __init__(self, model: str = "gpt-4"):
        # 创建包含所有工具的Agent
        self.agent = Agent(
            name="ZZDSJ Assistant",
            model=model,
            tools=ZZDSJAgnoToolkit(),  # 使用统一工具包
            show_tool_calls=True,
            markdown=True
        )
    
    async def run_query(self, query: str) -> str:
        """运行查询"""
        return await self.agent.run(query)
    
    async def run_with_context(self, query: str, context: dict) -> str:
        """带上下文运行"""
        return await self.agent.run(query, **context)

# 使用示例
async def example_usage():
    """使用示例函数"""
    # 创建Agent
    agent = ZZDSJAgnoAgent()
    
    # 知识查询 - 自动使用KnowledgeTools
    response1 = await agent.run_query("搜索人工智能相关的政策文档")
    print("知识查询结果:", response1)
    
    # 推理分析 - 自动使用ReasoningTools
    response2 = await agent.run_query("分析这些政策对AI发展的影响")
    print("推理分析结果:", response2)
    
    # 思考规划 - 自动使用ThinkingTools  
    response3 = await agent.run_query("制定AI政策实施的具体方案")
    print("思考规划结果:", response3)
    
    # 自定义工具 - 使用PolicySearchTool
    response4 = await agent.run_query("使用政策搜索器查找最新的AI监管政策")
    print("政策搜索结果:", response4)

if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage()) 