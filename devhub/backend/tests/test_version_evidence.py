import asyncio
from backend.app.github_service import GitHubService


class FakeGitHubService(GitHubService):
    def __init__(self, release=None, tags=None, files=None):
        super().__init__(token="test")
        self._release = release
        self._tags = tags or []
        self._files = files or {}

    async def latest_release(self, owner: str, repo: str):
        return self._release

    async def tags(self, owner: str, repo: str):
        return self._tags

    async def file_text(self, owner: str, repo: str, path: str, ref: str):
        return self._files.get(path)

    async def top_level_directories(self, owner: str, repo: str, ref: str):
        directories = []
        for path in self._files:
            if "/" in path:
                directory = path.split("/", 1)[0]
                if directory not in directories:
                    directories.append(directory)
        return directories


def run(coro):
    return asyncio.run(coro)


def test_github_release_has_highest_precedence_and_conflicts_are_retained():
    gh = FakeGitHubService(
        release={"tag_name": "v2.0.0", "html_url": "https://example/release", "published_at": "2026-08-30T00:00:00Z"},
        tags=[{"name": "v1.9.0"}],
        files={
            "config.yaml": 'version: "1.8.0"\n',
            "CHANGELOG.md": "## [1.7.0]\n",
            "package.json": '{"version":"1.6.0"}',
            "backend/app/main.py": 'APP_VERSION = "1.5.0"',
        },
    )
    result = run(gh.release_or_tag("owner", "repo", "main", "CHANGELOG.md"))
    assert result["version"] == "v2.0.0"
    assert result["source"] == "GitHub Release"
    assert [item["source"] for item in result["evidence"]] == [
        "GitHub Release",
        "Git tag",
        "Home Assistant manifest",
        "CHANGELOG.md",
        "Frontend package.json",
        "Backend APP_VERSION",
    ]
    assert len({item["version"] for item in result["evidence"]}) == 6


def test_git_tag_is_second_priority_fallback():
    gh = FakeGitHubService(
        tags=[{"name": "v1.9.0"}],
        files={"config.yaml": 'version: "1.8.0"\n'},
    )
    result = run(gh.release_or_tag("owner", "repo", "main"))
    assert result["version"] == "v1.9.0"
    assert result["source"] == "Git tag"


def test_home_assistant_manifest_fallback():
    gh = FakeGitHubService(files={"config.yaml": 'name: App\nversion: "1.8.0"\n'})
    result = run(gh.release_or_tag("owner", "repo", "main"))
    assert result["version"] == "1.8.0"
    assert result["source"] == "Home Assistant manifest"


def test_nested_home_assistant_manifest_is_discovered_for_product_directory():
    gh = FakeGitHubService(files={
        "mediahub/config.yaml": 'name: MediaHub\nversion: "0.10.0-dev"\nslug: mediahub\n',
        "CHANGELOG.md": "## [Unreleased]\n\n## [0.9.0-dev]\n",
    })
    result = run(gh.release_or_tag("stunwill", "media-request-home-assistant", "main", "CHANGELOG.md"))
    assert result["version"] == "0.10.0-dev"
    assert result["source"] == "Home Assistant manifest"
    manifest = next(item for item in result["evidence"] if item["source"] == "Home Assistant manifest")
    assert manifest["path"] == "mediahub/config.yaml"


def test_highest_nested_manifest_wins_when_multiple_config_files_exist():
    gh = FakeGitHubService(files={
        "legacy/config.yaml": 'version: "0.1.1-dev"\n',
        "mediahub/config.yaml": 'version: "0.10.0-dev"\n',
    })
    result = run(gh.release_or_tag("owner", "repo", "main"))
    assert result["version"] == "0.10.0-dev"
    assert next(item for item in result["evidence"] if item["source"] == "Home Assistant manifest")["path"] == "mediahub/config.yaml"


def test_changelog_fallback():
    gh = FakeGitHubService(files={"CHANGELOG.md": "# Changelog\n\n## [1.7.0] - 2026-08-30\n"})
    result = run(gh.release_or_tag("owner", "repo", "main", "CHANGELOG.md"))
    assert result["version"] == "1.7.0"
    assert result["source"] == "CHANGELOG.md"


def test_frontend_package_fallback():
    gh = FakeGitHubService(files={"package.json": '{"name":"app","version":"1.6.0"}'})
    result = run(gh.release_or_tag("owner", "repo", "main"))
    assert result["version"] == "1.6.0"
    assert result["source"] == "Frontend package.json"


def test_backend_app_version_fallback():
    gh = FakeGitHubService(files={"backend/app/main.py": 'APP_VERSION = "1.5.0"\n'})
    result = run(gh.release_or_tag("owner", "repo", "main"))
    assert result["version"] == "1.5.0"
    assert result["source"] == "Backend APP_VERSION"


def test_unknown_only_after_supported_evidence_is_exhausted():
    gh = FakeGitHubService()
    result = run(gh.release_or_tag("owner", "repo", "main"))
    assert result["version"] is None
    assert result["source"] == "Unknown"
    assert result["evidence"] == []
