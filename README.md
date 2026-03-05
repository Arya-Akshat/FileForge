# FileForge

A **production-grade** cloud-based file processing platform demonstrating distributed systems, async processing, and microservices architecture. Built as a learning project showcasing real-world patterns used at companies like Dropbox, Google Photos, and Netflix.


---

## 🏗️ System Architecture

### High-Level Overview
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FILEFORGE ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────┐     ┌──────────────────────────────────────────────────┐    │
│    │  React   │────▶│                   NGINX                          │    │
│    │ Frontend │◀────│              (Reverse Proxy)                     │    │
│    └──────────┘     │         Load Balancing, SSL Termination          │    │
│                     └───────────────────┬──────────────────────────────┘    │
│                                         │                                    │
│                                         ▼                                    │
│                     ┌──────────────────────────────────────────────────┐    │
│                     │              FastAPI Backend                      │    │
│                     │     • JWT Auth  • File Management  • Job API     │    │
│                     │     • /health endpoint for observability         │    │
│                     └─────────┬──────────────┬──────────────┬──────────┘    │
│                               │              │              │               │
│              ┌────────────────┼──────────────┼──────────────┼────────────┐  │
│              │                ▼              ▼              ▼            │  │
│              │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │  │
│              │  │  PostgreSQL  │  │    MinIO     │  │    RabbitMQ      │ │  │
│              │  │  (Metadata)  │  │   (Files)    │  │   (Job Queue)    │ │  │
│              │  │              │  │              │  │                  │ │  │
│              │  │ • Users      │  │ • raw/       │  │ • image_queue    │ │  │
│              │  │ • Files      │  │ • processed/ │  │ • video_queue    │ │  │
│              │  │ • Jobs       │  │ • thumbnails/│  │ • security_queue │ │  │
│              │  │              │  │ • encrypted/ │  │ • ai_queue       │ │  │
│              │  └──────────────┘  └──────────────┘  └────────┬─────────┘ │  │
│              │           DATA LAYER                          │           │  │
│              └───────────────────────────────────────────────┼───────────┘  │
│                                                              │              │
│                                                              ▼              │
│     ┌────────────────────────────────────────────────────────────────────┐  │
│     │                     WORKER POOL (Microservices)                    │  │
│     │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │  │
│     │  │   Image     │ │   Video     │ │  Security   │ │     AI      │  │  │
│     │  │  Processor  │ │  Processor  │ │   Worker    │ │   Tagger    │  │  │
│     │  │             │ │             │ │             │ │             │  │  │
│     │  │ • Thumbnail │ │ • Transcode │ │ • ClamAV    │ │ • Gemini    │  │  │
│     │  │ • Convert   │ │ • Preview   │ │ • Encrypt   │ │ • Auto-tag  │  │  │
│     │  │ • Compress  │ │ • Thumbnail │ │ • Decrypt   │ │ • Analyze   │  │  │
│     │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │  │
│     │         Horizontally Scalable: docker-compose up --scale          │  │
│     └────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram
```
┌────────────────────────────────────────────────────────────────────────────┐
│                           FILE PROCESSING FLOW                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. UPLOAD PHASE                                                            │
│  ┌──────┐    POST /init-upload     ┌─────────┐    Presigned URL   ┌──────┐ │
│  │Client│ ─────────────────────▶   │ Backend │ ────────────────▶  │MinIO │ │
│  └──────┘                          └─────────┘                    └──────┘ │
│      │                                                                │     │
│      │         PUT (direct upload using presigned URL)                │     │
│      └────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  2. PROCESSING PHASE                                                        │
│  ┌──────┐  POST /complete-upload   ┌─────────┐   Publish Job   ┌─────────┐ │
│  │Client│ ─────────────────────▶   │ Backend │ ──────────────▶ │RabbitMQ │ │
│  └──────┘                          └─────────┘                 └────┬────┘ │
│                                         │                           │      │
│                                    Create Job                  Consume     │
│                                    Record (DB)                      │      │
│                                         │                           ▼      │
│                                         │                    ┌──────────┐  │
│                                         └──────────────────▶ │  Worker  │  │
│                                                              └────┬─────┘  │
│  3. COMPLETION PHASE                                              │        │
│                                    ┌─────────┐  Update Status     │        │
│                              ┌──── │   DB    │ ◀──────────────────┤        │
│                              │     └─────────┘                    │        │
│                              │                                    ▼        │
│                              │     ┌─────────┐   Upload Result  ┌──────┐   │
│                              └───▶ │ Backend │ ◀──────────────  │MinIO │   │
│                                    └─────────┘                  └──────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Implementation Status

### ✅ Implemented (Production-Ready)

| Feature | Description | Key Files |
|---------|-------------|-----------|
| **JWT Authentication** | Secure user registration/login with bcrypt password hashing | `backend/app/core/security.py` |
| **Presigned URL Uploads** | Direct-to-storage uploads bypassing backend (like S3) | `backend/app/services/minio.py` |
| **Async Job Queue** | RabbitMQ-based distributed job processing | `backend/app/services/rabbitmq.py` |
| **Image Processing** | Thumbnail, format conversion, compression via Pillow | `workers/image_processor/` |
| **Video Processing** | Transcode, preview clips, thumbnails via FFmpeg | `workers/video_processor/` |
| **Virus Scanning** | ClamAV integration for malware detection | `workers/security/` |
| **File Encryption** | AES encryption/decryption at rest | `workers/security/` |
| **AI Tagging** | Google Gemini-powered auto-tagging | `workers/ai_tagger/` |
| **Database Migrations** | Alembic for schema versioning | `backend/alembic/` |
| **Health Endpoint** | `/health` for container orchestration | `backend/app/main.py` |
| **React Dashboard** | Modern UI with Tailwind + shadcn/ui | `frontend/src/` |

### 🚧 Planned (Not Yet Implemented)

| Feature | Priority | Complexity | Notes |
|---------|----------|------------|-------|
| WebSocket job updates | High | Medium | Replace polling with push notifications |
| Rate limiting | High | Low | Use Redis + sliding window algorithm |
| File sharing/permissions | Medium | Medium | ACL system for shared access |
| Batch operations | Medium | Low | Bulk upload/process API |
| Retry with exponential backoff | High | Low | Currently single-attempt processing |
| Dead letter queue | High | Low | Failed jobs need DLQ handling |
| Distributed tracing | Medium | Medium | Jaeger/Zipkin integration |
| CDN integration | Low | Medium | CloudFront/Cloudflare for static assets |

---

## ⚠️ Failure Scenarios & Handling

### Current Failure Handling

| Failure Type | Current Behavior | Impact | Improvement Needed |
|-------------|------------------|--------|-------------------|
| **Worker crashes mid-job** | Job stays in RUNNING state | Orphaned jobs | Add heartbeat + timeout mechanism |
| **RabbitMQ unavailable** | Backend returns 500 | Uploads fail | Add circuit breaker pattern |
| **MinIO unavailable** | Presigned URL generation fails | Upload blocked | Graceful degradation |
| **Database unavailable** | All requests fail | System down | Connection pooling + retries |
| **Job processing fails** | Status set to FAILED | User informed | Retry queue + DLQ |

### What Happens When a Worker Crashes?

```
Current Flow (Problem):
1. Worker picks up job from queue
2. Worker ACKs message immediately ❌
3. Worker crashes during processing
4. Job stuck in RUNNING forever
5. No automatic retry

