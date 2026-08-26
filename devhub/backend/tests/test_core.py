import os
os.environ["DEVHUB_DATABASE_URL"]="sqlite:///./test-devhub.db"
os.environ["DEVHUB_DATA_DIR"]="./test-data"
from fastapi.testclient import TestClient
from backend.app.database import Base, engine
from backend.app.main import app

client=TestClient(app)

def setup_module(): Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
def teardown_module(): Base.metadata.drop_all(bind=engine)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200; assert r.json()['version']=='0.1.0'

def test_project_and_register_flow():
    p=client.post('/api/projects',json={"name":"Test App","code":"TA","github_owner":"owner","github_repo":"repo","default_branch":"main","roadmap_path":"ROADMAP.md","changelog_path":"CHANGELOG.md","active":True})
    assert p.status_code==201
    pid=p.json()['id']
    item=client.post('/api/register',json={"project_id":pid,"item_type":"Defect","title":"Mobile overflow","description":"Page scrolls sideways","priority":"High","status":"Approved","actual_behaviour":"Horizontal scroll","expected_behaviour":"No horizontal scroll","testing_instructions":"Test portrait mobile","criteria":[{"description":"No horizontal scrolling","sort_order":0}]})
    assert item.status_code==201
    assert item.json()['item_key']=='TA-DEF-0001'
    assert len(item.json()['criteria'])==1
    release=client.post('/api/releases',json={"project_id":pid,"item_ids":[item.json()['id']]})
    assert release.status_code==201

def test_attachment_validation():
    item=client.get('/api/register').json()[0]
    r=client.post(f"/api/register/{item['id']}/attachments",files=[('files',('x.exe',b'bad','application/octet-stream'))])
    assert r.status_code==415
