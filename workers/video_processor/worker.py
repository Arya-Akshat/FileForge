import os
import sys
import pika
import json
import logging
import tempfile
import subprocess
from pathlib import Path
import boto3
from botocore.client import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, JSON, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

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
QUEUE_NAME = 'video_queue'

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


def create_video_thumbnail(input_path, output_path, time='00:00:01'):
    """Extract a thumbnail from video at specified time"""
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-ss', time,
        '-vframes', '1',
        '-vf', 'scale=640:-1',
        '-y',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def create_video_preview(input_path, output_path, duration=10):
    """Create a short preview clip from video"""
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-t', str(duration),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:v', '1M',
        '-b:a', '128k',
        '-y',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def convert_video(input_path, output_path, resolution='720p', format='mp4'):
    """Convert video to different format/resolution"""
    # Map resolution to height
    height_map = {
        '480p': '480',
        '720p': '720',
        '1080p': '1080'
    }
    height = height_map.get(resolution, '720')
    
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf', f'scale=-2:{height}',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-b:v', '2M',
        '-b:a', '192k',
        '-y',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def process_video_job(job_data):
    """Main video processing function"""
    job_id = job_data['job_id']
    file_id = job_data['file_id']
    bucket = job_data['bucket']
    key = job_data['key']
    job_type = job_data['type']
    params = job_data.get('params', {})
    
    logger.info(f"Processing video job {job_id} of type {job_type}")
    
    db = SessionLocal()
    
    try:
        # Update job status to running
        update_job_status(db, job_id, JobStatus.RUNNING)
        
        # Get original filename
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            raise Exception(f"File {file_id} not found")
        
        original_name = file.original_name
        base_name = Path(original_name).stem
        original_ext = Path(original_name).suffix
        
        # Download file from MinIO
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix) as tmp_input:
            input_path = tmp_input.name
            s3_client.download_file(bucket, key, input_path)
        
        # Process based on type
        output_path = None
        output_bucket = None
        output_key = None
        output_filename = None
        
        if job_type == 'video_thumbnail':
            time = params.get('time', '00:00:01')
            
            output_path = tempfile.mktemp(suffix='.jpg')
            create_video_thumbnail(input_path, output_path, time)
            
            output_bucket = 'thumbnails'
            output_filename = f"{base_name}_thumb.jpg"
            output_key = f"{file_id}_video_thumb.jpg"
            
        elif job_type == 'video_preview':
            duration = params.get('duration', 10)
            
            output_path = tempfile.mktemp(suffix='.mp4')
            create_video_preview(input_path, output_path, duration)
            
            output_bucket = 'processed'
            output_filename = f"{base_name}_preview.mp4"
            output_key = f"{file_id}_preview.mp4"
            
        elif job_type == 'video_convert':
            resolution = params.get('resolution', '720p')
            format = params.get('format', 'mp4')
            
            output_path = tempfile.mktemp(suffix=f'.{format}')
            convert_video(input_path, output_path, resolution, format)
            
            output_bucket = 'processed'
            output_filename = f"{base_name}_converted_{resolution}.{format}"
            output_key = f"{file_id}_converted_{resolution}.{format}"
        
        # Upload result to MinIO
        if output_path and output_bucket and output_key:
            s3_client.upload_file(output_path, output_bucket, output_key)
            
            # Get file size
            output_size = os.path.getsize(output_path)
            
            # Create File record for output
            result_file_id = str(uuid.uuid4())
            
            # Determine mime type
            mime_type = 'video/mp4' if job_type != 'video_thumbnail' else 'image/jpeg'
            
            file_query = f"""
                INSERT INTO files (id, owner_id, original_name, storage_bucket, storage_key, 
                                   size_bytes, mime_type, status, is_processed_output, parent_file_id, created_at)
                SELECT '{result_file_id}', owner_id, '{output_filename}', '{output_bucket}', '{output_key}',
                       {output_size}, '{mime_type}', 'READY', true, '{file_id}', NOW()
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
        update_job_status(db, job_id, JobStatus.FAILED, error_message=str(e))
    finally:
        db.close()


def callback(ch, method, properties, body):
    """RabbitMQ message callback"""
    try:
        message = json.loads(body)
        logger.info(f"Received message: {message.get('job_id')}")
        
        process_video_job(message)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error in callback: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main worker function"""
    logger.info(f"Starting video processor worker, connecting to {RABBITMQ_HOST}")
    
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
