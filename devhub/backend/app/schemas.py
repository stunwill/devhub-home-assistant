from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    roadmap_current_override: bool = False
    roadmap_next_override: bool = False
    changelog_source_sha: str | None = None
    changelog_parsed_version: str | None = None
    changelog_parsed_at: datetime | None = None
    changelog_status: str | None = None
    github_rate_limit_remaining: int | None = None
    github_rate_limit_limit: int | None = None
    github_rate_limit_reset_at: datetime | None = None
    github_backoff_until: datetime | None = None
    github_failure_count: int = 0

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
    roadmap_phase_id: int | None = None
    notes: str = ""
    item_ids: list[int] = []

class ReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    roadmap_phase_id: int | None = None
    planned_version: str | None
    actual_version: str | None
    status: str
    release_url: str | None
    pr_url: str | None
    release_at: datetime | None
    notes: str
    roadmap_updated: bool
    changelog_updated: bool
    roadmap_reconciliation_status: str | None = None
    changelog_reconciliation_status: str | None = None
    created_at: datetime

class TestResultUpdate(BaseModel):
    status: str
    notes: str = ""

class AssistedAttachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(default=0, ge=0, le=100 * 1024 * 1024)
    data_base64: str = Field(default="", max_length=72_000_000)

class AssistedRequirementRequest(BaseModel):
    project_id: int
    feedback: str = Field(min_length=1, max_length=8000)
    attachments: list[AssistedAttachment] = Field(default_factory=list, max_length=6)

class CandidateItem(BaseModel):
    id: int
    item_key: str
    title: str
    item_type: str
    status: str
    priority: str
    roadmap_phase_id: int | None = None
    score: float = 0
    match_reason: str | None = None

class EvidenceObservation(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    timestamp: str | None = Field(default=None, max_length=16)
    observation: str = Field(min_length=1, max_length=2000)
    confidence: Literal["High", "Moderate", "Low", "Unable to determine"] = "Moderate"
    evidence_type: Literal["direct", "inferred", "ambiguous"] = "direct"

class EvidenceAnalysis(BaseModel):
    summary: str = Field(default="", max_length=8000)
    analysed_sources: list[str] = Field(default_factory=list, max_length=12)
    observations: list[EvidenceObservation] = Field(default_factory=list, max_length=30)
    warnings: list[str] = Field(default_factory=list, max_length=20)

class AssistedRequirementDraft(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    item_type: str
    description: str = Field(default="", max_length=12000)
    actual_behaviour: str = Field(default="", max_length=8000)
    expected_behaviour: str = Field(default="", max_length=8000)
    priority: str = "Medium"
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=20)
    testing_instructions: str = Field(default="", max_length=12000)
    suggested_roadmap_phase_id: int | None = None
    duplicate_candidates: list[CandidateItem] = Field(default_factory=list, max_length=8)
    related_candidates: list[CandidateItem] = Field(default_factory=list, max_length=8)
    evidence: EvidenceAnalysis = Field(default_factory=EvidenceAnalysis)
    warnings: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("item_type")
    @classmethod
    def valid_item_type(cls, value: str) -> str:
        if value not in ITEM_TYPES:
            raise ValueError("Invalid item type")
        return value

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value: str) -> str:
        if value not in PRIORITIES:
            raise ValueError("Invalid priority")
        return value

    @field_validator("acceptance_criteria")
    @classmethod
    def clean_criteria(cls, value: list[str]) -> list[str]:
        result = []
        for item in value:
            text = str(item).strip()
            if text:
                result.append(text[:1000])
        return result[:20]
