import asyncio
import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
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
from .roadmap_parser import lifecycle_status, parse_roadmap, semantic_version, version_contains, version_order_key
from .schemas import AssistedRequirementDraft, AssistedRequirementRequest, ProjectCreate, ProjectDiscover, ProjectFromUrl, ProjectOut, ProjectUpdate, RegisterItemCreate, RegisterItemOut, RegisterItemUpdate, ReleaseCreate, ReleaseOut, TestResultUpdate, TEST_STATUSES

APP_VERSION = "0.5.10"
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


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_utc(value: datetime | None):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


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


def default_code(repo: str) -> str:
    parts = [x for x in re.split(r"[^A-Za-z0-9]+", repo) if x and x.lower() not in {"home", "assistant"}]
    if not parts:
        return "APP"
    if len(parts) == 1:
        return parts[0][:12].upper()
    return "".join(p[0] for p in parts)[:12].upper()


def friendly_project_name(repo: str) -> str:
    base = re.sub(r"-home-assistant$", "", repo, flags=re.I).strip("-_ ") or repo
    return " ".join(part[:1].upper() + part[1:] for part in re.split(r"[-_]+", base) if part)


def open_pr_summary(prs: list[dict]) -> list[dict]:
    return [{"number": p.get("number"), "title": p.get("title"), "url": p.get("html_url"), "created_at": p.get("created_at"), "updated_at": p.get("updated_at"), "draft": bool(p.get("draft")), "head": (p.get("head") or {}).get("ref")} for p in prs]


def _phase_dict(phase: RoadmapPhase, detected_version: str | None = None) -> dict:
    return {
        "id": phase.id,
        "version": phase.version,
        "title": phase.title,
        "phase_type": phase.phase_type,
        "status": phase.status,
        "lifecycle_status": lifecycle_status(phase, detected_version),
        "sort_order": phase.sort_order,
        "heading_level": phase.heading_level,
        "raw_heading": phase.raw_heading,
        "ignored": phase.ignored,
        "items": [{"id": i.id, "text": i.text, "completed": i.completed, "sort_order": i.sort_order} for i in phase.items],
        "linked_register_items": [{"id": i.id, "item_key": i.item_key, "title": i.title, "item_type": i.item_type, "status": i.status} for i in phase.register_items],
        "planned_releases": [{"id": r.id, "planned_version": r.planned_version, "actual_version": r.actual_version, "status": r.status} for r in phase.releases if r.status != "Released"],
        "completed_releases": [{"id": r.id, "planned_version": r.planned_version, "actual_version": r.actual_version, "status": r.status} for r in phase.releases if r.status == "Released"],
    }


def _choose_current_next(project: Project, phases: list[RoadmapPhase]) -> tuple[int | None, int | None]:
    selectable = [p for p in phases if not p.ignored]
    active = [p for p in selectable if p.phase_type != "Future"]
    future_bucket = next((p for p in selectable if p.phase_type == "Future"), None)
    if not active:
        return None, future_bucket.id if future_bucket else None

    detected = semantic_version(project.latest_version)
    if project.roadmap_current_override and project.roadmap_current_phase_id and any(p.id == project.roadmap_current_phase_id for p in selectable):
        current = next(p for p in selectable if p.id == project.roadmap_current_phase_id)
    else:
        exact_or_band = next((p for p in active if detected and version_contains(p.version, project.latest_version)), None)
        if exact_or_band:
            current = exact_or_band
        else:
            current = next((p for p in active if p.status == "In Progress" and (not detected or not version_order_key(p.version) or version_order_key(p.version) <= detected)), None)
            if not current and detected:
                historical = [(version_order_key(p.version), p) for p in active if version_order_key(p.version) and version_order_key(p.version) <= detected]
                current = max(historical, key=lambda pair: pair[0])[1] if historical else None
            current = current or next((p for p in active if p.status == "Unknown" and not detected), active[-1] if not detected else None)

    if project.roadmap_next_override and project.roadmap_next_phase_id and any(p.id == project.roadmap_next_phase_id for p in selectable):
        nxt = next(p for p in selectable if p.id == project.roadmap_next_phase_id)
    else:
        baseline = detected
        current_key = version_order_key(current.version) if current and current.phase_type != "Future" else None
        if current_key and (not baseline or current_key > baseline):
            baseline = current_key
        candidates = []
        if baseline:
            candidates = [(version_order_key(p.version), p) for p in active if version_order_key(p.version) and version_order_key(p.version) > baseline]
        elif current_key:
            candidates = [(version_order_key(p.version), p) for p in active if version_order_key(p.version) and version_order_key(p.version) > current_key]
        nxt = min(candidates, key=lambda pair: pair[0])[1] if candidates else future_bucket
    return current.id if current else None, nxt.id if nxt else None


