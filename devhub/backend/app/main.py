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

APP_VERSION = "0.5.1"
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


def _phase_dict(phase: RoadmapPhase) -> dict:
    return {
        "id": phase.id,
        "version": phase.version,
        "title": phase.title,
        "phase_type": phase.phase_type,
        "status": phase.status,
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
    active = [p for p in phases if not p.ignored and p.phase_type != "Future"]
    if not active:
        return None, None
    if project.roadmap_current_override and project.roadmap_current_phase_id and any(p.id == project.roadmap_current_phase_id for p in active):
        current = next(p for p in active if p.id == project.roadmap_current_phase_id)
    else:
        exact = next((p for p in active if project.latest_version and p.version and p.version.lower() == project.latest_version.lower()), None)
        current = exact or next((p for p in active if p.status in {"In Progress", "Unknown"}), active[-1])
    if project.roadmap_next_override and project.roadmap_next_phase_id and any(p.id == project.roadmap_next_phase_id for p in active):
        nxt = next(p for p in active if p.id == project.roadmap_next_phase_id)
    else:
        later = [p for p in active if p.sort_order > current.sort_order]
        nxt = later[0] if later else next((p for p in phases if p.phase_type == "Future" and not p.ignored), None)
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
        return {"status": latest.parse_status, "snapshot_id": latest.id, "phases": [_phase_dict(x) for x in latest.phases], "warnings": []}
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
    return {"status": parsed["status"], "snapshot_id": snapshot.id, "phases": [_phase_dict(x) for x in phases], "warnings": parsed.get("warnings") or []}


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
    try:
        data = await GitHubService().discover_repository(payload.repository_url)
    except ValueError as exc: raise HTTPException(422, str(exc))
    except Exception as exc: raise HTTPException(502, f"GitHub discovery failed: {exc}")
    code = payload.code or default_code(data["repo"])
    create = ProjectCreate(name=payload.name or data["name"], code=code, github_owner=data["owner"], github_repo=data["repo"], repository_url=data["repository_url"], default_branch=data["default_branch"], roadmap_path=payload.roadmap_path or data.get("roadmap_path") or "ROADMAP.md", changelog_path=payload.changelog_path or data.get("changelog_path") or "CHANGELOG.md", active=True)
    return await create_project(create, db)

@app.post("/api/projects", response_model=ProjectOut, status_code=201)
async def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**payload.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    try: await sync_project_record(p, db)
    except Exception: pass
    return p

@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def project(project_id: int, db: Session = Depends(get_db)): return project_or_404(db, project_id)

@app.post("/api/projects/{project_id}/refresh")
async def refresh_project(project_id: int, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    try: return await sync_project_record(p, db)
    except Exception as exc: raise HTTPException(502, str(exc))

@app.post("/api/projects/refresh-all")
async def refresh_all(db: Session = Depends(get_db)):
    results=[]
    for p in db.scalars(select(Project).where(Project.active == True)).all():
        try: results.append({"project_id":p.id,"ok":True,"data":await sync_project_record(p,db)})
        except Exception as exc: results.append({"project_id":p.id,"ok":False,"error":str(exc)})
    return results

@app.get("/api/projects/{project_id}/roadmap/intelligence")
async def roadmap_intelligence(project_id: int, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    latest = db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id == p.id).order_by(RoadmapSnapshot.id.desc()))
    if not latest: return await sync_roadmap_record(p, db, force=False)
    return {"status": latest.parse_status, "snapshot_id": latest.id, "current_phase_id": p.roadmap_current_phase_id, "next_phase_id": p.roadmap_next_phase_id, "current_source": "User override" if p.roadmap_current_override else "Detected", "next_source": "User override" if p.roadmap_next_override else "Detected", "phases": [_phase_dict(x) for x in latest.phases], "warnings": [latest.parse_error] if latest.parse_error else []}

@app.post("/api/projects/{project_id}/roadmap/reparse")
async def roadmap_reparse(project_id: int, db: Session = Depends(get_db)): return await sync_roadmap_record(project_or_404(db, project_id), db, force=True)

@app.post("/api/projects/{project_id}/roadmap/phases/{phase_id}/ignore")
def ignore_phase(project_id: int, phase_id: int, db: Session = Depends(get_db)):
    phase=db.get(RoadmapPhase,phase_id)
    if not phase or phase.project_id!=project_id: raise HTTPException(404,"Roadmap phase not found")
    phase.ignored=True; p=project_or_404(db,project_id)
    if p.roadmap_current_phase_id==phase.id: p.roadmap_current_phase_id=None; p.roadmap_current_override=False
    if p.roadmap_next_phase_id==phase.id: p.roadmap_next_phase_id=None; p.roadmap_next_override=False
    db.commit(); return {"ok":True}

@app.post("/api/projects/{project_id}/roadmap/phases/{phase_id}/restore")
def restore_phase(project_id:int, phase_id:int, db:Session=Depends(get_db)):
    phase=db.get(RoadmapPhase,phase_id)
    if not phase or phase.project_id!=project_id: raise HTTPException(404,"Roadmap phase not found")
    phase.ignored=False; db.commit(); return {"ok":True}

@app.post("/api/projects/{project_id}/roadmap/selection")
def roadmap_selection(project_id:int, payload:dict, db:Session=Depends(get_db)):
    p=project_or_404(db,project_id); which=payload.get("which"); phase_id=payload.get("phase_id")
    if which not in {"current","next"}: raise HTTPException(422,"which must be current or next")
    if phase_id is not None:
        phase=db.get(RoadmapPhase,int(phase_id))
        if not phase or phase.project_id!=project_id or phase.ignored: raise HTTPException(422,"Invalid roadmap phase")
    setattr(p,f"roadmap_{which}_phase_id",phase_id); setattr(p,f"roadmap_{which}_override",phase_id is not None); db.commit(); return {"ok":True}

@app.delete("/api/projects/{project_id}/roadmap/selection/{which}")
def clear_roadmap_selection(project_id:int,which:str,db:Session=Depends(get_db)):
    if which not in {"current","next"}: raise HTTPException(422,"Invalid selection")
    p=project_or_404(db,project_id); setattr(p,f"roadmap_{which}_override",False); latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==project_id).order_by(RoadmapSnapshot.id.desc()))
    if latest: _sync_phase_selection(p,list(latest.phases))
    db.commit(); return {"ok":True}

