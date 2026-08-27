"""Add GitHub synchronisation project fields

Revision ID: 0002_github_sync
Revises: 0001_initial
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_github_sync"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("repository_url", sa.String(500), nullable=True))
        batch.add_column(sa.Column("repository_description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("repository_visibility", sa.String(20), nullable=True))
        batch.add_column(sa.Column("logo_path", sa.String(500), nullable=True))
        batch.add_column(sa.Column("github_last_attempt_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("github_sync_status", sa.String(32), nullable=False, server_default="Never"))
        batch.add_column(sa.Column("github_sync_error", sa.Text(), nullable=True))
    op.execute("UPDATE projects SET repository_url = 'https://github.com/' || github_owner || '/' || github_repo WHERE repository_url IS NULL")

def downgrade():
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("github_sync_error")
        batch.drop_column("github_sync_status")
        batch.drop_column("github_last_attempt_at")
        batch.drop_column("logo_path")
        batch.drop_column("repository_visibility")
        batch.drop_column("repository_description")
        batch.drop_column("repository_url")
