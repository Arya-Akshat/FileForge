# FileForge Interview Prep: 10 Questions & Answers

> **How to use this**: Practice explaining these concepts using YOUR project as the example. Interviewers love when candidates can point to real implementations.

---

## 1. "Explain async vs sync processing using your project"

### The Question They're Really Asking
*"Do you understand when to use synchronous vs asynchronous architectures?"*

### Your Answer

> In FileForge, I use **synchronous processing** for fast operations like authentication and file metadata retrieval—things that complete in milliseconds. But for **file processing** (thumbnails, video transcoding, AI tagging), I use **asynchronous processing** with RabbitMQ.

**Why async for file processing?**

| Sync Approach | Async Approach (FileForge) |
|---------------|---------------------------|
| Request blocks until done | Request returns immediately |
| 30s timeout for video transcode? | Job runs in background for minutes |
| One slow job blocks others | Workers process independently |
| Scales poorly | Add more workers to scale |

**Code example** from `backend/app/api/files.py`:
```python
# Sync: Return immediately after queueing
for action in pipeline_actions:
    job = create_job(file_id, action)       # Save to DB
    rabbitmq.publish_job(queue, message)     # Queue for async processing
return {"status": "processing", "jobs": jobs}  # Don't wait for completion
```

**Real numbers**: Video transcoding takes 2-5 minutes. Imagine blocking an HTTP request for that long!

---

## 2. "How do you handle retries in your system?"

### The Question They're Really Asking
*"What happens when things fail? Have you thought about reliability?"*

### Your Answer

> RabbitMQ provides the foundation for retries through message acknowledgment. When a worker crashes, unacknowledged messages are automatically redelivered.

**Current implementation**:
```python
def callback(ch, method, properties, body):
    try:
        process_image_job(message)
        ch.basic_ack(delivery_tag=method.delivery_tag)  # ACK only on success
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # Don't retry on app error
```

**What I'd add for production**:

| Gap | Solution |
|-----|----------|
| No retry limit | Track attempts in message headers |
| No backoff | Use delayed retry exchange |
| No DLQ | Configure dead-letter exchange for failed messages |
| No alerting | Monitor DLQ depth |

**Exponential backoff I'd implement**:
```python
retry_delays = [1, 5, 30, 300]  # seconds
attempt = get_retry_count(properties)
if attempt < len(retry_delays):
    requeue_with_delay(retry_delays[attempt])
else:
    send_to_dlq()
```

---

## 3. "How would you scale this system?"

### The Question They're Really Asking
*"Do you understand distributed systems and bottlenecks?"*

### Your Answer

> FileForge is designed for horizontal scaling. Each component can scale independently.

**Scaling levers**:

| Component | How to Scale | Command |
|-----------|--------------|---------|
| Workers | Add more containers | `docker-compose up --scale image_worker=5` |
| Backend | Add instances behind NGINX | `docker-compose up --scale backend=3` |
| Storage | MinIO distributed mode | Multi-node cluster |
| Database | Read replicas | PostgreSQL streaming replication |

**Why this architecture scales**:

1. **Stateless backend**: No session state, any instance can handle any request
2. **Presigned URLs**: File uploads bypass backend entirely
3. **Queue-based decoupling**: Workers don't need to know about backend
4. **Separate queues per job type**: Video workers don't block image workers

**Bottleneck analysis**:
```
Current bottleneck: Database writes (single PostgreSQL)
Solution: Connection pooling, read replicas, or shard by user_id

Future bottleneck: RabbitMQ at extreme scale
Solution: Cluster mode, or migrate to Kafka for > 100k msgs/sec
```

---

## 4. "Why did you choose RabbitMQ over Kafka?"

### The Question They're Really Asking
*"Can you make technology decisions with clear reasoning?"*

### Your Answer

> I chose RabbitMQ because FileForge needs **job queue semantics**, not **event streaming**.

| Requirement | RabbitMQ | Kafka |
|-------------|----------|-------|
| Per-message acknowledgment | ✅ Native | ❌ Offset-based |
| Message redelivery on failure | ✅ Automatic | ❌ Manual seek |
| Learning curve | Moderate | Steep |
| Operational complexity | Lower | Higher (ZooKeeper) |

**When I'd choose Kafka**:
- Event sourcing / audit logs
- Stream processing with replay
- Extremely high throughput (>100k/sec)
- Multiple consumers need same events

**When RabbitMQ wins**:
- Task/job queues (our case)
- Request-response patterns
- Complex routing (topic exchanges)
- Smaller scale with simpler ops

> "Use the right tool for the job. RabbitMQ is a work queue; Kafka is an event log."

---

## 5. "What happens if a worker crashes mid-processing?"

### The Question They're Really Asking
*"Do you understand failure modes in distributed systems?"*

### Your Answer

> When a worker crashes, RabbitMQ detects the lost connection and requeues unacknowledged messages.

**Timeline**:
```
T0: Worker pulls message from queue
T1: Worker starts processing (status → RUNNING)
T2: Worker crashes
T3: RabbitMQ heartbeat timeout (60s default)
T4: Message requeued automatically
T5: Another worker picks it up
```

**Current gaps I'm aware of**:

| Problem | Impact | Solution |
|---------|--------|----------|
| Job stuck in RUNNING | User confusion | Heartbeat/timeout mechanism |
| Duplicate processing | Wasted resources | Idempotent operations |
| No retry limit | Infinite loop on bad data | Track attempt count |

**How I'd fix duplicate processing**:
```python
# Make output deterministic based on job_id
result_key = f"outputs/{job_id}/result.jpg"  # Same key on retry

# Check if result already exists
if minio.object_exists(bucket, result_key):
    return already_completed_response()
```

