# 🚀 Quick Start Guide - FileForge

## ⚡ Get Started in 3 Steps

### 1. Start Everything
```bash
./start.sh
```
This starts all services (API, workers, database, MinIO, RabbitMQ, Frontend).

### 2. Access the Application
Open your browser: **http://localhost**

### 3. Login & Upload
```bash
# Register a user
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Login
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

Or use the web interface at **http://localhost**

---

## 📦 What's Running?

| Service | URL | Credentials |
|---------|-----|-------------|
| **Web App** | http://localhost | Register/Login |
| **API Docs** | http://localhost/docs | - |
| **Backend API** | http://localhost/api | JWT token |
| **MinIO Console** | http://localhost:9001 | minio / minio123 |
| **RabbitMQ** | http://localhost:15672 | guest / guest |
| **PostgreSQL** | localhost:5432 | app / app |

---

## 🛠️ Useful Commands

```bash
# View logs
./logs.sh                    # All services
./logs.sh backend           # Specific service

# Stop everything
./stop.sh

# Check status
docker-compose ps

# Restart a service
docker-compose restart backend

# Scale workers
docker-compose up -d --scale image_worker=3

# Access database
docker-compose exec db psql -U app -d appdb

# View backend logs
docker-compose logs -f backend

# Rebuild after code changes
docker-compose up -d --build backend
```

---

## 🎯 Processing Options

When uploading files, you can request these processing actions:

**Images:**
- `thumbnail` - Generate thumbnails (64x64, 128x128, 256x256)
- `image_convert` - Convert to WebP
- `image_compress` - Reduce file size
- `ai_tag` - Auto-generate tags with Gemini AI

**Videos:**
- `video_thumbnail` - Extract frame as thumbnail
- `video_preview` - Create 10-second preview
- `video_convert` - Transcode to 480p/720p/1080p

**Security:**
- `virus_scan` - Scan with ClamAV
- `encrypt` - AES encryption
- `decrypt` - Decrypt file

---

## 📁 Project Structure

```
FileForge/
├── frontend/         # React frontend (Vite + shadcn/ui)
│   ├── src/
│   │   ├── pages/    # Dashboard, Upload, Results
│   │   ├── components/
│   │   └── lib/      # API client
│
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # REST endpoints
│   │   ├── db/       # Database models
│   │   └── services/ # MinIO, RabbitMQ
│   └── alembic/      # DB migrations
│
├── workers/          # Processing microservices
│   ├── image_processor/
│   ├── video_processor/
│   ├── security/
│   └── ai_tagger/
│
├── nginx/            # Reverse proxy config
└── docker-compose.yml
```

---

## 🔧 Development Mode

```bash
# Setup dev environment
./dev-setup.sh

# Start only infrastructure
docker-compose up -d db minio rabbitmq

# Run backend locally
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

---

## 🐛 Troubleshooting

**Backend won't start?**
```bash
docker-compose logs backend
# Usually: wait 10s for database, or check migrations
```

**Workers not processing?**
```bash
docker-compose logs image_worker
# Check: RabbitMQ connection, queue exists
```

**Can't connect to MinIO?**
```bash
docker-compose restart minio
# Verify buckets at http://localhost:9001
```

**Reset everything:**
```bash
docker-compose down -v  # ⚠️ Deletes all data!
./start.sh
```

---

## 📚 Next Steps

1. **Read the full README**: `README.md`
2. **Try the API examples**: `API_EXAMPLES.md`
3. **Explore API docs**: http://localhost/docs
4. **Monitor jobs**: http://localhost:15672 (RabbitMQ)
5. **Browse files**: http://localhost:9001 (MinIO)

---

## 🎓 Key Concepts

**File Upload Flow:**
1. Init upload → Get presigned URL
2. Upload file to MinIO
3. Complete upload → Trigger processing
4. Workers process → Update job status
5. Download processed files

**Job States:**
- `queued` → Job created, waiting for worker
- `running` → Worker is processing
- `success` → Processing complete
- `error` → Processing failed

**Storage Buckets:**
- `raw` - Original uploads
- `processed` - Processed outputs
- `thumbnails` - Generated thumbnails
- `encrypted` - Encrypted files

---

**Need help?** Check `README.md` for detailed documentation!

**Built with:** React • FastAPI • PostgreSQL • MinIO • RabbitMQ • Docker • Gemini AI
