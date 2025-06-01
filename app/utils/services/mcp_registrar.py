"""
MCP服务注册器
负责将MCP服务注册到Nacos服务发现系统
"""

import logging
import threading
import time
import socket
from typing import Dict, Any, Optional, List
import json

from app.utils.service_discovery import get_nacos_client
from app.config import settings

logger = logging.getLogger(__name__)

class MCPServiceRegistrar:
    """
    MCP服务注册器
    负责管理MCP服务在Nacos中的注册、心跳和注销
    """
    
    def __init__(self):
        """初始化MCP服务注册器"""
        self.nacos_client = get_nacos_client()
        self.registered_services = {}  # deployment_id -> registration_info
        self._heartbeat_thread = None
        self._running = False
    
    def register_mcp_service(self, deployment_id: str, name: str, 
                          service_port: int, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        向Nacos注册MCP服务
        
        参数:
            deployment_id: 部署ID
            name: 服务名称
            service_port: 服务端口
            metadata: 服务元数据
            
        返回:
            注册是否成功
        """
        if not metadata:
            metadata = {}
        
        # 构建服务名称
        service_name = f"mcp-{name}"
        
        # 尝试获取本机IP
        ip = settings.SERVICE_IP
        if ip == "127.0.0.1" or ip == "localhost":
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
            except Exception as e:
                logger.error(f"获取本地IP时出错: {e}")
                ip = "127.0.0.1"
        
        # 为元数据添加MCP服务特定信息
        metadata.update({
            "deployment_id": deployment_id,
            "type": "mcp-service",
            "app": "zz-backend-lite"
        })
        
        # 注册服务实例
        try:
            success = self.nacos_client.add_instance(
                service_name=service_name,
                ip=ip,
                port=service_port,
                weight=1.0,
                ephemeral=True,  # 临时实例，心跳停止时自动删除
                metadata=json.dumps(metadata),
                group_name=settings.NACOS_GROUP
            )
            
            if success:
                logger.info(f"MCP服务 {service_name} 已在 {ip}:{service_port} 注册到Nacos")
                # 保存注册信息
                self.registered_services[deployment_id] = {
                    "service_name": service_name,
                    "ip": ip,
                    "port": service_port,
                    "metadata": metadata
                }
                # 确保心跳线程运行
                self._ensure_heartbeat_running()
            else:
                logger.error(f"无法将MCP服务 {service_name} 注册到Nacos")
            
            return success
        
        except Exception as e:
            logger.error(f"注册MCP服务到Nacos时出错: {str(e)}")
            return False
    
    def deregister_mcp_service(self, deployment_id: str) -> bool:
        """
        从Nacos注销MCP服务
        
        参数:
            deployment_id: 部署ID
            
        返回:
            注销是否成功
        """
        if deployment_id not in self.registered_services:
            logger.warning(f"尝试注销未注册的MCP服务: {deployment_id}")
            return True
        
        registration_info = self.registered_services[deployment_id]
        
        try:
            success = self.nacos_client.remove_instance(
                service_name=registration_info["service_name"],
                ip=registration_info["ip"],
                port=registration_info["port"],
                group_name=settings.NACOS_GROUP
            )
            
            if success:
                logger.info(f"MCP服务 {registration_info['service_name']} 已从Nacos注销")
                # 移除注册信息
                del self.registered_services[deployment_id]
            else:
                logger.error(f"无法从Nacos注销MCP服务 {registration_info['service_name']}")
            
            return success
        
        except Exception as e:
            logger.error(f"从Nacos注销MCP服务时出错: {str(e)}")
            return False
    
    def update_mcp_service_status(self, deployment_id: str, healthy: bool) -> bool:
        """
        更新MCP服务的健康状态
        
        参数:
            deployment_id: 部署ID
            healthy: 是否健康
            
        返回:
            更新是否成功
        """
        if deployment_id not in self.registered_services:
            logger.warning(f"尝试更新未注册的MCP服务状态: {deployment_id}")
            return False
        
        registration_info = self.registered_services[deployment_id]
        
        # 更新元数据
        metadata = registration_info["metadata"].copy()
        metadata["healthy"] = "true" if healthy else "false"
        
        try:
            success = self.nacos_client.modify_instance(
                service_name=registration_info["service_name"],
                ip=registration_info["ip"],
                port=registration_info["port"],
                weight=1.0,
                metadata=json.dumps(metadata),
                group_name=settings.NACOS_GROUP
            )
            
            if success:
                # 更新缓存的注册信息
                registration_info["metadata"] = metadata
                self.registered_services[deployment_id] = registration_info
                logger.info(f"已更新MCP服务 {registration_info['service_name']} 的健康状态: {healthy}")
            else:
                logger.error(f"无法更新MCP服务 {registration_info['service_name']} 的健康状态")
            
            return success
        
        except Exception as e:
            logger.error(f"更新MCP服务状态时出错: {str(e)}")
            return False
    
    def list_registered_mcp_services(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的MCP服务
        
        返回:
            已注册MCP服务的列表
        """
        result = []
        for deployment_id, info in self.registered_services.items():
            result.append({
                "deployment_id": deployment_id,
                "service_name": info["service_name"],
                "ip": info["ip"],
                "port": info["port"],
                "metadata": info["metadata"]
            })
        return result
    
    def _ensure_heartbeat_running(self):
        """确保心跳线程在运行中"""
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._running = True
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_task, daemon=True)
            self._heartbeat_thread.start()
    
    def _heartbeat_task(self):
        """心跳任务，定期向Nacos发送所有注册服务的心跳"""
        while self._running:
            for deployment_id, info in list(self.registered_services.items()):
                try:
                    self.nacos_client.send_heartbeat(
                        service_name=info["service_name"],
                        ip=info["ip"],
                        port=info["port"],
                        metadata=json.dumps(info["metadata"]),
                        group_name=settings.NACOS_GROUP
                    )
                    logger.debug(f"已向MCP服务 {info['service_name']} 发送心跳")
                except Exception as e:
                    logger.error(f"向MCP服务 {info['service_name']} 发送心跳时出错: {str(e)}")
            
            # 每5秒发送一次心跳
            time.sleep(5)
    
    def stop(self):
        """停止心跳线程并注销所有服务"""
        self._running = False
        
        # 注销所有服务
        for deployment_id in list(self.registered_services.keys()):
            self.deregister_mcp_service(deployment_id)
        
        # 等待心跳线程结束
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)

# 全局单例
_mcp_registrar_instance = None

def get_mcp_service_registrar():
    """
    获取MCP服务注册器实例
    
    返回:
        MCPServiceRegistrar实例
    """
    global _mcp_registrar_instance
    
    if _mcp_registrar_instance is None:
        _mcp_registrar_instance = MCPServiceRegistrar()
    
    return _mcp_registrar_instance
