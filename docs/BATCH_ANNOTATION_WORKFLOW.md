# Batch Annotation Workflow Implementation

## Overview

This document describes the batch-style annotation workflow implemented for the text annotation feature. In this workflow, users accumulate multiple spans locally and submit them all at once, rather than saving each span individually.

## Key Design Decisions

### Why Batch Workflow?

1. **Better User Experience**: Users can review all annotations before committing
2. **Fewer API Calls**: One batch request instead of many individual ones
3. **Error Recovery**: Can fix mistakes before final submission
4. **Atomic Operations**: All spans are saved together, ensuring consistency

### Workflow Comparison

**Previous Workflow (Individual Saves):**
```
Select text → Choose label → Save & Continue → API call → Repeat
Select text → Choose label → Save & Continue → API call → Repeat
Select text → Choose label → Save & Continue → API call → Done
```

**New Workflow (Batch Submission):**
```
Select text → Choose label → Save & Continue → Add to local state
Select text → Choose label → Save & Continue → Add to local state
Select text → Choose label → Save & Continue → Add to local state → Done → One API call
```

## Backend Implementation

### Schema Validation

**File**: `app/annotations/text/schemas.py`

The `TextAnnotationCreate` schema now supports both formats:

1. **Old Format** (backward compatible):
   ```json
   {
     "resource_id": 123,
     "annotation_sub_type": "ner",
     "label": "PERSON",
     "span_start": 10,
     "span_end": 14,
     "annotation_data": { "confidence": 0.95 }
   }
   ```

2. **New Batch Format**:
   ```json
   {
     "resource_id": 123,
     "annotation_sub_type": "ner",
     "spans": [
       {
         "text": "John",
         "label": "PERSON",
         "start": 10,
         "end": 14,
         "confidence": 0.95
       },
       {
         "text": "Google",
         "label": "ORG",
         "start": 50,
         "end": 56,
         "confidence": 0.90
       }
     ]
   }
   ```

### Validation Rules

The schema validates spans in batch mode:

1. **Format Validation**: Either old format OR new format, not both
2. **Span Validation**:
   - `start < end` for each span
   - `text` cannot be empty
   - `label` cannot be empty
3. **Overlap Detection**: Spans cannot overlap (e.g., span A [10:20] and span B [15:25] is invalid)

Example validation error:
```
ValueError: Spans overlap: 'John' [10:14] overlaps with 'John Smith' [10:19]
```

### CRUD Operations

**File**: `app/annotations/text/crud.py`

The `create_annotation` function detects the format and handles both:

```python
def create_annotation(db, project_id, annotator_id, data):
    has_old_format = data.get('label') and data.get('span_start') and data.get('span_end')
    has_new_format = data.get('spans') and len(data.get('spans', [])) > 0
    
    if has_old_format:
        # Handle single span (old model)
        annotation = TextAnnotation(status='draft', **data)
        
    elif has_new_format:
        # Handle batch (new model)
        annotation = TextAnnotation(
            annotation_data={'spans': spans_with_ids},
            status='submitted',  # Batch goes directly to review
            submitted_at=datetime.utcnow()
        )
```

**Key Differences:**

| Aspect | Old Format | Batch Format |
|---------|-----------|--------------|
| Status | `draft` | `submitted` |
| Submission | Manual via separate endpoint | Automatic on creation |
| Review | Requires manual submission | Auto-enqueued for review |

## Frontend Implementation

### Text Annotation Editor

**File**: `src/components/text-annotation/TextAnnotationEditor.jsx`

#### State Management

```javascript
const [pendingSpans, setPendingSpans] = useState([]); // Local accumulation
const [submitError, setSubmitError] = useState('');
```

#### Save & Continue (Local Accumulation)