Ideal Flow (Planned):
1. Worker picks up job
2. Worker processes job
3. Worker ACKs only AFTER success ✅
4. If crash: RabbitMQ redelivers to another worker
5. Max retries → Dead Letter Queue
```

---

## 🔄 Trade-offs & Design Decisions

### Why RabbitMQ over Kafka/Redis?

| Criteria | RabbitMQ ✅ | Kafka | Redis (Queue) |
|----------|-----------|-------|---------------|
| **Use Case Fit** | Task queues, job processing | Event streaming, logs | Lightweight caching |
| **Message Acknowledgment** | Built-in, per-message | Offset-based | Limited |
| **Delivery Guarantee** | At-least-once ✅ | At-least-once | At-most-once |
| **Learning Curve** | Moderate | Steep | Easy |
| **Ordering** | Per-queue FIFO | Per-partition | FIFO |
| **Scalability** | Good for our scale | Overkill | Limited |

**Decision**: RabbitMQ is the right choice for job queues with individual ACKs and retry semantics.

### Why MinIO over Direct Filesystem?

| Criteria | MinIO ✅ | Filesystem |
|----------|---------|------------|
| **S3 Compatibility** | Full API compatibility | None |
| **Presigned URLs** | Built-in | Manual implementation |
| **Horizontal Scaling** | Distributed mode | NFS/shared storage |
| **Cloud Migration** | Swap to S3 easily | Major refactor |
| **Bucket Policies** | Native | Manual |

**Decision**: MinIO provides S3-compatible storage that makes cloud migration trivial.

### Sync vs Async Processing

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Sync** | Simple, immediate response | Blocks request, timeout risk | Small files, fast operations |
| **Async ✅** | Non-blocking, scalable | Complex, eventual consistency | Large files, slow processing |

**Decision**: Async processing is essential for video transcoding (can take minutes) and AI tagging (API latency).

### Monolith vs Microservices Workers

| Approach | Pros | Cons | Our Choice |
|----------|------|------|------------|
| **Single Worker** | Simple deployment | Can't scale independently | ❌ |
| **Per-Type Workers ✅** | Independent scaling, isolation | More containers | ✅ |

**Decision**: Separate workers allow scaling video processors independently (expensive) from image processors (cheap).

---

## 🔍 Observability

### Health Check Endpoint

```bash
GET /health
# Response: {"status": "healthy"}
```

Used by Docker Compose healthchecks and container orchestration.

### Structured Logging

All workers use structured logging with job_id for traceability:
```
2024-01-15 10:30:45 - image_processor - INFO - Processing job abc-123 of type thumbnail
2024-01-15 10:30:47 - image_processor - INFO - Job abc-123 completed successfully
```

### Monitoring Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Liveness probe |
| RabbitMQ `:15672` | Queue metrics, message rates |
| MinIO `:9001` | Storage metrics, bucket stats |
| PostgreSQL | Connection pool stats via pg_stat |

---

## 🚀 Features

### Core Features
- **User Authentication**: JWT-based secure authentication
- **File Storage**: S3-compatible object storage with MinIO
- **Async Processing**: Job queue system with RabbitMQ

### Processing Capabilities

#### Image Processing
- Format conversion (JPEG, PNG, WEBP)
- Thumbnail generation
- Image compression
- Resolution adjustment

#### Video Processing
- Video format conversion
- Thumbnail extraction
- Preview clip generation
- Resolution transcoding (480p, 720p, 1080p)

#### Security Features
- Virus scanning (ClamAV)
- File encryption/decryption (AES)
- Secure presigned URLs

#### AI Features
- Auto-tagging with Google Gemini
- Content analysis
- Metadata extraction

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/Arya-Akshat/FileForge.git
cd FileForge

# (Optional) Add your Gemini API key to backend/.env for AI features
# GEMINI_API_KEY=your_key_here
```

