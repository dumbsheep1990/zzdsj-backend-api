"""
LightRAG服务注册脚本 - 用于将LightRAG服务注册到Nacos服务发现系统
支持自动从主项目配置中获取配置信息
"""
import os
import sys
import requests
import json
import time
import socket
import importlib.util

# 添加项目根目录到系统路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(root_dir)

# 尝试导入项目配置和工具
try:
    from app.utils.service_discovery import NacosClient
    NACOS_CLIENT_IMPORTED = True
except ImportError:
    NACOS_CLIENT_IMPORTED = False
    print("警告: 无法导入NacosClient，将使用直接HTTP请求进行服务注册")

# 尝试从项目中获取配置
try:
    from app.config import settings
    PROJECT_CONFIG_AVAILABLE = True
    print("已从项目加载配置设置")
except ImportError:
    PROJECT_CONFIG_AVAILABLE = False
    print("无法从项目加载配置，将使用环境变量和默认值")

# 加载环境变量作为配置的后备来源
def get_config(key, default_value=None):
    """从多个来源获取配置值"""
    # 先从项目配置中获取
    if PROJECT_CONFIG_AVAILABLE and hasattr(settings, key):
        return getattr(settings, key)
    # 然后从环境变量中获取
    env_value = os.environ.get(key)
    if env_value is not None:
        return env_value
    # 最后使用默认值
    return default_value

# 服务配置
SERVICE_NAME = "lightrag-api"
SERVICE_IP = get_config("LIGHTRAG_SERVICE_IP", socket.gethostbyname(socket.gethostname()))
SERVICE_PORT = get_config("LIGHTRAG_PORT", "9621")

# Nacos服务发现配置
NACOS_SERVER = get_config("NACOS_SERVER", "http://localhost:8848")
NACOS_NAMESPACE = get_config("NACOS_NAMESPACE", "public")
NACOS_USERNAME = get_config("NACOS_USERNAME", "nacos")
NACOS_PASSWORD = get_config("NACOS_PASSWORD", "nacos")
HEALTH_CHECK_INTERVAL = int(get_config("HEALTH_CHECK_INTERVAL", "5"))  # 秒

def is_service_healthy():
    """检查LightRAG服务是否健康"""
    try:
        response = requests.get(f"http://{SERVICE_IP}:{SERVICE_PORT}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

def register_service_via_http():
    """通过HTTP API直接向Nacos注册服务"""
    login_url = f"{NACOS_SERVER}/nacos/v1/auth/login"
    login_data = {
        "username": NACOS_USERNAME,
        "password": NACOS_PASSWORD
    }
    
    try:
        # 登录获取token
        login_response = requests.post(login_url, data=login_data)
        if login_response.status_code != 200:
            print(f"登录Nacos失败: {login_response.text}")
            return False
        
        access_token = login_response.json().get("accessToken", "")
        
        # 注册服务
        register_url = f"{NACOS_SERVER}/nacos/v1/ns/instance"
        register_params = {
            "serviceName": SERVICE_NAME,
            "ip": SERVICE_IP,
            "port": SERVICE_PORT,
            "weight": 1.0,
            "enabled": True,
            "healthy": True,
            "ephemeral": True,  # 临时实例，服务停止后自动注销
            "metadata": json.dumps({
                "version": "1.0.0",
                "desc": "LightRAG知识图谱检索增强生成服务"
            }),
            "namespaceId": NACOS_NAMESPACE,
            "accessToken": access_token
        }
        
        register_response = requests.post(register_url, params=register_params)
        if register_response.status_code != 200 or register_response.text.lower() != "ok":
            print(f"注册服务失败: {register_response.text}")
            return False
        
        print(f"服务 {SERVICE_NAME} 已成功注册到Nacos")
        return True
    
    except Exception as e:
        print(f"注册服务过程中发生错误: {e}")
        return False

def register_service_via_client():
    """使用NacosClient注册服务"""
    try:
        client = NacosClient(
            server_addresses=NACOS_SERVER,
            namespace=NACOS_NAMESPACE,
            username=NACOS_USERNAME,
            password=NACOS_PASSWORD
        )
        
        success = client.register_instance(
            service_name=SERVICE_NAME,
            ip=SERVICE_IP,
            port=int(SERVICE_PORT),
            metadata={
                "version": "1.0.0",
                "desc": "LightRAG知识图谱检索增强生成服务"
            }
        )
        
        if success:
            print(f"服务 {SERVICE_NAME} 已成功注册到Nacos")
        else:
            print("注册服务失败")
        
        return success
    
    except Exception as e:
        print(f"使用NacosClient注册服务时发生错误: {e}")
        return False

def main():
    """主函数"""
    print(f"正在启动LightRAG服务注册 - 服务名: {SERVICE_NAME}, IP: {SERVICE_IP}, 端口: {SERVICE_PORT}")
    
    # 等待服务健康
    print("等待LightRAG服务启动并通过健康检查...")
    while not is_service_healthy():
        print("服务尚未准备就绪，等待5秒后重试...")
        time.sleep(5)
    
    print("LightRAG服务已就绪，开始注册到Nacos...")
    
    # 注册服务
    if NACOS_CLIENT_IMPORTED:
        success = register_service_via_client()
    else:
        success = register_service_via_http()
    
    if not success:
        print("服务注册失败，请检查网络连接和Nacos服务器状态")
        sys.exit(1)
    
    print("服务注册完成")
    
    # 定期检查服务健康状态并保持心跳
    print(f"开始定期健康检查，间隔: {HEALTH_CHECK_INTERVAL}秒")
    try:
        while True:
            time.sleep(HEALTH_CHECK_INTERVAL)
            is_healthy = is_service_healthy()
            if not is_healthy:
                print("警告: 服务健康检查失败，尝试重新注册...")
                if NACOS_CLIENT_IMPORTED:
                    register_service_via_client()
                else:
                    register_service_via_http()
    except KeyboardInterrupt:
        print("接收到中断信号，停止服务注册")
    
    print("服务注册脚本已结束")

if __name__ == "__main__":
    main()
