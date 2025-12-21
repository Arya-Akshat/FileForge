# FileForge System Walkthrough

> **Purpose**: This document explains how FileForge works internally, covering the request lifecycle, failure handling, and architectural decisions. Perfect for interview prep and code reviews.

---

## 📤 Upload → Queue → Worker → Result

### Step-by-Step Request Lifecycle

#### Phase 1: Initialize Upload (Client → Backend → MinIO)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Client: POST /api/files/init-upload                                        │
│ Body: { filename: "vacation.jpg", size_bytes: 1048576, mime_type: "image/jpeg" }
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Backend (files.py):                                                        │
│ 1. Validate JWT token → Extract user_id                                    │
│ 2. Generate unique file_id (UUID)                                          │
│ 3. Create storage_key: f"{user_id}/{file_id}/{filename}"                   │
│ 4. Call MinIO to generate presigned PUT URL (valid 1 hour)                 │
│ 5. Insert File record: status=PENDING_UPLOAD                               │
│ 6. Return: { file_id, upload_url, expires_at }                             │
└────────────────────────────────────────────────────────────────────────────┘
```

**Why presigned URLs?**
- Backend never touches file bytes → reduces memory/bandwidth
- Direct client-to-storage upload (like S3)
- Scales better: backend only handles metadata

#### Phase 2: Direct Upload (Client → MinIO)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Client: PUT {presigned_url}                                                │
│ Headers: Content-Type: image/jpeg                                          │
│ Body: <binary file data>                                                   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ MinIO:                                                                     │
│ 1. Validate presigned signature                                            │
│ 2. Verify size matches Content-Length                                      │
│ 3. Store file in "raw" bucket at storage_key                              │
│ 4. Return: 200 OK                                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

**Key insight**: The backend is completely bypassed during the actual file transfer.

#### Phase 3: Complete Upload & Queue Jobs (Client → Backend → RabbitMQ)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Client: POST /api/files/complete-upload                                    │
│ Body: { file_id: "abc-123", pipeline_actions: ["thumbnail", "ai_tag"] }    │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Backend (files.py):                                                        │
│ 1. Verify file exists in DB and belongs to user                            │
│ 2. Confirm file exists in MinIO (HEAD request)                             │
│ 3. Update file status: PENDING_UPLOAD → PROCESSING                         │
│ 4. For each action in pipeline_actions:                                    │
│    a. Create Job record: { file_id, type, status=QUEUED }                  │
│    b. Determine queue: thumbnail → image_queue, ai_tag → ai_queue          │
│    c. Publish message to RabbitMQ:                                         │
│       {                                                                    │
│         job_id: "job-456",                                                 │
│         file_id: "abc-123",                                                │
│         bucket: "raw",                                                     │
│         key: "user-1/abc-123/vacation.jpg",                                │
│         type: "thumbnail",                                                 │
│         params: { size: "256x256" }                                        │
│       }                                                                    │
│ 5. Return: { file, jobs: [...] }                                           │
└────────────────────────────────────────────────────────────────────────────┘
```

#### Phase 4: Worker Processing (RabbitMQ → Worker → MinIO → DB)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Worker (image_processor/worker.py):                                        │
│ 1. basic_consume() blocks waiting for messages on image_queue              │
│ 2. Receive message: { job_id, file_id, bucket, key, type, params }         │
│ 3. Update job status: QUEUED → RUNNING                                     │
│ 4. Download file from MinIO (bucket: raw, key: storage_key)                │
│ 5. Process based on type:                                                  │
│    - thumbnail: Pillow resize to 256x256                                   │
│    - image_convert: Pillow format conversion                               │
│    - image_compress: Pillow quality reduction                              │
│ 6. Upload result to MinIO (bucket: thumbnails/processed)                   │
│ 7. Create new File record for output (is_processed_output=true)            │
│ 8. Update job: status=COMPLETED, result_file_id=new_file_id                │
│ 9. ACK message to RabbitMQ                                                 │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 💥 What Happens If a Worker Crashes?

### Scenario: Worker Dies Mid-Processing

```
Timeline:
T0: Worker picks message from queue
T1: Worker ACKs message (current behavior)
T2: Worker starts processing
T3: Worker crashes (OOM, hardware failure, etc.)

Result: Job stuck in RUNNING forever
        Message lost (already ACKed)
        User sees job that never completes
```

### Current Behavior (Problem)

```python
# In worker.py callback()
def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        process_image_job(message)  # Can crash here
        ch.basic_ack(delivery_tag=method.delivery_tag)  # ACK after processing
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

**Good news**: We ACK after processing, not before! This means crashes result in redelivery.

### What RabbitMQ Does on Worker Crash

1. Worker TCP connection drops
2. RabbitMQ detects disconnect (heartbeat timeout)
3. Unacknowledged messages are requeued
4. Another worker picks up the message
5. Processing restarts from scratch

### Remaining Gaps

| Gap | Problem | Solution |
|-----|---------|----------|
| **No retry limit** | Infinite loop on poison messages | Add `x-death` header tracking |
| **No DLQ** | Failed messages lost | Configure dead-letter exchange |
| **No idempotency** | Duplicate processing on retry | Check if result already exists |
| **No timeout** | Slow jobs block workers | Add processing timeout |

---

## 🐰 Why RabbitMQ Was Chosen

### Requirements Analysis

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Job queue semantics | High | Each job processed exactly once |
| Message acknowledgment | High | Know when job completes |
| Retry on failure | High | Worker crashes shouldn't lose work |
| Multiple job types | Medium | Route to different workers |
| Horizontal scaling | Medium | Add more workers under load |
| Message ordering | Low | Jobs are independent |

### Why NOT Kafka?

```
Kafka is built for: Event streaming, log aggregation, real-time analytics
                    High throughput, message replay, event sourcing

