from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, files, jobs
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="FileForge: Powerful file processing platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])


@app.get("/")
async def root():
    return {"message": "FileForge API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