@app.get("/api/projects/{project_id}/roadmap/reconciliation")
async def roadmap_reconciliation(project_id:int,db:Session=Depends(get_db)): return await reconciliation_for_project(project_or_404(db,project_id),db)

@app.get("/api/projects/{project_id}/changelog/reconciliation")
async def changelog_reconciliation(project_id:int,db:Session=Depends(get_db)): return await sync_changelog_record(project_or_404(db,project_id),db,force=False)

@app.get("/api/projects/{project_id}/roadmap")
async def roadmap(project_id: int, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    try:
        text = await GitHubService().file_text(p.github_owner, p.github_repo, p.roadmap_path, p.default_branch)
        if text is None: raise HTTPException(404, "ROADMAP file not found")
        return {"path":p.roadmap_path,"content":text,"html":bleach.clean(markdown.markdown(text,extensions=["tables","fenced_code"]),tags=list(bleach.sanitizer.ALLOWED_TAGS)+["p","pre","h1","h2","h3","h4","h5","h6","table","thead","tbody","tr","th","td","img"],attributes={"a":["href"],"img":["src","alt"]})}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502, f"Unable to load roadmap: {exc}")

@app.get("/api/register", response_model=list[RegisterItemOut])
def list_register(project_id: int | None = None, roadmap_phase_id: int | None = None, db: Session = Depends(get_db)):
    stmt=select(RegisterItem).options(selectinload(RegisterItem.criteria),selectinload(RegisterItem.attachments)).order_by(RegisterItem.updated_at.desc())
    if project_id: stmt=stmt.where(RegisterItem.project_id==project_id)
    if roadmap_phase_id: stmt=stmt.where(RegisterItem.roadmap_phase_id==roadmap_phase_id)
    return list(db.scalars(stmt))

