import json
import re
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import get_db
from .github_service import GitHubService
from .models import AcceptanceTestResult, RegisterItem, Release, ReleaseItem, RoadmapPhase, RoadmapSnapshot
from .prompt_builder import build_release_prompt
from .roadmap_parser import version_contains


def _normalise_version(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    return value[1:] if value.startswith("v") else value


def _release_or_404(db: Session, release_id: int) -> Release:
    stmt = (
        select(Release)
        .options(
            selectinload(Release.scope).selectinload(ReleaseItem.item).selectinload(RegisterItem.criteria),
            selectinload(Release.results).selectinload(AcceptanceTestResult.criterion),
            selectinload(Release.roadmap_phase).selectinload(RoadmapPhase.items),
        )
        .where(Release.id == release_id)
    )
    release = db.scalar(stmt)
    if not release:
        raise HTTPException(404, "Release not found")
    return release


def _project_cache(project) -> dict:
    try:
        return json.loads(project.github_cache_json or "{}")
    except Exception:
        return {}


def _pr_number_from_url(url: str | None) -> int | None:
    if not url:
        return None
    match = re.search(r"/pull/(\d+)(?:/|$)", url)
    return int(match.group(1)) if match else None


def _score_pr(pr: dict, release: Release) -> tuple[int, list[str]]:
    version = _normalise_version(release.planned_version)
    title = str(pr.get("title") or "").lower()
    branch = str((pr.get("head") or {}).get("ref") or "").lower()
    score = 0
    evidence: list[str] = []
    if version:
        tokens = {version, f"v{version}"}
        if any(token in title for token in tokens):
            score += 6
            evidence.append("planned version appears in PR title")
        if any(token in branch for token in tokens):
            score += 5
            evidence.append("planned version appears in branch name")
    if release.roadmap_phase and release.roadmap_phase.title:
        words = [word.lower() for word in re.findall(r"[A-Za-z0-9]+", release.roadmap_phase.title) if len(word) >= 5]
        matches = sum(1 for word in words[:8] if word in title)
        if matches >= 2:
            score += 2
            evidence.append("PR title matches roadmap phase wording")
    return score, evidence


async def _all_pull_requests(gh: GitHubService, owner: str, repo: str) -> list[dict]:
    return await gh._get(f"/repos/{owner}/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=100") or []


async def _resolve_pr(gh: GitHubService, project, release: Release) -> dict:
    explicit_number = _pr_number_from_url(release.pr_url)
    if explicit_number:
        pr = await gh._get(f"/repos/{project.github_owner}/{project.github_repo}/pulls/{explicit_number}")
        if pr:
            return {
                "pr": pr,
                "association": {"method": "User confirmed", "confidence": "Confirmed", "evidence": ["PR explicitly associated with this DevHub release"]},
                "candidates": [],
            }

    candidates = []
    for pr in await _all_pull_requests(gh, project.github_owner, project.github_repo):
        score, evidence = _score_pr(pr, release)
        if score > 0:
            candidates.append({"score": score, "evidence": evidence, "pr": pr})
    candidates.sort(key=lambda row: (row["score"], row["pr"].get("updated_at") or ""), reverse=True)
    if candidates:
        top = candidates[0]
        tied = len(candidates) > 1 and candidates[1]["score"] == top["score"]
        if top["score"] >= 5 and not tied:
            confidence = "High" if top["score"] >= 6 else "Moderate"
            return {
                "pr": top["pr"],
                "association": {"method": "Detected", "confidence": confidence, "evidence": top["evidence"]},
                "candidates": [_candidate_summary(row) for row in candidates[:5]],
            }
    return {
        "pr": None,
        "association": {"method": "None", "confidence": "Unable to determine", "evidence": ["No unique high-confidence implementation PR match"]},
        "candidates": [_candidate_summary(row) for row in candidates[:5]],
    }


def _candidate_summary(row: dict) -> dict:
    pr = row["pr"]
    return {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "url": pr.get("html_url"),
        "branch": (pr.get("head") or {}).get("ref"),
        "state": pr.get("state"),
        "draft": bool(pr.get("draft")),
        "updated_at": pr.get("updated_at"),
        "score": row["score"],
        "evidence": row["evidence"],
    }


def _pr_summary(pr: dict | None) -> dict | None:
    if not pr:
        return None
    return {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "url": pr.get("html_url"),
        "branch": (pr.get("head") or {}).get("ref"),
        "head_sha": (pr.get("head") or {}).get("sha"),
        "state": pr.get("state"),
        "draft": bool(pr.get("draft")),
        "mergeable": pr.get("mergeable"),
        "mergeable_state": pr.get("mergeable_state"),
        "merged": bool(pr.get("merged_at")),
        "merged_at": pr.get("merged_at"),
        "merge_commit_sha": pr.get("merge_commit_sha"),
        "updated_at": pr.get("updated_at"),
    }


def _merge_readiness(pr: dict | None, ci: dict) -> dict:
    reasons: list[str] = []
    if not pr:
        return {"ready": False, "status": "Not ready", "reasons": ["No implementation PR is associated or confidently detected"]}
    if pr.get("merged_at"):
        return {"ready": False, "status": "Merged", "reasons": ["Implementation PR is already merged"]}
    if pr.get("state") != "open":
        reasons.append("PR is closed without merge")
    if pr.get("draft"):
        reasons.append("PR is still a draft")
    if ci.get("state") == "failure":
        reasons.append("CI is failing")
    elif ci.get("state") == "pending":
        reasons.append("CI is still running")
    elif ci.get("state") != "success":
        reasons.append("Required CI success is not confirmed")
    if pr.get("mergeable") is False:
        reasons.append("GitHub reports the PR is not mergeable")
    elif pr.get("mergeable") is not True:
        reasons.append("GitHub mergeability is not yet confirmed")
    ready = not reasons and pr.get("state") == "open" and not pr.get("draft") and ci.get("state") == "success" and pr.get("mergeable") is True
    return {"ready": ready, "status": "Ready to merge" if ready else "Not ready", "reasons": reasons}


async def _release_evidence(gh: GitHubService, project, release: Release) -> dict:
    planned = _normalise_version(release.planned_version)
    releases = await gh._get(f"/repos/{project.github_owner}/{project.github_repo}/releases?per_page=100") or []
    published = next((item for item in releases if not item.get("draft") and _normalise_version(item.get("tag_name")) == planned), None) if planned else None
    tags = await gh.tags(project.github_owner, project.github_repo)
    tag = next((item for item in tags if _normalise_version(item.get("name")) == planned), None) if planned else None
    cache = _project_cache(project)
    evidence = cache.get("version_evidence") or []
    matching_sources = [item for item in evidence if _normalise_version(item.get("version")) == planned] if planned else []
    return {
        "source_version_present": bool(matching_sources),
        "matching_sources": matching_sources,
        "github_release_published": bool(published),
        "github_release": {"tag": published.get("tag_name"), "url": published.get("html_url"), "published_at": published.get("published_at") or published.get("created_at")} if published else None,
        "git_tag_present": bool(tag),
        "git_tag": tag.get("name") if tag else None,
    }


def _scope_summary(release: Release) -> list[dict]:
    result_by_criterion = {result.criterion_id: result.status for result in release.results}
    rows = []
    for link in release.scope:
        item = link.item
        criteria = item.criteria or []
        passed = sum(1 for criterion in criteria if result_by_criterion.get(criterion.id) in {"Pass", "Not Applicable"})
        rows.append({
            "id": item.id,
            "item_key": item.item_key,
            "item_type": item.item_type,
            "title": item.title,
            "priority": item.priority,
            "status": item.status,
            "criteria_total": len(criteria),
            "criteria_passed": passed,
            "acceptance_status": "Complete" if criteria and passed == len(criteria) else ("Not started" if passed == 0 else "In progress"),
        })
    return rows


def _stage(status: str, detail: str | None = None) -> dict:
    return {"status": status, "detail": detail}


async def execution_state(release: Release, project, db: Session) -> dict:
    gh = GitHubService()
    resolved = await _resolve_pr(gh, project, release)
    raw_pr = resolved["pr"]
    if raw_pr and raw_pr.get("number"):
        detailed = await gh._get(f"/repos/{project.github_owner}/{project.github_repo}/pulls/{raw_pr['number']}")
        if detailed:
            raw_pr = detailed
    pr = _pr_summary(raw_pr)
    ci = await gh.combined_status(project.github_owner, project.github_repo, pr.get("head_sha") if pr else None)
    readiness = _merge_readiness(raw_pr, ci)
    evidence = await _release_evidence(gh, project, release)

    from .main import sync_changelog_record
    from .reconciliation import reconcile_release

    changelog = await sync_changelog_record(project, db, force=False)
    reconciliation = reconcile_release(project.latest_version, release, release.roadmap_phase, changelog)

    scope = _scope_summary(release)
    if reconciliation.get("status") == "Reconciled" and evidence["github_release_published"]:
        lifecycle = "Reconciled"
    elif evidence["github_release_published"]:
        lifecycle = "Released"
    elif pr and pr.get("merged"):
        lifecycle = "Merged"
    elif readiness["ready"]:
        lifecycle = "Ready to Merge"
    elif ci.get("state") == "pending":
        lifecycle = "CI Running"
    elif pr:
        lifecycle = "PR Open" if pr.get("state") == "open" else "Attention required"
    elif scope:
        lifecycle = "Ready for Development"
    else:
        lifecycle = "Planning"

    ci_stage = "Passing" if ci.get("state") == "success" else "Failing" if ci.get("state") == "failure" else "In progress" if ci.get("state") == "pending" else "Not started"
    stages = {
        "development": _stage("Complete" if pr and pr.get("merged") else "In progress" if pr else "Ready" if scope else "Not started", pr.get("branch") if pr else None),
        "pull_request": _stage("Complete" if pr and pr.get("merged") else "In progress" if pr else "Waiting", f"#{pr['number']}" if pr else None),
        "ci": _stage(ci_stage),
        "merge": _stage("Complete" if pr and pr.get("merged") else "Ready" if readiness["ready"] else "Waiting"),
        "github_release": _stage("Complete" if evidence["github_release_published"] else "Waiting"),
        "reconciliation": _stage("Complete" if reconciliation.get("status") == "Reconciled" else "Attention required" if evidence["github_release_published"] else "Waiting", reconciliation.get("status")),
    }
    return {
        "release_id": release.id,
        "project_id": project.id,
        "planned_version": release.planned_version,
        "title": release.roadmap_phase.title if release.roadmap_phase else None,
        "lifecycle": lifecycle,
        "scope": scope,
        "scope_count": len(scope),
        "pr": pr,
        "pr_association": resolved["association"],
        "pr_candidates": resolved["candidates"],
        "ci": ci,
        "merge_readiness": readiness,
        "release_evidence": evidence,
        "reconciliation": reconciliation,
        "changelog": changelog,
        "stages": stages,
        "supervised": True,
    }


def register_release_execution_routes(app):
    @app.get("/api/releases/{release_id}/execution")
    async def get_release_execution(release_id: int, db: Session = Depends(get_db)):
        release = _release_or_404(db, release_id)
        project = release.project
        return await execution_state(release, project, db)

    @app.put("/api/releases/{release_id}/execution/pr")
    async def associate_release_pr(release_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
        release = _release_or_404(db, release_id)
        project = release.project
        number = payload.get("pr_number")
        if number in (None, ""):
            release.pr_url = None
            db.commit()
            return {"associated": False, "pr_url": None}
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise HTTPException(422, "pr_number must be a positive integer or null")
        if number <= 0:
            raise HTTPException(422, "pr_number must be a positive integer or null")
        gh = GitHubService()
        pr = await gh._get(f"/repos/{project.github_owner}/{project.github_repo}/pulls/{number}")
        if not pr:
            raise HTTPException(404, "Pull request not found in this project repository")
        release.pr_url = pr.get("html_url")
        db.commit()
        return {"associated": True, "pr_number": number, "pr_url": release.pr_url}

    @app.post("/api/releases/{release_id}/execution/prompt")
    async def execution_prompt(release_id: int, db: Session = Depends(get_db)):
        release = _release_or_404(db, release_id)
        project = release.project
        state = await execution_state(release, project, db)
        latest = db.scalar(select(RoadmapSnapshot).where(RoadmapSnapshot.project_id == project.id).order_by(RoadmapSnapshot.id.desc()))
        current = db.get(RoadmapPhase, project.roadmap_current_phase_id) if project.roadmap_current_phase_id else None
        nxt = db.get(RoadmapPhase, project.roadmap_next_phase_id) if project.roadmap_next_phase_id else None
        from .main import _phase_dict
        structured = {
            "current": _phase_dict(current, project.latest_version) if current else None,
            "current_source": "User confirmed" if project.roadmap_current_override else "Detected",
            "next": _phase_dict(nxt, project.latest_version) if nxt else None,
            "next_source": "User override" if project.roadmap_next_override else "Detected",
            "selected_release_phase": _phase_dict(release.roadmap_phase, project.latest_version) if release.roadmap_phase else None,
            "parse_status": latest.parse_status if latest else "Unknown",
            "detected_release": project.latest_version,
            "version_source": _project_cache(project).get("version_source", "Unknown"),
            "reconciliation": state["reconciliation"],
            "changelog": state["changelog"],
        }
        base = build_release_prompt(project, release, None, None, structured)
        execution_lines = [
            "",
            "RELEASE EXECUTION CONTEXT:",
            f"- Planned version: {release.planned_version or 'Not set'}",
            f"- Current execution lifecycle: {state['lifecycle']}",
            f"- Associated PR: #{state['pr']['number']} {state['pr']['title']}" if state.get("pr") else "- Associated PR: None confirmed",
            f"- CI baseline: {state['ci'].get('state') or 'unknown'}",
            f"- Merge readiness: {state['merge_readiness']['status']}",
            f"- GitHub Release published: {'Yes' if state['release_evidence']['github_release_published'] else 'No'}",
            "",
            "Supervised execution requirements:",
            "1. Inspect latest main/default branch before making changes.",
            "2. Reconcile this approved scope against the repository without silently adding or removing work.",
            "3. Create a dedicated release branch.",
            "4. Implement only the approved DevHub release scope.",
            "5. Update and run relevant tests.",
            "6. Update version metadata consistently.",
            "7. Update changelogs and documentation where required.",
            "8. Create one focused Pull Request.",
            "9. Do not merge the Pull Request automatically.",
            "10. Do not publish a GitHub Release or deploy software without an explicit user action.",
        ]
        return {"prompt": base + "\n" + "\n".join(execution_lines)}

    @app.get("/api/releases/execution-summary")
    async def release_execution_summary(db: Session = Depends(get_db)):
        releases = list(db.scalars(select(Release).order_by(Release.created_at.desc())))
        seen: set[int] = set()
        output = []
        for release in releases:
            if release.project_id in seen or release.status == "Released":
                continue
            seen.add(release.project_id)
            loaded = _release_or_404(db, release.id)
            try:
                state = await execution_state(loaded, loaded.project, db)
            except Exception as exc:
                state = {"release_id": loaded.id, "project_id": loaded.project_id, "lifecycle": "Attention required", "error": str(exc)}
            output.append(state)
        return output
