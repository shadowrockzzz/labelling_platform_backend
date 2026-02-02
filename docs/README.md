# Backend Documentation

This directory contains documentation specific to the backend setup and infrastructure.

## Files

### QUICK_START.md
Quick 3-step guide to get MinIO (S3-compatible storage) up and running. Essential for text annotation features.

### S3_SETUP_GUIDE.md
Comprehensive guide for MinIO/S3 setup, including:
- Detailed installation steps
- Configuration options
- Troubleshooting
- Migration to AWS S3 for production
- Security best practices

## When to Use These Guides

- **First-time setup:** Start with QUICK_START.md
- **Development:** Keep both guides handy for reference
- **Production:** Use S3_SETUP_GUIDE.md for AWS S3 migration
- **Troubleshooting:** Both guides have troubleshooting sections

## Quick Reference

**Start MinIO:**
```bash
cd labelling_platform_backend
docker-compose up -d
```

**Stop MinIO:**
```bash
docker-compose down
```

**Check Logs:**
```bash
docker-compose logs minio
```

**Access MinIO Console:**
http://localhost:9001
- Username: `labelling_platform`
- Password: `labelling_platform_secret_key`

## Important Notes

- MinIO must be running for text annotation file uploads to work
- Files are stored in the `labelling-platform-files` bucket
- MinIO provides S3-compatible API - works with AWS S3 too
- For production, switch to AWS S3 by changing .env variables (no code changes needed!)
- If bucket doesn't auto-create, create manually via MinIO Console (see S3_SETUP_GUIDE.md)

## Recent Fixes & Improvements

### S3/MinIO Configuration (February 2, 2026)

Fixed critical issues with S3 storage setup:

1. **Fixed .env file path** - Backend now correctly loads S3 configuration
2. **Added missing TOKEN_PROVIDER field** - Configuration validation passes
3. **Manual bucket creation guide** - Steps to create bucket if auto-creation fails

**Impact:**
- ✅ Text content now displays properly in annotation editor
- ✅ File uploads work correctly
- ✅ File downloads work correctly
- ✅ No more S3 connection errors

For detailed information about all recent fixes, see:
- **BUG_FIX_LOG.md** - Complete bug fix log with all improvements

## Need More Help?

- Backend README: `../README.md`
- Main project setup: `SETUP_GUIDE.md`
- API documentation: `http://localhost:8000/docs`