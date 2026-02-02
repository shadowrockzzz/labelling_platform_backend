#!/bin/bash

# MinIO initialization script
# This script runs automatically when MinIO container starts
# It creates the default bucket for the labelling platform

# Wait for MinIO to be ready
until mc alias set local http://minio:9000 labelling_platform labelling_platform_secret_key; do
  echo "Waiting for MinIO to start..."
  sleep 5
done

echo "MinIO is ready, creating bucket..."

# Create bucket if it doesn't exist
mc mb local/labelling-platform-files --ignore-existing

echo "Bucket 'labelling-platform-files' created successfully!"

# Make bucket public (optional - for development)
# mc anonymous set download local/labelling-platform-files

echo "MinIO initialization complete!"