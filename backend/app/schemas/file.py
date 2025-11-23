from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from app.db.models import FileStatus, JobType, JobStatus


# File Schemas
class FileUploadInit(BaseModel):
    filename: str
    size_bytes: int
    mime_type: Optional[str] = None


class FileUploadInitResponse(BaseModel):
    file_id: UUID
    upload_url: str
    fields: dict


class FileUploadComplete(BaseModel):
    file_id: UUID
    pipeline_actions: List[str] = []  # e.g., ["thumbnail", "compress", "ai_tag"]


class FileResponse(BaseModel):
    id: UUID
    original_name: str
    size_bytes: int
    mime_type: Optional[str]
    status: FileStatus
    created_at: datetime
    download_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class FileDetailResponse(FileResponse):
    jobs: List["JobResponse"] = []
    processed_outputs: List[FileResponse] = []
    ai_tags: Optional[List[str]] = None


# Job Schemas
class JobCreate(BaseModel):
    file_id: UUID
    type: JobType
    params: dict = {}


class JobResponse(BaseModel):
    id: UUID
    file_id: UUID
    type: JobType
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result_file_id: Optional[UUID] = None
    error_message: Optional[str] = None
    params: dict = {}
    
    class Config:
        from_attributes = True


# Pipeline Schemas
class PipelineCreate(BaseModel):
    file_id: UUID
    name: str
    steps: List[dict]  # Each step: {"type": "thumbnail", "params": {...}}


class PipelineResponse(BaseModel):
    id: UUID
    file_id: UUID
    name: str
    steps: List[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Update forward references
FileDetailResponse.model_rebuild()
