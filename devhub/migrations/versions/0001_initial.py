"""Initial DevHub schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("projects",
        sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(120),nullable=False),sa.Column("code",sa.String(12),nullable=False),
        sa.Column("github_owner",sa.String(120),nullable=False),sa.Column("github_repo",sa.String(160),nullable=False),sa.Column("default_branch",sa.String(120),nullable=False),
        sa.Column("roadmap_path",sa.String(255),nullable=False),sa.Column("changelog_path",sa.String(255),nullable=False),sa.Column("active",sa.Boolean(),nullable=False),
        sa.Column("latest_version",sa.String(80)),sa.Column("latest_release_url",sa.String(500)),sa.Column("latest_release_at",sa.DateTime()),
        sa.Column("github_cache_json",sa.Text()),sa.Column("github_refreshed_at",sa.DateTime()),sa.UniqueConstraint("code"))
    op.create_index("ix_projects_code","projects",["code"])
    op.create_table("register_items",
        sa.Column("id",sa.Integer(),primary_key=True),sa.Column("project_id",sa.Integer(),sa.ForeignKey("projects.id"),nullable=False),sa.Column("item_key",sa.String(32),nullable=False),
        sa.Column("item_type",sa.String(40),nullable=False),sa.Column("title",sa.String(240),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("priority",sa.String(20),nullable=False),
        sa.Column("status",sa.String(40),nullable=False),sa.Column("target_release",sa.String(80)),sa.Column("actual_behaviour",sa.Text(),nullable=False),sa.Column("expected_behaviour",sa.Text(),nullable=False),
        sa.Column("testing_instructions",sa.Text(),nullable=False),sa.Column("github_pr_url",sa.String(500)),sa.Column("completed_release",sa.String(80)),sa.Column("completed_at",sa.DateTime()),
        sa.Column("notes",sa.Text(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.UniqueConstraint("item_key"))
    op.create_index("ix_register_items_project_id","register_items",["project_id"]); op.create_index("ix_register_items_item_key","register_items",["item_key"])
    op.create_table("acceptance_criteria",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("item_id",sa.Integer(),sa.ForeignKey("register_items.id"),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("sort_order",sa.Integer(),nullable=False))
    op.create_index("ix_acceptance_criteria_item_id","acceptance_criteria",["item_id"])
    op.create_table("attachments",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("item_id",sa.Integer(),sa.ForeignKey("register_items.id"),nullable=False),sa.Column("original_name",sa.String(255),nullable=False),sa.Column("stored_name",sa.String(255),nullable=False),sa.Column("content_type",sa.String(120),nullable=False),sa.Column("size_bytes",sa.Integer(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False),sa.UniqueConstraint("stored_name"))
    op.create_index("ix_attachments_item_id","attachments",["item_id"])
    op.create_table("releases",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("project_id",sa.Integer(),sa.ForeignKey("projects.id"),nullable=False),sa.Column("planned_version",sa.String(80)),sa.Column("actual_version",sa.String(80)),sa.Column("status",sa.String(40),nullable=False),sa.Column("release_url",sa.String(500)),sa.Column("pr_url",sa.String(500)),sa.Column("release_at",sa.DateTime()),sa.Column("notes",sa.Text(),nullable=False),sa.Column("roadmap_updated",sa.Boolean(),nullable=False),sa.Column("changelog_updated",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_index("ix_releases_project_id","releases",["project_id"])
    op.create_table("release_items",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("release_id",sa.Integer(),sa.ForeignKey("releases.id"),nullable=False),sa.Column("item_id",sa.Integer(),sa.ForeignKey("register_items.id"),nullable=False),sa.UniqueConstraint("release_id","item_id"))
    op.create_index("ix_release_items_release_id","release_items",["release_id"]); op.create_index("ix_release_items_item_id","release_items",["item_id"])
    op.create_table("acceptance_test_results",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("release_id",sa.Integer(),sa.ForeignKey("releases.id"),nullable=False),sa.Column("criterion_id",sa.Integer(),sa.ForeignKey("acceptance_criteria.id"),nullable=False),sa.Column("status",sa.String(24),nullable=False),sa.Column("notes",sa.Text(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.UniqueConstraint("release_id","criterion_id"))
    op.create_index("ix_acceptance_test_results_release_id","acceptance_test_results",["release_id"]); op.create_index("ix_acceptance_test_results_criterion_id","acceptance_test_results",["criterion_id"])

def downgrade():
    for table in ["acceptance_test_results","release_items","releases","attachments","acceptance_criteria","register_items","projects"]: op.drop_table(table)
