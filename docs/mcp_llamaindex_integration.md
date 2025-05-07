# MCP工具与LlamaIndex集成方案

## 1. 背景与目标

当前系统架构中使用了fastmcp作为MCP工具的封装，但在应用层与接口层还需要将MCP作为工具链调用。LlamaIndex框架支持MCP工具的引用（参考[官方文档](https://docs.llamaindex.ai/en/stable/api_reference/tools/mcp/)），本方案旨在将当前的MCP服务端集成到LlamaIndex工具调用链中。

## 2. 当前系统架构分析

### 2.1 现有MCP服务实现

- 系统使用FastMCP库创建MCP服务器实例
- 提供了工具注册、资源注册和第三方MCP集成功能
- 通过REST API暴露MCP服务能力

### 2.2 LlamaIndex架构

- 已实现了基于LlamaIndex的Agent框架，替换了LangChain
- 目前的KnowledgeAgent中使用了QueryEngineTool但尚未集成MCP工具

## 3. 集成方案设计

### 3.1 创建LlamaIndex MCP工具适配器

```python
# app/frameworks/llamaindex/tools.py
from typing import List, Dict, Any, Optional
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.tools.mcp import MCPTool, MCPToolSpec
from app.frameworks.fastmcp.tools import get_tool, list_tools
from app.frameworks.fastmcp.server import get_mcp_server
import logging

logger = logging.getLogger(__name__)

def create_mcp_tool(tool_name: str) -> Optional[MCPTool]:
    """
    将FastMCP工具转换为LlamaIndex MCPTool
    
    参数:
        tool_name: MCP工具名称
        
    返回:
        LlamaIndex MCPTool实例
    """
    try:
        # 获取MCP工具
        tool_data = get_tool(tool_name)
        if not tool_data:
            logger.error(f"未找到MCP工具: {tool_name}")
            return None
        
        # 获取工具schema
        schema = tool_data.get("schema")
        
        # 创建MCP工具规格
        tool_spec = MCPToolSpec(
            name=tool_data["name"],
            description=tool_data["description"],
            parameters=schema["parameters"] if schema else {},
        )
        
        # 创建MCP工具
        mcp_tool = MCPTool(
            spec=tool_spec,
            mcp_server_url="http://localhost:8000/api/mcp/tools"  # 使用本地MCP服务
        )
        
        return mcp_tool
    
    except Exception as e:
        logger.error(f"创建LlamaIndex MCP工具时出错: {str(e)}")
        return None

def get_all_mcp_tools(category: Optional[str] = None, tag: Optional[str] = None) -> List[MCPTool]:
    """
    获取所有MCP工具的LlamaIndex适配
    
    参数:
        category: 可选，按类别筛选
        tag: 可选，按标签筛选
        
    返回:
        LlamaIndex MCPTool列表
    """
    tools = []
    
    # 获取所有MCP工具
    mcp_tools = list_tools(category, tag)
    
    # 转换为LlamaIndex MCPTool
    for tool_data in mcp_tools:
        mcp_tool = create_mcp_tool(tool_data["name"])
        if mcp_tool:
            tools.append(mcp_tool)
    
    return tools
```

### 3.2 扩展现有的Agent类以支持MCP工具

```python
# 修改 app/frameworks/llamaindex/agent.py 添加MCP工具支持

def _initialize_agent(self):
    """初始化LlamaIndex代理"""
    try:
        # 获取查询引擎工具
        tools = self._get_knowledge_tools()
        
        # 添加MCP工具
        from app.frameworks.llamaindex.tools import get_all_mcp_tools
        mcp_tools = get_all_mcp_tools()
        tools.extend(mcp_tools)
        
        # 获取系统消息
        system_prompt = self.settings_data.get("system_prompt", "")
        if not system_prompt:
            system_prompt = f"你是{self.name}，一个知识丰富的助手。"
            if self.description:
                system_prompt += f" {self.description}"
        
        # 创建LLM
        llm = get_llm(model_name=self.model)
        
        # 创建代理
        agent = OpenAIAgent.from_tools(
            tools,
            llm=llm,
            system_prompt=system_prompt,
            verbose=True
        )
        
        return agent
        
    except Exception as e:
        logger.error(f"初始化LlamaIndex代理时出错: {str(e)}")
        raise
```

### 3.3 创建MCP客户端集成服务

```python
# app/frameworks/integration/mcp_integration.py
from typing import List, Dict, Any, Optional
from llama_index.core.tools import BaseTool
from llama_index.tools.mcp import MCPTool
from app.frameworks.fastmcp.server import get_mcp_server
from app.frameworks.fastmcp.integrations import create_mcp_client
from app.frameworks.llamaindex.tools import get_all_mcp_tools

class MCPIntegrationService:
    """MCP集成服务"""
    
    def __init__(self):
        # 确保MCP服务器已启动
        self.mcp_server = get_mcp_server()
    
    def get_tool_by_name(self, tool_name: str) -> Optional[MCPTool]:
        """根据名称获取MCP工具"""
        from app.frameworks.llamaindex.tools import create_mcp_tool
        return create_mcp_tool(tool_name)
    
    def get_all_tools(self, category: Optional[str] = None, tag: Optional[str] = None) -> List[MCPTool]:
        """获取所有MCP工具"""
        return get_all_mcp_tools(category, tag)
    
    def create_external_mcp_tool(self, provider_id: str, tool_name: str) -> Optional[MCPTool]:
        """创建外部MCP工具的LlamaIndex适配"""
        try:
            # 获取MCP客户端
            client = create_mcp_client(provider_id)
            if not client:
                return None
            
            # 获取工具schema
            tool_schema = client.get_tool_schema(tool_name)
            
            # 创建MCP工具规格
            from llama_index.tools.mcp import MCPToolSpec
            tool_spec = MCPToolSpec(
                name=tool_name,
                description=tool_schema.get("description", f"External MCP tool: {tool_name}"),
                parameters=tool_schema.get("parameters", {})
            )
            
            # 创建MCP工具
            mcp_tool = MCPTool(
                spec=tool_spec,
                mcp_server_url=client.api_url
            )
            
            return mcp_tool
            
        except Exception as e:
            import logging
            logging.error(f"创建外部MCP工具时出错: {str(e)}")
            return None
```

### 3.4 在现有API接口中暴露MCP工具集成能力

```python
# 添加到app/api/assistant_qa.py

class AssistantToolConfig(BaseModel):
    """助手工具配置"""
    tool_type: str = Field(..., description="工具类型: mcp, query_engine, function等")
    tool_name: str = Field(..., description="工具名称")
    enabled: bool = True
    settings: Optional[Dict[str, Any]] = None

@router.post("/{assistant_id}/tools", response_model=List[Dict[str, Any]])
async def configure_assistant_tools(
    assistant_id: str,
    tools: List[AssistantToolConfig],
    current_user = Depends(get_current_user)
):
    """配置助手工具"""
    try:
        # 验证助手存在并属于当前用户
        assistant = assistant_qa_service.get_by_id(assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="未找到助手")
        
        # 处理MCP工具
        configured_tools = []
        for tool_config in tools:
            if tool_config.tool_type == "mcp":
                # 获取MCP工具
                from app.frameworks.integration.mcp_integration import MCPIntegrationService
                mcp_service = MCPIntegrationService()
                mcp_tool = mcp_service.get_tool_by_name(tool_config.tool_name)
                
                if mcp_tool:
                    # 存储工具配置
                    tool_data = {
                        "tool_type": "mcp",
                        "tool_name": tool_config.tool_name,
                        "enabled": tool_config.enabled,
                        "settings": tool_config.settings or {}
                    }
                    configured_tools.append(tool_data)
                    
                    # 更新助手工具配置
                    assistant_qa_service.update_tools(assistant_id, configured_tools)
            
            # 其他工具类型处理...
            
        return configured_tools
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置助手工具时出错: {str(e)}")
```

## 4. 实施步骤

1. 创建`app/frameworks/llamaindex/tools.py`，实现MCP工具到LlamaIndex工具的转换
2. 修改`app/frameworks/llamaindex/agent.py`，在Agent初始化时加载MCP工具
3. 创建`app/frameworks/integration/mcp_integration.py`，提供统一的MCP集成服务
4. 更新现有API或添加新API以配置MCP工具
5. 在`requirements.txt`中添加所需依赖（llama-index-tools-mcp）

## 5. 依赖项

需要添加以下依赖：

```
llama-index-tools-mcp>=0.1.0
```

## 6. 优势与挑战

### 6.1 优势

1. **解耦设计**：API层、应用层和工具层解耦，易于维护和扩展
2. **统一接口**：通过LlamaIndex工具接口统一调用MCP服务
3. **灵活配置**：支持按需加载MCP工具，并支持外部MCP服务
4. **可扩展性**：便于未来集成更多类型的工具和服务

### 6.2 挑战

1. **性能考虑**：需确保MCP工具调用的性能满足要求
2. **错误处理**：需要完善的错误处理和重试机制
3. **安全性**：确保MCP工具的安全使用和权限控制

## 7. 后续优化方向

1. 实现更细粒度的工具权限控制
2. 添加工具使用监控和统计功能
3. 优化工具调用的性能和缓存机制
4. 扩展支持更多类型的MCP服务提供商
