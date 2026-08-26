import base64
import os
from datetime import datetime, timezone
import httpx

class GitHubService:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("DEVHUB_GITHUB_TOKEN", "")
        self.base = "https://api.github.com"

    @property
    def headers(self):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _get(self, path: str):
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base}{path}", headers=self.headers)
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

    async def file_text(self, owner: str, repo: str, path: str, ref: str):
        data = await self._get(f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
        if not data:
            return None
        if data.get("encoding") != "base64" or "content" not in data:
            return None
        return base64.b64decode(data["content"]).decode("utf-8")

    async def open_pull_requests(self, owner: str, repo: str):
        data = await self._get(f"/repos/{owner}/{repo}/pulls?state=open&per_page=100")
        return data or []

    async def latest_commit(self, owner: str, repo: str, branch: str):
        data = await self._get(f"/repos/{owner}/{repo}/commits/{branch}")
        if not data:
            return None
        commit = data.get("commit", {})
        return {"sha": data.get("sha"), "url": data.get("html_url"), "date": commit.get("committer", {}).get("date")}

    @staticmethod
    def parse_github_datetime(value: str | None):
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
