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
from .roadmap_parser import lifecycle_status, parse_roadmap, semantic_version, version_contains, version_order_key
from .schemas import AssistedRequirementDraft, AssistedRequirementRequest, ProjectCreate, ProjectDiscover, ProjectFromUrl, ProjectOut, RegisterItemCreate, RegisterItemOut, RegisterItemUpdate, ReleaseCreate, ReleaseOut, TestResultUpdate, TEST_STATUSES

APP_VERSION = "0.5.5"
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


def default_code(repo: str) -> str:
    parts = [x for x in re.split(r"[^A-Za-z0-9]+", repo) if x and x.lower() not in {"home", "assistant"}]
    if not parts:
        return "APP"
    if len(parts) == 1:
        return parts[0][:12].upper()
    return "".join(p[0] for p in parts)[:12].upper()


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

    if project.roadmap_current_override and project.roadmap_current_phase_id and any(p.id == project.roadmap_current_phase_id for p in selectable):
        current = next(p for p in selectable if p.id == project.roadmap_current_phase_id)
    else:
        detected = semantic_version(project.latest_version)
        exact_or_band = next((p for p in active if detected and version_contains(p.version, project.latest_version)), None)
        if exact_or_band:
            current = exact_or_band
        else:
            current = next((p for p in active if p.status == "In Progress"), None)
            if not current and detected:
                historical = [(version_order_key(p.version), p) for p in active if version_order_key(p.version) and version_order_key(p.version) <= detected]
                current = max(historical, key=lambda pair: pair[0])[1] if historical else None
            current = current or next((p for p in active if p.status == "Unknown"), active[-1])

    if project.roadmap_next_override and project.roadmap_next_phase_id and any(p.id == project.roadmap_next_phase_id for p in selectable):
        nxt = next(p for p in selectable if p.id == project.roadmap_next_phase_id)
    else:
        current_key = version_order_key(current.version) if current and current.phase_type != "Future" else semantic_version(project.latest_version)
        if current and version_contains(current.version, project.latest_version):
            current_key = semantic_version(project.latest_version) or current_key
        candidates = []
        if current_key:
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
    snapshot = RoadmapSnapshot(project_id=p.id, source_path=p.roadmap_path, source_sha=(meta or {}).get("sha"), markdown_text=text, fetched_at=datetime.utcnow(), parsed_at=datetime.utcnow(), parse_status=parsed["status"], parse_error="; ".join(parsed.get("warnings") or []) or None)
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
    p.changelog_parsed_at = datetime.utcnow()
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
    now = datetime.utcnow()
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
        p.github_cache_json = json.dumps({"open_pr_count": len(data.get("open_prs") or []), "open_prs": open_pr_summary(data.get("open_prs") or []), "last_merged_pr": data.get("last_merged_pr"), "latest_commit": commit, "ci": data.get("ci"), "version_source": version.get("source", "Unknown"), "version_evidence": [{"source": version.get("source", "Unknown"), "version": version.get("version")}], "rate_limit": {"remaining": p.github_rate_limit_remaining, "limit": p.github_rate_limit_limit, "reset_at": p.github_rate_limit_reset_at.isoformat() if p.github_rate_limit_reset_at else None}})
        p.github_refreshed_at = datetime.utcnow(); p.github_sync_status = "Synced"; p.github_sync_error = None; p.github_failure_count = 0; p.github_backoff_until = None
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
        else: p.github_backoff_until = datetime.utcnow() + timedelta(minutes=delay_minutes)
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
async def assisted_requirements_analyse(request: AssistedRequirementRequest, db: Session = Depends(get_db)):
    return await analyse_requirement(request, db)

@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)): return db.scalars(select(Project).order_by(Project.name)).all()

