from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

ITEM_TYPES = ["Defect", "Enhancement", "UX Improvement", "Technical Debt", "Performance", "Security", "Documentation"]
ITEM_STATUSES = ["New", "Reviewed", "Approved", "Planned", "In Development", "Ready for Test", "Passed", "Failed", "Released", "Deferred", "Rejected"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
TEST_STATUSES = ["Not Tested", "Pass", "Fail", "Not Applicable"]

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=12, pattern=r"^[A-Za-z0-9]+$")
    github_owner: str = Field(min_length=1, max_length=120)
    github_repo: str = Field(min_length=1, max_length=160)
    repository_url: str | None = None
    default_branch: str = "main"
    roadmap_path: str = "ROADMAP.md"
    changelog_path: str = "CHANGELOG.md"
    active: bool = True

class ProjectOut(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    repository_description: str | None = None
    repository_visibility: str | None = None
    logo_path: str | None = None
    latest_version: str | None = None
    latest_release_url: str | None = None
    latest_release_at: datetime | None = None
    github_refreshed_at: datetime | None = None
    github_last_attempt_at: datetime | None = None
    github_sync_status: str = "Never"
    github_sync_error: str | None = None
    github_cache_json: str | None = None
    roadmap_current_phase_id: int | None = None
    roadmap_next_phase_id: int | None = None

class ProjectDiscover(BaseModel):
    repository_url: str

class ProjectFromUrl(BaseModel):
    repository_url: str
    name: str | None = None
    code: str | None = None
    roadmap_path: str | None = None
    changelog_path: str | None = None

class CriterionCreate(BaseModel):
    description: str = Field(min_length=1)
    sort_order: int = 0

class CriterionOut(CriterionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_id: int

class RegisterItemCreate(BaseModel):
    project_id: int
    roadmap_phase_id: int | None = None
    item_type: str
    title: str = Field(min_length=1, max_length=240)
    description: str = ""
    priority: str = "Medium"
    status: str = "New"
    target_release: str | None = None
    actual_behaviour: str = ""
    expected_behaviour: str = ""
    testing_instructions: str = ""
    notes: str = ""
    criteria: list[CriterionCreate] = []

class RegisterItemUpdate(BaseModel):
    roadmap_phase_id: int | None = None
    item_type: str | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    target_release: str | None = None
    actual_behaviour: str | None = None
    expected_behaviour: str | None = None
    testing_instructions: str | None = None
    notes: str | None = None

class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_name: str
    content_type: str
    size_bytes: int

class RegisterItemOut(RegisterItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_key: str
    created_at: datetime
    updated_at: datetime
    criteria: list[CriterionOut] = []
    attachments: list[AttachmentOut] = []

class ReleaseCreate(BaseModel):
    project_id: int
    planned_version: str | None = None
    notes: str = ""
    item_ids: list[int] = []

class ReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    planned_version: str | None
    actual_version: str | None
    status: str
    release_url: str | None
    pr_url: str | None
    release_at: datetime | None
    notes: str
    roadmap_updated: bool
    changelog_updated: bool
    created_at: datetime

class TestResultUpdate(BaseModel):
    status: str
    notes: str = ""
