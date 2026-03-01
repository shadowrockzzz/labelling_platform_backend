# Text Annotation System

**Last Updated:** March 1, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Annotation Sub-Types](#annotation-sub-types)
3. [Batch Workflow](#batch-workflow)
4. [Classification Types](#classification-types)
5. [Custom Labels](#custom-labels)
6. [API Endpoints](#api-endpoints)

---

## Overview

The text annotation system supports multiple annotation types with a batch-style workflow where users accumulate multiple spans locally and submit them all at once.

### Key Features

- **8 Annotation Sub-Types**: NER, POS, Sentiment, Relation, Span, Classification, Dependency, Coreference
- **Batch Workflow**: Accumulate spans, submit together
- **Single-Annotation Model**: One annotation per resource with multiple spans
- **Custom Labels**: Project-specific labels with custom colors
- **S3 Storage**: Files stored in S3-compatible storage

---

## Annotation Sub-Types

### Supported Sub-Types

| Sub-Type | Code | Description | UI Type |
|----------|------|-------------|---------|
| Named Entity Recognition | `ner` | Identify named entities (PERSON, ORG, etc.) | Span selection |
| Part-of-Speech Tagging | `pos` | Tag grammatical parts of speech | Span selection |
| Sentiment Analysis | `sentiment` | Analyze sentiment (positive/negative/neutral) | Quick labels |
| Relation Extraction | `relation` | Identify relationships between entities | Form-based |
| Span/Sequence Labeling | `span` | Label text spans with categories | Span selection |
| Document Classification | `classification` | Classify entire documents | Label selection |
| Dependency Parsing | `dependency` | Analyze grammatical relationships | Form-based |
| Coreference Resolution | `coreference` | Identify mentions of same entity | Span selection |

### Sub-Type Details

#### 1. Named Entity Recognition (NER)

**Labels:** PERSON, ORG, GPE, LOC, DATE, MONEY, PERCENT, TIME, CARDINAL, ORDINAL, EVENT, WORK_OF_ART, LAW, LANGUAGE, PRODUCT, FAC

**Data Structure:**
```json
{
  "annotation_sub_type": "ner",
  "label": "PERSON",
  "span_start": 10,
  "span_end": 25,
  "annotation_data": {
    "entity_text": "John Doe",
    "confidence": 0.95,
    "nested": false
  }
}
```

#### 2. Part-of-Speech Tagging (POS)

**Labels:** NOUN, VERB, ADJ, ADV, PRON, DET, ADP, CONJ, PRT, NUM, X, .

**Data Structure:**
```json
{
  "annotation_sub_type": "pos",
  "label": "NOUN",
  "span_start": 0,
  "span_end": 5,
  "annotation_data": {
    "token": "Apple",
    "token_index": 0,
    "batch": false
  }
}
```

#### 3. Sentiment Analysis

**Labels:** positive, negative, neutral

**Data Structure:**
```json
{
  "annotation_sub_type": "sentiment",
  "label": "positive",
  "annotation_data": {
    "text": "Great product!",
    "intensity": 85,
    "emotions": {
      "joy": 0.7,
      "trust": 0.3
    }
  }
}
```

#### 4. Document Classification

**Labels:** sports, politics, technology, health, entertainment, business, science, world

**Data Structure:**
```json
{
  "annotation_sub_type": "classification",
  "label": "technology",
  "annotation_data": {
    "classification_type": "multi_class",
    "classes": [
      {"label": "technology", "confidence": 0.87},
      {"label": "business", "confidence": 0.10}
    ],
    "reasoning": "Contains technical terminology"
  }
}
```

---

## Batch Workflow

### Overview

The batch workflow allows users to accumulate multiple spans locally before submitting:

```
Select text → Choose label → Save & Continue → Add to local state
Select text → Choose label → Save & Continue → Add to local state
...
Click "Done" → Submit all spans in one API call
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Better UX** | Review all annotations before committing |
| **Fewer API Calls** | One batch request instead of many |
| **Error Recovery** | Fix mistakes before submission |
| **Atomic Operations** | All spans saved together |

### Data Flow

```
User selects text
      ↓
Build span object with unique ID
      ↓
Add to pendingSpans array (local state)
      ↓
Update UI (show pending count)
      ↓
... repeat for multiple spans ...
      ↓
User clicks "Done"
      ↓
POST /annotations with all spans
      ↓
Backend creates single annotation with spans array
```

### Validation

The schema validates spans in batch mode:

1. **Format Validation**: Either old format OR new format, not both
2. **Span Validation**: `start < end`, non-empty text and label
3. **Overlap Detection**: Spans cannot overlap

```python
@validator('spans')
def validate_spans(cls, v):
    for i, span in enumerate(v):
        if span.start >= span.end:
            raise ValueError(f'Span start must be less than end')
    
    # Check for overlaps
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            if v[i].overlaps(v[j]):
                raise ValueError(f"Spans overlap: '{v[i].text}' and '{v[j].text}'")
    return v
```

---

## Classification Types

### Binary Classification

- **Classes:** 2
- **Selection:** Mutually exclusive (exactly one)
- **UI Pattern:** Radio buttons or toggle

```json
{
  "classification_type": "binary",
  "options": ["spam", "not_spam"]
}
```

### Multi-Class Classification

- **Classes:** 3 or more
- **Selection:** Mutually exclusive (exactly one)
- **UI Pattern:** Radio buttons or single-select

```json
{
  "classification_type": "multi_class",
  "options": ["sports", "politics", "technology", "health"]
}
```

### Multi-Label Classification

- **Classes:** 3 or more
- **Selection:** Not mutually exclusive (0, 1, or many)
- **UI Pattern:** Checkboxes or multi-select

```json
{
  "classification_type": "multi_label",
  "selected_labels": ["action", "comedy", "romance"]
}
```

### Decision Tree

```
How many classes?
├─ 2 classes → Binary
└─ 3+ classes → Can items belong to multiple classes?
              ├─ No (mutually exclusive) → Multi-Class
              └─ Yes (can have multiple) → Multi-Label
```

---

## Custom Labels

### Overview

Projects can define custom labels with specific colors for text annotation.

### Configuration

```json
{
  "annotation_type": "text",
  "config": {
    "textSubType": "ner",
    "useCustomLabels": true,
    "customLabels": [
      {"name": "PERSON", "color": "#FF5733"},
      {"name": "ORGANIZATION", "color": "#33FF57"},
      {"name": "LOCATION", "color": "#3357FF"}
    ],
    "classificationType": "multi_class"
  }
}
```

### Label Structure

```python
class CustomLabel(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$')  # Hex color
```

### Label Palette Behavior

The LabelPalette component adapts based on project configuration:

```javascript
// Auto-detect classification type
const classificationType = projectConfig?.classificationType || 'multi_class';

// Handle selection based on type
if (classificationType === 'multi_label') {
  // Toggle label selection (can select multiple)
  setSelectedLabels(prev => 
    prev.includes(label) 
      ? prev.filter(l => l !== label)
      : [...prev, label]
  );
} else {
  // Single selection (binary or multi-class)
  onLabelSelect(label);
}
```

---

## API Endpoints

### Resource Management

```http
POST   /api/v1/annotations/text/projects/{id}/resources/upload
POST   /api/v1/annotations/text/projects/{id}/resources/url
GET    /api/v1/annotations/text/projects/{id}/resources
GET    /api/v1/annotations/text/projects/{id}/resources/{rid}
DELETE /api/v1/annotations/text/projects/{id}/resources/{rid}
```

### Annotation Management

```http
POST   /api/v1/annotations/text/projects/{id}/annotations
GET    /api/v1/annotations/text/projects/{id}/annotations
GET    /api/v1/annotations/text/projects/{id}/annotations/{aid}
PUT    /api/v1/annotations/text/projects/{id}/annotations/{aid}
DELETE /api/v1/annotations/text/projects/{id}/annotations/{aid}
POST   /api/v1/annotations/text/projects/{id}/annotations/{aid}/submit
POST   /api/v1/annotations/text/projects/{id}/annotations/{aid}/review
```

### Span Management (Single-Annotation Model)

```http
POST   /api/v1/annotations/text/projects/{id}/resources/{rid}/spans
GET    /api/v1/annotations/text/projects/{id}/resources/{rid}/annotation
PUT    /api/v1/annotations/text/projects/{id}/annotations/{aid}/spans/{sid}
DELETE /api/v1/annotations/text/projects/{id}/annotations/{aid}/spans/{sid}
```

### Queue Management

```http
GET    /api/v1/annotations/text/projects/{id}/queue
```

### Example: Create Batch Annotation

```bash
curl -X POST http://localhost:8000/api/v1/annotations/text/projects/1/annotations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "resource_id": 1,
    "annotation_type": "text",
    "annotation_sub_type": "ner",
    "spans": [
      {
        "text": "John Doe",
        "label": "PERSON",
        "start": 0,
        "end": 8
      },
      {
        "text": "Google",
        "label": "ORG",
        "start": 20,
        "end": 26
      }
    ]
  }'
```

---

## Next Steps

- [05-REVIEW-WORKFLOW.md](05-REVIEW-WORKFLOW.md) - Review and corrections
- [06-API-REFERENCE.md](06-API-REFERENCE.md) - Complete API reference