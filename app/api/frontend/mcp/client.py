"""
MCP服务和工具API模块
提供自定义MCP服务和第三方MCP工具的REST API接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field

from app.frameworks.fastmcp.server import get_mcp_server, get_server_status, restart_server
from app.frameworks.fastmcp.tools import register_tool, list_tools, get_tool, get_tool_schema
from app.frameworks.fastmcp.resources import register_resource, list_resources, get_resource
from app.frameworks.fastmcp.prompts import register_prompt, list_prompts, get_prompt
from app.frameworks.fastmcp.integrations import (
    get_recommended_providers,
    list_external_mcps,
    get_external_mcp,
    register_external_mcp,
    update_external_mcp,
    unregister_external_mcp,
    get_all_providers,
    get_provider_tools,
    test_tool,
    call_chat_api
)
from app.api.frontend.dependencies import ResponseFormatter, get_current_user, require_permission

router = APIRouter(prefix="/api/frontend/mcp", tags=["MCP服务和工具"])

# ============ 数据模型 ============

class MCPServerStatusResponse(BaseModel):
    """MCP服务器状态响应模型"""
    name: str
    tools_count: int
    resources_count: int
    prompts_count: int
    tools: List[str]
    resources: List[str]
    prompts: List[str]
    is_running: bool


class MCPServerRestartResponse(BaseModel):
    """MCP服务器重启响应模型"""
    status: str
    message: str


class MCPToolRequest(BaseModel):
    """MCP工具请求模型"""
    name: str
    description: Optional[str] = None
    category: str = "general"
    schema: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    code: str = Field(..., description="工具的Python代码")


class MCPToolResponse(BaseModel):
    """MCP工具响应模型"""
    name: str
    description: Optional[str] = None
    category: str
    tags: List[str]
    schema: Optional[Dict[str, Any]] = None


class MCPResourceRequest(BaseModel):
    """MCP资源请求模型"""
    uri: str
    description: Optional[str] = None
    category: str = "general"
    tags: Optional[List[str]] = None
    code: str = Field(..., description="资源的Python代码")


class MCPResourceResponse(BaseModel):
    """MCP资源响应模型"""
    uri: str
    description: Optional[str] = None
    category: str
    tags: List[str]


class MCPPromptRequest(BaseModel):
    """MCP提示请求模型"""
    name: str
    description: Optional[str] = None
    category: str = "general"
    tags: Optional[List[str]] = None
    code: str = Field(..., description="提示的Python代码")


class MCPPromptResponse(BaseModel):
    """MCP提示响应模型"""
    name: str
    description: Optional[str] = None
    category: str
    tags: List[str]


class MCPDeployRequest(BaseModel):
    """MCP部署请求模型"""
    name: str
    description: Optional[str] = None
    tools: List[str]
    resources: List[str]
    prompts: List[str]
    dependencies: List[str] = ["fastmcp"]
    enabled: bool = True


class MCPDeployResponse(BaseModel):
    """MCP部署响应模型"""
    status: str
    message: str
    deployment_id: Optional[str] = None
    deployment_url: Optional[str] = None
    docker_image: Optional[str] = None
    docker_container: Optional[str] = None
    deploy_directory: Optional[str] = None
    service_port: Optional[int] = None
    startup_info: Optional[Dict[str, Any]] = None


# 服务器状态API
@router.get("/server/status", response_model=MCPServerStatusResponse)
async def get_server_status_api():
    """获取MCP服务器状态"""
    status = get_server_status()
    return ResponseFormatter.format_success(status)


# 服务器重启API
@router.post("/server/restart", response_model=MCPServerRestartResponse)
async def restart_server_api(
    current_user = Depends(require_permission("mcp:admin"))
):
    """
    重启MCP服务器
    
    需要MCP管理员权限
    """
    result = restart_server()
    return ResponseFormatter.format_success(result)


# 工具API
@router.get("/tools", response_model=List[MCPToolResponse])
async def list_tools_api(
    category: Optional[str] = None, 
    tag: Optional[str] = None
):
    """
    列出所有MCP工具
    
    - **category**: 可选的类别过滤
    - **tag**: 可选的标签过滤
    """
    tools = list_tools(category, tag)
    return ResponseFormatter.format_success(tools)


@router.get("/tools/{name}", response_model=MCPToolResponse)
async def get_tool_api(name: str):
    """
    获取特定MCP工具详情
    
    - **name**: 工具名称
    """
    tool = get_tool(name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具 {name} 不存在"
        )
    return ResponseFormatter.format_success(tool)


@router.post("/tools", response_model=MCPToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool_api(
    tool_request: MCPToolRequest, 
    background_tasks: BackgroundTasks,
    current_user = Depends(require_permission("mcp:tool:create"))
):
    """
    创建新的MCP工具
    
    需要MCP工具创建权限
    """
    # 检查工具名称
    name = tool_request.name
    if not name or not name.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="工具名称必须是字母数字"
        )
    
    # 检查工具是否已存在
    existing_tool = get_tool(name)
    if existing_tool:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"工具 {name} 已存在"
        )
    
    # 准备工具数据
    tool_data = {
        "name": name,
        "description": tool_request.description,
        "category": tool_request.category,
        "tags": tool_request.tags or [],
        "schema": tool_request.schema,
        "code": tool_request.code
    }
    
    try:
        # 在后台任务中注册工具
        background_tasks.add_task(register_tool, **tool_data)
        
        # 构建响应
        response = {
            "name": name,
            "description": tool_request.description,
            "category": tool_request.category,
            "tags": tool_request.tags or [],
            "schema": tool_request.schema
        }
        
        return ResponseFormatter.format_success(response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工具失败: {str(e)}"
        )


# 资源API
@router.get("/resources", response_model=List[MCPResourceResponse])
async def list_resources_api(
    category: Optional[str] = None, 
    tag: Optional[str] = None
):
    """
    列出所有MCP资源
    
    - **category**: 可选的类别过滤
    - **tag**: 可选的标签过滤
    """
    resources = list_resources(category, tag)
    return ResponseFormatter.format_success(resources)


@router.get("/resources/{uri}", response_model=MCPResourceResponse)
async def get_resource_api(uri: str):
    """
    获取特定MCP资源详情
    
    - **uri**: 资源URI
    """
    resource = get_resource(uri)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"资源 {uri} 不存在"
        )
    return ResponseFormatter.format_success(resource)


@router.post("/resources", response_model=MCPResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_api(
    resource_request: MCPResourceRequest, 
    background_tasks: BackgroundTasks,
    current_user = Depends(require_permission("mcp:resource:create"))
):
    """
    创建新的MCP资源
    
    需要MCP资源创建权限
    """
    # 检查资源URI
    uri = resource_request.uri
    if not uri or not "/" in uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="资源URI必须包含有效路径"
        )
    
    # 检查资源是否已存在
    existing_resource = get_resource(uri)
    if existing_resource:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"资源 {uri} 已存在"
        )
    
    # 准备资源数据
    resource_data = {
        "uri": uri,
        "description": resource_request.description,
        "category": resource_request.category,
        "tags": resource_request.tags or [],
        "code": resource_request.code
    }
    
    try:
        # 在后台任务中注册资源
        background_tasks.add_task(register_resource, **resource_data)
        
        # 构建响应
        response = {
            "uri": uri,
            "description": resource_request.description,
            "category": resource_request.category,
            "tags": resource_request.tags or []
        }
        
        return ResponseFormatter.format_success(response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建资源失败: {str(e)}"
        )


# 提示API
@router.get("/prompts", response_model=List[MCPPromptResponse])
async def list_prompts_api(
    category: Optional[str] = None, 
    tag: Optional[str] = None
):
    """
    列出所有MCP提示
    
    - **category**: 可选的类别过滤
    - **tag**: 可选的标签过滤
    """
    prompts = list_prompts(category, tag)
    return ResponseFormatter.format_success(prompts)


@router.get("/prompts/{name}", response_model=MCPPromptResponse)
async def get_prompt_api(name: str):
    """
    获取特定MCP提示详情
    
    - **name**: 提示名称
    """
    prompt = get_prompt(name)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"提示 {name} 不存在"
        )
    return ResponseFormatter.format_success(prompt)


@router.post("/prompts", response_model=MCPPromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt_api(
    prompt_request: MCPPromptRequest, 
    background_tasks: BackgroundTasks,
    current_user = Depends(require_permission("mcp:prompt:create"))
):
    """
    创建新的MCP提示
    
    需要MCP提示创建权限
    """
    # 检查提示名称
    name = prompt_request.name
    if not name or not name.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="提示名称必须是字母数字"
        )
    
    # 检查提示是否已存在
    existing_prompt = get_prompt(name)
    if existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"提示 {name} 已存在"
        )
    
    # 准备提示数据
    prompt_data = {
        "name": name,
        "description": prompt_request.description,
        "category": prompt_request.category,
        "tags": prompt_request.tags or [],
        "code": prompt_request.code
    }
    
    try:
        # 在后台任务中注册提示
        background_tasks.add_task(register_prompt, **prompt_data)
        
        # 构建响应
        response = {
            "name": name,
            "description": prompt_request.description,
            "category": prompt_request.category,
            "tags": prompt_request.tags or []
        }
        
        return ResponseFormatter.format_success(response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建提示失败: {str(e)}"
        )


# 部署API
@router.post("/deploy", response_model=MCPDeployResponse)
async def deploy_mcp_service_api(
    deploy_request: MCPDeployRequest,
    current_user = Depends(require_permission("mcp:deploy"))
):
    """
    部署MCP服务
    
    将选定的工具、资源和提示部署为独立的MCP服务
    
    需要MCP部署权限
    """
    # 部署实现...
    # 注：此处简化实现，完整实现应包括Docker容器创建、服务启动等逻辑
    
    try:
        # 构建模拟响应
        response = {
            "status": "success",
            "message": f"MCP服务 '{deploy_request.name}' 部署请求已提交",
            "deployment_id": f"mcp-{deploy_request.name.lower()}",
            "deployment_url": f"http://localhost:8000/mcp/{deploy_request.name.lower()}"
        }
        
        return ResponseFormatter.format_success(response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"部署MCP服务失败: {str(e)}"
        )


###############################
# 第三方MCP工具API
###############################

class ExternalMCPProviderResponse(BaseModel):
    """外部MCP提供商响应模型"""
    id: str
    name: str
    description: Optional[str] = None
    provider: str
    api_url: str
    capabilities: List[str]
    requires_auth: bool
    metadata: Optional[Dict[str, Any]] = None


class ExternalMCPProviderRequest(BaseModel):
    """外部MCP提供商请求模型"""
    id: str
    name: str
    provider: str
    api_url: str
    description: Optional[str] = None
    api_key: Optional[str] = None
    auth_type: str = "api_key"
    capabilities: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


class ExternalMCPToolResponse(BaseModel):
    """外部MCP工具响应模型"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    returns: Optional[Dict[str, Any]] = None


