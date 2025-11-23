import os
import pika
import json
import logging
import tempfile
from pathlib import Path
import boto3
from botocore.client import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, JSON, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://app:app@db:5432/appdb')
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minio')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minio123')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
QUEUE_NAME = 'ai_queue'

# Database models
Base = declarative_base()

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobType(str, enum.Enum):
    IMAGE_CONVERT = "image_convert"
    THUMBNAIL = "thumbnail"
    IMAGE_COMPRESS = "image_compress"
    VIDEO_CONVERT = "video_convert"
    VIDEO_PREVIEW = "video_preview"
    VIDEO_THUMBNAIL = "video_thumbnail"
    COMPRESS = "compress"
    METADATA = "metadata"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    VIRUS_SCAN = "virus_scan"
    AI_TAG = "ai_tag"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), nullable=False)
    pipeline_id = Column(UUID(as_uuid=True), nullable=True)
    type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    result_file_id = Column(UUID(as_uuid=True), nullable=True)
    error_message = Column(Text, nullable=True)
    params = Column(JSON, default={})

class FileMetadata(Base):
    __tablename__ = "file_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), nullable=False)
    ai_tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FileStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"

class File(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    original_name = Column(String, nullable=False)
    storage_bucket = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String)
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADED)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed_output = Column(Boolean, default=False)
    parent_file_id = Column(UUID(as_uuid=True), nullable=True)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# MinIO client
s3_client = boto3.client(
    's3',
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)


def update_job_status(db, job_id, status, error_message=None):
    """Update job status in database"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        # If status is already a JobStatus enum, use it; otherwise convert string
        if isinstance(status, JobStatus):
            job.status = status
        else:
            job.status = JobStatus(status)
        job.updated_at = datetime.utcnow()
        if error_message:
            job.error_message = error_message
        db.commit()


def analyze_image_with_gemini(image_path):
    """Use Gemini API to analyze image and generate tags"""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, using mock tags")
        return ["sample", "image", "auto-tagged"]
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Upload image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Generate tags
        prompt = "Analyze this image and provide 5-10 descriptive tags as a comma-separated list. Only return the tags, nothing else."
        
        response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': image_data}])
        
        # Parse response
        tags_text = response.text.strip()
        tags = [tag.strip().lower() for tag in tags_text.split(',')]
        
        return tags[:10]  # Limit to 10 tags
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return ["error", "auto-tag-failed"]


def process_ai_job(job_data):
    """Main AI processing function"""
    job_id = job_data['job_id']
    file_id = job_data['file_id']
    bucket = job_data['bucket']
    key = job_data['key']
    job_type = job_data['type']
    
    logger.info(f"Processing AI job {job_id} of type {job_type}")
    
    db = SessionLocal()
    
    try:
        # Update job status to running
        update_job_status(db, job_id, JobStatus.RUNNING)
        
        # Download file from MinIO
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix) as tmp_input:
            input_path = tmp_input.name
            s3_client.download_file(bucket, key, input_path)
        
        # Process based on type
        if job_type == 'ai_tag':
            tags = analyze_image_with_gemini(input_path)
            
            # Store tags in file_metadata using ORM
            metadata = db.query(FileMetadata).filter(FileMetadata.file_id == file_id).first()
            
            if metadata:
                # Update existing
                metadata.ai_tags = tags
                metadata.updated_at = datetime.utcnow()
            else:
                # Create new
                metadata = FileMetadata(
                    file_id=file_id,
                    ai_tags=tags
                )
                db.add(metadata)
            
            # Update file status to READY
            file = db.query(File).filter(File.id == file_id).first()
            if file:
                file.status = FileStatus.READY
            
            db.commit()
            
            update_job_status(db, job_id, JobStatus.COMPLETED)
            logger.info(f"AI tagging completed with tags: {tags}")
        
        # Cleanup
        os.unlink(input_path)
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        update_job_status(db, job_id, JobStatus.FAILED, error_message=str(e))
    finally:
        db.close()


def callback(ch, method, properties, body):
    """RabbitMQ message callback"""
    try:
        message = json.loads(body)
        logger.info(f"Received message: {message.get('job_id')}")
        
        process_ai_job(message)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error in callback: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main worker function"""
    logger.info(f"Starting AI tagger worker, connecting to {RABBITMQ_HOST}")
    
    # Connect to RabbitMQ
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Declare queue
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    
    # Set QoS
    channel.basic_qos(prefetch_count=1)
    
    # Start consuming
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    
    logger.info(f"Waiting for messages on {QUEUE_NAME}...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Stopping worker...")
        channel.stop_consuming()
    
    connection.close()


if __name__ == '__main__':
    main()
