"""Add roadmap reconciliation metadata

Revision ID: 0004_reconciliation
Revises: 0003_roadmap_intelligence
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_reconciliation"
down_revision = "0003_roadmap_intelligence"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("roadmap_current_override", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("roadmap_next_override", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("changelog_source_sha", sa.String(80), nullable=True))
        batch.add_column(sa.Column("changelog_parsed_version", sa.String(80), nullable=True))
        batch.add_column(sa.Column("changelog_parsed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("changelog_status", sa.String(64), nullable=True))
        batch.add_column(sa.Column("github_rate_limit_remaining", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("github_rate_limit_limit", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("github_rate_limit_reset_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("github_backoff_until", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("github_failure_count", sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("releases") as batch:
        batch.add_column(sa.Column("roadmap_phase_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_releases_roadmap_phase", "roadmap_phases", ["roadmap_phase_id"], ["id"])
        batch.add_column(sa.Column("roadmap_reconciliation_status", sa.String(64), nullable=True))
        batch.add_column(sa.Column("changelog_reconciliation_status", sa.String(64), nullable=True))


def downgrade():
    with op.batch_alter_table("releases") as batch:
        batch.drop_column("changelog_reconciliation_status")
        batch.drop_column("roadmap_reconciliation_status")
        batch.drop_constraint("fk_releases_roadmap_phase", type_="foreignkey")
        batch.drop_column("roadmap_phase_id")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("github_failure_count")
        batch.drop_column("github_backoff_until")
        batch.drop_column("github_rate_limit_reset_at")
        batch.drop_column("github_rate_limit_limit")
        batch.drop_column("github_rate_limit_remaining")
        batch.drop_column("changelog_status")
        batch.drop_column("changelog_parsed_at")
        batch.drop_column("changelog_parsed_version")
        batch.drop_column("changelog_source_sha")
        batch.drop_column("roadmap_next_override")
        batch.drop_column("roadmap_current_override")
