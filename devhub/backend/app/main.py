import asyncio
import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import bleach
import markdown
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, SessionLocal, engine, get_db
from .github_service import GitHubService
from .models import AcceptanceCriterion, AcceptanceTestResult, Attachment, Project, RegisterItem, Release, ReleaseItem, RoadmapItem, RoadmapPhase, RoadmapSnapshot
from .prompt_builder import build_release_prompt
from .roadmap_parser import parse_roadmap
from .schemas import ProjectCreate, ProjectDiscover, ProjectFromUrl, ProjectOut, RegisterItemCreate, RegisterItemOut, RegisterItemUpdate, ReleaseCreate, ReleaseOut, TestResultUpdate, TEST_STATUSES

APP_VERSION = "0.4.0"
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
    }


def _choose_current_next(project: Project, phases: list[RoadmapPhase]) -> tuple[int | None, int | None]:
    active = [p for p in phases if not p.ignored and p.phase_type != "Future"]
    if not active:
        return None, None
    if project.roadmap_current_phase_id and any(p.id == project.roadmap_current_phase_id for p in active):
        current = next(p for p in active if p.id == project.roadmap_current_phase_id)
    else:
        exact = next((p for p in active if project.latest_version and p.version and p.version.lower() == project.latest_version.lower()), None)
        current = exact or next((p for p in active if p.status in {"In Progress", "Unknown"}), active[-1])
    if project.roadmap_next_phase_id and any(p.id == project.roadmap_next_phase_id for p in active):
        nxt = next(p for p in active if p.id == project.roadmap_next_phase_id)
    else:
        later = [p for p in active if p.sort_order > current.sort_order]
        nxt = later[0] if later else next((p for p in phases if p.phase_type == "Future" and not p.ignored), None)
    return current.id if current else None, nxt.id if nxt else None


async def sync_roadmap_record(p: Project, db: Session, force: bool = False):
    gh = GitHubService()
    text = await gh.file_text(p.github_owner, p.github_repo, p.roadmap_path, p.default_branch)
    if text is None:
        return {"status": "Missing", "phases": [], "warnings": ["Configured roadmap file was not found"]}
    meta = await gh.file_metadata(p.github_owner, p.github_repo, p.roadmap_path, p.default_branch)
    latest = db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id == p.id).order_by(RoadmapSnapshot.id.desc()))
    if latest and not force and meta and latest.source_sha == meta.get("sha"):
        return {"status": latest.parse_status, "snapshot_id": latest.id, "phases": [_phase_dict(x) for x in latest.phases], "warnings": []}
    parsed = parse_roadmap(text)
    snapshot = RoadmapSnapshot(project_id=p.id, source_path=p.roadmap_path, source_sha=(meta or {}).get("sha"), markdown_text=text, fetched_at=datetime.utcnow(), parsed_at=datetime.utcnow(), parse_status=parsed["status"], parse_error="; ".join(parsed.get("warnings") or []) or None)
    db.add(snapshot)
    db.flush()
    phases: list[RoadmapPhase] = []
    for phase_data in parsed.get("phases", []):
        phase = RoadmapPhase(project_id=p.id, snapshot_id=snapshot.id, version=phase_data.get("version"), title=phase_data.get("title") or phase_data.get("heading"), phase_type=phase_data.get("phase_type", "Section"), status=phase_data.get("status", "Unknown"), sort_order=phase_data.get("sort_order", 0), heading_level=phase_data.get("heading_level", 2), raw_heading=phase_data.get("raw_heading") or phase_data.get("heading", ""))
        db.add(phase)
        db.flush()
        for item in phase_data.get("items", []):
            db.add(RoadmapItem(roadmap_phase_id=phase.id, text=item["text"], completed=bool(item.get("completed")), sort_order=item.get("sort_order", 0)))
        phases.append(phase)
    db.flush()
    current_id, next_id = _choose_current_next(p, phases)
    p.roadmap_current_phase_id = current_id
    p.roadmap_next_phase_id = next_id
    db.commit()
    return {"status": parsed["status"], "snapshot_id": snapshot.id, "phases": [_phase_dict(x) for x in phases], "warnings": parsed.get("warnings") or []}


