# FileForge

A powerful cloud-based file processing platform with intelligent automation capabilities. Upload files and automatically process them with image conversion, video processing, AI tagging, virus scanning, encryption, and more.

## 🏗️ Architecture

```
Clients (Browser/API)
        ↓
    NGINX (Reverse Proxy)
        ↓
    Backend API (FastAPI)
   ↙️    ↓    ↘️
MinIO  Postgres  RabbitMQ
              ↓
        Worker Microservices
        - Image Processor
        - Video Processor
        - Security Worker
        - AI Tagger
```

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