class ExternalMCPToolRequest(BaseModel):
    """外部MCP工具请求模型"""
    tool_name: str
    parameters: Dict[str, Any] = {}
    timeout: Optional[float] = None
    context: Optional[Dict[str, Any]] = None


class ExternalMCPToolTestResponse(BaseModel):
    """外部MCP工具测试响应模型"""
    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# 第三方MCP提供商API
@router.get("/providers", response_model=List[ExternalMCPProviderResponse])
async def list_providers_api(capability: Optional[str] = None):
    """
    列出所有第三方MCP提供商
    
    - **capability**: 可选的能力过滤
    """
    providers = list_external_mcps(capability)
    return ResponseFormatter.format_success(providers)


@router.get("/providers/{provider_id}", response_model=ExternalMCPProviderResponse)
async def get_provider_api(provider_id: str):
    """
    获取特定第三方MCP提供商详情
    
    - **provider_id**: 提供商ID
    """
    provider = get_external_mcp(provider_id)
    if not provider:
        # 尝试获取推荐提供商
        recommended = get_recommended_providers()
        for rec in recommended:
            if rec["id"] == provider_id:
                return ResponseFormatter.format_success({
                    **rec,
                    "requires_auth": True
                })
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP提供商 {provider_id} 不存在"
        )
    
    return ResponseFormatter.format_success(provider)