def _sync_phase_selection(project: Project, phases: list[RoadmapPhase]):
    current_id, next_id = _choose_current_next(project, phases)
    if not project.roadmap_current_override:
        project.roadmap_current_phase_id = current_id
    if not project.roadmap_next_override:
        project.roadmap_next_phase_id = next_id


async def sync_roadmap_record(p: Project, db: Session, force: bool = False):
    gh = GitHubService()
    text, meta = await gh.file_text_and_metadata(p.github_owner, p.github_repo, p.roadmap_path, p.default_branch)
    if text is None:
        return {"status": "Missing", "phases": [], "warnings": ["Configured roadmap file was not found"]}
    latest = db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id == p.id).order_by(RoadmapSnapshot.id.desc()))
    if latest and not force and meta and latest.source_sha == meta.get("sha"):
        _sync_phase_selection(p, list(latest.phases)); db.commit()
        return {"status": latest.parse_status, "snapshot_id": latest.id, "phases": [_phase_dict(x, p.latest_version) for x in latest.phases], "warnings": []}
    previous_ignored = {(x.version or "", x.title): x.ignored for x in (latest.phases if latest else [])}
    parsed = parse_roadmap(text)
    snapshot = RoadmapSnapshot(project_id=p.id, source_path=p.roadmap_path, source_sha=(meta or {}).get("sha"), markdown_text=text, fetched_at=utcnow_naive(), parsed_at=utcnow_naive(), parse_status=parsed["status"], parse_error="; ".join(parsed.get("warnings") or []) or None)
    db.add(snapshot); db.flush()
    phases: list[RoadmapPhase] = []
    for phase_data in parsed.get("phases", []):
        key = (phase_data.get("version") or "", phase_data.get("title") or phase_data.get("heading"))
        phase = RoadmapPhase(project_id=p.id, snapshot_id=snapshot.id, version=phase_data.get("version"), title=phase_data.get("title") or phase_data.get("heading"), phase_type=phase_data.get("phase_type", "Section"), status=phase_data.get("status", "Unknown"), sort_order=phase_data.get("sort_order", 0), heading_level=phase_data.get("heading_level", 2), raw_heading=phase_data.get("raw_heading") or phase_data.get("heading", ""), ignored=previous_ignored.get(key, False))
        db.add(phase); db.flush()
        for item in phase_data.get("items", []):
            db.add(RoadmapItem(roadmap_phase_id=phase.id, text=item["text"], completed=bool(item.get("completed")), sort_order=item.get("sort_order", 0)))
        phases.append(phase)
    db.flush(); _sync_phase_selection(p, phases); db.commit()
    return {"status": parsed["status"], "snapshot_id": snapshot.id, "phases": [_phase_dict(x, p.latest_version) for x in phases], "warnings": parsed.get("warnings") or []}


async def sync_changelog_record(p: Project, db: Session, force: bool = False):
    gh = GitHubService()
    text, meta = await gh.file_text_and_metadata(p.github_owner, p.github_repo, p.changelog_path, p.default_branch)
    if not force and meta and p.changelog_source_sha == meta.get("sha") and p.changelog_parsed_at:
        return {"status": p.changelog_status or "Unable to determine", "version": p.changelog_parsed_version, "source_sha": p.changelog_source_sha, "parsed_at": p.changelog_parsed_at}
    state = compare_changelog(text, p.latest_version)
    p.changelog_source_sha = (meta or {}).get("sha")
    p.changelog_parsed_version = state.get("version")
    p.changelog_parsed_at = utcnow_naive()
    p.changelog_status = state.get("status")
    db.commit()
    return {**state, "source_sha": p.changelog_source_sha, "parsed_at": p.changelog_parsed_at}


