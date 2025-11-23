from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import tempfile
import os
from app.db.database import get_db
from app.db.models import File, Job, Pipeline, FileStatus, JobType, JobStatus
from app.schemas.file import (
    FileUploadInit, FileUploadInitResponse, FileUploadComplete,
    FileResponse, FileDetailResponse, PipelineCreate
)
from app.core.security import get_current_user_id
from app.services.minio import minio_service
from app.services.rabbitmq import rabbitmq_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    pipeline_actions: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Upload file directly to backend"""
    # Generate file ID and storage key
    file_id = uuid.uuid4()
    storage_key = f"{user_id}/{file_id}_{file.filename}"
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Upload to MinIO
        minio_service.upload_file(temp_path, 'raw', storage_key)
        
        # Create file record
        new_file = File(
            id=file_id,
            owner_id=user_id,
            original_name=file.filename,
            storage_bucket='raw',
            storage_key=storage_key,
            size_bytes=len(content),
            mime_type=file.content_type or 'application/octet-stream',
            status=FileStatus.UPLOADED
        )
        db.add(new_file)
        db.flush()
        
        # Parse pipeline actions
        actions = []
        if pipeline_actions:
            import json
            actions = json.loads(pipeline_actions)
        
        # Create pipeline if actions specified
        if actions:
            pipeline = Pipeline(
                file_id=new_file.id,
                name="Auto Pipeline",
                steps=[{"type": action} for action in actions]
            )
            db.add(pipeline)
            db.flush()
            
            # Create jobs for each action
            for action in actions:
                job = Job(
                    file_id=new_file.id,
                    pipeline_id=pipeline.id,
                    type=JobType(action),
                    status=JobStatus.QUEUED,
                    params={}
                )
                db.add(job)
                db.flush()
                
                # Publish job to RabbitMQ
                queue = rabbitmq_service.get_queue_for_job_type(action)
                message = {
                    "job_id": str(job.id),
                    "file_id": str(new_file.id),
                    "bucket": new_file.storage_bucket,
                    "key": new_file.storage_key,
                    "type": action,
                    "params": {}
                }
                rabbitmq_service.publish_job(queue, message)
            
            new_file.status = FileStatus.PROCESSING
        
        db.commit()
        
        return {"status": "success", "file_id": str(new_file.id)}
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.get("", response_model=List[FileResponse])
async def list_files(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """List all files for current user"""
    files = db.query(File).filter(
        File.owner_id == user_id,
        File.is_processed_output == False
    ).order_by(File.created_at.desc()).all()
    
    # Add download URLs
    for file in files:
        if file.status in [FileStatus.UPLOADED, FileStatus.READY]:
            file.download_url = minio_service.generate_download_url(
                file.storage_bucket,
                file.storage_key
            )
    
    return files


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get file details with jobs and processed outputs"""
    from sqlalchemy.orm import joinedload
    
    file = db.query(File).options(
        joinedload(File.file_metadata)
    ).filter(
        File.id == file_id,
        File.owner_id == user_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Get processed outputs
    processed_files = db.query(File).filter(
        File.parent_file_id == file_id,
        File.is_processed_output == True
    ).all()
    
    # Get AI tags from metadata if available
    ai_tags = []
    print(f"DEBUG - file.file_metadata: {file.file_metadata}")
    if file.file_metadata:
        print(f"DEBUG - file.file_metadata.ai_tags: {file.file_metadata.ai_tags}")
        if file.file_metadata.ai_tags:
            ai_tags = file.file_metadata.ai_tags
    print(f"DEBUG - Final ai_tags: {ai_tags}")
    
    # Build response with explicit fields
    from datetime import datetime
    
    # Serialize jobs
    jobs_data = []
    for job in file.jobs:
        jobs_data.append({
            "id": str(job.id),
            "file_id": str(job.file_id),
            "type": job.type.value if hasattr(job.type, 'value') else job.type,
            "status": job.status.value if hasattr(job.status, 'value') else job.status,
            "result_file_id": str(job.result_file_id) if job.result_file_id else None,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if isinstance(job.created_at, datetime) else job.created_at,
            "updated_at": job.updated_at.isoformat() if isinstance(job.updated_at, datetime) else job.updated_at
        })
    
    # Serialize processed outputs
    processed_data = []
    for pf in processed_files:
        processed_data.append({
            "id": str(pf.id),
            "original_name": pf.original_name,
            "storage_key": pf.storage_key,
            "size_bytes": pf.size_bytes,
            "mime_type": pf.mime_type,
            "status": pf.status.value if hasattr(pf.status, 'value') else pf.status,
            "created_at": pf.created_at.isoformat() if isinstance(pf.created_at, datetime) else pf.created_at
        })
    
    return {
        "id": str(file.id),
        "owner_id": str(file.owner_id),
        "original_name": file.original_name,
        "storage_bucket": file.storage_bucket,
        "storage_key": file.storage_key,
        "size_bytes": file.size_bytes,
        "mime_type": file.mime_type,
        "status": file.status.value if hasattr(file.status, 'value') else file.status,
        "created_at": file.created_at.isoformat() if isinstance(file.created_at, datetime) else file.created_at,
        "is_processed_output": file.is_processed_output,
        "parent_file_id": str(file.parent_file_id) if file.parent_file_id else None,
        "jobs": jobs_data,
        "processed_outputs": processed_data,
        "ai_tags": ai_tags
    }


@router.get("/{file_id}/jobs", response_model=List)
async def get_file_jobs(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all jobs for a file"""
    from app.schemas.file import JobResponse
    
    # Verify file ownership
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == user_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    jobs = db.query(Job).filter(Job.file_id == file_id).order_by(Job.created_at).all()
    return jobs


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Download file directly through backend"""
    from fastapi.responses import StreamingResponse
    
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == user_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Get file from MinIO
    try:
        obj = minio_service.get_object(file.storage_bucket, file.storage_key)
        
        return StreamingResponse(
            obj['Body'],
            media_type=file.mime_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{file.original_name}"'
            }
        )
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete a file"""
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == user_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Get processed output files
    processed_files = db.query(File).filter(File.parent_file_id == file_id).all()
    processed_file_ids = [pf.id for pf in processed_files]
    
    # Delete all jobs associated with this file (both file_id and result_file_id)
    jobs = db.query(Job).filter(
        (Job.file_id == file_id) | (Job.result_file_id.in_(processed_file_ids))
    ).all()
    for job in jobs:
        db.delete(job)
    db.commit()  # Commit job deletions first
    
    # Now delete processed output files
    for pf in processed_files:
        try:
            minio_service.delete_file(pf.storage_bucket, pf.storage_key)
        except Exception as e:
            logger.error(f"Error deleting processed file from MinIO: {e}")
        db.delete(pf)
    db.commit()  # Commit processed file deletions
    
    # Delete from MinIO
    try:
        minio_service.delete_file(file.storage_bucket, file.storage_key)
    except Exception as e:
        logger.error(f"Error deleting file from MinIO: {e}")
    
    # Delete metadata if exists
    if file.file_metadata:
        db.delete(file.file_metadata)
    
    # Delete from database
    db.delete(file)
    db.commit()
    
    return {"status": "deleted"}