@router.post("/providers", response_model=ExternalMCPProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_api(
    provider_request: ExternalMCPProviderRequest,
    current_user = Depends(require_permission("mcp:provider:create"))
):
    """
    创建新的第三方MCP提供商
    
    需要MCP提供商创建权限
    """
    # 检查提供商ID
    provider_id = provider_request.id
    
    # 检查提供商是否已存在
    existing_provider = get_external_mcp(provider_id)
    if existing_provider:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MCP提供商 {provider_id} 已存在"
        )
    
    try:
        # 注册提供商
        provider = register_external_mcp(provider_request.dict())
        return ResponseFormatter.format_success(provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建MCP提供商失败: {str(e)}"
        )


@router.delete("/providers/{provider_id}")
async def delete_provider_api(
    provider_id: str,
    current_user = Depends(require_permission("mcp:provider:delete"))
):
    """
    删除第三方MCP提供商
    
    需要MCP提供商删除权限
    """
    # 检查提供商是否存在
    existing_provider = get_external_mcp(provider_id)
    if not existing_provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP提供商 {provider_id} 不存在"
        )
    
    try:
        # 注销提供商
        unregister_external_mcp(provider_id)
        return ResponseFormatter.format_success({
            "status": "success",
            "message": f"MCP提供商 {provider_id} 已删除"
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除MCP提供商失败: {str(e)}"
        )


# 第三方MCP工具API
@router.get("/providers/{provider_id}/tools", response_model=List[ExternalMCPToolResponse])
async def list_provider_tools_api(
    provider_id: str,
    api_key: Optional[str] = None
):
    """
    列出第三方MCP提供商的工具
    
    - **provider_id**: 提供商ID
    - **api_key**: 可选的API密钥
    """
    # 检查提供商是否存在
    provider = get_external_mcp(provider_id)
    if not provider:
        # 检查推荐提供商
        recommended = get_recommended_providers()
        for rec in recommended:
            if rec["id"] == provider_id:
                if not api_key:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"访问 {provider_id} 需要API密钥"
                    )
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP提供商 {provider_id} 不存在"
            )
    
    try:
        # 获取提供商工具
        tools = get_provider_tools(provider_id, api_key)
        return ResponseFormatter.format_success(tools)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP提供商工具失败: {str(e)}"
        )


