from pathlib import Path


def test_reconciliation_migration_is_forward_from_roadmap_intelligence():
    text = Path('migrations/versions/0004_reconciliation.py').read_text()
    assert 'down_revision = "0003_roadmap_intelligence"' in text
    assert 'roadmap_current_override' in text
    assert 'roadmap_next_override' in text
    assert 'roadmap_phase_id' in text
    assert 'changelog_source_sha' in text
    assert 'github_rate_limit_remaining' in text
    assert 'github_backoff_until' in text
    assert 'roadmap_reconciliation_status' in text


def test_migration_preserves_existing_tables_and_data():
    text = Path('migrations/versions/0004_reconciliation.py').read_text()
    assert 'drop_table' not in text.split('def upgrade():',1)[1].split('def downgrade():',1)[0]
    assert 'drop_column' not in text.split('def upgrade():',1)[1].split('def downgrade():',1)[0]
