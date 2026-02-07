# Review Corrections Feature

## Overview

The Review Corrections feature provides an audit trail workflow for annotation review. Reviewers can suggest corrections to annotations without directly modifying them, and the original annotators can accept or reject these corrections.

## Architecture

### Audit Trail Approach (Option B)

This implementation uses an **audit trail** approach where:
1. Reviewers create corrections as separate records
2. Original annotations remain unchanged
3. Annotators review and decide to accept/reject corrections
4. Accepted corrections update the original annotation
5. Full history is preserved

### Database Model

#### `review_corrections` Table

```sql
CREATE TABLE review_corrections (
    id SERIAL PRIMARY KEY,
    annotation_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    original_data JSONB,
    corrected_data JSONB,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    annotator_response TEXT,
    FOREIGN KEY (annotation_id) REFERENCES text_annotations(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
);
```

**Fields:**
- `id`: Unique identifier for the correction
- `annotation_id`: Link to the original annotation
- `reviewer_id`: ID of the reviewer who created the correction
- `status`: Correction status (`pending`, `accepted`, `rejected`)
- `original_data`: Snapshot of original annotation data (for comparison)
- `corrected_data`: The corrected annotation data
- `comment`: Reviewer's explanation for the correction
- `annotator_response`: Optional response from original annotator
- `created_at`, `updated_at`: Timestamps

### Relationships

- **TextAnnotation**: `review_corrections` (one-to-many, cascade delete)
- **User**: `reviewer` (many-to-one)
- **User**: `annotator` (via annotation)

## API Endpoints

### Create Correction

**POST** `/api/v1/annotations/text/projects/{project_id}/annotations/{annotation_id}/corrections`

Create a new review correction for an annotation.

**Request Body:**
```json
{
  "annotation_id": 123,
  "corrected_data": {
    "spans": [
      {
        "id": "span_abc123",
        "text": "Apple Inc.",
        "label": "ORG",
        "start": 0,
        "end": 10
      }
    ]
  },
  "comment": "The entity should be labeled as ORG, not PER"
}
```

**Response:** `ReviewCorrectionResponse`

**Permissions:** `admin`, `reviewer`, `project_manager`

---

### List Corrections

**GET** `/api/v1/annotations/text/projects/{project_id}/annotations/{annotation_id}/corrections`

List all review corrections for an annotation.

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `accepted`, `rejected`)
- `page` (default: 1): Page number for pagination
- `limit` (default: 20): Items per page

**Response:** `ReviewCorrectionListResponse`

---

### Get Single Correction

**GET** `/api/v1/annotations/text/projects/{project_id}/corrections/{correction_id}`

Get details of a specific correction.

**Response:** `ReviewCorrectionResponse`

---

### Update Correction

**PUT** `/api/v1/annotations/text/projects/{project_id}/corrections/{correction_id}`

Update a correction status (accept or reject).

**Request Body:**
```json
{
  "status": "accepted",
  "annotator_response": "Thank you for the correction, I've applied it."
}
```

**Response:** `ReviewCorrectionResponse`

**Permissions:** Only the original annotator of the annotation

**Constraints:**
- Only pending corrections can be updated
- Status must be `accepted` or `rejected`

---

### Accept Correction

**POST** `/api/v1/annotations/text/projects/{project_id}/corrections/{correction_id}/accept`

Accept a correction and apply it to the original annotation.

**Query Parameters:**
- `annotator_response` (optional): Optional response from annotator

**Response:** `TextAnnotationResponse` (the updated annotation)

**Permissions:** Only the original annotator of the annotation

**Behavior:**
1. Applies `corrected_data` to the original annotation
2. Marks correction status as `accepted`
3. Stores annotator response if provided
4. Updates annotation `updated_at` timestamp

## Workflow

### 1. Reviewer Creates Correction

```
Reviewer → Create Correction → Status: pending
```

1. Reviewer identifies issue with annotation
2. Creates correction with:
   - Corrected annotation data
   - Explanation comment
3. Correction is saved with `pending` status
4. Annotator is notified (optional - depends on notification system)

### 2. Annotator Reviews Correction

```
Annotator → Accept/Reject → Status: accepted/rejected
```

**Option A: Accept Correction**
1. Annotator reviews correction
2. Calls `/corrections/{id}/accept`
3. System applies corrected data to original annotation
4. Correction status becomes `accepted`
5. Annotation is updated with new data

**Option B: Reject Correction**
1. Annotator reviews correction
2. Calls `/corrections/{id}/update` with status=`rejected`
3. Provides optional response explaining why
4. Correction status becomes `rejected`
5. Original annotation remains unchanged

### 3. Audit Trail

All corrections are preserved in the database:
- Pending corrections: Awaiting annotator action
- Accepted corrections: Applied to annotation
- Rejected corrections: Rejected by annotator

This provides:
- Complete history of annotation changes
- Accountability for reviewer decisions
- Annotator control over final data

## Migration

Run the migration to create the `review_corrections` table:

```bash
cd labelling_platform_backend
python migration_add_review_corrections.py
```

To rollback:
```bash
python migration_add_review_corrections.py --downgrade
```

## Frontend Implementation

### API Service

Add to `textAnnotationService.js`:

```javascript
// Create correction
export const createCorrection = async (projectId, annotationId, correctedData, comment) => {
  const token = localStorage.getItem('token');
  const response = await fetch(
    `${API_URL}/projects/${projectId}/annotations/${annotationId}/corrections`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        annotation_id: annotationId,
        corrected_data: correctedData,
        comment: comment
      })
    }
  );
  return response.json();
};

// List corrections
export const listCorrections = async (projectId, annotationId, status = null) => {
  const token = localStorage.getItem('token');
  let url = `${API_URL}/projects/${projectId}/annotations/${annotationId}/corrections`;
  if (status) url += `?status=${status}`;
  
  const response = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// Accept correction
export const acceptCorrection = async (projectId, correctionId, response = null) => {
  const token = localStorage.getItem('token');
  let url = `${API_URL}/projects/${projectId}/corrections/${correctionId}/accept`;
  if (response) url += `?annotator_response=${encodeURIComponent(response)}`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

### Review Panel UI

Update `ReviewPanel.jsx` to include:
1. List of pending corrections for current annotation
2. Button to create new correction
3. UI to review and accept/reject corrections
4. Display of original vs corrected data

## Benefits

1. **Accountability**: Track who made what changes and why
2. **Annotator Control**: Annotators have final say on their work
3. **Collaboration**: Reviewers can provide constructive feedback
4. **Audit Trail**: Complete history of all annotation changes
5. **Non-destructive**: Original work preserved until explicitly accepted

## Future Enhancements

Potential improvements:
1. **Notifications**: Alert annotators when new corrections are created
2. **Bulk Operations**: Accept/reject multiple corrections at once
3. **Correction History**: Show timeline of all corrections on an annotation
4. **Dispute Resolution**: Allow escalation for disputed corrections
5. **Analytics**: Track correction acceptance rates by reviewer