@app.post("/api/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**payload.model_dump()); db.add(p); db.commit(); db.refresh(p); return p

@app.post("/api/projects/discover", response_model=ProjectDiscover)
async def discover_project(payload: ProjectFromUrl):
    return ProjectDiscover(**await GitHubService().discover_repository(payload.repository_url))

@app.post("/api/projects/from-url", response_model=ProjectOut)
async def create_project_from_url(payload: ProjectFromUrl, db: Session = Depends(get_db)):
    data = await GitHubService().discover_repository(payload.repository_url)
    existing = db.scalar(select(Project).where(Project.github_owner == data["github_owner"], Project.github_repo == data["github_repo"]))
    if existing: raise HTTPException(409, "Project already configured")
    p = Project(name=data["github_repo"], code=default_code(data["github_repo"]), github_owner=data["github_owner"], github_repo=data["github_repo"], repository_url=data["repository_url"], repository_description=data.get("description"), repository_visibility=data.get("visibility"), default_branch=data.get("default_branch") or "main", roadmap_path=data.get("roadmap_path") or "ROADMAP.md", changelog_path=data.get("changelog_path") or "CHANGELOG.md")
    db.add(p); db.commit(); db.refresh(p)
    try: await sync_project_record(p, db)
    except Exception: pass
    return p

@app.post("/api/projects/{project_id}/refresh")
async def refresh_project(project_id: int, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    try: return await sync_project_record(p, db)
    except Exception as exc: raise HTTPException(502, str(exc))

@app.post("/api/projects/refresh-all")
async def refresh_all(db: Session = Depends(get_db)):
    results=[]
    for p in db.scalars(select(Project).where(Project.active == True)).all():
        try: await sync_project_record(p, db); results.append({"project_id":p.id,"status":"Synced"})
        except Exception as exc: results.append({"project_id":p.id,"status":"Failed","error":str(exc)})
    return {"results":results}

@app.get("/api/projects/sync-summary")
def sync_summary(db: Session = Depends(get_db)):
    projects=db.scalars(select(Project).where(Project.active == True)).all(); failed=[p for p in projects if p.github_sync_status=="Failed"]
    latest=max([p.github_refreshed_at for p in projects if p.github_refreshed_at], default=None)
    return {"active_projects":len(projects),"failed_projects":len(failed),"status":"Degraded" if failed else "Healthy","last_successful_sync":latest,"interval_seconds":BACKGROUND_SYNC_SECONDS}

@app.get("/api/projects/sync-diagnostics")
def sync_diagnostics(db: Session = Depends(get_db)):
    out=[]
    for p in db.scalars(select(Project).order_by(Project.name)).all():
        cache={}
        try: cache=json.loads(p.github_cache_json or "{}")
        except json.JSONDecodeError: pass
        latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
        out.append({"project_id":p.id,"project":p.name,"last_successful_sync":p.github_refreshed_at,"last_attempted_sync":p.github_last_attempt_at,"sync_state":p.github_sync_status,"latest_commit_sha":(cache.get("latest_commit") or {}).get("sha"),"roadmap_source_sha":latest.source_sha if latest else None,"roadmap_parsed_time":latest.parsed_at if latest else None,"roadmap_parse_state":latest.parse_status if latest else "Unknown","detected_version":p.latest_version,"version_source":cache.get("version_source","Unknown"),"ci_state":(cache.get("ci") or {}).get("state"),"changelog_reconciliation_state":p.changelog_status,"last_error":p.github_sync_error,"backoff_until":p.github_backoff_until,"rate_limit":{"remaining":p.github_rate_limit_remaining,"limit":p.github_rate_limit_limit,"reset_at":p.github_rate_limit_reset_at}})
    return out

@app.get("/api/projects/{project_id}/roadmap")
async def roadmap(project_id: int, db: Session = Depends(get_db)):
    p=project_or_404(db, project_id); gh=GitHubService(); text=await gh.file_text(p.github_owner,p.github_repo,p.roadmap_path,p.default_branch)
    if text is None: raise HTTPException(404,"Roadmap not found")
    return {"markdown":text,"html":bleach.clean(markdown.markdown(text),tags=["p","ul","ol","li","strong","em","h1","h2","h3","h4","code","pre","a","blockquote"],attributes={"a":["href"]})}

@app.get("/api/projects/{project_id}/roadmap/intelligence")
def roadmap_intelligence(project_id: int, db: Session = Depends(get_db)):
    p=project_or_404(db, project_id); snapshot=db.scalar(select(RoadmapSnapshot).options(selectinload(RoadmapSnapshot.phases).selectinload(RoadmapPhase.items),selectinload(RoadmapSnapshot.phases).selectinload(RoadmapPhase.register_items),selectinload(RoadmapSnapshot.phases).selectinload(RoadmapPhase.releases)).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
    if not snapshot: return {"status":"Unknown","phases":[],"current_phase_id":p.roadmap_current_phase_id,"next_phase_id":p.roadmap_next_phase_id,"current_phase_source":"User override" if p.roadmap_current_override else "Detected","next_phase_source":"User override" if p.roadmap_next_override else "Detected"}
    detected_current,detected_next=_choose_current_next(Project(latest_version=p.latest_version, roadmap_current_phase_id=None, roadmap_next_phase_id=None, roadmap_current_override=False, roadmap_next_override=False), list(snapshot.phases))
    return {"status":snapshot.parse_status,"snapshot_id":snapshot.id,"source_path":snapshot.source_path,"source_sha":snapshot.source_sha,"fetched_at":snapshot.fetched_at,"parsed_at":snapshot.parsed_at,"error":snapshot.parse_error,"current_phase_id":p.roadmap_current_phase_id,"next_phase_id":p.roadmap_next_phase_id,"detected_current_phase_id":detected_current,"detected_next_phase_id":detected_next,"current_phase_source":"User confirmed" if p.roadmap_current_override and p.roadmap_current_phase_id==detected_current else "User override" if p.roadmap_current_override else "Detected","next_phase_source":"User confirmed" if p.roadmap_next_override and p.roadmap_next_phase_id==detected_next else "User override" if p.roadmap_next_override else "Detected","phases":[_phase_dict(x,p.latest_version) for x in snapshot.phases]}

@app.post("/api/projects/{project_id}/roadmap/reparse")
async def roadmap_reparse(project_id: int, db: Session = Depends(get_db)):
    return await sync_roadmap_record(project_or_404(db, project_id), db, force=True)

@app.put("/api/projects/{project_id}/roadmap/selection")
def roadmap_selection(project_id: int, payload: dict, db: Session = Depends(get_db)):
    p=project_or_404(db, project_id)
    for kind in ("current","next"):
        key=f"{kind}_phase_id"
        if key in payload:
            value=payload.get(key)
            if value is not None:
                phase=db.get(RoadmapPhase,int(value))
                if not phase or phase.project_id!=p.id or phase.ignored: raise HTTPException(400,"Invalid roadmap phase")
            setattr(p,f"roadmap_{kind}_phase_id",int(value) if value else None); setattr(p,f"roadmap_{kind}_override",value is not None)
    if not p.roadmap_current_override or not p.roadmap_next_override:
        snapshot=db.scalar(select(RoadmapSnapshot).options(selectinload(RoadmapSnapshot.phases)).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
        if snapshot: _sync_phase_selection(p,list(snapshot.phases))
    db.commit(); return {"ok":True}

@app.put("/api/roadmap/phases/{phase_id}")
def update_phase(phase_id: int, payload: dict, db: Session = Depends(get_db)):
    phase=db.get(RoadmapPhase,phase_id)
    if not phase: raise HTTPException(404,"Roadmap phase not found")
    if "ignored" in payload: phase.ignored=bool(payload["ignored"])
    p=project_or_404(db,phase.project_id); snapshot=db.get(RoadmapSnapshot,phase.snapshot_id)
    db.flush(); _sync_phase_selection(p,list(snapshot.phases) if snapshot else []); db.commit(); return {"ok":True}

@app.get("/api/projects/{project_id}/reconciliation")
async def project_reconciliation(project_id: int, db: Session = Depends(get_db)):
    return await reconciliation_for_project(project_or_404(db,project_id),db)

@app.post("/api/projects/{project_id}/logo")
async def upload_project_logo(project_id:int,file:UploadFile=File(...),db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if file.content_type not in ALLOWED_LOGO_TYPES: raise HTTPException(400,"Unsupported project logo type")
    data=await file.read(5*1024*1024+1)
    if len(data)>5*1024*1024: raise HTTPException(413,"Project logo too large")
    ext=Path(file.filename or "logo").suffix.lower() or ".bin"; name=f"project-{p.id}-{uuid.uuid4().hex}{ext}"; target=PROJECT_LOGO_DIR/name; target.write_bytes(data)
    if p.logo_path:
        old=(PROJECT_LOGO_DIR/Path(p.logo_path).name)
        if old.exists(): old.unlink()
    p.logo_path=name;db.commit();return {"logo_path":name}

@app.get("/api/projects/{project_id}/logo")
def project_logo(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if not p.logo_path: raise HTTPException(404,"No project logo")
    path=(PROJECT_LOGO_DIR/Path(p.logo_path).name).resolve()
    if PROJECT_LOGO_DIR.resolve() not in path.parents or not path.exists(): raise HTTPException(404,"Project logo missing")
    return FileResponse(path)

@app.get("/api/register", response_model=list[RegisterItemOut])
def list_register(db: Session = Depends(get_db)): return db.scalars(select(RegisterItem).options(selectinload(RegisterItem.criteria), selectinload(RegisterItem.attachments))).all()

@app.post("/api/register", response_model=RegisterItemOut)
def create_register(payload: RegisterItemCreate, db: Session = Depends(get_db)):
    p=project_or_404(db,payload.project_id)
    if payload.roadmap_phase_id:
        phase=db.get(RoadmapPhase,payload.roadmap_phase_id)
        if not phase or phase.project_id!=p.id: raise HTTPException(400,"Roadmap phase does not belong to project")
    data=payload.model_dump(exclude={"criteria"}); item=RegisterItem(**data,item_key=make_item_key(db,p,payload.item_type));db.add(item);db.flush()
    for idx,text in enumerate(payload.criteria): db.add(AcceptanceCriterion(register_item_id=item.id,description=text,sort_order=idx))
    db.commit();db.refresh(item);return item

@app.put("/api/register/{item_id}", response_model=RegisterItemOut)
def update_register(item_id:int,payload:RegisterItemUpdate,db:Session=Depends(get_db)):
    item=item_or_404(db,item_id)
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(item,k,v)
    db.commit();db.refresh(item);return item

@app.post("/api/register/{item_id}/attachments")
async def upload_attachment(item_id:int,file:UploadFile=File(...),db:Session=Depends(get_db)):
    item=item_or_404(db,item_id)
    if file.content_type not in ALLOWED_TYPES: raise HTTPException(400,"Unsupported attachment type")
    data=await file.read(MAX_UPLOAD_BYTES+1)
    if len(data)>MAX_UPLOAD_BYTES: raise HTTPException(413,"Attachment too large")
    safe=Path(file.filename or "upload.bin").name; stored=f"{uuid.uuid4().hex}-{safe}"; (UPLOAD_DIR/stored).write_bytes(data); att=Attachment(register_item_id=item.id,original_name=safe,stored_name=stored,content_type=file.content_type,size_bytes=len(data));db.add(att);db.commit();return {"id":att.id}

@app.get("/api/attachments/{attachment_id}")
def get_attachment(attachment_id:int,db:Session=Depends(get_db)):
    att=db.get(Attachment,attachment_id)
    if not att: raise HTTPException(404,"Attachment not found")
    path=(UPLOAD_DIR/att.stored_name).resolve()
    if UPLOAD_DIR.resolve() not in path.parents or not path.exists(): raise HTTPException(404,"File not found")
    return FileResponse(path,media_type=att.content_type,filename=att.original_name)

@app.get("/api/releases", response_model=list[ReleaseOut])
def list_releases(db:Session=Depends(get_db)): return db.scalars(select(Release).order_by(Release.created_at.desc())).all()

@app.post("/api/releases", response_model=ReleaseOut)
def create_release(payload:ReleaseCreate,db:Session=Depends(get_db)):
    project_or_404(db,payload.project_id)
    if payload.roadmap_phase_id:
        phase=db.get(RoadmapPhase,payload.roadmap_phase_id)
        if not phase or phase.project_id!=payload.project_id: raise HTTPException(400,"Roadmap phase does not belong to project")
    release=Release(project_id=payload.project_id,roadmap_phase_id=payload.roadmap_phase_id,planned_version=payload.planned_version,status="Planned");db.add(release);db.flush()
    for iid in payload.item_ids:
        item=db.get(RegisterItem,iid)
        if item and item.project_id==payload.project_id: db.add(ReleaseItem(release_id=release.id,register_item_id=iid))
    db.commit();db.refresh(release);return release

@app.post("/api/releases/{release_id}/prompt")
async def release_prompt(release_id:int,db:Session=Depends(get_db)):
    release=db.scalar(select(Release).options(selectinload(Release.project),selectinload(Release.items).selectinload(ReleaseItem.register_item)).where(Release.id==release_id))
    if not release: raise HTTPException(404,"Release not found")
    p=release.project
    intel=roadmap_intelligence(p.id,db); current=next((x for x in intel.get("phases",[]) if x["id"]==intel.get("current_phase_id")),None); nxt=next((x for x in intel.get("phases",[]) if x["id"]==intel.get("next_phase_id")),None); selected=next((x for x in intel.get("phases",[]) if x["id"]==release.roadmap_phase_id),None)
    recon=await reconciliation_for_project(p,db)
    changelog=await sync_changelog_record(p,db,force=False)
    return {"prompt":build_release_prompt(p,release,[ri.register_item for ri in release.items],current,nxt,selected,recon,changelog)}
