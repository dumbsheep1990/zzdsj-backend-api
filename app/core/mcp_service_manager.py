"""
MCP服务管理器模块
提供MCP服务的生命周期管理、状态检查和调度功能
"""

import os
import json
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class MCPServiceManager:
    """
    MCP服务管理器
    
    负责管理MCP服务的生命周期，包括部署、启动、停止、重启和状态查询
    """
    
    def __init__(self, deployments_dir: Optional[str] = None):
        """
        初始化MCP服务管理器
        
        参数:
            deployments_dir: 部署配置文件目录，如果不提供则使用默认目录
        """
        self.deployments_dir = deployments_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "data", 
            "deployments"
        )
        os.makedirs(self.deployments_dir, exist_ok=True)
        self.deployments_cache = {}
        self._load_all_deployments()
    
    def _load_all_deployments(self) -> None:
        """加载所有部署配置"""
        try:
            for file_name in os.listdir(self.deployments_dir):
                if file_name.endswith('.json'):
                    deployment_id = file_name.replace('.json', '')
                    file_path = os.path.join(self.deployments_dir, file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.deployments_cache[deployment_id] = json.load(f)
        except Exception as e:
            logger.error(f"加载部署配置失败: {str(e)}")
    
    def list_deployments(self) -> List[Dict[str, Any]]:
        """
        列出所有部署的MCP服务
        
        返回:
            部署列表
        """
        result = []
        for deployment_id, config in self.deployments_cache.items():
            # 获取状态并添加到结果
            status = self.get_deployment_status(deployment_id)
            deployment_info = config.copy()
            deployment_info.update({"status": status})
            result.append(deployment_info)
        return result
    
    def get_deployment(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """
        获取部署配置
        
        参数:
            deployment_id: 部署ID
            
        返回:
            部署配置，如果不存在则返回None
        """
        if deployment_id not in self.deployments_cache:
            # 尝试从文件加载
            file_path = os.path.join(self.deployments_dir, f"{deployment_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.deployments_cache[deployment_id] = json.load(f)
        
        return self.deployments_cache.get(deployment_id)
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        获取部署状态
        
        参数:
            deployment_id: 部署ID
            
        返回:
            状态信息字典
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return {"state": "unknown", "error": "部署不存在"}
        
        container_name = deployment.get("container")
        if not container_name:
            return {"state": "error", "error": "部署配置缺少容器名称"}
        
        try:
            # 检查容器状态
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                check=False
            )
            
            status_output = result.stdout.strip()
            
            if not status_output:
                return {"state": "not_deployed", "message": "容器不存在"}
            elif "Up" in status_output:
                # 容器运行中
                return {"state": "running", "message": status_output}
            elif "Exited" in status_output:
                # 容器已停止
                return {"state": "stopped", "message": status_output}
            else:
                # 其他状态
                return {"state": "unknown", "message": status_output}
                
        except Exception as e:
            logger.error(f"获取容器状态失败: {str(e)}")
            return {"state": "error", "error": str(e)}
    
    async def start_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        启动指定的MCP服务
        
        参数:
            deployment_id: 部署ID
            
        返回:
            操作结果
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return {"status": "error", "message": "部署不存在"}
        
        deploy_dir = deployment.get("deploy_directory")
        if not deploy_dir or not os.path.exists(deploy_dir):
            return {"status": "error", "message": "部署目录不存在"}
        
        container_name = deployment.get("container")
        if not container_name:
            return {"status": "error", "message": "部署配置缺少容器名称"}
        
        try:
            # 检查容器是否已存在
            status = self.get_deployment_status(deployment_id)
            
            if status["state"] == "running":
                return {"status": "success", "message": "服务已经在运行中"}
            
            # 如果容器存在但已停止，则启动它
            if status["state"] == "stopped":
                result = subprocess.run(
                    ["docker", "start", container_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return {"status": "success", "message": f"服务已启动: {result.stdout.strip()}"}
            
            # 否则使用docker-compose启动
            os.chdir(deploy_dir)
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # 更新部署状态
            deployment["status"] = "running"
            deployment["last_started"] = datetime.now().isoformat()
            self._save_deployment(deployment_id, deployment)
            
            return {
                "status": "success", 
                "message": "服务已启动",
                "details": result.stdout.strip()
            }
            
        except Exception as e:
            logger.error(f"启动服务失败: {str(e)}")
            return {"status": "error", "message": f"启动服务失败: {str(e)}"}
    
    async def stop_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        停止指定的MCP服务
        
        参数:
            deployment_id: 部署ID
            
        返回:
            操作结果
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return {"status": "error", "message": "部署不存在"}
        
        deploy_dir = deployment.get("deploy_directory")
        if not deploy_dir or not os.path.exists(deploy_dir):
            return {"status": "error", "message": "部署目录不存在"}
        
        container_name = deployment.get("container")
        if not container_name:
            return {"status": "error", "message": "部署配置缺少容器名称"}
        
        try:
            # 检查容器是否运行中
            status = self.get_deployment_status(deployment_id)
            
            if status["state"] != "running":
                return {"status": "success", "message": "服务已经停止"}
            
            # 停止容器
            result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            # 更新部署状态
            deployment["status"] = "stopped"
            deployment["last_stopped"] = datetime.now().isoformat()
            self._save_deployment(deployment_id, deployment)
            
            return {
                "status": "success", 
                "message": "服务已停止",
                "details": result.stdout.strip()
            }
            
        except Exception as e:
            logger.error(f"停止服务失败: {str(e)}")
            return {"status": "error", "message": f"停止服务失败: {str(e)}"}
    
    async def restart_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        重启指定的MCP服务
        
        参数:
            deployment_id: 部署ID
            
        返回:
            操作结果
        """
        try:
            # 先停止再启动
            stop_result = await self.stop_deployment(deployment_id)
            if stop_result["status"] == "error":
                return stop_result
            
            # 短暂等待确保容器完全停止
            await asyncio.sleep(2)
            
            # 启动服务
            start_result = await self.start_deployment(deployment_id)
            return start_result
            
        except Exception as e:
            logger.error(f"重启服务失败: {str(e)}")
            return {"status": "error", "message": f"重启服务失败: {str(e)}"}
    
    async def delete_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        删除指定的MCP服务
        
        参数:
            deployment_id: 部署ID
            
        返回:
            操作结果
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return {"status": "error", "message": "部署不存在"}
        
        deploy_dir = deployment.get("deploy_directory")
        container_name = deployment.get("container")
        image_name = deployment.get("docker_image")
        
        try:
            # 检查容器是否运行中，如果是则停止它
            status = self.get_deployment_status(deployment_id)
            if status["state"] == "running":
                await self.stop_deployment(deployment_id)
            
            # 删除容器（如果存在）
            if container_name:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    capture_output=True,
                    text=True,
                    check=False  # 不检查返回码，因为容器可能不存在
                )
            
            # 删除镜像（如果存在）
            if image_name:
                subprocess.run(
                    ["docker", "rmi", image_name],
                    capture_output=True,
                    text=True,
                    check=False  # 不检查返回码，因为镜像可能不存在
                )
            
            # 删除部署目录
            if deploy_dir and os.path.exists(deploy_dir):
                # 谨慎删除，确保是部署目录
                if "mcp_deploy_" in deploy_dir:
                    import shutil
                    shutil.rmtree(deploy_dir)
            
            # 删除部署配置
            config_file = os.path.join(self.deployments_dir, f"{deployment_id}.json")
            if os.path.exists(config_file):
                os.remove(config_file)
            
            # 从缓存中移除
            if deployment_id in self.deployments_cache:
                del self.deployments_cache[deployment_id]
            
            return {"status": "success", "message": "部署已完全删除"}
            
        except Exception as e:
            logger.error(f"删除部署失败: {str(e)}")
            return {"status": "error", "message": f"删除部署失败: {str(e)}"}
    
    def _save_deployment(self, deployment_id: str, deployment: Dict[str, Any]) -> None:
        """
        保存部署配置
        
        参数:
            deployment_id: 部署ID
            deployment: 部署配置
        """
        try:
            # 更新缓存
            self.deployments_cache[deployment_id] = deployment
            
            # 保存到文件
            file_path = os.path.join(self.deployments_dir, f"{deployment_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(deployment, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存部署配置失败: {str(e)}")
    
    async def get_deployment_logs(self, deployment_id: str, lines: int = 100) -> Dict[str, Any]:
        """
        获取部署的日志
        
        参数:
            deployment_id: 部署ID
            lines: 获取的日志行数
            
        返回:
            日志内容
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return {"status": "error", "message": "部署不存在"}
        
        container_name = deployment.get("container")
        if not container_name:
            return {"status": "error", "message": "部署配置缺少容器名称"}
        
        try:
            # 检查容器是否存在
            status = self.get_deployment_status(deployment_id)
            if status["state"] == "not_deployed":
                return {"status": "error", "message": "容器不存在"}
            
            # 获取日志
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "status": "success", 
                "message": "获取日志成功",
                "logs": result.stdout
            }
            
        except Exception as e:
            logger.error(f"获取日志失败: {str(e)}")
            return {"status": "error", "message": f"获取日志失败: {str(e)}"}
    
    async def check_deployment_health(self, deployment_id: str) -> Dict[str, Any]:
        """
        检查部署的健康状态
        
        参数:
            deployment_id: 部署ID
            
        返回:
            健康状态
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return {"status": "error", "message": "部署不存在"}
        
        # 获取服务URL
        service_port = deployment.get("service_port")
        if not service_port:
            return {"status": "error", "message": "部署配置缺少服务端口"}
        
        health_url = f"http://localhost:{service_port}/health"
        
        try:
            # 检查容器状态
            status = self.get_deployment_status(deployment_id)
            if status["state"] != "running":
                return {"health": "unavailable", "message": "服务未运行"}
            
            # 发送HTTP请求检查健康状态
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                
                if response.status_code == 200:
                    return {"health": "healthy", "message": "服务运行正常", "details": response.json()}
                else:
                    return {"health": "unhealthy", "message": f"服务返回异常状态码: {response.status_code}"}
                
        except httpx.TimeoutException:
            return {"health": "unhealthy", "message": "服务请求超时"}
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {"health": "unknown", "message": f"健康检查失败: {str(e)}"}
            
    async def get_tool_schema(self, deployment_id: str, tool_name: str) -> Dict[str, Any]:
        """
        获取工具的JSON Schema
        
        参数:
            deployment_id: 部署ID
            tool_name: 工具名称
            
        返回:
            工具的Schema
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"部署不存在: {deployment_id}")
        
        # 获取服务URL
        service_port = deployment.get("service_port")
        if not service_port:
            raise ValueError(f"部署配置缺少服务端口: {deployment_id}")
        
        # 构建API URL
        schema_url = f"http://localhost:{service_port}/api/mcp/tools/{tool_name}"
        
        try:
            # 检查容器状态
            status = self.get_deployment_status(deployment_id)
            if status["state"] != "running":
                raise ValueError(f"服务未运行: {deployment_id}")
            
            # 发送HTTP请求获取Schema
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(schema_url)
                response.raise_for_status()
                
                tool_data = response.json()
                
                # 提取Schema
                if "schema" in tool_data:
                    return tool_data["schema"]
                else:
                    # 如果没有schema字段，尝试构造一个基本schema
                    return {
                        "name": tool_name,
                        "description": tool_data.get("description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"获取工具Schema失败: {str(e)}")
            raise ValueError(f"获取工具Schema失败: HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error(f"获取工具Schema超时: {tool_name}")
            raise ValueError(f"获取工具Schema超时")
        except Exception as e:
            logger.error(f"获取工具Schema出错: {str(e)}")
            raise ValueError(f"获取工具Schema失败: {str(e)}")
    
    async def get_tool_examples(self, deployment_id: str, tool_name: str) -> List[Dict[str, Any]]:
        """
        获取工具的使用示例
        
        参数:
            deployment_id: 部署ID
            tool_name: 工具名称
            
        返回:
            工具的使用示例列表
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"部署不存在: {deployment_id}")
        
        # 获取服务URL
        service_port = deployment.get("service_port")
        if not service_port:
            raise ValueError(f"部署配置缺少服务端口: {deployment_id}")
        
        # 构建API URL
        examples_url = f"http://localhost:{service_port}/api/mcp/tools/{tool_name}/examples"
        
        try:
            # 检查容器状态
            status = self.get_deployment_status(deployment_id)
            if status["state"] != "running":
                raise ValueError(f"服务未运行: {deployment_id}")
            
            # 发送HTTP请求获取示例
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(examples_url)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    # 如果没有示例接口，则生成一个基本示例
                    if e.response.status_code == 404:
                        # 获取工具Schema
                        schema = await self.get_tool_schema(deployment_id, tool_name)
                        
                        # 生成一个基本示例
                        return [
                            {
                                "tool_name": tool_name,
                                "description": "基本示例",
                                "parameters": self._generate_example_parameters(schema),
                                "expected_result": None
                            }
                        ]
                    else:
                        raise
                    
        except httpx.TimeoutException:
            logger.error(f"获取工具示例超时: {tool_name}")
            raise ValueError(f"获取工具示例超时")
        except Exception as e:
            logger.error(f"获取工具示例出错: {str(e)}")
            # 返回空示例列表而不是抛出异常
            return []
    
    def _generate_example_parameters(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据工具Schema生成示例参数
        
        参数:
            schema: 工具Schema
            
        返回:
            示例参数
        """
        example_params = {}
        
        try:
            # 获取参数定义
            props = schema.get("parameters", {}).get("properties", {})
            
            # 为每个参数生成示例值
            for name, prop in props.items():
                prop_type = prop.get("type")
                
                # 使用默认值或示例值
                if "default" in prop:
                    example_params[name] = prop["default"]
                elif "example" in prop:
                    example_params[name] = prop["example"]
                # 否则根据类型生成示例值
                elif prop_type == "string":
                    example_params[name] = f"example_{name}"
                elif prop_type == "integer":
                    example_params[name] = 1
                elif prop_type == "number":
                    example_params[name] = 1.0
                elif prop_type == "boolean":
                    example_params[name] = True
                elif prop_type == "array":
                    example_params[name] = []
                elif prop_type == "object":
                    example_params[name] = {}
            
            return example_params
            
        except Exception as e:
            logger.error(f"生成示例参数出错: {str(e)}")
            return {}
            
# 创建全局实例
_manager_instance = None

def get_mcp_service_manager() -> MCPServiceManager:
    """
    获取MCP服务管理器实例
    
    返回:
        MCPServiceManager实例
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MCPServiceManager()
    return _manager_instance
