"""
MCP服务和工具API模块
提供自定义MCP服务和第三方MCP工具的REST API接口
[迁移桥接] - 该文件已迁移至 app/api/frontend/mcp/client.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.mcp.client import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/mcp.py，该文件已迁移至app/api/frontend/mcp/client.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)

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
    add_provider_config,
    create_mcp_client
)
from app.api.dependencies import get_current_user

# 创建路由器
router = APIRouter(prefix="/api/mcp", tags=["MCP"])

###############################
# 自定义MCP服务API
###############################

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
    return status

# 服务器重启API
@router.post("/server/restart", response_model=MCPServerRestartResponse)
async def restart_server_api():
    """重启MCP服务器"""
    result = restart_server()
    return result

# 工具API
@router.get("/tools", response_model=List[MCPToolResponse])
async def list_tools_api(category: Optional[str] = None, tag: Optional[str] = None):
    """列出所有MCP工具"""
    tools = list_tools(category, tag)
    return tools

@router.get("/tools/{name}", response_model=MCPToolResponse)
async def get_tool_api(name: str):
    """获取特定MCP工具详情"""
    tool = get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"未找到MCP工具: {name}")
    
    # 获取工具模式
    schema = get_tool_schema(name)
    tool["schema"] = schema
    
    return tool

@router.post("/tools", response_model=MCPToolResponse)
async def create_tool_api(tool_request: MCPToolRequest, background_tasks: BackgroundTasks):
    """创建新的MCP工具"""
    # 保存工具代码到临时文件
    import tempfile
    import os
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="mcp_tool_")
    temp_file = os.path.join(temp_dir, f"{tool_request.name}.py")
    
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(tool_request.code)
    
    try:
        # 动态加载工具代码
        import importlib.util
        import sys
        
        spec = importlib.util.spec_from_file_location(tool_request.name, temp_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[tool_request.name] = module
        spec.loader.exec_module(module)
        
        # 注册工具
        if not hasattr(module, tool_request.name):
            raise HTTPException(status_code=400, detail=f"工具代码中未找到函数: {tool_request.name}")
        
        tool_func = getattr(module, tool_request.name)
        
        # 创建装饰器并注册
        decorator = register_tool(
            name=tool_request.name,
            description=tool_request.description,
            category=tool_request.category,
            schema=tool_request.schema,
            tags=tool_request.tags or []
        )
        
        # 应用装饰器
        decorated_func = decorator(tool_func)
        
        # 获取注册后的工具信息
        tool = get_tool(tool_request.name)
        if not tool:
            raise HTTPException(status_code=500, detail="工具注册失败")
        
        # 获取工具模式
        schema = get_tool_schema(tool_request.name)
        tool["schema"] = schema
        
        # 在后台清理临时文件
        background_tasks.add_task(lambda: os.unlink(temp_file))
        background_tasks.add_task(lambda: os.rmdir(temp_dir))
        
        return tool
        
    except Exception as e:
        # 清理临时文件
        try:
            os.unlink(temp_file)
            os.rmdir(temp_dir)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"创建MCP工具失败: {str(e)}")

# 资源API
@router.get("/resources", response_model=List[MCPResourceResponse])
async def list_resources_api(category: Optional[str] = None, tag: Optional[str] = None):
    """列出所有MCP资源"""
    resources_list = list_resources(category, tag)
    return resources_list

@router.get("/resources/{uri:path}", response_model=MCPResourceResponse)
async def get_resource_api(uri: str):
    """获取特定MCP资源详情"""
    resource = get_resource(uri)
    if not resource:
        raise HTTPException(status_code=404, detail=f"未找到MCP资源: {uri}")
    
    return resource

@router.post("/resources", response_model=MCPResourceResponse)
async def create_resource_api(resource_request: MCPResourceRequest, background_tasks: BackgroundTasks):
    """创建新的MCP资源"""
    # 保存资源代码到临时文件
    import tempfile
    import os
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="mcp_resource_")
    temp_file = os.path.join(temp_dir, f"{resource_request.uri.replace('://', '_').replace('/', '_')}.py")
    
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(resource_request.code)
    
    try:
        # 动态加载资源代码
        import importlib.util
        import sys
        
        module_name = f"mcp_resource_{resource_request.uri.replace('://', '_').replace('/', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, temp_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # 查找资源函数
        resource_func = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and not attr_name.startswith("__"):
                resource_func = attr
                break
        
        if not resource_func:
            raise HTTPException(status_code=400, detail="资源代码中未找到函数")
        
        # 创建装饰器并注册
        decorator = register_resource(
            uri=resource_request.uri,
            description=resource_request.description,
            category=resource_request.category,
            tags=resource_request.tags or []
        )
        
        # 应用装饰器
        decorated_func = decorator(resource_func)
        
        # 获取注册后的资源信息
        resource = get_resource(resource_request.uri)
        if not resource:
            raise HTTPException(status_code=500, detail="资源注册失败")
        
        # 在后台清理临时文件
        background_tasks.add_task(lambda: os.unlink(temp_file))
        background_tasks.add_task(lambda: os.rmdir(temp_dir))
        
        return resource
        
    except Exception as e:
        # 清理临时文件
        try:
            os.unlink(temp_file)
            os.rmdir(temp_dir)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"创建MCP资源失败: {str(e)}")

# 提示API
@router.get("/prompts", response_model=List[MCPPromptResponse])
async def list_prompts_api(category: Optional[str] = None, tag: Optional[str] = None):
    """列出所有MCP提示"""
    prompts_list = list_prompts(category, tag)
    return prompts_list

@router.get("/prompts/{name}", response_model=MCPPromptResponse)
async def get_prompt_api(name: str):
    """获取特定MCP提示详情"""
    prompt = get_prompt(name)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"未找到MCP提示: {name}")
    
    return prompt

@router.post("/prompts", response_model=MCPPromptResponse)
async def create_prompt_api(prompt_request: MCPPromptRequest, background_tasks: BackgroundTasks):
    """创建新的MCP提示"""
    # 保存提示代码到临时文件
    import tempfile
    import os
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="mcp_prompt_")
    temp_file = os.path.join(temp_dir, f"{prompt_request.name}.py")
    
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(prompt_request.code)
    
    try:
        # 动态加载提示代码
        import importlib.util
        import sys
        
        spec = importlib.util.spec_from_file_location(prompt_request.name, temp_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[prompt_request.name] = module
        spec.loader.exec_module(module)
        
        # 注册提示
        if not hasattr(module, prompt_request.name):
            raise HTTPException(status_code=400, detail=f"提示代码中未找到函数: {prompt_request.name}")
        
        prompt_func = getattr(module, prompt_request.name)
        
        # 创建装饰器并注册
        decorator = register_prompt(
            name=prompt_request.name,
            description=prompt_request.description,
            category=prompt_request.category,
            tags=prompt_request.tags or []
        )
        
        # 应用装饰器
        decorated_func = decorator(prompt_func)
        
        # 获取注册后的提示信息
        prompt = get_prompt(prompt_request.name)
        if not prompt:
            raise HTTPException(status_code=500, detail="提示注册失败")
        
        # 在后台清理临时文件
        background_tasks.add_task(lambda: os.unlink(temp_file))
        background_tasks.add_task(lambda: os.rmdir(temp_dir))
        
        return prompt
        
    except Exception as e:
        # 清理临时文件
        try:
            os.unlink(temp_file)
            os.rmdir(temp_dir)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"创建MCP提示失败: {str(e)}")

# 部署API
@router.post("/deploy", response_model=MCPDeployResponse)
async def deploy_mcp_service_api(deploy_request: MCPDeployRequest):
    """部署MCP服务"""
    try:
        # 准备服务器
        server = get_mcp_server()
        
        # 检查工具是否存在
        for tool_name in deploy_request.tools:
            try:
                if not get_tool(tool_name):
                    raise HTTPException(status_code=404, detail=f"未找到MCP工具: {tool_name}")
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"检查工具时出错: {str(e)}")
        
        # 检查资源是否存在
        for resource_uri in deploy_request.resources:
            try:
                if not get_resource(resource_uri):
                    raise HTTPException(status_code=404, detail=f"未找到MCP资源: {resource_uri}")
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"检查资源时出错: {str(e)}")
        
        # 检查提示是否存在
        for prompt_name in deploy_request.prompts:
            try:
                if not get_prompt(prompt_name):
                    raise HTTPException(status_code=404, detail=f"未找到MCP提示: {prompt_name}")
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"检查提示时出错: {str(e)}")
        
        # 执行部署逻辑
        import uuid
        import os
        import tempfile
        import shutil
        import json
        import subprocess
        import random
        from datetime import datetime
        
        # 创建部署ID
        deployment_id = str(uuid.uuid4())
        
        # 生成随机端口（避开常用端口）
        service_port = random.randint(10000, 65000)
        
        # 创建部署目录
        deploy_dir = os.path.join(tempfile.gettempdir(), f"mcp_deploy_{deployment_id}")
        os.makedirs(deploy_dir, exist_ok=True)
        
        # 创建服务器文件
        server_file = os.path.join(deploy_dir, "server.py")
        with open(server_file, "w", encoding="utf-8") as f:
            f.write(f"""from fastmcp import FastMCP