---

## 6. "How do you ensure data consistency?"

### The Question They're Really Asking
*"Do you understand distributed transactions and eventual consistency?"*

### Your Answer

> FileForge uses **eventual consistency** with the database as the source of truth.

**Pattern: Outbox-like behavior**

```python
# In complete_upload:
1. Create Job record in PostgreSQL (status: QUEUED)
2. Publish message to RabbitMQ
3. Return response

# If RabbitMQ publish fails:
# - Transaction rolls back
# - No orphan jobs in DB
```

**Consistency guarantees**:

| Operation | Consistency | Reason |
|-----------|-------------|--------|
| Job creation | Strong | PostgreSQL transaction |
| File upload | Eventual | Direct to MinIO |
| Job status | Eventual | Worker updates async |

**What I'd add for production**:
- Transactional outbox pattern (write to outbox table, separate publisher)
- Saga pattern for multi-step workflows
- Compensation logic for failed workflows

---

## 7. "How does authentication work?"

### The Question They're Really Asking
*"Do you understand security basics?"*

### Your Answer

> FileForge uses **JWT (JSON Web Tokens)** for stateless authentication.

**Flow**:
```
1. POST /register → Hash password with bcrypt, store user
2. POST /login → Verify password, return JWT token
3. Subsequent requests → Include "Authorization: Bearer <token>"
4. Backend → Verify JWT signature, extract user_id
```

**Security measures**:

| Threat | Mitigation |
|--------|------------|
| Password theft | bcrypt hashing (12 rounds) |
| Token forgery | JWT signature verification |
| Token theft | Short expiration (30 min) |
| Brute force | (Planned) Rate limiting |

**Code from `backend/app/core/security.py`**:
```python
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

---

## 8. "How would you add a new processing type?"

### The Question They're Really Asking
*"Is your system extensible? Can you design for change?"*

### Your Answer

> Adding a new processor is straightforward due to the decoupled architecture.

**Steps to add "PDF → Image" converter**:

1. **Define job type** (`backend/app/db/models.py`):
```python
class JobType(str, Enum):
    PDF_CONVERT = "pdf_convert"  # Add here
```

2. **Map to queue** (`backend/app/services/rabbitmq.py`):
```python
mapping = {
    'pdf_convert': 'document_queue',  # Add here
}
```

3. **Create worker** (`workers/pdf_processor/worker.py`):
```python
def process_pdf_job(job_data):
    # Download PDF from MinIO
    # Convert using pdf2image
    # Upload result to MinIO
    # Update job status
```

4. **Add to docker-compose**:
```yaml
pdf_worker:
  build: ./workers/pdf_processor
  depends_on: [rabbitmq, minio, db]
```

**Why this is easy**: Each worker is independent. No changes to existing workers or backend logic beyond the mapping.

---

## 9. "How would you implement rate limiting?"

### The Question They're Really Asking
*"Can you protect systems from abuse?"*

### Your Answer

> I'd implement rate limiting at the NGINX layer and application layer.

**Approach: Token Bucket via Redis**

```python
# Middleware pseudocode
async def rate_limit_middleware(request):
    user_id = get_user_id(request)
    key = f"ratelimit:{user_id}:{endpoint}"
    
    current = redis.incr(key)
    if current == 1:
        redis.expire(key, 60)  # 60-second window
    
    if current > 100:  # 100 requests/minute
        raise HTTPException(429, "Too Many Requests")
```

**NGINX layer (defense in depth)**:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
}
```

**Different limits for different operations**:

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/login` | 5/min | Prevent brute force |
| `/upload` | 10/min | Expensive operation |
| `/files` | 100/min | Cheap read |

---

## 10. "What would you do differently if starting over?"

### The Question They're Really Asking
*"Can you reflect and learn? Are you honest about limitations?"*

### Your Answer

> Great question. Here's what I've learned:

**What I'd keep**:
- ✅ RabbitMQ for job queues (right tool)
- ✅ MinIO with presigned URLs (scales well)
- ✅ Separate workers per job type (independent scaling)

**What I'd change**:

| Current | Change To | Why |
|---------|-----------|-----|
| No retry limits | Exponential backoff + DLQ | Prevent infinite loops |
| Manual job polling | WebSocket updates | Better UX |
| Sync DB writes | Transactional outbox | Better consistency |
| No tracing | OpenTelemetry | Debug distributed issues |

**Biggest lesson learned**:
> "I underestimated operational complexity. Building features is fun; handling failures gracefully is where production systems differ from demos."

---

## 💡 Interview Tips

### Show, Don't Just Tell
- Pull up the code while explaining
- Point to specific files: "Here in `worker.py` line 150..."
- Show the architecture diagram from README

### Acknowledge Gaps Proactively
- "Here's what I'd add for production..."
- "This is a learning project, so I simplified X, but in production..."

### Connect to Real Companies
- "This is similar to how Dropbox handles uploads..."
- "Netflix uses a similar worker pattern for encoding..."

### Quantify When Possible
- "Video transcoding takes 2-5 minutes"
- "The presigned URL approach reduces backend memory by 10x"
- "We can scale to 5 workers with a single command"

---

## Quick Reference: Key Code Locations

| Concept | File | Line |
|---------|------|------|
| JWT auth | `backend/app/core/security.py` | - |
| Presigned URLs | `backend/app/services/minio.py` | - |
| Queue publishing | `backend/app/services/rabbitmq.py` | - |
| Worker main loop | `workers/image_processor/worker.py` | `main()` |
| Job status update | `workers/image_processor/worker.py` | `update_job_status()` |
| Health endpoint | `backend/app/main.py` | `/health` |
