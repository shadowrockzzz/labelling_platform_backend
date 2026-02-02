# S3/MinIO Setup Guide

This guide will help you set up MinIO (S3-compatible storage) for the labelling platform.

## What is MinIO?

MinIO is a high-performance, S3-compatible object storage system. It provides the same API as AWS S3 but runs locally, making it perfect for development and testing without needing an AWS account.

## Quick Start

### 1. Start MinIO Container

```bash
# From backend directory
cd labelling_platform_backend
docker-compose up -d
```

This will:
- Pull the MinIO Docker image
- Start the MinIO server on port 9000 (S3 API)
- Start the MinIO Console on port 9001 (Web UI)
- Create a Docker volume for persistent storage
- Automatically create the `labelling-platform-files` bucket

### 2. Verify MinIO is Running

```bash
# Check if the container is running
docker ps

# You should see 'labelling_platform_minio' in the list
```

### 3. Access MinIO Console (Optional)

Open your browser and go to: **http://localhost:9001**

**Login Credentials:**
- Username: `labelling_platform`
- Password: `labelling_platform_secret_key`

From the console, you can:
- Browse uploaded files
- Check bucket contents
- View file metadata
- Download/upload files manually

### 4. Restart Your Backend Server

The backend needs to load the new S3 configuration:

```bash
# If your backend is running, stop it first (Ctrl+C)
# Then start it again
cd labelling_platform_backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the Setup

Now you can test if S3 is working:

1. Open your frontend application
2. Navigate to a project
3. Click on "Text Annotation" tab
4. Upload a text file (e.g., .txt file)
5. The file should now display with its full content!

## Configuration Details

### Environment Variables

The following S3 settings are configured in `labelling_platform_backend/.env`:

```bash
AWS_ACCESS_KEY_ID=labelling_platform
AWS_SECRET_ACCESS_KEY=labelling_platform_secret_key
AWS_S3_BUCKET=labelling-platform-files
AWS_S3_ENDPOINT=http://localhost:9000
AWS_REGION=us-east-1
```

### File Storage Structure

Files are stored in S3 with the following structure:

```
labelling-platform-files/
├── projects/
│   ├── {project_id}/
│   │   ├── inputs/
│   │   │   ├── uploads/
│   │   │   │   └── {uuid}.txt          # Uploaded files
│   │   │   └── external/
│   │   │       └── {uuid}.json          # URL resources
│   │   └── outputs/
│   │       └── text/
│   │           └── {annotation_id}.json  # Annotation outputs
```

## Common Commands

### Start MinIO
```bash
docker-compose up -d
```

### Stop MinIO
```bash
docker-compose down
```

### View MinIO Logs
```bash
docker-compose logs minio
```

### Restart MinIO
```bash
docker-compose restart minio
```

### Access MinIO Container Shell
```bash
docker exec -it labelling_platform_minio sh
```

### Remove All MinIO Data (⚠️ Warning: This deletes all files)
```bash
docker-compose down -v
```

## Troubleshooting

### Issue: "S3 not configured" error in logs

**Solution:** 
1. Ensure MinIO is running: `docker ps`
2. Check that the `.env` file has the correct S3 settings
3. Verify the config path in `app/core/config.py` points to the correct `.env` location

### Issue: Cannot connect to MinIO

**Solution:**
1. Check if port 9000 is available: `netstat -an | grep 9000`
2. If port is in use, either:
   - Stop the conflicting service, or
   - Change the port in `docker-compose.yml`

### Issue: Bucket creation failed

**Solution:**
1. Check MinIO logs: `docker-compose logs minio`
2. Manually create bucket using MinIO Console at http://localhost:9001
3. Name bucket exactly: `labelling-platform-files`

**Manual Bucket Creation Steps:**

1. **Open MinIO Console**
   - Navigate to: http://localhost:9001
   - Login with credentials:
     - Username: `labelling_platform`
     - Password: `labelling_platform_secret_key`

2. **Create Bucket**
   - Click on "Buckets" in the left sidebar
   - Click on blue "+ Create Bucket" button
   - Enter bucket name: `labelling-platform-files` (exact match required)
   - Click "Create Bucket"

3. **Verify Bucket**
   - You should see `labelling-platform-files` in bucket list
   - Click on bucket to view its contents (should be empty initially)

4. **Alternative: Create Bucket via Docker CLI**

   If you prefer command line:

   ```bash
   # Set up MinIO client alias
   docker exec labelling_platform_minio mc alias set local http://localhost:9000 labelling_platform labelling_platform_secret_key

   # Create bucket
   docker exec labelling_platform_minio mc mb local/labelling-platform-files

   # Verify bucket was created
   docker exec labelling_platform_minio mc ls local/
   ```

5. **Test Backend Connection**

   After creating bucket, restart your backend:

   ```bash
   # Stop backend (Ctrl+C in terminal)
   # Restart backend
   cd labelling_platform_backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Verify in Backend Logs**

   You should see successful S3 operations when uploading files:

   ```
   INFO: Uploaded file to S3: projects/3/resources/123.txt
   INFO: Downloaded file from S3: projects/3/resources/123.txt
   ```

**Why Manual Creation Might Be Needed:**

- MinIO init script may fail to execute properly
- Docker container startup timing issues
- Network connectivity problems during initialization
- Permission issues with volume mounts

**Verification Checklist:**
- [ ] MinIO container is running (`docker ps`)
- [ ] Bucket `labelling-platform-files` exists in MinIO Console
- [ ] Backend can connect to MinIO (no connection errors in logs)
- [ ] S3 configuration is loaded correctly (check backend logs on startup)
- [ ] File upload works (test by uploading a text file)
- [ ] File download works (text content displays in annotation editor)

### Issue: Files upload but content is still empty

**Solution:**
1. Restart the backend server to reload configuration
2. Clear browser cache and reload the page
3. Check backend logs for S3-related errors

## Migrating to AWS S3 (Production)

When you're ready to move to production with AWS S3:

### 1. Create AWS S3 Bucket
```bash
# Using AWS CLI
aws s3 mb s3://your-bucket-name --region us-east-1
```

### 2. Update .env File
```bash
# Change these values in labelling_platform_backend/.env
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_S3_ENDPOINT=  # Leave empty or remove for AWS
AWS_REGION=your-aws-region
```

### 3. No Code Changes Needed!

The boto3 library works identically with both MinIO and AWS S3. Just changing the environment variables is sufficient.

### 4. Optional: Migrate Existing Data
If you have data in MinIO that you want to move to AWS S3:

```bash
# Install AWS CLI and MinIO Client
pip install awscli minio-py

# Sync data from MinIO to AWS S3
aws s3 sync s3://labelling-platform-files s3://your-bucket-name \
  --endpoint-url http://localhost:9000
```

## Security Notes

⚠️ **Important:** The current credentials are for development only. For production:

1. Use strong, unique passwords
2. Enable HTTPS for MinIO (configure SSL certificates)
3. Use IAM roles and policies in AWS S3
4. Enable bucket encryption
5. Set up proper access control lists (ACLs)
6. Use environment-specific credentials
7. Never commit `.env` files to version control

## Additional Resources

- [MinIO Documentation](https://docs.min.io/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)

## Support

If you encounter any issues:

1. Check the logs: `docker-compose logs minio`
2. Verify configuration in `.env` file
3. Ensure ports 9000 and 9001 are not blocked by firewall
4. Check that Docker is running properly: `docker info`