import logging
import importlib
import traceback
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_server.log')
    ]
)
logger = logging.getLogger(__name__)

# 创建MCP服务器
mcp = FastMCP(
    name="{deploy_request.name}",
    description="{deploy_request.description or ''}",
)

# 加载工具
try:
    from tools import *
    logger.info("已加载MCP工具模块")
except Exception as e:
    logger.error(f"加载工具模块失败: {{str(e)}}")
    logger.error(traceback.format_exc())

# 加载资源
try:
    from resources import *
    logger.info("已加载MCP资源模块")
except Exception as e:
    logger.error(f"加载资源模块失败: {{str(e)}}")
    logger.error(traceback.format_exc())

# 加载提示
try:
    from prompts import *
    logger.info("已加载MCP提示模块")
except Exception as e:
    logger.error(f"加载提示模块失败: {{str(e)}}")
    logger.error(traceback.format_exc())

if __name__ == "__main__":
    # 从环境变量获取端口，如果不存在则使用默认端口
    port = int(os.environ.get("MCP_SERVICE_PORT", {service_port}))
    # 启动服务器
    logger.info(f"启动MCP服务器在端口: {{port}}...")
    mcp.run(host="0.0.0.0", port=port)
""")
        
        # 创建tools.py文件，包含所有工具
        tools_file = os.path.join(deploy_dir, "tools.py")
        with open(tools_file, "w", encoding="utf-8") as f:
            f.write("""from fastmcp import register_tool\n\n""")
            
            # 为每个工具添加代码
            for tool_name in deploy_request.tools:
                tool_data = get_tool(tool_name)
                if not tool_data:
                    continue
                
                # 从工具注册表中提取代码
                # 注意：这里我们需要从工具注册表中获取实际代码
                # 实际实现中，可能需要保存工具源代码的功能
                # 这里使用简化的假代码来模拟
                f.write(f"""
