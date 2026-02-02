# 🚀 Quick Start - MinIO Setup

Get your S3 storage up and running in 3 simple steps!

## Step 1: Start MinIO

```bash
# From the backend directory
cd labelling_platform_backend
docker-compose up -d
```

**What happens:**
- Downloads MinIO Docker image (first time only)
- Starts MinIO server on http://localhost:9000
- Starts MinIO Console on http://localhost:9001
- Attempts to create `labelling-platform-files` bucket automatically

**Verify it's running:**
```bash
docker ps
```

**If bucket wasn't created automatically:**
1. Open MinIO Console: http://localhost:9001
2. Login: `labelling_platform` / `labelling_platform_secret_key`
3. Click "Buckets" → "+ Create Bucket"
4. Name it: `labelling-platform-files`
5. Click "Create Bucket"

## Step 2: Restart Backend Server

The backend needs to load the new S3 configuration:

```bash
# Stop current backend (if running)
# Press Ctrl+C in the terminal where backend is running

# Restart backend (from labelling_platform_backend directory)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Step 3: Test It!

1. Open your frontend application (usually http://localhost:5173 or http://localhost:3000)
2. Login to your account
3. Navigate to a project
4. Go to "Text Annotation" tab
5. Upload a text file (.txt)
6. **✨ The file content should now display!**

## That's It! 🎉

Your text annotation issue is now fixed. Files will be stored in MinIO and retrieved properly.

---

## Optional: Explore MinIO Console

Want to see your files in the browser?

1. Open: http://localhost:9001
2. Login with:
   - Username: `labelling_platform`
   - Password: `labelling_platform_secret_key`
3. Browse to `labelling-platform-files` bucket to see uploaded files

## Need Help?

- **Full Guide:** See `S3_SETUP_GUIDE.md` in the same directory
- **Check Logs:** `docker-compose logs minio`
- **Restart MinIO:** `docker-compose restart minio`
- **Stop MinIO:** `docker-compose down`

## Common Issues

**Problem:** Still see empty text content?
**Solution:** 
1. Make sure you restarted the backend server
2. Clear browser cache and reload the page
3. Check backend logs for S3 errors

**Problem:** "S3 not configured" in logs?
**Solution:**
1. Verify MinIO is running: `docker ps`
2. Check that `.env` file has the correct S3 settings
3. Restart the backend server

**Problem:** Port 9000 already in use?
**Solution:**
1. Find what's using it: `lsof -i :9000`
2. Stop that service, OR
3. Edit port in `docker-compose.yml` and restart

## Next Steps

✅ S3 is now configured and working
✅ Text content will display properly
✅ Files are stored persistently
✅ Ready for development and testing

When ready for production, just change the S3 settings in `.env` to point to AWS S3 - no code changes needed!

---

**Happy Labelling! 📝✨**