"""Add roadmap intelligence tables

Revision ID: 0003_roadmap_intelligence
Revises: 0002_github_sync
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_roadmap_intelligence"
down_revision = "0002_github_sync"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roadmap_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_path", sa.String(255), nullable=False),
        sa.Column("source_sha", sa.String(80), nullable=True),
        sa.Column("markdown_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(), nullable=True),
        sa.Column("parse_status", sa.String(40), nullable=False, server_default="Unknown"),
        sa.Column("parse_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_roadmap_snapshots_project_id", "roadmap_snapshots", ["project_id"])

    op.create_table(
        "roadmap_phases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("roadmap_snapshots.id"), nullable=False),
        sa.Column("version", sa.String(80), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("phase_type", sa.String(40), nullable=False, server_default="Section"),
        sa.Column("status", sa.String(40), nullable=False, server_default="Unknown"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("heading_level", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("raw_heading", sa.String(500), nullable=False),
        sa.Column("ignored", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_roadmap_phases_project_id", "roadmap_phases", ["project_id"])
    op.create_index("ix_roadmap_phases_snapshot_id", "roadmap_phases", ["snapshot_id"])

    op.create_table(
        "roadmap_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("roadmap_phase_id", sa.Integer(), sa.ForeignKey("roadmap_phases.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_roadmap_items_phase_id", "roadmap_items", ["roadmap_phase_id"])

    with op.batch_alter_table("register_items") as batch:
        batch.add_column(sa.Column("roadmap_phase_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_register_items_roadmap_phase", "roadmap_phases", ["roadmap_phase_id"], ["id"])

    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("roadmap_current_phase_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("roadmap_next_phase_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_projects_current_roadmap_phase", "roadmap_phases", ["roadmap_current_phase_id"], ["id"])
        batch.create_foreign_key("fk_projects_next_roadmap_phase", "roadmap_phases", ["roadmap_next_phase_id"], ["id"])


def downgrade():
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("fk_projects_next_roadmap_phase", type_="foreignkey")
        batch.drop_constraint("fk_projects_current_roadmap_phase", type_="foreignkey")
        batch.drop_column("roadmap_next_phase_id")
        batch.drop_column("roadmap_current_phase_id")
    with op.batch_alter_table("register_items") as batch:
        batch.drop_constraint("fk_register_items_roadmap_phase", type_="foreignkey")
        batch.drop_column("roadmap_phase_id")
    op.drop_index("ix_roadmap_items_phase_id", table_name="roadmap_items")
    op.drop_table("roadmap_items")
    op.drop_index("ix_roadmap_phases_snapshot_id", table_name="roadmap_phases")
    op.drop_index("ix_roadmap_phases_project_id", table_name="roadmap_phases")
    op.drop_table("roadmap_phases")
    op.drop_index("ix_roadmap_snapshots_project_id", table_name="roadmap_snapshots")
    op.drop_table("roadmap_snapshots")
