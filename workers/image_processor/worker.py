import os
import sys
import pika
import json
import logging
import tempfile
from pathlib import Path
from PIL import Image
from io import BytesIO
import boto3
from botocore.client import Config
from sqlalchemy import create_engine, text
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
QUEUE_NAME = 'image_queue'

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


def update_job_status(db, job_id, status, error_message=None, result_file_id=None):
    """Update job status in database"""
    from uuid import UUID
    from sqlalchemy import text
    from datetime import datetime
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = JobStatus(status)
        job.updated_at = datetime.utcnow()
        if error_message:
            job.error_message = error_message
        if result_file_id:
            job.result_file_id = result_file_id
        db.commit()


def create_thumbnail(input_path, output_path, size=(256, 256)):
    """Create a thumbnail from an image"""
    with Image.open(input_path) as img:
        # Convert RGBA to RGB if necessary
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(output_path, 'JPEG', quality=85)


def convert_image(input_path, output_path, target_format='WEBP', quality=85):
    """Convert image to different format"""
    with Image.open(input_path) as img:
        # Convert RGBA to RGB for formats that don't support transparency
        if target_format in ['JPEG', 'JPG'] and img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output_path, target_format, quality=quality)


def compress_image(input_path, output_path, quality=60):
    """Compress an image"""
    with Image.open(input_path) as img:
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output_path, 'JPEG', quality=quality, optimize=True)


def process_image_job(job_data):
    """Main image processing function"""
    job_id = job_data['job_id']
    file_id = job_data['file_id']
    bucket = job_data['bucket']
    key = job_data['key']
    job_type = job_data['type']
    params = job_data.get('params', {})
    
    logger.info(f"Processing image job {job_id} of type {job_type}")
    
    db = SessionLocal()
    
    try:
        # Update job status to running
        update_job_status(db, job_id, JobStatus.RUNNING)
        
        # Download file from MinIO
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix) as tmp_input:
            input_path = tmp_input.name
            s3_client.download_file(bucket, key, input_path)
        
        # Get original filename for output naming
        file_obj = db.query(File).filter(File.id == file_id).first()
        original_name = file_obj.original_name if file_obj else 'file'
        base_name = Path(original_name).stem
        
        # Process based on type
        output_path = None
        output_bucket = None
        output_key = None
        
        if job_type == 'thumbnail':
            size = params.get('size', '256x256')
            width, height = map(int, size.split('x'))
            
            output_path = tempfile.mktemp(suffix='.jpg')
            create_thumbnail(input_path, output_path, size=(width, height))
            
            output_bucket = 'thumbnails'
            output_key = f"{base_name}_thumb_{size}.jpg"
            
        elif job_type == 'image_convert':
            target_format = params.get('target_format', 'WEBP').upper()
            quality = params.get('quality', 85)
            
            ext = target_format.lower()
            if ext == 'jpg':
                ext = 'jpeg'
            output_path = tempfile.mktemp(suffix=f'.{ext}')
            convert_image(input_path, output_path, target_format, quality)
            
            output_bucket = 'processed'
            output_key = f"{base_name}_converted.{ext}"
            
        elif job_type == 'image_compress':
            quality = params.get('quality', 60)
            
            output_path = tempfile.mktemp(suffix='.jpg')
            compress_image(input_path, output_path, quality)
            
            output_bucket = 'processed'
            output_key = f"{base_name}_compressed.jpg"
        
        # Upload result to MinIO
        if output_path and output_bucket and output_key:
            s3_client.upload_file(output_path, output_bucket, output_key)
            
            # Get file size
            output_size = os.path.getsize(output_path)
            
            # Create File record for output
            import uuid
            result_file_id = str(uuid.uuid4())
            
            file_query = f"""
                INSERT INTO files (id, owner_id, original_name, storage_bucket, storage_key, 
                                   size_bytes, mime_type, status, is_processed_output, parent_file_id, created_at)
                SELECT '{result_file_id}', owner_id, '{output_key}', '{output_bucket}', '{output_key}',
                       {output_size}, 'image/jpeg', 'READY', true, '{file_id}', NOW()
                FROM files WHERE id = '{file_id}'
            """
            db.execute(text(file_query))
            db.commit()
            
            # Update job with result
            update_job_status(db, job_id, JobStatus.COMPLETED, result_file_id=result_file_id)
            
            # Update file status to READY
            file = db.query(File).filter(File.id == file_id).first()
            if file:
                file.status = FileStatus.READY
                db.commit()
            
            logger.info(f"Job {job_id} completed successfully")
        else:
            update_job_status(db, job_id, JobStatus.COMPLETED)
            
            # Update file status to READY
            file = db.query(File).filter(File.id == file_id).first()
            if file:
                file.status = FileStatus.READY
                db.commit()
        
        # Cleanup
        os.unlink(input_path)
        if output_path and os.path.exists(output_path):
            os.unlink(output_path)
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        db.rollback()
        update_job_status(db, job_id, JobStatus.FAILED, error_message=str(e))
    finally:
        db.close()


def callback(ch, method, properties, body):
    """RabbitMQ message callback"""
    try:
        message = json.loads(body)
        logger.info(f"Received message: {message.get('job_id')}")
        
        process_image_job(message)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error in callback: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main worker function"""
    logger.info(f"Starting image processor worker, connecting to {RABBITMQ_HOST}")
    
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
