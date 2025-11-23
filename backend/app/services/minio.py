from boto3 import client
from botocore.client import Config
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MinIOService:
    def __init__(self):
        self.client = client(
            's3',
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}" if not settings.MINIO_SECURE else f"https://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """Create required buckets if they don't exist"""
        buckets = ['raw', 'processed', 'thumbnails', 'temp', 'encrypted']
        for bucket in buckets:
            try:
                self.client.head_bucket(Bucket=bucket)
            except:
                logger.info(f"Creating bucket: {bucket}")
                self.client.create_bucket(Bucket=bucket)
    
    def generate_upload_url(self, bucket: str, key: str, expires_in: int = 3600):
        """Generate a presigned URL for uploading a file"""
        url = self.client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in
        )
        # Replace MinIO URL with NGINX proxy URL for browser access
        url = url.replace('http://minio:9000/', 'http://localhost/minio/')
        url = url.replace('minio:9000/', 'localhost/minio/')
        return url
    
    def generate_download_url(self, bucket: str, key: str, expires_in: int = 3600):
        """Generate a presigned URL for downloading a file"""
        url = self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in
        )
        # Replace MinIO URL with NGINX proxy URL for browser access
        url = url.replace('http://minio:9000/', 'http://localhost/minio/')
        url = url.replace('minio:9000/', 'localhost/minio/')
        return url
    
    def upload_file(self, file_path: str, bucket: str, key: str):
        """Upload a file directly"""
        self.client.upload_file(file_path, bucket, key)
    
    def download_file(self, bucket: str, key: str, file_path: str):
        """Download a file directly"""
        self.client.download_file(bucket, key, file_path)
    
    def delete_file(self, bucket: str, key: str):
        """Delete a file"""
        self.client.delete_object(Bucket=bucket, Key=key)
    
    def get_object(self, bucket: str, key: str):
        """Get object from MinIO"""
        return self.client.get_object(Bucket=bucket, Key=key)


minio_service = MinIOService()
