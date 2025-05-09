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
SERVICE_NAME = get_config("LIGHTRAG_SERVICE_NAME", "lightrag-api")
SERVICE_IP = get_config("LIGHTRAG_SERVICE_IP", socket.gethostbyname(socket.gethostname()))
SERVICE_PORT = get_config("LIGHTRAG_SERVER_PORT", "9621")

# 服务元数据
SERVICE_METADATA = {
    "version": "1.0.0",
    "desc": "LightRAG知识图谱检索增强生成服务",
    "type": "rag",
    "api_version": "v1",
    "capabilities": ["knowledge_graph", "hybrid_search", "multi_workdir"],
    "api_url": get_config("LIGHTRAG_API_URL", f"http://{SERVICE_IP}:{SERVICE_PORT}"),
}

# Nacos服务发现配置
NACOS_SERVER = get_config("NACOS_SERVER_ADDRESSES", "http://localhost:8848")
NACOS_NAMESPACE = get_config("NACOS_NAMESPACE", "public")
NACOS_GROUP = get_config("NACOS_GROUP", "DEFAULT_GROUP")
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
            "metadata": json.dumps(SERVICE_METADATA),
            "namespaceId": NACOS_NAMESPACE,
            "groupName": NACOS_GROUP,
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
        # 创建Nacos客户端
        client = NacosClient(
            server_addresses=NACOS_SERVER,
            namespace=NACOS_NAMESPACE,
            username=NACOS_USERNAME,
            password=NACOS_PASSWORD
        )
        
        # 注册服务
        success = client.add_instance(
            service_name=SERVICE_NAME,
            ip=SERVICE_IP,
            port=int(SERVICE_PORT),
            weight=1.0,
            ephemeral=True,  # 临时实例
            metadata=SERVICE_METADATA,
            group_name=NACOS_GROUP,
            cluster_name="DEFAULT"
        )
        
        if success:
            print(f"服务 {SERVICE_NAME} 已成功注册到Nacos, 组: {NACOS_GROUP}, 命名空间: {NACOS_NAMESPACE}")
            print(f"API地址: {SERVICE_METADATA.get('api_url')}")
            return True
        else:
            print(f"注册服务 {SERVICE_NAME} 到Nacos失败")
            return False
    except Exception as e:
        print(f"注册服务到Nacos时出错: {str(e)}")
        return False

def heartbeat_task():
    """心跳任务函数"""
    if NACOS_CLIENT_IMPORTED:
        client = NacosClient(
            server_addresses=NACOS_SERVER,
            namespace=NACOS_NAMESPACE,
            username=NACOS_USERNAME,
            password=NACOS_PASSWORD
        )
    
    try:
        while True:
            time.sleep(HEALTH_CHECK_INTERVAL)  # 心跳间隔
            
            # 检查服务健康状态
            healthy = is_service_healthy()
            print(".", end="", flush=True)  # 显示心跳点
            
            if not healthy:
                print(f"\n\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 警告: LightRAG服务不可用，跳过心跳\n")
                continue
            
            # 发送心跳包
            if NACOS_CLIENT_IMPORTED:
                try:
                    client.send_heartbeat(
                        service_name=SERVICE_NAME, 
                        ip=SERVICE_IP, 
                        port=int(SERVICE_PORT),
                        group_name=NACOS_GROUP,
                        metadata=SERVICE_METADATA
                    )
                except Exception as e:
                    print(f"\n\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 发送心跳包时出错: {str(e)}\n")
                    # 心跳失败时尝试重新注册
                    register_service_via_client()
            else:
                # 如果没有NacosClient，采用HTTP方式重新注册
                register_service_via_http()
    except KeyboardInterrupt:
        print("\n\n收到退出信号，结束心跳")

def main():
    """主函数"""
    print(f"\n====== LightRAG服务注册工具 v1.2.0 ======")
    print(f"\n服务信息:")
    print(f"- 名称: {SERVICE_NAME}")
    print(f"- IP: {SERVICE_IP}")
    print(f"- 端口: {SERVICE_PORT}")
    print(f"- API地址: {SERVICE_METADATA.get('api_url')}")
    print(f"- Nacos服务器: {NACOS_SERVER}")
    print(f"- 命名空间: {NACOS_NAMESPACE}")
    print(f"- 组: {NACOS_GROUP}")
    print(f"- 元数据: {json.dumps(SERVICE_METADATA, ensure_ascii=False, indent=2)}")
    
    # 检查服务健康状态
    print("\n正在检查LightRAG服务健康状态...")
    
    # 最多等待30秒等待服务启动
    healthy = False
    for i in range(6):
        if is_service_healthy():
            healthy = True
            print(f"LightRAG服务健康\n")
            break
        else:
            print(f"\r服务尚未就绪，等待{(i+1)*5}秒...", end="", flush=True)
            time.sleep(5)
    
    if not healthy:
        print("\n\n警告: LightRAG服务不可用，请确保服务已启动")
        print("     继续注册过程，但可能不能正常工作\n")
    
    # 注册服务
    print("\n正在尝试将LightRAG服务注册到Nacos...")
    
    if NACOS_CLIENT_IMPORTED:
        success = register_service_via_client()
    else:
        success = register_service_via_http()
    
    if not success:
        print("\n尝试暴力注册...")
        success = register_service_via_http()
    
    if success:
        print("\n服务注册成功！启动心跳定时器...")
        # 启动心跳任务
        heartbeat_task()
    else:
        print("\n服务注册失败，请检查Nacos服务器配置并重试")
        sys.exit(1)

if __name__ == "__main__":
    main()
