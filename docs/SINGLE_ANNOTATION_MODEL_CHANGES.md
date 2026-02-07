# Single-Annotation Model Implementation

## Overview

This document describes the implementation of the single-annotation model for the labeling platform, where one resource = ONE annotation containing all labeled spans/entities.

## Summary of Changes

### Backend Changes (Completed)

#### 1. Updated Schemas (`app/annotations/text/schemas.py`)

**New Schemas Added:**
- `SpanData` - Generic span data structure for all annotation types
- `SpanCreate` - Schema for adding a single span to an existing annotation
- `SpanUpdate` - Schema for updating a specific span within an annotation

**Modified Schemas:**
- `TextAnnotationCreate` - Now supports both old (single span) and new (spans array) formats
  - Added `spans` field for new format
  - Kept old fields for backward compatibility

#### 2. Updated CRUD Operations (`app/annotations/text/crud.py`)

**New Functions Added:**
- `is_array_annotation(annotation)` - Check if annotation uses new array-based format
- `get_or_create_annotation(db, project_id, annotator_id, resource_id, annotation_sub_type)` - Get existing annotation or create new one with empty spans array
- `add_span_to_annotation(db, annotation_id, span_data)` - Add a new span to existing annotation
- `remove_span_from_annotation(db, annotation_id, span_id)` - Remove specific span from annotation
- `update_span_in_annotation(db, annotation_id, span_id, span_updates)` - Update specific span
- `get_annotation_with_spans(db, resource_id, annotator_id)` - Get annotation with all spans

#### 3. Updated Service Layer (`app/annotations/text/service.py`)

**Modified Functions:**
- `format_annotation_output(annotation)` - Now supports both old and new formats
  - Detects format using `is_array_annotation()`
  - Returns type-specific output for spans array
  - Maintains backward compatibility for old format

**New Service Functions Added:**
- `add_span_to_annotation_service(db, project_id, annotator_id, resource_id, annotation_sub_type, span_data)` - Service layer for adding spans
- `remove_span_from_annotation_service(db, project_id, user_id, annotation_id, span_id)` - Service layer for removing spans
- `update_span_in_annotation_service(db, project_id, user_id, annotation_id, span_id, span_updates)` - Service layer for updating spans
- `get_annotation_with_spans_service(db, project_id, resource_id, user_id)` - Service layer for getting annotations

#### 4. Updated API Endpoints (`app/annotations/text/router.py`)

**New Endpoints Added:**

```
POST   /api/v1/annotations/text/projects/{project_id}/resources/{resource_id}/spans
        - Add a span to an annotation for a resource
        - Query params: annotation_sub_type (default: "ner")
        - Body: SpanCreate schema
        - Creates annotation if doesn't exist, otherwise appends

GET    /api/v1/annotations/text/projects/{project_id}/resources/{resource_id}/annotation
        - Get annotation for a resource with all spans
        - Query params: user_id (optional, filter by annotator)
        - Returns: TextAnnotationResponse with all spans in annotation_data.spans

PUT    /api/v1/annotations/text/projects/{project_id}/annotations/{annotation_id}/spans/{span_id}
        - Update a specific span within an annotation
        - Body: SpanUpdate schema (partial updates allowed)
        - Only annotator who created the annotation can update

DELETE /api/v1/annotations/text/projects/{project_id}/annotations/{annotation_id}/spans/{span_id}
        - Remove a specific span from an annotation
        - Only annotator who created the annotation can delete
```

## Data Structure

### New Format (Spans Array)

```json
{
  "id": 1,
  "resource_id": 100,
  "project_id": 10,
  "annotator_id": 5,
  "annotation_type": "text",
  "annotation_sub_type": "ner",
  "status": "draft",
  "label": null,
  "span_start": null,
  "span_end": null,
  "annotation_data": {
    "spans": [
      {
        "id": "span_abc123",
        "text": "John Doe",
        "label": "PERSON",
        "start": 0,
        "end": 8,
        "confidence": 0.95,
        "nested": false
      },
      {
        "id": "span_def456",
        "text": "Google",
        "label": "ORG",
        "start": 20,
        "end": 26,
        "confidence": 0.98
      }
    ]
  },
  "created_at": "2026-02-07T15:00:00Z",
  "updated_at": "2026-02-07T15:01:00Z"
}
```

### Old Format (Backward Compatible)

```json
{
  "id": 1,
  "resource_id": 100,
  "project_id": 10,
  "annotator_id": 5,
  "annotation_type": "text",
  "annotation_sub_type": "ner",
  "status": "submitted",
  "label": "PERSON",
  "span_start": 0,
  "span_end": 8,
  "annotation_data": {
    "entity_text": "John Doe",
    "confidence": 0.95
  },
  "created_at": "2026-02-07T15:00:00Z"
}
```

## Annotation Sub-Types

The new model supports all annotation sub-types:
- `ner` - Named Entity Recognition
- `pos` - Part-of-Speech Tagging
- `sentiment` - Sentiment/Emotion Analysis
- `relation` - Relation Extraction
- `span` - Span/Sequence Labeling
- `classification` - Document Classification
- `dependency` - Dependency Parsing
- `coreference` - Coreference Resolution

