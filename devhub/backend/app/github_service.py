import base64
import os
import re
from datetime import datetime, timezone
import httpx

class GitHubService:
    REPO_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
    SEMVER_TAG_RE = re.compile(r"^v?\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?$", re.I)

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("DEVHUB_GITHUB_TOKEN", "")
        self.base = "https://api.github.com"
        self.rate_limit = {"remaining": None, "limit": None, "reset_at": None}

    @property
    def headers(self):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @classmethod
    def parse_repository_url(cls, value: str) -> tuple[str, str]:
        value = value.strip()
        match = cls.REPO_URL_RE.match(value)
        if not match:
            raise ValueError("Enter a GitHub repository URL such as https://github.com/owner/repository")
        return match.groups()

    def _capture_rate_limit(self, response: httpx.Response):
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        reset = response.headers.get("X-RateLimit-Reset")
        self.rate_limit = {
            "remaining": int(remaining) if remaining and remaining.isdigit() else None,
            "limit": int(limit) if limit and limit.isdigit() else None,
            "reset_at": datetime.fromtimestamp(int(reset), tz=timezone.utc).replace(tzinfo=None) if reset and reset.isdigit() else None,
        }

    async def _get(self, path: str):
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base}{path}", headers=self.headers)
        self._capture_rate_limit(response)
        if response.status_code == 404:
            return None
        if response.status_code == 401:
            raise RuntimeError("GitHub authentication failed")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise RuntimeError("GitHub API rate limit exceeded")
        response.raise_for_status()
        return response.json()

    async def repository(self, owner: str, repo: str):
        return await self._get(f"/repos/{owner}/{repo}")

    async def latest_release(self, owner: str, repo: str):
        return await self._get(f"/repos/{owner}/{repo}/releases/latest")

    async def tags(self, owner: str, repo: str):
        return await self._get(f"/repos/{owner}/{repo}/tags?per_page=100") or []

    async def release_or_tag(self, owner: str, repo: str):
        release = await self.latest_release(owner, repo)
        if release:
            return {"version": release.get("tag_name"), "url": release.get("html_url"), "published_at": release.get("published_at") or release.get("created_at"), "source": "GitHub Release", "release": release}
        for tag in await self.tags(owner, repo):
            name = tag.get("name") or ""
            if self.SEMVER_TAG_RE.match(name):
                return {"version": name, "url": f"https://github.com/{owner}/{repo}/tree/{name}", "published_at": None, "source": "Git tag", "release": None}
        return {"version": None, "url": None, "published_at": None, "source": "Unknown", "release": None}

    async def file_data(self, owner: str, repo: str, path: str, ref: str):
        return await self._get(f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")

    async def file_text(self, owner: str, repo: str, path: str, ref: str):
        data = await self.file_data(owner, repo, path, ref)
        if not data or data.get("encoding") != "base64" or "content" not in data:
            return None
        return base64.b64decode(data["content"]).decode("utf-8")

    async def file_metadata(self, owner: str, repo: str, path: str, ref: str):
        data = await self.file_data(owner, repo, path, ref)
        if not data:
            return None
        return {"sha": data.get("sha"), "path": data.get("path"), "html_url": data.get("html_url")}

    async def file_text_and_metadata(self, owner: str, repo: str, path: str, ref: str):
        data = await self.file_data(owner, repo, path, ref)
        if not data:
            return None, None
        text = None
        if data.get("encoding") == "base64" and "content" in data:
            text = base64.b64decode(data["content"]).decode("utf-8")
        return text, {"sha": data.get("sha"), "path": data.get("path"), "html_url": data.get("html_url")}

    async def open_pull_requests(self, owner: str, repo: str):
        return await self._get(f"/repos/{owner}/{repo}/pulls?state=open&sort=updated&direction=desc&per_page=100") or []

    async def merged_pull_requests(self, owner: str, repo: str):
        data = await self._get(f"/repos/{owner}/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=100")
        return [p for p in (data or []) if p.get("merged_at")]

    async def last_merged_pull_request(self, owner: str, repo: str):
        merged = await self.merged_pull_requests(owner, repo)
        if not merged:
            return None
        merged.sort(key=lambda p: p.get("merged_at") or "", reverse=True)
        p = merged[0]
        return {"number": p.get("number"), "title": p.get("title"), "url": p.get("html_url"), "merged_at": p.get("merged_at"), "head": (p.get("head") or {}).get("ref")}

    async def latest_commit(self, owner: str, repo: str, branch: str):
        data = await self._get(f"/repos/{owner}/{repo}/commits/{branch}")
        if not data:
            return None
        commit = data.get("commit", {})
        return {"sha": data.get("sha"), "url": data.get("html_url"), "date": commit.get("committer", {}).get("date"), "message": commit.get("message")}

    async def combined_status(self, owner: str, repo: str, sha: str | None):
        if not sha:
            return {"state": "unknown", "statuses": [], "checks": []}
        status_data = await self._get(f"/repos/{owner}/{repo}/commits/{sha}/status") or {}
        checks_data = await self._get(f"/repos/{owner}/{repo}/commits/{sha}/check-runs?per_page=100") or {}
        checks = checks_data.get("check_runs") or []
        conclusions = [c.get("conclusion") for c in checks if c.get("status") == "completed"]
        running = any(c.get("status") in {"queued", "in_progress", "requested", "waiting", "pending"} for c in checks)
        failing = any(c in {"failure", "cancelled", "timed_out", "action_required", "startup_failure"} for c in conclusions)
        passing = bool(checks) and all(c in {"success", "neutral", "skipped"} for c in conclusions) and not running
        combined = status_data.get("state", "unknown")
        if failing or combined in {"failure", "error"}: state = "failure"
        elif running or combined == "pending": state = "pending"
        elif passing or combined == "success": state = "success"
        else: state = "unknown"
        return {"state": state, "statuses": status_data.get("statuses", []), "checks": [{"name": c.get("name"), "status": c.get("status"), "conclusion": c.get("conclusion"), "url": c.get("html_url")} for c in checks]}

    async def detect_path(self, owner: str, repo: str, ref: str, candidates: list[str]):
        for path in candidates:
            try:
                if await self.file_text(owner, repo, path, ref) is not None:
                    return path
            except Exception:
                continue
        return None

    async def discover_repository(self, repository_url: str):
        owner, repo = self.parse_repository_url(repository_url)
        metadata = await self.repository(owner, repo)
        if not metadata:
            raise ValueError("GitHub repository not found or inaccessible")
        branch = metadata.get("default_branch") or "main"
        version_info = await self.release_or_tag(owner, repo)
        prs = await self.open_pull_requests(owner, repo)
        merged = await self.last_merged_pull_request(owner, repo)
        commit = await self.latest_commit(owner, repo, branch)
        status = await self.combined_status(owner, repo, commit.get("sha") if commit else None)
        roadmap = await self.detect_path(owner, repo, branch, ["ROADMAP.md", "docs/ROADMAP.md", "Roadmap.md", "docs/roadmap.md"])
        changelog = await self.detect_path(owner, repo, branch, ["CHANGELOG.md", "docs/CHANGELOG.md", "Changelog.md", "docs/changelog.md"])
        return {"owner": owner, "repo": repo, "repository_url": metadata.get("html_url") or repository_url, "name": metadata.get("name") or repo, "description": metadata.get("description"), "visibility": metadata.get("visibility") or ("private" if metadata.get("private") else "public"), "default_branch": branch, "latest_release": version_info.get("release"), "version": version_info, "open_prs": prs, "last_merged_pr": merged, "latest_commit": commit, "ci": status, "roadmap_path": roadmap, "changelog_path": changelog, "rate_limit": self.rate_limit}

    @staticmethod
    def parse_github_datetime(value: str | None):
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