async def sync_project_record(p: Project, db: Session):
    gh = GitHubService()
    p.github_last_attempt_at = datetime.utcnow()
    try:
        data = await gh.discover_repository(p.repository_url or f"https://github.com/{p.github_owner}/{p.github_repo}")
        version = data.get("version") or {}
        commit = data.get("latest_commit")
        p.repository_url = data.get("repository_url")
        p.repository_description = data.get("description")
        p.repository_visibility = data.get("visibility")
        p.default_branch = data.get("default_branch") or p.default_branch
        if version.get("version"):
            p.latest_version = version.get("version")
            p.latest_release_url = version.get("url")
            p.latest_release_at = gh.parse_github_datetime(version.get("published_at"))
        p.github_cache_json = json.dumps({"open_pr_count": len(data.get("open_prs") or []), "open_prs": open_pr_summary(data.get("open_prs") or []), "last_merged_pr": data.get("last_merged_pr"), "latest_commit": commit, "ci": data.get("ci"), "version_source": version.get("source", "Unknown")})
        p.github_refreshed_at = datetime.utcnow()
        p.github_sync_status = "Synced"
        p.github_sync_error = None
        db.commit(); db.refresh(p)
        try:
            await sync_roadmap_record(p, db, force=False)
        except Exception:
            pass
        return data
    except Exception as exc:
        p.github_sync_status = "Failed"
        p.github_sync_error = str(exc)
        db.commit()
        raise


async def sync_active_projects_once():
    db = SessionLocal()
    try:
        for project in db.scalars(select(Project).where(Project.active == True)).all():
            try:
                await sync_project_record(project, db)
            except Exception:
                continue
    finally:
        db.close()


async def background_sync_loop():
    while True:
        await asyncio.sleep(BACKGROUND_SYNC_SECONDS)
        await sync_active_projects_once()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(background_sync_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="DevHub", version=APP_VERSION, lifespan=lifespan)

@app.get("/api/health")
def health(): return {"status": "ok", "version": APP_VERSION}

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
    p = Project(name=payload.name or data["name"], code=code, github_owner=data["owner"], github_repo=data["repo"], repository_url=data["repository_url"], repository_description=data.get("description"), repository_visibility=data.get("visibility"), default_branch=data["default_branch"], roadmap_path=payload.roadmap_path or data.get("roadmap_path") or "ROADMAP.md", changelog_path=payload.changelog_path or data.get("changelog_path") or "CHANGELOG.md", active=True, github_sync_status="Never")
    db.add(p); db.commit(); db.refresh(p); await sync_project_record(p, db); return p

@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Project).where(Project.code == payload.code.upper())): raise HTTPException(409, "Project code already exists")
    if db.scalar(select(Project).where(Project.github_owner == payload.github_owner, Project.github_repo == payload.github_repo)): raise HTTPException(409, "This GitHub repository is already configured")
    p = Project(**payload.model_dump()); p.code = p.code.upper(); p.repository_url = p.repository_url or f"https://github.com/{p.github_owner}/{p.github_repo}"
    db.add(p); db.commit(); db.refresh(p); return p

@app.put("/api/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectCreate, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    for key, value in payload.model_dump().items(): setattr(p, key, value)
    p.code = p.code.upper(); db.commit(); db.refresh(p); return p

@app.post("/api/projects/{project_id}/refresh")
async def refresh_project(project_id: int, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    try: return {"project": ProjectOut.model_validate(p), "github": await sync_project_record(p, db)}
    except Exception as exc: raise HTTPException(502, f"GitHub refresh failed: {exc}")

@app.post("/api/projects/refresh-all")
async def refresh_all(db: Session = Depends(get_db)):
    result=[]
    for p in db.scalars(select(Project).where(Project.active == True)).all():
        try: await sync_project_record(p, db); result.append({"id":p.id,"status":"Synced"})
        except Exception as exc: result.append({"id":p.id,"status":"Failed","error":str(exc)})
    return result

@app.get("/api/projects/sync-summary")
def sync_summary(db: Session = Depends(get_db)):
    projects=list(db.scalars(select(Project).where(Project.active == True)).all()); failed=[p for p in projects if p.github_sync_status=="Failed"]; refreshed=[p.github_refreshed_at for p in projects if p.github_refreshed_at]
    return {"active_projects":len(projects),"failed_projects":len(failed),"status":"Operational" if not failed else "Degraded","last_successful_sync":max(refreshed).isoformat() if refreshed else None,"interval_seconds":BACKGROUND_SYNC_SECONDS}

@app.get("/api/projects/{project_id}/roadmap/intelligence")
async def roadmap_intelligence(project_id: int, db: Session = Depends(get_db)):
    p=project_or_404(db,project_id)
    latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc()))
    if not latest: return await sync_roadmap_record(p,db,force=True)
    phases=[_phase_dict(x) for x in latest.phases]
    return {"status":latest.parse_status,"snapshot_id":latest.id,"source_path":latest.source_path,"source_sha":latest.source_sha,"fetched_at":latest.fetched_at,"parsed_at":latest.parsed_at,"error":latest.parse_error,"current_phase_id":p.roadmap_current_phase_id,"next_phase_id":p.roadmap_next_phase_id,"phases":phases}