def _latest_release_for_project(db: Session, p: Project):
    return db.scalar(select(Release).options(selectinload(Release.roadmap_phase).selectinload(RoadmapPhase.items), selectinload(Release.roadmap_phase).selectinload(RoadmapPhase.register_items)).where(Release.project_id == p.id).order_by(Release.created_at.desc()))


async def reconciliation_for_project(p: Project, db: Session):
    changelog_state = await sync_changelog_record(p, db, force=False)
    release = _latest_release_for_project(db, p)
    phase = release.roadmap_phase if release and release.roadmap_phase else (db.get(RoadmapPhase, p.roadmap_current_phase_id) if p.roadmap_current_phase_id else None)
    result = reconcile_release(p.latest_version, release, phase, changelog_state)
    if release:
        release.roadmap_reconciliation_status = result["status"]
        release.changelog_reconciliation_status = changelog_state.get("status")
        db.commit()
    return result


async def sync_project_record(p: Project, db: Session):
    now = utcnow_naive()
    if p.github_backoff_until and p.github_backoff_until > now:
        return {"skipped": True, "reason": "Backoff active until GitHub retry window"}
    gh = GitHubService(); p.github_last_attempt_at = now
    try:
        data = await gh.discover_repository(p.repository_url or f"https://github.com/{p.github_owner}/{p.github_repo}")
        version = data.get("version") or {}; commit = data.get("latest_commit"); rate = data.get("rate_limit") or {}
        previous_version = p.latest_version
        p.repository_url = data.get("repository_url"); p.repository_description = data.get("description"); p.repository_visibility = data.get("visibility"); p.default_branch = data.get("default_branch") or p.default_branch
        if version.get("version"):
            p.latest_version = version.get("version"); p.latest_release_url = version.get("url"); p.latest_release_at = gh.parse_github_datetime(version.get("published_at"))
        p.github_rate_limit_remaining = rate.get("remaining"); p.github_rate_limit_limit = rate.get("limit"); p.github_rate_limit_reset_at = rate.get("reset_at")
        ci = dict(data.get("ci") or {})
        ci["commit_sha"] = commit.get("sha") if commit else None
        p.github_cache_json = json.dumps({"open_pr_count": len(data.get("open_prs") or []), "open_prs": open_pr_summary(data.get("open_prs") or []), "last_merged_pr": data.get("last_merged_pr"), "latest_commit": commit, "ci": ci, "version_source": version.get("source", "Unknown"), "version_evidence": version.get("evidence") or [], "rate_limit": {"remaining": p.github_rate_limit_remaining, "limit": p.github_rate_limit_limit, "reset_at": iso_utc(p.github_rate_limit_reset_at)}})
        p.github_refreshed_at = utcnow_naive(); p.github_sync_status = "Synced"; p.github_sync_error = None; p.github_failure_count = 0; p.github_backoff_until = None
        db.commit(); db.refresh(p)
        try: await sync_roadmap_record(p, db, force=False)
        except Exception: pass
        try: await sync_changelog_record(p, db, force=False)
        except Exception: pass
        if previous_version != p.latest_version:
            try: await reconciliation_for_project(p, db)
            except Exception: pass
        return data
    except Exception as exc:
        p.github_sync_status = "Failed"; p.github_sync_error = str(exc); p.github_failure_count = (p.github_failure_count or 0) + 1
        delay_minutes = min(60, 2 ** min(p.github_failure_count, 5))
        if "authentication failed" in str(exc).lower(): delay_minutes = 60
        if "rate limit" in str(exc).lower() and p.github_rate_limit_reset_at: p.github_backoff_until = p.github_rate_limit_reset_at
        else: p.github_backoff_until = utcnow_naive() + timedelta(minutes=delay_minutes)
        db.commit(); raise


async def sync_active_projects_once():
    db = SessionLocal()
    try:
        for project in db.scalars(select(Project).where(Project.active == True)).all():
            try: await sync_project_record(project, db)
            except Exception: continue
    finally: db.close()


async def background_sync_loop():
    while True:
        await asyncio.sleep(BACKGROUND_SYNC_SECONDS); await sync_active_projects_once()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(background_sync_loop())
    try: yield
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass


app = FastAPI(title="DevHub", version=APP_VERSION, lifespan=lifespan)