### 2. Start All Services

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

This will start:
- **Backend API**: http://localhost:80/api
- **MinIO Console**: http://localhost:9001 (minio/minio123)
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **API Documentation**: http://localhost:80/docs
- **PostgreSQL**: localhost:5432

### 3. Initialize Database

The backend automatically runs migrations on startup, but if you need to run them manually:

```bash
# Enter backend container
docker-compose exec backend bash

# Run migrations
alembic upgrade head
```

## 📝 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost/docs
- **ReDoc**: http://localhost/redoc
- **OpenAPI JSON**: http://localhost/openapi.json

### Key Endpoints

#### Authentication
```
POST /api/auth/register    - Register new user
POST /api/auth/login       - Login and get JWT token
GET  /api/auth/me          - Get current user info
```

#### Files
```
POST   /api/files/init-upload      - Initialize file upload
POST   /api/files/complete-upload  - Complete upload & trigger processing
GET    /api/files                  - List all user files
GET    /api/files/{id}             - Get file details
GET    /api/files/{id}/jobs        - Get file processing jobs
DELETE /api/files/{id}             - Delete file
```

#### Jobs
```
GET /api/jobs/{id}  - Get job details
GET /api/jobs       - List all jobs
```

## 🔧 Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Create Database Migration

```bash
cd backend

# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Worker Development

Each worker can be run independently:

```bash
cd workers/image_processor

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://app:app@localhost:5432/appdb
export MINIO_ENDPOINT=localhost:9000
export RABBITMQ_HOST=localhost

