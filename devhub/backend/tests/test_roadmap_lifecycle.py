from types import SimpleNamespace

from backend.app.main import _choose_current_next


def phase(pid, order, version, title, status='Unknown', ignored=False, phase_type='Release'):
    return SimpleNamespace(id=pid, sort_order=order, version=version, title=title, status=status, ignored=ignored, phase_type=phase_type)


def project(version='v0.4.0', current=None, next_id=None, current_override=False, next_override=False):
    return SimpleNamespace(latest_version=version, roadmap_current_phase_id=current, roadmap_next_phase_id=next_id, roadmap_current_override=current_override, roadmap_next_override=next_override)


def test_automatic_current_and_next_detection():
    phases=[phase(1,0,'v0.4.0','Roadmap Intelligence'),phase(2,1,'v0.5.x','Assisted Requirements','Planned')]
    assert _choose_current_next(project(),phases)==(1,2)


def test_current_phase_override():
    phases=[phase(1,0,'v0.4.0','Roadmap Intelligence'),phase(2,1,'v0.5.x','Assisted Requirements','Planned')]
    assert _choose_current_next(project(current=2,current_override=True),phases)[0]==2


def test_next_phase_override():
    phases=[phase(1,0,'v0.4.0','Roadmap Intelligence'),phase(2,1,'v0.5.x','Assisted Requirements'),phase(3,2,'v0.6.x','Release Execution')]
    assert _choose_current_next(project(next_id=3,next_override=True),phases)[1]==3


def test_cleared_override_uses_detection():
    phases=[phase(1,0,'v0.4.0','Roadmap Intelligence'),phase(2,1,'v0.5.x','Assisted Requirements')]
    assert _choose_current_next(project(current=2,current_override=False),phases)[0]==1


def test_ignored_phase_excluded_from_planning():
    phases=[phase(1,0,'v0.4.0','Roadmap Intelligence'),phase(2,1,'v0.5.x','Reference Notes',ignored=True),phase(3,2,'v0.6.x','Release Execution')]
    assert _choose_current_next(project(),phases)==(1,3)
