import json
import pika
from typing import Any, Dict, Callable
from app.config import settings

def get_rabbitmq_connection():
    """Get RabbitMQ connection"""
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
    """Publish a message to RabbitMQ"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare exchange
    channel.exchange_declare(
        exchange=exchange,
        exchange_type=exchange_type,
        durable=True
    )
    
    # Convert message to JSON if it's a dict or list
    if isinstance(message, (dict, list)):
        message = json.dumps(message)
    
    # Publish message
    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
            content_type='application/json' if isinstance(message, str) and message.startswith('{') else 'text/plain'
        )
    )
    
    connection.close()

def init_queue(queue_name: str, exchange: str, routing_key: str, exchange_type: str = 'direct'):
    """Initialize a RabbitMQ queue"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare exchange
    channel.exchange_declare(
        exchange=exchange,
        exchange_type=exchange_type,
        durable=True
    )
    
    # Declare queue
    channel.queue_declare(
        queue=queue_name,
        durable=True
    )
    
    # Bind queue to exchange
    channel.queue_bind(
        queue=queue_name,
        exchange=exchange,
        routing_key=routing_key
    )
    
    connection.close()

def start_consumer(queue_name: str, callback: Callable, prefetch_count: int = 1):
    """Start a RabbitMQ consumer"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Set prefetch count
    channel.basic_qos(prefetch_count=prefetch_count)
    
    # Define callback wrapper
    def callback_wrapper(ch, method, properties, body):
        try:
            # Try to parse as JSON
            if properties.content_type == 'application/json':
                message = json.loads(body)
            else:
                message = body.decode()
            
            # Call user callback
            callback(message)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
        
        except Exception as e:
            print(f"Error processing message: {e}")
            # Negative acknowledge message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    # Start consuming
    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback_wrapper
    )
    
    # Start consuming
    print(f"Starting consumer for queue {queue_name}")
    channel.start_consuming()