@register_tool(
    name="{tool_name}",
    description="{tool_data.get('description', '')}",
    category="{tool_data.get('category', 'general')}",
    tags={tool_data.get('tags', [])}
)
async def {tool_name}(*args, **kwargs):
    # 工具实现
    # 实际部署时，这里应该是工具的真实代码
    pass
""")
        
        # 创建resources.py文件，包含所有资源
        resources_file = os.path.join(deploy_dir, "resources.py")
        with open(resources_file, "w", encoding="utf-8") as f:
            f.write("""from fastmcp import register_resource\n\n""")
            
            # 为每个资源添加代码
            for resource_uri in deploy_request.resources:
                resource_data = get_resource(resource_uri)
                if not resource_data:
                    continue
                
                # 从资源注册表中提取代码
                f.write(f"""
@register_resource(
    uri="{resource_uri}",
    description="{resource_data.get('description', '')}",
    category="{resource_data.get('category', 'general')}",
    tags={resource_data.get('tags', [])}
)
def resource_{resource_uri.replace('://', '_').replace('/', '_').replace('-', '_')}(*args, **kwargs):
    # 资源实现
    # 实际部署时，这里应该是资源的真实代码
    pass
""")
        
        # 创建prompts.py文件，包含所有提示
        prompts_file = os.path.join(deploy_dir, "prompts.py")
        with open(prompts_file, "w", encoding="utf-8") as f:
            f.write("""from fastmcp import register_prompt\n\n""")
            
            # 为每个提示添加代码
            for prompt_name in deploy_request.prompts:
                prompt_data = get_prompt(prompt_name)
                if not prompt_data:
                    continue
                
                # 从提示注册表中提取代码
                f.write(f"""