@app.post("/api/projects/{project_id}/roadmap/reparse")
async def reparse_roadmap(project_id:int,db:Session=Depends(get_db)):
    return await sync_roadmap_record(project_or_404(db,project_id),db,force=True)

@app.put("/api/projects/{project_id}/roadmap/selection")
def roadmap_selection(project_id:int,payload:dict,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    current=payload.get("current_phase_id"); nxt=payload.get("next_phase_id")
    for value in (current,nxt):
        if value is not None:
            phase=db.get(RoadmapPhase,int(value))
            if not phase or phase.project_id!=p.id: raise HTTPException(422,"Roadmap phase does not belong to this project")
    p.roadmap_current_phase_id=current; p.roadmap_next_phase_id=nxt; db.commit(); return {"current_phase_id":current,"next_phase_id":nxt}

@app.put("/api/roadmap/phases/{phase_id}")
def update_roadmap_phase(phase_id:int,payload:dict,db:Session=Depends(get_db)):
    phase=db.get(RoadmapPhase,phase_id)
    if not phase: raise HTTPException(404,"Roadmap phase not found")
    if "ignored" in payload: phase.ignored=bool(payload["ignored"])
    if payload.get("status") in {"Completed","In Progress","Planned","Future","Unknown"}: phase.status=payload["status"]
    db.commit(); return _phase_dict(phase)

@app.get("/api/roadmap/phases/{phase_id}")
def roadmap_phase_detail(phase_id:int,db:Session=Depends(get_db)):
    phase=db.scalar(select(RoadmapPhase).options(selectinload(RoadmapPhase.items),selectinload(RoadmapPhase.register_items)).where(RoadmapPhase.id==phase_id))
    if not phase: raise HTTPException(404,"Roadmap phase not found")
    return _phase_dict(phase)

@app.get("/api/projects/{project_id}/roadmap")
async def roadmap(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    try:
        text=await GitHubService().file_text(p.github_owner,p.github_repo,p.roadmap_path,p.default_branch)
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
    for c in payload.criteria: db.add(AcceptanceCriterion(item_id=item.id,**c.model_dump()))
    db.commit(); return item_or_404(db,item.id)

@app.put("/api/register/{item_id}",response_model=RegisterItemOut)
def update_item(item_id:int,payload:RegisterItemUpdate,db:Session=Depends(get_db)):
    item=item_or_404(db,item_id)
    changes=payload.model_dump(exclude_unset=True)
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
    project_or_404(db,payload.project_id); r=Release(project_id=payload.project_id,planned_version=payload.planned_version,notes=payload.notes); db.add(r); db.flush()
    for item_id in payload.item_ids:
        item=item_or_404(db,item_id)
        if item.project_id!=payload.project_id: raise HTTPException(422,"Release item belongs to another project")
        db.add(ReleaseItem(release_id=r.id,item_id=item_id))
    db.commit(); db.refresh(r); return r

@app.post("/api/releases/{release_id}/prompt")
async def release_prompt(release_id:int,db:Session=Depends(get_db)):
    r=db.scalar(select(Release).options(selectinload(Release.scope).selectinload(ReleaseItem.item).selectinload(RegisterItem.criteria),selectinload(Release.scope).selectinload(ReleaseItem.item).selectinload(RegisterItem.attachments)).where(Release.id==release_id))
    if not r: raise HTTPException(404,"Release not found")
    p=project_or_404(db,r.project_id); roadmap_text=await GitHubService().file_text(p.github_owner,p.github_repo,p.roadmap_path,p.default_branch); changelog_text=await GitHubService().file_text(p.github_owner,p.github_repo,p.changelog_path,p.default_branch)
    latest=db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id==p.id).order_by(RoadmapSnapshot.id.desc())); current=db.get(RoadmapPhase,p.roadmap_current_phase_id) if p.roadmap_current_phase_id else None; nxt=db.get(RoadmapPhase,p.roadmap_next_phase_id) if p.roadmap_next_phase_id else None
    structured={"current":_phase_dict(current) if current else None,"next":_phase_dict(nxt) if nxt else None,"parse_status":latest.parse_status if latest else "Unknown"}
    return {"prompt":build_release_prompt(p,r,roadmap_text,changelog_text,structured)}

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
