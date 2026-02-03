# Custom Labels Feature

## Overview
This feature allows project managers and administrators to define custom labels and colors for text annotation projects, replacing the system-defined default labels when needed.

## Features

### 1. Label Configuration in Project Settings
- **Default Labels**: Use system-defined labels for each annotation sub-type (NER, POS, etc.)
- **Custom Labels**: Define your own labels with custom hex colors
- **Label Limits**: 1-20 labels per project
- **Validation**: 
  - Unique label names (case-insensitive)
  - Valid hex color codes (#RRGGBB format)
  - Non-empty label names

### 2. Color Picker Component
- Native browser color picker for full color spectrum
- Custom hex color input option
- Real-time color preview
- Color validation (#RRGGBB format)
- Clean, simplified interface

### 3. Label Editor Component
- Toggle between default and custom labels
- Add/remove labels dynamically (1-20 labels)
- Edit label names and colors
- Visual validation feedback
- Auto-capitalizes label names for consistency
- Starts with single empty label when enabling custom labels
- Preserves label selection when re-editing projects

### 4. Backward Compatibility
- Projects without custom labels automatically use system defaults
- Existing projects continue to work without modification
- Migration path: Update project config to enable custom labels

## Implementation Details

### Backend Changes

#### 1. Schema Validation (`app/schemas/project.py`)
```python
class LabelConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$')
```

#### 2. Project Config Structure
```json
{
  "textSubType": "ner",
  "useCustomLabels": true,
  "customLabels": [
    {
      "name": "PERSON",
      "color": "#3B82F6"
    },
    {
      "name": "ORGANIZATION",
      "color": "#10B981"
    }
  ]
}
```

### Frontend Changes

#### 1. New Components
- `ColorPicker.jsx` - Color selection interface
- `LabelEditor.jsx` - Label configuration interface
- Integrated into `ProjectForm.jsx`

#### 2. Updated Components
- `LabelPalette.jsx` - Supports custom labels from project config
- `TextAnnotationEditor.jsx` - Receives and uses project config
- `TextAnnotationWorkspace.jsx` - Passes project config to editor

#### 3. Label Display
- Custom colors rendered using inline styles
- Automatic contrast calculation for text color
- "Custom" badge when using custom labels

## Usage

### For Project Managers/Admins

1. **Create/Edit Project**
   - Navigate to project form (create or edit)
   - Select "Text Annotation" as annotation type
   - Choose annotation sub-type (NER, POS, etc.)
   - Locate "Label Palette Configuration" section

2. **Use Custom Labels**
   - Select "Use Custom Labels" radio button
   - Starts with one empty label automatically
   - Click "Add Label" to create additional labels (up to 20)
   - Set label name (e.g., "PERSON")
   - Click color box to open native color picker or type hex code
   - Add more labels as needed (1-20)

3. **Use Default Labels**
   - Select "Use Default Labels" radio button
   - System will use predefined labels for the sub-type

### For Annotators

- Open annotation workspace for a project
- Label palette displays labels based on project configuration
- Custom labels appear with "Custom" badge
- Labels use configured colors
- No additional setup required

## Label Sub-Types and Defaults

### NER (Named Entity Recognition)
- PERSON, ORGANIZATION, LOCATION, DATE, TIME, MONEY, PERCENT, GPE

### POS (Part-of-Speech)
- NOUN, VERB, ADJ, ADV, PRON, DET, ADP, CONJ

### Sentiment
- POSITIVE, NEGATIVE, NEUTRAL, MIXED

### Span
- SPAN, SEGMENT, PHRASE, CLAUSE

### Relation
- SUBJECT, OBJECT, PREPOSITION, CONJUNCTION

### Classification
- CLASS_1, CLASS_2, CLASS_3, CLASS_4, CLASS_5

### Dependency
- ROOT, NMOD, DOBJ, IOBJ, POBJ

### Coreference
- ENTITY, PRONOUN, PROPER_NOUN

## API Examples

### Create Project with Custom Labels
```bash
POST /api/v1/projects/
{
  "name": "Medical Entity Recognition",
  "description": "Custom labels for medical text",
  "annotation_type": "text",
  "config": {
    "textSubType": "ner",
    "useCustomLabels": true,
    "customLabels": [
      {"name": "DISEASE", "color": "#EF4444"},
      {"name": "SYMPTOM", "color": "#F59E0B"},
      {"name": "MEDICATION", "color": "#10B981"}
    ]
  }
}
```

### Update Project Labels
```bash
PATCH /api/v1/projects/{project_id}/
{
  "config": {
    "customLabels": [
      {"name": "DISEASE", "color": "#EF4444"},
      {"name": "SYMPTOM", "color": "#F59E0B"},
      {"name": "MEDICATION", "color": "#10B981"},
      {"name": "DOSAGE", "color": "#3B82F6"}
    ]
  }
}
```

## Color Guidelines

### Recommended Colors
- **Blue tones**: `#3B82F6`, `#2563EB`, `#60A5FA`
- **Green tones**: `#10B981`, `#059669`, `#34D399`
- **Red tones**: `#EF4444`, `#DC2626`, `#F472B6`
- **Orange tones**: `#F59E0B`, `#F97316`, `#FBBF24`
- **Purple tones**: `#8B5CF6`, `#7C3AED`, `#A78BFA`

### Contrast Considerations
- Lighter backgrounds (lightness > 128): Use dark text
- Darker backgrounds (lightness <= 128): Use white text
- System automatically calculates appropriate text color

## Limitations

1. **Maximum Labels**: 20 labels per project
2. **Label Name Length**: 1-50 characters
3. **Color Format**: Only hex (#RRGGBB) supported
4. **Sub-Type**: Custom labels are per annotation sub-type
5. **Project Scope**: Labels are project-specific, not global

## Testing

### Manual Testing Steps

1. **Create Project with Default Labels**
   - Verify system labels appear correctly
   - Test annotation creation with default labels

2. **Create Project with Custom Labels**
   - Add 3-5 custom labels with different colors
   - Verify labels appear in palette
   - Test annotation creation with custom labels

3. **Edit Project Labels**
   - Change label names
   - Update colors
   - Add/remove labels
   - Verify changes reflect in annotation workspace

4. **Backward Compatibility**
   - Open existing project (no custom labels)
   - Verify default labels work
   - Verify no errors in console

5. **Edge Cases**
   - Try to add duplicate label names
   - Try to add invalid hex colors
   - Try to remove all labels (minimum 1 required)
   - Try to add more than 20 labels

## Future Enhancements

1. **Label Groups**: Organize labels into categories
2. **Label Hierarchies**: Parent-child label relationships
3. **Label Templates**: Save and reuse label configurations
4. **Label Import/Export**: JSON or CSV import/export
5. **Color Themes**: Pre-defined color schemes
6. **Label Shortcuts**: Keyboard shortcuts for common labels
7. **Label Statistics**: Track label usage frequency
8. **Label Suggestions**: ML-based label suggestions

## Troubleshooting

### Labels Not Appearing
- Check `useCustomLabels` flag in project config
- Verify `customLabels` array is not empty
- Check browser console for errors
- Verify project was saved successfully

### Colors Not Displaying
- Verify hex format (#RRGGBB)
- Check for valid color codes
- Clear browser cache

### Validation Errors
- Ensure label names are unique (case-insensitive)
- Check hex color format
- Verify label count is within limits (1-20)
- Ensure label names are not empty

### Radio Button Toggles While Typing
- This issue has been fixed
- Component now properly handles state updates
- Radio buttons remain stable during editing

### Toggle Resets to "Default Labels"
- This issue has been fixed
- Custom label selection is now preserved
- Project config is properly loaded on re-edit

### Console Errors: "handleConfigChange is not defined"
- This has been fixed
- All syntax errors resolved
- Component functions properly updated

## Related Files

### Backend
- `app/schemas/project.py` - Schema validation
- `app/models/project.py` - Database model
- `app/crud/project.py` - CRUD operations
- `app/api/v1/projects.py` - API endpoints

### Frontend
- `src/components/projects/ColorPicker.jsx`
- `src/components/projects/LabelEditor.jsx`
- `src/components/projects/ProjectForm.jsx`
- `src/features/text-annotation/components/LabelPalette.jsx`
- `src/components/text-annotation/TextAnnotationEditor.jsx`
- `src/components/text-annotation/TextAnnotationWorkspace.jsx`