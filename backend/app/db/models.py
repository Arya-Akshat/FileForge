import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, JSON, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base


class FileStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobType(str, enum.Enum):
    # Image processing
    IMAGE_CONVERT = "image_convert"
    THUMBNAIL = "thumbnail"
    IMAGE_COMPRESS = "image_compress"
    
    # Video processing
    VIDEO_CONVERT = "video_convert"
    VIDEO_PREVIEW = "video_preview"
    VIDEO_THUMBNAIL = "video_thumbnail"
    
    # Generic processing
    COMPRESS = "compress"
    METADATA = "metadata"
    
    # Security
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    VIRUS_SCAN = "virus_scan"
    
    # AI
    AI_TAG = "ai_tag"


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_name = Column(String, nullable=False)
    storage_bucket = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String)
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADED)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed_output = Column(Boolean, default=False)
    parent_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="files")
    jobs = relationship("Job", back_populates="file", foreign_keys="Job.file_id", cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="file", cascade="all, delete-orphan")
    file_metadata = relationship("FileMetadata", back_populates="file", uselist=False, cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=True)
    type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    result_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    params = Column(JSON, default={})
    
    # Relationships
    file = relationship("File", back_populates="jobs", foreign_keys=[file_id])
    result_file = relationship("File", foreign_keys=[result_file_id])
    pipeline = relationship("Pipeline", back_populates="jobs")


class Pipeline(Base):
    __tablename__ = "pipelines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    name = Column(String, nullable=False)
    steps = Column(JSON, nullable=False)  # List of job specs
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    file = relationship("File", back_populates="pipelines")
    jobs = relationship("Job", back_populates="pipeline", cascade="all, delete-orphan")


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False, unique=True)
    exif_data = Column(JSON, nullable=True)
    video_info = Column(JSON, nullable=True)
    ai_tags = Column(JSON, nullable=True)  # List of tags
    custom_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    file = relationship("File", back_populates="file_metadata")
