# Annotation Editing Fixes

## Overview

Implemented fixes to enable proper editing of annotations that have been reviewed (approved or rejected). Previously, the edit functionality was broken for reviewed annotations, preventing annotators from fixing issues identified during review.

## Problem Statement

When an annotation was reviewed (either approved or rejected), clicking the **Edit** button would fail to properly load the annotation editor. This prevented annotators from:

1. Fixing issues pointed out by reviewers
2. Correcting their work after receiving feedback
3. Resubmitting improved annotations

### Root Causes

1. **Backend**: No automatic status reset when editing reviewed annotations
2. **Frontend**: Editor wasn't auto-loading the annotation's resource content
3. **Frontend**: Editor wasn't initializing with existing annotation spans
4. **Frontend**: Save handler was creating new annotations instead of updating existing ones

## Solution

### 1. Backend: Automatic Status Reset

**File**: `app/annotations/text/router.py`

Modified the `update_annotation_endpoint` to automatically reset annotation status to "draft" when editing reviewed annotations.

```python
@router.put("/{project_id}/annotations/{annotation_id}", response_model=TextAnnotationResponse)
def update_annotation_endpoint(...):
    # ... existing validation code ...
    
    # If annotation is reviewed (approved or rejected), reset to draft when edited
    update_data = annotation_data.model_dump(exclude_unset=True)
    if annotation.status in ["approved", "rejected"]:
        # Reset to draft and clear review fields
        update_data["status"] = "draft"
        update_data["reviewer_id"] = None
        update_data["review_comment"] = None
        update_data["reviewed_at"] = None
        # Keep the original created_at and annotator_id
    
    annotation = update_annotation(db, annotation_id, update_data)
    return annotation
```

**Benefits**:
- Annotators can fix rejected work and resubmit
- Reviewers can request changes to approved work
- Clean workflow: edit → save → draft → resubmit
- Preserves original annotation metadata (created_at, annotator_id)

### 2. Frontend: Auto-load Resource Content

**File**: `src/components/text-annotation/TextAnnotationWorkspace.jsx`

Updated `handleEditAnnotation` to automatically load the annotation's resource when clicking Edit.

```javascript
const handleEditAnnotation = async (annotation) => {
  setEditingAnnotation(annotation);
  
  // If no resource is selected or different resource, load it
  if (!selectedResource || selectedResource.id !== annotation.resource_id) {
    try {
      setLoadingResource(true);
      const fullResource = await getResource(annotation.resource_id);
      setSelectedResource(fullResource);
      setResourceWithContent(fullResource);
    } catch (error) {
      alert('Failed to load annotation resource: ' + 
            (error.response?.data?.error || error.message));
      return; // Don't show editor if resource fails to load
    } finally {
      setLoadingResource(false);
    }
  } else if (!resourceWithContent || resourceWithContent.id !== annotation.resource_id) {
    // Resource selected but content not loaded
    try {
      setLoadingResource(true);
      const fullResource = await getResource(annotation.resource_id);
      setResourceWithContent(fullResource);
    } catch (error) {
      alert('Failed to load resource content: ' + 
            (error.response?.data?.error || error.message));
      return;
    } finally {
      setLoadingResource(false);
    }
  }
  
  setShowEditor(true);
};
```

**Benefits**:
- Editor always has required resource data
- No manual resource selection needed when editing
- Graceful error handling with user feedback

### 3. Frontend: Initialize Editor with Existing Spans

**File**: `src/components/text-annotation/TextAnnotationEditor.jsx`

Added initialization logic to populate editor with existing annotation spans.

```javascript
useEffect(() => {
  if (annotation) {
    setSelectedLabel(annotation.label || '');
    setAnnotationData(annotation.annotation_data || {});
    
    // For span-based annotations, populate pendingSpans with existing spans
    if (showSpanFields && annotation.annotation_data?.spans) {
      setPendingSpans(annotation.annotation_data.spans);
    }
  } else {
    // Clear pending spans when not editing
    setPendingSpans([]);
  }
}, [annotation, showSpanFields]);
```

**Benefits**:
- Editor shows existing spans when editing
- Users can see what they're modifying
- Spans are displayed with labels and positions

### 4. Frontend: Update vs Create Logic

**File**: `src/components/text-annotation/TextAnnotationEditor.jsx`

Modified `handleBatchSubmit` to distinguish between creating new annotations and updating existing ones.

```javascript
const handleBatchSubmit = async (e, closeEditor = true) => {
  // ... validation code ...
  
  try {
    if (annotation) {
      // Editing existing annotation - update it
      const updateData = {
        annotation_data: {
          spans: pendingSpans.length > 0 
            ? pendingSpans 
            : annotation.annotation_data?.spans || []
        }
      };
      await textAnnotationService.updateAnnotation(projectId, annotation.id, updateData);
    } else {
      // Creating new annotation
      const batchData = {
        resource_id: resource.id,
        annotation_type: 'text',
        annotation_sub_type: annotationSubType,
        spans: pendingSpans
      };
      await textAnnotationService.createAnnotation(projectId, batchData);
    }
    
    // Clear pending spans on success
    setPendingSpans([]);
    setSubmitError('');
    
    // Call onSave to refresh annotations in parent
    if (onSave) {
      onSave(null, closeEditor);
    }
  } catch (error) {
    // ... error handling ...
  }
};
```

