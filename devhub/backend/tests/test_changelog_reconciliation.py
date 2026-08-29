from types import SimpleNamespace

from backend.app.reconciliation import compare_changelog, normalise_version, parse_changelog_latest, reconcile_release


def test_common_changelog_heading_formats():
    assert parse_changelog_latest('## [0.4.0]\n')['version'] == '0.4.0'
    assert parse_changelog_latest('## v0.4.0\n')['version'] == '0.4.0'
    assert parse_changelog_latest('## 0.4.0\n')['version'] == '0.4.0'


def test_unreleased_is_skipped():
    parsed = parse_changelog_latest('## Unreleased\n- Work\n## [0.4.0]\n- Done\n')
    assert parsed['version'] == '0.4.0'


def test_malformed_empty_and_unrecognisable():
    assert parse_changelog_latest('')['status'] == 'Unable to determine'
    assert parse_changelog_latest('# Changelog\n## bananas\n')['status'] == 'Unable to determine'
    assert parse_changelog_latest('## [0.4]\n')['status'] == 'Unable to determine'


def test_v_prefix_normalisation_and_comparison():
    assert normalise_version('v0.4.0') == '0.4.0'
    assert compare_changelog('## 0.4.0', 'v0.4.0')['status'] == 'Current'
    assert compare_changelog('## 0.3.0', 'v0.4.0')['status'] == 'Changelog may require reconciliation'
    assert compare_changelog('## 0.5.0', 'v0.4.0')['status'] == 'Ahead of detected release'


def test_missing_changelog():
    assert compare_changelog(None, 'v0.4.0')['status'] == 'Missing changelog'


def phase(completed=(True, True), statuses=('Released',), version='v0.4.0'):
    items = [SimpleNamespace(text=f'Item {i}', completed=value) for i, value in enumerate(completed)]
    register = [SimpleNamespace(status=s, completed_release='v0.4.0' if s == 'Released' else None) for s in statuses]
    return SimpleNamespace(id=2, version=version, title='Roadmap Intelligence', items=items, register_items=register)


def release(planned='v0.4.0', actual=None):
    return SimpleNamespace(planned_version=planned, actual_version=actual)


def test_completed_roadmap_phase_reconciles():
    result = reconcile_release('v0.4.0', release(), phase(), {'status':'Current'})
    assert result['status'] == 'Reconciled'
    assert result['repository_state'] == 'Reconciled'


def test_partially_delivered_phase_requires_reconciliation():
    result = reconcile_release('v0.4.0', release(), phase((True, False)), {'status':'Current'})
    assert result['status'] == 'Reconciliation required'
    assert result['potentially_outstanding'] == 1


def test_mismatched_release_version_requires_review():
    result = reconcile_release('v0.4.1', release('v0.4.0'), phase(version='v0.4.1'), {'status':'Current'})
    assert result['status'] == 'Reconciliation required'
    assert result['release_match'] == 'Review required'


def test_changelog_warning_recommends_reconciliation():
    result = reconcile_release('v0.4.0', release(), phase(), {'status':'Changelog may require reconciliation'})
    assert result['status'] == 'Reconciliation recommended'


def test_missing_devhub_release_record_is_diagnosed_separately():
    result = reconcile_release('v0.35.0', None, phase(version='v0.35.0'), {'status':'Current'})
    assert result['status'] == 'Reconciliation recommended'
    assert result['repository_state'] == 'Reconciled'
    assert result['release_history_status'] == 'Release record missing for v0.35.0'
    assert 'internal release record' in result['reasons'][0]


def test_unable_to_determine_without_release_version():
    result = reconcile_release(None, release(), phase(), {'status':'Unable to determine'})
    assert result['status'] == 'Unable to determine'
