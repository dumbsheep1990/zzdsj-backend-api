from nacos import NacosClient
import socket
import threading
import time
from app.config import settings

# 全局Nacos客户端实例
_nacos_client = None

def get_nacos_client():
    """获取或创建Nacos客户端实例"""
    global _nacos_client
    
    if _nacos_client is None:
        _nacos_client = NacosClient(
            server_addresses=settings.NACOS_SERVER_ADDRESSES,
            namespace=settings.NACOS_NAMESPACE
        )
    
    return _nacos_client

def register_service():
    """向Nacos注册服务"""
    client = get_nacos_client()
    
    # 如果未指定则获取本地IP
    ip = settings.SERVICE_IP
    if ip == "127.0.0.1" or ip == "localhost":
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except Exception as e:
            print(f"获取本地IP时出错: {e}")
            ip = "127.0.0.1"
    
    # 注册服务实例
    success = client.add_instance(
        service_name=settings.SERVICE_NAME,
        ip=ip,
        port=settings.SERVICE_PORT,
        weight=1.0,
        ephemeral=True,  # 临时实例在心跳停止时将自动删除
        group_name=settings.NACOS_GROUP
    )
    
    if success:
        print(f"服务 {settings.SERVICE_NAME} 已在 {ip}:{settings.SERVICE_PORT} 注册到Nacos")
    else:
        print(f"无法将服务 {settings.SERVICE_NAME} 注册到Nacos")
    
    return success

def deregister_service():
    """从Nacos注销服务"""
    client = get_nacos_client()
    
    # 注销服务实例
    success = client.remove_instance(
        service_name=settings.SERVICE_NAME,
        ip=settings.SERVICE_IP,
        port=settings.SERVICE_PORT,
        group_name=settings.NACOS_GROUP
    )
    
    if success:
        print(f"服务 {settings.SERVICE_NAME} 已从Nacos注销")
    else:
        print(f"无法从Nacos注销服务 {settings.SERVICE_NAME}")
    
    return success

def start_heartbeat():
    """启动后台线程向Nacos发送心跳"""
    def heartbeat_task():
        client = get_nacos_client()
        
        while True:
            try:
                # 发送心跳
                client.send_heartbeat(
                    service_name=settings.SERVICE_NAME,
                    ip=settings.SERVICE_IP,
                    port=settings.SERVICE_PORT,
                    group_name=settings.NACOS_GROUP
                )
                
                # 休眠5秒
                time.sleep(5)
            
            except Exception as e:
                print(f"向Nacos发送心跳时出错: {e}")
                time.sleep(1)
    
    # 启动心跳线程
    heartbeat_thread = threading.Thread(target=heartbeat_task, daemon=True)
    heartbeat_thread.start()

def get_service_instances(service_name: str, group_name: str = None):
    """获取服务的所有实例"""
    client = get_nacos_client()
    
    if group_name is None:
        group_name = settings.NACOS_GROUP
    
    try:
        instances = client.list_naming_instance(
            service_name=service_name,
            group_name=group_name
        )
        
        return instances.get('hosts', [])
    
    except Exception as e:
        print(f"从Nacos获取服务实例时出错: {e}")
        return []

def get_config(data_id: str, group: str = None):
    """从Nacos获取配置"""
    client = get_nacos_client()
    
    if group is None:
        group = settings.NACOS_GROUP
    
    try:
        return client.get_config(
            data_id=data_id,
            group=group
        )
    
    except Exception as e:
        print(f"从Nacos获取配置时出错: {e}")
        return None

def publish_config(data_id: str, content: str, group: str = None):
    """发布配置到Nacos"""
    client = get_nacos_client()
    
    if group is None:
        group = settings.NACOS_GROUP
    
    try:
        return client.publish_config(
            data_id=data_id,
            group=group,
            content=content
        )
    
    except Exception as e:
        print(f"向Nacos发布配置时出错: {e}")
        return False