@app.post("/api/register", response_model=RegisterItemOut, status_code=201)
def create_register(payload:RegisterItemCreate,db:Session=Depends(get_db)):
    project=project_or_404(db,payload.project_id)
    if payload.item_type not in {"Defect","Enhancement","UX Improvement","Technical Debt","Performance","Security","Documentation"}: raise HTTPException(422,"Invalid item type")
    if payload.roadmap_phase_id:
        phase=db.get(RoadmapPhase,payload.roadmap_phase_id)
        if not phase or phase.project_id!=project.id or phase.ignored: raise HTTPException(422,"Invalid roadmap phase")
    data=payload.model_dump(exclude={"criteria"}); item=RegisterItem(**data,item_key=make_item_key(db,project,payload.item_type)); db.add(item); db.flush()
    for c in payload.criteria: db.add(AcceptanceCriterion(item_id=item.id,description=c.description,sort_order=c.sort_order))
    db.commit(); return item_or_404(db,item.id)

@app.patch("/api/register/{item_id}",response_model=RegisterItemOut)
def update_register(item_id:int,payload:RegisterItemUpdate,db:Session=Depends(get_db)):
    item=item_or_404(db,item_id); data=payload.model_dump(exclude_unset=True)
    if "roadmap_phase_id" in data and data["roadmap_phase_id"] is not None:
        phase=db.get(RoadmapPhase,data["roadmap_phase_id"])
        if not phase or phase.project_id!=item.project_id or phase.ignored: raise HTTPException(422,"Invalid roadmap phase")
    for k,v in data.items(): setattr(item,k,v)
    db.commit(); return item_or_404(db,item.id)

@app.post("/api/register/{item_id}/attachments",response_model=list[RegisterItemOut])
async def upload_attachments(item_id:int,files:list[UploadFile]=File(...),db:Session=Depends(get_db)):
    item=item_or_404(db,item_id)
    if len(files)>8: raise HTTPException(422,"Maximum 8 attachments per upload")
    for file in files:
        if file.content_type not in ALLOWED_TYPES: raise HTTPException(422,f"Unsupported file type: {file.content_type}")
        data=await file.read(MAX_UPLOAD_BYTES+1)
        if len(data)>MAX_UPLOAD_BYTES: raise HTTPException(413,"Attachment exceeds 100 MB")
        safe=Path(file.filename or "upload").name; key=f"{uuid.uuid4().hex}-{safe}"; (UPLOAD_DIR/key).write_bytes(data)
        db.add(Attachment(item_id=item.id,original_name=safe,stored_name=key,content_type=file.content_type or "application/octet-stream",size_bytes=len(data)))
    db.commit(); return [item_or_404(db,item.id)]

@app.get("/api/attachments/{attachment_id}")
def attachment(attachment_id:int,db:Session=Depends(get_db)):
    a=db.get(Attachment,attachment_id)
    if not a: raise HTTPException(404,"Attachment not found")
    path=(UPLOAD_DIR/a.stored_name).resolve()
    if UPLOAD_DIR.resolve() not in path.parents: raise HTTPException(403,"Invalid path")
    return FileResponse(path,media_type=a.content_type,filename=a.original_name)

@app.get("/api/releases",response_model=list[ReleaseOut])
def releases(project_id:int|None=None,db:Session=Depends(get_db)):
    stmt=select(Release).order_by(Release.created_at.desc())
    if project_id: stmt=stmt.where(Release.project_id==project_id)
    return list(db.scalars(stmt))

@app.post("/api/releases",response_model=ReleaseOut,status_code=201)
def create_release(payload:ReleaseCreate,db:Session=Depends(get_db)):
    project_or_404(db,payload.project_id)
    if payload.roadmap_phase_id:
        phase=db.get(RoadmapPhase,payload.roadmap_phase_id)
        if not phase or phase.project_id!=payload.project_id or phase.ignored: raise HTTPException(422,"Invalid roadmap phase")
    release=Release(project_id=payload.project_id,planned_version=payload.planned_version,roadmap_phase_id=payload.roadmap_phase_id,notes=payload.notes)
    db.add(release); db.flush()
    for item_id in payload.item_ids:
        item=db.get(RegisterItem,item_id)
        if item and item.project_id==payload.project_id: db.add(ReleaseItem(release_id=release.id,item_id=item.id))
    db.commit(); db.refresh(release); return release