@router.post("/providers/{provider_id}/tools/{tool_name}/test", response_model=ExternalMCPToolTestResponse)
async def test_provider_tool_api(
    provider_id: str,
    tool_name: str,
    tool_request: ExternalMCPToolRequest,
    api_key: Optional[str] = None
):
    """
    测试第三方MCP提供商的工具
    
    - **provider_id**: 提供商ID
    - **tool_name**: 工具名称
    - **tool_request**: 工具请求参数
    - **api_key**: 可选的API密钥
    """
    # 验证提供商
    provider = get_external_mcp(provider_id)
    if not provider and not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"访问 {provider_id} 需要API密钥"
        )
    
    try:
        # 测试工具
        result = test_tool(
            provider_id, 
            tool_name, 
            tool_request.parameters, 
            api_key, 
            timeout=tool_request.timeout,
            context=tool_request.context
        )
        
        return ResponseFormatter.format_success(result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试工具失败: {str(e)}"
        )


# 聊天API (对于支持聊天能力的第三方MCP)
class ChatMessageRequest(BaseModel):
    """聊天消息请求模型"""
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    stream: bool = False


@router.post("/providers/{provider_id}/chat")
async def chat_with_provider_api(
    provider_id: str,
    chat_request: ChatMessageRequest,
    api_key: Optional[str] = None
):
    """
    与支持聊天能力的第三方MCP提供商聊天
    
    - **provider_id**: 提供商ID
    - **chat_request**: 聊天请求参数
    - **api_key**: 可选的API密钥
    
    如果stream=true，则返回流式响应
    """
    # 验证提供商
    provider = get_external_mcp(provider_id)
    if not provider and not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"访问 {provider_id} 需要API密钥"
        )
    
    # 验证提供商是否支持聊天
    all_providers = get_all_providers()
    provider_info = None
    for p in all_providers:
        if p["id"] == provider_id:
            provider_info = p
            break
    
    if not provider_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP提供商 {provider_id} 不存在"
        )
    
    if "chat" not in provider_info.get("capabilities", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MCP提供商 {provider_id} 不支持聊天功能"
        )
    
    # 准备聊天参数
    chat_params = {
        "messages": chat_request.messages,
        "stream": chat_request.stream
    }
    
    if chat_request.model:
        chat_params["model"] = chat_request.model
    
    if chat_request.temperature is not None:
        chat_params["temperature"] = chat_request.temperature
    
    if chat_request.max_tokens is not None:
        chat_params["max_tokens"] = chat_request.max_tokens
    
    if chat_request.tools:
        chat_params["tools"] = chat_request.tools
    
    try:
        # 调用聊天API
        if chat_request.stream:
            # 流式响应
            async def generate():
                async for chunk in call_chat_api(provider_id, chat_params, api_key):
                    yield f"data: {json.dumps(chunk)}\n\n"
            
            return StreamingResponse(
                generate(), 
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            result = await call_chat_api(provider_id, chat_params, api_key)
            return ResponseFormatter.format_success(result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天请求失败: {str(e)}"
        )
