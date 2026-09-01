import os
os.environ["DEVHUB_DATABASE_URL"]="sqlite:///./test-devhub.db"
os.environ["DEVHUB_DATA_DIR"]="./test-data"
from fastapi.testclient import TestClient
from backend.app.database import Base, engine
from backend.app.github_service import GitHubService
from backend.app.main import friendly_project_name, iso_utc
from backend.app.server import app
from datetime import datetime

client=TestClient(app)

def setup_module(): Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
def teardown_module(): Base.metadata.drop_all(bind=engine)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200; assert r.json()['version']=='0.6.0'

def test_sync_summary_empty_portfolio():
    r=client.get('/api/projects/sync-summary')
    assert r.status_code==200
    body=r.json()
    assert body['active_projects']==0
    assert body['failed_projects']==0
    assert body['status']=='ok'
    assert body['interval_seconds']>=300

def test_repository_url_parser():
    assert GitHubService.parse_repository_url('https://github.com/stunwill/devhub-home-assistant') == ('stunwill','devhub-home-assistant')
    try:
        GitHubService.parse_repository_url('https://example.com/stunwill/devhub-home-assistant')
        assert False
    except ValueError:
        assert True

def test_friendly_project_name():
    assert friendly_project_name('devhub-home-assistant') == 'Devhub'
    assert friendly_project_name('media-request-home-assistant') == 'Media Request'

def test_iso_utc_marks_naive_values_as_utc():
    assert iso_utc(datetime(2026,8,30,0,25,0))=='2026-08-30T00:25:00Z'

def test_version_evidence_parsers():
    assert GitHubService._manifest_version('name: App\nversion: "1.2.3"\n')=='1.2.3'
    assert GitHubService._changelog_version('# Changelog\n\n## [1.2.3] - 2026-08-30\n')=='1.2.3'
    assert GitHubService._package_version('{"name":"x","version":"1.2.3"}')=='1.2.3'
    assert GitHubService._backend_version('APP_VERSION = "1.2.3"')=='1.2.3'

def test_project_and_register_flow():
    p=client.post('/api/projects',json={"name":"Test App","code":"TA","github_owner":"owner","github_repo":"repo","repository_url":"https://github.com/owner/repo","default_branch":"main","roadmap_path":"ROADMAP.md","changelog_path":"CHANGELOG.md","active":True})
    assert p.status_code==201
    pid=p.json()['id']
    assert p.json()['github_sync_status']=='Never'
    assert p.json()['roadmap_current_override'] is False
    renamed=client.put(f'/api/projects/{pid}',json={"name":"Friendly App"})
    assert renamed.status_code==200
    assert renamed.json()['name']=='Friendly App'
    assert renamed.json()['github_owner']=='owner'
    assert renamed.json()['github_repo']=='repo'
    item=client.post('/api/register',json={"project_id":pid,"item_type":"Defect","title":"Mobile overflow","description":"Page scrolls sideways","priority":"High","status":"Approved","actual_behaviour":"Horizontal scroll","expected_behaviour":"No horizontal scroll","testing_instructions":"Test portrait mobile","criteria":[{"description":"No horizontal scrolling","sort_order":0}]})
    assert item.status_code==201
    assert item.json()['item_key']=='TA-DEF-0001'
    assert item.json()['roadmap_phase_id'] is None
    assert len(item.json()['criteria'])==1
    release=client.post('/api/releases',json={"project_id":pid,"item_ids":[item.json()['id']]})
    assert release.status_code==201
    assert release.json()['roadmap_phase_id'] is None

def test_blank_project_name_is_rejected():
    project=client.get('/api/projects').json()[0]
    r=client.put(f"/api/projects/{project['id']}",json={"name":"   "})
    assert r.status_code==422

def test_sync_summary_reports_unsynced_project():
    r=client.get('/api/projects/sync-summary')
    assert r.status_code==200
    body=r.json()
    assert body['active_projects']==1
    assert body['failed_projects']==0

def test_register_filters_accept_roadmap_fields():
    r=client.get('/api/register?priority=High&status=Approved')
    assert r.status_code==200
    assert len(r.json())==1

def test_sync_diagnostics_contract():
    rows=client.get('/api/projects/sync-diagnostics')
    assert rows.status_code==200
    assert len(rows.json())==1
    assert 'rate_limit' in rows.json()[0]
    assert 'roadmap_parse_state' in rows.json()[0]
    assert 'version_evidence' in rows.json()[0]
    assert 'ci_commit_sha' in rows.json()[0]

def test_assisted_requirements_status_disabled_by_default():
    os.environ.pop('DEVHUB_AI_API_KEY',None)
    os.environ['DEVHUB_AI_ENABLED']='false'
    r=client.get('/api/assisted-requirements/status')
    assert r.status_code==200
    assert r.json()['enabled'] is False
    assert r.json()['configured'] is False

def test_assisted_analysis_does_not_create_register_item_when_disabled():
    project=client.get('/api/projects').json()[0]
    before=len(client.get('/api/register').json())
    r=client.post('/api/assisted-requirements/analyse',json={"project_id":project['id'],"feedback":"The mobile page scrolls sideways","attachments":[]})
    assert r.status_code==503
    after=len(client.get('/api/register').json())
    assert before==after

def test_attachment_validation():
    item=client.get('/api/register').json()[0]
    r=client.post(f"/api/register/{item['id']}/attachments",files=[('files',('x.exe',b'bad','application/octet-stream'))])
    assert r.status_code==415

def test_logo_validation():
    project=client.get('/api/projects').json()[0]
    r=client.post(f"/api/projects/{project['id']}/logo",files={'file':('x.exe',b'bad','application/octet-stream')})
    assert r.status_code==415

def test_project_logo_upload_get_and_remove():
    project=client.get('/api/projects').json()[0]
    pid=project['id']
    svg=b'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="blue"/></svg>'
    uploaded=client.post(f'/api/projects/{pid}/logo',files={'file':('logo.svg',svg,'image/svg+xml')})
    assert uploaded.status_code==200
    assert uploaded.json()['logo_url']==f'/api/projects/{pid}/logo'
    refreshed=next(p for p in client.get('/api/projects').json() if p['id']==pid)
    assert refreshed['logo_path']
    served=client.get(f'/api/projects/{pid}/logo')
    assert served.status_code==200
    assert b'<svg' in served.content
    removed=client.delete(f'/api/projects/{pid}/logo')
    assert removed.status_code==204
    refreshed=next(p for p in client.get('/api/projects').json() if p['id']==pid)
    assert refreshed['logo_path'] is None
    assert client.get(f'/api/projects/{pid}/logo').status_code==404
