import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
import bleach
import markdown
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from .database import Base, engine, get_db
from .github_service import GitHubService
from .models import AcceptanceCriterion, AcceptanceTestResult, Attachment, Project, RegisterItem, Release, ReleaseItem
from .prompt_builder import build_release_prompt
from .schemas import ProjectCreate, ProjectDiscover, ProjectFromUrl, ProjectOut, RegisterItemCreate, RegisterItemOut, RegisterItemUpdate, ReleaseCreate, ReleaseOut, TestResultUpdate, TEST_STATUSES

APP_VERSION = "0.2.0"
DATA_DIR = Path(os.getenv("DEVHUB_DATA_DIR", "./data"))
UPLOAD_DIR = DATA_DIR / "uploads"
PROJECT_LOGO_DIR = DATA_DIR / "project-logos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_LOGO_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4", "video/quicktime", "video/webm"}
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}

app = FastAPI(title="DevHub", version=APP_VERSION)
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
    type_code = {"Defect":"DEF", "Enhancement":"ENH", "UX Improvement":"UX", "Technical Debt":"TECH", "Performance":"PERF", "Security":"SEC", "Documentation":"DOC"}.get(item_type, "ITEM")
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
    return [
        {
            "number": p.get("number"),
            "title": p.get("title"),
            "url": p.get("html_url"),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
            "draft": bool(p.get("draft")),
            "head": (p.get("head") or {}).get("ref"),
        }
        for p in prs
    ]

async def sync_project_record(p: Project, db: Session):
    gh = GitHubService()
    p.github_last_attempt_at = datetime.utcnow()
    try:
        data = await gh.discover_repository(p.repository_url or f"https://github.com/{p.github_owner}/{p.github_repo}")
        release = data.get("latest_release")
        commit = data.get("latest_commit")
        p.repository_url = data.get("repository_url")
        p.repository_description = data.get("description")
        p.repository_visibility = data.get("visibility")
        p.default_branch = data.get("default_branch") or p.default_branch
        if release:
            p.latest_version = release.get("tag_name")
            p.latest_release_url = release.get("html_url")
            p.latest_release_at = gh.parse_github_datetime(release.get("published_at") or release.get("created_at"))
        p.github_cache_json = json.dumps({
            "open_pr_count": len(data.get("open_prs") or []),
            "open_prs": open_pr_summary(data.get("open_prs") or []),
            "last_merged_pr": data.get("last_merged_pr"),
            "latest_commit": commit,
            "ci": data.get("ci"),
        })
        p.github_refreshed_at = datetime.utcnow()
        p.github_sync_status = "Synced"
        p.github_sync_error = None
        db.commit(); db.refresh(p)
        return data
    except Exception as exc:
        p.github_sync_status = "Failed"
        p.github_sync_error = str(exc)
        db.commit()
        raise

@app.get("/api/health")
def health():
    return {"status":"ok", "version":APP_VERSION}

@app.get("/api/projects", response_model=list[ProjectOut])
def projects(db: Session = Depends(get_db)):
    return list(db.scalars(select(Project).order_by(Project.name)))

@app.post("/api/projects/discover")
async def discover_project(payload: ProjectDiscover):
    try:
        return await GitHubService().discover_repository(payload.repository_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"GitHub discovery failed: {exc}")

@app.post("/api/projects/from-url", response_model=ProjectOut, status_code=201)
async def create_project_from_url(payload: ProjectFromUrl, db: Session = Depends(get_db)):
    gh = GitHubService()
    try:
        data = await gh.discover_repository(payload.repository_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"GitHub discovery failed: {exc}")
    if db.scalar(select(Project).where(Project.github_owner == data["owner"], Project.github_repo == data["repo"])):
        raise HTTPException(409, "This GitHub repository is already configured")
    code = (payload.code or default_code(data["repo"])).upper()
    if db.scalar(select(Project).where(Project.code == code)):
        code = f"{code[:9]}{uuid.uuid4().hex[:3].upper()}"
    p = Project(
        name=payload.name or data["name"], code=code, github_owner=data["owner"], github_repo=data["repo"],
        repository_url=data["repository_url"], repository_description=data.get("description"), repository_visibility=data.get("visibility"),
        default_branch=data["default_branch"], roadmap_path=payload.roadmap_path or data.get("roadmap_path") or "ROADMAP.md",
        changelog_path=payload.changelog_path or data.get("changelog_path") or "CHANGELOG.md", active=True,
        github_sync_status="Never",
    )
    db.add(p); db.commit(); db.refresh(p)
    await sync_project_record(p, db)
    return p

