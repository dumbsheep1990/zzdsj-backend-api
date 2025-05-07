"""
服务管理模块 - 管理外部服务的自动启动和状态监控
支持在应用程序启动时自动启动所需的外部服务
"""
import os
import sys
import time
import logging
import subprocess
import threading
import signal
from typing import Dict, List, Optional, Union, Any, Callable
import atexit

logger = logging.getLogger(__name__)

class ServiceManager:
    """服务管理器 - 负责管理应用程序依赖的外部服务"""
    
    def __init__(self):
        """初始化服务管理器"""
        self.services = {}  # 服务注册表
        self.managed_processes = {}  # 管理的进程
        self.services_lock = threading.RLock()
        self.startup_order = []  # 服务启动顺序
        
        # 注册程序退出时清理进程
        atexit.register(self.cleanup_all_services)
    
    def register_service(self, 
                       service_name: str, 
                       service_type: str, 
                       start_cmd: Optional[str] = None,
                       stop_cmd: Optional[str] = None,
                       startup_dir: Optional[str] = None,
                       health_check: Optional[Callable] = None,
                       depends_on: Optional[List[str]] = None,
                       auto_start: bool = True,
                       environment: Optional[Dict[str, str]] = None) -> bool:
        """
        注册服务
        
        Args:
            service_name: 服务名称
            service_type: 服务类型 (docker/process/external)
            start_cmd: 启动命令
            stop_cmd: 停止命令
            startup_dir: 启动目录
            health_check: 健康检查函数
            depends_on: 依赖的其他服务
            auto_start: 是否自动启动
            environment: 环境变量
            
        Returns:
            注册是否成功
        """
        with self.services_lock:
            # 检查服务是否已经注册
            if service_name in self.services:
                logger.warning(f"服务 {service_name} 已注册")
                return False
            
            # 注册服务
            self.services[service_name] = {
                "name": service_name,
                "type": service_type,
                "start_cmd": start_cmd,
                "stop_cmd": stop_cmd,
                "startup_dir": startup_dir or os.getcwd(),
                "health_check": health_check,
                "depends_on": depends_on or [],
                "auto_start": auto_start,
                "environment": environment or {},
                "status": "registered"
            }
            
            # 添加到启动顺序列表
            self.startup_order.append(service_name)
            
            logger.info(f"服务 {service_name} 已注册")
            return True
    
    def start_service(self, service_name: str) -> bool:
        """
        启动指定服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            启动是否成功
        """
        with self.services_lock:
            # 检查服务是否已注册
            if service_name not in self.services:
                logger.error(f"服务 {service_name} 未注册")
                return False
            
            service = self.services[service_name]
            
            # 检查服务是否已经运行
            if service["status"] == "running":
                logger.info(f"服务 {service_name} 已在运行")
                return True
            
            # 检查依赖
            for dep in service["depends_on"]:
                if dep not in self.services or self.services[dep]["status"] != "running":
                    logger.error(f"服务 {service_name} 的依赖 {dep} 未运行")
                    return False
            
            # 根据服务类型执行启动
            try:
                if service["type"] == "docker":
                    # Docker服务启动
                    return self._start_docker_service(service)
                elif service["type"] == "process":
                    # 进程服务启动
                    return self._start_process_service(service)
                elif service["type"] == "external":
                    # 外部服务只需验证健康状态
                    return self._check_external_service(service)
                else:
                    logger.error(f"不支持的服务类型: {service['type']}")
                    return False
            except Exception as e:
                logger.error(f"启动服务 {service_name} 时出错: {str(e)}")
                service["status"] = "error"
                return False
    
    def _start_docker_service(self, service: Dict) -> bool:
        """启动Docker服务"""
        if not service.get("start_cmd"):
            logger.error(f"服务 {service['name']} 没有定义启动命令")
            return False
        
        logger.info(f"正在启动Docker服务: {service['name']}")
        
        # 构建环境变量
        env = os.environ.copy()
        env.update(service["environment"])
        
        try:
            # 执行Docker启动命令
            process = subprocess.Popen(
                service["start_cmd"],
                shell=True,
                cwd=service["startup_dir"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待启动完成
            stdout, stderr = process.communicate(timeout=60)
            
            if process.returncode != 0:
                logger.error(f"启动Docker服务 {service['name']} 失败: {stderr}")
                service["status"] = "error"
                return False
            
            # 检查服务健康状态
            if service.get("health_check") and callable(service["health_check"]):
                healthy = False
                for _ in range(5):  # 尝试5次
                    if service["health_check"]():
                        healthy = True
                        break
                    time.sleep(3)
                
                if not healthy:
                    logger.error(f"Docker服务 {service['name']} 健康检查失败")
                    service["status"] = "unhealthy"
                    return False
            
            service["status"] = "running"
            logger.info(f"Docker服务 {service['name']} 已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动Docker服务 {service['name']} 时出错: {str(e)}")
            service["status"] = "error"
            return False
    
    def _start_process_service(self, service: Dict) -> bool:
        """启动进程服务"""
        if not service.get("start_cmd"):
            logger.error(f"服务 {service['name']} 没有定义启动命令")
            return False
        
        logger.info(f"正在启动进程服务: {service['name']}")
        
        # 构建环境变量
        env = os.environ.copy()
        env.update(service["environment"])
        
        try:
            # 执行进程启动命令
            process = subprocess.Popen(
                service["start_cmd"],
                shell=True,
                cwd=service["startup_dir"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 将进程保存到管理列表
            self.managed_processes[service["name"]] = process
            
            # 检查进程是否正常启动
            time.sleep(2)
            if process.poll() is not None:
                # 进程已退出
                stdout, stderr = process.communicate()
                logger.error(f"进程服务 {service['name']} 启动后立即退出: {stderr}")
                service["status"] = "error"
                return False
            
            # 检查服务健康状态
            if service.get("health_check") and callable(service["health_check"]):
                healthy = False
                for _ in range(5):  # 尝试5次
                    if service["health_check"]():
                        healthy = True
                        break
                    time.sleep(3)
                
                if not healthy:
                    logger.error(f"进程服务 {service['name']} 健康检查失败")
                    service["status"] = "unhealthy"
                    # 尝试终止进程
                    process.terminate()
                    return False
            
            service["status"] = "running"
            logger.info(f"进程服务 {service['name']} 已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动进程服务 {service['name']} 时出错: {str(e)}")
            service["status"] = "error"
            return False
    
    def _check_external_service(self, service: Dict) -> bool:
        """检查外部服务"""
        logger.info(f"检查外部服务: {service['name']}")
        
        # 外部服务需要健康检查
        if not service.get("health_check") or not callable(service["health_check"]):
            logger.error(f"外部服务 {service['name']} 没有定义健康检查函数")
            return False
        
        try:
            # 执行健康检查
            if service["health_check"]():
                service["status"] = "running"
                logger.info(f"外部服务 {service['name']} 可用")
                return True
            else:
                service["status"] = "unavailable"
                logger.error(f"外部服务 {service['name']} 不可用")
                return False
                
        except Exception as e:
            logger.error(f"检查外部服务 {service['name']} 时出错: {str(e)}")
            service["status"] = "error"
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """
        停止指定服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            停止是否成功
        """
        with self.services_lock:
            # 检查服务是否已注册
            if service_name not in self.services:
                logger.error(f"服务 {service_name} 未注册")
                return False
            
            service = self.services[service_name]
            
            # 检查服务是否在运行
            if service["status"] != "running":
                logger.info(f"服务 {service_name} 未运行")
                return True
            
            # 检查其他服务是否依赖此服务
            for other_name, other_service in self.services.items():
                if service_name in other_service["depends_on"] and other_service["status"] == "running":
                    logger.warning(f"无法停止服务 {service_name}，因为 {other_name} 依赖它")
                    return False
            
            # 根据服务类型执行停止
            try:
                if service["type"] == "docker":
                    # Docker服务停止
                    return self._stop_docker_service(service)
                elif service["type"] == "process":
                    # 进程服务停止
                    return self._stop_process_service(service)
                elif service["type"] == "external":
                    # 外部服务只需标记状态
                    service["status"] = "stopped"
                    return True
                else:
                    logger.error(f"不支持的服务类型: {service['type']}")
                    return False
            except Exception as e:
                logger.error(f"停止服务 {service_name} 时出错: {str(e)}")
                return False
    
    def _stop_docker_service(self, service: Dict) -> bool:
        """停止Docker服务"""
        if not service.get("stop_cmd"):
            logger.error(f"服务 {service['name']} 没有定义停止命令")
            return False
        
        logger.info(f"正在停止Docker服务: {service['name']}")
        
        # 构建环境变量
        env = os.environ.copy()
        env.update(service["environment"])
        
        try:
            # 执行Docker停止命令
            process = subprocess.Popen(
                service["stop_cmd"],
                shell=True,
                cwd=service["startup_dir"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待停止完成
            stdout, stderr = process.communicate(timeout=60)
            
            if process.returncode != 0:
                logger.error(f"停止Docker服务 {service['name']} 失败: {stderr}")
                return False
            
            service["status"] = "stopped"
            logger.info(f"Docker服务 {service['name']} 已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止Docker服务 {service['name']} 时出错: {str(e)}")
            return False
    
    def _stop_process_service(self, service: Dict) -> bool:
        """停止进程服务"""
        logger.info(f"正在停止进程服务: {service['name']}")
        
        # 检查是否有管理的进程
        if service["name"] in self.managed_processes:
            process = self.managed_processes[service["name"]]
            
            try:
                # 尝试优雅终止进程
                if process.poll() is None:  # 进程仍在运行
                    process.terminate()
                    process.wait(timeout=10)
                
                # 检查进程是否仍在运行
                if process.poll() is None:
                    # 强制终止
                    process.kill()
                    process.wait(timeout=5)
                
                # 从管理列表中移除
                del self.managed_processes[service["name"]]
                
                service["status"] = "stopped"
                logger.info(f"进程服务 {service['name']} 已停止")
                return True
                
            except Exception as e:
                logger.error(f"停止进程服务 {service['name']} 时出错: {str(e)}")
                return False
        
        # 如果没有管理的进程，尝试使用停止命令
        if service.get("stop_cmd"):
            try:
                # 构建环境变量
                env = os.environ.copy()
                env.update(service["environment"])
                
                # 执行停止命令
                process = subprocess.Popen(
                    service["stop_cmd"],
                    shell=True,
                    cwd=service["startup_dir"],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # 等待停止完成
                stdout, stderr = process.communicate(timeout=60)
                
                if process.returncode != 0:
                    logger.error(f"停止进程服务 {service['name']} 失败: {stderr}")
                    return False
                
                service["status"] = "stopped"
                logger.info(f"进程服务 {service['name']} 已停止")
                return True
                
            except Exception as e:
                logger.error(f"执行停止命令停止进程服务 {service['name']} 时出错: {str(e)}")
                return False
        
        # 如果既没有管理的进程，也没有停止命令，则标记为已停止
        service["status"] = "stopped"
        logger.warning(f"进程服务 {service['name']} 没有管理的进程或停止命令，已标记为停止")
        return True
    
    def restart_service(self, service_name: str) -> bool:
        """
        重启指定服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            重启是否成功
        """
        with self.services_lock:
            if service_name not in self.services:
                logger.error(f"服务 {service_name} 未注册")
                return False
            
            logger.info(f"正在重启服务: {service_name}")
            
            # 先停止再启动
            stop_success = self.stop_service(service_name)
            if not stop_success:
                logger.error(f"重启服务 {service_name} 时停止失败")
                return False
            
            # 等待服务完全停止
            time.sleep(2)
            
            # 启动服务
            start_success = self.start_service(service_name)
            if not start_success:
                logger.error(f"重启服务 {service_name} 时启动失败")
                return False
            
            logger.info(f"服务 {service_name} 已重启")
            return True
    
    def get_service_status(self, service_name: str) -> Dict:
        """
        获取服务状态
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务状态信息
        """
        with self.services_lock:
            if service_name not in self.services:
                return {"name": service_name, "status": "not_registered"}
            
            service = self.services[service_name]
            
            # 对于正在运行的服务，执行健康检查
            if service["status"] == "running" and service.get("health_check") and callable(service["health_check"]):
                try:
                    if not service["health_check"]():
                        service["status"] = "unhealthy"
                except Exception:
                    service["status"] = "error"
            
            # 返回服务信息副本
            return {
                "name": service["name"],
                "type": service["type"],
                "status": service["status"],
                "depends_on": service["depends_on"].copy()
            }
    
    def list_services(self) -> List[Dict]:
        """
        列出所有服务
        
        Returns:
            服务列表
        """
        with self.services_lock:
            services_list = []
            for service_name in self.startup_order:
                services_list.append(self.get_service_status(service_name))
            return services_list
    
    def start_all_services(self) -> Dict[str, bool]:
        """
        启动所有自动启动的服务
        
        Returns:
            服务启动结果字典
        """
        results = {}
        with self.services_lock:
            # 按照启动顺序启动服务
            for service_name in self.startup_order:
                service = self.services[service_name]
                if service["auto_start"]:
                    logger.info(f"自动启动服务: {service_name}")
                    results[service_name] = self.start_service(service_name)
                else:
                    logger.info(f"跳过非自动启动服务: {service_name}")
                    results[service_name] = None
        
        return results
    
    def stop_all_services(self) -> Dict[str, bool]:
        """
        停止所有服务
        
        Returns:
            服务停止结果字典
        """
        results = {}
        with self.services_lock:
            # 按照启动顺序的逆序停止服务
            for service_name in reversed(self.startup_order):
                if self.services[service_name]["status"] == "running":
                    logger.info(f"停止服务: {service_name}")
                    results[service_name] = self.stop_service(service_name)
                else:
                    logger.info(f"跳过未运行服务: {service_name}")
                    results[service_name] = None
        
        return results
    
    def cleanup_all_services(self):
        """清理所有服务（程序退出时调用）"""
        logger.info("程序退出，正在清理服务...")
        self.stop_all_services()
        
        # 确保所有管理的进程已终止
        for name, process in list(self.managed_processes.items()):
            try:
                if process.poll() is None:  # 进程仍在运行
                    logger.info(f"强制终止进程: {name}")
                    process.kill()
            except Exception as e:
                logger.error(f"终止进程 {name} 时出错: {str(e)}")
                
        logger.info("服务清理完成")

# 全局服务管理器实例
_service_manager = None

def get_service_manager() -> ServiceManager:
    """获取全局服务管理器实例"""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager

# LightRAG服务相关函数

def is_lightrag_available() -> bool:
    """检查LightRAG服务是否可用"""
    import requests
    try:
        response = requests.get("http://localhost:9621/health", timeout=3)
        return response.status_code == 200
    except Exception:
        return False

def register_lightrag_service():
    """注册LightRAG服务"""
    # 项目根目录
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    lightrag_dir = os.path.join(root_dir, 'docker', 'lightrag')
    
    manager = get_service_manager()
    
    # 注册LightRAG服务
    manager.register_service(
        service_name="lightrag-api",
        service_type="docker",
        start_cmd="docker-compose up -d",
        stop_cmd="docker-compose down",
        startup_dir=lightrag_dir,
        health_check=is_lightrag_available,
        depends_on=["postgres", "redis"],  # 假设这些服务已经注册
        auto_start=True
    )
    
    # 返回注册的服务
    return manager.get_service_status("lightrag-api")
