import asyncio
import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import bleach
import markdown
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .assisted_requirements import ai_status, analyse_requirement
from .database import Base, SessionLocal, engine, get_db
from .github_service import GitHubService
from .models import AcceptanceCriterion, AcceptanceTestResult, Attachment, Project, RegisterItem, Release, ReleaseItem, RoadmapItem, RoadmapPhase, RoadmapSnapshot
from .prompt_builder import build_release_prompt
from .reconciliation import compare_changelog, reconcile_release
from .roadmap_parser import parse_roadmap
from .schemas import AssistedRequirementDraft, AssistedRequirementRequest, ProjectCreate, ProjectDiscover, ProjectFromUrl, ProjectOut, RegisterItemCreate, RegisterItemOut, RegisterItemUpdate, ReleaseCreate, ReleaseOut, TestResultUpdate, TEST_STATUSES

APP_VERSION = "0.5.2"
DATA_DIR = Path(os.getenv("DEVHUB_DATA_DIR", "./data"))
UPLOAD_DIR = DATA_DIR / "uploads"
PROJECT_LOGO_DIR = DATA_DIR / "project-logos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_LOGO_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "video/quicktime", "video/webm"}
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}
BACKGROUND_SYNC_SECONDS = max(300, int(os.getenv("DEVHUB_SYNC_INTERVAL_SECONDS", "900")))

Base.metadata.create_all(bind=engine)


def project_or_404(db: Session, project_id: int) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


def item_or_404(db: Session, item_id: int) -> RegisterItem:
    stmt = select(RegisterItem).options(selectinload(RegisterItem.criteria), selectinload(RegisterItem.attachments)).where(RegisterItem.id == item_id)
    item = db.scalar(stmt)
    if not item:
        raise HTTPException(404, "Register item not found")
    return item


def make_item_key(db: Session, project: Project, item_type: str) -> str:
    type_code = {"Defect": "DEF", "Enhancement": "ENH", "UX Improvement": "UX", "Technical Debt": "TECH", "Performance": "PERF", "Security": "SEC", "Documentation": "DOC"}.get(item_type, "ITEM")
    prefix = f"{project.code.upper()}-{type_code}-"
    count = db.scalar(select(func.count(RegisterItem.id)).where(RegisterItem.item_key.like(f"{prefix}%"))) or 0
    return f"{prefix}{count + 1:04d}"
