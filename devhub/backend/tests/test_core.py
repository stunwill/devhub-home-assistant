import os
os.environ["DEVHUB_DATABASE_URL"]="sqlite:///./test-devhub.db"
os.environ["DEVHUB_DATA_DIR"]="./test-data"
from fastapi.testclient import TestClient
from backend.app.database import Base, engine
from backend.app.github_service import GitHubService
from backend.app.main import app

client=TestClient(app)

def setup_module(): Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
def teardown_module(): Base.metadata.drop_all(bind=engine)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200; assert r.json()['version']=='0.4.2'

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

def test_project_and_register_flow():
    p=client.post('/api/projects',json={"name":"Test App","code":"TA","github_owner":"owner","github_repo":"repo","repository_url":"https://github.com/owner/repo","default_branch":"main","roadmap_path":"ROADMAP.md","changelog_path":"CHANGELOG.md","active":True})
    assert p.status_code==201
    pid=p.json()['id']
    assert p.json()['github_sync_status']=='Never'
    assert p.json()['roadmap_current_override'] is False
    item=client.post('/api/register',json={"project_id":pid,"item_type":"Defect","title":"Mobile overflow","description":"Page scrolls sideways","priority":"High","status":"Approved","actual_behaviour":"Horizontal scroll","expected_behaviour":"No horizontal scroll","testing_instructions":"Test portrait mobile","criteria":[{"description":"No horizontal scrolling","sort_order":0}]})
    assert item.status_code==201
    assert item.json()['item_key']=='TA-DEF-0001'
    assert item.json()['roadmap_phase_id'] is None
    assert len(item.json()['criteria'])==1
    release=client.post('/api/releases',json={"project_id":pid,"item_ids":[item.json()['id']]})
    assert release.status_code==201
    assert release.json()['roadmap_phase_id'] is None

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

def test_attachment_validation():
    item=client.get('/api/register').json()[0]
    r=client.post(f"/api/register/{item['id']}/attachments",files=[('files',('x.exe',b'bad','application/octet-stream'))])
    assert r.status_code==415

def test_logo_validation():
    project=client.get('/api/projects').json()[0]
    r=client.post(f"/api/projects/{project['id']}/logo",files={'file':('x.exe',b'bad','application/octet-stream')})
    assert r.status_code==415
