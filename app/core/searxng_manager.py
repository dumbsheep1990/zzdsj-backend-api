"""
SearxNG搜索引擎服务管理器
负责SearxNG服务的部署、启动、停止和健康检查
"""

import os
import json
import aiohttp
import logging
import subprocess
from typing import Dict, List, Any, Optional, Union
import asyncio
from pathlib import Path
import time

from app.config import settings
from app.utils.service_discovery import register_service, deregister_service, send_heartbeat

logger = logging.getLogger(__name__)

class SearxNGManager:
    """SearxNG搜索引擎服务管理器"""
    
    def __init__(self):
        """初始化SearxNG管理器"""
        # Docker配置路径
        self.docker_dir = Path("E:/zz-backend-lite/docker/searxng")
        self.compose_file = self.docker_dir / "docker-compose.yml"
        
        # 服务配置
        self.container_name = "searxng"
        self.host = "localhost"
        self.port = 8888
        self.base_url = f"http://{self.host}:{self.port}"
        self.search_endpoint = f"{self.base_url}/search"
        self.health_endpoint = f"{self.base_url}/healthz"
        
        # Nacos服务注册信息
        self.service_name = "search-engine"
        self.service_id = None
        self.nacos_registered = False
        
        # 服务状态
        self.is_running = False
        self.last_health_check = 0
        self.health_check_interval = 30  # 秒
    
    async def deploy(self) -> bool:
        """
        部署SearxNG服务
        
        返回:
            bool: 部署是否成功
        """
        try:
            logger.info("开始部署SearxNG搜索引擎服务...")
            
            # 检查Docker是否已安装
            docker_check = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if docker_check.returncode != 0:
                logger.error("Docker未安装或不可用")
                return False
            
            # 检查docker-compose文件是否存在
            if not self.compose_file.exists():
                logger.error(f"Docker Compose文件不存在: {self.compose_file}")
                return False
            
            # 启动容器
            os.chdir(self.docker_dir)
            deploy_result = subprocess.run(
                ["docker-compose", "up", "-d"], 
                capture_output=True, 
                text=True
            )
            
            if deploy_result.returncode != 0:
                logger.error(f"SearxNG部署失败: {deploy_result.stderr}")
                return False
            
            logger.info(f"SearxNG部署成功: {deploy_result.stdout}")
            
            # 等待服务启动
            start_time = time.time()
            max_wait_time = 60  # 最多等待60秒
            
            while time.time() - start_time < max_wait_time:
                health_status = await self.check_health()
                if health_status:
                    self.is_running = True
                    logger.info("SearxNG服务已成功启动")
                    
                    # 注册到Nacos
                    await self.register_to_nacos()
                    return True
                
                logger.info("等待SearxNG服务启动...")
                await asyncio.sleep(5)
            
            logger.error(f"SearxNG服务启动超时")
            return False
            
        except Exception as e:
            logger.error(f"部署SearxNG服务时出错: {str(e)}")
            return False
    
    async def stop(self) -> bool:
        """
        停止SearxNG服务
        
        返回:
            bool: 停止是否成功
        """
        try:
            logger.info("停止SearxNG服务...")
            
            # 从Nacos注销
            if self.nacos_registered and self.service_id:
                await self.deregister_from_nacos()
            
            # 停止容器
            os.chdir(self.docker_dir)
            stop_result = subprocess.run(
                ["docker-compose", "down"], 
                capture_output=True, 
                text=True
            )
            
            if stop_result.returncode != 0:
                logger.error(f"停止SearxNG服务失败: {stop_result.stderr}")
                return False
            
            logger.info("SearxNG服务已停止")
            self.is_running = False
            return True
            
        except Exception as e:
            logger.error(f"停止SearxNG服务时出错: {str(e)}")
            return False
    
    async def restart(self) -> bool:
        """
        重启SearxNG服务
        
        返回:
            bool: 重启是否成功
        """
        await self.stop()
        return await self.deploy()
    
    async def check_health(self) -> bool:
        """
        检查SearxNG服务健康状态
        
        返回:
            bool: 服务是否健康
        """
        try:
            current_time = time.time()
            
            # 如果距离上次检查时间不到间隔时间，且已知服务在运行，则直接返回
            if (current_time - self.last_health_check < self.health_check_interval and 
                self.is_running):
                return True
            
            # 执行健康检查
            async with aiohttp.ClientSession() as session:
                async with session.get(self.health_endpoint, timeout=5) as response:
                    self.last_health_check = current_time
                    if response.status == 200:
                        self.is_running = True
                        return True
                    else:
                        self.is_running = False
                        logger.warning(f"SearxNG服务健康检查失败，HTTP状态码: {response.status}")
                        return False
                        
        except Exception as e:
            self.is_running = False
            logger.warning(f"SearxNG服务健康检查出错: {str(e)}")
            return False
    
    async def register_to_nacos(self) -> bool:
        """
        注册SearxNG服务到Nacos
        
        返回:
            bool: 注册是否成功
        """
        try:
            logger.info("将SearxNG服务注册到Nacos...")
            
            # 注册服务
            self.service_id = await register_service(
                service_name=self.service_name,
                ip=self.host,
                port=self.port,
                metadata={
                    "type": "search-engine",
                    "api_endpoint": "/search",
                    "health_endpoint": "/healthz",
                    "description": "SearxNG元搜索引擎"
                }
            )
            
            if self.service_id:
                self.nacos_registered = True
                logger.info(f"SearxNG服务成功注册到Nacos，服务ID: {self.service_id}")
                return True
            else:
                logger.error("SearxNG服务注册到Nacos失败")
                return False
                
        except Exception as e:
            logger.error(f"注册SearxNG服务到Nacos时出错: {str(e)}")
            return False
    
    async def deregister_from_nacos(self) -> bool:
        """
        从Nacos注销SearxNG服务
        
        返回:
            bool: 注销是否成功
        """
        try:
            if not self.service_id:
                logger.warning("无法注销SearxNG服务，服务ID不存在")
                return False
            
            logger.info(f"从Nacos注销SearxNG服务，服务ID: {self.service_id}")
            
            # 注销服务
            result = await deregister_service(
                service_name=self.service_name,
                service_id=self.service_id
            )
            
            if result:
                self.nacos_registered = False
                self.service_id = None
                logger.info("SearxNG服务已从Nacos注销")
                return True
            else:
                logger.error("从Nacos注销SearxNG服务失败")
                return False
                
        except Exception as e:
            logger.error(f"从Nacos注销SearxNG服务时出错: {str(e)}")
            return False
    
    async def send_heartbeat(self) -> bool:
        """
        向Nacos发送心跳
        
        返回:
            bool: 发送心跳是否成功
        """
        try:
            if not self.service_id or not self.nacos_registered:
                return False
            
            # 先检查服务健康状态
            health_status = await self.check_health()
            if not health_status:
                logger.warning("SearxNG服务不健康，不发送心跳")
                return False
            
            # 发送心跳
            result = await send_heartbeat(
                service_name=self.service_name,
                ip=self.host,
                port=self.port
            )
            
            if not result:
                logger.warning("发送SearxNG服务心跳到Nacos失败")
            
            return result
            
        except Exception as e:
            logger.error(f"发送SearxNG服务心跳时出错: {str(e)}")
            return False
    
    async def search(self, query: str, engines: List[str] = None, 
                   language: str = 'zh-CN', max_results: int = 10) -> List[Dict[str, Any]]:
        """
        通过SearxNG执行搜索
        
        参数:
            query: 搜索查询
            engines: 搜索引擎列表，默认为None（使用所有可用引擎）
            language: 搜索语言，默认为zh-CN
            max_results: 最大结果数，默认为10
            
        返回:
            搜索结果列表
        """
        try:
            # 检查服务是否在运行
            if not self.is_running:
                health_status = await self.check_health()
                if not health_status:
                    logger.error("SearxNG服务未运行，无法执行搜索")
                    return []
            
            # 准备查询参数
            params = {
                'q': query,
                'format': 'json',
                'lang': language,
                'pageno': 1,
                'language': language,
            }
            
            # 添加引擎参数（如果提供）
            if engines:
                params['engines'] = ','.join(engines)
            
            # 执行搜索请求
            async with aiohttp.ClientSession() as session:
                async with session.get(self.search_endpoint, params=params, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"SearxNG搜索请求失败，HTTP状态码: {response.status}")
                        return []
                    
                    data = await response.json()
                    results = data.get('results', [])
                    
                    # 限制结果数量
                    if len(results) > max_results:
                        results = results[:max_results]
                    
                    # 转换为标准格式
                    formatted_results = []
                    for result in results:
                        formatted_results.append({
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                            'content': result.get('content', ''),
                            'source': result.get('engine', ''),
                            'score': result.get('score', 0.0),
                            'published_date': result.get('publishedDate', '')
                        })
                    
                    return formatted_results
                    
        except Exception as e:
            logger.error(f"执行SearxNG搜索时出错: {str(e)}")
            return []

# 全局单例
_searxng_manager = None

def get_searxng_manager() -> SearxNGManager:
    """
    获取SearxNG管理器单例
    
    返回:
        SearxNGManager实例
    """
    global _searxng_manager
    
    if _searxng_manager is None:
        _searxng_manager = SearxNGManager()
    
    return _searxng_manager