# Run worker
python worker.py
```

## 🔄 Processing Pipeline Example

### 1. Upload File with Processing

```bash
# Register and login
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
# Save the token from response

# Initialize upload
curl -X POST http://localhost/api/files/init-upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "photo.jpg",
    "size_bytes": 1048576,
    "mime_type": "image/jpeg"
  }'
# Save file_id and upload_url from response

# Upload file to MinIO
curl -X PUT "UPLOAD_URL" \
  --upload-file photo.jpg

# Complete upload with processing options
curl -X POST http://localhost/api/files/complete-upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "FILE_ID",
    "pipeline_actions": ["thumbnail", "image_compress", "ai_tag"]
  }'
```

### 2. Monitor Job Progress

```bash
# Get file details with jobs
curl http://localhost/api/files/FILE_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check specific job
curl http://localhost/api/jobs/JOB_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f image_worker
docker-compose logs -f video_worker

# With timestamps
docker-compose logs -f --timestamps backend
```

### Service Health

```bash
# Check service status
docker-compose ps

# Restart specific service
docker-compose restart backend
docker-compose restart image_worker

# Scale workers
docker-compose up -d --scale image_worker=3
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U app -d appdb

# Common queries
SELECT * FROM users;
SELECT * FROM files ORDER BY created_at DESC LIMIT 10;
SELECT * FROM jobs WHERE status = 'error';
```

### MinIO Access

1. Open http://localhost:9001
2. Login with: `minio` / `minio123`
3. Browse buckets: `raw`, `processed`, `thumbnails`, `encrypted`

### RabbitMQ Management

1. Open http://localhost:15672
2. Login with: `guest` / `guest`
3. View queues, messages, and connections

## 🗂️ Project Structure

```
CloudComputing/
├── backend/                 # FastAPI backend
│   ├── alembic/            # Database migrations
│   ├── app/
│   │   ├── api/            # API routes
│   │   │   ├── auth.py     # Authentication endpoints
│   │   │   ├── files.py    # File management
│   │   │   └── jobs.py     # Job management
│   │   ├── core/           # Core functionality
│   │   │   ├── config.py   # Settings
│   │   │   └── security.py # Auth & JWT
│   │   ├── db/             # Database
│   │   │   ├── models.py   # SQLAlchemy models
│   │   │   └── database.py # DB connection
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   │   ├── minio.py    # MinIO client
│   │   │   └── rabbitmq.py # RabbitMQ client
│   │   └── main.py         # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
│
├── workers/                # Processing workers
│   ├── image_processor/    # Image processing
│   ├── video_processor/    # Video processing
│   ├── security/           # Virus scan & encryption
│   └── ai_tagger/          # AI auto-tagging
│
├── nginx/                  # Reverse proxy
│   └── nginx.conf
│
├── docker-compose.yml      # Docker orchestration
└── README.md
```

## 🎯 Processing Job Types

| Job Type | Queue | Description | Output |
|----------|-------|-------------|--------|
| `thumbnail` | image_queue | Generate image thumbnail | thumbnails/ |
| `image_convert` | image_queue | Convert image format | processed/ |
| `image_compress` | image_queue | Compress image | processed/ |
| `video_thumbnail` | video_queue | Extract video frame | thumbnails/ |
| `video_preview` | video_queue | Create short preview | processed/ |
| `video_convert` | video_queue | Transcode video | processed/ |
| `virus_scan` | security_queue | Scan for malware | - |
| `encrypt` | security_queue | Encrypt file | encrypted/ |
| `decrypt` | security_queue | Decrypt file | processed/ |
| `ai_tag` | ai_queue | Generate AI tags | metadata |

## 🔐 Security Considerations

### Production Deployment

1. **Change Default Credentials**
   ```bash
   # In docker-compose.yml and .env
   - Use strong SECRET_KEY
   - Change MinIO credentials
   - Change PostgreSQL password
   - Use secure RabbitMQ credentials
   ```

2. **Enable HTTPS**
   - Add SSL certificates to NGINX
   - Update nginx.conf for HTTPS

3. **Secure MinIO**
   - Enable TLS
   - Use IAM policies
   - Rotate access keys

4. **Environment Variables**
   - Never commit .env files
   - Use secrets management (Docker Secrets, Kubernetes Secrets)

5. **Database**
   - Enable SSL connections
   - Use connection pooling
   - Regular backups

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Database not ready: Wait for PostgreSQL healthcheck
# - Port conflict: Change port in docker-compose.yml
# - Migration error: Check alembic/versions/
```