@app.post("/api/releases/{release_id}/complete",response_model=ReleaseOut)
def complete_release(release_id:int,payload:dict,db:Session=Depends(get_db)):
    r=db.get(Release,release_id)
    if not r: raise HTTPException(404,"Release not found")
    r.actual_version=payload.get("actual_version") or r.planned_version; r.release_url=payload.get("release_url"); r.pr_url=payload.get("pr_url"); r.status="Released"; r.release_at=datetime.utcnow(); r.roadmap_updated=bool(payload.get("roadmap_updated")); r.changelog_updated=bool(payload.get("changelog_updated")); db.commit(); db.refresh(r); return r

@app.get("/api/releases/{release_id}/reconciliation")
def release_reconciliation(release_id:int,db:Session=Depends(get_db)):
    r=db.get(Release,release_id)
    if not r: raise HTTPException(404,"Release not found")
    return {"release_status":r.status,"roadmap_updated":r.roadmap_updated,"changelog_updated":r.changelog_updated,"needs_roadmap_update":r.status=="Released" and not r.roadmap_updated,"needs_changelog_update":r.status=="Released" and not r.changelog_updated,"roadmap_reconciliation_status":r.roadmap_reconciliation_status,"changelog_reconciliation_status":r.changelog_reconciliation_status}

@app.get("/api/releases/{release_id}/acceptance-tests")
def test_results(release_id:int,db:Session=Depends(get_db)):
    r=db.get(Release,release_id)
    if not r: raise HTTPException(404,"Release not found")
    rows=db.scalars(select(AcceptanceTestResult).where(AcceptanceTestResult.release_id==release_id)).all()
    return [{"id":x.id,"item_id":x.item_id,"status":x.status,"notes":x.notes} for x in rows]

@app.patch("/api/releases/{release_id}/acceptance-tests/{item_id}")
def update_test(release_id:int,item_id:int,payload:TestResultUpdate,db:Session=Depends(get_db)):
    if payload.status not in TEST_STATUSES: raise HTTPException(422,"Invalid test status")
    row=db.scalar(select(AcceptanceTestResult).where(AcceptanceTestResult.release_id==release_id,AcceptanceTestResult.item_id==item_id))
    if not row: row=AcceptanceTestResult(release_id=release_id,item_id=item_id); db.add(row)
    row.status=payload.status; row.notes=payload.notes; row.tested_at=datetime.utcnow(); db.commit(); return {"ok":True}

@app.post("/api/releases/{release_id}/prompt")
def release_prompt(release_id:int,payload:dict|None=None,db:Session=Depends(get_db)):
    r=db.get(Release,release_id)
    if not r: raise HTTPException(404,"Release not found")
    p=project_or_404(db,r.project_id); items=[]
    for ri in db.scalars(select(ReleaseItem).where(ReleaseItem.release_id==r.id)).all():
        item=item_or_404(db,ri.item_id); items.append(item)
    phase=db.get(RoadmapPhase,r.roadmap_phase_id) if r.roadmap_phase_id else (db.get(RoadmapPhase,p.roadmap_next_phase_id) if p.roadmap_next_phase_id else None)
    changelog={"status":p.changelog_status,"version":p.changelog_parsed_version}; recon=reconcile_release(p.latest_version,r,phase,changelog)
    context={"roadmap_phase":_phase_dict(phase) if phase else None,"reconciliation":recon,"changelog":changelog,"detected_version":p.latest_version,"version_source":(json.loads(p.github_cache_json or "{}") or {}).get("version_source")}
    return {"prompt":build_release_prompt(p,r,items,payload or {},context)}

frontend_dist=Path(__file__).resolve().parents[2]/"frontend"/"dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets",StaticFiles(directory=frontend_dist/"assets"),name="assets")
    @app.get("/{full_path:path}")
    def spa(full_path:str):
        candidate=frontend_dist/full_path
        if full_path and candidate.is_file(): return FileResponse(candidate)
        return FileResponse(frontend_dist/"index.html")
