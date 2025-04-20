from nacos import NacosClient
import socket
import threading
import time
from app.config import settings

# Global Nacos client instance
_nacos_client = None

def get_nacos_client():
    """Get or create a Nacos client instance"""
    global _nacos_client
    
    if _nacos_client is None:
        _nacos_client = NacosClient(
            server_addresses=settings.NACOS_SERVER_ADDRESSES,
            namespace=settings.NACOS_NAMESPACE
        )
    
    return _nacos_client

def register_service():
    """Register the service with Nacos"""
    client = get_nacos_client()
    
    # Get local IP if not specified
    ip = settings.SERVICE_IP
    if ip == "127.0.0.1" or ip == "localhost":
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except Exception as e:
            print(f"Error getting local IP: {e}")
            ip = "127.0.0.1"
    
    # Register service instance
    success = client.add_instance(
        service_name=settings.SERVICE_NAME,
        ip=ip,
        port=settings.SERVICE_PORT,
        weight=1.0,
        ephemeral=True,  # Ephemeral instance will be automatically removed when heartbeat stops
        group_name=settings.NACOS_GROUP
    )
    
    if success:
        print(f"Service {settings.SERVICE_NAME} registered with Nacos at {ip}:{settings.SERVICE_PORT}")
    else:
        print(f"Failed to register service {settings.SERVICE_NAME} with Nacos")
    
    return success

def deregister_service():
    """Deregister the service from Nacos"""
    client = get_nacos_client()
    
    # Deregister service instance
    success = client.remove_instance(
        service_name=settings.SERVICE_NAME,
        ip=settings.SERVICE_IP,
        port=settings.SERVICE_PORT,
        group_name=settings.NACOS_GROUP
    )
    
    if success:
        print(f"Service {settings.SERVICE_NAME} deregistered from Nacos")
    else:
        print(f"Failed to deregister service {settings.SERVICE_NAME} from Nacos")
    
    return success

def start_heartbeat():
    """Start a background thread to send heartbeats to Nacos"""
    def heartbeat_task():
        client = get_nacos_client()
        
        while True:
            try:
                # Send heartbeat
                client.send_heartbeat(
                    service_name=settings.SERVICE_NAME,
                    ip=settings.SERVICE_IP,
                    port=settings.SERVICE_PORT,
                    group_name=settings.NACOS_GROUP
                )
                
                # Sleep for 5 seconds
                time.sleep(5)
            
            except Exception as e:
                print(f"Error sending heartbeat to Nacos: {e}")
                time.sleep(1)
    
    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=heartbeat_task, daemon=True)
    heartbeat_thread.start()

def get_service_instances(service_name: str, group_name: str = None):
    """Get all instances of a service"""
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
        print(f"Error getting service instances from Nacos: {e}")
        return []

def get_config(data_id: str, group: str = None):
    """Get configuration from Nacos"""
    client = get_nacos_client()
    
    if group is None:
        group = settings.NACOS_GROUP
    
    try:
        return client.get_config(
            data_id=data_id,
            group=group
        )
    
    except Exception as e:
        print(f"Error getting configuration from Nacos: {e}")
        return None

def publish_config(data_id: str, content: str, group: str = None):
    """Publish configuration to Nacos"""
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
        print(f"Error publishing configuration to Nacos: {e}")
        return False
