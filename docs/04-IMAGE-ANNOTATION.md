# Image Annotation System

**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Annotation Types](#annotation-types)
3. [Shape Types](#shape-types)
4. [API Endpoints](#api-endpoints)
5. [Storage](#storage)

---

## Overview

The image annotation system supports multiple shape types for object detection, segmentation, and keypoint annotation tasks.

### Key Features

- **4 Shape Types**: Bounding Box, Polygon, Keypoint, Segmentation
- **Interactive Canvas**: Draw, edit, and delete shapes
- **S3 Storage**: Images stored in S3-compatible storage
- **Keyboard Shortcuts**: Efficient annotation workflow

---

## Annotation Types

| Type | Description | Use Case |
|------|-------------|----------|
| `bounding_box` | Rectangular regions | Object detection |
| `polygon` | Custom polygons | Instance segmentation |
| `keypoint` | Points with connections | Pose estimation |
| `segmentation` | Pixel-level masks | Semantic segmentation |

---

## Shape Types

### 1. Bounding Box

Rectangular annotation for object detection.

**Data Structure:**
```json
{
  "id": "bbox_001",
  "type": "bounding_box",
  "label": "person",
  "coordinates": {
    "x": 100,
    "y": 150,
    "width": 200,
    "height": 300
  }
}
```

**Keyboard Shortcuts:**
- `B` - Select bounding box tool
- Arrow keys - Move selected box
- `Delete` - Remove selected box

### 2. Polygon

Multi-point polygon for complex shapes.

**Data Structure:**
```json
{
  "id": "poly_001",
  "type": "polygon",
  "label": "car",
  "coordinates": {
    "points": [
      {"x": 100, "y": 100},
      {"x": 200, "y": 100},
      {"x": 200, "y": 200},
      {"x": 100, "y": 200}
    ]
  }
}
```

**Interaction:**
- Click to add points
- Double-click to close polygon
- Drag points to adjust

### 3. Keypoint

Point annotations with optional connections.

**Data Structure:**
```json
{
  "id": "kp_001",
  "type": "keypoint",
  "label": "nose",
  "coordinates": {
    "x": 250,
    "y": 180
  }
}
```

**Pose Estimation Template:**
```json
{
  "keypoints": [
    {"label": "nose", "x": 250, "y": 180},
    {"label": "left_eye", "x": 240, "y": 170},
    {"label": "right_eye", "x": 260, "y": 170},
    {"label": "left_shoulder", "x": 200, "y": 250},
    {"label": "right_shoulder", "x": 300, "y": 250}
  ],
  "connections": [
    ["left_shoulder", "right_shoulder"],
    ["nose", "left_eye"],
    ["nose", "right_eye"]
  ]
}
```

### 4. Segmentation

Pixel-level masks for semantic segmentation.

**Data Structure:**
```json
{
  "id": "seg_001",
  "type": "segmentation",
  "label": "background",
  "coordinates": {
    "mask_url": "s3://bucket/masks/seg_001.png",
    "rle": "encoded_run_length",
    "bbox": [100, 100, 200, 200]
  }
}
```

---

## API Endpoints

### Resource Management

```http
POST   /api/v1/annotations/image/projects/{id}/resources/upload
GET    /api/v1/annotations/image/projects/{id}/resources
GET    /api/v1/annotations/image/projects/{id}/resources/{rid}
DELETE /api/v1/annotations/image/projects/{id}/resources/{rid}
```

### Annotation Management

```http
POST   /api/v1/annotations/image/projects/{id}/annotations
GET    /api/v1/annotations/image/projects/{id}/annotations
GET    /api/v1/annotations/image/projects/{id}/annotations/{aid}
PUT    /api/v1/annotations/image/projects/{id}/annotations/{aid}
DELETE /api/v1/annotations/image/projects/{id}/annotations/{aid}
POST   /api/v1/annotations/image/projects/{id}/annotations/{aid}/submit
POST   /api/v1/annotations/image/projects/{id}/annotations/{aid}/review
```

### Example: Create Image Annotation

```bash
curl -X POST http://localhost:8000/api/v1/annotations/image/projects/1/annotations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "resource_id": 1,
    "annotation_type": "image",
    "annotation_sub_type": "bounding_box",
    "shapes": [
      {
        "type": "bounding_box",
        "label": "person",
        "coordinates": {
          "x": 100,
          "y": 150,
          "width": 200,
          "height": 300
        }
      }
    ]
  }'
```

---

## Storage

### Image Storage

Images are stored in S3-compatible storage:

```
s3://labelling-platform-files/
└── projects/
    └── {project_id}/
        └── images/
            └── {resource_id}.{ext}
```

### Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)
- BMP (.bmp)

### Size Limits

- Maximum file size: 10MB
- Maximum dimensions: 4096 x 4096 pixels

---

## Next Steps

- [05-REVIEW-WORKFLOW.md](05-REVIEW-WORKFLOW.md) - Review and corrections
- [06-API-REFERENCE.md](06-API-REFERENCE.md) - Complete API reference