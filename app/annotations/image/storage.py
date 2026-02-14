"""
Image Storage Utilities

Handles image upload, thumbnail generation, and presigned URL generation
using MinIO/S3 and Pillow for image processing.

Uses the existing S3 configuration from app.utils.s3_utils.
"""

import io
import os
import uuid
import logging
from typing import Optional, Tuple, List
from datetime import timedelta

from fastapi import UploadFile, HTTPException, status
from PIL import Image
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionError, NoCredentialsError
from botocore.client import Config

from app.core.config import settings
from app.utils.s3_utils import get_s3_client as get_base_s3_client, generate_presigned_url, delete_file_from_s3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Allowed image formats
ALLOWED_FORMATS = {'JPEG', 'PNG'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
THUMBNAIL_SIZE = (300, 300)


def get_s3_client():
    """Get S3/MinIO client using existing configuration."""
    return get_base_s3_client()


def get_bucket_name() -> str:
    """Get the S3 bucket name for image storage."""
    return settings.AWS_S3_BUCKET or 'labelling-platform'


async def validate_image(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded image file.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
    
    return True, None


async def extract_image_metadata(file: UploadFile) -> dict:
    """
    Extract metadata from image file including dimensions.
    
    Returns:
        Dictionary with width, height, format, and other metadata
    """
    try:
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset for later reading
        
        # Open with Pillow
        img = Image.open(io.BytesIO(content))
        
        metadata = {
            'width': img.width,
            'height': img.height,
            'format': img.format,
            'mode': img.mode,
        }
        
        # Extract EXIF data if available
        if hasattr(img, '_getexif') and img._getexif():
            exif = img._getexif()
            # Filter to safe EXIF tags only
            safe_exif = {}
            for tag_id, value in exif.items():
                try:
                    # Only include basic EXIF data, skip binary data
                    if isinstance(value, (str, int, float)):
                        safe_exif[str(tag_id)] = value
                except Exception:
                    pass
            metadata['exif'] = safe_exif
        
        return metadata
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process image: {str(e)}"
        )


async def upload_image_to_storage(
    file: UploadFile,
    project_id: int,
    resource_id: int
) -> Tuple[str, str]:
    """
    Upload image to MinIO/S3 storage.
    
    Args:
        file: UploadFile object
        project_id: Project ID
        resource_id: Resource ID
        
    Returns:
        Tuple of (file_path, thumbnail_path)
    """
    s3_client = get_s3_client()
    bucket = get_bucket_name()
    
    # Determine file extension
    content_type = file.content_type
    ext = 'jpg' if content_type == 'image/jpeg' else 'png'
    
    # Generate paths
    file_path = f"images/{project_id}/{resource_id}/original.{ext}"
    thumbnail_path = f"images/{project_id}/{resource_id}/thumbnail.jpg"
    
    try:
        # Read file content
        content = await file.read()
        
        # Upload original image
        s3_client.put_object(
            Bucket=bucket,
            Key=file_path,
            Body=content,
            ContentType=content_type
        )
        
        # Generate and upload thumbnail
        thumbnail_content = await generate_thumbnail_content(content)
        s3_client.put_object(
            Bucket=bucket,
            Key=thumbnail_path,
            Body=thumbnail_content,
            ContentType='image/jpeg'
        )
        
        return file_path, thumbnail_path
        
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


async def generate_thumbnail_content(image_content: bytes) -> bytes:
    """
    Generate thumbnail from image content.
    
    Args:
        image_content: Raw image bytes
        
    Returns:
        Thumbnail image as JPEG bytes
    """
    try:
        img = Image.open(io.BytesIO(image_content))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Create thumbnail maintaining aspect ratio
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        return output.read()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate thumbnail: {str(e)}"
        )


async def upload_mask_to_storage(
    mask_content: bytes,
    project_id: int,
    resource_id: int,
    mask_id: str
) -> str:
    """
    Upload segmentation mask to storage.
    
    Args:
        mask_content: Raw mask image bytes (PNG)
        project_id: Project ID
        resource_id: Resource ID
        mask_id: Unique mask identifier
        
    Returns:
        Path to the stored mask
    """
    s3_client = get_s3_client()
    bucket = get_bucket_name()
    
    mask_path = f"images/{project_id}/{resource_id}/masks/{mask_id}.png"
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=mask_path,
            Body=mask_content,
            ContentType='image/png'
        )
        
        return mask_path
        
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload mask: {str(e)}"
        )


def get_presigned_url(file_path: str, expiry: int = 3600) -> str:
    """
    Generate presigned URL for file access.
    
    Args:
        file_path: Path to file in S3
        expiry: URL expiry time in seconds (default 1 hour)
        
    Returns:
        Presigned URL string
    """
    s3_client = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': file_path
            },
            ExpiresIn=expiry
        )
        return url
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate URL: {str(e)}"
        )


def delete_image_from_storage(file_path: str, thumbnail_path: str = None) -> bool:
    """
    Delete image and thumbnail from storage.
    
    Args:
        file_path: Path to main image
        thumbnail_path: Path to thumbnail (optional)
        
    Returns:
        True if successful
    """
    s3_client = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        objects_to_delete = [{'Key': file_path}]
        
        if thumbnail_path:
            objects_to_delete.append({'Key': thumbnail_path})
        
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={'Objects': objects_to_delete}
        )
        
        return True
        
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )


def delete_masks_from_storage(project_id: int, resource_id: int) -> bool:
    """
    Delete all masks for a resource.
    
    Args:
        project_id: Project ID
        resource_id: Resource ID
        
    Returns:
        True if successful
    """
    s3_client = get_s3_client()
    bucket = get_bucket_name()
    
    mask_prefix = f"images/{project_id}/{resource_id}/masks/"
    
    try:
        # List all objects with the mask prefix
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=mask_prefix
        )
        
        if 'Contents' in response:
            objects_to_delete = [
                {'Key': obj['Key']} 
                for obj in response['Contents']
            ]
            
            if objects_to_delete:
                s3_client.delete_objects(
                    Bucket=bucket,
                    Delete={'Objects': objects_to_delete}
                )
        
        return True
        
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete masks: {str(e)}"
        )


async def download_image_from_url(url: str) -> Tuple[bytes, str]:
    """
    Download image from URL.
    
    Args:
        url: Image URL
        
    Returns:
        Tuple of (image_content, content_type)
    """
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            
            if content_type not in ALLOWED_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid content type from URL: {content_type}"
                )
            
            return response.content, content_type
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download image from URL: {str(e)}"
        )


def create_resource_paths(project_id: int, resource_id: int, ext: str) -> Tuple[str, str]:
    """
    Create standard paths for image resources.
    
    Args:
        project_id: Project ID
        resource_id: Resource ID
        ext: File extension
        
    Returns:
        Tuple of (file_path, thumbnail_path)
    """
    file_path = f"images/{project_id}/{resource_id}/original.{ext}"
    thumbnail_path = f"images/{project_id}/{resource_id}/thumbnail.jpg"
    return file_path, thumbnail_path