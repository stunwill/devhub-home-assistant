import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

os.environ["DEVHUB_DATABASE_URL"] = "sqlite:///./test-assisted-devhub.db"
os.environ["DEVHUB_DATA_DIR"] = "./test-assisted-data"

from backend.app.assisted_requirements import candidate_items
from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.models import Project, RoadmapPhase, RoadmapSnapshot

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    os.environ["DEVHUB_AI_ENABLED"] = "true"
    os.environ["DEVHUB_AI_API_KEY"] = "test-key"
    os.environ["DEVHUB_AI_MODEL"] = "test-model"
    os.environ["DEVHUB_AI_PROVIDER"] = "openai"


def teardown_function():
    Base.metadata.drop_all(bind=engine)


def create_project() -> int:
    response = client.post('/api/projects', json={
        "name": "Test App", "code": "TA", "github_owner": "owner", "github_repo": "repo",
        "repository_url": "https://github.com/owner/repo", "default_branch": "main",
        "roadmap_path": "ROADMAP.md", "changelog_path": "CHANGELOG.md", "active": True,
    })
    assert response.status_code == 201
    return response.json()["id"]


def valid_draft(phase_id=None):
    return {
        "title": "Fix mobile horizontal overflow",
        "item_type": "Defect",
        "description": "The page exceeds the mobile viewport.",
        "actual_behaviour": "The page scrolls sideways.",
        "expected_behaviour": "The page remains within the viewport.",
        "priority": "High",
        "acceptance_criteria": ["The page does not horizontally scroll at 390 px."],
        "testing_instructions": "Open through Home Assistant ingress at 390 px and verify no horizontal scrolling.",
        "suggested_roadmap_phase_id": phase_id,
        "warnings": [],
    }


def test_successful_structured_analysis_is_advisory_only():
    project_id = create_project()
    before = client.get('/api/register').json()
    with patch('backend.app.assisted_requirements.OpenAICompatibleProvider.analyse', new=AsyncMock(return_value=valid_draft())):
        response = client.post('/api/assisted-requirements/analyse', json={"project_id": project_id, "feedback": "Mobile page scrolls sideways", "attachments": []})
    assert response.status_code == 200
    assert response.json()["item_type"] == "Defect"
    assert response.json()["priority"] == "High"
    assert client.get('/api/register').json() == before


def test_provider_failure_returns_502_without_creating_item():
    project_id = create_project()
    with patch('backend.app.assisted_requirements.OpenAICompatibleProvider.analyse', new=AsyncMock(side_effect=Exception("provider offline"))):
        response = client.post('/api/assisted-requirements/analyse', json={"project_id": project_id, "feedback": "A useful feedback sentence", "attachments": []})
    assert response.status_code == 502
    assert client.get('/api/register').json() == []


def test_invalid_provider_response_is_rejected():
    project_id = create_project()
    with patch('backend.app.assisted_requirements.OpenAICompatibleProvider.analyse', new=AsyncMock(return_value={"title": "Bad", "item_type": "Invented", "priority": "Urgent"})):
        response = client.post('/api/assisted-requirements/analyse', json={"project_id": project_id, "feedback": "A useful feedback sentence", "attachments": []})
    assert response.status_code == 502
    assert "validation" in response.text.lower()


def test_duplicate_candidates_are_deterministic_and_local():
    project_id = create_project()
    existing = client.post('/api/register', json={
        "project_id": project_id, "item_type": "Defect", "title": "Mobile horizontal overflow",
        "description": "Mobile page scrolls sideways beyond the viewport", "priority": "High", "status": "New",
        "actual_behaviour": "Horizontal scroll on mobile", "expected_behaviour": "No horizontal scroll", "testing_instructions": "Test at 390 px", "criteria": []
    })
    assert existing.status_code == 201
    db = SessionLocal()
    try:
        duplicates, related = candidate_items(db, project_id, "Mobile horizontal overflow page scrolls sideways beyond viewport")
        assert duplicates or related
        assert (duplicates + related)[0].item_key == existing.json()["item_key"]
    finally:
        db.close()


def test_invalid_roadmap_suggestion_is_cleared():
    project_id = create_project()
    with patch('backend.app.assisted_requirements.OpenAICompatibleProvider.analyse', new=AsyncMock(return_value=valid_draft(99999))):
        response = client.post('/api/assisted-requirements/analyse', json={"project_id": project_id, "feedback": "A useful feedback sentence", "attachments": []})
    assert response.status_code == 200
    assert response.json()["suggested_roadmap_phase_id"] is None


def test_valid_current_roadmap_suggestion_is_retained():
    project_id = create_project()
    db = SessionLocal()
    try:
        snapshot = RoadmapSnapshot(project_id=project_id, source_path="ROADMAP.md", markdown_text="# Roadmap", parse_status="Parsed")
        db.add(snapshot); db.flush()
        phase = RoadmapPhase(project_id=project_id, snapshot_id=snapshot.id, version="v0.5.x", title="Assisted Requirements", phase_type="Version", status="In Progress", sort_order=1, heading_level=2, raw_heading="v0.5.x Assisted Requirements")
        db.add(phase); db.flush()
        project = db.get(Project, project_id)
        project.roadmap_current_phase_id = phase.id
        db.commit()
        phase_id = phase.id
    finally:
        db.close()
    with patch('backend.app.assisted_requirements.OpenAICompatibleProvider.analyse', new=AsyncMock(return_value=valid_draft(phase_id))):
        response = client.post('/api/assisted-requirements/analyse', json={"project_id": project_id, "feedback": "A useful feedback sentence", "attachments": []})
    assert response.status_code == 200
    assert response.json()["suggested_roadmap_phase_id"] == phase_id


def test_invalid_image_encoding_becomes_warning_not_crash():
    project_id = create_project()
    with patch('backend.app.assisted_requirements.OpenAICompatibleProvider.analyse', new=AsyncMock(return_value=valid_draft())):
        response = client.post('/api/assisted-requirements/analyse', json={
            "project_id": project_id,
            "feedback": "The screenshot shows an error",
            "attachments": [{"name": "error.png", "content_type": "image/png", "size_bytes": 10, "data_base64": "%%%not-base64%%%"}],
        })
    assert response.status_code == 200
    assert any("invalid image encoding" in warning.lower() for warning in response.json()["warnings"])


def test_unsupported_evidence_type_is_reported():
    project_id = create_project()
    with patch('backend.app.assisted_requirements.OpenAICompatibleProvider.analyse', new=AsyncMock(return_value=valid_draft())):
        response = client.post('/api/assisted-requirements/analyse', json={
            "project_id": project_id,
            "feedback": "A useful feedback sentence",
            "attachments": [{"name": "notes.pdf", "content_type": "application/pdf", "size_bytes": 20, "data_base64": ""}],
        })
    assert response.status_code == 200
    assert any("unsupported evidence type" in warning.lower() for warning in response.json()["warnings"])
