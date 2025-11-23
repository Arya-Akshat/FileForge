# API Examples for FileForge

## Prerequisites

```bash
# Set base URL
export BASE_URL="http://localhost"

# Or if running backend directly
export BASE_URL="http://localhost:8000"
```

## 1. Authentication

### Register User

```bash
curl -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### Login

```bash
# Login and save token
TOKEN=$(curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

### Get Current User

```bash
curl -X GET "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

## 2. File Upload Flow

### Step 1: Initialize Upload

```bash
# Request upload URL
UPLOAD_RESPONSE=$(curl -X POST "$BASE_URL/api/files/init-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-image.jpg",
    "size_bytes": 524288,
    "mime_type": "image/jpeg"
  }')

echo "$UPLOAD_RESPONSE" | jq .

# Extract values
FILE_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.file_id')
UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.upload_url')

echo "File ID: $FILE_ID"
echo "Upload URL: $UPLOAD_URL"
```

### Step 2: Upload File to MinIO

```bash
# Upload actual file
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: image/jpeg" \
  --upload-file /path/to/your/image.jpg
```

### Step 3: Complete Upload with Processing

```bash
# Trigger processing pipeline
curl -X POST "$BASE_URL/api/files/complete-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": \"$FILE_ID\",
    \"pipeline_actions\": [\"thumbnail\", \"image_compress\", \"ai_tag\"]
  }"
```

## 3. File Management

### List All Files

```bash
curl -X GET "$BASE_URL/api/files" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Get File Details

```bash
curl -X GET "$BASE_URL/api/files/$FILE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Get File Jobs

```bash
curl -X GET "$BASE_URL/api/files/$FILE_ID/jobs" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Delete File

```bash
curl -X DELETE "$BASE_URL/api/files/$FILE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

## 4. Job Management

### Get Specific Job

```bash
JOB_ID="your-job-id"
curl -X GET "$BASE_URL/api/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### List All Jobs

```bash
curl -X GET "$BASE_URL/api/jobs" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## 5. Complete Upload Example with Different Processing Options

### Image: Thumbnail + Compress + AI Tag

```bash
curl -X POST "$BASE_URL/api/files/complete-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": \"$FILE_ID\",
    \"pipeline_actions\": [\"thumbnail\", \"image_compress\", \"ai_tag\"]
  }"
```

### Image: Convert to WebP

```bash
curl -X POST "$BASE_URL/api/files/complete-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": \"$FILE_ID\",
    \"pipeline_actions\": [\"image_convert\"]
  }"
```

### Video: Thumbnail + Preview

```bash
curl -X POST "$BASE_URL/api/files/complete-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": \"$FILE_ID\",
    \"pipeline_actions\": [\"video_thumbnail\", \"video_preview\"]
  }"
```

### Security: Virus Scan + Encrypt

```bash
curl -X POST "$BASE_URL/api/files/complete-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": \"$FILE_ID\",
    \"pipeline_actions\": [\"virus_scan\", \"encrypt\"]
  }"
```

## 6. Monitoring Job Progress

### Poll for Job Status

```bash
# Check file status
while true; do
  STATUS=$(curl -s -X GET "$BASE_URL/api/files/$FILE_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  echo "File status: $STATUS"
  
  if [ "$STATUS" = "ready" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 2
done

# Get all jobs for file
curl -X GET "$BASE_URL/api/files/$FILE_ID/jobs" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## 7. Python Example

```python
import requests
import time

BASE_URL = "http://localhost"

# 1. Register and login
def login(email, password):
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    return response.json()["access_token"]

# 2. Upload file
def upload_file(token, file_path, pipeline_actions):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Initialize upload
    with open(file_path, 'rb') as f:
        file_size = len(f.read())
    
    init_response = requests.post(
        f"{BASE_URL}/api/files/init-upload",
        headers=headers,
        json={
            "filename": file_path.split('/')[-1],
            "size_bytes": file_size,
            "mime_type": "image/jpeg"
        }
    )
    
    data = init_response.json()
    file_id = data["file_id"]
    upload_url = data["upload_url"]
    
    # Upload to MinIO
    with open(file_path, 'rb') as f:
        requests.put(upload_url, data=f.read())
    
    # Complete upload with processing
    requests.post(
        f"{BASE_URL}/api/files/complete-upload",
        headers=headers,
        json={
            "file_id": file_id,
            "pipeline_actions": pipeline_actions
        }
    )
    
    return file_id

# 3. Wait for processing
def wait_for_processing(token, file_id):
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        response = requests.get(
            f"{BASE_URL}/api/files/{file_id}",
            headers=headers
        )
        status = response.json()["status"]
        print(f"Status: {status}")
        
        if status in ["ready", "failed"]:
            break
        
        time.sleep(2)
    
    # Get jobs
    jobs_response = requests.get(
        f"{BASE_URL}/api/files/{file_id}/jobs",
        headers=headers
    )
    return jobs_response.json()

# Usage
token = login("user@example.com", "password123")
file_id = upload_file(token, "image.jpg", ["thumbnail", "ai_tag"])
jobs = wait_for_processing(token, file_id)
print("Jobs:", jobs)
```

## 8. Testing with Sample Data

```bash
# Create a test image
convert -size 800x600 xc:blue test-image.jpg

# Or download a sample
curl -o test-image.jpg https://via.placeholder.com/800x600

# Upload it
FILE_ID=$(curl -X POST "$BASE_URL/api/files/init-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-image.jpg",
    "size_bytes": 50000,
    "mime_type": "image/jpeg"
  }' | jq -r '.file_id')

UPLOAD_URL=$(curl -X POST "$BASE_URL/api/files/init-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-image.jpg",
    "size_bytes": 50000,
    "mime_type": "image/jpeg"
  }' | jq -r '.upload_url')

curl -X PUT "$UPLOAD_URL" --upload-file test-image.jpg

curl -X POST "$BASE_URL/api/files/complete-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": \"$FILE_ID\",
    \"pipeline_actions\": [\"thumbnail\", \"image_compress\"]
  }"
```