@app.get("/api/health")
def health(): return {"status": "ok", "version": APP_VERSION}

@app.get("/api/assisted-requirements/status")
def assisted_requirements_status(): return ai_status()

@app.post("/api/assisted-requirements/analyse", response_model=AssistedRequirementDraft)
async def assisted_requirements_analyse(payload: AssistedRequirementRequest, db: Session = Depends(get_db)):
    project = project_or_404(db, payload.project_id)
    try:
        return await analyse_requirement(db, project, payload)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except ValueError as exc:
        raise HTTPException(502, str(exc))
    except Exception:
        raise HTTPException(502, "Assisted requirement analysis failed")

@app.get("/api/projects", response_model=list[ProjectOut])
def projects(db: Session = Depends(get_db)): return list(db.scalars(select(Project).order_by(Project.name)))

@app.post("/api/projects/discover")
async def discover_project(payload: ProjectDiscover):
    try: return await GitHubService().discover_repository(payload.repository_url)
    except ValueError as exc: raise HTTPException(422, str(exc))
    except Exception as exc: raise HTTPException(502, f"GitHub discovery failed: {exc}")

@app.post("/api/projects/from-url", response_model=ProjectOut, status_code=201)
async def create_project_from_url(payload: ProjectFromUrl, db: Session = Depends(get_db)):
    gh = GitHubService()
    try: data = await gh.discover_repository(payload.repository_url)
    except ValueError as exc: raise HTTPException(422, str(exc))
    except Exception as exc: raise HTTPException(502, f"GitHub discovery failed: {exc}")
    if db.scalar(select(Project).where(Project.github_owner == data["owner"], Project.github_repo == data["repo"])): raise HTTPException(409, "This GitHub repository is already configured")
    code = (payload.code or default_code(data["repo"])).upper()
    if db.scalar(select(Project).where(Project.code == code)): code = f"{code[:9]}{uuid.uuid4().hex[:3].upper()}"
    p = Project(name=(payload.name or friendly_project_name(data["repo"])).strip(), code=code, github_owner=data["owner"], github_repo=data["repo"], repository_url=data["repository_url"], repository_description=data.get("description"), repository_visibility=data.get("visibility"), default_branch=data.get("default_branch") or "main", roadmap_path=data.get("roadmap_path") or "ROADMAP.md", changelog_path=data.get("changelog_path") or "CHANGELOG.md", active=True)
    db.add(p); db.commit(); db.refresh(p)
    try: await sync_project_record(p, db)
    except Exception: pass
    db.refresh(p); return p

@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**payload.model_dump()); db.add(p); db.commit(); db.refresh(p); return p

