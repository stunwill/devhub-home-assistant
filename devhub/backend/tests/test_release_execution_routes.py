import os
os.environ.setdefault('DEVHUB_DATABASE_URL','sqlite:///./test-release-execution.db')
os.environ.setdefault('DEVHUB_DATA_DIR','./test-release-execution-data')

from backend.app.server import app


def test_release_execution_routes_are_registered():
    paths={route.path for route in app.routes}
    assert '/api/releases/{release_id}/execution' in paths
    assert '/api/releases/{release_id}/execution/pr' in paths
    assert '/api/releases/{release_id}/execution/prompt' in paths
    assert '/api/releases/execution-summary' in paths


def test_release_execution_does_not_expose_merge_or_publish_routes():
    paths={route.path.lower() for route in app.routes}
    assert not any('merge-pull' in path or 'merge-pr' in path for path in paths)
    assert not any('publish-release' in path or 'create-github-release' in path for path in paths)