@register_prompt(
    name="{prompt_name}",
    description="{prompt_data.get('description', '')}",
    category="{prompt_data.get('category', 'general')}",
    tags={prompt_data.get('tags', [])}
)
def {prompt_name}(*args, **kwargs):
    # 提示实现
    # 实际部署时，这里应该是提示的真实代码
    pass
""")
        
        # 创建README.md
        readme_file = os.path.join(deploy_dir, "README.md")
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(f"""# {deploy_request.name}

{deploy_request.description or ""}

## 工具列表

{", ".join(deploy_request.tools)}

## 资源列表

{", ".join(deploy_request.resources)}

## 提示列表

{", ".join(deploy_request.prompts)}

## 部署信息

- 部署ID: {deployment_id}
- 服务端口: {service_port}
- 创建时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 使用方法

1. 通过Docker部署:
   ```
   docker run -p {service_port}:{service_port} {deploy_request.name.lower().replace(' ', '-')}:{deployment_id[:8]}
   ```

2. API访问:
   ```
   http://localhost:{service_port}/
""")
        
        # 创建requirements.txt
        requirements_file = os.path.join(deploy_dir, "requirements.txt")
        with open(requirements_file, "w", encoding="utf-8") as f:
            # 基础依赖
            f.write("fastmcp>=0.1.0\n")
            f.write("fastapi>=0.95.0\n")
            f.write("uvicorn>=0.20.0\n")
            f.write("httpx>=0.24.0\n")
            f.write("pydantic>=2.0.0\n")
            
            # 添加用户指定的依赖
            for dep in deploy_request.dependencies:
                if dep != "fastmcp":  # 避免重复
                    f.write(f"{dep}\n")
        
        # 创建Dockerfile
        dockerfile = os.path.join(deploy_dir, "Dockerfile")
        with open(dockerfile, "w", encoding="utf-8") as f:
            f.write(f"""FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${{MCP_SERVICE_PORT}}/health || exit 1

# 暴露端口
EXPOSE ${{MCP_SERVICE_PORT}}

# 设置环境变量
ENV MCP_SERVICE_PORT={service_port}

# 启动服务
CMD ["python", "server.py"]
""")
        
        # 创建docker-compose.yml
        docker_compose = os.path.join(deploy_dir, "docker-compose.yml")
        with open(docker_compose, "w", encoding="utf-8") as f:
            f.write(f"""version: '3'

services:
  mcp-service:
    build: .
    image: {deploy_request.name.lower().replace(' ', '-')}:{deployment_id[:8]}
    container_name: mcp-{deployment_id[:8]}
    ports:
      - "{service_port}:{service_port}"
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    environment:
      - MCP_SERVICE_NAME={deploy_request.name}
      - MCP_DEPLOYMENT_ID={deployment_id}
      - MCP_SERVICE_PORT={service_port}
""")
        
        # 创建部署配置文件
        config_file = os.path.join(deploy_dir, "deployment.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({
                "deployment_id": deployment_id,
                "name": deploy_request.name,
                "description": deploy_request.description,
                "tools": deploy_request.tools,
                "resources": deploy_request.resources,
                "prompts": deploy_request.prompts,
                "dependencies": deploy_request.dependencies,
                "enabled": deploy_request.enabled,
                "created_at": datetime.now().isoformat(),
                "status": "pending",
                "image": f"{deploy_request.name.lower().replace(' ', '-')}:{deployment_id[:8]}",
                "container": f"mcp-{deployment_id[:8]}",
                "service_port": service_port
            }, f, indent=2)
        
        # 创建启动脚本
        start_script = os.path.join(deploy_dir, "start.sh")
        with open(start_script, "w", encoding="utf-8") as f:
            f.write(f"""#!/bin/bash
docker-compose up -d
echo "MCP service started. Access at http://localhost:{service_port}"
""")
        
        # 赋予执行权限
        os.chmod(start_script, 0o755)
        
        # 创建停止脚本
        stop_script = os.path.join(deploy_dir, "stop.sh")
        with open(stop_script, "w", encoding="utf-8") as f:
            f.write("""#!/bin/bash
docker-compose down
echo "MCP service stopped"
""")
        
        # 赋予执行权限
        os.chmod(stop_script, 0o755)
        
        # 异步启动构建和部署过程
        # 在实际实现中，这部分应该放入后台任务处理
        # 为了简化示例，这里只创建目录和文件
        
        # 创建部署信息目录
        deployments_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "deployments")
        os.makedirs(deployments_dir, exist_ok=True)
        
        # 复制部署配置
        deployment_config = os.path.join(deployments_dir, f"{deployment_id}.json")
        shutil.copy(config_file, deployment_config)
        
        # 设置部署URL
        # 在实际环境中，应该是动态分配的URL或IP:端口
        deployment_url = f"http://localhost:{service_port}/mcp/{deployment_id}"
        
        # 设置镜像名
        image_name = f"{deploy_request.name.lower().replace(' ', '-')}:{deployment_id[:8]}"
        
        # 返回部署信息
        return {
            "status": "success",
            "message": f"MCP服务 {deploy_request.name} 已成功部署为Docker容器",
            "deployment_id": deployment_id,
            "deployment_url": deployment_url,
            "service_port": service_port,
            "docker_image": image_name,
            "docker_container": f"mcp-{deployment_id[:8]}",
            "deploy_directory": deploy_dir,
            "startup_info": {
                "access_url": f"http://localhost:{service_port}",
                "api_docs": f"http://localhost:{service_port}/docs",
                "health_endpoint": f"http://localhost:{service_port}/health",
                "docker_run_command": f"docker run -p {service_port}:{service_port} {image_name}",
                "docker_compose_command": "docker-compose up -d",
                "startup_script": "bash start.sh",
                "shutdown_script": "bash stop.sh"
            }
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"部署MCP服务失败: {str(e)}")

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
    """列出所有第三方MCP提供商"""
    providers = get_recommended_providers(capability)
    return providers

@router.get("/providers/{provider_id}", response_model=ExternalMCPProviderResponse)
async def get_provider_api(provider_id: str):
    """获取特定第三方MCP提供商详情"""
    provider = get_external_mcp(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"未找到MCP提供商: {provider_id}")
    
    return {
        "id": provider.id,
        "name": provider.name,
        "description": provider.description,
        "provider": provider.provider,
        "api_url": provider.api_url,
        "capabilities": provider.capabilities,
        "requires_auth": provider.auth_type != "none",
        "metadata": provider.metadata
    }

@router.post("/providers", response_model=ExternalMCPProviderResponse)
async def create_provider_api(provider_request: ExternalMCPProviderRequest):
    """创建新的第三方MCP提供商"""
    try:
        # 注册提供商
        provider = register_external_mcp(
            id=provider_request.id,
            name=provider_request.name,
            provider=provider_request.provider,
            api_url=provider_request.api_url,
            description=provider_request.description,
            api_key=provider_request.api_key,
            auth_type=provider_request.auth_type,
            capabilities=provider_request.capabilities,
            metadata=provider_request.metadata
        )
        
        # 持久化配置
        add_provider_config(
            provider_id=provider_request.id,
            name=provider_request.name,
            provider=provider_request.provider,
            api_url=provider_request.api_url,
            description=provider_request.description,
            capabilities=provider_request.capabilities,
            metadata=provider_request.metadata
        )
        
        return {
            "id": provider.id,
            "name": provider.name,
            "description": provider.description,
            "provider": provider.provider,
            "api_url": provider.api_url,
            "capabilities": provider.capabilities,
            "requires_auth": provider.auth_type != "none",
            "metadata": provider.metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建MCP提供商失败: {str(e)}")

@router.delete("/providers/{provider_id}", response_model=Dict[str, str])
async def delete_provider_api(provider_id: str):
    """删除第三方MCP提供商"""
    success = unregister_external_mcp(provider_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"未找到MCP提供商: {provider_id}")
    
    return {"status": "success", "message": f"已删除MCP提供商: {provider_id}"}

# 第三方MCP工具API
@router.get("/providers/{provider_id}/tools", response_model=List[ExternalMCPToolResponse])
async def list_provider_tools_api(provider_id: str, api_key: Optional[str] = None):
    """列出第三方MCP提供商的工具"""
    try:
        # 创建客户端
        client = await create_mcp_client(provider_id, api_key)
        
        # 获取工具列表
        tools = await client.get_tools()
        
        # 格式化响应
        result = []
        for tool in tools:
            result.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
                "returns": tool.get("returns")
            })
        
        # 关闭客户端
        await client.close()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取MCP工具列表失败: {str(e)}")

@router.post("/providers/{provider_id}/tools/{tool_name}/test", response_model=ExternalMCPToolTestResponse)
async def test_provider_tool_api(
    provider_id: str,
    tool_name: str,
    tool_request: ExternalMCPToolRequest,
    api_key: Optional[str] = None
):
    """测试第三方MCP提供商的工具"""
    try:
        # 创建客户端
        client = await create_mcp_client(provider_id, api_key)
        
        # 调用工具
        response = await client.call_tool(
            tool_name=tool_request.tool_name or tool_name,
            parameters=tool_request.parameters,
            timeout=tool_request.timeout,
            context=tool_request.context
        )
        
        # 关闭客户端
        await client.close()
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试MCP工具失败: {str(e)}")

# 聊天API (对于支持聊天能力的第三方MCP)
class ChatMessageRequest(BaseModel):
    """聊天消息请求模型"""
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    stream: bool = False

@router.post("/providers/{provider_id}/chat", response_model=Dict[str, Any])
async def chat_with_provider_api(
    provider_id: str,
    chat_request: ChatMessageRequest,
    api_key: Optional[str] = None
):
    """与支持聊天能力的第三方MCP提供商聊天"""
    try:
        # 创建聊天客户端
        from app.frameworks.fastmcp.integrations import create_chat_client
        client = await create_chat_client(provider_id, api_key)
        
        # 发送消息
        if chat_request.stream:
            # FastAPI不直接支持返回异步迭代器，需要用StreamingResponse
            from fastapi.responses import StreamingResponse
            import json
            
            async def stream_generator():
                async for chunk in client.stream_message(
                    messages=chat_request.messages,
                    model=chat_request.model,
                    temperature=chat_request.temperature,
                    max_tokens=chat_request.max_tokens,
                    tools=chat_request.tools
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # 发送结束信号
                yield "data: [DONE]\n\n"
                
                # 关闭客户端
                await client.close()
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            response = await client.send_message(
                messages=chat_request.messages,
                model=chat_request.model,
                temperature=chat_request.temperature,
                max_tokens=chat_request.max_tokens,
                tools=chat_request.tools
            )
            
            # 关闭客户端
            await client.close()
            
            return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天请求失败: {str(e)}")
