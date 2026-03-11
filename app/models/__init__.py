from app.models.user import User
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment

# Note: Legacy models removed (annotation, dataset, review_correction)
# Use app.annotations.text.models and app.annotations.image.models instead

__all__ = ["User", "Project", "ProjectAssignment"]