### Workers not processing jobs

```bash
# Check RabbitMQ
docker-compose logs rabbitmq

# Check worker logs
docker-compose logs image_worker

# Verify queue connections
# Visit http://localhost:15672 and check Queues tab
```

### MinIO connection issues

```bash
# Check MinIO status
docker-compose logs minio

# Verify buckets exist
# Visit http://localhost:9001 and check buckets: raw, processed, thumbnails, encrypted
```

### Database migration issues

```bash
# Reset database (⚠️ destroys all data)
docker-compose down -v
docker-compose up -d db
docker-compose exec backend alembic upgrade head
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale workers for increased throughput
docker-compose up -d --scale image_worker=5
docker-compose up -d --scale video_worker=3

# Scale backend for more API capacity
docker-compose up -d --scale backend=3
```

### Add Load Balancer

Update nginx.conf:
```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

## 🚢 Deployment

### Single Server Deployment

```bash
# On production server
git clone <your-repo>
cd CloudComputing

# Configure production settings
cp .env.example .env
# Edit .env with production values

# Start services
docker-compose -f docker-compose.yml up -d
```

### Kubernetes Deployment

Convert docker-compose to Kubernetes manifests:
```bash
# Use kompose (optional)
kompose convert -f docker-compose.yml
```

## 📚 Technology Stack

- **Backend**: FastAPI, Python 3.11
- **Database**: PostgreSQL 16
- **Object Storage**: MinIO (S3-compatible)
- **Message Queue**: RabbitMQ
- **Reverse Proxy**: NGINX
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Auth**: JWT (python-jose)
- **Image Processing**: Pillow
- **Video Processing**: FFmpeg
- **Virus Scanning**: ClamAV
- **AI**: Google Gemini API
- **Containerization**: Docker

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - feel free to use this project for learning or commercial purposes.

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [MinIO Documentation](https://min.io/docs/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)

## 💡 Next Steps / Roadmap

### Phase 1 (Current)
- ✅ Basic file upload/download
- ✅ User authentication
- ✅ Image processing workers
- ✅ Video processing workers
- ✅ Security workers
- ✅ AI tagging

### Phase 2 (Future)
- [ ] Real-time job status updates (WebSockets)
- [ ] File sharing & permissions
- [ ] Batch operations
- [ ] Advanced search & filtering
- [ ] Usage analytics dashboard
- [ ] Rate limiting & quotas

### Phase 3 (Advanced)
- [ ] Multi-region deployment
- [ ] CDN integration
- [ ] Advanced AI features
- [ ] Custom processing pipelines
- [ ] Webhook notifications
- [ ] API rate limiting

---

**Built with ❤️ as a learning project for Cloud Computing**
