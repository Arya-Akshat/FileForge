from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import Job
from app.schemas.file import JobResponse
from app.core.security import get_current_user_id

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get job details"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify ownership through file
    if str(job.file.owner_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job"
        )
    
    return job


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """List all jobs for current user"""
    jobs = db.query(Job).join(Job.file).filter(
        Job.file.has(owner_id=user_id)
    ).order_by(Job.created_at.desc()).all()
    
    return jobs
