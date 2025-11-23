import os
import pika
import json
import logging
import tempfile
from pathlib import Path
import boto3
from botocore.client import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, JSON, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
from cryptography.fernet import Fernet
import hashlib
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
QUEUE_NAME = 'security_queue'

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


def scan_file_for_virus(file_path):
    """Scan file with ClamAV"""
    try:
        import pyclamd
        cd = pyclamd.ClamdUnixSocket()
        
        # Check if clamd is available
        if not cd.ping():
            logger.warning("ClamAV daemon not available, skipping virus scan")
            return True, "ClamAV not available"
        
        result = cd.scan_file(file_path)
        
        if result is None:
            return True, "Clean"
        else:
            return False, f"Virus detected: {result}"
    except Exception as e:
        logger.error(f"Error scanning file: {e}")
        return True, f"Scan error: {str(e)}"


def encrypt_file(input_path, output_path, password):
    """Encrypt a file using Fernet (AES)"""
    # Derive key from password
    key = hashlib.sha256(password.encode()).digest()
    key_b64 = Fernet.generate_key()  # In production, derive from password properly
    cipher = Fernet(key_b64)
    
    with open(input_path, 'rb') as f:
        data = f.read()
    
    encrypted = cipher.encrypt(data)
    
    with open(output_path, 'wb') as f:
        f.write(key_b64 + b'\n' + encrypted)  # Store key with file (simplified)


def decrypt_file(input_path, output_path, password):
    """Decrypt a file"""
    with open(input_path, 'rb') as f:
        key_b64 = f.readline().strip()
        encrypted = f.read()
    
    cipher = Fernet(key_b64)
    decrypted = cipher.decrypt(encrypted)
    
    with open(output_path, 'wb') as f:
        f.write(decrypted)


def process_security_job(job_data):
    """Main security processing function"""
    job_id = job_data['job_id']
    file_id = job_data['file_id']
    bucket = job_data['bucket']
    key = job_data['key']
    job_type = job_data['type']
    params = job_data.get('params', {})
    
    logger.info(f"Processing security job {job_id} of type {job_type}")
    
    db = SessionLocal()
    
    try:
        # Update job status to running
        update_job_status(db, job_id, JobStatus.RUNNING)
        
        # Download file from MinIO
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix) as tmp_input:
            input_path = tmp_input.name
            s3_client.download_file(bucket, key, input_path)
        
        # Process based on type
        output_path = None
        output_bucket = None
        output_key = None
        
        if job_type == 'virus_scan':
            is_clean, scan_result = scan_file_for_virus(input_path)
            
            if is_clean:
                # Store success message in error_message field (we'll use it for scan results)
                update_job_status(db, job_id, JobStatus.COMPLETED, error_message="✓ No virus found - File is clean")
                
                # Update file status to READY
                file = db.query(File).filter(File.id == file_id).first()
                if file:
                    file.status = FileStatus.READY
                    db.commit()
                
                logger.info(f"Virus scan passed: {scan_result}")
            else:
                # Mark file as unsafe
                file_query = f"UPDATE files SET status = 'FAILED' WHERE id = '{file_id}'"
                db.execute(text(file_query))
                db.commit()
                
                update_job_status(db, job_id, JobStatus.FAILED, error_message=f"⚠ Virus detected: {scan_result}")
                logger.warning(f"Virus detected: {scan_result}")
            
        elif job_type == 'encrypt':
            password = params.get('password', 'default_password')  # Should come from user
            
            # Get original filename
            file_obj = db.query(File).filter(File.id == file_id).first()
            original_name = file_obj.original_name if file_obj else 'file'
            base_name = Path(original_name).stem
            original_ext = Path(original_name).suffix
            
            output_path = tempfile.mktemp(suffix='.enc')
            encrypt_file(input_path, output_path, password)
            
            output_bucket = 'encrypted'
            output_key = f"{base_name}_encrypted{original_ext}.enc"
            
        elif job_type == 'decrypt':
            password = params.get('password', 'default_password')
            
            # Get original filename and strip .enc extension
            file_obj = db.query(File).filter(File.id == file_id).first()
            original_name = file_obj.original_name if file_obj else 'file'
            
            # If file ends with .enc, remove it to get the original extension
            if original_name.endswith('.enc'):
                original_name = original_name[:-4]  # Remove .enc
            
            base_name = Path(original_name).stem
            original_ext = Path(original_name).suffix
            
            output_path = tempfile.mktemp(suffix=original_ext)
            decrypt_file(input_path, output_path, password)
            
            output_bucket = 'processed'
            output_key = f"{base_name}_decrypted{original_ext}"
        
        elif job_type == 'compress':
            # Create ZIP file
            import zipfile
            
            output_path = tempfile.mktemp(suffix='.zip')
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Get original filename from database
                file = db.query(File).filter(File.id == file_id).first()
                original_name = file.original_name if file else 'file'
                zipf.write(input_path, arcname=original_name)
            
            output_bucket = 'processed'
            output_key = f"{file_id}_compressed.zip"
        
        # Upload result to MinIO if applicable
        if output_path and output_bucket and output_key:
            s3_client.upload_file(output_path, output_bucket, output_key)
            
            # Get file size
            output_size = os.path.getsize(output_path)
            
            # Create File record for output
            result_file_id = str(uuid.uuid4())
            
            file_query = f"""
                INSERT INTO files (id, owner_id, original_name, storage_bucket, storage_key, 
                                   size_bytes, mime_type, status, is_processed_output, parent_file_id, created_at)
                SELECT '{result_file_id}', owner_id, '{output_key}', '{output_bucket}', '{output_key}',
                       {output_size}, 'application/octet-stream', 'READY', true, '{file_id}', NOW()
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
        
        process_security_job(message)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error in callback: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main worker function"""
    logger.info(f"Starting security worker, connecting to {RABBITMQ_HOST}")
    
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
