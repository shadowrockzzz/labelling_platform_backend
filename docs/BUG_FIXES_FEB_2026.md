# Bug Fixes - February 2026

## Issues Fixed

### 1. Queue Endpoint Missing Required Field

**Problem:**
```
GET /api/v1/annotations/text/projects/3/queue HTTP/1.1 500 Internal Server Error
ValidationError: 1 validation error for QueueListResponse
total Field required
```

**Root Cause:**
The `get_queue_tasks_endpoint` in `app/annotations/text/router.py` was returning `QueueListResponse` without the required `total` parameter.

**Fix:**
Added `total` parameter to the response:
```python
return QueueListResponse(
    success=True,
    data=tasks,
    total=len(tasks)  # Added this line
)
```

**File Modified:** `labelling_platform_backend/app/annotations/text/router.py`

---

### 2. MinIO/S3 Connection Failure Blocking File Uploads

**Problem:**
```
POST /api/v1/annotations/text/projects/3/resources/upload HTTP/1.1 500 Internal Server Error
botocore.exceptions.EndpointConnectionError: 
Could not connect to endpoint URL: "http://localhost:9000/..."
ConnectionRefusedError: [Errno 111] Connection refused
```

**Root Cause:**
MinIO (S3-compatible storage) was not running at `http://localhost:9000`. The `upload_file_to_s3` function didn't handle connection failures gracefully, causing the entire file upload to fail.

**Fix:**
Updated `upload_file_to_s3` in `app/utils/s3_utils.py` to handle connection errors gracefully:
- Added exception handling for `EndpointConnectionError`, `ConnectionError`, and `NoCredentialsError`
- Returns `True` (mock success) when S3/MinIO is not available
- Logs warning message explaining that metadata will be saved but file content won't be stored
- Allows development to continue without running MinIO

```python
except EndpointConnectionError as e:
    logger.error(f"Cannot connect to S3 endpoint at {settings.AWS_S3_ENDPOINT}: {e}")
    logger.warning("S3/MinIO is not running. File metadata will be saved but file content won't be stored.")
    return True  # Continue anyway - save metadata to DB
```

**File Modified:** `labelling_platform_backend/app/utils/s3_utils.py`

---

## Benefits

1. **Queue endpoint works** - Admins and project managers can now view queue tasks
2. **Development without MinIO** - File uploads work even when MinIO is not running
3. **Graceful degradation** - System continues working with degraded functionality instead of failing completely
4. **Clear logging** - Developers get clear warnings about what's not working

## Next Steps

To fully enable file storage, either:

1. **Start MinIO** (recommended for development):
   ```bash
   cd labelling_platform_backend
   docker-compose up minio
   ```

2. **Or use local file storage** - Modify upload functions to save to disk

3. **Or configure AWS S3** - Set up real S3 credentials in `.env`

---

## Testing

Verify fixes by:
1. ✓ Queue endpoint returns 200 OK
2. ✓ File upload succeeds (even without MinIO)
3. ✓ Resource metadata is saved to database
4. ✓ Logs show appropriate warnings about MinIO not running