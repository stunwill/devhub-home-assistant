from types import SimpleNamespace

from backend.app.release_execution import _merge_readiness, _normalise_version, _score_pr


def release(version='0.6.0', title='Release Execution'):
    return SimpleNamespace(planned_version=version, roadmap_phase=SimpleNamespace(title=title))


def pr(**overrides):
    value={
        'number':21,
        'title':'DevHub v0.6.0: Release Execution',
        'state':'open',
        'draft':False,
        'mergeable':True,
        'merged_at':None,
        'head':{'ref':'release/v0.6.0-release-execution'},
    }
    value.update(overrides)
    return value


def test_normalise_version_accepts_v_prefix():
    assert _normalise_version('v0.6.0') == '0.6.0'
    assert _normalise_version('0.6.0') == '0.6.0'


def test_pr_matching_uses_version_and_branch_evidence():
    score,evidence=_score_pr(pr(),release())
    assert score >= 11
    assert 'planned version appears in PR title' in evidence
    assert 'planned version appears in branch name' in evidence


def test_merge_readiness_requires_confirmed_passing_ci_and_mergeability():
    state=_merge_readiness(pr(),{'state':'success'})
    assert state['ready'] is True
    assert state['status']=='Ready to merge'


def test_merge_readiness_blocks_draft_pr():
    state=_merge_readiness(pr(draft=True),{'state':'success'})
    assert state['ready'] is False
    assert 'PR is still a draft' in state['reasons']


def test_merge_readiness_blocks_failing_ci():
    state=_merge_readiness(pr(),{'state':'failure'})
    assert state['ready'] is False
    assert 'CI is failing' in state['reasons']


def test_merge_readiness_blocks_running_ci():
    state=_merge_readiness(pr(),{'state':'pending'})
    assert state['ready'] is False
    assert 'CI is still running' in state['reasons']


def test_merge_readiness_blocks_closed_unmerged_pr():
    state=_merge_readiness(pr(state='closed'),{'state':'success'})
    assert state['ready'] is False
    assert 'PR is closed without merge' in state['reasons']


def test_merge_readiness_does_not_assume_unknown_mergeability_is_safe():
    state=_merge_readiness(pr(mergeable=None),{'state':'success'})
    assert state['ready'] is False
    assert 'GitHub mergeability is not yet confirmed' in state['reasons']


def test_no_pr_is_not_ready():
    state=_merge_readiness(None,{'state':'unknown'})
    assert state['ready'] is False
    assert state['status']=='Not ready'