@app.put("/api/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "name" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(422, "Display name is required")
        setattr(p, key, value)
    db.commit(); db.refresh(p); return p

@app.post("/api/projects/{project_id}/refresh")
async def refresh_project(project_id: int, db: Session = Depends(get_db)):
    return await sync_project_record(project_or_404(db, project_id), db)

@app.post("/api/projects/refresh-all")
async def refresh_all(db: Session = Depends(get_db)):
    results=[]
    for p in db.scalars(select(Project).where(Project.active==True)).all():
        try: results.append({"project_id":p.id,"status":"ok","data":await sync_project_record(p,db)})
        except Exception as exc: results.append({"project_id":p.id,"status":"error","error":str(exc)})
    return results

@app.get("/api/projects/sync-summary")
def sync_summary(db: Session = Depends(get_db)):
    active=list(db.scalars(select(Project).where(Project.active==True))); failed=[p for p in active if p.github_sync_status=="Failed"]
    last=max((p.github_refreshed_at for p in active if p.github_refreshed_at),default=None)
    return {"active_projects":len(active),"failed_projects":len(failed),"status":"degraded" if failed else "ok","last_successful_sync":iso_utc(last),"interval_seconds":BACKGROUND_SYNC_SECONDS}

@app.get("/api/projects/sync-diagnostics")
def sync_diagnostics(db: Session = Depends(get_db)):
    rows=[]
    for p in db.scalars(select(Project).order_by(Project.name)):
        latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
        cache=json.loads(p.github_cache_json or "{}")
        ci = cache.get("ci") or {}
        rows.append({"project_id":p.id,"project":p.name,"last_successful_sync":iso_utc(p.github_refreshed_at),"last_attempted_sync":iso_utc(p.github_last_attempt_at),"sync_state":p.github_sync_status,"latest_commit_sha":((cache.get("latest_commit") or {}).get("sha")),"ci_commit_sha":ci.get("commit_sha"),"roadmap_source_sha":latest.source_sha if latest else None,"roadmap_parsed_time":iso_utc(latest.parsed_at) if latest else None,"roadmap_parse_state":latest.parse_status if latest else "Unknown","detected_version":p.latest_version,"version_source":cache.get("version_source","Unknown"),"version_evidence":cache.get("version_evidence",[]),"ci_state":ci.get("state"),"changelog_reconciliation_state":p.changelog_status,"last_error":p.github_sync_error,"backoff_until":iso_utc(p.github_backoff_until),"rate_limit":{"remaining":p.github_rate_limit_remaining,"limit":p.github_rate_limit_limit,"reset_at":iso_utc(p.github_rate_limit_reset_at)}})
    return rows

@app.get("/api/projects/{project_id}/roadmap/intelligence")
async def roadmap_intelligence(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id); latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
    if not latest:
        try: await sync_roadmap_record(p,db,force=False)
        except Exception as exc: return {"status":"Error","error":str(exc),"phases":[]}
        latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
    if not latest: return {"status":"Missing","phases":[]}
    phases=list(latest.phases); detected_project=Project(latest_version=p.latest_version); detected_current,detected_next=_choose_current_next(detected_project,phases)
    return {"status":latest.parse_status,"snapshot_id":latest.id,"source_path":latest.source_path,"source_sha":latest.source_sha,"fetched_at":iso_utc(latest.fetched_at),"parsed_at":iso_utc(latest.parsed_at),"error":latest.parse_error,"current_phase_id":p.roadmap_current_phase_id,"next_phase_id":p.roadmap_next_phase_id,"current_phase_source":"User confirmed" if p.roadmap_current_override else "Detected","next_phase_source":"User override" if p.roadmap_next_override else "Detected","detected_current_phase_id":detected_current,"detected_next_phase_id":detected_next,"phases":[_phase_dict(x,p.latest_version) for x in phases]}

@app.post("/api/projects/{project_id}/roadmap/reparse")
async def reparse_roadmap(project_id:int,db:Session=Depends(get_db)): return await sync_roadmap_record(project_or_404(db,project_id),db,force=True)

@app.put("/api/projects/{project_id}/roadmap/selection")
def roadmap_selection(project_id:int,payload:dict,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if "current_phase_id" in payload:
        value=payload.get("current_phase_id"); phase=db.get(RoadmapPhase,value) if value else None
        if phase and (phase.project_id!=p.id or phase.ignored): raise HTTPException(422,"Current phase is unavailable")
        p.roadmap_current_phase_id=value; p.roadmap_current_override=value is not None
    if "next_phase_id" in payload:
        value=payload.get("next_phase_id"); phase=db.get(RoadmapPhase,value) if value else None
        if phase and (phase.project_id!=p.id or phase.ignored): raise HTTPException(422,"Next phase is unavailable")
        p.roadmap_next_phase_id=value; p.roadmap_next_override=value is not None
    latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
    if latest: _sync_phase_selection(p,list(latest.phases))
    db.commit(); return {"current_phase_id":p.roadmap_current_phase_id,"next_phase_id":p.roadmap_next_phase_id,"current_phase_source":"User confirmed" if p.roadmap_current_override else "Detected","next_phase_source":"User override" if p.roadmap_next_override else "Detected"}

@app.put("/api/roadmap/phases/{phase_id}")
def update_roadmap_phase(phase_id:int,payload:dict,db:Session=Depends(get_db)):
    phase=db.get(RoadmapPhase,phase_id)
    if not phase: raise HTTPException(404,"Roadmap phase not found")
    if "ignored" in payload: phase.ignored=bool(payload["ignored"])
    if payload.get("status") in {"Completed","In Progress","Planned","Future","Unknown"}: phase.status=payload["status"]
    p=db.get(Project,phase.project_id); latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
    if latest: _sync_phase_selection(p,list(latest.phases))
    db.commit(); return _phase_dict(phase,p.latest_version)

@app.get("/api/roadmap/phases/{phase_id}")
def roadmap_phase_detail(phase_id:int,db:Session=Depends(get_db)):
    phase=db.scalar(select(RoadmapPhase).options(selectinload(RoadmapPhase.items),selectinload(RoadmapPhase.register_items),selectinload(RoadmapPhase.releases)).where(RoadmapPhase.id==phase_id))
    if not phase: raise HTTPException(404,"Roadmap phase not found")
    p=db.get(Project,phase.project_id)
    return _phase_dict(phase,p.latest_version if p else None)

@app.get("/api/projects/{project_id}/changelog/reconciliation")
async def changelog_reconciliation(project_id:int,db:Session=Depends(get_db)): return await sync_changelog_record(project_or_404(db,project_id),db,force=False)

@app.get("/api/projects/{project_id}/reconciliation")
async def project_reconciliation(project_id:int,db:Session=Depends(get_db)): return await reconciliation_for_project(project_or_404(db,project_id),db)

@app.get("/api/projects/{project_id}/roadmap")
async def roadmap(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    try:
        latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
        text=latest.markdown_text if latest else await GitHubService().file_text(p.github_owner,p.github_repo,p.roadmap_path,p.default_branch)
        if text is None: raise HTTPException(404,"Configured roadmap file was not found")
        html=bleach.clean(markdown.markdown(text,extensions=["tables","fenced_code"]),tags=set(bleach.sanitizer.ALLOWED_TAGS)|{"p","pre","h1","h2","h3","h4","h5","h6","table","thead","tbody","tr","th","td"},attributes={"a":["href","title"]})
        return {"path":p.roadmap_path,"markdown":text,"html":html,"github_url":f"https://github.com/{p.github_owner}/{p.github_repo}/blob/{p.default_branch}/{p.roadmap_path}"}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502,f"Roadmap retrieval failed: {exc}")

@app.post("/api/projects/{project_id}/logo")
async def upload_project_logo(project_id:int,file:UploadFile=File(...),db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if file.content_type not in ALLOWED_LOGO_TYPES: raise HTTPException(415,"Logo must be SVG, PNG, WebP or JPEG")
    data=await file.read(5*1024*1024+1)
    if len(data)>5*1024*1024: raise HTTPException(413,"Logo exceeds 5 MB limit")
    suffix={"image/svg+xml":".svg","image/png":".png","image/webp":".webp","image/jpeg":".jpg"}[file.content_type]; stored=f"project-{p.id}-{uuid.uuid4().hex}{suffix}"; path=PROJECT_LOGO_DIR/stored; path.write_bytes(data)
    if p.logo_path:
        old=PROJECT_LOGO_DIR/Path(p.logo_path).name
        if old.exists(): old.unlink()
    p.logo_path=stored; db.commit(); db.refresh(p); return {"logo_url":f"/api/projects/{p.id}/logo"}

@app.get("/api/projects/{project_id}/logo")
def project_logo(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if not p.logo_path: raise HTTPException(404,"Project logo not configured")
    path=(PROJECT_LOGO_DIR/Path(p.logo_path).name).resolve()
    if PROJECT_LOGO_DIR.resolve() not in path.parents or not path.exists(): raise HTTPException(404,"Project logo missing")
    return FileResponse(path)

@app.delete("/api/projects/{project_id}/logo",status_code=204)
def delete_project_logo(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if p.logo_path:
        path=PROJECT_LOGO_DIR/Path(p.logo_path).name
        if path.exists(): path.unlink()
    p.logo_path=None; db.commit()

@app.get("/api/register",response_model=list[RegisterItemOut])
def list_register(project_id:int|None=None,roadmap_phase_id:int|None=None,item_type:str|None=None,status:str|None=None,priority:str|None=None,target_release:str|None=None,db:Session=Depends(get_db)):
    stmt=select(RegisterItem).options(selectinload(RegisterItem.criteria),selectinload(RegisterItem.attachments)).order_by(RegisterItem.created_at.desc())
    if project_id: stmt=stmt.where(RegisterItem.project_id==project_id)
    if roadmap_phase_id: stmt=stmt.where(RegisterItem.roadmap_phase_id==roadmap_phase_id)
    if item_type: stmt=stmt.where(RegisterItem.item_type==item_type)
    if status: stmt=stmt.where(RegisterItem.status==status)
    if priority: stmt=stmt.where(RegisterItem.priority==priority)
    if target_release: stmt=stmt.where(RegisterItem.target_release==target_release)
    return list(db.scalars(stmt).unique())

@app.post("/api/register",response_model=RegisterItemOut,status_code=201)
def create_item(payload:RegisterItemCreate,db:Session=Depends(get_db)):
    p=project_or_404(db,payload.project_id)
    if payload.roadmap_phase_id:
        phase=db.get(RoadmapPhase,payload.roadmap_phase_id)
        if not phase or phase.project_id!=p.id: raise HTTPException(422,"Roadmap phase does not belong to project")
    data=payload.model_dump(exclude={"criteria"}); item=RegisterItem(**data,item_key=make_item_key(db,p,payload.item_type)); db.add(item); db.flush()
    for c in payload.criteria: db.add(AcceptanceCriterion(item_id=item.id,**c.model_dump())
    db.commit(); return item_or_404(db,item.id)

@app.put("/api/register/{item_id}",response_model=RegisterItemOut)
def update_item(item_id:int,payload:RegisterItemUpdate,db:Session=Depends(get_db)):
    item=item_or_404(db,item_id); changes=payload.model_dump(exclude_unset=True)
    if "roadmap_phase_id" in changes and changes["roadmap_phase_id"] is not None:
        phase=db.get(RoadmapPhase,changes["roadmap_phase_id"])
        if not phase or phase.project_id!=item.project_id: raise HTTPException(422,"Roadmap phase does not belong to project")
    for k,v in changes.items(): setattr(item,k,v)
    db.commit(); return item_or_404(db,item_id)

@app.post("/api/register/{item_id}/criteria",status_code=201)
def add_criterion(item_id:int,payload:dict,db:Session=Depends(get_db)):
    item_or_404(db,item_id); text=str(payload.get("description","")).strip()
    if not text: raise HTTPException(422,"Description is required")
    c=AcceptanceCriterion(item_id=item_id,description=text,sort_order=int(payload.get("sort_order",0))); db.add(c); db.commit(); db.refresh(c); return {"id":c.id,"description":c.description,"sort_order":c.sort_order}

@app.post("/api/register/{item_id}/attachments",response_model=list[dict])
async def upload_attachments(item_id:int,files:list[UploadFile]=File(...),db:Session=Depends(get_db)):
    item_or_404(db,item_id); result=[]
    for f in files:
        if f.content_type not in ALLOWED_TYPES: raise HTTPException(415,f"Unsupported attachment type: {f.content_type}")
        data=await f.read(MAX_UPLOAD_BYTES+1)
        if len(data)>MAX_UPLOAD_BYTES: raise HTTPException(413,"Attachment exceeds 100 MB limit")
        safe=re.sub(r"[^A-Za-z0-9._-]","_",Path(f.filename or "file").name); stored=f"{uuid.uuid4().hex}_{safe}"; (UPLOAD_DIR/stored).write_bytes(data); a=Attachment(item_id=item_id,original_name=safe,stored_name=stored,content_type=f.content_type or "application/octet-stream",size_bytes=len(data)); db.add(a); db.flush(); result.append({"id":a.id,"name":safe,"content_type":a.content_type,"size_bytes":a.size_bytes})
    db.commit(); return result

@app.get("/api/attachments/{attachment_id}")
def attachment(attachment_id:int,db:Session=Depends(get_db)):
    a=db.get(Attachment,attachment_id)
    if not a: raise HTTPException(404,"Attachment not found")
    path=(UPLOAD_DIR/a.stored_name).resolve()
    if UPLOAD_DIR.resolve() not in path.parents or not path.exists(): raise HTTPException(404,"Attachment file missing")
    return FileResponse(path,media_type=a.content_type,filename=a.original_name)

@app.get("/api/releases",response_model=list[ReleaseOut])
def list_releases(project_id:int|None=None,db:Session=Depends(get_db)):
    stmt=select(Release).order_by(Release.created_at.desc())
    if project_id: stmt=stmt.where(Release.project_id==project_id)
    return list(db.scalars(stmt))

@app.post("/api/releases",response_model=ReleaseOut,status_code=201)
def create_release(payload:ReleaseCreate,db:Session=Depends(get_db)):
    project_or_404(db,payload.project_id)
    if payload.roadmap_phase_id:
        phase=db.get(RoadmapPhase,payload.roadmap_phase_id)
        if not phase or phase.project_id!=payload.project_id or phase.ignored: raise HTTPException(422,"Roadmap phase is unavailable for this release")
    r=Release(project_id=payload.project_id,planned_version=payload.planned_version,roadmap_phase_id=payload.roadmap_phase_id,notes=payload.notes); db.add(r); db.flush()
    for item_id in payload.item_ids:
        item=item_or_404(db,item_id)
        if item.project_id!=payload.project_id: raise HTTPException(422,"Release item belongs to another project")
        db.add(ReleaseItem(release_id=r.id,item_id=item_id))
    db.commit(); db.refresh(r); return r

@app.get("/api/releases/{release_id}/reconciliation")
async def release_reconciliation(release_id:int,db:Session=Depends(get_db)):
    r=db.scalar(select(Release).options(selectinload(Release.roadmap_phase).selectinload(RoadmapPhase.items),selectinload(Release.roadmap_phase).selectinload(RoadmapPhase.register_items)).where(Release.id==release_id))
    if not r: raise HTTPException(404,"Release not found")
    p=project_or_404(db,r.project_id); changelog=await sync_changelog_record(p,db,force=False); result=reconcile_release(p.latest_version,r,r.roadmap_phase,changelog); r.roadmap_reconciliation_status=result["status"]; r.changelog_reconciliation_status=changelog.get("status"); db.commit(); return result

@app.post("/api/releases/{release_id}/prompt")
async def release_prompt(release_id:int,db:Session=Depends(get_db)):
    r=db.scalar(select(Release).options(selectinload(Release.scope).selectinload(ReleaseItem.item).selectinload(RegisterItem.criteria),selectinload(Release.scope).selectinload(ReleaseItem.item).selectinload(RegisterItem.attachments),selectinload(Release.roadmap_phase).selectinload(RoadmapPhase.items)).where(Release.id==release_id))
    if not r: raise HTTPException(404,"Release not found")
    p=project_or_404(db,r.project_id); latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc())); current=db.get(RoadmapPhase,p.roadmap_current_phase_id) if p.roadmap_current_phase_id else None; nxt=db.get(RoadmapPhase,p.roadmap_next_phase_id) if p.roadmap_next_phase_id else None
    changelog=await sync_changelog_record(p,db,force=False); recon=await reconciliation_for_project(p,db)
    structured={"current":_phase_dict(current,p.latest_version) if current else None,"current_source":"User confirmed" if p.roadmap_current_override else "Detected","next":_phase_dict(nxt,p.latest_version) if nxt else None,"next_source":"User override" if p.roadmap_next_override else "Detected","selected_release_phase":_phase_dict(r.roadmap_phase,p.latest_version) if r.roadmap_phase else None,"parse_status":latest.parse_status if latest else "Unknown","detected_release":p.latest_version,"version_source":json.loads(p.github_cache_json or "{}").get("version_source","Unknown"),"reconciliation":recon,"changelog":changelog}
    return {"prompt":build_release_prompt(p,r,None,None,structured)}

@app.put("/api/releases/{release_id}/tests/{criterion_id}")
def update_test_result(release_id:int,criterion_id:int,payload:TestResultUpdate,db:Session=Depends(get_db)):
    if payload.status not in TEST_STATUSES: raise HTTPException(422,"Invalid test status")
    result=db.scalar(select(AcceptanceTestResult).where(AcceptanceTestResult.release_id==release_id,AcceptanceTestResult.criterion_id==criterion_id))
    if not result: result=AcceptanceTestResult(release_id=release_id,criterion_id=criterion_id); db.add(result)
    result.status=payload.status; result.notes=payload.notes; db.commit(); return {"status":result.status,"notes":result.notes}

FRONTEND_DIST=Path(__file__).resolve().parents[2]/"frontend"/"dist"
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/",StaticFiles(directory=FRONTEND_DIST,html=True),name="frontend")