@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Project).where(Project.code == payload.code.upper())):
        raise HTTPException(409, "Project code already exists")
    if db.scalar(select(Project).where(Project.github_owner == payload.github_owner, Project.github_repo == payload.github_repo)):
        raise HTTPException(409, "This GitHub repository is already configured")
    p = Project(**payload.model_dump())
    p.code = p.code.upper()
    p.repository_url = p.repository_url or f"https://github.com/{p.github_owner}/{p.github_repo}"
    db.add(p); db.commit(); db.refresh(p)
    return p

@app.put("/api/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectCreate, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    for key, value in payload.model_dump().items(): setattr(p, key, value)
    p.code = p.code.upper()
    db.commit(); db.refresh(p)
    return p

@app.post("/api/projects/{project_id}/refresh")
async def refresh_project(project_id: int, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    try:
        data = await sync_project_record(p, db)
        return {"project": ProjectOut.model_validate(p), "github": data}
    except Exception as exc:
        raise HTTPException(502, f"GitHub refresh failed: {exc}")

@app.post("/api/projects/refresh-all")
async def refresh_all(db: Session = Depends(get_db)):
    result=[]
    for p in db.scalars(select(Project).where(Project.active == True)).all():
        try:
            await sync_project_record(p, db); result.append({"id":p.id,"status":"Synced"})
        except Exception as exc:
            result.append({"id":p.id,"status":"Failed","error":str(exc)})
    return result

@app.post("/api/projects/{project_id}/logo")
async def upload_project_logo(project_id:int,file:UploadFile=File(...),db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if file.content_type not in ALLOWED_LOGO_TYPES: raise HTTPException(415,"Logo must be SVG, PNG, WebP or JPEG")
    data=await file.read(5*1024*1024+1)
    if len(data)>5*1024*1024: raise HTTPException(413,"Logo exceeds 5 MB limit")
    suffix={"image/svg+xml":".svg","image/png":".png","image/webp":".webp","image/jpeg":".jpg"}[file.content_type]
    stored=f"project-{p.id}-{uuid.uuid4().hex}{suffix}"
    path=PROJECT_LOGO_DIR/stored; path.write_bytes(data)
    if p.logo_path:
        old=PROJECT_LOGO_DIR/Path(p.logo_path).name
        if old.exists(): old.unlink()
    p.logo_path=stored; db.commit(); db.refresh(p)
    return {"logo_url":f"/api/projects/{p.id}/logo"}

@app.get("/api/projects/{project_id}/logo")
def project_logo(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if not p.logo_path: raise HTTPException(404,"Project logo not configured")
    path=(PROJECT_LOGO_DIR/Path(p.logo_path).name).resolve()
    if PROJECT_LOGO_DIR.resolve() not in path.parents or not path.exists(): raise HTTPException(404,"Project logo missing")
    return FileResponse(path)

@app.delete("/api/projects/{project_id}/logo", status_code=204)
def delete_project_logo(project_id:int,db:Session=Depends(get_db)):
    p=project_or_404(db,project_id)
    if p.logo_path:
        path=PROJECT_LOGO_DIR/Path(p.logo_path).name
        if path.exists(): path.unlink()
    p.logo_path=None; db.commit()

@app.get("/api/projects/{project_id}/roadmap")
async def roadmap(project_id: int, db: Session = Depends(get_db)):
    p = project_or_404(db, project_id)
    try:
        text = await GitHubService().file_text(p.github_owner,p.github_repo,p.roadmap_path,p.default_branch)
        if text is None: raise HTTPException(404, "Configured roadmap file was not found")
        html = bleach.clean(markdown.markdown(text, extensions=["tables", "fenced_code"]), tags=set(bleach.sanitizer.ALLOWED_TAGS)|{"p","pre","h1","h2","h3","h4","h5","h6","table","thead","tbody","tr","th","td"}, attributes={"a":["href","title"]})
        return {"path":p.roadmap_path,"markdown":text,"html":html,"github_url":f"https://github.com/{p.github_owner}/{p.github_repo}/blob/{p.default_branch}/{p.roadmap_path}"}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502, f"Roadmap retrieval failed: {exc}")

@app.get("/api/register", response_model=list[RegisterItemOut])
def list_register(project_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(RegisterItem).options(selectinload(RegisterItem.criteria),selectinload(RegisterItem.attachments)).order_by(RegisterItem.created_at.desc())
    if project_id: stmt = stmt.where(RegisterItem.project_id == project_id)
    return list(db.scalars(stmt).unique())

@app.post("/api/register", response_model=RegisterItemOut, status_code=201)
def create_item(payload: RegisterItemCreate, db: Session = Depends(get_db)):
    p = project_or_404(db,payload.project_id)
    data = payload.model_dump(exclude={"criteria"})
    item = RegisterItem(**data,item_key=make_item_key(db,p,payload.item_type))
    db.add(item); db.flush()
    for c in payload.criteria: db.add(AcceptanceCriterion(item_id=item.id,**c.model_dump()))
    db.commit()
    return item_or_404(db,item.id)

@app.put("/api/register/{item_id}", response_model=RegisterItemOut)
def update_item(item_id:int,payload:RegisterItemUpdate,db:Session=Depends(get_db)):
    item=item_or_404(db,item_id)
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(item,k,v)
    db.commit(); return item_or_404(db,item_id)

@app.post("/api/register/{item_id}/criteria", status_code=201)
def add_criterion(item_id:int, payload:dict, db:Session=Depends(get_db)):
    item_or_404(db,item_id)
    text=str(payload.get("description","")).strip()
    if not text: raise HTTPException(422,"Description is required")
    c=AcceptanceCriterion(item_id=item_id,description=text,sort_order=int(payload.get("sort_order",0))); db.add(c); db.commit(); db.refresh(c)
    return {"id":c.id,"description":c.description,"sort_order":c.sort_order}

@app.post("/api/register/{item_id}/attachments", response_model=list[dict])
async def upload_attachments(item_id:int, files:list[UploadFile]=File(...), db:Session=Depends(get_db)):
    item_or_404(db,item_id); result=[]
    for f in files:
        if f.content_type not in ALLOWED_TYPES: raise HTTPException(415,f"Unsupported attachment type: {f.content_type}")
        data=await f.read(MAX_UPLOAD_BYTES+1)
        if len(data)>MAX_UPLOAD_BYTES: raise HTTPException(413,"Attachment exceeds 100 MB limit")
        safe=re.sub(r"[^A-Za-z0-9._-]","_",Path(f.filename or "file").name)
        stored=f"{uuid.uuid4().hex}_{safe}"
        (UPLOAD_DIR/stored).write_bytes(data)
        a=Attachment(item_id=item_id,original_name=safe,stored_name=stored,content_type=f.content_type or "application/octet-stream",size_bytes=len(data)); db.add(a); db.flush()
        result.append({"id":a.id,"name":safe,"content_type":a.content_type,"size_bytes":a.size_bytes})
    db.commit(); return result

@app.get("/api/attachments/{attachment_id}")
def attachment(attachment_id:int,db:Session=Depends(get_db)):
    a=db.get(Attachment,attachment_id)
    if not a: raise HTTPException(404,"Attachment not found")
    path=(UPLOAD_DIR/a.stored_name).resolve()
    if UPLOAD_DIR.resolve() not in path.parents or not path.exists(): raise HTTPException(404,"Attachment file missing")
    return FileResponse(path,media_type=a.content_type,filename=a.original_name)

@app.post("/api/releases", response_model=ReleaseOut, status_code=201)
def create_release(payload:ReleaseCreate,db:Session=Depends(get_db)):
    project_or_404(db,payload.project_id)
    r=Release(project_id=payload.project_id,planned_version=payload.planned_version,notes=payload.notes); db.add(r); db.flush()
    for item_id in dict.fromkeys(payload.item_ids):
        item=item_or_404(db,item_id)
        if item.project_id!=payload.project_id: raise HTTPException(422,"All release items must belong to the release project")
        db.add(ReleaseItem(release_id=r.id,item_id=item_id)); item.status="Planned"
    db.commit(); db.refresh(r); return r

@app.get("/api/releases", response_model=list[ReleaseOut])
def releases(project_id:int|None=None,db:Session=Depends(get_db)):
    stmt=select(Release).order_by(Release.created_at.desc())
    if project_id: stmt=stmt.where(Release.project_id==project_id)
    return list(db.scalars(stmt))

@app.post("/api/releases/{release_id}/prompt")
async def release_prompt(release_id:int,db:Session=Depends(get_db)):
    stmt=select(Release).options(selectinload(Release.scope).selectinload(ReleaseItem.item).selectinload(RegisterItem.criteria),selectinload(Release.scope).selectinload(ReleaseItem.item).selectinload(RegisterItem.attachments),selectinload(Release.project)).where(Release.id==release_id)
    r=db.scalar(stmt)
    if not r: raise HTTPException(404,"Release not found")
    gh=GitHubService()
    try:
        roadmap_text=await gh.file_text(r.project.github_owner,r.project.github_repo,r.project.roadmap_path,r.project.default_branch)
        changelog_text=await gh.file_text(r.project.github_owner,r.project.github_repo,r.project.changelog_path,r.project.default_branch)
    except Exception:
        roadmap_text=changelog_text=None
    return {"prompt":build_release_prompt(r.project,r,roadmap_text,changelog_text)}

@app.post("/api/releases/{release_id}/reconcile")
async def reconcile(release_id:int,db:Session=Depends(get_db)):
    r=db.get(Release,release_id)
    if not r: raise HTTPException(404,"Release not found")
    p=project_or_404(db,r.project_id)
    release=await GitHubService().latest_release(p.github_owner,p.github_repo)
    if not release: return {"matched":False,"message":"No GitHub release detected"}
    version=release.get("tag_name")
    if r.planned_version and version!=r.planned_version: return {"matched":False,"detected_version":version}
    r.actual_version=version; r.release_url=release.get("html_url"); r.release_at=GitHubService.parse_github_datetime(release.get("published_at") or release.get("created_at")); r.status="Ready for Test"
    for link in r.scope: link.item.status="Ready for Test"
    db.commit(); return {"matched":True,"version":version,"status":r.status}

@app.put("/api/releases/{release_id}/criteria/{criterion_id}")
def update_test(release_id:int,criterion_id:int,payload:TestResultUpdate,db:Session=Depends(get_db)):
    if payload.status not in TEST_STATUSES: raise HTTPException(422,"Invalid test status")
    if not db.get(Release,release_id) or not db.get(AcceptanceCriterion,criterion_id): raise HTTPException(404,"Release or criterion not found")
    result=db.scalar(select(AcceptanceTestResult).where(AcceptanceTestResult.release_id==release_id,AcceptanceTestResult.criterion_id==criterion_id))
    if not result: result=AcceptanceTestResult(release_id=release_id,criterion_id=criterion_id); db.add(result)
    result.status=payload.status; result.notes=payload.notes; db.commit()
    return {"status":result.status,"notes":result.notes}

frontend_dist=Path(__file__).resolve().parents[2]/"frontend"/"dist"
if frontend_dist.exists():
    app.mount("/assets",StaticFiles(directory=frontend_dist/"assets"),name="assets")
    @app.get("/{full_path:path}")
    def spa(full_path:str):
        candidate=(frontend_dist/full_path).resolve()
        if full_path and frontend_dist.resolve() in candidate.parents and candidate.is_file(): return FileResponse(candidate)
        return FileResponse(frontend_dist/"index.html")