FileForge needs:    Job queues, task distribution, per-message ACKs
                    At-least-once delivery with retry semantics
```

| Feature | RabbitMQ | Kafka |
|---------|----------|-------|
| Message ACK | Per-message ✅ | Offset-based |
| Redelivery | Automatic on NACK ✅ | Manual seek |
| Routing | Flexible exchanges ✅ | Partition-based |
| Complexity | Moderate ✅ | High |

### Why NOT Redis Queues (LPUSH/RPOP)?

```
Redis is built for: Caching, pub/sub, simple queues
                    Low latency, in-memory speed

Missing for us:     No native ACK mechanism
                    No built-in retry/DLQ
                    No message persistence by default
```

### RabbitMQ Architecture in FileForge

```
┌─────────────────────────────────────────────────────────────────┐
│                         RabbitMQ                                │
│                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │ image_queue │  │ video_queue │  │  ai_queue   │   ...      │
│   │  (durable)  │  │  (durable)  │  │  (durable)  │            │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│          │                │                │                    │
└──────────┼────────────────┼────────────────┼────────────────────┘
           │                │                │
           ▼                ▼                ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │   Image     │  │   Video     │  │     AI      │
    │  Workers    │  │  Workers    │  │   Workers   │
    │   (1-5)     │  │   (1-3)     │  │   (1-2)     │
    └─────────────┘  └─────────────┘  └─────────────┘
```

**Key configurations**:
- `durable=True`: Queues survive RabbitMQ restart
- `delivery_mode=2`: Messages persisted to disk
- `prefetch_count=1`: Worker processes one job at a time

---

## 🔄 How Idempotency Works (and Where It's Missing)

### What is Idempotency?

> Processing the same request multiple times produces the same result as processing it once.

### Where FileForge IS Idempotent

#### 1. File Upload (Presigned URLs)
```python
# Uploading the same file to the same key overwrites
# Result: Same file content, no duplicates
PUT /raw/user-1/file-abc/photo.jpg  # First upload
PUT /raw/user-1/file-abc/photo.jpg  # Re-upload = same result
```

#### 2. User Registration (Email Uniqueness)
```python
# Database constraint prevents duplicates
email = Column(String, unique=True)  # Raises IntegrityError on duplicate
```

### Where FileForge is NOT Idempotent (Gaps)

#### 1. Job Processing (Problem!)
```python
# If worker crashes after uploading result but before DB update:
# - Retry creates ANOTHER result file
# - Original file remains in storage

# Current code:
result_file_id = str(uuid.uuid4())  # New ID every time!
s3_client.upload_file(output_path, output_bucket, output_key)  # Duplicate files
```

**Fix**: Use deterministic result file ID based on job_id:
```python
# Idempotent version:
result_file_id = f"{job_id}-result"  # Same ID on retry
result_key = f"{job_id}/output.jpg"   # Same key on retry

# Check if already exists:
if not file_exists_in_db(result_file_id):
    s3_client.upload_file(...)
    create_file_record(result_file_id, ...)
```

#### 2. Complete Upload (Creates Multiple Jobs)
```python
# If client retries POST /complete-upload:
# - Backend creates ANOTHER set of jobs
# - Same file processed multiple times

# Fix: Check if jobs already exist for file_id + action type
existing = db.query(Job).filter(
    Job.file_id == file_id,
    Job.type == action_type
).first()
if not existing:
    create_job(...)
```

### Idempotency Keys (Best Practice)

For critical operations, use client-provided idempotency keys:
```python
POST /api/files/complete-upload
Headers:
  Idempotency-Key: "client-uuid-12345"
Body:
  { file_id: "...", pipeline_actions: [...] }

# Backend:
1. Check Redis: GET idempotency:client-uuid-12345
2. If exists → Return cached response
3. If not → Process request, cache response for 24h
```

---

## 🎯 Key Takeaways for Interviews

### Questions You Can Now Answer

1. **"Walk me through what happens when a user uploads a file"**
   → Full lifecycle from init-upload → presigned URL → complete-upload → queue → worker

2. **"How do you handle worker failures?"**
   → RabbitMQ ACK semantics, message redelivery, current gaps (no DLQ)

3. **"Why RabbitMQ over Kafka?"**
   → Job queue semantics vs event streaming, per-message ACK, simpler

4. **"What about idempotency?"**
   → Where it exists (uploads, registration), where it's missing (job processing), how to fix

5. **"How would you scale this?"**
   → Horizontal worker scaling, stateless backend, presigned URLs for storage

### Architecture Principles Demonstrated

| Principle | Implementation |
|-----------|----------------|
| **Separation of Concerns** | Workers isolated by job type |
| **Async Processing** | Queue-based decoupling |
| **Stateless Services** | Backend has no session state |
| **Direct-to-Storage** | Presigned URLs bypass backend |
| **Database as Source of Truth** | Job status persisted |
| **Graceful Degradation** | Failed jobs marked, not lost |
