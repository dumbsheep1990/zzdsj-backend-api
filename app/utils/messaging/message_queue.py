import json
import pika
from typing import Any, Dict, Callable
from app.config import settings

def get_rabbitmq_connection():
    """获取RabbitMQ连接"""
    credentials = pika.PlainCredentials(
        username=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD
    )
    
    parameters = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600
    )
    
    return pika.BlockingConnection(parameters)

def publish_message(exchange: str, routing_key: str, message: Any, exchange_type: str = 'direct'):
    """向RabbitMQ发布消息"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # 声明交换机
    channel.exchange_declare(
        exchange=exchange,
        exchange_type=exchange_type,
        durable=True
    )
    
    # 如果消息是字典或列表则转换为JSON
    if isinstance(message, (dict, list)):
        message = json.dumps(message)
    
    # 发布消息
    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # 使消息持久化
            content_type='application/json' if isinstance(message, str) and message.startswith('{') else 'text/plain'
        )
    )
    
    connection.close()

def init_queue(queue_name: str, exchange: str, routing_key: str, exchange_type: str = 'direct'):
    """初始化RabbitMQ队列"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # 声明交换机
    channel.exchange_declare(
        exchange=exchange,
        exchange_type=exchange_type,
        durable=True
    )
    
    # 声明队列
    channel.queue_declare(
        queue=queue_name,
        durable=True
    )
    
    # 将队列绑定到交换机
    channel.queue_bind(
        queue=queue_name,
        exchange=exchange,
        routing_key=routing_key
    )
    
    connection.close()

def start_consumer(queue_name: str, callback: Callable, prefetch_count: int = 1):
    """启动RabbitMQ消费者"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # 设置预取计数
    channel.basic_qos(prefetch_count=prefetch_count)
    
    # 定义回调包装器
    def callback_wrapper(ch, method, properties, body):
        try:
            # 尝试解析为JSON
            if properties.content_type == 'application/json':
                message = json.loads(body)
            else:
                message = body.decode()
            
            # 调用用户回调
            callback(message)
            
            # 确认消息
            ch.basic_ack(delivery_tag=method.delivery_tag)
        
        except Exception as e:
            print(f"处理消息时出错: {e}")
            # 消息负确认
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    # 开始消费
    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback_wrapper
    )
    
    # 开始消费
    print(f"正在为队列 {queue_name} 启动消费者")
    channel.start_consuming()
