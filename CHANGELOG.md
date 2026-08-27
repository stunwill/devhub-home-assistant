# Changelog

All notable changes to DevHub are documented here.

## [0.3.0] - 2026-08-27

### Added

- Polished Portfolio dashboard with responsive, information-dense project cards.
- Card-level latest release, open PR, last merged PR, CI and GitHub sync status.
- Sidebar GitHub synchronisation summary with real degraded/operational state.
- Backend GitHub synchronisation loop for active projects approximately every 15 minutes, independent of the browser session.
- `/api/projects/sync-summary` for Portfolio-level GitHub health information.
- aarch64 Home Assistant add-on startup smoke test that verifies migrations, FastAPI startup and `/api/health` availability.

### Changed

- Portfolio is now the main operational development view rather than a simple project listing.
- Mobile Portfolio layout now uses a dedicated single-column card design with no page-level horizontal scrolling.
- Project cards now use uploaded artwork where available and accessible fallback icons otherwise.
- Home Assistant and frontend version metadata bumped to 0.3.0.
- Documentation updated for background synchronisation and startup regression protection.

### Preserved

- Repository-URL onboarding and GitHub metadata discovery from v0.2.0.
- Last-known-good GitHub cache when refresh fails.
- PR #4 startup import-path fix using `PYTHONPATH=/app`.
- Raspberry Pi 5 / aarch64 image build protection.
- Existing Register, Feedback, Release Builder and Roadmap functionality.

## [0.2.0] - 2026-08-27

### Added

- GitHub repository URL onboarding with repository discovery and validation.
- Automatic retrieval of repository description, visibility, default branch, releases, open PRs, last merged PR, latest commit and CI state.
- Responsive project-card dashboard showing current release, open PRs, last merged PR, CI state and sync age.
- Project Details view with repository, PR, release and roadmap information.
- Project logo/icon upload stored in persistent runtime storage.
- Roadmap and changelog path detection during project onboarding.
- Manual all-project refresh plus periodic 15-minute refresh while DevHub is open.
- Sync status/error tracking that preserves last known good GitHub data.
- Alembic migration for GitHub synchronisation and project artwork metadata.

### Changed

- Project setup now prioritises a GitHub repository URL instead of manual GitHub metadata entry.
- Updated public-repository Home Assistant installation guidance.
- Bumped DevHub application and add-on version to 0.2.0.

### Preserved

- Raspberry Pi 5 / aarch64 Home Assistant image build validation introduced by PR #2.
- Existing defect/enhancement register, feedback attachments, release builder and roadmap-aware prompt generation.

## [0.1.0] - 2026-08-26

### Added

- Initial Home Assistant add-on foundation with ingress support.
- React/Vite frontend and FastAPI backend architecture.
- SQLite persistence with Alembic migrations.
- Portfolio dashboard and project configuration.
- GitHub release metadata refresh and roadmap retrieval.
- Defect and enhancement register with acceptance criteria and testing instructions.
- Feedback capture with image and video attachment support.
- Next Release Builder with roadmap-aware development prompt generation.
- Release records, acceptance testing, readiness and release history foundations.
- GitHub Actions CI for backend and frontend validation.
- Security controls for secrets, uploads, Markdown and persistent runtime data.