```javascript
const handleSaveAndContinue = (e) => {
  e.preventDefault();
  
  // Build span object with unique ID
  const spanData = {
    id: `span_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    text: selectedText.text,
    label: selectedLabel,
    start: selectedText.start,
    end: selectedText.end,
    ...buildAnnotationData(selectedLabel)
  };

  // Add to local state (NO API CALL)
  setPendingSpans(prev => [...prev, spanData]);

  // Reset form for next annotation
  setSelectedText({ text: '', start: null, end: null });
  setSelectedLabel('');
  setAnnotationData({});
};
```

#### Pending Spans Display

Users can see all accumulated spans before submission:

```jsx
{showSpanFields && !annotation && pendingSpans.length > 0 && (
  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
    <h4>Pending Spans ({pendingSpans.length}) - Ready to submit</h4>
    {pendingSpans.map((span) => (
      <div key={span.id} className="flex justify-between">
        <span>{span.label} [{span.start}:{span.end}] "{span.text}"</span>
        <button onClick={() => removePendingSpan(span.id)}>
          <Trash2 size={14} />
        </button>
      </div>
    ))}
  </div>
)}
```

#### Remove Pending Span

Users can delete individual spans before submission:

```javascript
const removePendingSpan = (spanId) => {
  setPendingSpans(prev => prev.filter(span => span.id !== spanId));
};
```

#### Batch Submission (Done Button)

```javascript
const handleBatchSubmit = async (e, closeEditor = true) => {
  e.preventDefault();
  
  if (pendingSpans.length === 0) {
    setSubmitError('No spans to submit. Please add at least one annotation.');
    return;
  }

  try {
    const batchData = {
      resource_id: resource.id,
      annotation_type: 'text',
      annotation_sub_type: annotationSubType,
      spans: pendingSpans
    };

    await textAnnotationService.createAnnotation(projectId, batchData);

    // Clear pending spans on success
    setPendingSpans([]);
    setSubmitError('');

    // Refresh annotations in parent
    if (onSave) {
      onSave(batchData, closeEditor);
    }

  } catch (error) {
    // Keep pending spans for retry
    setSubmitError(error.response?.data?.detail || 'Failed to submit annotations. Please try again.');
  }
};
```

### Service Layer

**File**: `src/services/textAnnotationService.js`

The `createAnnotation` function handles both formats:

```javascript
const createAnnotation = async (projectId, data) => {
  const response = await api.post(`/annotations/text/projects/${projectId}/annotations`, data);
  return response.data;
};
```

## User Experience Flow

### Step-by-Step Workflow

1. **Select Resource**: User opens a text resource for annotation
2. **Open Editor**: Click "Create New Annotation"
3. **Select Text**: User highlights text in the text area
4. **Choose Label**: Click a label from the palette
5. **Save & Continue**: Click "Save & Continue" button
   - Span is added to `pendingSpans` array (local only)
   - Form is cleared for next annotation
   - Pending spans count increases
6. **Repeat**: Steps 3-5 can be repeated multiple times
7. **Review Pending**: User can see all pending spans in a list
8. **Remove Spans** (optional): Click trash icon to remove individual spans
9. **Done**: Click "Done" button
   - All pending spans are submitted in one API call
   - If successful: pending spans are cleared, editor closes
   - If error: pending spans are kept for retry with error message
10. **View Results**: Annotation list refreshes to show new annotation with all spans

### Visual Feedback

1. **Pending Counter**: Shows number of pending spans (e.g., "Pending Spans (5)")
2. **Pending List**: Displays each pending span with label, position, and text
3. **Remove Button**: Trash icon for each pending span
4. **Done Button**: Shows count (e.g., "Done (5)")
5. **Error Message**: Appears if submission fails

### Error Handling

**Submission Errors:**

1. **Validation Error** (e.g., overlapping spans):
   - Error message displayed
   - Pending spans kept
   - User can remove problematic spans and retry

2. **Network Error**:
   - Error message displayed
   - Pending spans kept
   - User can retry submission

3. **Server Error**:
   - Error message displayed
   - Pending spans kept
   - User can retry submission

## Data Flow Diagram

```
┌─────────────┐
│ User Action │
│ (Save &    │
│  Continue)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Build Span Object  │
│ - text, label,    │
│   start, end,     │
│   metadata        │
└──────┬────────────┘
       │
       ▼
┌─────────────────────┐
│ Add to pendingSpans│
│ (Local State Only) │
└──────┬────────────┘
       │
       ▼
┌─────────────────────┐
│ Update UI          │
│ - Show count       │
│ - Show list        │
│ - Clear form       │
└─────────────────────┘

... (repeat for multiple spans) ...

┌─────────────┐
│ User Action │
│ (Done)      │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Validate Spans     │
│ - Check count > 0  │
└──────┬────────────┘
       │
       ▼
┌─────────────────────┐
│ Build Batch Data   │
│ {                 │
│   resource_id,     │
│   spans: [...]    │
│ }                 │
└──────┬────────────┘
       │
       ▼
┌─────────────────────┐
│ API Call           │
│ POST /annotations  │
└──────┬────────────┘
       │
       ├─ Success ─────┐
       │              ▼
       │      ┌─────────────────┐
       │      │ Clear State     │
       │      │ Refresh UI      │
       │      └─────────────────┘
       │
       └─ Error ──────┐
                      ▼
              ┌─────────────────┐
              │ Show Error      │
              │ Keep Pending    │
              │ (for retry)    │
              └─────────────────┘
```

## Benefits

### For Users

1. **Review Before Submit**: See all annotations before committing
2. **Easy Corrections**: Remove or fix mistakes before submission
3. **Continuous Workflow**: Annotate multiple spans without interruptions
4. **Better Feedback**: Clear indication of pending work

### For Developers

1. **Simpler Code**: Single batch submission endpoint
2. **Fewer Requests**: Reduced API load
3. **Better Error Handling**: Retry mechanism with preserved state
4. **Backward Compatible**: Old workflow still works

### For System

1. **Reduced Database Load**: Fewer transactions
2. **Atomic Operations**: All spans saved together
3. **Better Performance**: Less network overhead
4. **Consistent State**: Spans are never partially saved

## Backward Compatibility

The implementation maintains full backward compatibility:

1. **Old Format Support**: Single-span annotations still work
2. **Dual-Mode Components**: Components detect and handle both formats
3. **Gradual Migration**: Users can adopt new workflow gradually
4. **No Data Loss**: Existing annotations are preserved

## Testing Recommendations

### Unit Tests

1. Test schema validation for both formats
2. Test span overlap detection
3. Test span ID generation
4. Test batch submission with various span counts

### Integration Tests

1. Test full workflow end-to-end
2. Test error handling and retry
3. Test remove pending span
4. Test submission with empty pending spans

### User Acceptance Tests

1. Test with multiple spans
2. Test with overlapping spans (should fail)
3. Test network error handling
4. Test with different annotation types

## Future Enhancements

Potential improvements:

1. **Draft Persistence**: Save pending spans to localStorage for page refresh
2. **Undo/Redo**: Support undo/redo for pending spans
3. **Span Editing**: Allow editing individual pending spans
4. **Conflict Detection**: Show warnings about potentially problematic spans
5. **Auto-Save**: Periodically save pending spans as drafts
6. **Batch Review**: Show all pending spans in a modal for final review

## Related Documentation

- [Frontend Changes](../../frontend/docs/SINGLE_ANNOTATION_MODEL_FRONTEND_CHANGES.md)
- [Backend Changes](SINGLE_ANNOTATION_MODEL_CHANGES.md)
- [Bug Fixes](BUG_FIXES_FEB_2026.md)
- [Schemas Reference](../app/annotations/text/schemas.py)
- [CRUD Reference](../app/annotations/text/crud.py)