from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    github_owner: Mapped[str] = mapped_column(String(120))
    github_repo: Mapped[str] = mapped_column(String(160))
    default_branch: Mapped[str] = mapped_column(String(120), default="main")
    roadmap_path: Mapped[str] = mapped_column(String(255), default="ROADMAP.md")
    changelog_path: Mapped[str] = mapped_column(String(255), default="CHANGELOG.md")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    latest_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latest_release_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latest_release_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    github_cache_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items = relationship("RegisterItem", back_populates="project", cascade="all, delete-orphan")
    releases = relationship("Release", back_populates="project", cascade="all, delete-orphan")

class RegisterItem(Base):
    __tablename__ = "register_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    item_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(40), default="New")
    target_release: Mapped[str | None] = mapped_column(String(80), nullable=True)
    actual_behaviour: Mapped[str] = mapped_column(Text, default="")
    expected_behaviour: Mapped[str] = mapped_column(Text, default="")
    testing_instructions: Mapped[str] = mapped_column(Text, default="")
    github_pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_release: Mapped[str | None] = mapped_column(String(80), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project = relationship("Project", back_populates="items")
    criteria = relationship("AcceptanceCriterion", back_populates="item", cascade="all, delete-orphan", order_by="AcceptanceCriterion.sort_order")
    attachments = relationship("Attachment", back_populates="item", cascade="all, delete-orphan")

class AcceptanceCriterion(Base):
    __tablename__ = "acceptance_criteria"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("register_items.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    item = relationship("RegisterItem", back_populates="criteria")

class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("register_items.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    item = relationship("RegisterItem", back_populates="attachments")

class Release(Base):
    __tablename__ = "releases"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    planned_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    actual_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Planning")
    release_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    release_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    roadmap_updated: Mapped[bool] = mapped_column(Boolean, default=False)
    changelog_updated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="releases")
    scope = relationship("ReleaseItem", back_populates="release", cascade="all, delete-orphan")
    results = relationship("AcceptanceTestResult", back_populates="release", cascade="all, delete-orphan")

class ReleaseItem(Base):
    __tablename__ = "release_items"
    __table_args__ = (UniqueConstraint("release_id", "item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("releases.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("register_items.id"), index=True)
    release = relationship("Release", back_populates="scope")
    item = relationship("RegisterItem")

class AcceptanceTestResult(Base):
    __tablename__ = "acceptance_test_results"
    __table_args__ = (UniqueConstraint("release_id", "criterion_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("releases.id"), index=True)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("acceptance_criteria.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="Not Tested")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    release = relationship("Release", back_populates="results")
    criterion = relationship("AcceptanceCriterion")
