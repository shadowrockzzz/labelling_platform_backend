"""
AWS S3 utilities for file storage.
Supports both AWS S3 and S3-compatible services (MinIO, DigitalOcean Spaces, etc.)
"""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import Optional
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_s3_client():
    """
    Get configured S3 client.
    Falls back to local storage if S3 is not configured.
    """
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("S3 not configured, using mock storage")
        return None
    
    config = {}
    if settings.AWS_S3_ENDPOINT:
        # For S3-compatible services
        config = {
            'endpoint_url': settings.AWS_S3_ENDPOINT,
            'config': Config(signature_version='s3v4')
        }
    
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        **config
    )


def upload_file_to_s3(file_content: bytes, s3_key: str, content_type: str = "text/plain") -> bool:
    """
    Upload file to S3.
    
    Args:
        file_content: File content as bytes
        s3_key: S3 object key (path)
        content_type: MIME type
        
    Returns:
        True if successful, False otherwise
    """
    if not settings.AWS_S3_BUCKET:
        logger.warning("S3 bucket not configured, skipping upload")
        return True  # Mock success
    
    try:
        s3 = get_s3_client()
        if not s3:
            return True
        
        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type
        )
        logger.info(f"Uploaded file to S3: {s3_key}")
        return True
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        return False


def download_file_from_s3(s3_key: str) -> Optional[bytes]:
    """
    Download file from S3.
    
    Args:
        s3_key: S3 object key (path)
        
    Returns:
        File content as bytes, or None if failed
    """
    if not settings.AWS_S3_BUCKET:
        logger.warning("S3 bucket not configured")
        return None
    
    try:
        s3 = get_s3_client()
        if not s3:
            return None
        
        response = s3.get_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key
        )
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"Error downloading from S3: {e}")
        return None


def save_json_to_s3(data: dict, s3_key: str) -> bool:
    """
    Save JSON data to S3.
    
    Args:
        data: Dictionary to save as JSON
        s3_key: S3 object key (path)
        
    Returns:
        True if successful, False otherwise
    """
    json_content = json.dumps(data, indent=2).encode('utf-8')
    return upload_file_to_s3(json_content, s3_key, "application/json")


def load_json_from_s3(s3_key: str) -> Optional[dict]:
    """
    Load JSON data from S3.
    
    Args:
        s3_key: S3 object key (path)
        
    Returns:
        Dictionary with JSON data, or None if failed
    """
    content = download_file_from_s3(s3_key)
    if content:
        try:
            return json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from S3: {e}")
    return None


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL for S3 object.
    
    Args:
        s3_key: S3 object key (path)
        expiration: URL expiration time in seconds (default: 1 hour)
        
    Returns:
        Presigned URL string, or None if failed
    """
    if not settings.AWS_S3_BUCKET:
        logger.warning("S3 bucket not configured")
        return None
    
    try:
        s3 = get_s3_client()
        if not s3:
            return None
        
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_S3_BUCKET,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return None


def delete_file_from_s3(s3_key: str) -> bool:
    """
    Delete file from S3.
    
    Args:
        s3_key: S3 object key (path)
        
    Returns:
        True if successful, False otherwise
    """
    if not settings.AWS_S3_BUCKET:
        logger.warning("S3 bucket not configured")
        return True  # Mock success
    
    try:
        s3 = get_s3_client()
        if not s3:
            return True
        
        s3.delete_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key
        )
        logger.info(f"Deleted file from S3: {s3_key}")
        return True
    except ClientError as e:
        logger.error(f"Error deleting from S3: {e}")
        return False