import pytest

from backend.app.github_service import GitHubService


@pytest.mark.asyncio
async def test_completed_successful_checks_override_stale_combined_pending(monkeypatch):
    service=GitHubService()
    async def fake_get(path):
        if path.endswith('/status'):
            return {'state':'pending','statuses':[]}
        if 'check-runs' in path:
            return {'check_runs':[{'name':'CI','status':'completed','conclusion':'success','html_url':'https://example.test/check'}]}
        raise AssertionError(path)
    monkeypatch.setattr(service,'_get',fake_get)
    result=await service.combined_status('owner','repo','abc123')
    assert result['state']=='success'
    assert result['commit_sha']=='abc123'


@pytest.mark.asyncio
async def test_in_progress_check_is_pending(monkeypatch):
    service=GitHubService()
    async def fake_get(path):
        if path.endswith('/status'):
            return {'state':'success','statuses':[]}
        return {'check_runs':[{'name':'CI','status':'in_progress','conclusion':None}]}
    monkeypatch.setattr(service,'_get',fake_get)
    result=await service.combined_status('owner','repo','abc123')
    assert result['state']=='pending'


@pytest.mark.asyncio
async def test_failed_check_is_failure(monkeypatch):
    service=GitHubService()
    async def fake_get(path):
        if path.endswith('/status'):
            return {'state':'success','statuses':[]}
        return {'check_runs':[{'name':'CI','status':'completed','conclusion':'failure'}]}
    monkeypatch.setattr(service,'_get',fake_get)
    result=await service.combined_status('owner','repo','abc123')
    assert result['state']=='failure'


@pytest.mark.asyncio
async def test_no_ci_information_is_unknown(monkeypatch):
    service=GitHubService()
    async def fake_get(path):
        if path.endswith('/status'):
            return {'state':'pending','statuses':[]}
        return {'check_runs':[]}
    monkeypatch.setattr(service,'_get',fake_get)
    result=await service.combined_status('owner','repo','abc123')
    assert result['state']=='unknown'