**Benefits**:
- Correct API endpoint called for each scenario
- No duplicate annotations created
- Properly updates existing annotations

### 5. Frontend: UI Enhancements

Updated the editor UI to better support editing:

- **Existing Spans Display**: Shows "Existing Spans" when editing (vs "Pending Spans" for new)
- **Done Button**: Now works for both creating and editing span-based annotations
- **Save & Continue**: Only shows when creating (not editing)
- **Instructions**: Updated to reflect editing workflow

## Workflows

### Editing a Rejected Annotation

1. **Annotator** sees annotation with status "REJECTED" and review comment
2. Clicks **Edit** button
3. System auto-loads the annotation's resource content
4. Editor opens displaying all existing spans
5. Annotator can:
   - Modify existing spans (remove or update)
   - Add new spans
   - Fix issues identified in review comment
6. Clicks **Done** to save changes
7. Annotation status resets to "draft" (review fields cleared)
8. Annotator clicks **Submit** to resubmit for review

### Editing an Approved Annotation

1. **Annotator** sees annotation with status "APPROVED"
2. Clicks **Edit** button
3. System auto-loads the annotation's resource content
4. Editor opens displaying all existing spans
5. Annotator makes changes
6. Clicks **Done** to save changes
7. Annotation status resets to "draft" (review fields cleared)
8. Annotator must resubmit for re-approval

### Editing a Draft Annotation

1. **Annotator** sees annotation with status "draft"
2. Clicks **Edit** button
3. System auto-loads the annotation's resource content
4. Editor opens displaying all existing spans
5. Annotator makes changes
6. Clicks **Done** to save changes
7. Annotation remains in "draft" status (no review involved)

## Technical Details

### Status Transition Logic

| Initial Status | After Edit | After Save | Review Fields |
|----------------|-------------|-------------|---------------|
| draft | - | draft | Unchanged |
| submitted | N/A* | draft | Unchanged |
| rejected | - | **draft** | **Cleared** |
| approved | - | **draft** | **Cleared** |

*Note: "submitted" annotations cannot be edited; they must be reviewed first.

### Cleared Review Fields

When an annotation is edited after review, the following fields are cleared:

- `reviewer_id` - ID of the reviewer
- `review_comment` - Reviewer's feedback
- `reviewed_at` - Timestamp of review

### Preserved Fields

The following fields are preserved:

- `created_at` - Original creation timestamp
- `annotator_id` - Original annotator ID
- `project_id` - Project association
- `resource_id` - Resource association

## Files Modified

### Backend

- `app/annotations/text/router.py` - Added status reset logic in `update_annotation_endpoint`

### Frontend

- `src/components/text-annotation/TextAnnotationWorkspace.jsx` - Auto-load resource when editing
- `src/components/text-annotation/TextAnnotationEditor.jsx` - Initialize with spans, update vs create logic

## Testing

### Test Cases

1. **Edit Rejected Annotation**
   - Create annotation, submit, reject with comment
   - Click Edit - should load resource and show spans
   - Modify spans, click Done
   - Verify status is "draft", review fields cleared
   - Submit again for review

2. **Edit Approved Annotation**
   - Create annotation, submit, approve
   - Click Edit - should load resource and show spans
   - Modify spans, click Done
   - Verify status is "draft", review fields cleared
   - Submit again for review

3. **Edit Draft Annotation**
   - Create annotation with spans
   - Click Edit - should load resource and show spans
   - Add/remove spans, click Done
   - Verify status remains "draft"

4. **Edit with Different Resource**
   - Have annotation for Resource A
   - Select Resource B
   - Click Edit annotation for Resource A
   - Verify Resource A is loaded, not Resource B

5. **Error Handling**
   - Mock network error when loading resource
   - Verify alert shown, editor doesn't open
   - Verify state is clean for retry

## Benefits

1. **User Experience**: Smooth workflow for fixing reviewed work
2. **Collaboration**: Enables iterative improvement through review
3. **Quality**: Reviewers can request changes, annotators can respond
4. **Flexibility**: Both approved and rejected annotations can be edited
5. **Data Integrity**: Preserves original metadata while enabling updates

## Future Enhancements

1. **Edit History**: Track all edit operations on annotations
2. **Versioning**: Store previous annotation versions
3. **Diff View**: Show changes between annotation versions
4. **Notifications**: Alert reviewers when annotations are resubmitted
5. **Bulk Edit**: Edit multiple annotations at once

## Related Documentation

- [Review Corrections Feature](REVIEW_CORRECTIONS_FEATURE.md) - Alternative review workflow
- [Batch Annotation Workflow](BATCH_ANNOTATION_WORKFLOW.md) - Creating multiple spans
- [Single Annotation Model Changes](SINGLE_ANNOTATION_MODEL_CHANGES.md) - Annotation data structure
- [Frontend Implementation Guide](../labelling_platform_frontend/docs/REVIEW_EDIT_IMPLEMENTATION.md) - Frontend details