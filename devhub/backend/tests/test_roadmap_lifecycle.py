from types import SimpleNamespace

from backend.app.main import _choose_current_next
from backend.app.roadmap_parser import lifecycle_status, version_contains


def phase(pid, order, version, title, status='Unknown', ignored=False, phase_type='Release'):
    return SimpleNamespace(id=pid, sort_order=order, version=version, title=title, status=status, ignored=ignored, phase_type=phase_type)


def project(version='v0.35.0', current=None, next_id=None, current_override=False, next_override=False):
    return SimpleNamespace(latest_version=version, roadmap_current_phase_id=current, roadmap_next_phase_id=next_id, roadmap_current_override=current_override, roadmap_next_override=next_override)


def test_descending_versions_do_not_move_backwards_and_future_bucket_is_next():
    phases=[phase(1,0,'v0.35.0','Current'),phase(2,1,'v0.34.0','Old'),phase(3,2,'v0.33.0','Older'),phase(4,3,None,'Future',phase_type='Future',status='Future')]
    assert _choose_current_next(project(),phases)==(1,4)
    assert lifecycle_status(phases[1],'v0.35.0')=='Historical / Released'
    assert lifecycle_status(phases[2],'v0.35.0')=='Historical / Released'


def test_future_semver_is_preferred_over_source_order():
    phases=[phase(1,0,'v0.36.0','Planned','Planned'),phase(2,1,'v0.35.0','Current'),phase(3,2,'v0.34.0','Old')]
    assert _choose_current_next(project(),phases)==(2,1)


def test_ascending_versions_select_next_semver():
    phases=[phase(1,0,'v0.34.0','Old'),phase(2,1,'v0.35.0','Current'),phase(3,2,'v0.36.0','Next','Planned')]
    assert _choose_current_next(project(),phases)==(2,3)


def test_patch_progression_is_valid_next():
    phases=[phase(1,0,'v0.35.0','Current'),phase(2,1,'v0.35.1','Patch','Planned')]
    assert _choose_current_next(project(),phases)==(1,2)


def test_no_future_never_falls_back_to_older_version():
    phases=[phase(1,0,'v0.35.0','Current'),phase(2,1,'v0.34.0','Old')]
    assert _choose_current_next(project(),phases)==(1,None)


def test_version_band_contains_current_release_and_progresses_to_next_band():
    phases=[phase(1,0,'v0.4.x','Old line'),phase(2,1,'v0.5.x','Current line'),phase(3,2,'v0.6.x','Next line')]
    assert version_contains('v0.5.x','v0.5.4') is True
    assert lifecycle_status(phases[0],'v0.5.4')=='Historical / Released'
    assert lifecycle_status(phases[1],'v0.5.4')=='Current / Released'
    assert lifecycle_status(phases[2],'v0.5.4')=='Future / Planned'
    assert _choose_current_next(project('v0.5.4'),phases)==(2,3)


def test_stale_in_progress_historical_phase_cannot_drive_next_phase():
    phases=[phase(1,0,'v0.2.0','Old in progress','In Progress'),phase(2,1,'v0.5.x','Current line'),phase(3,2,'v0.6.x','Next line','Planned')]
    assert _choose_current_next(project('v0.5.7'),phases)==(2,3)


def test_mediahub_dev_version_resolves_active_phase_and_future_bucket():
    phases=[
        phase(1,0,'v0.9.0','Plex Library Intelligence','Completed'),
        phase(2,1,'v0.10.0','Television Requests and Sonarr Workflow','In Progress'),
        phase(3,2,None,'Future',phase_type='Future',status='Future'),
    ]
    assert version_contains('v0.10.0','0.10.0-dev') is True
    assert _choose_current_next(project('0.10.0-dev'),phases)==(2,3)
    assert lifecycle_status(phases[0],'0.10.0-dev')=='Historical / Released'
    assert lifecycle_status(phases[1],'0.10.0-dev')=='Current / Released'


def test_current_phase_override():
    phases=[phase(1,0,'v0.35.0','Current'),phase(2,1,'v0.36.0','Next','Planned')]
    assert _choose_current_next(project(current=2,current_override=True),phases)[0]==2


def test_next_phase_override_can_select_future_bucket():
    phases=[phase(1,0,'v0.35.0','Current'),phase(2,1,'v0.36.0','Next','Planned'),phase(3,2,None,'Future',phase_type='Future',status='Future')]
    assert _choose_current_next(project(next_id=3,next_override=True),phases)[1]==3


def test_cleared_override_uses_detection():
    phases=[phase(1,0,'v0.35.0','Current'),phase(2,1,'v0.36.0','Next','Planned')]
    assert _choose_current_next(project(current=2,current_override=False),phases)[0]==1


def test_ignored_phase_excluded_from_planning():
    phases=[phase(1,0,'v0.35.0','Current'),phase(2,1,'v0.36.0','Reference',ignored=True),phase(3,2,'v0.37.0','Next','Planned')]
    assert _choose_current_next(project(),phases)==(1,3)
