# Review Workflow

**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Annotation Lifecycle](#annotation-lifecycle)
3. [Review Corrections](#review-corrections)
4. [Editing Reviewed Annotations](#editing-reviewed-annotations)
5. [API Endpoints](#api-endpoints)

---

## Overview

The review workflow provides a complete system for reviewing, approving, rejecting, and suggesting corrections to annotations while maintaining a full audit trail.

### Key Features

- **Complete Lifecycle**: Draft → Submitted → Reviewed → Approved/Rejected
- **Review Corrections**: Suggest changes without modifying original
- **Audit Trail**: Full history of all changes and decisions
- **Status Management**: Automatic status transitions

---

## Annotation Lifecycle

### Status Flow

```
┌─────────────┐
│    Draft    │     Annotator creates/edits
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Submitted  │     Annotator submits for review
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Under Review│     Reviewer opens annotation
└──────┬──────┘
       │
       ├───────────────────────┐
       ▼                       ▼
┌──────────────┐        ┌──────────────┐
│   Approved   │        │   Rejected   │
└──────────────┘        └──────────────┘
       │                       │
       │                       ▼
       │                ┌──────────────┐
       │                │    Draft     │  Annotator edits
       │                └──────────────┘
       │                       │
       └───────────────────────┘
```

### Status Definitions

| Status | Description | Who Can Edit |
|--------|-------------|--------------|
| `draft` | Work in progress | Annotator, Reviewer |
| `submitted` | Awaiting review | Nobody |
| `approved` | Accepted by reviewer | Nobody (final) |
| `rejected` | Rejected with feedback | Annotator, Reviewer |

### Reviewer Edit Permissions

Reviewers have direct edit access to annotations in the following scenarios:

| Action | Text Annotations | Image Annotations |
|--------|-----------------|-------------------|
| Update full annotation | ✅ | ✅ |
| Update individual span/shape | ✅ | ✅ |
| Delete individual span/shape | ✅ | ✅ |
| Add new span/shape | ✅ (via add span endpoint) | ✅ (via add shape endpoint) |

**Important:** When a reviewer edits an annotation they didn't create:
- The annotation status is reset to `draft`
- Review fields (reviewer_id, review_comment, reviewed_at) are cleared
- The annotation goes through the review workflow again

This ensures proper workflow tracking while allowing reviewers to make direct corrections when needed.

---

## Review Corrections

### Overview

The review corrections system allows reviewers to suggest changes to annotations without directly modifying the original data. Annotators can then accept or reject these suggestions.

### Benefits

| Benefit | Description |
|---------|-------------|
| **Audit Trail** | Complete history of all correction attempts |
| **Original Preserved** | Original annotation data never lost |
| **Transparency** | Full visibility into all changes |
| **Annotator Control** | Annotators decide whether to accept changes |

### Workflow

```
Reviewer reviews annotation
         ↓
Reviewer suggests corrections
         ↓
Correction stored (status: pending)
         ↓
Annotator views pending corrections
         ↓
Annotator accepts or rejects
         ↓
If accepted: Annotation updated, correction status → accepted
If rejected: Correction status → rejected
```

### Data Model

```python
class ReviewCorrection(Base):
    __tablename__ = "review_corrections"
    
    id = Column(Integer, primary_key=True)
    annotation_id = Column(Integer, ForeignKey("text_annotations.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    
    corrected_data = Column(JSON)  # The suggested corrections
    comment = Column(Text)         # Reviewer's explanation
    status = Column(String)        # pending, accepted, rejected
    
    annotator_response = Column(Text)  # Annotator's feedback
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

### Creating a Correction

```bash
curl -X POST http://localhost:8000/api/v1/annotations/text/projects/1/annotations/5/corrections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer REVIEWER_TOKEN" \
  -d '{
    "corrected_data": {
      "spans": [
        {"text": "John Smith", "label": "PERSON", "start": 0, "end": 10}
      ]
    },
    "comment": "Please update the entity name to include full surname"
  }'
```

### Accepting a Correction

```bash
curl -X POST "http://localhost:8000/api/v1/annotations/text/projects/1/corrections/3/accept?annotator_response=Thanks%20for%20the%20correction" \
  -H "Authorization: Bearer ANNOTATOR_TOKEN"
```

---

## Editing Reviewed Annotations

### Behavior Changes

When editing annotations that have been reviewed (approved or rejected), the system automatically:

1. **Resets status to draft** - Allows annotator to make changes
2. **Clears review fields** - Removes reviewer_id, review_comment, reviewed_at
3. **Preserves annotation data** - Original data remains intact

### Implementation

```python
def update_annotation(db, annotation_id, update_data, user_id):
    annotation = get_annotation(db, annotation_id)
    
    # Check if annotation was reviewed
    if annotation.status in ['approved', 'rejected']:
        # Reset to draft and clear review fields
        annotation.status = 'draft'
        annotation.reviewer_id = None
        annotation.review_comment = None
        annotation.reviewed_at = None
        annotation.submitted_at = None
    
    # Apply updates
    for field, value in update_data.items():
        setattr(annotation, field, value)
    
    db.commit()
    return annotation
```

### User Experience

```
Before Edit:
┌─────────────────────────────────┐
│ Status: Approved                │
│ Reviewer: John Doe              │
│ Review Comment: Looks good!     │
└─────────────────────────────────┘

User clicks "Edit"

After Edit:
┌─────────────────────────────────┐
│ Status: Draft                   │
│ Reviewer: -                     │
│ Review Comment: -               │
└─────────────────────────────────┘
```

---

## API Endpoints

### Review Actions

```http
# Submit annotation for review
POST /api/v1/annotations/text/projects/{id}/annotations/{aid}/submit

# Review annotation (approve/reject)
POST /api/v1/annotations/text/projects/{id}/annotations/{aid}/review
```

### Review Request Body

```json
{
  "action": "approve",  // or "reject"
  "comment": "Great work on the NER annotations!"
}
```

### Correction Endpoints

```http
# Create correction suggestion
POST /api/v1/annotations/text/projects/{id}/annotations/{aid}/corrections

# List corrections for annotation
GET /api/v1/annotations/text/projects/{id}/annotations/{aid}/corrections

# Get specific correction
GET /api/v1/annotations/text/projects/{id}/corrections/{cid}

# Accept correction
POST /api/v1/annotations/text/projects/{id}/corrections/{cid}/accept

# Reject correction
POST /api/v1/annotations/text/projects/{id}/corrections/{cid}/reject
```

---

## Next Steps

- [06-API-REFERENCE.md](06-API-REFERENCE.md) - Complete API reference
- [CHANGELOG.md](CHANGELOG.md) - Version history and bug fixes