Each sub-type has its own metadata fields in the span structure.

## Backward Compatibility

- Old annotations (with individual records) remain as-is
- Frontend can detect format using `is_array_annotation()`
- No migration script needed
- Gradual transition possible

## Frontend Implementation Requirements

### Files to Update

1. **`src/hooks/useTextAnnotations.js`**
   - Add functions: `addSpanToAnnotation()`, `updateSpan()`, `deleteSpan()`
   - Modify `submitAnnotation()` to work with spans array

2. **`src/components/text-annotation/TextAnnotationEditor.jsx`**
   - Maintain local state for all spans: `localSpans = []`
   - "Add Span" button adds span to `localSpans` array
   - Display added spans in editor (list view)
   - Allow editing/removing individual spans before submission
   - "Submit Annotation" button submits all spans together

3. **`src/components/text-annotation/AnnotationList.jsx`**
   - Show one annotation per resource
   - Expand to view all spans inside
   - Each span can be viewed but not individually reviewed
   - Review action applies to entire annotation

4. **`src/components/text-annotation/ReviewPanel.jsx`**
   - Reviewer sees one annotation with all spans
   - Approve/reject entire annotation
   - Add comment for overall feedback

5. **`src/features/text-annotation/components/HighlightableTextArea.jsx`**
   - Highlight all spans from `annotation_data.spans` array
   - Show hover tooltips for each span

### New API Calls

```javascript
// Add span to annotation
POST /api/v1/annotations/text/projects/{projectId}/resources/{resourceId}/spans
Body: {
  text: "John Doe",
  label: "PERSON",
  start: 0,
  end: 8,
  annotation_sub_type: "ner"
}

// Get annotation with spans
GET /api/v1/annotations/text/projects/{projectId}/resources/{resourceId}/annotation

// Update specific span
PUT /api/v1/annotations/text/projects/{projectId}/annotations/{annotationId}/spans/{spanId}
Body: {
  label: "ORG",  // Partial update
  confidence: 0.98
}

// Delete specific span
DELETE /api/v1/annotations/text/projects/{projectId}/annotations/{annotationId}/spans/{spanId}
```

### New Workflow for Annotators

1. **Old Workflow:**
   - Select text → Select label → Click "Save" → Creates new annotation → Editor stays open
   - Each "Save" creates separate annotation record
   - Multiple annotations per resource

2. **New Workflow:**
   - Select text → Select label → Click "Add Span" → Adds to `localSpans` array → Editor stays open
   - Repeat for all spans
   - Click "Submit Annotation" → Submits all spans together as one annotation
   - One annotation per resource with all spans

### New Workflow for Reviewers

**Old Workflow:**
- See list of individual annotations
- Review and approve/reject each separately

**New Workflow:**
- See one annotation per resource
- Expand to view all spans inside
- Approve/reject entire annotation
- Provide overall feedback

## Testing Plan

1. **Backend Testing:**
   - [ ] Create new annotation with multiple spans
   - [ ] Verify all spans stored in one record
   - [ ] Test adding span to existing annotation
   - [ ] Test updating specific span
   - [ ] Test deleting specific span
   - [ ] Verify old annotations still work
   - [ ] Test annotation submission and review

2. **Frontend Testing:**
   - [ ] Add multiple spans to local state
   - [ ] Submit annotation with all spans
   - [ ] View annotation with all spans
   - [ ] Edit individual span
   - [ ] Delete individual span
   - [ ] Reviewer approves complete annotation
   - [ ] Backward compatibility with old annotations

## Benefits

✅ **Single Annotation Per Resource** - Clean data model  
✅ **Better Review Workflow** - Reviewer sees complete annotation  
✅ **Backward Compatible** - Existing data unchanged  
✅ **Consistent Across All Types** - NER, POS, Sentiment, etc.  
✅ **No Migration Needed** - Gradual transition possible  
✅ **Improved Performance** - Fewer database records  

## Migration Strategy

### Phase 1: Backend (Completed)
- ✅ Add new schemas, CRUD, service, and endpoints
- ✅ Maintain backward compatibility

### Phase 2: Frontend (To Be Done)
- Update components to use new endpoints
- Implement new workflow for annotators
- Update reviewer interface

### Phase 3: Gradual Rollout
- Start new annotations with new model
- Existing annotations remain in old format
- Optional: Provide migration script for old data

### Phase 4: Complete Transition (Optional)
- After validation, migrate old annotations to new format
- Remove old code paths

## Status

- ✅ Backend schemas updated
- ✅ Backend CRUD operations updated
- ✅ Backend service layer updated
- ✅ Backend API endpoints updated
- ⏳ Frontend components to be updated
- ⏳ Frontend testing to be completed
- ⏳ Documentation updates to be completed

## Next Steps

1. Update frontend components (see Frontend Implementation Requirements above)
2. Test new workflow with real data
3. Update user documentation
4. Train annotators and reviewers on new workflow
5. Monitor and gather feedback
6. Iterate based on user feedback