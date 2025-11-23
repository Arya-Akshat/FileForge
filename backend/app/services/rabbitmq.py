import pika
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQService:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()
    
    def connect(self):
        """Establish connection to RabbitMQ"""
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD
        )
        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self._declare_queues()
    
    def _declare_queues(self):
        """Declare all required queues"""
        queues = [
            'image_queue',
            'video_queue',
            'metadata_queue',
            'security_queue',
            'ai_queue',
            'generic_queue'
        ]
        for queue in queues:
            self.channel.queue_declare(queue=queue, durable=True)
    
    def publish_job(self, queue: str, message: dict):
        """Publish a job message to a queue"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            logger.info(f"Published message to {queue}: {message.get('job_id')}")
        except Exception as e:
            logger.error(f"Error publishing to RabbitMQ: {e}")
            raise
    
    def get_queue_for_job_type(self, job_type: str) -> str:
        """Map job type to appropriate queue"""
        mapping = {
            'image_convert': 'image_queue',
            'thumbnail': 'image_queue',
            'image_compress': 'image_queue',
            'video_convert': 'video_queue',
            'video_preview': 'video_queue',
            'video_thumbnail': 'video_queue',
            'compress': 'security_queue',
            'metadata': 'image_queue',  # Route to image_queue (no dedicated metadata worker)
            'encrypt': 'security_queue',
            'decrypt': 'security_queue',
            'virus_scan': 'security_queue',
            'ai_tag': 'ai_queue'
        }
        return mapping.get(job_type, 'image_queue')
    
    def close(self):
        """Close RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()


rabbitmq_service = RabbitMQService()
